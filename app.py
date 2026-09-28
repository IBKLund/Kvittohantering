import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Inställningar för mappar och filer
KVITTO_MAPP = "sparade_kvitton"
DATA_FIL = "utlagg_data.csv"

if not os.path.exists(KVITTO_MAPP):
    os.makedirs(KVITTO_MAPP)

# Kontomappning för Spiris (BAS-kontoplan)
KONTO_KARTOR = {
    "Resor & Milersättning": "5800",
    "Fika & Mötesmat": "6071",
    "Kontorsmaterial": "6110",
    "Övriga utlägg": "6990"
}

# Läs in befintlig data
if os.path.exists(DATA_FIL):
    df = pd.read_csv(DATA_FIL)
else:
    df = pd.DataFrame(columns=["ID", "Datum", "Namn", "Kategori", "Konto", "Belopp", "Beskrivning", "Kvitto_Fil", "Status"])

st.title("Föreningens Utläggshantering 💰")

flik1, flik2 = st.tabs(["Inskickning (Medlem)", "Attestering & Export (Styrelse)"])

with flik1:
    st.header("Registrera nytt utlägg")
    
    medlem_namn = st.text_input("Ditt namn")
    kategori = st.selectbox("Kategori", list(KONTO_KARTOR.keys()))
    belopp = st.number_input("Belopp (kr)", min_value=1, step=1)
    beskrivning = st.text_area("Vad avser utlägget?")
    kvitto_fil = st.file_uploader("Ladda upp kvitto (Bild/PDF)", type=["png", "jpg", "jpeg", "pdf"])
    
    if st.button("Skicka in för godkännande"):
        if medlem_namn and belopp and kvitto_fil:
            utlagg_id = f"UT-{int(datetime.now().timestamp())}"
            
            # Spara kvittofilen lokalt
            fil_andelse = kvitto_fil.name.split(".")[-1]
            sparad_filnamn = f"{utlagg_id}_kvitto.{fil_andelse}"
            sökväg = os.path.join(KVITTO_MAPP, sparad_filnamn)
            with open(sökväg, "wb") as f:
                f.write(kvitto_fil.getbuffer())
            
            # Lägg till i data-tabellen
            ny_rad = {
                "ID": utlagg_id,
                "Datum": datetime.now().strftime("%Y-%m-%d"),
                "Namn": medlem_namn,
                "Kategori": kategori,
                "Konto": KONTO_KARTOR[kategori],
                "Belopp": belopp,
                "Beskrivning": beskrivning,
                "Kvitto_Fil": sparad_filnamn,
                "Status": "⚠️ Väntar"
            }
            
            df = pd.concat([df, pd.DataFrame([ny_rad])], ignore_index=True)
            df.to_csv(DATA_FIL, index=False)
            st.success(f"Utlägg inskickat! ID: {utlagg_id}")
        else:
            st.error("Vänligen fyll i alla fält och bifoga ett kvitto.")

with flik2:
    st.header("Styrelsens hantering")
    
    losenord = st.text_input("Ange lösenord för styrelsen", type="password")
    if losenord == "styrelsen123":
        st.subheader("Ärenden som väntar på attest")
        
ventande = df[df["Status"] == "⚠️ Väntar"]
        
        if ventande.empty:
            st.info("Inga nya utlägg att hantera just nu.")
        else:
            for idx, rad in ventande.iterrows():
                meddelande = f"**{rad['Namn']}** - {rad['Kategori']} ({rad['Belopp']} kr) \n*Beskrivning:* {rad['Beskrivning']}"
                st.write(meddelande)
                st.caption(f"Kvittofil: {rad['Kvitto_Fil']}")
                
                col1, col2 = st.columns(2)
                if col1.button("Godkänn", key=f"g_{rad['ID']}"):
                    df.at[idx, "Status"] = "✅ Godkänd"
                    df.to_csv(DATA_FIL, index=False)
                    st.rerun()
                if col2.button("Neka", key=f"n_{rad['ID']}"):
                    df.at[idx, "Status"] = "❌ Nekad"
                    df.to_csv(DATA_FIL, index=False)
                    st.rerun()
                st.divider()
        
        st.subheader("Exportera bokföringsunderlag till Spiris")
        godkanda = df[df["Status"] == "✅ Godkänd"]
        
        if not godkanda.empty:
            st.dataframe(godkanda[["ID", "Datum", "Namn", "Konto", "Belopp", "Beskrivning", "Kvitto_Fil"]])
            
            # Skapa CSV-sträng anpassad för import
            csv_data = godkanda[["Datum", "Konto", "Belopp", "Beskrivning", "Kvitto_Fil"]].to_csv(index=False)
            
            st.download_button(
                label="Ladda ner CSV för Spiris",
                data=csv_data,
                file_name=f"spiris_import_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.write("Inga godkända utlägg finns att exportera ännu.")
