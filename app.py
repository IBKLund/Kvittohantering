import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# MÅSTE ligga absolut först i filen
st.set_page_config(page_title="Föreningens Kvittohantering", layout="wide")

# =========================================================================
# INITIERA SESSIONS-MINNET (MOLNSÄKERT)
# =========================================================================
if "lag" not in st.session_state:
    st.session_state["lag"] = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]

if "konton" not in st.session_state:
    st.session_state["konton"] = [
        "5800 Biljetter (tåg/buss/flyg/båt)",
        "5830 Kost",
        "5831 Logi",
        "7330 Bilersättning",
        "2999 Övrigt"
    ]

if "attestanter" not in st.session_state:
    st.session_state["attestanter"] = []

if "vantande_utlagg" not in st.session_state:
    st.session_state["vantande_utlagg"] = []

if "godkanda_utlagg" not in st.session_state:
    st.session_state["godkanda_utlagg"] = []

# E-postinställningar
MAIL_AVSANDARE = "kvitto@ibklund.se"
MAIL_LOSENORD = "lquelydfygnvizqv"
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

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

# Skapa appens flikar
flik_registrera, flik_attestera, flik_admin = st.tabs([
    "📝 Registrera Utlägg", 
    "✅ Attestfunktion", 
    "⚙️ Adminpanel"
])

# =========================================================================
# FLIK 1: REGISTRERA UTLÄGG
# =========================================================================
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
        lag_reg = st.selectbox("Välj lag/avdelning:", options=st.session_state["lag"])
        konto_reg = st.selectbox("Välj kategori/konto för kvittot:", options=st.session_state["konton"])
        belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0, value=0.0)
        
        st.subheader("Bankuppgifter för utbetalning")
        bank_reg = st.text_input("Bankens namn:", placeholder="t.ex. Swedbank")
        clearing_reg = st.text_input("Clearingnummer:")
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
                    "id": len(st.session_state["vantande_utlagg"]) + len(st.session_state["godkanda_utlagg"]) + 1,
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
                
                st.session_state["vantande_utlagg"].append(nytt_utlagg)
                
                mailade = []
                for att in st.session_state["attestanter"]:
                    if lag_reg in att.get("lag", []):
                        if skicka_notis_mail(att["epost"], att["namn"], lag_reg, belopp_reg, konto_reg, namn_reg.strip()):
                            mailade.append(att["namn"])
                
                st.success(f"✅ Utlägget på {belopp_reg} kr har registrerats!")
                if mailade:
                    st.info(f"📧 Mailnotis har skickats till lagets attestant(er): {', '.join(mailade)}")
                
                st.session_state.uploader_id += 1
                st.rerun()

# =========================================================================
# FLIK 2: ATTESTFUNKTION
# =========================================================================
with flik_attestera:
    st.title("✅ Attestfunktion")
    
    st.subheader("Vem är du?")
    attestant_namn_lista = [a["namn"] for a in st.session_state["attestanter"]]
    
    if not attestant_namn_lista:
        st.warning("⚠️ Inga attestanter är upplagda ännu. Gå till Adminpanelen för att lägga till dig som attestant.")
    else:
        aktiv_attestant_namn = st.selectbox("Välj ditt namn för att se dina ärenden:", options=attestant_namn_lista)
        aktiv_attestant = next(a for a in st.session_state["attestanter"] if a["namn"] == aktiv_attestant_namn)
        mina_lag = aktiv_attestant.get("lag", [])
        
        st.write(f"Du har behörighet för följande lag: **{', '.join(mina_lag)}**")
        st.divider()

        aktuell_ko = [u for u in st.session_state["vantande_utlagg"] if u["lag"] in mina_lag]
        
        st.subheader("Ärenden som väntar på ditt godkännande")
        if not aktuell_ko:
            st.info("📥 Inga väntande utlägg för dina lag just nu.")
        else:
            for idx, utl in enumerate(aktuell_ko):
                st.markdown(f"### Ärende från {utl['namn']} ({utl['lag']})")
                st.write(f"**Bank:** {utl['bank']} | **Clearing:** {utl['clearing']} | **Konto:** {utl['kontonummer']} | **Fil:** {utl['filnamn']}")
                
                nytt_konto = st.selectbox(
                    f"Konto för ärende #{utl['id']}:", 
                    options=st.session_state["konton"], 
                    index=st.session_state["konton"].index(utl["kategori"]) if utl["kategori"] in st.session_state["konton"] else 0,
                    key=f"konto_{utl['id']}"
                )
                nytt_belopp = st.number_input(
                    f"Belopp (kr) för ärende #{utl['id']}:", 
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
                        
                        st.session_state["godkanda_utlagg"].append(utl)
                        st.session_state["vantande_utlagg"] = [u for u in st.session_state["vantande_utlagg"] if u["id"] != utl["id"]]
                        st.success("Utlägg attesterat!")
                        st.rerun()
            
                with col_b2:
                    if st.button("🗑️ Radera utlägg", key=f"radera_{utl['id']}"):
                        st.session_state["vantande_utlagg"] = [u for u in st.session_state["vantande_utlagg"] if u["id"] != utl["id"]]
                        st.warning("Utlägg borttaget och raderat ur kön.")
                        st.rerun()
                st.divider()

        # Export till Spiris
        st.subheader("Export till Spiris")
        mina_godkanda = [u for u in st.session_state["godkanda_utlagg"] if u["lag"] in mina_lag]
        
        if mina_godkanda:
            df_spiris = pd.DataFrame(mina_godkanda)
            kolumner_att_visa = ["namn", "lag", "kategori", "belopp", "bank", "clearing", "kontonummer", "datum_attesterat"]
            st.dataframe(df_spiris[kolumner_att_visa])
            
            csv = df_spiris[kolumner_att_visa].to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 Ladda ner fil för Spiris (CSV)",
                data=csv,
                file_name=f"spiris_export_{aktiv_attestant_namn}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Det finns inga godkända kvitton att exportera till Spiris för dina lag än.")

        # Historik per attestant
        st.divider()
        st.subheader(f"Din historik ({aktiv_attestant_namn})")
        historik_lista = [u for u in st.session_state["godkanda_utlagg"] if u.get("attesterat_av") == aktiv_attestant_namn]
