import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# MÅSTE ligga absolut först
st.set_page_config(page_title="IBK Lund - Kvittohantering", layout="wide")

# =========================================================================
# LÖSENORD OCH INSTÄLLNINGAR
# =========================================================================
ADMIN_LOSENORD = "IBKLund2022!"  # <-- Ditt adminlösenord
DATA_FILE = "admin_data.json"

MAIL_AVSANDARE = "kvitto@ibklund.se"
MAIL_LOSENORD = "uzierddeiefbongh"  
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

DEFAULT_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2", "LundaLägret", "NovaOpen"]

DEFAULT_KONTON = [
    "5800 Biljetter (tåg/buss/flyg/båt)",
    "5830 Kost",
    "5831 Logi",
    "7330 Bilersättning",
    "2999 Övrigt"
]

DEFAULT_ATTESTANTER = [
    {"namn": "Christer Sölve", "epost": "christer@solve.se", "lag": ["Herr Elit"]},
    {"namn": "Magnus Berglund", "epost": "magnus.berglund@ibklund.se", "lag": ["LundaLägret", "NovaOpen"]}
]

# =========================================================================
# PERMANENT FILHANTERING (MOLNSÄKER)
# =========================================================================
def ladda_data():
    default_struktur = {
        "lag": DEFAULT_LAG.copy(),
        "konton": DEFAULT_KONTON.copy(),
        "attestanter": DEFAULT_ATTESTANTER.copy(),
        "vantande_utlagg": [],
        "godkanda_utlagg": []
    }
    if not os.path.exists(DATA_FILE):
        return default_struktur
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in default_struktur.items():
            if k not in data or not isinstance(data[k], type(v)):
                data[k] = v
        if not data["attestanter"]:
            data["attestanter"] = DEFAULT_ATTESTANTER.copy()
        return data
    except:
        return default_struktur

def spara_data():
    try:
        temp_data = {
            "lag": st.session_state["lag"],
            "konton": st.session_state["konton"],
            "attestanter": st.session_state["attestanter"],
            "vantande_utlagg": st.session_state["vantande_utlagg"],
            "godkanda_utlagg": st.session_state["godkanda_utlagg"]
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(temp_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass

# Läs in data till session_state en gång per körning
if "lag" not in st.session_state or not st.session_state["attestanter"]:
    sparad_data = ladda_data()
    for nyckel, varde in sparad_data.items():
        st.session_state[nyckel] = varde
    spara_data()

# Hantera admin-inloggningstillstånd
if "admin_inloggad" not in st.session_state:
    st.session_state["admin_inloggad"] = False

def skicka_notis_mail(till_epost, attestant_namn, lag_namn, belopp, kategori, inskickat_av):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"
    text = f"Hej {attestant_namn},\n\nEtt nytt utlägg har registrerats av {inskickat_av} för {lag_namn} och väntar på din attest.\n\n• Kategori/Konto: {kategori}\n• Belopp: {belopp} kr\n\nLogga in i appen för att hantera ärendet."
    msg.attach(MIMEText(text, "plain", "utf-8"))
    try:
        server = smtplib.SMTP(MAIL_SMTP_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_AVSANDARE, MAIL_LOSENORD)
        server.sendmail(MAIL_AVSANDARE, till_epost, msg.as_string())
        server.quit()
        return True
    except:
        return False

# =========================================================================
# SIDOMENY OCH INLOGGNINGSKONTROLL
# =========================================================================
st.sidebar.title("IBK Lund")
st.sidebar.subheader("Kvitto & Utlägg")
sida = st.sidebar.radio("Välj funktion:", ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"])

# Om användaren klickar på Adminpanelen, visa ett inloggningsformulär med knapp i sidebar
if sida == "⚙️ Adminpanel":
    st.sidebar.markdown("---")
    if not st.session_state["admin_inloggad"]:
        pwd_input = st.sidebar.text_input("Admin lösenord:", type="password")
        if st.sidebar.button("🔓 Logga in som Admin"):
            if pwd_input == ADMIN_LOSENORD:
                st.session_state["admin_inloggad"] = True
                st.rerun()
            else:
                st.sidebar.error("Felaktigt lösenord!")
    else:
        if st.sidebar.button("🔒 Logga ut"):
            st.session_state["admin_inloggad"] = False
            st.rerun()

# =========================================================================
# MENY 1: REGISTRERA UTLÄGG
# =========================================================================
if sida == "📝 Registrera Utlägg":
    st.title("📝 Registrera nytt utlägg")
    st.info("ℹ️ Utbetalning sker runt den 25:e varje månad. Kvitton efter den 10:e utbetalas nästa månad.")
    
    namn_reg = st.text_input("Ditt Namn:")
    lag_reg = st.selectbox("Välj lag / aktivitet:", options=st.session_state["lag"])
    konto_reg = st.selectbox("Välj konto:", options=st.session_state["konton"])
    belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0)
    
    st.subheader("Bankuppgifter för utbetalning")
    bank_reg = st.text_input("Bank:")
    clearing_reg = st.text_input("Clearingnummer:")
    konto_nr_reg = st.text_input("Kontonummer:")
    
    fil_reg = st.file_uploader("Ladda upp kvitto (Bild eller PDF)", type=["pdf", "png", "jpg", "jpeg"])
    
    if st.button("Skicka in utlägg", type="primary"):
        if namn_reg and bank_reg and clearing_reg and konto_nr_reg:
            nytt_utlagg = {
                "id": len(st.session_state["vantande_utlagg"]) + len(st.session_state["godkanda_utlagg"]) + 1,
                "namn": namn_reg,
                "lag": lag_reg,
                "kategori": konto_reg,
                "belopp": belopp_reg,
                "bank": bank_reg,
                "clearing": clearing_reg,
                "kontonummer": konto_nr_reg,
                "filnamn": fil_reg.name if fil_reg else "Inget underlag",
                "datum_inskickat": datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state["vantande_utlagg"].append(nytt_utlagg)
            spara_data()
            
            mailade = []
            for att in st.session_state["attestanter"]:
                if lag_reg in att.get("lag", []):
                    if skicka_notis_mail(att["epost"], att["namn"], lag_reg, belopp_reg, konto_reg, namn_reg):
                        mailade.append(att["namn"])
                        
            st.success("✅ Utlägget har registrerats!")
            st.rerun()
        else:
            st.error("Du måste fylla i namn, bankuppgifter och belopp.")

# =========================================================================
# MENY 2: ATTESTFUNKTION
# =========================================================================
elif sida == "✅ Attestfunktion":
    st.title("✅ Attestfunktion")
    
    attestant_namn_lista = [a["namn"] for a in st.session_state["attestanter"]]
    if not attestant_namn_lista:
        st.warning("🔒 Inga godkända attestanter finns i systemet ännu. Be admin lägga till dig under Adminpanelen.")
    else:
        aktiv_attestant = st.selectbox("Välj ditt namn för att logga in i attestvyn:", options=["-- Välj namn --"] + attestant_namn_lista)
        
        if aktiv_attestant != "-- Välj namn --":
            match = next(a for a in st.session_state["attestanter"] if a["namn"] == aktiv_attestant)
            mina_lag = match["lag"]
            
            st.success(f"Inloggad som {aktiv_attestant}. Du har behörighet för: {', '.join(mina_lag)}")
            st.divider()
            
            st.subheader("Ärenden som väntar på ditt godkännande")
            aktuell_ko = [u for u in st.session_state["vantande_utlagg"] if u["lag"] in mina_lag]
            
            if not aktuell_ko:
                st.info("📥 Inga nya utlägg ligger i kön för dina lag/aktiviteter just nu.")
            else:
                for utl in list(st.session_state["vantande_utlagg"]):
                    if utl["lag"] in mina_lag:
                        with st.container(border=True):
                            st.write(f"**Inskickat av:** {utl['namn']} | **Lag/Aktivitet:** {utl['lag']}")
                            st.write(f"**Bank:** {utl['bank']} | **Clearing:** {utl['clearing']} | **Konto:** {utl['kontonummer']}")
                            
                            nytt_konto = st.selectbox(
                                f"Korrigera konto för #{utl['id']}:", 
                                options=st.session_state["konton"], 
                                index=st.session_state["konton"].index(utl["kategori"]) if utl["kategori"] in st.session_state["konton"] else 0,
                                key=f"k_{utl['id']}"
                            )
                            nytt_belopp = st.number_input(
                                f"Korrigera belopp för #{utl['id']}:", 
                                value=float(utl["belopp"]), 
                                key=f"b_{utl['id']}"
                            )
                            
                            if st.button(f"✅ Godkänn & Attestera #{utl['id']}", type="primary", key=f"g_{utl['id']}"):
                                utl["kategori"] = nytt_konto
                                utl["belopp"] = nytt_belopp
                                utl["attesterat_av"] = aktiv_attestant
                                utl["datum_attesterat"] = datetime.now().strftime("%Y-%m-%d")
                                st.session_state["godkanda_utlagg"].append(utl)
