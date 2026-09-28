import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Inställningar för mappar och filer
KVITTO_MAPP = "sparade_kvitton"
DATA_FIL = "utlagg_data.csv"

if not os.path.exists(KVITTO_MAPP):
    os.makedirs(KVITTO_MAPP)

# Standardkonton enligt BAS-kontoplanen (Går att ändra live av admin)
KONTO_KARTOR = {
    "Bilersättning": "5841",
    "Logi": "5820",
    "Kost": "6071",
    "Biljett (flyg/tåg/buss)": "5810",
    "Övrigt": "6990"
}

# Lista över lag (Ändra dessa så att de matchar er förening!)
LAG_LISTA = ["A-laget Herr", "A-laget Dam", "Juniorer U19", "Pojkar U15", "Flickor U15", "Styrelse/Kansli"]
FORENING_NAMN = "Idrottsföreningen" # Er standardförening

# Läs in befintlig data
if os.path.exists(DATA_FIL):
    df = pd.read_csv(DATA_FIL, dtype={"Konto": str})
else:
    df = pd.DataFrame(columns=["ID", "Datum", "Namn", "Kategori", "Konto", "Belopp", "Beskrivning", "Lag", "Förening", "Kvitto_Fil", "Status"])

st.title("Föreningens Utläggshantering 💰")

flik1, flik2 = st.tabs(["Inskickning (Medlem)", "Attestering & Export (Styrelse)"])

with flik1:
    st.header("Registrera nytt utlägg")
    
    medlem_namn = st.text_input("Ditt namn")
    lag = st.selectbox("Vilket lag tillhör du?", LAG_LISTA)
    kategori = st.selectbox("Kategori", list(KONTO_KARTOR.keys()))
    belopp = st.number_input("Belopp (kr)", min_value=1, step=1)
    beskrivning = st.text_area("Vad avser utlägget? (t.ex. 'Bensin till bortamatch')")
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
                "Lag": lag,
                "Förening": FORENING_NAMN,
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
        
        # Filtrera fram väntande
        df_ventande = df[df["Status"] == "⚠️ Väntar"]
        
        if df_ventande.empty:
            st.info("Inga nya utlägg att hantera just nu.")
        else:
            for idx, rad in df_ventande.iterrows():
                st.markdown(f"### Utlägg från {rad['Namn']} ({rad['Lag']})")
                
                # Inmatningsfält för korrigeringar live under attestering
                col_k1, col_k2, col_k3 = st.columns(3)
                justerat_konto = col_k1.text_input("Bokföringskonto", value=str(rad['Konto']), key=f"konto_{rad['ID']}")
                justerat_lag = col_k2.selectbox("Lag/Sektion", LAG_LISTA, index=LAG_LISTA.index(rad['Lag']) if rad['Lag'] in LAG_LISTA else 0, key=f"lag_{rad['ID']}")
                justerad_forening = col_k3.text_input("Förening", value=str(rad['Förening']), key=f"for_{rad['ID']}")
                
                st.write(f"**Kategori:** {rad['Kategori']} | **Belopp:** {rad['Belopp']} kr")
                st.write(f"*Beskrivning:* {rad['Beskrivning']}")
                st.caption(f"Bifogad kvittofil: {rad['Kvitto_Fil']}")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                if col1.button("✅ Godkänn", key=f"g_{rad['ID']}"):
                    df.at[idx, "Konto"] = justerat_konto
                    df.at[idx, "Lag"] = justerat_lag
                    df.at[idx, "Förening"] = justerad_forening
                    df.at[idx, "Status"] = "✅ Godkänd"
                    df.to_csv(DATA_FIL, index=False)
                    st.rerun()
                if col2.button("❌ Neka", key=f"n_{rad['ID']}"):
                    df.at[idx, "Status"] = "❌ Nekad"
                    df.to_csv(DATA_FIL, index=False)
                    st.rerun()
                    
                st.divider()
        
        st.subheader("Exportera godkända underlag till Spiris")
        df_godkanda = df[df["Status"] == "✅ Godkänd"]
        
        if not df_godkanda.empty:
            st.dataframe(df_godkanda[["ID", "Datum", "Namn", "Förening", "Lag", "Konto", "Belopp", "Beskrivning", "Kvitto_Fil"]])
            
            # Skapa den slutgiltiga exportfilen formaterad för bokföringen
            csv_export = df_godkanda[["Datum", "Förening", "Lag", "Konto", "Belopp", "Beskrivning", "Kvitto_Fil"]]
            csv_data = csv_export.to_csv(index=False)
            
            st.download_button(
                label="Ladda ner CSV för Spiris",
                data=csv_data,
                file_name=f"spiris_import_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.write("Inga godkända utlägg finns att exportera ännu.")
