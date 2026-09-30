import streamlit as st
import pandas as pd
import json, os, resend
from datetime import datetime

st.set_page_config(page_title="IBK Lund", layout="wide")
DATA_FILE = "admin_data.json"

# SÄKER LÖSNING: Hämtar nyckeln dolt från Streamlits inställningar istället för att hårdkoda den
if "RESEND_API_KEY" in st.secrets:
    resend.api_key = st.secrets["RESEND_API_KEY"]
else:
    st.error("⚠️ RESEND_API_KEY saknas i Streamlit Secrets!")

MAIL_AVSANDARE = "onboarding@resend.dev"

DEFAULT_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2", "LundaLägret", "NovaOpen"]
DEFAULT_KONTON = ["5800 Biljetter", "5830 Kost", "5831 Logi", "7330 Bilersättning", "2999 Övrigt"]
DEFAULT_ATTESTANTER = [
    {"namn": "Christer Sölve", "epost": "christer@solve.se", "lag": ["Herr Elit"]},
    {"namn": "Magnus Berglund", "epost": "magnus.berglund@ibklund.se", "lag": ["LundaLägret", "NovaOpen"]}
]

def ladda_data():
    str_dat = {"lag": DEFAULT_LAG.copy(), "konton": DEFAULT_KONTON.copy(), "attestanter": DEFAULT_ATTESTANTER.copy(), "vantande_utlagg": [], "godkanda_utlagg": []}
    if not os.path.exists(DATA_FILE): return str_dat
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        for k, v in str_dat.items():
            if k not in data or not isinstance(data[k], type(v)): data[k] = v
        if not data["attestanter"]: data["attestanter"] = DEFAULT_ATTESTANTER.copy()
        return data
    except: return str_dat

def spara_data():
    try:
        temp = {k: st.session_state[k] for k in ["lag", "konton", "attestanter", "vantande_utlagg", "godkanda_utlagg"]}
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(temp, f, ensure_ascii=False, indent=4)
    except: pass

if "lag" not in st.session_state or not st.session_state["attestanter"]:
    for k, v in ladda_data().items(): st.session_state[k] = v
    spara_data()

for m in ["minne_namn", "minne_bank", "minne_clearing", "minne_konto", "bekraftelse_meddelande", "an_namn", "an_mail", "an_lag"]:
    if m not in st.session_state: st.session_state[m] = "" if m != "an_lag" else []

def skicka_notis_mail(till, namn, lag, belopp, kat, av):
    # ÄNDRA HÄR: Klistra in den exakta länken till din Streamlit-app (t.ex. https://streamlit.app)
    APP_LANK = "https://kvittohantering.streamlit.app/" 

    msg_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #003366; padding: 20px; text-align: center; color: white;">
            <h2 style="margin: 0; font-size: 22px;">IBK Lund</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.8;">Kvitto- & Utläggshantering</p>
        </div>
        <div style="padding: 24px; line-height: 1.6; color: #333;">
            <p style="font-size: 16px; margin-top: 0;">Hej <b>{namn}</b>,</p>
            <p>Ett nytt utlägg har registrerats och väntar på ditt godkännande.</p>
            
            <div style="background-color: #f9f9f9; border-left: 4px solid #003366; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 5px 0; color: #666; width: 120px;"><b>Inskickat av:</b></td><td style="padding: 5px 0;">{av}</td></tr>
                    <tr><td style="padding: 5px 0; color: #666;"><b>Lag/Aktivitet:</b></td><td style="padding: 5px 0;">{lag}</td></tr>
                    <tr><td style="padding: 5px 0; color: #666;"><b>Kategori:</b></td><td style="padding: 5px 0;">{kat}</td></tr>
                    <tr><td style="padding: 5px 0; color: #666;"><b>Belopp:</b></td><td style="padding: 5px 0; font-size: 16px; color: #003366;"><b>{belopp} kr</b></td></tr>
                </table>
            </div>
            
            <p style="margin-bottom: 25px;">Vänligen logga in i appen för att granska underlaget, korrigera eventuella uppgifter och attestera utlägget.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{APP_LANK}" style="background-color: #003366; color: white; padding: 12px 30px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">Gå till Attestfunktionen</a>
            </div>
        </div>
        <div style="background-color: #f4f4f4; padding: 15px; text-align: center; font-size: 12px; color: #888; border-top: 1px solid #ddd;">
            Detta är ett automatiskt meddelande från IBK Lunds kvittoapp.
        </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": "IBK Lund Kvittohantering <onboarding@resend.dev>", # Inlagt visningsnamn här!
            "to": till,
            "subject": f"🔔 Nytt utlägg att attestera - {lag}",
            "html": msg_html
        })
        return True
    except: 
        return False


st.sidebar.title("IBK Lund")
sida = st.sidebar.radio("Välj funktion:", ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"])

if sida == "📝 Registrera Utlägg":
    st.title("📝 Registrera nytt utlägg")
    st.info("ℹ️ Utbetalning sker runt den 25:e varje månad. Kvitton efter den 10:e utbetalas nästa månad.")
    if st.session_state["bekraftelse_meddelande"]:
        st.success(st.session_state["bekraftelse_meddelande"])
        st.session_state["bekraftelse_meddelande"] = ""
    with st.form("huvud_reg_form", clear_on_submit=True):
        namn_reg = st.text_input("Ditt Namn:", value=st.session_state["minne_namn"])
        lag_reg = st.selectbox("Välj lag / aktivitet:", options=st.session_state["lag"])
        konto_reg = st.selectbox("Välj konto:", options=st.session_state["konton"])
        belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0)
        st.subheader("Bankuppgifter för utbetalning")
        bank_reg = st.text_input("Bank:", value=st.session_state["minne_bank"])
        clearing_reg = st.text_input("Clearingnummer:", value=st.session_state["minne_clearing"])
        konto_nr_reg = st.text_input("Kontonummer:", value=st.session_state["minne_konto"])
        fil_reg = st.file_uploader("Ladda upp kvitto", type=["pdf", "png", "jpg", "jpeg"])
        if st.form_submit_button("Skicka in utlägg", type="primary"):
            if namn_reg and bank_reg and clearing_reg and konto_nr_reg:
                st.session_state["minne_namn"], st.session_state["minne_bank"], st.session_state["minne_clearing"], st.session_state["minne_konto"] = namn_reg.strip(), bank_reg.strip(), clearing_reg.strip(), konto_nr_reg.strip()
                utl = {"id": len(st.session_state["vantande_utlagg"]) + len(st.session_state["godkanda_utlagg"]) + 1, "namn": namn_reg.strip(), "lag": lag_reg, "kategori": konto_reg, "belopp": belopp_reg, "bank": bank_reg.strip(), "clearing": clearing_reg.strip(), "kontonummer": konto_nr_reg.strip(), "filnamn": fil_reg.name if fil_reg else "Inget underlag", "datum_inskickat": datetime.now().strftime("%Y-%m-%d")}
                st.session_state["vantande_utlagg"].append(utl)
                spara_data()
                att_namn = []
                for a in st.session_state["attestanter"]:
                    if lag_reg in a.get("lag", []):
                        att_namn.append(a["namn"])
                        skicka_notis_mail(a["epost"], a["namn"], lag_reg, belopp_reg, konto_reg, namn_reg)
                st.session_state["bekraftelse_meddelande"] = f"✅ Registrerat! Väntar på attest av {' & '.join(att_namn)}." if att_namn else f"✅ Registrerat! (Ingen attestant kopplad)."
                st.rerun()
            else: st.error("Fyll i alla namn- och bankuppgifter.")

elif sida == "✅ Attestfunktion":
    st.title("✅ Attestfunktion")
    att_namn = [a["namn"] for a in st.session_state["attestanter"]]
    if not att_namn: st.warning("🔒 Inga godkända attestanter finns i systemet.")
    else:
        aktiv = st.selectbox("Välj ditt namn:", options=["-- Välj namn --"] + att_namn)
        if aktiv != "-- Välj namn --":
            match = next(a for a in st.session_state["attestanter"] if a["namn"] == aktiv)
            st.success(f"Inloggad: {aktiv}. Behörig för: {', '.join(match['lag'])}")
            for u in list(st.session_state["vantande_utlagg"]):
                if u["lag"] in match["lag"]:
                    with st.container(border=True):
                        st.write(f"**Från:** {u['namn']} | **Val:** {u['lag']} | **Bank:** {u['bank']} {u['clearing']}-{u['kontonummer']}")
                        nk = st.selectbox(f"Konto:", options=st.session_state["konton"], index=st.session_state["konton"].index(u["kategori"]) if u["kategori"] in st.session_state["konton"] else 0, key=f"k_{u['id']}")
                        nb = st.number_input(f"Belopp:", value=float(u["belopp"]), key=f"b_{u['id']}")
                        if st.button(f"Godkänn #{u['id']}", type="primary", key=f"g_{u['id']}"):
                            u["kategori"], u["belopp"], u["attesterat_av"], u["datum_attesterat"] = nk, nb, aktiv, datetime.now().strftime("%Y-%m-%d")
                            st.session_state["godkanda_utlagg"].append(u); st.session_state["vantande_utlagg"].remove(u); spara_data(); st.rerun()
                        if st.button(f"Radera #{u['id']}", key=f"r_{u['id']}"): st.session_state["vantande_utlagg"].remove(u); spara_data(); st.rerun()
            st.subheader("Export till Spiris")
            df = pd.DataFrame([u for u in st.session_state["godkanda_utlagg"] if u["lag"] in match["lag"]])
            if not df.empty:
                cols = ["namn", "lag", "kategori", "belopp", "bank", "clearing", "kontonummer", "datum_attesterat"]
                st.dataframe(df[cols])
                st.download_button("📥 Ladda ner CSV", data=df[cols].to_csv(index=False, encoding="utf-8-sig"), file_name=f"spiris_{aktiv}.csv", mime="text/csv")
            else: st.info("Inga godkända utlägg att exportera.")
            st.subheader("Din historik")
            hist = [u for u in st.session_state["godkanda_utlagg"] if u.get("attesterat_av") == aktiv]
            if hist: st.dataframe(pd.DataFrame(hist)[["datum_attesterat", "namn", "lag", "kategori", "belopp"]])

elif sida == "⚙️ Adminpanel":
    st.title("⚙️ Adminpanel")
    st.subheader("Hantering av Lag & Aktiviteter")
    st.write(", ".join(st.session_state["lag"]))
    nl = st.text_input("Lägg till lag/aktivitet:", key="admin_lag")
    if st.button("Spara nytt val", key="as_lag"):
        if nl and nl not in st.session_state["lag"]: st.session_state["lag"].append(nl.strip()); spara_data(); st.rerun()
    st.divider()
    st.subheader("Hantering av Bokföringskonton")
    st.write(", ".join(st.session_state["konton"]))
    nk = st.text_input("Lägg till kontonamn:", key="admin_konto")
    if st.button("Spara nytt konto", key="as_konto"):
        if nk and nk not in st.session_state["konton"]: st.session_state["konton"].append(nk.strip()); spara_data(); st.rerun()
    st.divider()
    st.subheader("Hantera Attestanter & Behörigheter")
    an = st.text_input("Namn på attestant:", key="an_namn", value=st.session_state["an_namn"])
    ae = st.text_input("E-post till attestant:", key="an_mail", value=st.session_state["an_mail"])
    al = st.multiselect("Välj lag/aktiviteter:", options=st.session_state["lag"], key="an_lag_widget", default=st.session_state["an_lag"])
    if st.button("Spara attestant", key="as_att"):
        if an and ae and al:
            st.session_state["attestanter"] = [a for a in st.session_state["attestanter"] if a["namn"].lower() != an.strip().lower()]
            st.session_state["attestanter"].append({"namn": an.strip(), "epost": ae.strip(), "lag": al})
            st.session_state["an_namn"], st.session_state["an_mail"], st.session_state["an_lag"] = "", "", []
            spara_data(); st.rerun()
    if st.session_state["attestanter"]:
        st.write("### Registrerade attestanter:")
        for i, att in enumerate(st.session_state["attestanter"]):
            c_txt, c_ed, c_del = st.columns()
            c_txt.write(f"👤 **{att['namn']}** ({att['epost']}) - {', '.join(att['lag'])}")
            if c_ed.button("✏️", key=f"ed_{i}"):
                st.session_state["an_namn"], st.session_state["an_mail"], st.session_state["an_lag"] = att["namn"], att["epost"], att["lag"]
                st.rerun()
            if c_del.button("🗑️", key=f"del_{i}"):
                st.session_state["attestanter"].remove(att)
                spara_data(); st.rerun()
