import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
            "konton": ["4000 Inköp", "5000 Lokaler", "5800 Resekostnader", "6000 Övrigt"],
            "anvandare": [],
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(standard_data, f, ensure_ascii=False, indent=4)
        return standard_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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
# --- FLIK 1: REGISTRERA UTLÄGG (Konto borttaget härifrån) ---
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

            # Mailnotis skickas
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
# --- FLIK 2: ATTESTFUNKTION (Konto tillagt här för val/ändring) ---
# =========================================================================
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Granska inskickade underlag och tilldela bokföringskonto.")

    st.divider()
    st.subheader("Ärenden som väntar på godkännande")

    # Exempel på ett väntande ärende (Detta kan senare hämtas live från en databas)
    st.info("📥 **1 nytt utlägg att hantera:**")

    col_info, col_konto = st.columns([2, 1])

    with col_info:
        st.write("**Inskickat av:** Kalle Karlsson")
        st.write("**Lag:** A-lag")
        st.write("**Kategori:** Material (Föreslaget)")
        st.write("**Belopp:** 1 250,00 kr")
        st.caption("📄 *Kvitto_matchställ.pdf (Bifogad)*")

    with col_konto:
        # HÄR FÅR ATTESTANTEN VÄLJA OCH KORRIGERA KONTO LIVE
        valt_konto_attest = st.selectbox(
            "Välj/Ändra bokföringskonto:",
            options=admin_data.get("konton", []),
            key="attest_konto_val",
        )

    # Knappar för slutgiltigt beslut
    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("👍 Godkänn & Boka", type="primary"):
            st.success(
                f"Utlägget godkänt och bokfört på konto **{valt_konto_attest}**!"
            )
    with col_btn2:
        if st.button("👎 Neka utlägg"):
            st.error("Utlägget har nekats och returnerats till avsändaren.")


# =========================================================================
# --- FLIK 3: ADMINPANEL ---
# =========================================================================
with flik_admin:
    st.title("⚙️ Administratörspanel")

    # --- SEKTION: KATEGORIER ---
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

    # --- SEKTION: LAG & KONTON ---
    with st.expander("🏃‍♂️ & 🧾 Hantera Lag och Konton"):
        col_lag, col_konto = st.columns(2)
        with col_lag:
            st.write("**Registrerade lag:**", admin_data.get("lag", []))
            nytt_lag = st.text_input("Nytt lag:", key="admin_nytt_lag")
            if st.button("➕ Lägg till lag", key="btn_add_lag"):
                if nytt_lag and nytt_lag not in admin_data["lag"]:
                    admin_data["lag"].append(nytt_lag)
                    spara_admin_data(admin_data)
                    st.rerun()
        with col_konto:
            st.write("**Bokföringskonton:**", admin_data.get("konton", []))
            nytt_konto = st.text_input(
                "Nytt konto (t.ex. 4000 Inköp):", key="admin_nytt_konto"
            )
            if st.button("➕ Lägg till konto", key="btn_add_konto"):
                if nytt_konto and nytt_konto not in admin_data["konton"]:
                    admin_data["konton"].append(nytt_konto)
                    spara_admin_data(admin_data)
                    st.rerun()

    # --- SEKTION: PERSONER & LAGKOPPLING ---
    with st.expander("👥 Hantera Attestanter & Lagkoppling"):
        st.write("**Registrerade användare och deras ansvarslag:**")
        for anv in admin_data.get("anvandare", []):
            lag_str = ", ".join(anv.get("lag", [])) if anv.get("lag") else "Inga lag kopplade"
            st.text(f"• {anv['namn']} ({anv['epost']}) — Lag: [{lag_str}]")

        st.divider()
        st.write("**Lägg till ny attestant:**")
        anv_namn = st.text_input("Namn på person:", key="admin_anv_namn")
        anv_epost = st.text_input(
            "E-postadress (för notiser):",
            placeholder="namn@forening.se",
            key="admin_anv_epost",
        )
        anv_losen = st.text_input(
            "Ange lösenord/PIN:", type="password", key="admin_anv_losen"
        )
        anv_lag = st.multiselect(
            "Välj vilka lag denna person ska ta emot attest för:",
            options=admin_data.get("lag", []),
            key="admin_anv_lag_multi",
        )

        if st.button("💾 Spara användare och kopplingar", key="btn_save_user"):
            if anv_namn and anv_epost and anv_losen:
                ny_anvandare = {
                    "namn": anv_namn,
                    "epost": anv_epost,
                    "losenord": anv_losen,
                    "lag": anv_lag,
                }
                admin_data["anvandare"].append(ny_anvandare)
                spara_admin_data(admin_data)
