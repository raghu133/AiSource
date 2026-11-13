import os
import sys
import sqlite3
from datetime import datetime

from machine_id import get_machine_id
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication, QMessageBox

# ================= PATHS =================

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = get_app_dir()
DB_FILE = os.path.join(APP_DIR, "license_db.sqlite")
if not os.path.exists(DB_FILE) and getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    bundled_db = os.path.join(sys._MEIPASS, "license_db.sqlite")
    if os.path.exists(bundled_db):
        try:
            import shutil
            shutil.copy2(bundled_db, DB_FILE)
        except Exception:
            DB_FILE = bundled_db

ENV_FILE = os.path.join(APP_DIR, ".env")

def _load_env_files() -> None:
    candidates = [
        os.path.join(APP_DIR, ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, ".env"))
    seen = set()
    for env_path in candidates:
        norm = os.path.normcase(os.path.abspath(env_path))
        if norm in seen:
            continue
        seen.add(norm)
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)

_load_env_files()

# ================= QT POPUPS =================

# def _popup(kind, title, msg):
#     app = QApplication.instance()
#     if app is None:
#         app = QApplication(sys.argv)

#     if kind == "error":
#         QMessageBox.critical(None, title, msg)
#     elif kind == "warning":
#         QMessageBox.warning(None, title, msg)

def _popup(kind, title, msg):
    app = QApplication.instance()

    if app is None:
        print(f"{title}: {msg}")
        return

    box = QMessageBox()
    box.setWindowTitle(title)
    box.setText(msg)

    if kind == "error":
        box.setIcon(QMessageBox.Critical)
    else:
        box.setIcon(QMessageBox.Warning)

    box.setStandardButtons(QMessageBox.Ok)
    box.exec()




def block_and_exit(msg):
    _popup("error", "License Error", msg)
    raise SystemExit(1)


def warn(msg):
    _popup("warning", "License Warning", msg)

# ================= LOAD SECRET =================

def load_secret():
    if not os.path.exists(DB_FILE):
        block_and_exit(
            "License system not initialized.\nContact administrator."
        )
    row = None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT secret FROM app_secret WHERE id=1")
        row = cur.fetchone()
        con.close()
    except sqlite3.OperationalError:
        row = None
    except Exception:
        row = None

    if row and row[0]:
        return str(row[0]).encode()

    env_secret = os.getenv("FERNET_SECRET")
    if env_secret:
        return env_secret.encode()

    block_and_exit(
        "Secret key not found (app_secret/FERNET_SECRET).\nContact administrator."
    )


def load_latest_license_from_db():
    if not os.path.exists(DB_FILE):
        return None
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT license_code FROM licenses ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        con.close()
        if row and row[0]:
            return str(row[0]).strip()
    except Exception:
        return None
    return None

# ================= LICENSE VALIDATION =================

def validate_license(code, fernet):
    try:
        decrypted = fernet.decrypt(code.encode()).decode()
        machine_id, expiry = decrypted.split("|")

        if machine_id != get_machine_id():
            return False, "This license does not belong to this computer.", 0

        expiry_date = datetime.fromisoformat(expiry).date()
        today = datetime.now().date()
        days_left = (expiry_date - today).days

        if days_left < 0:
            return False, "License expired.\nPlease contact administrator.", 0

        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute(
            "SELECT id FROM licenses WHERE license_code=? AND machine_id=?",
            (code, machine_id)
        )
        row = cur.fetchone()
        con.close()

        if not row:
            return False, "License not registered.\nContact administrator.", 0

        return True, "OK", days_left

    except Exception:
        return False, "Invalid or tampered license.", 0

# ================= ENFORCE LICENSE =================

def enforce_license():
    code = os.getenv("LICENSE_SECRET")
    if not code:
        code = load_latest_license_from_db()

    # 🔥 THIS WILL NOW ALWAYS SHOW MESSAGE
    if not code:
        block_and_exit(
            "License not found (LICENSE_SECRET).\nPlease contact administrator."
        )

    secret = load_secret()
    fernet = Fernet(secret)

    valid, message, days_left = validate_license(code, fernet)

    if not valid:
        block_and_exit(message)

    if 0 < days_left <= 30:
        warn(f"⚠️ Your license will expire in {days_left} day(s).")
    elif days_left == 0:
        warn("⚠️ Your license expires TODAY!")

    return True
