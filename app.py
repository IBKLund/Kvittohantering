import streamlit as st
import pandas as pd
from datetime import datetime

# MÅSTE ligga absolut först
st.set_page_config(page_title="IBK Lund - Kvittohantering", layout="wide")

# =========================================================================
# LÖSENORD OCH INSTÄLLNINGAR (Ändra ditt adminlösenord här!)
# =========================================================================
ADMIN_LOSENORD = "admin123"  # <-- Byt ut till det lösenord du vill ha för adminfliken!

# Trygg initiering av sessionsminnet
if "lag" not in st.session_state:
    st.session_state["lag"] = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]
if "konton" not in st.session_state:
    st.session_state["konton"] = ["5800 Biljetter", "5830 Kost", "5831 Logi", "7330 Bilersättning"]
if "attestanter" not in st.session_state:
    st.session_state["attestanter"] = []
if "vantande_utlagg" not in st.session_state:
    st.session_state["vantande_utlagg"] = []
if "godkanda_utlagg" not in st.session_state:
    st.session_state["godkanda_utlagg"] = []

# E-postinställningar
MAIL_AVSANDARE = "kvitto@ibklund.se"
MAIL_LOSENORD = "uzierddeiefbongh"
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

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
# NY ENHETLIG SIDOMENY
# =========================================================================
st.sidebar.title("IBK Lund")
st.sidebar.subheader("Kvitto & Utlägg")
sida = st.sidebar.radio("Välj funktion:", ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"])

st.sidebar.divider()
if st.sidebar.button("♻️ Nollställ appens cache"):
    st.session_state.clear()
    st.rerun()

# =========================================================================
# MENY 1: REGISTRERA UTLÄGG (Öppen för alla)
# =========================================================================
if sida == "📝 Registrera Utlägg":
    st.title("📝 Registrera nytt utlägg")
    st.info("ℹ️ Utbetalning sker runt den 25:e varje månad. Kvitton efter den 10:e utbetalas nästa månad.")
    
    namn_reg = st.text_input("Ditt Namn:")
    lag_reg = st.selectbox("Välj lag:", options=st.session_state["lag"])
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
            
            # Notis till rätt lag-attestanter
            mailade = []
            for att in st.session_state["attestanter"]:
                if lag_reg in att.get("lag", []):
                    if skicka_notis_mail(att["epost"], att["namn"], lag_reg, belopp_reg, konto_reg, namn_reg):
                        mailade.append(att["namn"])
                        
            st.success("✅ Utlägget har registrerats och fälten har tömts!")
            st.rerun()  # Tömmer fälten automatiskt genom omladdning
        else:
            st.error("Du måste fylla i namn, bankuppgifter och belopp.")

# =========================================================================
# MENY 2: ATTESTFUNKTION (Kräver val av registrerad attestant)
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
            
            # Visa enbart väntande utlägg för attestantens tilldelade lag
            st.subheader("Ärenden som väntar på ditt godkännande")
            aktuell_ko = [u for u in st.session_state["vantande_utlagg"] if u["lag"] in mina_lag]
            
            if not aktuell_ko:
                st.info("📥 Inga nya utlägg ligger i kön för dina lag just nu.")
            else:
                for utl in list(st.session_state["vantande_utlagg"]):
                    if utl["lag"] in mina_lag:
                        with st.container(border=True):
                            st.write(f"**Inskickat av:** {utl['namn']} | **Lag:** {utl['lag']}")
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
                            
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                if st.button(f"✅ Godkänn & Attestera #{utl['id']}", type="primary", key=f"g_{utl['id']}"):
                                    utl["kategori"] = nytt_konto
                                    utl["belopp"] = nytt_belopp
                                    utl["attesterat_av"] = aktiv_attestant
                                    utl["datum_attesterat"] = datetime.now().strftime("%Y-%m-%d")
                                    st.session_state["godkanda_utlagg"].append(utl)
                                    st.session_state["vantande_utlagg"].remove(utl)
                                    st.success("Godkänt!")
                                    st.rerun()
                            with col_b2:
                                if st.button(f"🗑️ Radera utlägg #{utl['id']}", key=f"r_{utl['id']}"):
                                    st.session_state["vantande_utlagg"].remove(utl)
                                    st.warning("Utlägg raderat!")
                                    st.rerun()

            # Spiris Export
            st.divider()
            st.subheader("Export till Spiris")
            mina_godkanda = [u for u in st.session_state["godkanda_utlagg"] if u["lag"] in mina_lag]
            if mina_godkanda:
                df_spiris = pd.DataFrame(mina_godkanda)
                kolumner = ["namn", "lag", "kategori", "belopp", "bank", "clearing", "kontonummer", "datum_attesterat"]
                st.dataframe(df_spiris[kolumner])
                csv = df_spiris[kolumner].to_csv(index=False, encoding="utf-8-sig")
                st.download_button("📥 Ladda ner fil för Spiris (CSV)", data=csv, file_name=f"spiris_{aktiv_attestant}.csv", mime="text/csv")
            else:
                st.info("Inga godkända utlägg att exportera till Spiris för dina lag än.")

            # Historik per person
            st.divider()
            st.subheader(f"Din historik ({aktiv_attestant})")
            historik = [u for u in st.session_state["godkanda_utlagg"] if u.get("attesterat_av") == aktiv_attestant]
            if historik:
                st.dataframe(pd.DataFrame(historik)[["datum_attesterat", "namn", "lag", "kategori", "belopp"]])
            else:
                st.caption("Du har inte attesterat några kvitton i historiken än.")

# =========================================================================
