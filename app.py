import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import streamlit as st

# =========================================================================
# 1. INSTÄLLNINGAR FÖR BACKEND
# =========================================================================
DATA_FILE = "admin_data.json"

MAIL_AVSANDARE = "din_forenings_mail@gmail.com"
MAIL_LOSENORD = "ditt_app_losenord"
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587

# DINA EXAKTA KORREKTA KONTON OCH LAG
STANDARD_KONTON = [
    "5800 Biljetter (tåg/buss/flyg/båt)",
    "5830 Kost",
    "5831 Logi",
    "7330 Bilersättning",
    "2999 Övrigt",
]
STANDARD_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2"]


def ladda_admin_data():
    if not os.path.exists(DATA_FILE):
        standard_data = {
            "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
            "lag": STANDARD_LAG,
            "konton": STANDARD_KONTON,
            "anvandare": [],
            "godkanda_utlagg": [],
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(standard_data, f, ensure_ascii=False, indent=4)
        return standard_data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Säkerställ att grundstrukturen alltid är intakt
        if "godkanda_utlagg" not in data:
            data["godkanda_utlagg"] = []
        if "anvandare" not in data:
            data["anvandare"] = []

        # Tvinga uppdatering av dina specifika lag och konton så att gamla listor rensas bort
        data["lag"] = STANDARD_LAG
        data["konton"] = STANDARD_KONTON

        return data


def spara_admin_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def skicka_attest_mail(till_epost, attestant_namn, lag_namn, belopp, kategori):
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"
    text = f"Hej {attestant_namn},\nEtt nytt utlägg har registrerats för {lag_namn} och väntar på din attest."
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


# Hämta sparad data
admin_data = ladda_admin_data()
spara_admin_data(admin_data)  # Skriv direkt till filen så att uppdateringen sparar sig

# =========================================================================
# 2. SKAPA DE TRE FLIKARNA
# =========================================================================
flik_registrera, flik_attestera, flik_admin = st.tabs(
    ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"]
)

# --- FLIK 1: REGISTRERA UTLÄGG ---
with flik_registrera:
    st.title("📝 Registrera nytt utlägg")
    st.write("Fyll i uppgifterna och ladda upp ditt kvitto.")

    aktuella_kategorier = list(admin_data.get("kategorier", []))
    if "Övrigt" in aktuella_kategorier:
        aktuella_kategorier.remove("Övrigt")
        aktuella_kategorier.sort()
        aktuella_kategorier.append("Övrigt")

    valt_lag = st.selectbox(
        "Välj lag/avdelning:", options=admin_data.get("lag", []), key="reg_lag"
    )
    vald_kategori = st.selectbox(
        "Välj kategori:", options=aktuella_kategorier, key="reg_kat"
    )
    belopp = st.number_input(
        "Belopp (kr):", min_value=0.0, step=10.0, value=0.0, key="reg_belopp"
    )
    uppladdad_fil = st.file_uploader(
        "Ladda upp kvitto eller underlag (Obligatoriskt) *",
        type=["pdf", "png", "jpg", "jpeg"],
    )

    if st.button("Skicka in utlägg", type="primary"):
        if not uppladdad_fil:
            st.error(
                "❌ Du måste ladda upp ett kvitto eller underlag för att kunna skicka in utlägget!"
            )
        elif belopp <= 0:
            st.warning("⚠️ Vänligen ange ett giltigt belopp över 0 kr.")
        else:
            st.success(
                f"✅ Utlägget på {belopp} kr för {valt_lag} har skickats till attest!"
            )
            for anv in admin_data.get("anvandare", []):
                if valt_lag in anv.get("lag", []):
                    skicka_attest_mail(
                        anv["epost"],
                        anv["namn"],
                        valt_lag,
                        belopp,
                        vald_kategori,
                    )

# --- FLIK 2: ATTESTFUNKTION ---
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Granska inskickade underlag och tilldela bokföringskonto.")
    st.divider()
    st.subheader("Ärenden som väntar på godkännande")
    st.info("📥 **1 nytt utlägg att hantera:**")

    col_info, col_konto = st.columns(2)
    with col_info:
        namn_inskickat = "Kalle Karlsson"
        lag_inskickat = "Dam Elit"
        kat_inskickat = "Material"
        belopp_inskickat = 1250.00
        filnamn_inskickat = "Kvitto_matchställ.pdf"

        st.write(f"**Inskickat av:** {namn_inskickat}")
        st.write(f"**Lag:** {lag_inskickat}")
        st.write(f"**Kategori:** {kat_inskickat}")
        st.write(f"**Belopp:** {belopp_inskickat:,.2f} kr")
        st.caption(f"📄 *{filnamn_inskickat} (Bifogad)*")

    with col_konto:
        valt_konto_attest = st.selectbox(
            "Välj/Ändra bokföringskonto:",
            options=admin_data.get("konton", []),
            key="attest_konto_val",
        )

    col_btn1, col_btn2, _ = st.columns(3)
    with col_btn1:
        if st.button("👍 Godkänn", type="primary"):
            nytt_godkant = {
                "Inskickat av": namn_inskickat,
                "Lag": lag_inskickat,
                "Kategori": kat_inskickat,
                "Belopp (kr)": belopp_inskickat,
                "Bokföringskonto": valt_konto_attest,
                "Kvittofil": filnamn_inskickat,
            }
            admin_data["godkanda_utlagg"].append(nytt_godkant)
            spara_admin_data(admin_data)
            st.success(f"Utlägget godkänt på konto: **{valt_konto_attest}**.")
            st.rerun()

    with col_btn2:
        if st.button("👎 Neka utlägg"):
            st.error("Utlägget har nekats.")

    st.divider()
    st.subheader("📦 Exportera godkända utlägg")
    if admin_data["godkanda_utlagg"]:
        df = pd.DataFrame(admin_data["godkanda_utlagg"])
        st.dataframe(df)
        csv_data = df.to_csv(index=False, encoding="utf-8-sig", sep=";")
        st.download_button(
            label="📥 Ladda ner som CSV-fil för bokföring",
            data=csv_data,
            file_name="godkanda_utlagg.csv",
            mime="text/csv",
        )
    else:
        st.caption("Det finns inga godkända utlägg i historiken ännu.")

# --- FLIK 3: ADMINPANEL ---
with flik_admin:
    st.title("⚙️ Administratörspanel")

    with st.expander("📁 Hantera Kategorier (Utläggstyper)", expanded=False):
        st.write(
            f"**Aktuella kategorier:** {', '.join(admin_data['kategorier'])}"
        )
        col1, col2 = st.columns(2)
        with col1:
            ny_kat = st.text_input(
                "Lägg till ny kategori:",
                placeholder="t.ex. Kläder",
                key="admin_ny_kat",
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
                key="admin_del_kat_sel",
            )
            if (
                st.button("🗑️ Ta bort", key="del_kat")
                and kat_att_ta_bort != "---"
            ):
                admin_data["kategorier"].remove(kat_att_ta_bort)
                spara_admin_data(admin_data)
                st.warning(f"'{kat_att_ta_bort}' borttagen!")
                st.rerun()

    with st.expander("🏃‍♂️ & 🧾 Hantera Lag och Konton", expanded=False):
        st.write("**Registrerade lag:**")
        st.write(", ".join(admin_data.get("lag", [])))
        st.write("**Bokföringskonton:**")
        for k in admin_data.get("konton", []):
            st.text(f"• {k}")

    with st.expander("👥 Hantera Attestanter & Lagkoppling", expanded=True):
        st.subheader("Registrerade användare och ansvarsområden")

        if admin_data.get("anvandare") and len(admin_data["anvandare"]) > 0:
            anv_list = []
            for anv in admin_data["anvandare"]:
                anv_list.append(
                    {
                        "Namn": anv.get("namn", ""),
                        "E-post": anv.get("epost", ""),
                        "Kopplade Lag": ", ".join(anv.get("lag", [])),
                    }
                )
            st.dataframe(pd.DataFrame(anv_list), use_container_width=True)
        else:
            st.info("Inga attestanter har registrerats ännu.")

        st.divider()
        st.subheader("Skapa ny attestantprofil")

        with st.form("skapa_anvandare_form", clear_on_submit=True):
            anv_namn = st.text_input("Namn på person:")
            anv_epost = st.text_input("E-postadress (för notiser):")
            anv_losen = st.text_input("Ange lösenord/PIN:", type="password")

            tillgangliga_lag = list(admin_data.get("lag", []))
            anv_lag = st.multiselect(
                "Markera de lag personen får attestera för:",
                options=tillgangliga_lag,
