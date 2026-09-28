import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import streamlit as st

# =========================================================================
# 1. INSTÄLLNINGAR FÖR BACKEND (DATA & MAIL)
# =========================================================================
DATA_FILE = "admin_data.json"

# --- MAILKONFIGURATION (Fyll i dina egna uppgifter här sen) ---
MAIL_AVSANDARE = "din_forenings_mail@gmail.com"
# Ett genererat "App-lösenord" från t.ex. Google (inte ditt vanliga privata lösenord)
MAIL_LOSENORD = "ditt_app_losenord"
MAIL_SMTP_SERVER = "://gmail.com"
MAIL_PORT = 587


def ladda_admin_data():
    if not os.path.exists(DATA_FILE):
        standard_data = {
            "kategorier": ["Bilersättning", "Kost", "Logi", "Biljetter", "Övrigt"],
            "lag": ["A-lag", "J20", "P15"],
            "konton": ["4000", "5000", "6000"],
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
    """Skickar ett automatiskt mail till rätt attestant."""
    msg = MIMEMultipart()
    msg["From"] = MAIL_AVSANDARE
    msg["To"] = till_epost
    msg["Subject"] = f"Nytt utlägg att attestera - {lag_namn}"

    text = f"""Hej {attestant_namn},

Ett nytt utlägg har registrerats för ett av dina ansvarsområden/lag och väntar på din attest.

• Lag: {lag_namn}
• Kategori: {kategori}
• Belopp: {belopp} kr

Logga in i Streamlit-appen för att granska underlaget och godkänna eller neka utlägget.

Med vänlig hälsning,
Ekonomisystemet"""

    msg.attach(MIMEText(text, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(MAIL_SMTP_SERVER, MAIL_PORT)
        server.starttls()
        server.login(MAIL_AVSANDARE, MAIL_LOSENORD)
        server.sendmail(MAIL_AVSANDARE, till_epost, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        # Visas i server-loggen om det misslyckas (t.ex. vid fel inställningar)
        print(f"Kunde inte skicka mail: {e}")
        return False


# Ladda data vid start
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
    st.write("Fyll i alla uppgifter och ladda upp ditt kvitto.")

    aktuella_kategorier = list(admin_data.get("kategorier", []))
    if "Övrigt" in aktuella_kategorier:
        aktuella_kategorier.remove("Övrigt")
        aktuella_kategorier.sort()
        aktuella_kategorier.append("Övrigt")

    valt_lag = st.selectbox(
        "Välj lag/avdelning:", options=admin_data.get("lag", [])
    )
    vald_kategori = st.selectbox(
        "Välj kategori:", options=aktuella_kategorier
    )
    valt_konto = st.selectbox(
        "Välj bokföringskonto:", options=admin_data.get("konton", [])
    )
    belopp = st.number_input(
        "Belopp (kr):", min_value=0.0, step=10.0, value=0.0
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
                f"✅ Utlägget på {belopp} kr för {valt_lag} har registrerats!"
            )

            # SÖK EFTER KOPPLADE ATTESTANTER OCH SKICKA MAIL
            mail_skickat_till = []
            for anv in admin_data.get("anvandare", []):
                # Kontrollera om det valda laget finns i listan över personens lag
                if valt_lag in anv.get("lag", []):
                    # Försök skicka mailet
                    framgang = skicka_attest_mail(
                        till_epost=anv["epost"],
                        attestant_namn=anv["namn"],
                        lag_namn=valt_lag,
                        belopp=belopp,
                        kategori=vald_kategori,
                    )
                    if framgang:
                        mail_skickat_till.append(anv["namn"])

            if mail_skickat_till:
                st.info(
                    f"📧 E-postnotis har skickats till ansvarig attestant: {', '.join(mail_skickat_till)}"
                )
            else:
                st.caption(
                    "ℹ️ Ingen attestant är kopplad till detta lag ännu, så inget mail skickades."
                )


# =========================================================================
# --- FLIK 2: ATTESTFUNKTION ---
# =========================================================================
with flik_attestera:
    st.title("✅ Attestfunktion")
    st.write("Här visas inskickade utlägg som väntar på ditt godkännande.")
    st.info("Inga nya utlägg att attestera just nu.")


# =========================================================================
# --- FLIK 3: ADMINPANEL ---
# =========================================================================
with flik_admin:
    st.title("⚙️ Administratörspanel")
    st.caption("Hantera systemets grunddata, lagkopplingar och behörigheter.")

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

    # --- SEKTION: PERSONER, LÖSENORD & LAGKOPPLING ---
    with st.expander("👥 Hantera Attestanter & Lagkoppling"):
        st.write("**Registrerade användare och deras ansvarslag:**")
        for anv in admin_data.get("anvandare", []):
            lag_str = ", ".join(anv.get("lag", [])) if anv.get("lag") else "Inga lag kopplade"
            st.text(f"• {anv['namn']} ({anv['epost']}) — Kopplad till: [{lag_str}]")

        st.divider()
        st.write("**Lägg till ny attestant och koppla lag:**")
        anv_namn = st.text_input("Namn på person:")
        anv_epost = st.text_input("E-postadress (för notiser):", placeholder="namn@forening.se")
        anv_losen = st.text_input("Ange lösenord/PIN:", type="password")
        
        # HÄR ÄR MULTISELECT FÖR ATT KOPPLA FLERA LAG TILL SAMMA PERSON
        anv_lag = st.multiselect(
            "Välj vilka lag denna person ska ta emot attest för:",
            options=admin_data.get("lag", []),
        )

        if st.button("💾 Spara användare och kopplingar"):
            if anv_namn and anv_epost and anv_losen:
                ny_anvandare = {
                    "namn": anv_namn,
                    "epost": anv_epost,
                    "losenord": anv_losen,
                    "lag": anv_lag,  # Sparar listan med valda lag
                }
                admin_data["anvandare"].append(ny_anvandare)
                spara_admin_data(admin_data)
                st.success(f"Attestanten {anv_namn} har sparats och kopplats till valda lag!")
                st.rerun()
            else:
                st.error("Vänligen fyll i namn, e-post och lösenord.")
