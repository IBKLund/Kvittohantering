import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st
from datetime import datetime

# =========================================================================
# 1. GLOBAL KONFIGURATION & DATABAS
# =========================================================================
DATA_FILE = "admin_data.json"

MAIL_AVSANDARE = "kvitto@ibklund.se"  # <-- Din Workspace-mail
MAIL_LOSENORD = "lquelydfygnvizqv"     # <-- Ditt 16-siffriga Applösenord
MAIL_SMTP_SERVER = "://gmail.com"     # <-- Korrekt Gmail SMTP
MAIL_PORT = 587

# Initiala standardvärden om filen inte finns eller är tom
DEFAULT_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]
DEFAULT_KONTON = [
    "5800 Biljetter (tåg/buss/flyg/båt)",
    "5830 Kost",
    "5831 Logi",
    "7330 Bilersättning",
    "2999 Övrigt"
]

def ladda_system_data():
    default_data = {
        "lag": DEFAULT_LAG,
        "konton": DEFAULT_KONTON,
        "attestanter": [],       # VIKTIG: Denna saknades i ert gamla system
        "vantande_utlagg": [],
        "godkanda_utlagg": []
    }
    
    # Om filen inte finns alls, skapa den med standardvärden
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # AGGRESSIV FELSÄKRING: Om något av dessa fält saknas (eller är felaktigt), 
        # tvingar vi in en tom lista eller standardvärden istället för att krascha fliken.
        if "lag" not in data or not data["lag"]: data["lag"] = DEFAULT_LAG
        if "konton" not in data or not data["konton"]: data["konton"] = DEFAULT_KONTON
        if "attestanter" not in data or not isinstance(data["attestanter"], list): data["attestanter"] = []
        if "vantande_utlagg" not in data: data["vantande_utlagg"] = []
        if "godkanda_utlagg" not in data: data["godkanda_utlagg"] = []
            
        return data
    except Exception as e:
        # Om filen är korrupt eller låst av molnet, returnera standarddatan direkt
        return default_data

def spara_system_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def skicka_notis_mail(till_epost, attestant_namn, lag_namn, belopp, kategori, inskickat_av):
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

# Läs in och reparera datan omedelbart
nu_data = ladda_system_data()

# Sidans titel och layout
st.set_page_config(page_title="Föreningens Kvittohantering", layout="wide")

flik_registrera, flik_attestera, flik_admin = st.tabs([
    "📝 Registrera Utlägg", 
    "✅ Attestfunktion", 
    "⚙️ Adminpanel"
])

# -------------------------------------------------------------------------
# FLIK 1: REGISTRERA UTLÄGG
# -------------------------------------------------------------------------
with flik_registrera:
    st.title("📝 Registrera nytt utlägg")
    
    st.info(
        "ℹ️ **Utbetalningsinformation:**\n"
        "* Utbetalning sker runt den **25:e varje månad**.\n"
        "* Kvitton som inkommer **efter den 10:e** utbetalas nästa månad."
    )

    if "uploader_id" not in st.session_state:
        st.session_state.uploader_id = 100

    with st.form("huvud_reg_form", clear_on_submit=True):
        namn_reg = st.text_input("Ditt Namn (Obligatoriskt):", placeholder="t.ex. Johan Larsson")
        lag_reg = st.selectbox("Välj lag/avdelning:", options=nu_data["lag"])
        konto_reg = st.selectbox("Välj kategori/konto för kvittot:", options=nu_data["konton"])
        belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0, value=0.0)
        
        st.subheader("Bankuppgifter för utbetalning")
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            bank_reg = st.text_input("Bankens namn:", placeholder="e.g. Swedbank")
        with col_b2:
            clearing_reg = st.text_input("Clearingnummer:")
        with col_b3:
            konto_nr_reg = st.text_input("Kontonummer:")

        fil_reg = st.file_uploader(
            "Ladda upp kvitto eller underlag (PDF, PNG, JPG) *", 
            type=["pdf", "png", "jpg", "jpeg"],
            key=f"file_up_{st.session_state.uploader_id}"
        )
        
        skicka_reg_btn = st.form_submit_button("Skicka in utlägg", type="primary")

        if skicka_reg_btn:
            if not namn_reg.strip():
                st.error("❌ Du måste fylla i ditt namn!")
            elif belopp_reg <= 0:
                st.warning("⚠️ Beloppet måste vara högre än 0 kr.")
            elif not (bank_reg and clearing_reg and konto_nr_reg):
                st.error("❌ Du måste fylla i kompletta bankuppgifter för utbetalning!")
            elif not fil_reg:
                st.error("❌ Du måste bifoga en kvittofil!")
            else:
                nytt_utlagg = {
                    "id": len(nu_data["vantande_utlagg"]) + len(nu_data["godkanda_utlagg"]) + 1,
                    "namn": namn_reg.strip(),
                    "lag": lag_reg,
                    "kategori": konto_reg,
                    "belopp": belopp_reg,
                    "bank": bank_reg.strip(),
                    "clearing": clearing_reg.strip(),
                    "kontonummer": konto_nr_reg.strip(),
                    "filnamn": fil_reg.name,
                    "datum_inskickat": datetime.now().strftime("%Y-%m-%d")
                }
                
                nu_data["vantande_utlagg"].append(nytt_utlagg)
                spara_system_data(nu_data)
                
                mailade = []
                for att in nu_data["attestanter"]:
                    if lag_reg in att.get("lag", []):
                        if skicka_notis_mail(att["epost"], att["namn"], lag_reg, belopp_reg, konto_reg, namn_reg.strip()):
                            mailade.append(att["namn"])
                
                st.success(f"✅ Utlägget på {belopp_reg} kr har registrerats!")
                if mailade:
                    st.info(f"📧 Mailnotis har skickats till lagets attestant(er): {', '.join(mailade)}")
                
                st.session_state.uploader_id += 1
                st.rerun()

# -------------------------------------------------------------------------
# FLIK 2: ATTESTFUNKTION
# -------------------------------------------------------------------------
with flik_attestera:
    st.title("✅ Attestfunktion")
    
    st.subheader("Vem är du?")
    attestant_namn_lista = [a["namn"] for a in nu_data["attestanter"]]
    
    if not attestant_namn_lista:
        st.warning("⚠️ Inga attestanter är upplagda ännu. Lägg till en under Adminpanelen.")
    else:
        aktiv_attestant_namn = st.selectbox("Välj ditt namn för att se dina ärenden:", options=attestant_namn_lista)
        aktiv_attestant = next(a for a in nu_data["attestanter"] if a["namn"] == aktiv_attestant_namn)
        mina_lag = aktiv_attestant.get("lag", [])
        
        st.write(f"Du har behörighet för följande lag: **{', '.join(mina_lag)}**")
        st.divider()

        aktuell_ko = [u for u in nu_data["vantande_utlagg"] if u["lag"] in mina_lag]
        
        st.subheader("Ärenden som väntar på ditt godkännande")
        if not aktuell_ko:
            st.info("📥 Inga väntande utlägg för dina lag just nu.")
        else:
            for idx, utl in enumerate(aktuell_ko):
                with st.container(border=True):
                    col_l, col_r = st.columns(2)
                    
                    with col_l:
                        st.write(f"**Inskickat av:** {utl['namn']} ({utl.get('datum_inskickat', 'Okänt datum')})")
                        st.write(f"**Lag:** {utl['lag']}")
                        st.caption(f"📄 *Filunderlag: {utl['filnamn']}*")
                        st.write(f"**Bank:** {utl['bank']} | **Clearing:** {utl['clearing']} | **Konto:** {utl['kontonummer']}")
                    
                    with col_r:
                        nytt_konto = st.selectbox(
                            f"Konto (Korrigera om felaktigt):", 
                            options=nu_data["konton"], 
                            index=nu_data["konton"].index(utl["kategori"]) if utl["kategori"] in nu_data["konton"] else 0,
                            key=f"konto_{utl['id']}"
                        )
                        nytt_belopp = st.number_input(
                            f"Belopp (kr) (Korrigera om felaktigt):", 
                            value=float(utl["belopp"]), 
                            key=f"belopp_{utl['id']}"
                        )
                        
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            if st.button("✅ Godkänn & Attestera", key=f"godkand_{utl['id']}", type="primary"):
                                utl["kategori"] = nytt_konto
                                utl["belopp"] = nytt_belopp
                                utl["attesterat_av"] = aktiv_attestant_namn
                                utl["datum_attesterat"] = datetime.now().strftime("%Y-%m-%d")
                                
