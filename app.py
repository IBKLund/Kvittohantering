import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st

# =========================================================================
# 1. GLOBAL KONFIGURATION (Ändra dina Workspace-uppgifter här!)
# =========================================================================
DATA_FILE = "admin_data.json"

MAIL_AVSANDARE = "kvitto@ibklund.se"  # <-- Din Workspace-mail
MAIL_LOSENORD = "lquelydfygnvizqv"           # <-- Ditt 16-siffriga Applösenord
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

# Systemets låsta grunddata enligt dina instruktioner
STANDARD_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]
STANDARD_KONTON = [
    "5800 Biljetter (tåg/buss/flyg/båt)",
    "5830 Kost",
    "5831 Logi",
    "7330 Bilersättning",
    "2999 Övrigt"
]

# =========================================================================
# 2. STORM-SÄKRAD DATAHANTERING (DIREKT MOT FIL)
# =========================================================================
def ladda_data():
    """Läser in data direkt från fil. Reparerar automatiskt vid fel eller tom fil."""
    default_structure = {
        "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
        "lag": STANDARD_LAG,
        "konton": STANDARD_KONTON,
        "anvandare": [],
        "vantande_utlagg": [],
        "godkanda_utlagg": []
    }
    
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_structure, f, ensure_ascii=False, indent=4)
        return default_structure

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Säkerställ att inga nycklar eller listor saknas
        if not data or not isinstance(data, dict): data = default_structure
        if "kategorier" not in data or not data["kategorier"]: data["kategorier"] = default_structure["kategorier"]
        if "anvandare" not in data: data["anvandare"] = []
        if "vantande_utlagg" not in data: data["vantande_utlagg"] = []
        if "godkanda_utlagg" not in data: data["godkanda_utlagg"] = []
        
        # Tvinga alltid dina exakta lag och konton
        data["lag"] = STANDARD_LAG
        data["konton"] = STANDARD_KONTON
        return data
    except:
        # Om filen är korrupt på disk, rädda appen genom att skriva över med standard
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_structure, f, ensure_ascii=False, indent=4)
        return default_structure

def spara_data(data):
    """Skriver data direkt till filen i realtid."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def skicka_mail(till_epost, attestant_namn, lag_namn, belopp, kategori, inskickat_av):
    """Skickar automatisk e-postnotis via SMTP."""
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"
    
    body = (
        f"Hej {attestant_namn},\n\n"
        f"Ett nytt utlägg har registrerats av {inskickat_av} för {lag_namn} och väntar på din attest.\n\n"
        f"• Kategori: {kategori}\n"
        f"• Belopp: {belopp} kr\n\n"
        f"Logga in i appen för att granska underlaget.\n\n"
        f"Med vänlig hälsning,\nEkonomisystemet"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))
    try:
        server = smtplib.SMTP(MAIL_SMTP_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_AVSANDARE, MAIL_LOSENORD)
        server.sendmail(MAIL_AVSANDARE, till_epost, msg.as_string())
        server.quit()
        return True
    except:
        return False

# Läs in dagsfärsk data direkt vid sidladdning
nuvarande_data = ladda_data()

# =========================================================================
# 3. GRÄNSSNITT MED DE TRE UNIKA FLIKARNA
# =========================================================================
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
    st.write("Fyll i uppgifterna och ladda upp ditt kvitto.")

    # Sessions-nyckel för att kunna tvinga filuppladdaren att tömmas vid inskick
    if "clean_uploader_trigger" not in st.session_state:
        st.session_state.clean_uploader_trigger = 0

    # clear_on_submit=True tömmer automatiskt alla text/nummerfält vid lyckat tryck
    with st.form("utlagg_form_huvud", clear_on_submit=True):
        namn_input = st.text_input("Ditt Namn (Obligatoriskt):", placeholder="t.ex. Johan Larsson")
        
        # Sortera kategorier snyggt (Övrigt sist)
        kat_lista = list(nuvarande_data["kategorier"])
        if "Övrigt" in kat_lista:
            kat_lista.remove("Övrigt")
            kat_lista.sort()
            kat_lista.append("Övrigt")
            
        lag_val = st.selectbox("Välj lag/avdelning:", options=nuvarande_data["lag"])
        kat_val = st.selectbox("Välj kategori:", options=kat_lista)
        belopp_val = st.number_input("Belopp (kr):", min_value=0.0, step=10.0, value=0.0)
        
        fil_val = st.file_uploader(
            "Ladda upp kvitto eller underlag (Obligatoriskt) *", 
            type=["pdf", "png", "jpg", "jpeg"],
            key=f"uploader_id_{st.session_state.clean_uploader_trigger}"
        )
        
        skicka_knapp = st.form_submit_button("Skicka in utlägg", type="primary")

        if skicka_knapp:
            if not namn_input.strip():
                st.error("❌ Du måste fylla i ditt namn!")
            elif not fil_val:
                st.error("❌ Du måste bifoga en kvittofil/underlag!")
            elif belopp_val <= 0:
                st.warning("⚠️ Beloppet måste vara högre än 0 kr.")
            else:
                # Bygg utläggsobjektet
                nytt_id = len(nuvarande_data["vantande_utlagg"]) + len(nuvarande_data["godkanda_utlagg"]) + 1
                utl_objekt = {
                    "id": nytt_id,
                    "namn": namn_input.strip(),
                    "lag": lag_val,
                    "kategori": kat_val,
                    "belopp": belopp_val,
                    "filnamn": fil_val.name
                }
                
                # Spara direkt till hårddisken
                nuvarande_data["vantande_utlagg"].append(utl_objekt)
                spara_data(nuvarande_data)
                
                # Sök efter kopplade attestanter och skicka mail live
                notifierade = []
                for a in nuvarande_data["anvandare"]:
                    if lag_val in a.get("lag", []):
                        if skicka_mail(a["epost"], a["namn"], lag_val, belopp_val, kat_val, namn_input.strip()):
                            notifierade.append(a["namn"])
                
                st.success(f"✅ Utlägget på {belopp_val} kr för {lag_val} har skickats till kön!")
                if notifierade:
                    st.info(f"📧 E-postnotis har skickats till: {', '.join(notifierade)}")
                
                # Tvinga filuppladdaren att nollställas vid nästa rendering
                st.session_state.clean_uploader_trigger += 1
                st.rerun()

# -------------------------------------------------------------------------
# FLIK 2: ATTESTFUNKTION
# -------------------------------------------------------------------------
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Granska inskickade underlag live och tilldela bokföringskonto.")
    st.divider()

    st.subheader("Ärenden som väntar på godkännande")
    kö_lista = nuvarande_data["vantande_utlagg"]
    
    if not kö_lista:
        st.info("📥 Inga nya utlägg ligger i kön just nu. Bra jobbat!")
    else:
        for idx, utl in enumerate(kö_lista):
            with st.container(border=True):
                col_vänster, col_höger = st.columns(2)
                
                with col_vänster:
                    st.write(f"**Inskickat av:** {utl['namn']}")
                    st.write(f"**Lag:** {utl['lag']}")
                    st.write(f"**Kategori:** {utl['kategori']}")
                    st.write(f"**Belopp:** {utl['belopp']:,.2f} kr")
                    st.caption(f"📄 *Fil: {utl['filnamn']}*")
                
                with col_höger:
                    # KOPPLING: Hittar automatiskt rätt konto baserat på utläggets valda kategori
                    konto_index = 0
                    for k_idx, k_namn in enumerate(nuvarande_data["konton"]):
                        if utl["kategori"].lower() in k_namn.lower():
                            konto_index = k_idx
                            break
                    
                    valt_konto = st.selectbox(
                        "Välj/Ändra bokföringskonto:",
                        options=nuvarande_data["konton"],
                        index=konto_index,
                        key=f"attest_select_{utl['id']}_{idx}"
                    )
                
                btn_col1, btn_col2, _ = st.columns(3)
                with btn_col1:
                    if st.button("👍 Godkänn", key=f"btn_godkand_{utl['id']}_{idx}", type="primary"):
                        godkänt_objekt = {
                            "Inskickat av": utl["namn"],
                            "Lag": utl["lag"],
                            "Kategori": utl["kategori"],
                            "Belopp (kr)": utl["belopp"],
                            "Bokföringskonto": valt_konto,
                            "Kvittofil": utl["filnamn"]
                        }
