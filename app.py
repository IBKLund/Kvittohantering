import streamlit as st
import pandas as pd
from datetime import datetime

# MÅSTE ligga absolut först
st.set_page_config(page_title="Kvittohantering", layout="wide")

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

# Skapa flikarna
flik_registrera, flik_attestera, flik_admin = st.tabs([
    "📝 Registrera Utlägg", 
    "✅ Attestfunktion", 
    "⚙️ Adminpanel"
])

# =========================================================================
# FLIK 1: REGISTRERA
# =========================================================================
with flik_registrera:
    st.title("📝 Registrera nytt utlägg")
    st.info("ℹ️ Utbetalning sker runt den 25:e varje månad. Kvitton efter den 10:e utbetalas nästa månad.")
    
    namn_reg = st.text_input("Ditt Namn:")
    lag_reg = st.selectbox("Välj lag:", options=st.session_state["lag"])
    konto_reg = st.selectbox("Välj konto:", options=st.session_state["konton"])
    belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0)
    
    st.subheader("Bankuppgifter")
    bank_reg = st.text_input("Bank:")
    clearing_reg = st.text_input("Clearingnummer:")
    konto_nr_reg = st.text_input("Kontonummer:")
    
    fil_reg = st.file_uploader("Ladda upp kvitto", type=["pdf", "png", "jpg", "jpeg"])
    
    if st.button("Skicka in utlägg", type="primary"):
        if namn_reg and bank_reg and clearing_reg and konto_nr_reg:
            nytt_utlagg = {
                "id": len(st.session_state["vantande_utlagg"]) + 1,
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
            st.success("✅ Utlägget har registrerats!")
        else:
            st.error("Fyll i alla fält.")

# =========================================================================
# FLIK 2: ATTEST
# =========================================================================
with flik_attestera:
    st.title("✅ Attestfunktion")
    
    attestant_namn_lista = [a["namn"] for a in st.session_state["attestanter"]]
    if not attestant_namn_lista:
        st.warning("Inga attestanter finns. Lägg till en i Adminpanelen först.")
    else:
        aktiv_attestant = st.selectbox("Välj ditt namn:", options=attestant_namn_lista)
        # Hitta den valda attestantens lag
        match = next(a for a in st.session_state["attestanter"] if a["namn"] == aktiv_attestant)
        mina_lag = match["lag"]
        
        st.write(f"Dina lag: {', '.join(mina_lag)}")
        
        # Visa väntande
        for utl in list(st.session_state["vantande_utlagg"]):
            if utl["lag"] in mina_lag:
                with st.container(border=True):
                    st.write(f"**Inskickat av:** {utl['namn']} | **Lag:** {utl['lag']} | **Belopp:** {utl['belopp']} kr")
                    if st.button(f"Godkänn #{utl['id']}", type="primary"):
                        st.session_state["godkanda_utlagg"].append(utl)
                        st.session_state["vantande_utlagg"].remove(utl)
                        st.success("Godkänt!")
                    if st.button(f"Radera #{utl['id']}"):
                        st.session_state["vantande_utlagg"].remove(utl)
                        st.warning("Raderat!")

# =========================================================================
# FLIK 3: ADMINPANEL
# =========================================================================
with flik_admin:
    st.title("⚙️ Adminpanel")
    st.write("Om du ser denna text fungerar fliken!")
    
    try:
        # Enkel visning och tillägg av lag
        st.subheader("Befintliga lag i systemet:")
        st.write(", ".join(st.session_state["lag"]))
        
        nytt_lag = st.text_input("Lägg till lagnamn:")
        if st.button("Spara nytt lag"):
            if nytt_lag and nytt_lag not in st.session_state["lag"]:
                st.session_state["lag"].append(nytt_lag)
                st.success("Lag tillagt!")
        
        st.divider()
        
        # Enkel hantering av attestanter
        st.subheader("Skapa ny attestant:")
        a_namn = st.text_input("Namn på attestant:")
        a_epost = st.text_input("E-post till attestant:")
        a_lag = st.multiselect("Välj lag för denna person:", options=st.session_state["lag"])
        
        if st.button("Spara attestant"):
            if a_namn and a_epost and a_lag:
                st.session_state["attestanter"].append({"namn": a_namn, "epost": a_epost, "lag": a_lag})
                st.success("Attestant sparad!")
                
        if st.session_state["attestanter"]:
            st.subheader("Registrerade attestanter:")
            for att in st.session_state["attestanter"]:
                st.write(f"👤 {att['namn']} ({att['epost']}) - Ansvarar för: {', '.join(att['lag'])}")
                
    except Exception as e:
        st.error(f"Ett dolt fel uppstod i adminfliken: {e}")
