import os
import sys
import sqlite3
import hashlib
import uuid
import platform
from datetime import datetime
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QTextEdit, QMessageBox, QVBoxLayout, QHBoxLayout, QDateEdit
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QFont


# ======================================================
# PATHS
# ======================================================

# def get_app_dir():
#     base = os.getenv("APPDATA") or os.path.expanduser("~")
#     path = os.path.join(base, "AI_Trainer")
#     os.makedirs(path, exist_ok=True)
#     return path

# APP_DIR = get_app_dir()
# DB_FILE = os.path.join(APP_DIR, "license_db.sqlite")
# ENV_FILE = os.path.join(APP_DIR, ".env")

# ======================================================
# PATHS (EXE FOLDER / SCRIPT FOLDER)
# ======================================================

def get_base_dir():
    if getattr(sys, "frozen", False):
        # Running as EXE
        return os.path.dirname(sys.executable)
    else:
        # Running as Python script
        return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
DB_FILE = os.path.join(BASE_DIR, "license_db.sqlite")
ENV_FILE = os.path.join(BASE_DIR, ".env")

# ======================================================
# LOAD OR CREATE FERNET SECRET (NEXT TO EXE)
# ======================================================

if not os.path.exists(ENV_FILE):
    secret = Fernet.generate_key().decode()
    with open(ENV_FILE, "w") as f:
        f.write(f"FERNET_SECRET={secret}\n")

# load_dotenv(ENV_FILE, override=True)

# FERNET_SECRET = os.getenv("FERNET_SECRET")

# if not FERNET_SECRET:
#     print("FATAL: FERNET_SECRET could not be initialized")
#     raise SystemExit(1)

# ======================================================
# LOAD OR CREATE FERNET SECRET (SAFE)
# ======================================================

def load_or_create_fernet_secret():
    secret = None

    # 1️⃣ If .env exists, read it manually
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("FERNET_SECRET="):
                    secret = line.strip().split("=", 1)[1]
                    break

    # 2️⃣ If not found, generate and APPEND
    if not secret:
        secret = Fernet.generate_key().decode()
        with open(ENV_FILE, "a", encoding="utf-8") as f:
            f.write(f"\nFERNET_SECRET={secret}\n")

    # 3️⃣ Load env vars normally
    load_dotenv(dotenv_path=ENV_FILE, override=True)

    # 4️⃣ Final safety fallback
    os.environ["FERNET_SECRET"] = secret
    return secret


FERNET_SECRET = load_or_create_fernet_secret()
fernet = Fernet(FERNET_SECRET.encode())

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_secret (
            id INTEGER PRIMARY KEY,
            secret TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT,
            license_code TEXT,
            expiry_date TEXT
        )
    """)
    cur.execute("SELECT secret FROM app_secret WHERE id = 1")
    row = cur.fetchone()
    if not row:
        cur.execute(
            "INSERT INTO app_secret(id, secret) VALUES(1, ?)",
            (FERNET_SECRET,)
        )
    elif str(row[0]).strip() != str(FERNET_SECRET).strip():
        cur.execute(
            "UPDATE app_secret SET secret = ? WHERE id = 1",
            (FERNET_SECRET,)
        )
    con.commit()
    con.close()

init_db()



# ======================================================
# MACHINE ID
# ======================================================

def get_machine_id():
    raw = (
        platform.node() +
        platform.system() +
        platform.processor() +
        str(uuid.getnode())
    )
    return hashlib.sha256(raw.encode()).hexdigest()


# ======================================================
# DATABASE INIT
# ======================================================

# def init_db():
#     con = sqlite3.connect(DB_FILE)
#     cur = con.cursor()

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS app_secret (
#             id INTEGER PRIMARY KEY,
#             secret TEXT
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS licenses (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             machine_id TEXT,
#             license_code TEXT,
#             expiry_date TEXT
#         )
#     """)

#     cur.execute("SELECT secret FROM app_secret WHERE id=1")
#     row = cur.fetchone()

#     if not row:
#         secret = Fernet.generate_key().decode()
#         cur.execute(
#             "INSERT INTO app_secret(id, secret) VALUES(1, ?)",
#             (secret,)
#         )
#         con.commit()
#     else:
#         secret = row[0]

#     con.close()
#     return secret.encode()


# SECRET_KEY = init_db()
# fernet = Fernet(SECRET_KEY)


# ======================================================
# LICENSE GENERATION
# ======================================================

def generate_license(machine_id, expiry_date):
    payload = f"{machine_id}|{expiry_date}"
    code = fernet.encrypt(payload.encode()).decode()

    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO licenses(machine_id, license_code, expiry_date) VALUES (?, ?, ?)",
        (machine_id, code, expiry_date)
    )
    con.commit()
    con.close()

    return code


# ======================================================
# LICENSE VALIDATION (USED BY MAIN APP)
# ======================================================

def _popup(kind, title, msg):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    if kind == "error":
        QMessageBox.critical(None, title, msg)
    else:
        QMessageBox.warning(None, title, msg)


def block_and_exit(msg):
    _popup("error", "License Error", msg)
    raise SystemExit(1)


def warn(msg):
    _popup("warning", "License Warning", msg)


def validate_license(code):
    try:
        decrypted = fernet.decrypt(code.encode()).decode()
        mid, expiry = decrypted.split("|")

        if mid != get_machine_id():
            return False, "License does not belong to this computer.", 0

        expiry_date = datetime.fromisoformat(expiry).date()
        today = datetime.now().date()
        days_left = (expiry_date - today).days

        if days_left < 0:
            return False, "License expired.", 0

        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute(
            "SELECT id FROM licenses WHERE license_code=? AND machine_id=?",
            (code, mid)
        )
        exists = cur.fetchone()
        con.close()

        if not exists:
            return False, "License not registered.", 0

        return True, "OK", days_left

    except Exception:
        return False, "Invalid or tampered license.", 0
    

def enforce_license():
    code = os.getenv("LICENSE_SECRET")

    if not code:
        # fallback: get last license from DB
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT license_code FROM licenses ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        con.close()

        if not row:
            block_and_exit("License not found.\nContact administrator.")

        code = row[0]

    valid, msg, days_left = validate_license(code)

    if not valid:
        block_and_exit(msg)

    if 0 < days_left <= 30:
        warn(f"⚠ License expires in {days_left} day(s).")
    elif days_left == 0:
        warn("⚠ License expires TODAY!")

    return True



# def enforce_license():
#     code = os.getenv("LICENSE_SECRET")

#     if not code:
#         block_and_exit("License not found.\nContact administrator.")

#     valid, msg, days_left = validate_license(code)

#     if not valid:
#         block_and_exit(msg)

#     if 0 < days_left <= 30:
#         warn(f"⚠ License expires in {days_left} day(s).")
#     elif days_left == 0:
#         warn("⚠ License expires TODAY!")

#     return True


# ======================================================
# LICENSE GENERATOR UI
# ======================================================

class LicenseGenerator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("License Generator")
        self.setFixedSize(600, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        row_mid = QHBoxLayout()
        lbl_mid = QLabel("Machine ID")
        self.entry_mid = QLineEdit()
        self.entry_mid.setFont(QFont("Consolas", 9))

        btn_fetch = QPushButton("Get This Computer ID")
        btn_fetch.clicked.connect(self.fetch_machine_id)

        row_mid.addWidget(lbl_mid)
        row_mid.addWidget(self.entry_mid)
        row_mid.addWidget(btn_fetch)

        row_exp = QHBoxLayout()
        lbl_exp = QLabel("Expiry Date")
        self.date_expiry = QDateEdit()
        self.date_expiry.setCalendarPopup(True)
        self.date_expiry.setDate(QDate.currentDate().addDays(1))
        self.date_expiry.setDisplayFormat("yyyy-MM-dd")

        row_exp.addWidget(lbl_exp)
        row_exp.addWidget(self.date_expiry)

        btn_generate = QPushButton("Generate License")
        btn_generate.setStyleSheet("background:#3498db;color:white;padding:6px;")
        btn_generate.clicked.connect(self.on_generate)

        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 9))

        layout.addLayout(row_mid)
        layout.addLayout(row_exp)
        layout.addWidget(btn_generate)
        layout.addWidget(self.txt_result)

        self.setLayout(layout)

    def fetch_machine_id(self):
        self.entry_mid.setText(get_machine_id())
        QMessageBox.information(self, "Machine ID", "Machine ID fetched.")

    def on_generate(self):
        mid = self.entry_mid.text().strip()
        expiry = self.date_expiry.date().toString("yyyy-MM-dd")

        if not mid:
            QMessageBox.critical(self, "Error", "Machine ID required")
            return

        if datetime.fromisoformat(expiry) <= datetime.now():
            QMessageBox.critical(self, "Error", "Expiry must be future date")
            return

        code = generate_license(mid, expiry)
        self.txt_result.setPlainText(code)

        QMessageBox.information(
            self,
            "Success",
            f"License generated.\nValid till {expiry}"
        )


# ======================================================
# RUN GENERATOR
# ======================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LicenseGenerator()
    win.show()
    sys.exit(app.exec())
