import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime
from pathlib import Path
from html import escape

import pandas as pd
import requests
import resend
import streamlit as st

st.set_page_config(page_title="IBK Lund", layout="wide")
APP_DIR = Path(__file__).parent
LOGO_CANDIDATES = [
    APP_DIR / "ibk-lund-logo.png",
    APP_DIR / "02-logga-ibk-lund-webb.png",
    APP_DIR / "assets" / "ibk-lund-logo.png",
    APP_DIR / "assets" / "02-logga-ibk-lund-webb.png",
]
LOGO_PATH = next((path for path in LOGO_CANDIDATES if path.is_file()), LOGO_CANDIDATES[0])

st.markdown(
    """
    <style>
    :root {
        --ibk-navy: #171717;
        --ibk-blue: #c3d600;
        --ibk-pale: #f5f7df;
        --ibk-ink: #171717;
    }
    [data-testid="stSidebar"] {
        background: var(--ibk-navy);
    }
    [data-testid="stSidebar"] * {
        color: #ffffff;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        border-radius: 0.5rem;
        padding: 0.25rem 0.4rem;
    }
    h1, h2, h3 {
        color: var(--ibk-navy);
    }
    [data-testid="stAlert"] {
        border-radius: 0.6rem;
    }
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"] {
        background: var(--ibk-navy);
        border-color: var(--ibk-navy);
        color: #ffffff;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover {
        background: var(--ibk-blue);
        border-color: var(--ibk-blue);
        color: #171717;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULT_LAG = ["Dam Elit", "Herr Elit", "Dam div1", "Herr div2", "LundaLägret", "NovaOpen"]
DEFAULT_KONTON = ["5800 Biljetter", "5830 Kost", "5831 Logi", "7330 Bilersättning", "2999 Övrigt"]


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
    return st.session_state.get("anvandare", read_secrets_users())


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 310_000)
    return salt, digest.hex()


def password_matches(user, password):
    if "password_hash" in user and "password_salt" in user:
        _, candidate = hash_password(password, user["password_salt"])
        return hmac.compare_digest(candidate, user["password_hash"])
    return hmac.compare_digest(str(user.get("password", "")), password)


def secret_users_for_storage():
    users = []
    for user in read_secrets_users():
        role = str(user.get("role", "")).strip().lower()
        username = str(user.get("username", "")).strip()
        password = str(user.get("password", ""))
        if not username or not password or role not in {"admin", "attestant"}:
            continue
        salt, digest = hash_password(password)
        users.append({
            "username": username,
            "name": str(user.get("name", username)).strip(),
            "email": str(user.get("email", "")).strip(),
            "role": role,
            "lag": user.get("lag", []) if role == "attestant" else [],
            "password_salt": salt,
            "password_hash": digest,
        })
    return users


def authenticate_user(username, password):
    username = (username or "").strip()
    password = password or ""
    if not username or not password:
        return None

    for user in get_app_users():
        if str(user.get("username", "")).strip().lower() == username.lower():
            role = str(user.get("role", "")).strip().lower()
            if password_matches(user, password) and role in {"admin", "attestant"}:
                return {
                    "username": user.get("username", username),
                    "name": user.get("name", user.get("username", username)),
                    "email": user.get("email", ""),
                    "role": role,
                    "lag": user.get("lag", []) if role == "attestant" else [],
                }
    return None


def apps_script_request(action, **values):
    missing = [key for key in ["APPS_SCRIPT_URL", "APPS_SCRIPT_TOKEN"] if key not in st.secrets]
    if missing:
        raise RuntimeError(f"Saknar Streamlit Secrets: {', '.join(missing)}.")
    response = requests.post(
        st.secrets["APPS_SCRIPT_URL"],
        json={"token": st.secrets["APPS_SCRIPT_TOKEN"], "action": action, **values},
        timeout=120,
    )
    response.raise_for_status()
    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError("Google Apps Script returnerade inte giltig JSON.") from error
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Google Apps Script misslyckades utan felbeskrivning."))
    return result


def load_data():
    default = {
        "lag": DEFAULT_LAG.copy(),
        "konton": DEFAULT_KONTON.copy(),
        "vantande_utlagg": [],
        "godkanda_utlagg": [],
    }
    stored = apps_script_request("loadData").get("data", {})
    if not stored:
        data = {**default, "anvandare": secret_users_for_storage()}
        save_data(data)
        return data
    data = {}
    for key, value in default.items():
        stored_value = stored.get(key)
        data[key] = stored_value if isinstance(stored_value, type(value)) else value
    if "anvandare" not in stored:
        data["anvandare"] = secret_users_for_storage()
        save_data(data)
    elif isinstance(stored["anvandare"], list):
        data["anvandare"] = stored["anvandare"]
        if not data["anvandare"]:
            data["anvandare"] = secret_users_for_storage()
        if "attestanter" in stored:
            save_data(data)
        elif not stored["anvandare"]:
            save_data(data)
    else:
        raise RuntimeError("Användarlistan i Google Sheets har fel format.")
    sensitive_fields = {"bank", "clearing", "kontonummer"}
    removed_bank_data = "bankprofiler" in stored
    for key in ["vantande_utlagg", "godkanda_utlagg"]:
        for expense in data[key]:
            for field in sensitive_fields:
                if field in expense:
                    del expense[field]
                    removed_bank_data = True
    if removed_bank_data:
        save_data(data)
    return data


def save_data(data=None):
    if data is None:
        data = {
            key: st.session_state.get(key, [])
            for key in ["lag", "konton", "vantande_utlagg", "godkanda_utlagg", "anvandare"]
        }
    apps_script_request("saveData", data=data)


def upload_receipt(uploaded_file, expense_id):
    safe_name = Path(uploaded_file.name).name.replace("/", "_").replace("\\", "_")
    return upload_receipt_content(
        uploaded_file.getvalue(),
        safe_name,
        uploaded_file.type or "application/octet-stream",
        expense_id,
    )


def upload_receipt_content(content, original_name, mime_type, expense_id):
    safe_name = Path(original_name).name.replace("/", "_").replace("\\", "_")
    filename = f"utlagg_{expense_id}_{safe_name}"
    result = apps_script_request(
        "uploadReceipt",
        filename=filename,
        mimeType=mime_type,
        content=base64.b64encode(content).decode("ascii"),
    )
    return result["fileId"], result["filename"]


def download_drive_file(file_id):
    result = apps_script_request("downloadReceipt", fileId=file_id)
    return base64.b64decode(result["content"])


def delete_drive_file(file_id):
    apps_script_request("deleteReceipt", fileId=file_id)


try:
    saved_data = load_data()
except Exception as error:
    st.error(f"Kunde inte läsa eller initiera Google Apps Script-lagringen. Kontrollera URL, token och Apps Script-egenskaper: {error}")
    st.stop()
for key, value in saved_data.items():
    st.session_state[key] = value

for key in [
    "bekraftelse_meddelande",
    "mail_fel",
    "auth_user",
    "auth_username",
    "auth_role",
    "auth_lag",
    "camera_round",
]:
    if key not in st.session_state:
        if key in {"auth_lag", "mail_fel"}:
            st.session_state[key] = []
        elif key == "camera_round":
            st.session_state[key] = 0
        else:
            st.session_state[key] = ""


def refresh_authenticated_user():
    username = st.session_state.get("auth_username")
    if not username:
        st.session_state.pop("auth_user", None)
        st.session_state.pop("auth_role", None)
        st.session_state.pop("auth_lag", None)
        return

    configured_user = next(
        (
            user for user in get_app_users()
            if str(user.get("username", "")).strip().lower() == str(username).strip().lower()
        ),
        None,
    )
    if not configured_user:
        for key in ["auth_user", "auth_username", "auth_role", "auth_lag", "auth_email"]:
            st.session_state.pop(key, None)
        return

    role = str(configured_user.get("role", "")).strip().lower()
    if role not in {"admin", "attestant"}:
        for key in ["auth_user", "auth_username", "auth_role", "auth_lag", "auth_email"]:
            st.session_state.pop(key, None)
        return

    st.session_state["auth_user"] = configured_user.get("name", configured_user.get("username"))
    st.session_state["auth_role"] = role
    st.session_state["auth_lag"] = configured_user.get("lag", []) if role == "attestant" else []
    st.session_state["auth_email"] = configured_user.get("email", "")


refresh_authenticated_user()


def send_notification_email(till, namn, lag, belopp, kat, av, expense_id, kommentar):
    if "RESEND_API_KEY" not in st.secrets:
        return False, "RESEND_API_KEY saknas i Streamlit Secrets."
    if "MAIL_FROM" not in st.secrets:
        return False, "MAIL_FROM saknas i Streamlit Secrets."
    if not LOGO_PATH.is_file():
        return False, f"Logotypen saknas: {LOGO_PATH.name}. Lägg den bredvid app.py i GitHub."

    app_url = get_app_base_url()
    msg_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background-color:#171717; border-bottom:6px solid #c3d600; padding:20px; text-align:center; color:white;">
            <img src="cid:ibk-lund-logo" alt="IBK Lund" width="72" style="display:block;margin:0 auto 10px;background:#fff;border-radius:6px;padding:4px;">
            <h2 style="margin:0; font-size:22px; color:#ffffff;">IBK Lund</h2>
            <p style="margin:5px 0 0; opacity:0.9;">Kvitto- & Utläggshantering</p>
        </div>
        <div style="padding:24px; line-height:1.6; color:#333;">
            <p style="font-size:16px; margin-top:0;">Hej <b>{escape(namn)}</b>,</p>
            <p>Ett nytt utlägg väntar på ditt godkännande.</p>
            <div style="background-color:#f7f8ec; border-left:4px solid #c3d600; padding:15px; margin:20px 0; border-radius:4px;">
                <table style="width:100%; border-collapse:collapse;">
                    <tr><td style="padding:5px 0; color:#666; width:120px;"><b>Utläggs-ID:</b></td><td>#{expense_id}</td></tr>
                    <tr><td style="padding:5px 0; color:#666; width:120px;"><b>Inskickat av:</b></td><td>{escape(av)}</td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Lag/Aktivitet:</b></td><td>{escape(lag)}</td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Kategori:</b></td><td>{escape(kat)}</td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Belopp:</b></td><td style="font-size:16px; color:#171717;"><b>{belopp} kr</b></td></tr>
                    <tr><td style="padding:5px 0; color:#666;"><b>Inskickad:</b></td><td>{datetime.now().strftime('%Y-%m-%d')}</td></tr>
                </table>
            </div>
            <p>Vänligen logga in i appen för att granska underlaget, korrigera eventuella uppgifter och attestera utlägget.</p>
            {f'<p><b>Kommentar från den som registrerade:</b> {escape(kommentar)}</p>' if kommentar else ''}
            <div style="text-align:center; margin:30px 0;">
                <a href="{app_url}" style="background-color:#c3d600; color:#171717; padding:12px 30px; text-decoration:none; font-weight:bold; border-radius:5px; display:inline-block;">Gå till appen</a>
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
                "from": st.secrets["MAIL_FROM"],
                "to": till,
                "subject": f"🔔 Utlägg #{expense_id} att attestera - {lag}",
                "html": msg_html,
                "attachments": [
                    {
                        "filename": LOGO_PATH.name,
                        "content": base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii"),
                        "content_type": "image/png",
                        "content_id": "ibk-lund-logo",
                    }
                ],
            }
        )
        return True, ""
    except Exception as error:
        return False, str(error)


if LOGO_PATH.is_file():
    st.sidebar.image(str(LOGO_PATH), width=180)
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
    st.info(
        "ℹ️ Appen samlar inte in bank- eller kontonummer. "
        "Utbetalningsuppgifter lämnas separat enligt föreningens rutin. "
        "Utbetalning sker runt den 25:e varje månad; kvitton efter den 10:e utbetalas nästa månad."
    )
    if st.session_state.get("bekraftelse_meddelande"):
        st.success(st.session_state["bekraftelse_meddelande"])
        st.session_state["bekraftelse_meddelande"] = ""
    if st.session_state.get("mail_fel"):
        st.warning("Utlägget sparades, men e-postnotisen kunde inte skickas: " + "; ".join(st.session_state["mail_fel"]))
        st.session_state["mail_fel"] = []

    st.caption("Ta ett foto av kvittot med kameran, eller välj en befintlig bild eller PDF nedan.")
    camera_receipt = st.camera_input(
        "Fotografera kvitto",
        key=f"receipt_camera_{st.session_state['camera_round']}",
    )

    with st.form("huvud_reg_form", clear_on_submit=True):
        namn_reg = st.text_input("Ditt Namn:")
        lag_reg = st.selectbox("Välj lag / aktivitet:", options=st.session_state["lag"])
        konto_reg = st.selectbox("Välj konto:", options=st.session_state["konton"])
        belopp_reg = st.number_input("Belopp (kr):", min_value=0.0, step=1.0)
        kommentar_reg = st.text_area("Kommentar (valfritt)", max_chars=1000)
        fil_reg = st.file_uploader("Eller välj kvittofil", type=["pdf", "png", "jpg", "jpeg"])
        receipt_file = camera_receipt if camera_receipt is not None else fil_reg

        if st.form_submit_button("Skicka in utlägg", type="primary"):
            if camera_receipt is not None and fil_reg is not None:
                st.error("Välj antingen ett foto från kameran eller en fil, inte båda.")
            elif not namn_reg.strip():
                st.error("Fyll i ditt namn.")
            elif receipt_file is None:
                st.error("Du måste bifoga ett kvitto för att skicka in utlägget.")
            elif receipt_file.size > 10 * 1024 * 1024:
                st.error("Kvittofilen får vara högst 10 MB.")
            elif belopp_reg <= 0:
                st.error("Beloppet måste vara större än 0 kr.")
            else:
                all_expenses = st.session_state["vantande_utlagg"] + st.session_state["godkanda_utlagg"]
                expense_id = max((int(item["id"]) for item in all_expenses), default=0) + 1
                try:
                    file_id, file_name = upload_receipt(receipt_file, expense_id)
                    utl = {
                        "id": expense_id,
                        "namn": namn_reg.strip(),
                        "lag": lag_reg,
                        "kategori": konto_reg,
                        "belopp": float(belopp_reg),
                        "kommentar": kommentar_reg.strip(),
                        "filnamn": file_name,
                        "drive_file_id": file_id,
                        "datum_inskickat": datetime.now().strftime("%Y-%m-%d"),
                    }
                    st.session_state["vantande_utlagg"].append(utl)
                    try:
                        save_data()
                    except Exception:
                        st.session_state["vantande_utlagg"].remove(utl)
                        delete_drive_file(file_id)
                        raise
                except Exception as error:
                    st.error(f"Utlägget kunde inte sparas. Kontrollera Apps Script och Google Sheets/Drive: {error}")
                else:
                    attestants = [
                        user for user in get_app_users()
                        if str(user.get("role", "")).strip().lower() == "attestant"
                        and lag_reg in user.get("lag", [])
                    ]
                    att_namn = []
                    mail_fel = []
                    for att in attestants:
                        att_name = str(att.get("name", att.get("username", ""))).strip()
                        att_email = str(att.get("email", "")).strip()
                        if att_name:
                            att_namn.append(att_name)
                            if not att_email:
                                mail_fel.append(f"{att_name}: e-postadress saknas i användarinställningarna.")
                                continue
                            sent, mail_error = send_notification_email(
                                att_email, att_name, lag_reg, belopp_reg, konto_reg, namn_reg.strip(),
                                expense_id, kommentar_reg.strip()
                            )
                            if not sent:
                                mail_fel.append(f"{att_name}: {mail_error}")

                    st.session_state["mail_fel"] = mail_fel
                    if att_namn:
                        st.session_state["bekraftelse_meddelande"] = f"✅ Registrerat! Väntar på attest av {' & '.join(att_namn)}."
                    else:
                        st.session_state["bekraftelse_meddelande"] = "✅ Registrerat! (Ingen attestant kopplad)."
                    if camera_receipt is not None:
                        st.session_state["camera_round"] += 1
                    st.rerun()

elif page == "✅ Attestfunktion":
    if "auth_user" not in st.session_state or not st.session_state.get("auth_user"):
        render_login_panel()

    if st.session_state.get("auth_role") != "attestant":
        st.warning("🔒 Attestering kräver en separat användare med rollen attestant.")
        st.stop()

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
            st.write(
                f"**Utlägg #{u['id']}** — inskickat {u.get('datum_inskickat', 'okänt datum')}  \n"
                f"**Från:** {u['namn']} | **Lag/aktivitet:** {u['lag']} | "
                f"**Belopp:** {u['belopp']} kr | **Konto:** {u['kategori']}"
            )
            if u.get("kommentar"):
                st.info(f"**Kommentar från den som registrerade:** {u['kommentar']}")
            try:
                receipt_bytes = download_drive_file(u["drive_file_id"])
                st.download_button(
                    "Hämta kvitto för granskning",
                    data=receipt_bytes,
                    file_name=u["filnamn"],
                    mime="application/pdf" if u["filnamn"].lower().endswith(".pdf") else "image/*",
                    key=f"receipt_{u['id']}",
                )
                if u["filnamn"].lower().endswith((".png", ".jpg", ".jpeg")):
                    st.image(receipt_bytes, caption=u["filnamn"], width=500)
            except Exception as error:
                st.error(f"Kunde inte läsa kvittot från privat Drive-lagring: {error}")

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
                try:
                    save_data()
                    st.rerun()
                except Exception as error:
                    st.error(f"Utlägget attesterades men kunde inte sparas: {error}")

            if col_b.button(f"Radera #{u['id']}", key=f"r_{u['id']}"):
                try:
                    delete_drive_file(u["drive_file_id"])
                    st.session_state["vantande_utlagg"].remove(u)
                    save_data()
                    st.rerun()
                except Exception as error:
                    st.error(f"Kunde inte radera utlägget eller kvittot från lagringen: {error}")

    st.subheader("Attesterade utlägg")
    approved_for_user = [u for u in st.session_state["godkanda_utlagg"] if u["lag"] in access_lag]
    df = pd.DataFrame(approved_for_user)
    if not df.empty:
        cols = ["id", "namn", "lag", "kategori", "belopp", "attesterat_av", "datum_attesterat", "kvitto_mailat_till_spiris"]
        st.dataframe(df.reindex(columns=cols))
        st.caption(
            "Periodens kvitton mejlas till Spiris och sammanställningen med kvitton "
            "mejlas till ekonomi@ibklund.se den 11:e varje månad."
        )
    else:
        st.info("Inga godkända utlägg ännu.")

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

    st.subheader("Hantera behörigheter och användare")
    st.caption(
        "Lägg till inloggningar här. Behörighet och attestlag sparas i den permanenta appdatabasen. "
        "Lösenord lagras som saltade hashvärden. APP_USERS i Secrets används endast för första uppstarten."
    )
    configured_users = get_app_users()
    if configured_users:
        for user_index, user in enumerate(configured_users):
            role = str(user.get("role", "")).strip().lower()
            display_name = user.get("name", user.get("username", "Okänd"))
            email = user.get("email", "")
            teams = user.get("lag", []) if role == "attestant" else []
            username = user.get("username", "")
            suffix = f" — {email}" if email else ""
            if role == "attestant":
                suffix += f" — lag: {', '.join(teams)}"
            with st.expander(f"{display_name} (`{username}`, {role}){suffix}"):
                with st.form(f"edit_app_user_{user_index}"):
                    st.markdown("#### Redigera användare")
                    edit_username = st.text_input(
                        "Användarnamn",
                        value=str(user.get("username", "")),
                        key=f"edit_username_{user_index}",
                    )
                    edit_name = st.text_input(
                        "Namn",
                        value=str(user.get("name", "")),
                        key=f"edit_name_{user_index}",
                    )
                    edit_email = st.text_input(
                        "E-post",
                        value=str(user.get("email", "")),
                        key=f"edit_email_{user_index}",
                    )
                    edit_role = st.selectbox(
                        "Roll",
                        options=["attestant", "admin"],
                        index=0 if role == "attestant" else 1,
                        key=f"edit_role_{user_index}",
                    )
                    edit_teams = st.multiselect(
                        "Lag/aktiviteter (gäller endast attestanter)",
                        options=st.session_state["lag"],
                        default=[team for team in teams if team in st.session_state["lag"]],
                        key=f"edit_teams_{user_index}",
                    )
                    edit_password = st.text_input(
                        "Nytt lösenord (lämna tomt för att behålla nuvarande)",
                        type="password",
                        key=f"edit_password_{user_index}",
                    )
                    edit_password_confirm = st.text_input(
                        "Upprepa nytt lösenord",
                        type="password",
                        key=f"edit_password_confirm_{user_index}",
                    )
                    save_user_changes = st.form_submit_button("Spara ändringar")

                if save_user_changes:
                    normalized_username = edit_username.strip().lower()
                    last_admin = role == "admin" and sum(
                        str(existing.get("role", "")).strip().lower() == "admin"
                        for existing in configured_users
                    ) == 1
                    if not normalized_username or not edit_name.strip():
                        st.error("Fyll i användarnamn och namn.")
                    elif not re.fullmatch(r"[a-zA-Z0-9._-]{3,50}", normalized_username):
                        st.error("Användarnamnet ska vara 3–50 tecken och bara innehålla bokstäver, siffror, punkt, bindestreck eller understreck.")
                    elif any(
                        index != user_index
                        and str(existing.get("username", "")).strip().lower() == normalized_username
                        for index, existing in enumerate(configured_users)
                    ):
                        st.error("Det användarnamnet finns redan.")
                    elif edit_role == "attestant" and (
                        not edit_email.strip()
                        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", edit_email.strip())
                        or not edit_teams
                    ):
                        st.error("Attestanter behöver en giltig e-postadress och minst ett lag/aktivitet.")
                    elif last_admin and edit_role != "admin":
                        st.error("Den sista adminanvändaren kan inte göras om till attestant.")
                    elif bool(edit_password) != bool(edit_password_confirm):
                        st.error("Fyll i båda lösenordsfälten för att byta lösenord.")
                    elif edit_password and len(edit_password) < 12:
                        st.error("Det nya lösenordet måste vara minst 12 tecken.")
                    elif edit_password and edit_password != edit_password_confirm:
                        st.error("De nya lösenorden stämmer inte överens.")
                    else:
                        updated_user = {
                            **user,
                            "username": normalized_username,
                            "name": edit_name.strip(),
                            "email": edit_email.strip(),
                            "role": edit_role,
                            "lag": edit_teams if edit_role == "attestant" else [],
                        }
                        if edit_password:
                            salt, digest = hash_password(edit_password)
                            updated_user.pop("password", None)
                            updated_user["password_salt"] = salt
                            updated_user["password_hash"] = digest

                        st.session_state["anvandare"][user_index] = updated_user
                        try:
                            save_data()
                            if st.session_state.get("auth_username", "").lower() == str(user.get("username", "")).lower():
                                st.session_state["auth_username"] = normalized_username
                            st.success(f"Uppgifterna för {edit_name.strip()} sparades.")
                            st.rerun()
                        except Exception as error:
                            st.session_state["anvandare"][user_index] = user
                            st.error(f"Ändringarna kunde inte sparas: {error}")

                with st.form(f"delete_app_user_{user_index}"):
                    confirm_delete = st.checkbox(
                        f"Bekräfta att {display_name} ska tas bort",
                        key=f"confirm_delete_{user_index}",
                    )
                    delete_user = st.form_submit_button("Ta bort användare")

                if delete_user:
                    if not confirm_delete:
                        st.error("Bekräfta borttagningen genom att markera rutan.")
                    elif role == "admin" and sum(
                        str(existing.get("role", "")).strip().lower() == "admin"
                        for existing in configured_users
                    ) <= 1:
                        st.error("Den sista adminanvändaren kan inte tas bort.")
                    else:
                        removed_user = st.session_state["anvandare"].pop(user_index)
                        try:
                            save_data()
                            st.success(f"Användaren {display_name} togs bort.")
                            st.rerun()
                        except Exception as error:
                            st.session_state["anvandare"].insert(user_index, removed_user)
                            st.error(f"Användaren kunde inte tas bort: {error}")
    else:
        st.warning("Inga användare är konfigurerade. Kontrollera att en första admin finns i APP_USERS i Streamlit Secrets.")

    with st.form("add_app_user_form", clear_on_submit=True):
        st.markdown("#### Lägg till användare")
        new_username = st.text_input("Användarnamn")
        new_name = st.text_input("Namn")
        new_email = st.text_input("E-post (krävs för attestantnotiser)")
        new_role = st.selectbox("Roll", options=["attestant", "admin"])
        new_teams = st.multiselect(
            "Lag/aktiviteter (gäller endast attestanter)",
            options=st.session_state["lag"],
        )
        new_password = st.text_input("Lösenord (minst 12 tecken)", type="password")
        new_password_confirm = st.text_input("Upprepa lösenord", type="password")
        add_user = st.form_submit_button("Skapa användare", type="primary")

    if add_user:
        username_normalized = new_username.strip().lower()
        if not username_normalized or not new_name.strip():
            st.error("Fyll i användarnamn och namn.")
        elif not re.fullmatch(r"[a-zA-Z0-9._-]{3,50}", username_normalized):
            st.error("Användarnamnet ska vara 3–50 tecken och bara innehålla bokstäver, siffror, punkt, bindestreck eller understreck.")
        elif any(
            str(user.get("username", "")).strip().lower() == username_normalized
            for user in get_app_users()
        ):
            st.error("Det användarnamnet finns redan.")
        elif new_role == "attestant" and (
            not new_email.strip()
            or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", new_email.strip())
            or not new_teams
        ):
            st.error("Attestanter behöver en giltig e-postadress och minst ett lag/aktivitet.")
        elif len(new_password) < 12:
            st.error("Lösenordet måste vara minst 12 tecken.")
        elif new_password != new_password_confirm:
            st.error("Lösenorden stämmer inte överens.")
        else:
            salt, password_hash = hash_password(new_password)
            new_user = {
                "username": username_normalized,
                "name": new_name.strip(),
                "email": new_email.strip(),
                "role": new_role,
                "lag": new_teams if new_role == "attestant" else [],
                "password_salt": salt,
                "password_hash": password_hash,
            }
            st.session_state["anvandare"].append(new_user)
            try:
                save_data()
                st.success(f"Användaren {new_name.strip()} skapades.")
                st.rerun()
            except Exception as error:
                st.session_state["anvandare"].remove(new_user)
                st.error(f"Användaren kunde inte sparas: {error}")
