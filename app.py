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

# Dina låsta lag och konton
STANDARD_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]
STANDARD_KONTON = [
    "5800 Biljetter (tåg/buss/flyg/båt)",
    "5830 Kost",
    "5831 Logi",
    "7330 Bilersättning",
    "2999 Övrigt"
]

# =========================================================================
# 2. STRÄNG DATAHANTERING (Tvingar ren och korrekt laddning)
# =========================================================================
def ladda_system_data():
    default_data = {
        "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
        "lag": STANDARD_LAG,
        "konton": STANDARD_KONTON,
        "anvandare": [],
        "vantande_utlagg": [],
        "godkanda_utlagg": []
    }
    
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Tvinga fram korrekta fält och listor om något saknas på disk
        if "anvandare" not in data or not isinstance(data["anvandare"], list): data["anvandare"] = []
        if "vantande_utlagg" not in data: data["vantande_utlagg"] = []
        if "godkanda_utlagg" not in data: data["godkanda_utlagg"] = []
        if "kategorier" not in data: data["kategorier"] = default_data["kategorier"]
        
        # Säkerställ dina låsta inställningar
        data["lag"] = STANDARD_LAG
        data["konton"] = STANDARD_KONTON
        return data
    except:
        # Om filen är låst eller korrupt, skriv över den direkt för att rädda appen
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
        return default_data

def spara_system_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def skicka_notis_mail(till_epost, attestant_namn, lag_namn, belopp, kategori, inskickat_av):
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"
    text = f"Hej {attestant_namn},\n\nEtt nytt utlägg har registrerats av {inskickat_av} för {lag_namn} och väntar på din attest.\n\n• Kategori: {kategori}\n• Belopp: {belopp} kr\n\nLogga in i appen för att hantera ärendet."
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

# Läs in och verifiera filen omedelbart
nu_data = ladda_system_data()

# =========================================================================
# 3. STRUKTUR FÖR FLIKARNA
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

    if "uploader_id" not in st.session_state:
        st.session_state.uploader_id = 100

    # Formulär med inbyggd rensning vid godkänt tryck
    with st.form("huvud_reg_form", clear_on_submit=True):
        namn_reg = st.text_input("Ditt Namn (Obligatoriskt):", placeholder="t.ex. Johan Larsson")
        
        kat_sorterad = list(nu_data["kategorier"])
        if "Övrigt" in kat_sorterad:
            kat_sorterad.remove("Övrigt")
            kat_sorterad.sort()
            kat_sorterad.append("Övrigt")
            
        lag_reg = st.selectbox("Välj lag/avdelning:", options=nu_data["lag"])
        kat_reg = st.selectbox("Välj kategori:", options=kat_sorterad)
        belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=10.0, value=0.0)
        
        fil_reg = st.file_uploader(
            "Ladda upp kvitto eller underlag (Obligatoriskt) *", 
            type=["pdf", "png", "jpg", "jpeg"],
            key=f"file_up_{st.session_state.uploader_id}"
        )
        
        skicka_reg_btn = st.form_submit_button("Skicka in utlägg", type="primary")

        if skicka_reg_btn:
            if not namn_reg.strip():
                st.error("❌ Du måste fylla i ditt namn!")
            elif not fil_reg:
                st.error("❌ Du måste bifoga en kvittofil!")
            elif belopp_reg <= 0:
                st.warning("⚠️ Beloppet måste vara högre än 0 kr.")
            else:
                nytt_utlagg = {
                    "id": len(nu_data["vantande_utlagg"]) + len(nu_data["godkanda_utlagg"]) + 1,
                    "namn": namn_reg.strip(),
                    "lag": lag_reg,
                    "kategori": kat_reg,
                    "belopp": belopp_reg,
                    "filnamn": fil_reg.name
                }
                
                nu_data["vantande_utlagg"].append(nytt_utlagg)
                spara_system_data(nu_data)
                
                mailade_personer = []
                for a in nu_data["anvandare"]:
                    if lag_reg in a.get("lag", []):
                        if skicka_notis_mail(a["epost"], a["namn"], lag_reg, belopp_reg, kat_reg, namn_reg.strip()):
                            mailade_personer.append(a["namn"])
                
                st.success(f"✅ Utlägget på {belopp_reg} kr för {lag_reg} har registrerats!")
                if mailade_personer:
                    st.info(f"📧 Mailnotis har skickats till: {', '.join(mailade_personer)}")
                
                st.session_state.uploader_id += 1
                st.rerun()

# -------------------------------------------------------------------------
# FLIK 2: ATTESTFUNKTION
# -------------------------------------------------------------------------
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Granska inskickade underlag live och tilldela bokföringskonto.")
    st.divider()

    st.subheader("Ärenden som väntar på godkännande")
    aktuell_ko = nu_data["vantande_utlagg"]
    
    if not aktuell_ko:
        st.info("📥 Inga nya utlägg ligger i kön just nu.")
    else:
        for i, utl in enumerate(aktuell_ko):
            with st.container(border=True):
                col_l, col_r = st.columns(2)
                
                with col_l:
                    st.write(f"**Inskickat av:** {utl['namn']}")
                    st.write(f"**Lag:** {utl['lag']}")
                    st.write(f"**Kategori:** {utl['kategori']}")
                    st.write(f"**Belopp:** {utl['belopp']:,.2f} kr")
                    st.caption(f"📄 *Filunderlag: {utl['filnamn']}*")
                
                with col_r:
                    # KOPPLING: Matchar automatiskt kategori till rätt bokföringskonto
                    k_index = 0
                    for check_idx, k_text in enumerate(nu_data["konton"]):
                        if utl["kategori"].lower() in k_text.lower():
                            k_index = check_idx
                            break
                    
                    valt_konto = st.selectbox(
                        "Bokföringskonto (Förvalt baserat på kategori):",
                        options=nu_data["konton"],
                        index=k_index,
                        key=f"attest_box_{utl['id']}_{i}"
                    )
                
                b1, b2, _ = st.columns(3)
                with b1:
                    if st.button("👍 Godkänn", key=f"ok_btn_{utl['id']}_{i}", type="primary"):
                        godkant_post = {
                            "Inskickat av": utl["namn"],
                            "Lag": utl["lag"],
                            "Kategori": utl["kategori"],
                            "Belopp (kr)": utl["belopp"],
                            "Bokföringskonto": valt_konto,
                            "Kvittofil": utl["filnamn"]
                        }
                        nu_data["godkanda_utlagg"].append(godkant_post)
                        nu_data["vantande_utlagg"].pop(i)
                        spara_system_data(nu_data)
                        st.success("Godkänt!")
                        st.rerun()
                with b2:
                    if st.button("👎 Neka", key=f"nok_btn_{utl['id']}_{i}"):
                        nu_data["vantande_utlagg"].pop(i)
                        spara_system_data(nu_data)
                        st.warning("Nekat.")
                        st.rerun()

    # --- HISTORIK & EXPORT ---
    st.divider()
    st.subheader("📦 Exportera godkända utlägg")
    list_godkand = nu_data["godkanda_utlagg"]
    
    if list_godkand:
        df_export = pd.DataFrame(list_godkand)
        st.dataframe(df_export, use_container_width=True)
        
        st.write("**Rensa i historiken innan export:**")
