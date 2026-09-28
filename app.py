import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st

# =========================================================================
# 1. INSTÄLLNINGAR FÖR BACKEND (Skriv in dina Workspace-uppgifter här!)
# =========================================================================
DATA_FILE = "admin_data.json"

MAIL_AVSANDARE = "kvitto@ibklund.se"  # <-- Din Workspace-mail
MAIL_LOSENORD = "lquelydfygnvizqv"           # <-- Ditt 16-siffriga Applösenord
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

STANDARD_KONTON = [
    "5800 Biljetter (tåg/buss/flyg/båt)",
    "5830 Kost",
    "5831 Logi",
    "7330 Bilersättning",
    "2999 Övrigt"
]
STANDARD_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]

def ladda_admin_data():
    if not os.path.exists(DATA_FILE):
        standard_data = {
            "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
            "lag": STANDARD_LAG,
            "konton": STANDARD_KONTON,
            "anvandare": [],
            "vantande_utlagg": [],
            "godkanda_utlagg": []
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(standard_data, f, ensure_ascii=False, indent=4)
        return standard_data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "godkanda_utlagg" not in data:
            data["godkanda_utlagg"] = []
        if "vantande_utlagg" not in data:
            data["vantande_utlagg"] = []
        if "anvandare" not in data:
            data["anvandare"] = []
        data["lag"] = STANDARD_LAG
        data["konton"] = STANDARD_KONTON
        return data

def spara_admin_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def skicka_attest_mail(till_epost, attestant_namn, lag_namn, belopp, kategori, inskickat_av):
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"

    text = f"Hej {attestant_namn},\n\nEtt nytt utlägg har registrerats av {inskickat_av} för {lag_namn} och väntar på din attest.\n\n• Kategori: {kategori}\n• Belopp: {belopp} kr\n\nLogga in i appen för att godkänna ärendet."

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

admin_data = ladda_admin_data()

# =========================================================================
# 2. SKAPA DE TRE FLIKARNA
# =========================================================================
flik_registrera, flik_attestera, flik_admin = st.tabs([
    "📝 Registrera Utlägg", 
    "✅ Attestfunktion", 
    "⚙️ Adminpanel"
])

# --- FLIK 1: REGISTRERA UTLÄGG ---
with flik_registrera:
    st.title("📝 Registrera nytt utlägg")
    st.write("Fyll i uppgifterna och ladda upp ditt kvitto.")

    # Tvinga uppladdaren att rensas via en sessionsräknare som ändras vid inskick
    if "uploader_cleaner" not in st.session_state:
        st.session_state.uploader_cleaner = 0

    # Vi lägger allt i ett formulär som rensar fälten helt vid godkänt inskick
    with st.form("registrera_utlagg_form", clear_on_submit=True):
        anv_namn_reg = st.text_input("Ditt Namn (Obligatoriskt):", placeholder="t.ex. Johan Larsson")

        aktuella_kategorier = list(admin_data.get("kategorier", []))
        if "Övrigt" in aktuella_kategorier:
            aktuella_kategorier.remove("Övrigt")
            aktuella_kategorier.sort()
            aktuella_kategorier.append("Övrigt")

        valt_lag = st.selectbox("Välj lag/avdelning:", options=admin_data.get("lag", []))
        vald_kategori = st.selectbox("Välj kategori:", options=aktuella_kategorier)
        belopp = st.number_input("Belopp (kr):", min_value=0.0, step=10.0)
        
        uppladdad_fil = st.file_uploader(
            "Ladda upp kvitto eller underlag (Obligatoriskt) *", 
            type=["pdf", "png", "jpg", "jpeg"],
            key=f"kvitto_file_{st.session_state.uploader_cleaner}"
        )

        skicka_knapp = st.form_submit_button("Skicka in utlägg", type="primary")

        if skicka_knapp:
            if not anv_namn_reg.strip():
                st.error("❌ Du måste fylla i ditt namn för att registrera utlägget!")
            elif not uppladdad_fil:
                st.error("❌ Du måste ladda upp ett kvitto eller underlag!")
            elif belopp <= 0:
                st.warning("⚠️ Vänligen ange ett belopp över 0 kr.")
            else:
                nytt_utlagg = {
                    "id": len(admin_data["vantande_utlagg"]) + 1,
                    "namn": anv_namn_reg.strip(),
                    "lag": valt_lag,
                    "kategori": vald_kategori,
                    "belopp": belopp,
                    "filnamn": uppladdad_fil.name
                }
                
                admin_data["vantande_utlagg"].append(nytt_utlagg)
                spara_admin_data(admin_data)
                
                # Skicka mailnotis live
                mail_skickat_till = []
                for anv in admin_data.get("anvandare", []):
                    if valt_lag in anv.get("lag", []):
                        if skicka_attest_mail(anv["epost"], anv["namn"], valt_lag, belopp, vald_kategori, anv_namn_reg):
                            mail_skickat_till.append(anv["namn"])

                st.success(f"✅ Utlägget på {belopp} kr för {valt_lag} har skickats till kö!")
                if mail_skickat_till:
                    st.info(f"📧 E-postnotis har skickats till ansvarig attestant: {', '.join(mail_skickat_till)}")
                
                # Ändra nyckeln för att tvinga filuppladdaren att tömmas
                st.session_state.uploader_cleaner += 1
                st.rerun()

# --- FLIK 2: ATTESTFUNKTION ---
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Granska inskickade underlag live och tilldela bokföringskonto.")
    st.divider()

    st.subheader("Ärenden som väntar på godkännande")
    vantande = admin_data.get("vantande_utlagg", [])
    
    if len(vantande) == 0:
        st.info("📥 Inga nya utlägg ligger i kön just nu.")
    else:
        for index, utl in enumerate(vantande):
            with st.container(border=True):
                col_info, col_konto = st.columns(2)
                
                with col_info:
                    st.write(f"**Inskickat av:** {utl['namn']}")
                    st.write(f"**Lag:** {utl['lag']}")
                    st.write(f"**Kategori:** {utl['kategori']}")
                    st.write(f"**Belopp:** {utl['belopp']:,.2f} kr")
                    st.caption(f"📄 *{utl['filnamn']} (Bifogad)*")

                with col_konto:
                    # KOPPLING: Matchar vald kategori mot rätt bokföringskonto automatiskt
                    forval_index = 0
                    for k_idx, konto_namn in enumerate(admin_data.get("konton", [])):
                        if utl['kategori'].lower() in konto_namn.lower():
                            forval_index = k_idx
                            break
                    
                    valt_konto_attest = st.selectbox(
                        "Välj/Ändra bokföringskonto:", 
                        options=admin_data.get("konton", []), 
                        index=forval_index,
                        key=f"attest_konto_{index}"
                    )

                col_btn1, col_btn2, _ = st.columns(3)
                with col_btn1:
                    if st.button("👍 Godkänn", key=f"godkand_{index}", type="primary"):
                        nytt_godkant = {
                            "Inskickat av": utl["namn"],
                            "Lag": utl["lag"],
                            "Kategori": utl["kategori"],
                            "Belopp (kr)": utl["belopp"],
                            "Bokföringskonto": valt_konto_attest,
                            "Kvittofil": utl["filnamn"]
                        }
                        admin_data["godkanda_utlagg"].append(nytt_godkant)
                        admin_data["vantande_utlagg"].pop(index)
                        spara_admin_data(admin_data)
                        st.success("Utlägget godkänt!")
                        st.rerun()

                with col_btn2:
                    if st.button("👎 Neka", key=f"neka_{index}"):
                        admin_data["vantande_utlagg"].pop(index)
                        spara_admin_data(admin_data)
                        st.warning("Utlägget nekades.")
                        st.rerun()

    st.divider()
    st.subheader("📦 Exportera godkända utlägg")
    godkanda = admin_data.get("godkanda_utlagg", [])
    
    if godkanda:
        st.write(f"Det finns **{len(godkanda)}** godkända utlägg i historiken.")
        df = pd.DataFrame(godkanda)
        st.dataframe(df, use_container_width=True)
        
        st.write("**Rensa i historiken innan export:**")
        rader_att_valja = [f"{i}: {x['Inskickat av']} - {x['Belopp (kr)']} kr ({x['Lag']})" for i, x in enumerate(godkanda)]
        rad_att_radera = st.selectbox("Välj utlägg att städa bort:", options=["---"] + rader_att_valja)
        
        if st.button("🗑️ Ta bort valt utlägg från listan") and rad_att_radera != "---":
            index_att_radera = int(rad_att_radera.split(":"))
            admin_data["godkanda_utlagg"].pop(index_att_radera)
            spara_admin_data(admin_data)
            st.success("Utlägget raderades från exportlistan!")
            st.rerun()

