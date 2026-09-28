import json
import os
import streamlit as st

# 1. INSTÄLLNING FÖR DEN BAKOMLIGGANDE DATA-FILEN
DATA_FILE = "admin_data.json"


def ladda_admin_data():
    """Läser in inställningar från filen. Skapar standarddata om filen inte finns."""
    if not os.path.exists(DATA_FILE):
        standard_data = {
            "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
            "lag": ["A-lag", "J20", "P15"],
            "konton": ["4000", "5000", "6000"],
            "anvandare": [{"namn": "Anna", "roll": "Huvudadmin"}],
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(standard_data, f, ensure_ascii=False, indent=4)
        return standard_data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def spara_admin_data(data):
    """Sparar alla ändringar till JSON-filen."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# Hämta aktuell data när appen laddas
admin_data = ladda_admin_data()


# 2. SKAPA SKÄRMFLIKARNA I APPEN
flik_attest, flik_admin = st.tabs(["📋 Registrera Attest", "⚙️ Adminpanel"])


# =========================================================================
# --- FLIK 1: REGISTRERA ATTEST (Den vanliga vyn för användare) ---
# =========================================================================
with flik_attest:
    st.title("📋 Attestera och registrera utlägg")
    st.write("Fyll i uppgifterna nedan för att skicka in ditt utlägg.")

    # Sortera kategorierna så att 'Övrigt' alltid hamnar sist i rullistan
    aktuella_kategorier = list(admin_data.get("kategorier", []))
    if "Övrigt" in aktuella_kategorier:
        aktuella_kategorier.remove("Övrigt")
        aktuella_kategorier.sort()
        aktuella_kategorier.append("Övrigt")

    # HÄMTA DATA TILL RULLISTORNA FRÅN ADMINPANELEN
    vald_kategori = st.selectbox(
        "Välj kategori:",
        options=aktuella_kategorier,
        placeholder="Välj...",
    )
    valt_lag = st.selectbox(
        "Välj lag/avdelning:", options=admin_data.get("lag", [])
    )
    valt_konto = st.selectbox(
        "Välj bokföringskonto:", options=admin_data.get("konton", [])
    )

    belopp = st.number_input("Belopp (kr):", min_value=0.0, step=10.0)

    if st.button("Skicka in för attest"):
        st.success(
            f"Utlägget på {belopp} kr för {valt_lag} inom kategorin '{vald_kategori}' har skickats!"
        )


# =========================================================================
# --- FLIK 2: ADMINPANEL (Här styr du allt i realtid) ---
# =========================================================================
with flik_admin:
    st.title("⚙️ Administratörspanel")
    st.caption(
        "Här styr du allt som visas i appens rullistor och hanterar behörigheter."
    )

    # --- SEKTION: KATEGORIER ---
    with st.expander("📁 Hantera Kategorier (Utläggstyper)", expanded=True):
        st.write(
            f"**Aktuella kategorier:** {', '.join(admin_data['kategorier'])}"
        )

        col1, col2 = st.columns(2)
        with col1:
            ny_kat = st.text_input(
                "Lägg till ny kategori:", placeholder="t.ex. Kläder"
            )
            if st.button("➕ Lägg till", key="add_kat"):
                if ny_kat and ny_kat not in admin_data["kategorier"]:
                    admin_data["kategorier"].append(ny_kat)
                    spara_admin_data(admin_data)
                    st.success(f"'{ny_kat}' tillagd!")
                    st.rerun()

        with col2:
            kat_att_ta_bort = st.selectbox(
                "Ta bort en kategori:",
                options=["---"] + admin_data["kategorier"],
            )
            if (
                st.button("🗑️ Ta bort", key="del_kat")
                and kat_att_ta_bort != "---"
            ):
                admin_data["kategorier"].remove(kat_att_ta_bort)
                spara_admin_data(admin_data)
                st.warning(f"'{kat_att_ta_bort}' borttagen!")
                st.rerun()

    # --- SEKTION: LAG & KONTON ---
    with st.expander("🏃‍♂️ & 🧾 Hantera Lag och Konton"):
        col_lag, col_konto = st.columns(2)

        with col_lag:
            st.write("**Registrerade lag:**", admin_data.get("lag", []))
            nytt_lag = st.text_input("Nytt lag:")
            if st.button("➕ Lägg till lag"):
                if nytt_lag and nytt_lag not in admin_data["lag"]:
                    admin_data["lag"].append(nytt_lag)
                    spara_admin_data(admin_data)
                    st.rerun()

        with col_konto:
            st.write("**Bokföringskonton:**", admin_data.get("konton", []))
            nytt_konto = st.text_input("Nytt konto (nummer):")
            if st.button("➕ Lägg till konto"):
                if nytt_konto and nytt_konto not in admin_data["konton"]:
                    admin_data["konton"].append(nytt_konto)
                    spara_admin_data(admin_data)
                    st.rerun()

    # --- SEKTION: PERSONER & LÖSENORD ---
    with st.expander("👥 Hantera Attestanter & Lösenord"):
        st.write("**Användare i systemet:**")
        for anv in admin_data.get("anvandare", []):
            st.text(f"• {anv['namn']} ({anv['roll']})")

        st.divider()
        st.write("**Lägg till ny attestant:**")
        anv_namn = st.text_input("Namn på person:")
        anv_losen = st.text_input("Ange lösenord/PIN:", type="password")
        anv_roll = st.selectbox("Behörighetsnivå:", ["Attestant", "Huvudadmin"])

        if st.button("💾 Spara användare"):
            if anv_namn and anv_losen:
                ny_anvandare = {
                    "namn": anv_namn,
                    "losenord": anv_losen,
                    "roll": anv_roll,
                }
                admin_data["anvandare"].append(ny_anvandare)
                spara_admin_data(admin_data)
                st.success(f"{anv_namn} har lagts till!")
                st.rerun()
