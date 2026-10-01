import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import resend
import streamlit as st

st.set_page_config(page_title="IBK Lund", layout="wide")

DATA_FILE = "admin_data.json"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

DEFAULT_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2", "LundaLägret", "NovaOpen"]
DEFAULT_KONTON = ["5800 Biljetter", "5830 Kost", "5831 Logi", "7330 Bilersättning", "2999 Övrigt"]
DEFAULT_ATTESTANTER = [
    {"namn": "Christer Sölve", "epost": "christer@solve.se", "lag": ["Herr Elit"]},
    {"namn": "Magnus Berglund", "epost": "magnus.berglund@ibklund.se", "lag": ["LundaLägret", "NovaOpen"]},
]


def get_app_base_url():
    if "APP_BASE_URL" in st.secrets:
        return st.secrets["APP_BASE_URL"].rstrip("/")
    return "http://localhost:8501"


if "RESEND_API_KEY" in st.secrets:
    resend.api_key = st.secrets["RESEND_API_KEY"]
else:
    st.error("⚠️ RESEND_API_KEY saknas i Streamlit Secrets!")


def read_secrets_users():
    users = []
    if "APP_USERS" in st.secrets:
        raw = st.secrets["APP_USERS"]
        if isinstance(raw, list):
            users = raw
    return users


def get_app_users():
    users = read_secrets_users()
    if not users:
        users = [
            {
                "username": "christer",
                "password": "ibk123",
                "name": "Christer Sölve",
                "email": "christer@solve.se",
                "role": "admin",
                "lag": ["Herr Elit"],
            },
            {
                "username": "magnus",
                "password": "ibk123",
                "name": "Magnus Berglund",
                "email": "magnus.berglund@ibklund.se",
                "role": "attestant",
                "lag": ["LundaLägret", "NovaOpen"],
            },
        ]
    return users


def authenticate_user(username, password):
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return None

    for user in get_app_users():
        if str(user.get("username", "")).strip().lower() == username.lower():
            if str(user.get("password", "")) == password:
                return {
                    "username": user.get("username", username),
                    "name": user.get("name", user.get("username", username)),
                    "email": user.get("email", ""),
                    "role": user.get("role", "attestant"),
                    "lag": user.get("lag", []),
                }
    return None


def load_data():
    default = {
        "lag": DEFAULT_LAG.copy(),
        "konton": DEFAULT_KONTON.copy(),
        "attestanter": DEFAULT_ATTESTANTER.copy(),
        "vantande_utlagg": [],
        "godkanda_utlagg": [],
    }
    if not os.path.exists(DATA_FILE):
        return default

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in default.items():
            if key not in data or not isinstance(data[key], type(value)):
                data[key] = value
        if not data["attestanter"]:
            data["attestanter"] = DEFAULT_ATTESTANTER.copy()
        return data
    except Exception:
        return default


def save_data():
    try:
        payload = {
            "lag": st.session_state.get("lag", []),
            "konton": st.session_state.get("konton", []),
            "attestanter": st.session_state.get("attestanter", []),
            "vantande_utlagg": st.session_state.get("vantande_utlagg", []),
            "godkanda_utlagg": st.session_state.get("godkanda_utlagg", []),
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


for key, value in load_data().items():
    st.session_state.setdefault(key, value)

for key in [
    "minne_namn",
    "minne_bank",
    "minne_clearing",
    "minne_konto",
    "bekraftelse_meddelande",
    "an_namn",
    "an_mail",
    "an_lag",
    "auth_user",
    "auth_role",
]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "an_lag" else []


def send_notification_email(till, namn, lag, belopp, kat, av):
    app_url = get_app_base_url()
    msg_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background-color:#003366; padding:20px; text-align:center; color:white;">
            <h2 style="margin:0; font-size:22px;">IBK Lund</h2>
            <p style="margin:5px 0 0; opacity:0.8;">Kvitto- & Utläggshantering</p>
        </div>
        <div style="padding:24px; line-height:1.6; color:#333;">
            <p style="font-size:16px; margin-top:0;">Hej <b>{namn}</b>,</p>
            <p>Ett nytt utlägg har registrerats och väntar på ditt godkännande.</p>
            <div style="background-color:#f9f9f9; border-left:4px solid #003366; padding:15px; margin:20px 0; border-radius:4px;">
                <table style="width:100%; border-collapse:collapse;">
                    <tr><td style="padding:5px 0; color:#666; width:120px;"><b>Inskickat av:</b></td><td>{av}</td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Lag/Aktivitet:</b></td><td>{lag}</td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Kategori:</b></td><td>{kat}</td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Belopp:</b></td><td style="font-size:16px; color:#003366;"><b>{belopp} kr</b></td></tr>
                </table>
            </div>
            <p>Vänligen logga in i appen för att granska underlaget, korrigera eventuella uppgifter och attestera utlägget.</p>
            <div style="text-align:center; margin:30px 0;">
                <a href="{app_url}" style="background-color:#003366; color:white; padding:12px 30px; text-decoration:none; font-weight:bold; border-radius:5px; display:inline-block;">Gå till appen</a>
            </div>
        </div>
        <div style="background-color:#f4f4f4; padding:15px; text-align:center; font-size:12px; color:#888; border-top:1px solid #ddd;">
            Detta är ett automatiskt meddelande från IBK Lunds kvittoapp.
        </div>
    </div>
    """

    try:
        resend.Emails.send(
            {
                "from": "IBK Lund Kvittohantering <onboarding@resend.dev>",
                "to": till,
                "subject": f"🔔 Nytt utlägg att attestera - {lag}",
                "html": msg_html,
            }
        )
        return True
    except Exception:
        return False


st.sidebar.title("IBK Lund")
page = st.sidebar.radio("Välj funktion:", ["📝 Registrera Utlägg", "✅ Attestfunktion", "⚙️ Adminpanel"])


def render_login_panel():
    st.warning("🔒 Du måste logga in för att komma åt denna sida.")
    with st.form("login_form"):
        username = st.text_input("Användarnamn")
        password = st.text_input("Lösenord", type="password")
        submitted = st.form_submit_button("Logga in")
        if submitted:
            user = authenticate_user(username, password)
            if user:
                st.session_state["auth_user"] = user["name"]
                st.session_state["auth_role"] = user["role"]
                st.session_state["auth_lag"] = user["lag"]
                st.session_state["auth_username"] = user["username"]
                st.session_state["auth_email"] = user["email"]
                st.success(f"Inloggad som {user['name']}")
                st.rerun()
            else:
                st.error("Fel användarnamn eller lösenord.")
    st.stop()


if page == "📝 Registrera Utlägg":
    st.title("📝 Registrera nytt utlägg")
    st.info("ℹ️ Utbetalning sker runt den 25:e varje månad. Kvitton efter den 10:e utbetalas nästa månad.")
    if st.session_state.get("bekraftelse_meddelande"):
        st.success(st.session_state["bekraftelse_meddelande"])
        st.session_state["bekraftelse_meddelande"] = ""

    with st.form("huvud_reg_form", clear_on_submit=True):
        namn_reg = st.text_input("Ditt Namn:", value=st.session_state["minne_namn"])
        lag_reg = st.selectbox("Välj lag / aktivitet:", options=st.session_state["lag"])
        konto_reg = st.selectbox("Välj konto:", options=st.session_state["konton"])
        belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0)

        st.subheader("Bankuppgifter för utbetalning")
        bank_reg = st.text_input("Bank:", value=st.session_state["minne_bank"])
        clearing_reg = st.text_input("Clearingnummer:", value=st.session_state["minne_clearing"])
        konto_nr_reg = st.text_input("Kontonummer:", value=st.session_state["minne_konto"])
        fil_reg = st.file_uploader("Ladda upp kvitto", type=["pdf", "png", "jpg", "jpeg"])

        if st.form_submit_button("Skicka in utlägg", type="primary"):
            if not (namn_reg and bank_reg and clearing_reg and konto_nr_reg):
                st.error("Fyll i alla namn- och bankuppgifter.")
            else:
                st.session_state["minne_namn"] = namn_reg.strip()
                st.session_state["minne_bank"] = bank_reg.strip()
                st.session_state["minne_clearing"] = clearing_reg.strip()
                st.session_state["minne_konto"] = konto_nr_reg.strip()

                file_name = "Inget underlag"
                if fil_reg is not None:
                    file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fil_reg.name}"
                    target = UPLOAD_DIR / file_name
                    target.write_bytes(fil_reg.getvalue())

                utl = {
                    "id": len(st.session_state["vantande_utlagg"]) + len(st.session_state["godkanda_utlagg"]) + 1,
                    "namn": namn_reg.strip(),
                    "lag": lag_reg,
                    "kategori": konto_reg,
                    "belopp": float(belopp_reg),
                    "bank": bank_reg.strip(),
                    "clearing": clearing_reg.strip(),
                    "kontonummer": konto_nr_reg.strip(),
                    "filnamn": file_name,
                    "datum_inskickat": datetime.now().strftime("%Y-%m-%d"),
                }

                st.session_state["vantande_utlagg"].append(utl)
                save_data()

                att_namn = []
                for att in st.session_state["attestanter"]:
                    if lag_reg in att.get("lag", []):
                        att_namn.append(att["namn"])
                        send_notification_email(att["epost"], att["namn"], lag_reg, belopp_reg, konto_reg, namn_reg.strip())

                if att_namn:
                    st.session_state["bekraftelse_meddelande"] = f"✅ Registrerat! Väntar på attest av {' & '.join(att_namn)}."
                else:
                    st.session_state["bekraftelse_meddelande"] = "✅ Registrerat! (Ingen attestant kopplad)."
                st.rerun()

elif page == "✅ Attestfunktion":
    if "auth_user" not in st.session_state or not st.session_state.get("auth_user"):
        render_login_panel()

    current_user = st.session_state.get("auth_user")
    access_lag = st.session_state.get("auth_lag", [])

    st.title("✅ Attestfunktion")
    st.success(f"Inloggad: {current_user}.")

    if not access_lag:
        st.warning("Din användare är inte kopplad till några lag/aktiviteter.")
        st.stop()

    for u in list(st.session_state["vantande_utlagg"]):
        if u["lag"] not in access_lag:
            continue

        with st.container(border=True):
            st.write(f"**Från:** {u['namn']} | **Lag:** {u['lag']} | **Bank:** {u['bank']} {u['clearing']}-{u['kontonummer']}")
            nk = st.selectbox(
                f"Konto för {u['namn']}:",
                options=st.session_state["konton"],
                index=st.session_state["konton"].index(u["kategori"]) if u["kategori"] in st.session_state["konton"] else 0,
                key=f"k_{u['id']}",
            )
            nb = st.number_input(f"Belopp för {u['namn']}:", value=float(u["belopp"]), key=f"b_{u['id']}")

            col_a, col_b = st.columns(2)
            if col_a.button(f"Godkänn #{u['id']}", type="primary", key=f"g_{u['id']}"):
                u["kategori"] = nk
                u["belopp"] = float(nb)
                u["attesterat_av"] = current_user
                u["datum_attesterat"] = datetime.now().strftime("%Y-%m-%d")
                st.session_state["godkanda_utlagg"].append(u)
                st.session_state["vantande_utlagg"].remove(u)
                save_data()
                st.rerun()

            if col_b.button(f"Radera #{u['id']}", key=f"r_{u['id']}"):
                st.session_state["vantande_utlagg"].remove(u)
                save_data()
                st.rerun()

    st.subheader("Export till Spiris")
    df = pd.DataFrame([u for u in st.session_state["godkanda_utlagg"] if u["lag"] in access_lag])
    if not df.empty:
        cols = ["namn", "lag", "kategori", "belopp", "bank", "clearing", "kontonummer", "datum_attesterat"]
        st.dataframe(df[cols])
        st.download_button(
            label="📥 Ladda ner CSV",
            data=df[cols].to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"spiris_{current_user.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Inga godkända utlägg att exportera.")

    st.subheader("Din historik")
    hist = [u for u in st.session_state["godkanda_utlagg"] if u.get("attesterat_av") == current_user]
    if hist:
        st.dataframe(pd.DataFrame(hist)[["datum_attesterat", "namn", "lag", "kategori", "belopp"]])

elif page == "⚙️ Adminpanel":
    if "auth_user" not in st.session_state or not st.session_state.get("auth_user"):
        render_login_panel()

    if st.session_state.get("auth_role") != "admin":
        st.warning("🔒 Du är inloggad men saknar admin-behörighet.")
        st.stop()

    st.title("⚙️ Adminpanel")

    st.subheader("Hantering av Lag & Aktiviteter")
    st.write(", ".join(st.session_state["lag"]))
    nl = st.text_input("Lägg till lag/aktivitet:", key="admin_lag")
    if st.button("Spara nytt val", key="as_lag"):
        if nl and nl not in st.session_state["lag"]:
            st.session_state["lag"].append(nl.strip())
            save_data()
            st.rerun()

    st.divider()

    st.subheader("Hantering av Bokföringskonton")
    st.write(", ".join(st.session_state["konton"]))
    nk = st.text_input("Lägg till kontonamn:", key="admin_konto")
    if st.button("Spara nytt konto", key="as_konto"):
        if nk and nk not in st.session_state["konton"]:
            st.session_state["konton"].append(nk.strip())
            save_data()
            st.rerun()

    st.divider()

    st.subheader("Hantera Attestanter & Behörigheter")
    an = st.text_input("Namn på attestant:", key="an_namn", value=st.session_state["an_namn"])
    ae = st.text_input("E-post till attestant:", key="an_mail", value=st.session_state["an_mail"])
    al = st.multiselect("Välj lag/aktiviteter:", options=st.session_state["lag"], key="an_lag_widget", default=st.session_state["an_lag"])

    if st.button("Spara attestant", key="as_att"):
        if an and ae and al:
            st.session_state["attestanter"] = [
                a for a in st.session_state["attestanter"] if a["namn"].lower() != an.strip().lower()
            ]
            st.session_state["attestanter"].append({
                "namn": an.strip(),
                "epost": ae.strip(),
                "lag": al,
            })
            st.session_state["an_namn"], st.session_state["an_mail"], st.session_state["an_lag"] = "", "", []
            save_data()
            st.rerun()

    if st.session_state["attestanter"]:
        st.write("### Registrerade attestanter:")
        for i, att in enumerate(st.session_state["attestanter"]):
            c_txt, c_ed, c_del = st.columns([4, 1, 1])
            c_txt.write(f"👤 **{att['namn']}** ({att['epost']}) - {', '.join(att.get('lag', []))}")
            if c_ed.button("✏️", key=f"ed_{i}"):
                st.session_state["an_namn"] = att["namn"]
                st.session_state["an_mail"] = att["epost"]
                st.session_state["an_lag"] = att.get("lag", [])
                st.rerun()
            if c_del.button("🗑️", key=f"del_{i}"):
                st.session_state["attestanter"].remove(att)
                save_data()
                st.rerun()

    st.divider()
    st.subheader("Användare för login")
    st.caption("Det här styr vilka som kan logga in för att attestera/admin. Lägg in i .streamlit/secrets.toml som en lista av användare.")
    st.code(
        '''
APP_USERS = [
  { username = "christer", password = "byt-mitt-losenord", name = "Christer Sölve", email = "christer@solve.se", role = "admin", lag = ["Herr Elit"] },
  { username = "magnus", password = "byt-mitt-losenord", name = "Magnus Berglund", email = "magnus.berglund@ibklund.se", role = "attestant", lag = ["LundaLägret", "NovaOpen"] }
]
'''
    )
