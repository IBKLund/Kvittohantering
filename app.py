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


def ladda_admin_data():
    if not os.path.exists(DATA_FILE):
        standard_data = {
            "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
            "lag": ["A-lag", "J20", "P15"],
            "konton": [
                "4000 Inköp",
                "5000 Lokaler",
                "5800 Resekostnader",
                "6000 Övrigt",
            ],
            "anvandare": [],
            "godkanda_utlagg": [],
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(standard_data, f, ensure_ascii=False, indent=4)
        return standard_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "godkanda_utlagg" not in data:
            data["godkanda_utlagg"] = []
        return data


def spara_admin_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def skicka_attest_mail(till_epost, attestant_namn, lag_namn, belopp, kategori):
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"

    text = f"""Hej {attestant_namn},
Ett nytt utlägg har registrerats för {lag_namn} och väntar på din attest.
• Kategori: {kategori}
• Belopp: {belopp} kr
Logga in för att välja konto och godkänna utlägget."""

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
flik_registrera, flik_attestera, flik_admin = st.tabs(
    ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"]
)


# =========================================================================
# --- FLIK 1: REGISTRERA UTLÄGG ---
# =========================================================================
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


# =========================================================================
# --- FLIK 2: ATTESTFUNKTION ---
# =========================================================================
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Granska inskickade underlag och tilldela bokföringskonto.")

    st.divider()
    st.subheader("Ärenden som väntar på godkännande")

    st.info("📥 **1 nytt utlägg att hantera:**")

    col_info, col_konto = st.columns(2)

    with col_info:
        namn_inskickat = "Kalle Karlsson"
        lag_inskickat = "A-lag"
        kat_inskickat = "Material"
        belopp_inskickat = 1250.00
        filnamn_inskickat = "Kvitto_matchställ.pdf"

        st.write(f"**Inskickat av:** {namn_inskickat}")
        st.write(f"**Lag:** {lag_inskickat}")
        st.write(f"**Kategori:** {kat_inskickat}")
        st.write(f"**Belopp:** {belopp_inskickat:,.2f} kr")
        st.caption(f"📄 *{filnamn_inskickat} (Bifogad)*")

    with col_konto:
        # Här fylls kolumnen med rätt indrag
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
        st.write(
            f"Det finns **{len(admin_data['godkanda_utlagg'])}** godkända utlägg."
        )
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


# =========================================================================
# --- FLIK 3: ADMINPANEL ---
# =========================================================================
with flik_admin:
    st.title("⚙️ Administratörspanel")

    with st.expander("📁 Hantera Kategorier (Utläggstyper)", expanded=True):
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

    with st.expander("🏃‍♂️ & 🧾 Hantera Lag och Konton"):
        col_lag, col_konto_admin = st.columns(2)
        with col_lag:
            st.write("**Registrerade lag:**", admin_data.get("lag", []))
            nytt_lag = st.text_input("Nytt lag:", key="admin_nytt_lag")
            if st.button("➕ Lägg till lag", key="btn_add_lag"):
                if nytt_lag and nytt_lag not in admin_data["lag"]:
                    admin_data["lag"].append(nytt_lag)
                    spara_admin_data(admin_data)
                    st.rerun()
        with col_konto_admin:
            st.write("**Bokföringskonton:**", admin_data.get("konton", []))
            nytt_konto = st.text_input(
                "Nytt konto (t.ex. 4000 Inköp):", key="admin_nytt_konto"
            )
            if st.button("➕ Lägg till konto", key="btn_add_konto"):
                if nytt_konto and nytt_konto not in admin_data["konton"]:
                    admin_data["konton"].append(nytt_konto)
                    spara_admin_data(admin_data)
                    st.rerun()

    with st.expander("👥 Hantera Attestanter & Lagkoppling"):
        st.write("**Registrerade användare och deras ansvarslag:**")
        for anv in admin_data.get("anvandare", []):
            lag_str = (
                ", ".join(anv.get("lag", []))
                if anv.get("lag")
