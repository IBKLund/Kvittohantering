import streamlit as st
import pandas as pd
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

st.set_page_config(page_title="IBK Lund - Kvittohantering", layout="wide")
DATA_FILE = "admin_data.json"

MAIL_AVSANDARE = "kvitto@ibklund.se"
MAIL_LOSENORD = "uzierddeiefbongh"  
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

DEFAULT_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2", "LundaLägret", "NovaOpen"]
DEFAULT_KONTON = ["5800 Biljetter (tåg/buss/flyg/båt)", "5830 Kost", "5831 Logi", "7330 Bilersättning", "2999 Övrigt"]
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

if "minne_namn" not in st.session_state: st.session_state["minne_namn"] = ""
if "minne_bank" not in st.session_state: st.session_state["minne_bank"] = ""
if "minne_clearing" not in st.session_state: st.session_state["minne_clearing"] = ""
if "minne_konto" not in st.session_state: st.session_state["minne_konto"] = ""
if "bekraftelse_meddelande" not in st.session_state: st.session_state["bekraftelse_meddelande"] = ""

def skicka_notis_mail(till, namn, lag, belopp, kat, av):
    msg = MIMEMultipart()
    msg["From"], msg["To"], msg["Subject"] = MAIL_AVSANDARE, till, f"Nytt utlägg att attestera - {lag}"
    text = f"Hej {namn},\n\nEtt nytt utlägg har registrerats av {av} för {lag}.\n• Kategori: {kat}\n• Belopp: {belopp} kr\n\nLogga in för att hantera ärendet."
    msg.attach(MIMEText(text, "plain", "utf-8"))
    try:
        s = smtplib.SMTP(MAIL_SMTP_SERVER, MAIL_PORT)
        s.starttls()
        s.login(MAIL_AVSANDARE, MAIL_LOSENORD)
        s.sendmail(MAIL_AVSANDARE, till, msg.as_string())
        s.quit()
        return True
    except: return False

st.sidebar.title("IBK Lund")
sida = st.sidebar.radio("Välj funktion:", ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"])

# =========================================================================
# MENY 1: REGISTRERA UTLÄGG
# =========================================================================
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
                st.session_state["minne_namn"] = namn_reg.strip()
                st.session_state["minne_bank"] = bank_reg.strip()
                st.session_state["minne_clearing"] = clearing_reg.strip()
                st.session_state["minne_konto"] = konto_nr_reg.strip()
                utl = {"id": len(st.session_state["vantande_utlagg"]) + len(st.session_state["godkanda_utlagg"]) + 1, "namn": namn_reg.strip(), "lag": lag_reg, "kategori": konto_reg, "belopp": belopp_reg, "bank": bank_reg.strip(), "clearing": clearing_reg.strip(), "kontonummer": konto_nr_reg.strip(), "filnamn": fil_reg.name if fil_reg else "Inget underlag", "datum_inskickat": datetime.now().strftime("%Y-%m-%d")}
                st.session_state["vantande_utlagg"].append(utl)
                spara_data()
                att_namn = []
                for a in st.session_state["attestanter"]:
                    if lag_reg in a.get("lag", []):
                        att_namn.append(a["namn"])
                        skicka_notis_mail(a["epost"], a["namn"], lag_reg, belopp_reg, konto_reg, namn_reg)
                st.session_state["bekraftelse_meddelande"] = f"✅ Utlägget har registrerats och väntar på attestering av {' & '.join(att_namn)}!" if att_namn else f"✅ Utlägget registrerat! (Ingen attestant kopplad till {lag_reg})."
                st.rerun()
            else: st.error("Du måste fylla i alla bank- och namnuppgifter.")

# =========================================================================
# MENY 2: ATTESTFUNKTION
# =========================================================================
elif sida == "✅ Attestfunktion":
    st.title("✅ Attestfunktion")
    att_namn = [a["namn"] for a in st.session_state["attestanter"]]
    if not att_namn: st.warning("🔒 Inga godkända attestanter finns i systemet ännu.")
    else:
        aktiv = st.selectbox("Välj ditt namn:", options=["-- Välj namn --"] + att_namn)
        if aktiv != "-- Välj namn --":
            match = next(a for a in st.session_state["attestanter"] if a["namn"] == aktiv)
            st.success(f"Inloggad: {aktiv}. Behörig för: {', '.join(match['lag'])}")
            for u in list(st.session_state["vantande_utlagg"]):
                if u["lag"] in match["lag"]:
                    with st.container(border=True):
                        st.write(f"**Från:** {u['namn']} | **Val:** {u['lag']} | **Bank:** {u['bank']} {u['clearing']}-{u['kontonummer']} | **Fil:** {u['filnamn']}")
                        nk = st.selectbox(f"Konto för #{u['id']}:", options=st.session_state["konton"], index=st.session_state["konton"].index(u["kategori"]) if u["kategori"] in st.session_state["konton"] else 0, key=f"k_{u['id']}")
                        nb = st.number_input(f"Belopp för #{u['id']}:", value=float(u["belopp"]), key=f"b_{u['id']}")
                        if st.button(f"Godkänn #{u['id']}", type="primary", key=f"g_{u['id']}"):
                            u["kategori"], u["belopp"], u["attesterat_av"], u["datum_attesterat"] = nk, nb, aktiv, datetime.now().strftime("%Y-%m-%d")
                            st.session_state["godkanda_utlagg"].append(u); st.session_state["vantande_utlagg"].remove(u); spara_data(); st.rerun()
                        if st.button(f"Radera #{u['id']}", key=f"r_{u['id']}"):
                            st.session_state["vantande_utlagg"].remove(u); spara_data(); st.rerun()
            st.subheader("Export till Spiris")
            df = pd.DataFrame([u for u in st.session_state["godkanda_utlagg"] if u["lag"] in match["lag"]])
            if not df.empty:
                cols = ["namn", "lag", "kategori", "belopp", "bank", "clearing", "kontonummer", "datum_attesterat"]
                st.dataframe(df[cols])
                st.download_button("📥 Ladda ner CSV för Spiris", data=df[cols].to_csv(index=False, encoding="utf-8-sig"), file_name=f"spiris_{aktiv}.csv", mime="text/csv")
            else: st.info("Inga godkända utlägg finns att exportera.")
            st.subheader("Din historik")
            hist = [u for u in st.session_state["godkanda_utlagg"] if u.get("attesterat_av") == aktiv]
            if hist: st.dataframe(pd.DataFrame(hist)[["datum_attesterat", "namn", "lag", "kategori", "belopp"]])
            else: st.caption("Du har inte attesterat några kvitton än.")

# =========================================================================
# MENY 3: ADMINPANEL
# =========================================================================
elif sida == "⚙️ Adminpanel":
    st.title("⚙️ Adminpanel")
    st.write("Här administrerar du föreningens register över lag, konton och vem som attesterar.")
    st.divider()
    
    st.subheader("Hantering av Lag & Aktiviteter")
    st.write("**Befintliga val:** " + ", ".join(st.session_state["lag"]))
    nl = st.text_input("Lägg till lag/aktivitet:", key="admin_lag")
    if st.button("Spara nytt val", key="as_lag"):
        if nl and nl not in st.session_state["lag"]: st.session_state["lag"].append(nl.strip()); spara_data(); st.rerun()
            
    st.divider()
    st.subheader("Hantering av Bokföringskonton")
    st.write("**Befintliga konton:** " + ", ".join(st.session_state["konton"]))
    nk = st.text_input("Lägg till kontonamn:", key="admin_konto")
    if st.button("Spara nytt konto", key="as_konto"):
        if nk and nk not in st.session_state["konton"]: st.session_state["konton"].append(nk.strip()); spara_data(); st.rerun()
            
    st.divider()
    st.subheader("Hantera Attestanter & Behörigheter")
    an = st.text_input("Namn på attestant:", key="an_namn")
    ae = st.text_input("E-post till attestant:", key="an_mail")
    al = st.multiselect("Välj lag/aktiviteter:", options=st.session_state["lag"], key="an_lag")
    if st.button("Spara attestant", key="as_att"):
        if an and ae and al: st.session_state["attestanter"].append({"namn": an.strip(), "epost": ae.strip(), "lag": al})
    spara_data(); st.success("Attestant sparad!"); st.rerun()
    if st.session_state["attestanter"]: st.write("### Registrerade attestanter just nu:")
        for i, att in enumerate(st.session_state["attestanter"]):
    st.write(f"👤 {att['namn']} ({att['epost']}) - Ansvarar för: {', '.join(att['lag'])}")
    if st.button(f"Ta bort {att['namn']}", key=f"ad_del_{i}"):
    st.session_state["attestanter"].remove(att)
    spara_data(); st.rerun()
