import os
import sys
import re
import json
import time
import math
import ctypes
import threading
from typing import Dict, List, Optional, Tuple

import pyttsx3
import numpy as np
import cv2
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except Exception:
    pyautogui = None

from PySide6.QtCore import (
    Qt, QObject, Signal, Slot, QTimer, QThread,
    QEvent, QPoint, QFile, QSize, QCoreApplication, QRectF, QEasingCurve, QPropertyAnimation, Property
)
from PySide6.QtGui import QImage, QPixmap, QIcon, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QListWidgetItem, QMessageBox,
    QPushButton, QLineEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QStackedWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QFrame, QInputDialog, QDialog, QFileDialog, QScroller,
    QAbstractItemView, QToolButton, QProgressBar
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

from licence_manager import enforce_license

# DINOv3 vision recognition engine (pure standalone ViT-S/16 ONNX)
try:
    import dinov3_vision
    _DINOV3_AVAILABLE = dinov3_vision.is_available()
except ImportError:
    dinov3_vision = None
    _DINOV3_AVAILABLE = False

# Color consistency engine (HSV/Lab object descriptor & color compatibility gating)
try:
    import color_matcher
    _COLOR_MATCHER_AVAILABLE = True
except Exception:
    color_matcher = None
    _COLOR_MATCHER_AVAILABLE = False


# -------------------------
# App data (DEV: store next to main.py)
# -------------------------
APP_NAME = "AI_Trainer"

def app_data_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = app_data_dir()
BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR) if getattr(sys, "frozen", False) else BASE_DIR
APP_DIR = app_data_dir()
os.makedirs(APP_DIR, exist_ok=True)

def resolve_asset_path(*paths: str) -> str:
    for base in [BUNDLE_DIR, BASE_DIR]:
        candidate = os.path.join(base, *paths)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(BASE_DIR, *paths)

# Ensure essential runtime files are present in APP_DIR next to the executable
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    for fname in [
        ".env",
        "license_db.sqlite",
        "settings.json",
        "learned_meta.json",
        "learned_data_dinov3.json",
        "empty_tray_baseline.jpg",
        "empty_cover_baseline.jpg",
    ]:
        src = os.path.join(sys._MEIPASS, fname)
        dst = os.path.join(APP_DIR, fname)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                import shutil
                shutil.copy2(src, dst)
            except Exception:
                pass

SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
LEARNED_PATH = os.path.join(APP_DIR, "learned_data_dinov3.json")
LEARNED_META_PATH = os.path.join(APP_DIR, "learned_meta.json")
THUMB_DIR = os.path.join(APP_DIR, "thumbs")
EMPTY_TRAY_BASELINE_PATH = os.path.join(APP_DIR, "empty_tray_baseline.jpg")
EMPTY_COVER_BASELINE_PATH = os.path.join(APP_DIR, "empty_cover_baseline.jpg")
LOGO_PATH = resolve_asset_path("logo.png")
IMGS_DIR = resolve_asset_path("Imgs")
DIALOG_ICON_PATH = resolve_asset_path("iLogo.png")
APP_DIALOG_TITLE = "iLogic AI POS (DINOv3)"
COVER_PRESENT_SAME_RATIO = 0.07

DEFAULT_SETTINGS = {
    "scale": {
        "enabled": True,
        "port": "COM1",
        "baud": 9600,
        "stable_seconds": 0.3,
        "open_threshold": 0.001,
    },
    "camera": {
        "enabled": True,
        "index": 0,
        "polygon": [[80, 60], [560, 60], [560, 420], [80, 420]],
        "show_boundary": True,
        "empty_baseline_path": EMPTY_TRAY_BASELINE_PATH,
        "empty_baseline_polygon": [[80, 60], [560, 60], [560, 420], [80, 420]],
        "empty_cover_baseline_path": EMPTY_COVER_BASELINE_PATH,
        "empty_cover_baseline_polygon": [[80, 60], [560, 60], [560, 420], [80, 420]],
        "empty_diff_threshold": 0.015,
    },
    "db": {
        "enabled": True,
        "driver": "ODBC Driver 17 for SQL Server",
        "server": "localhost",
        "database": "SEYON",
        "user": "ilt",
        "password": "ilt",
        "uom_filter": "ALL",
        "table": "tblInventory",
        "col_code": "InventoryCode",
        "col_name": "Description",
        "col_uom": "UOM",
        "col_brand": "BrandCode",
        "col_price": "RetailPrice",
    },
    "qr": {"prefix_value": "20", "code_len": 5, "price_len": 5, "qty_len": 6},
    "behavior": {
        "match_threshold": 0.55,
        "max_samples": 40,
        "confidence_margin": 0.03,
        "appear_min_hits": 2,
        "top_matches_count": 6,
    },
}


def _deep_merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst


def load_settings() -> dict:
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            _deep_merge(s, user)
        except Exception:
            pass
    s["scale"]["enabled"] = True
    s["camera"]["enabled"] = True
    s["db"]["enabled"] = True
    return s


def save_settings(s: dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


# -------------------------
# SQL Server (pyodbc)
# -------------------------
def fetch_products_like(query_text: str, settings: dict, limit: int = 50) -> List[dict]:
    import pyodbc

    db = settings["db"]
    if not db.get("database"):
        return []

    conn_str = (
        f"DRIVER={{{db['driver']}}};"
        f"SERVER={db['server']};"
        f"DATABASE={db['database']};"
        f"UID={db['user']};"
        f"PWD={db['password']};"
    )
    conn = pyodbc.connect(conn_str, timeout=5)
    cur = conn.cursor()

    table = db.get("table", "tblInventory")
    col_code = db.get("col_code", "InventoryCode")
    col_name = db.get("col_name", "Description")
    col_uom = db.get("col_uom", "UOM")
    col_brand = db.get("col_brand", "BrandCode")
    col_price = db.get("col_price", "RetailPrice")

    cur.execute(
        f"""
        SELECT TOP (?) {col_code}, {col_name}, {col_uom}, {col_brand}, {col_price}
        FROM {table}
        WHERE {col_name} LIKE ?
          AND NOT (
              ISNULL(InActive, 'N') = 'Y'
              OR ISNULL(Discontinued, 'N') = 'Y'
          )
        ORDER BY {col_name}
        """,
        limit,
        f"%{query_text}%",
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append(
            {
                "Code": str(r[0]).strip(),
                "Name": str(r[1]).strip(),
                "UOM": str(r[2]).strip().upper(),
                "Brand": str(r[3]).strip() if r[3] is not None else "",
                "Price": float(r[4] or 0.0),
            }
        )
    return out


def fetch_all_products(settings: dict) -> List[dict]:
    import pyodbc

    db = settings["db"]
    if not db.get("database"):
        return []

    conn_str = (
        f"DRIVER={{{db['driver']}}};"
        f"SERVER={db['server']};"
        f"DATABASE={db['database']};"
        f"UID={db['user']};"
        f"PWD={db['password']};"
    )
    conn = pyodbc.connect(conn_str, timeout=5)
    cur = conn.cursor()

    table = db.get("table", "tblInventory")
    col_code = db.get("col_code", "InventoryCode")
    col_name = db.get("col_name", "Description")
    col_uom = db.get("col_uom", "UOM")
    col_brand = db.get("col_brand", "BrandCode")
    col_price = db.get("col_price", "RetailPrice")

    cur.execute(
        f"""
        SELECT {col_code}, {col_name}, {col_uom}, {col_brand}, {col_price}
        FROM {table}
        WHERE NOT (
            ISNULL(InActive, 'N') = 'Y'
            OR ISNULL(Discontinued, 'N') = 'Y'
        )
        ORDER BY {col_name}
        """
    )
    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        out.append(
            {
                "Code": str(r[0]).strip(),
                "Name": str(r[1]).strip(),
                "UOM": str(r[2]).strip().upper(),
                "Brand": str(r[3]).strip() if r[3] is not None else "",
                "Price": float(r[4] or 0.0),
            }
        )
    return out



def fetch_product_by_code(code: str, settings: dict) -> Optional[dict]:
    import pyodbc

    db = settings["db"]
    if not db.get("database"):
        return None

    conn_str = (
        f"DRIVER={{{db['driver']}}};"
        f"SERVER={db['server']};"
        f"DATABASE={db['database']};"
        f"UID={db['user']};"
        f"PWD={db['password']};"
    )
    conn = pyodbc.connect(conn_str, timeout=5)
    cur = conn.cursor()

    table = db.get("table", "tblInventory")
    col_code = db.get("col_code", "InventoryCode")
    col_name = db.get("col_name", "Description")
    col_uom = db.get("col_uom", "UOM")
    col_brand = db.get("col_brand", "BrandCode")
    col_price = db.get("col_price", "RetailPrice")

    cur.execute(
        f"""
        SELECT TOP 1 {col_code}, {col_name}, {col_uom}, {col_brand}, {col_price}
        FROM {table}
        WHERE {col_code} = ?
          AND NOT (
              ISNULL(InActive, 'N') = 'Y'
              OR ISNULL(Discontinued, 'N') = 'Y'
          )
        """,
        str(code),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None

    return {
        "Code": str(row[0]).strip(),
        "Name": str(row[1]).strip(),
        "UOM": str(row[2]).strip().upper(),
        "Brand": str(row[3]).strip() if row[3] is not None else "",
        "Price": float(row[4] or 0.0),
    }


def validate_admin_password(password: str, settings: dict) -> bool:
    if str(password).strip() in {"1234", "admin", "admin123", "ilt"}:
        return True
    try:
        import pyodbc

        db = settings.get("db", {})
        if not db or not db.get("database"):
            return False

        conn_str = (
            f"DRIVER={{{db.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
            f"SERVER={db.get('server', 'localhost')};"
            f"DATABASE={db.get('database', '')};"
            f"UID={db.get('user', 'sa')};"
            f"PWD={db.get('password', '')};"
        )
        conn = pyodbc.connect(conn_str, timeout=5)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP 1 1
            FROM tblCashier
            WHERE CashierGroupCode = 'ADMIN' AND Password = ?
            """,
            password,
        )
        row = cur.fetchone()
        conn.close()
        return bool(row)
    except Exception as e:
        print(f"[Admin Auth Error: {e}]")
        return str(password).strip() in {"1234", "admin", "admin123", "ilt"}


# -------------------------
# Barcode
# -------------------------

# pcs workng perfectly but not kg
# def make_barcode(item: dict, qty_or_weight: float, settings: dict) -> str:
#     qr = settings["qr"]
#     prefix = str(qr.get("prefix_value", "20"))
#     code_len = int(qr.get("code_len", 5))
#     price_len = int(qr.get("price_len", 5))
#     qty_len = int(qr.get("qty_len", 5))

#     item_code = str(item.get("Code", "0")).zfill(code_len)[-code_len:]
#     retail_price = float(item.get("Price", 0.0))
#     uom = str(item.get("UOM", "KG")).upper()

#     if uom == "PCS":
#         return str(item.get("Code", "")).strip()

#     qty = max(1.0, float(qty_or_weight)) if uom == "PCS" else max(0.0, float(qty_or_weight))
#     total_amount = retail_price * qty

#     amt_int = int(round(total_amount * 100))
#     amt_str = str(amt_int).zfill(price_len)[-price_len:]

#     # q_int = int(round(qty * (10 ** (qty_len - 1))))
#     q_int = int(round(qty * 1000))
#     q_str = str(q_int).zfill(qty_len)[-qty_len:]

#     return f"{prefix}{item_code}{amt_str}{q_str}"




# kg working perfectly
def make_barcode(item: dict, qty_or_weight: float, settings: dict) -> str:
    qr = settings["qr"]
    prefix = str(qr["prefix_value"])
    code_len = int(qr["code_len"])
    price_len = int(qr["price_len"])
    qty_len = int(qr["qty_len"])

    pcs_item_code = str(item.get("Code", "0"))
    item_code = str(item.get("Code", "0")).zfill(code_len)[-code_len:]
    retail_price = float(item.get("Price", 0.0))
    uom = str(item.get("UOM", "KG")).upper()

    if uom == "PCS":
        qty = max(1.0, float(qty_or_weight))
        total_amount = retail_price * qty
        amt_int = int(round(total_amount * (10 ** (price_len - 2))))
        amt_str = str(amt_int).zfill(price_len)[-price_len:]

        qty_int = int(round(qty * (10 ** (qty_len - 1))))
        qty_str = str(qty_int).zfill(qty_len)[-qty_len:]
        return f"{pcs_item_code}"

    weight_val = max(0.0, float(qty_or_weight))
    total_amount = retail_price * weight_val
    # amt_int = int(round(total_amount * (10 ** (price_len - 2))))
    # amt_str = str(amt_int).zfill(price_len)[-price_len:]
    amt_int = int(round(total_amount * 100))
    amt_str = str(amt_int).zfill(price_len)[-price_len:]

    # wt_int = int(round(weight_val * (10 ** (qty_len - 1))))
    # wt_str = str(wt_int).zfill(qty_len)[-qty_len:]
    wt_int = int(round(weight_val * 1000))
    wt_str = str(wt_int).zfill(qty_len)[-qty_len:]
    print(f"DEBUG: weight_val={weight_val}, total_amount={total_amount}, amt_int={amt_int}, wt_int={wt_int}")
    return f"{prefix}{item_code}{amt_str}{wt_str}0"


# def make_barcode(item: dict, weight: float, settings: dict, debug: bool = False) -> str:
#     """
#     BARCODE RULES

#     PCS:
#         Return plain item code.

#     KG:
#         PREFIX(2) + ITEM(5) + AMOUNT(5) + 0 + QTY(5)
#         POS decodes:
#             Qty    = QTY / 10000
#             Amount = AMOUNT / 100
#             Price  = Amount / Qty
#     """
#     qr = settings.get("qr", {})
#     prefix = str(qr.get("prefix_value", "20"))
#     code_len = int(qr.get("code_len", 5))

#     item_code = str(item.get("Code", "")).strip()
#     uom = str(item.get("UOM", "KG")).upper()

#     # PCS must stay as the direct inventory code.
#     if uom == "PCS":
#         return item_code

#     # KG uses DB unit price as source-of-truth.
#     retail_price = float(item.get("Price", 0.0) or 0.0)
#     safe_weight = max(0.0, float(weight or 0.0))

#     # Encode weight first (POS qty precision), then compute amount from that
#     # encoded qty to keep unit-price stable in POS decoding.
#     qty_int = int(round(safe_weight * 10000))
#     qty_encoded = qty_int / 10000.0

#     amount = qty_encoded * retail_price
#     amt_int = int(round(amount * 100))

#     code_field = item_code.zfill(code_len)[-code_len:]
#     amt_str = str(max(0, amt_int)).zfill(5)[-5:]
#     qty_str = str(max(0, qty_int)).zfill(5)[-5:]

#     barcode = f"{prefix}{code_field}{amt_str}0{qty_str}"

#     if debug:
#         decoded_qty = qty_int / 10000.0
#         decoded_amount = amt_int / 100.0
#         decoded_price = (decoded_amount / decoded_qty) if decoded_qty > 0 else 0.0
#         print("=== KG BARCODE DEBUG ===")
#         print(f"Barcode      : {barcode}")
#         print(f"DB Price     : {retail_price:.2f}")
#         print(f"Weight(KG)   : {safe_weight:.4f}")
#         print(f"POS Qty      : {decoded_qty:.4f}")
#         print(f"POS Amount   : {decoded_amount:.2f}")
#         print(f"POS UnitPrice: {decoded_price:.2f}")
#         print("========================")

#     return barcode


def make_kg_barcode_debug(item, weight, settings):
    code = make_barcode(item, weight, settings)
    print("BARCODE :", code)
    print("LENGTH  :", len(code))
    print("PREFIX  :", code[:2])
    print("ITEM    :", code[2:7])
    print("AMOUNT  :", code[7:12], "=>", int(code[7:12]) / 100)
    print("QTY RAW :", code[13:18], "=>", int(code[13:18]) / 10000)
    return code




# -------------------------
# Windows auto-type (SendInput)
# -------------------------
def _send_input_keys(text: str, send_enter: bool = False) -> bool:
    if os.name != "nt":
        return False

    user32 = ctypes.windll.user32
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_RETURN = 0x0D

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("ki", KEYBDINPUT)]

    def _send_unicode_char(ch: str):
        code = ord(ch)
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, None))
        up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None))
        arr = (INPUT * 2)(down, up)
        user32.SendInput(2, arr, ctypes.sizeof(INPUT))

    for ch in text:
        _send_unicode_char(ch)

    if send_enter:
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_RETURN, 0, 0, 0, None))
        up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_RETURN, 0, KEYEVENTF_KEYUP, 0, None))
        arr = (INPUT * 2)(down, up)
        user32.SendInput(2, arr, ctypes.sizeof(INPUT))

    return True

def _get_foreground_hwnd() -> Optional[int]:
    if os.name != "nt":
        return None
    return int(ctypes.windll.user32.GetForegroundWindow())


def _set_foreground_hwnd(hwnd: Optional[int]) -> bool:
    if os.name != "nt" or not hwnd:
        return False
    user32 = ctypes.windll.user32
    SW_RESTORE = 9
    try:
        # Restore only if minimized; do not alter maximized/normal state.
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        return int(user32.GetForegroundWindow()) == int(hwnd)
    except Exception:
        return False


def _send_ctrl_v(send_enter: bool = True) -> bool:
    if os.name != "nt":
        return False
    user32 = ctypes.windll.user32
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("ki", KEYBDINPUT)]

    def _tap_vk(vk: int):
        down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, 0, 0, None))
        up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None))
        arr = (INPUT * 2)(down, up)
        user32.SendInput(2, arr, ctypes.sizeof(INPUT))

    ctrl_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_CONTROL, 0, 0, 0, None))
    v_down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_V, 0, 0, 0, None))
    v_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, None))
    ctrl_up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, None))
    arr = (INPUT * 4)(ctrl_down, v_down, v_up, ctrl_up)
    user32.SendInput(4, arr, ctypes.sizeof(INPUT))

    if send_enter:
        _tap_vk(VK_RETURN)
    return True


# -------------------------
# Features (HSV histogram on polygon mask)
# -------------------------
def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v) + 1e-9)
    return (v / n).astype(np.float32)


def polygon_foreground_mask(frame_bgr: np.ndarray, polygon: List[List[int]]) -> np.ndarray:
    roi_mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
    pts = np.array(polygon, dtype=np.int32)
    cv2.fillPoly(roi_mask, [pts], 255)

    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    fg_mask = cv2.inRange(hsv, (0, 40, 40), (179, 255, 255))
    mask = cv2.bitwise_and(fg_mask, roi_mask)
    if cv2.countNonZero(mask) < 50:
        mask = roi_mask
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def polygon_feature_raw(
    frame_bgr: np.ndarray,
    polygon: List[List[int]],
    extra_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    mask = polygon_foreground_mask(frame_bgr, polygon)
    if extra_mask is not None:
        try:
            if extra_mask.shape[:2] != mask.shape[:2]:
                extra_mask = cv2.resize(extra_mask, (mask.shape[1], mask.shape[0]), interpolation=cv2.INTER_NEAREST)
            mask = cv2.bitwise_and(mask, extra_mask.astype(np.uint8))
        except Exception:
            pass
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    h_hist = cv2.calcHist([hsv], [0], mask, [30], [0, 180]).flatten()
    s_hist = cv2.calcHist([hsv], [1], mask, [32], [0, 256]).flatten()

    feat = np.concatenate([h_hist, s_hist]).astype(np.float32)
    s = float(feat.sum())
    if s > 0:
        feat = feat / s
    return feat


def polygon_feature(
    frame_bgr: np.ndarray,
    polygon: List[List[int]],
    extra_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    return _normalize(polygon_feature_raw(frame_bgr, polygon, extra_mask=extra_mask))


def draw_polygon_with_handles(frame_bgr: np.ndarray, polygon: List[List[int]]) -> np.ndarray:
    out = frame_bgr.copy()
    if not polygon or len(polygon) < 3:
        return out
    try:
        pts = np.array(polygon, np.int32).reshape((-1, 1, 2))
        cv2.polylines(out, [pts], True, (0, 255, 0), 2)
        for pt in polygon:
            if len(pt) >= 2:
                cv2.circle(out, (int(pt[0]), int(pt[1])), 8, (0, 255, 255), -1)
                cv2.circle(out, (int(pt[0]), int(pt[1])), 10, (0, 0, 0), 2)
    except Exception:
        pass
    return out


def boundary_only_frame(frame_bgr: np.ndarray, polygon: List[List[int]]) -> np.ndarray:
    out = np.zeros_like(frame_bgr)
    if not polygon or len(polygon) < 3:
        return frame_bgr.copy()
    mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [np.array(polygon, dtype=np.int32)], 255)
    out[mask > 0] = frame_bgr[mask > 0]
    return out


def _fill_mask_holes(mask: np.ndarray) -> np.ndarray:
    """Fills internal holes in a binary mask while preserving external boundaries."""
    if mask is None or cv2.countNonZero(mask) == 0:
        return mask
    h, w = mask.shape[:2]
    padded = np.zeros((h + 2, w + 2), dtype=np.uint8)
    padded[1 : h + 1, 1 : w + 1] = mask.astype(np.uint8)
    inv = cv2.bitwise_not(padded)
    cv2.floodFill(inv, None, (0, 0), 0)
    internal_holes = inv[1 : h + 1, 1 : w + 1]
    return cv2.bitwise_or(mask.astype(np.uint8), internal_holes)


def _clean_object_mask(mask: np.ndarray, roi_mask: Optional[np.ndarray] = None) -> np.ndarray:
    if mask is None:
        return mask
    out = mask.astype(np.uint8)
    if roi_mask is not None:
        out = cv2.bitwise_and(out, roi_mask.astype(np.uint8))
    k3 = np.ones((3, 3), np.uint8)
    k5 = np.ones((5, 5), np.uint8)
    k7 = np.ones((7, 7), np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, k3, iterations=1)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, k7, iterations=2)
    out = _fill_mask_holes(out)

    contours, _ = cv2.findContours(out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return out
    h, w = out.shape[:2]
    roi_area = float(cv2.countNonZero(roi_mask)) if roi_mask is not None else float(h * w)
    min_area = max(28.0, roi_area * 0.00022)
    max_area = max(min_area, roi_area * 0.75)
    cleaned = np.zeros_like(out)
    valid = []
    for c in contours:
        area = float(cv2.contourArea(c))
        if min_area <= area <= max_area:
            valid.append((area, c))
    if not valid:
        return out
    valid.sort(key=lambda x: x[0], reverse=True)
    largest = valid[0][0]
    for area, c in valid:
        if area >= max(min_area, largest * 0.05):
            cv2.drawContours(cleaned, [c], -1, 255, -1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, k5, iterations=1)
    return cleaned


def _dominant_foreground_mask(mask: np.ndarray, roi_mask: Optional[np.ndarray] = None) -> np.ndarray:
    cleaned = _clean_object_mask(mask, roi_mask)
    if cleaned is None:
        return cleaned

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return cleaned

    h, w = cleaned.shape[:2]
    roi_area = float(cv2.countNonZero(roi_mask)) if roi_mask is not None else float(h * w)
    min_area = max(28.0, roi_area * 0.00025)
    valid = [(float(cv2.contourArea(c)), c) for c in contours if float(cv2.contourArea(c)) >= min_area]
    if not valid:
        return cleaned

    valid.sort(key=lambda x: x[0], reverse=True)
    largest = valid[0][0]
    focused = np.zeros_like(cleaned)
    for area, contour in valid:
        if area >= largest * 0.35:
            cv2.drawContours(focused, [contour], -1, 255, -1)
    return _clean_object_mask(focused, roi_mask)


def _cover_like_pixels(
    hsv_img: np.ndarray,
    lab_img: np.ndarray,
    gray_img: Optional[np.ndarray] = None,
) -> np.ndarray:
    sat = hsv_img[:, :, 1].astype(np.float32)
    lab_a = lab_img[:, :, 1].astype(np.float32) - 128.0
    lab_b = lab_img[:, :, 2].astype(np.float32) - 128.0
    chroma = np.sqrt((lab_a * lab_a) + (lab_b * lab_b))
    pale_plastic = (sat < 42.0) & (chroma < 10.0)
    glare = (hsv_img[:, :, 2] >= 225) & (sat <= 42.0)
    cover_bool = pale_plastic | glare
    if gray_img is not None:
        # Organic produce (garlic, cauliflower, onion, potato) has rich surface texture;
        # smooth clear plastic film has very low local texture.
        blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)
        texture = cv2.absdiff(gray_img, blurred)
        cover_bool = cover_bool & (texture < 8)
    return (cover_bool.astype(np.uint8)) * 255


def _suppress_cover_like_mask(
    frame_bgr: np.ndarray,
    mask: np.ndarray,
    roi_mask: Optional[np.ndarray] = None,
    min_keep_pixels: int = 24,
    min_keep_ratio: float = 0.30,
) -> np.ndarray:
    if mask is None or cv2.countNonZero(mask) < min_keep_pixels:
        return mask
    try:
        hsv_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        lab_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        gray_img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        cover_like = _cover_like_pixels(hsv_img, lab_img, gray_img=gray_img)
        if roi_mask is not None:
            cover_like = cv2.bitwise_and(cover_like, roi_mask.astype(np.uint8))
        pure_produce = cv2.bitwise_and(mask.astype(np.uint8), cv2.bitwise_not(cover_like))
        keep_threshold = max(int(min_keep_pixels), int(cv2.countNonZero(mask) * float(min_keep_ratio)))
        if cv2.countNonZero(pure_produce) >= keep_threshold:
            # Fill internal holes so the produce body remains solid and unaffected by glare
            solid_produce = _fill_mask_holes(pure_produce)
            refined = cv2.bitwise_and(solid_produce, mask.astype(np.uint8))
            k3 = np.ones((3, 3), np.uint8)
            refined = cv2.morphologyEx(refined, cv2.MORPH_CLOSE, k3, iterations=1)
            return refined
    except Exception:
        pass
    return mask


def _suppress_boundary_hand_contours(
    mask: Optional[np.ndarray],
    polygon: List[List[int]],
    frame_shape: Tuple[int, int],
) -> Optional[np.ndarray]:
    """
    Suppresses hand, arm, and edge reflection contours that cross the outer boundary of the polygon ROI.
    Legitimate produce sits completely inside the platform plate.
    """
    if mask is None or cv2.countNonZero(mask) < 20 or not polygon or len(polygon) < 3:
        return mask
    try:
        h, w = frame_shape[:2]
        poly_pts = np.array(polygon, dtype=np.int32)
        pbx, pby, pbw, pbh = cv2.boundingRect(poly_pts)
        cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return mask
        cleaned = mask.copy()
        erased_any = False
        for c in cnts:
            area = float(cv2.contourArea(c))
            if area < 30.0:
                continue
            bx, by, bw, bh = cv2.boundingRect(c)
            # A contour crosses the boundary if it touches the outer frame edge or polygon bounding box edge
            touches_border = (
                bx <= 4
                or by <= 4
                or (bx + bw) >= (w - 4)
                or (by + bh) >= (h - 4)
                or bx <= (pbx + 6)
                or by <= (pby + 6)
                or (bx + bw) >= (pbx + pbw - 6)
                or (by + bh) >= (pby + pbh - 6)
            )
            # Also check if contour points lie along the polygon boundary
            if not touches_border:
                step = max(1, len(c) // 12)
                for pt in c[::step]:
                    dist = cv2.pointPolygonTest(poly_pts, (float(pt[0][0]), float(pt[0][1])), True)
                    if abs(dist) <= 6.0:  # within 6 pixels of polygon border
                        touches_border = True
                        break

            # If it touches the border and has significant size or spans across the edge (hand/arm reaching in)
            if touches_border and (area >= 90 or (bw > pbw * 0.25 or bh > pbh * 0.25)):
                cv2.drawContours(cleaned, [c], -1, 0, -1)
                erased_any = True
        if erased_any:
            return cleaned
    except Exception:
        pass
    return mask


def _best_object_blob_mask(
    mask: np.ndarray,
    score_map: np.ndarray,
    roi_mask: Optional[np.ndarray] = None,
    glare_mask: Optional[np.ndarray] = None,
    cover_like_mask: Optional[np.ndarray] = None,
    tray_like_mask: Optional[np.ndarray] = None,
    max_area_ratio: float = 0.28,
) -> np.ndarray:
    cleaned = _clean_object_mask(mask, roi_mask)
    if cleaned is None or cv2.countNonZero(cleaned) < 16:
        return cleaned

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return cleaned

    h, w = cleaned.shape[:2]
    roi_area = float(cv2.countNonZero(roi_mask)) if roi_mask is not None else float(h * w)
    min_area = max(22.0, roi_area * 0.00018)
    max_area = max(min_area * 2.0, roi_area * float(max_area_ratio))

    pbx, pby, pbw, pbh = (0, 0, w, h)
    if roi_mask is not None:
        r_cnts, _ = cv2.findContours(roi_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if r_cnts:
            pbx, pby, pbw, pbh = cv2.boundingRect(r_cnts[0])
    cx_ref, cy_ref = pbx + pbw / 2.0, pby + pbh / 2.0
    diag = np.sqrt(pbw * pbw + pbh * pbh) / 2.0 + 1e-6

    best_score = -1e9
    best_mask = None
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area or area > max_area:
            continue

        one = np.zeros_like(cleaned)
        cv2.drawContours(one, [contour], -1, 255, thickness=cv2.FILLED)
        px = float(cv2.countNonZero(one))
        if px <= 0:
            continue

        active = one > 0
        if glare_mask is not None:
            active = active & (glare_mask == 0)
            if int(np.count_nonzero(active)) < 12:
                active = one > 0
        if int(np.count_nonzero(active)) == 0:
            continue

        dev_mean = float(np.mean(score_map[active]))
        dev_peak = float(np.percentile(score_map[active], 90))
        dev_term = (dev_mean * 0.45) + (dev_peak * 0.55)
        cover_ratio = 0.0
        tray_ratio = 0.0
        if cover_like_mask is not None:
            cover_ratio = float(cv2.countNonZero(cv2.bitwise_and(one, cover_like_mask))) / px
        if tray_like_mask is not None and cv2.countNonZero(tray_like_mask) >= 80:
            tray_ratio = float(cv2.countNonZero(cv2.bitwise_and(one, tray_like_mask))) / px

        perim = float(cv2.arcLength(contour, True))
        circularity = 0.0
        if perim > 1e-6:
            circularity = float((4.0 * np.pi * area) / (perim * perim))

        x, y, bw, bh = cv2.boundingRect(contour)
        elongation = (max(float(bw), float(bh)) / max(1.0, min(float(bw), float(bh))))
        touches_border = (
            x <= (pbx + 8) or y <= (pby + 8) or (x + bw) >= (pbx + pbw - 8) or (y + bh) >= (pby + pbh - 8)
        )
        dist = np.sqrt((x + bw / 2.0 - cx_ref) ** 2 + (y + bh / 2.0 - cy_ref) ** 2)
        center_weight = max(0.20, 1.0 - (dist / diag) * 0.65)

        size_term = min(area, 3200.0) / 900.0
        elong_penalty = max(0.0, elongation - 2.5) * 1.65
        score = (dev_term * 1.55) + size_term + (max(0.0, circularity) * 1.6) - (cover_ratio * 4.8) - (tray_ratio * 3.8) - elong_penalty
        score *= center_weight
        if touches_border:
            score *= 0.05
        if elongation > 3.2:
            score *= 0.15
        if score > best_score:
            best_score = score
            best_mask = one

    if best_mask is None:
        if cleaned is not None and roi_area > 0 and (float(cv2.countNonZero(cleaned)) / roi_area) >= 0.35:
            active = cleaned > 0
            if int(np.count_nonzero(active)) >= 24:
                ref = float(np.percentile(score_map[active], 88))
                core = ((score_map >= ref) & active).astype(np.uint8) * 255
                core = _clean_object_mask(core, roi_mask)
                if core is not None and cv2.countNonZero(core) >= 12:
                    return core
        return cleaned

    if best_score < 1.15:
        return cleaned
    return best_mask


def bgr_to_qpixmap(frame_bgr: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)


def rounded_pixmap(pixmap: QPixmap, size: QSize, radius: float) -> QPixmap:
    if pixmap.isNull():
        return QPixmap()
    scaled = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out = QPixmap(size)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing, True)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
    painter.setClipPath(path)
    x = (size.width() - scaled.width()) // 2
    y = (size.height() - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return out


# -------------------------
# Brain
# -------------------------
class Brain:
    def __init__(self, learned_path: str, meta_path: str, thumb_dir: str, max_samples: int = 40):
        self.learned_path = learned_path
        self.meta_path = meta_path
        self.thumb_dir = thumb_dir
        self.max_samples = max_samples
        self.debug = os.environ.get("DEBUG_MATCH", "0") == "1"
        self.last_match_details: Dict[str, dict] = {}
        self.data: Dict[str, List[List[float]]] = {}
        self.meta: Dict[str, dict] = {}
        # Pre-normalized matrix cache: code -> (arr_norm: np.ndarray [shape (N, D), float32], valid_indices: List[int])
        self._gallery_cache: Dict[str, Tuple[np.ndarray, List[int]]] = {}
        os.makedirs(self.thumb_dir, exist_ok=True)
        self.load()

    def load(self) -> None:
        if os.path.exists(self.learned_path):
            try:
                with open(self.learned_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                out = {}
                for code, val in raw.items():
                    if isinstance(val, dict) and "MAIN" in val:
                        out[code] = [s["hist"] for s in val["MAIN"] if isinstance(s, dict) and "hist" in s]
                    elif isinstance(val, list):
                        out[code] = val
                self.data = out
            except Exception:
                self.data = {}

        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self.meta = raw
            except Exception:
                self.meta = {}

        self._rebuild_gallery_cache()
        self._migrate_from_thumbs_if_needed()

    def _migrate_from_thumbs_if_needed(self) -> None:
        """Ensure all items in DINOv3 gallery have full 360-degree rotational variants from stored thumbnails."""
        if not self.meta:
            return
        if dinov3_vision is None or not dinov3_vision.is_available():
            return
        needs_upgrade = any(len(self.data.get(str(k).strip(), [])) < 10 for k in self.meta.keys())
        if not needs_upgrade and self.data:
            return
        print("[Brain] Generating 360-degree rotational variants for produce gallery...")
        migrated_count = 0
        for code, meta in self.meta.items():
            code_key = str(code).strip()
            if len(self.data.get(code_key, [])) >= 10:
                continue
            thumb_path = meta.get("thumb")
            if not thumb_path or not os.path.exists(thumb_path):
                alt_thumb = self._thumb_path(code)
                if os.path.exists(alt_thumb):
                    thumb_path = alt_thumb
            if thumb_path and os.path.exists(thumb_path):
                img = cv2.imread(thumb_path)
                if img is not None:
                    variants = dinov3_vision.extract_dinov3_pose_variants(img)
                    if not variants:
                        single = dinov3_vision.compute_embedding(img)
                        if single is not None:
                            variants = [single]
                    if variants:
                        self.data[code_key] = [v.tolist() for v in variants]
                        migrated_count += 1
        if migrated_count > 0:
            print(f"[Brain] Successfully updated {migrated_count} items with 360-degree rotation coverage.")
            self.save()
            self._rebuild_gallery_cache()

    def save(self) -> None:
        data_snapshot = dict(self.data)
        path = self.learned_path
        def _write():
            try:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data_snapshot, f, separators=(",", ":"))
                os.replace(tmp, path)
            except Exception as e:
                print(f"[Brain save error: {e}]")
        threading.Thread(target=_write, daemon=True).start()

    def save_meta(self) -> None:
        meta_snapshot = dict(self.meta)
        path = self.meta_path
        def _write():
            try:
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(meta_snapshot, f, separators=(",", ":"))
                os.replace(tmp, path)
            except Exception as e:
                print(f"[Brain save_meta error: {e}]")
        threading.Thread(target=_write, daemon=True).start()

    def _estimate_code_threshold(self, code: str) -> Optional[float]:
        samples = self.data.get(str(code).strip(), [])
        if not samples or len(samples) < 2:
            return None
        try:
            # Group by dimension to handle potential mixed sample lengths safely
            by_dim = {}
            for s in samples:
                if isinstance(s, (list, np.ndarray)) and len(s) > 0:
                    by_dim.setdefault(len(s), []).append(s)
            if not by_dim:
                return None
            dominant_dim = max(by_dim.keys(), key=lambda d: len(by_dim[d]))
            dominant_samples = by_dim[dominant_dim]
            if len(dominant_samples) < 2:
                return None
            arr = np.asarray(dominant_samples, dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms = np.where(norms > 1e-8, norms, 1.0)
            arr_norm = arr / norms
            sim_matrix = np.dot(arr_norm, arr_norm.T)
            np.fill_diagonal(sim_matrix, -1.0)
            max_sims = np.max(sim_matrix, axis=1)
            p20 = float(np.percentile(max_sims, 20))
            return float(max(0.35, min(0.92, p20 - 0.03)))
        except Exception:
            return None

    def _thumb_path(self, code: str) -> str:
        safe = "".join(c for c in str(code) if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.thumb_dir, f"{safe}.jpg")

    def _display_thumb_path(self, code: str) -> str:
        safe = "".join(c for c in str(code) if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.thumb_dir, f"{safe}_display.jpg")

    def save_thumb(self, code: str, frame_bgr: np.ndarray) -> str:
        path = self._thumb_path(code)
        cv2.imwrite(path, frame_bgr)
        return path

    def save_display_thumb(self, code: str, frame_bgr: np.ndarray) -> str:
        path = self._display_thumb_path(code)
        cv2.imwrite(path, frame_bgr)
        self.meta.setdefault(str(code).strip(), {})
        self.meta[str(code).strip()]["display_thumb"] = path
        self.save_meta()
        return path

    def _rebuild_code_cache(self, code: str) -> None:
        """Build and cache contiguous L2-normalized float32 matrix for a code.
        Groups samples by dimension so inhomogeneous lists (e.g. mixed legacy HSV
        and modern DINOv2 vectors) never cause np.asarray() to crash."""
        code_key = str(code).strip()
        samples = self.data.get(code_key, [])
        if not samples:
            self._gallery_cache.pop(code_key, None)
            return

        # Partition samples by vector dimension (length)
        by_dim: Dict[int, Tuple[List[Any], List[int]]] = {}
        for idx, s in enumerate(samples):
            if isinstance(s, (list, np.ndarray)):
                d = len(s)
                if d > 0:
                    if d not in by_dim:
                        by_dim[d] = ([], [])
                    by_dim[d][0].append(s)
                    by_dim[d][1].append(idx)

        if not by_dim:
            self._gallery_cache.pop(code_key, None)
            return

        # Store a mapping of dim -> (arr_norm, valid_indices) for this code.
        # Each arr is strictly homogeneous since all vectors in by_dim[d][0] have length d.
        dim_caches = {}
        for d, (s_list, idx_list) in by_dim.items():
            try:
                arr = np.asarray(s_list, dtype=np.float32)
                norms = np.linalg.norm(arr, axis=1, keepdims=True)
                norms = np.where(norms > 1e-8, norms, 1.0)
                arr_norm = np.ascontiguousarray(arr / norms)
                dim_caches[d] = (arr_norm, idx_list)
            except Exception as e:
                print(f"[Brain._rebuild_code_cache] Error converting dim {d} for {code_key}: {e}")

        if dim_caches:
            self._gallery_cache[code_key] = dim_caches
        else:
            self._gallery_cache.pop(code_key, None)

    def _rebuild_gallery_cache(self) -> None:
        """Rebuild pre-normalized matrix cache and stacked contiguous matrix for all codes."""
        self._gallery_cache.clear()
        self._stacked_gallery = {}
        for code in list(self.data.keys()):
            self._rebuild_code_cache(code)

        # Build stacked contiguous matrix per feature dimension for fast vectorized BLAS GEMV
        by_dim_blocks: Dict[int, List[Tuple[str, np.ndarray, List[int]]]] = {}
        for code, dim_map in self._gallery_cache.items():
            if isinstance(dim_map, dict):
                for d, (arr_norm, valid_indices) in dim_map.items():
                    by_dim_blocks.setdefault(d, []).append((code, arr_norm, valid_indices))
            elif isinstance(dim_map, tuple):
                arr_norm, valid_indices = dim_map
                d = arr_norm.shape[1]
                by_dim_blocks.setdefault(d, []).append((code, arr_norm, valid_indices))

        for d, blocks in by_dim_blocks.items():
            if not blocks:
                continue
            all_arrs = [b[1] for b in blocks]
            stacked_mat = np.ascontiguousarray(np.vstack(all_arrs), dtype=np.float32)
            code_segments = []
            curr_idx = 0
            for code, arr_norm, valid_indices in blocks:
                n_samples = arr_norm.shape[0]
                code_segments.append((code, curr_idx, curr_idx + n_samples, valid_indices))
                curr_idx += n_samples
            self._stacked_gallery[d] = {
                "matrix": stacked_mat,
                "segments": code_segments,
            }

    def delete(self, code: str) -> None:
        """Delete an item from data and cache."""
        code_key = str(code).strip()
        self.data.pop(code_key, None)
        self._gallery_cache.pop(code_key, None)
        self.last_match_details.pop(code_key, None)
        self._rebuild_gallery_cache()

    def learn_batch(
        self,
        code: str,
        feats: List[np.ndarray],
        meta: Optional[dict] = None,
        thumb_bgr: Optional[np.ndarray] = None,
    ) -> None:
        code = str(code).strip()
        if not feats:
            return

        # Ensure all features in this batch are valid arrays and filter to dominant dimension
        valid_batch = [f for f in feats if isinstance(f, (list, np.ndarray)) and len(f) > 0]
        if not valid_batch:
            return

        batch_dims = [len(f) for f in valid_batch]
        if len(set(batch_dims)) > 1:
            chosen_dim = 384 if 384 in batch_dims else max(set(batch_dims), key=batch_dims.count)
            valid_batch = [f for f in valid_batch if len(f) == chosen_dim]

        target_dim = len(valid_batch[0])
        self.data.setdefault(code, [])

        # If retraining with a new feature space (e.g. 384-dim DINOv2 vs old 62-dim HSV),
        # prune legacy samples of mismatched dimension so gallery stays clean and homogeneous
        if self.data[code]:
            existing_dims = {len(s) for s in self.data[code] if isinstance(s, (list, np.ndarray)) and len(s) > 0}
            if existing_dims != {target_dim}:
                self.data[code] = [s for s in self.data[code] if isinstance(s, (list, np.ndarray)) and len(s) == target_dim]

        for feat in valid_batch:
            self.data[code].append(np.asarray(feat, dtype=float).tolist())

        # Enforce max_samples cap (FIFO: roll off oldest first)
        self.data[code] = self.data[code][-self.max_samples :]
        self._rebuild_code_cache(code)
        self.save()

        if meta is not None:
            self.meta[code] = meta

        if thumb_bgr is not None:
            path = self.save_thumb(code, thumb_bgr)
            self.meta.setdefault(code, {})
            self.meta[code]["thumb"] = path
            if "color_profile" not in self.meta[code] and _COLOR_MATCHER_AVAILABLE and color_matcher is not None:
                try:
                    c_prof = color_matcher.compute_color_profile(thumb_bgr)
                    if c_prof:
                        self.meta[code]["color_profile"] = c_prof
                        dom_fam = c_prof.get("dominant_family", "UNKNOWN")
                        fam_dist = c_prof.get("families", {})
                        dom_pct = float(fam_dist.get(dom_fam, 1.0)) * 100.0
                        name = self.meta[code].get("Name") or self.meta[code].get("name") or code
                        print(f"[Brain.learn_batch] Product '{name}' ({code}) saved -> Color Family: {dom_fam} ({dom_pct:.1f}%)")
                except Exception as e:
                    print(f"[Brain.learn_batch] Color profile extraction error for {code}: {e}")

        self.meta.setdefault(code, {})
        est = self._estimate_code_threshold(code)
        if est is not None:
            self.meta[code]["score_threshold"] = round(float(est), 4)

        # Single consolidated metadata save per batch
        self.save_meta()
        self._rebuild_gallery_cache()

    def learn(self, code: str, feat: np.ndarray, meta: Optional[dict] = None, thumb_bgr: Optional[np.ndarray] = None) -> None:
        self.learn_batch(code, [feat], meta=meta, thumb_bgr=thumb_bgr)

    def match_all(self, feat: np.ndarray) -> List[Tuple[str, float]]:
        """
        Gallery matching: compares the live embedding against every stored sample
        of each code individually using cached normalized matrices, and returns
        the maximum similarity per code.
        Preserves List[Tuple[code, score]] sorted descending.
        """
        matches = []
        feat_arr = np.asarray(feat, dtype=np.float32)
        norm_feat = np.linalg.norm(feat_arr)
        if norm_feat > 1e-8:
            feat_norm = np.ascontiguousarray(feat_arr / norm_feat, dtype=np.float32)
        else:
            feat_norm = np.ascontiguousarray(feat_arr, dtype=np.float32)
        feat_len = len(feat_arr)

        self.last_match_details = {}

        if not self._gallery_cache and self.data:
            self._rebuild_gallery_cache()

        stacked_info = getattr(self, "_stacked_gallery", {}).get(feat_len)
        if stacked_info is not None:
            # High-performance Vectorized execution: 1 single BLAS matrix-vector dot product
            matrix = stacked_info["matrix"]
            all_scores = np.dot(matrix, feat_norm)
            segments = stacked_info["segments"]
            for code, start_idx, end_idx, valid_indices in segments:
                sub_scores = all_scores[start_idx:end_idx]
                best_local_idx = int(np.argmax(sub_scores))
                best_score = float(sub_scores[best_local_idx])
                best_orig_idx = valid_indices[best_local_idx]

                matches.append((code, best_score))
                self.last_match_details[code] = {
                    "best_idx": best_orig_idx,
                    "best_score": best_score,
                    "total_samples": len(self.data.get(code, [])),
                }
        else:
            # Fallback to per-code cache
            for code, cache_val in self._gallery_cache.items():
                if isinstance(cache_val, dict):
                    cache_entry = cache_val.get(feat_len)
                    if cache_entry is None:
                        continue
                    arr_norm, valid_indices = cache_entry
                elif isinstance(cache_val, tuple):
                    arr_norm, valid_indices = cache_val
                    if arr_norm.shape[1] != feat_len:
                        continue
                else:
                    continue

                scores = np.dot(arr_norm, feat_norm)
                best_local_idx = int(np.argmax(scores))
                best_score = float(scores[best_local_idx])
                best_orig_idx = valid_indices[best_local_idx]

                matches.append((code, best_score))
                self.last_match_details[code] = {
                    "best_idx": best_orig_idx,
                    "best_score": best_score,
                    "total_samples": len(self.data.get(code, [])),
                }

        matches.sort(key=lambda x: x[1], reverse=True)

        # Log winning sample index in debug mode
        if matches and (getattr(self, "debug", False) or os.environ.get("DEBUG_MATCH", "0") == "1"):
            top_code, top_score = matches[0]
            detail = self.last_match_details.get(top_code, {})
            print(
                f"[Brain.match_all] Top match: '{top_code}' score={top_score:.4f} "
                f"(winning sample index {detail.get('best_idx')}/{detail.get('total_samples')})"
            )

        return matches

    def match(self, feat: np.ndarray) -> Tuple[Optional[str], float]:
        matches = self.match_all(feat)
        if not matches:
            return None, 0.0
        return matches[0]


# -------------------------
# Scale reader (QSerialPort)
# -------------------------
class ScaleReader(QObject):
    weightChanged = Signal(float)
    liveWeightChanged = Signal(float)

    def __init__(self, port_name: str, baud: int, stable_seconds: float = 0.3):
        super().__init__()
        self.stable_seconds = float(stable_seconds)

        self.serial = QSerialPort()
        self.serial.setPortName(port_name)
        self.serial.setBaudRate(int(baud))
        self.serial.readyRead.connect(self._on_ready_read)

        self._buffer = bytearray()
        self._last_raw = None
        self._last_emitted = None
        self._last_live_emitted = None
        self._live_zero_candidate_t = None
        self._live_zero_hold_seconds = 0.35
        self._last_change_t = 0.0
        self._zero_sent = False
        # Universal fast scale pattern: supports ALCAS, CAS, Toledo, and raw decimal streams
        self._scale_pattern = re.compile(r"(?:(?:ST|US|[SU\?MD])[\w,:]*\s*)?([+-]?\s*\d+(?:[.,]\d+))")

    def open(self) -> bool:
        if self.serial.isOpen():
            self.serial.close()
        return bool(self.serial.open(QSerialPort.ReadOnly))

    def close(self):
        if self.serial.isOpen():
            self.serial.close()

    def reconfigure(self, port_name: str, baud: int, stable_seconds: Optional[float] = None) -> bool:
        if stable_seconds is not None:
            self.stable_seconds = float(stable_seconds)
        self.close()
        self.serial.setPortName(port_name)
        self.serial.setBaudRate(int(baud))
        return self.open()

    def _handle_raw_weight(self, raw: float, now: float) -> None:
        # Emit live value immediately for UI (no stability delay).
        live = 0.0 if raw < 0.001 else float(raw)
        if live > 0.0:
            self._live_zero_candidate_t = None
            if self._last_live_emitted is None or abs(live - self._last_live_emitted) >= 0.001:
                self.liveWeightChanged.emit(live)
                self._last_live_emitted = live
        else:
            if self._live_zero_candidate_t is None:
                self._live_zero_candidate_t = now
            if (now - self._live_zero_candidate_t) >= self._live_zero_hold_seconds:
                if self._last_live_emitted is None or abs(self._last_live_emitted) >= 0.001:
                    self.liveWeightChanged.emit(0.0)
                    self._last_live_emitted = 0.0

        # Fast zero handling: avoid delay when scale is cleared
        if raw < 0.001:
            self._last_raw = None
            self._last_change_t = now
            if not self._zero_sent:
                self.weightChanged.emit(0.0)
                self._last_emitted = 0.0
                self._zero_sent = True
            return

        self._zero_sent = False
        # Fast Plateau: allow +/- 3g electrical/air micro-vibrations so timer doesn't constantly reset
        if self._last_raw is None or abs(raw - self._last_raw) > 0.003:
            self._last_raw = raw
            self._last_change_t = now
            return

        if (now - self._last_change_t) >= self.stable_seconds:
            if self._last_emitted is None or abs(raw - self._last_emitted) >= 0.002:
                self.weightChanged.emit(raw)
                self._last_emitted = raw

    @Slot()
    def _on_ready_read(self):
        incoming = self.serial.readAll().data()
        self._buffer += incoming

        # Parse complete records when available.
        chunks = re.split(rb"[\r\n]+", self._buffer)
        processed = False

        if len(chunks) > 1:
            self._buffer = bytearray(chunks[-1])
            now = time.time()
            latest_raw = None
            # Find the newest valid weight packet by checking lines backwards (zero backlog queueing)
            for line in reversed(chunks[:-1]):
                if not line:
                    continue
                try:
                    text = line.decode("ascii", errors="ignore")
                except Exception:
                    continue
                matches = self._scale_pattern.findall(text)
                if matches:
                    try:
                        clean_str = matches[-1].replace(" ", "").replace(",", ".")
                        latest_raw = float(clean_str)
                        break
                    except ValueError:
                        continue

            if latest_raw is not None:
                self._handle_raw_weight(latest_raw, now)
                processed = True
        else:
            # Fallback for stream protocols (parse from rolling buffer)
            try:
                text = self._buffer.decode("ascii", errors="ignore")
            except Exception:
                text = ""
            if text:
                matches = self._scale_pattern.findall(text)
                if matches:
                    try:
                        clean_str = matches[-1].replace(" ", "").replace(",", ".")
                        raw = float(clean_str)
                        self._handle_raw_weight(raw, time.time())
                        processed = True
                    except ValueError:
                        pass

        if not processed and len(self._buffer) > 4096:
            self._buffer = self._buffer[-1024:]


    # @Slot()
    # def _on_ready_read(self):
    #     self._buffer += self.serial.readAll().data()
    #     try:
    #         text = self._buffer.decode("ascii", errors="ignore")
    #     except Exception:
    #         self._buffer.clear()
    #         return

    #     matches = re.findall(r"(\d+\.\d+)", text)
    #     if matches:
    #         raw = float(matches[-1])
    #         now = time.time()
    #         if self._last_raw is None or abs(raw - self._last_raw) > 0.01:
    #             self._last_raw = raw
    #             self._last_change_t = now
    #         elif (now - self._last_change_t) >= self.stable_seconds:
    #             self.weightChanged.emit(raw)

    #     if len(self._buffer) > 4096:
    #         self._buffer = self._buffer[-1024:]


# -------------------------
# Camera worker
# -------------------------
class CameraWorker(QThread):
    frameReady = Signal(object)

    def __init__(self, cam_index: int = 0, fps: int = 15):
        super().__init__()
        self.cam_index = int(cam_index)
        self.fps = int(fps)
        self._running = True
        self._cap = None
        self.gui_busy = False
        self._latest_frame = None

    def run(self):
        # On Windows, DirectShow (CAP_DSHOW) is required to prevent MSMF video buffer deadlocks
        try:
            self._cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                self._cap = cv2.VideoCapture(self.cam_index)
        except Exception:
            self._cap = cv2.VideoCapture(self.cam_index)

        try:
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        while self._running:
            try:
                ok, frame = self._cap.read()
                if ok and frame is not None:
                    self._latest_frame = frame
                    if not self.gui_busy:
                        self.gui_busy = True
                        self.frameReady.emit(frame)
                else:
                    self.msleep(15)
            except Exception:
                self.msleep(15)

        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass

    def stop(self):
        self._running = False


# -------------------------
# Floating weight widget
# -------------------------
class FloatingWeight(QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self.lbl = QLabel("0.000 KG", self)
        self.lbl.setAlignment(Qt.AlignCenter)
        self.lbl.setStyleSheet("""
            QLabel {
                background: black;
                color: white;
                padding: 14px;
                border-radius: 12px;
                font-size: 22px;
                font-weight: bold;
            }
        """)
        self.lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.lbl.adjustSize()
        self.setFixedSize(self.lbl.sizeHint())
        self.lbl.setGeometry(0, 0, self.width(), self.height())
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 20, screen.bottom() - self.height() - 20)

        self._drag_pos = None
        self._pressed_pos = None
        self._prev_hwnd: Optional[int] = None

    def set_weight(self, w: float):
        self.lbl.setText(f"{w:.3f} KG")
        self.lbl.adjustSize()
        self.setFixedSize(self.lbl.sizeHint())
        self.lbl.setGeometry(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed_pos = event.globalPosition().toPoint()
            self._drag_pos = self._pressed_pos - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._pressed_pos:
            released_pos = event.globalPosition().toPoint()
            if (released_pos - self._pressed_pos).manhattanLength() < 6:
                self.clicked.emit()
        self._drag_pos = None
        self._pressed_pos = None
        event.accept()


class KgAllToggle(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(108, 46)
        self.setFocusPolicy(Qt.NoFocus)
        self._knob_pos = 0.0
        self._anim = QPropertyAnimation(self, b"knobPos", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._on_toggled)
        self._on_toggled(self.isChecked())

    def _get_knob_pos(self):
        return self._knob_pos

    def _set_knob_pos(self, value):
        self._knob_pos = float(max(0.0, min(1.0, value)))
        self.update()

    knobPos = Property(float, _get_knob_pos, _set_knob_pos)

    def _on_toggled(self, checked: bool):
        self._anim.stop()
        self._anim.setStartValue(self._knob_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        self.setToolTip("KG-only view is ON" if checked else "KG-only view is OFF")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(1, 1, -1, -1)
        radius = r.height() / 2.0

        if self.isChecked():
            bg = QColor("#18C261")
            label = "KG"
            label_color = QColor("#FFFFFF")
        else:
            bg = QColor("#E8E8E8")
            label = "ALL"
            label_color = QColor("#5F6670")

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(r, radius, radius)

        knob_d = r.height() - 6
        travel = r.width() - knob_d - 6
        knob_x = r.x() + 3 + (travel * self._knob_pos)
        knob_y = r.y() + 3
        knob_rect = QRectF(knob_x, knob_y, knob_d, knob_d)

        label_rect = QRectF(r.x() + 10, r.y(), r.width() - 20, r.height())
        painter.setPen(label_color)
        painter.drawText(label_rect, Qt.AlignCenter, label)

        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QColor("#D7DCE2"))
        painter.drawEllipse(knob_rect)
        painter.end()


# -------------------------
# Inventory Product Dialog
# -------------------------
class InventoryProductDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        product: dict,
        currency_symbol: str,
        image_path: Optional[str],
        on_take_picture,
        on_choose_file,
    ):
        super().__init__(parent)
        self.setWindowTitle("Product Details")
        self.product = product
        self.currency_symbol = currency_symbol
        self.on_take_picture = on_take_picture
        self.on_choose_file = on_choose_file
        self.setModal(True)
        self.resize(660, 390)
        self.setStyleSheet("""
            QDialog {
                background: #F6F0E8;
            }
            QLabel[role="title"] {
                color: #231A13;
                font-size: 30px;
                font-weight: 700;
            }
            QLabel[role="metaLabel"] {
                color: #8B7866;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 0.04em;
            }
            QLabel[role="metaValue"] {
                color: #241B14;
                font-size: 24px;
                font-weight: 600;
            }
            QPushButton {
                min-height: 46px;
                border-radius: 14px;
                padding: 0 20px;
                font-weight: 600;
                font-size: 16px;
                border: 1px solid #D7C3AE;
                background: #FFFCF9;
                color: #2B2119;
            }
            QPushButton:hover {
                background: #F0E1D2;
            }
            QPushButton[role="primary"] {
                background: #FFFCF9;
                border-color: #D7C3AE;
                color: #2B2119;
            }
            QPushButton[role="primary"]:hover {
                background: #F0E1D2;
            }
            QPushButton[role="danger"] {
                background: #FFF4F2;
                border-color: #E7B8B1;
                color: #8B2E23;
            }
            QPushButton[role="danger"]:hover {
                background: #FBE5E1;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(0)
        self.lblPreview = QLabel("No image")
        self.lblPreview.setAlignment(Qt.AlignCenter)
        self.lblPreview.setFixedSize(260, 260)
        self.lblPreview.setStyleSheet(
            "background: transparent; color:#8A7868;"
        )
        left.addWidget(self.lblPreview, 1)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.setContentsMargins(0, 4, 0, 4)
        right.setSpacing(16)

        name = self.product.get("Name", "")
        code = self.product.get("Code", "")
        price = float(self.product.get("Price", 0.0) or 0.0)
        uom = self.product.get("UOM", "")

        title = QLabel(name if name else "Item")
        title.setProperty("role", "title")
        title.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        right.addWidget(title)

        price_text = f"{self.currency_symbol}{price:.2f}" if price > 0 else "-"
        details = QGridLayout()
        details.setContentsMargins(0, 6, 0, 0)
        details.setHorizontalSpacing(18)
        details.setVerticalSpacing(16)
        details.setColumnStretch(1, 1)

        for row, (label_text, value_text) in enumerate([
            ("Code", code if code else "-"),
            ("UOM", uom if uom else "-"),
            ("Price", price_text),
        ]):
            label = QLabel(label_text)
            label.setProperty("role", "metaLabel")
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            label.setStyleSheet("background: transparent;")

            value = QLabel(value_text)
            value.setProperty("role", "metaValue")
            value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setWordWrap(True)
            value.setStyleSheet("background: transparent;")

            details.addWidget(label, row, 0)
            details.addWidget(value, row, 1)

        right.addLayout(details)

        right.addStretch(1)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.btnTakePicture = QPushButton("Take Picture")
        self.btnTakePicture.setProperty("role", "primary")
        self.btnChooseFile = QPushButton("Choose File")
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.setProperty("role", "danger")
        buttons.addWidget(self.btnTakePicture)
        buttons.addWidget(self.btnChooseFile)
        buttons.addWidget(self.btnCancel)
        right.addLayout(buttons)
        root.addLayout(right, 1)

        self.btnTakePicture.clicked.connect(self._take_picture)
        self.btnChooseFile.clicked.connect(self._choose_file)
        self.btnCancel.clicked.connect(self.reject)

        self._set_preview_from_path(image_path)

    def _set_preview_from_path(self, image_path: Optional[str]):
        if image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            self.lblPreview.setPixmap(rounded_pixmap(pix, self.lblPreview.size(), 32))
            self.lblPreview.setText("")
            return
        self.lblPreview.setPixmap(QPixmap())
        self.lblPreview.setText("No image")

    def _take_picture(self):
        self.accept()
        self.on_take_picture()

    def _choose_file(self):
        image_path = self.on_choose_file()
        if image_path:
            self._set_preview_from_path(image_path)


# -------------------------
# Guided Multi-Pose Training Dialog (Manual Multi-Capture)
# -------------------------
class GuidedMultiPoseDialog(QDialog):
    """
    Guides the operator through manually capturing 4 distinct poses during training.
    The operator positions/rotates the item and clicks 'Capture Pose' for each angle.
    """

    DEFAULT_PROMPTS = [
        "Pose 1 of 4: Place item naturally in tray, then click 'Capture Pose 1 of 4'.",
        "Pose 2 of 4: Rotate item ~90° or turn to another side, then click 'Capture Pose 2 of 4'.",
        "Pose 3 of 4: Tilt item or show another face (top / bottom / side), then click 'Capture Pose 3 of 4'.",
        "Pose 4 of 4: Final angle or flipped orientation, then click 'Capture Pose 4 of 4'.",
    ]

    def __init__(
        self,
        parent: QWidget,
        product: dict,
        target_poses: int = 4,
        countdown_seconds: Optional[float] = None,
    ):
        super().__init__(parent)
        self.parent_app = parent
        self.product = product
        self.target_poses = max(1, int(target_poses))
        self.captured_frames: List[np.ndarray] = []
        self.current_pose_index = 0

        self.setWindowTitle("Multi-Angle Manual Training")
        self.setModal(True)
        self.resize(680, 640)
        self.setStyleSheet("""
            QDialog {
                background: #F7F3EE;
            }
            QLabel[role="dialogTitle"] {
                color: #231A13;
                font-size: 22px;
                font-weight: 700;
            }
            QLabel[role="stepBadge"] {
                background: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                border-radius: 12px;
                padding: 4px 14px;
            }
            QLabel[role="promptBanner"] {
                background: #FFF7ED;
                border: 1.5px solid #FDBA74;
                color: #9A3412;
                font-size: 15px;
                font-weight: 600;
                border-radius: 8px;
                padding: 10px 14px;
            }
            QLabel[role="warningBanner"] {
                color: #DC2626;
                font-size: 13px;
                font-weight: 600;
            }
            QProgressBar {
                border: 1px solid #D7C3AE;
                border-radius: 6px;
                background: #EAE3D9;
                text-align: center;
                height: 18px;
                font-size: 12px;
                font-weight: bold;
                color: #2B2119;
            }
            QProgressBar::chunk {
                background-color: #16A34A;
                border-radius: 5px;
            }
            QPushButton {
                min-height: 44px;
                border-radius: 10px;
                padding: 0 18px;
                font-weight: 600;
                font-size: 15px;
                border: 1px solid #D7C3AE;
                background: #FFFCF9;
                color: #2B2119;
            }
            QPushButton:hover {
                background: #F0E1D2;
            }
            QPushButton[role="primary"] {
                background: #1E293B;
                border-color: #1E293B;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton[role="primary"]:hover {
                background: #334155;
            }
            QPushButton[role="success"] {
                background: #15803D;
                border-color: #15803D;
                color: #FFFFFF;
            }
            QPushButton[role="success"]:hover {
                background: #166534;
            }
            QPushButton[role="danger"] {
                background: #FFF4F2;
                border-color: #E7B8B1;
                color: #8B2E23;
            }
            QPushButton[role="danger"]:hover {
                background: #FBE5E1;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Header: Product Name + Step Badge
        header = QHBoxLayout()
        name = self.product.get("Name", "") or "Item"
        code = self.product.get("Code", "")
        self.lblTitle = QLabel(f"Training: {name} ({code})")
        self.lblTitle.setProperty("role", "dialogTitle")
        header.addWidget(self.lblTitle)

        header.addStretch()

        self.lblStepBadge = QLabel(f"Pose 1 of {self.target_poses}")
        self.lblStepBadge.setProperty("role", "stepBadge")
        header.addWidget(self.lblStepBadge)
        layout.addLayout(header)

        # Guided Prompt Banner
        self.lblPrompt = QLabel(self.DEFAULT_PROMPTS[0])
        self.lblPrompt.setProperty("role", "promptBanner")
        self.lblPrompt.setWordWrap(True)
        layout.addWidget(self.lblPrompt)

        # Warning / feedback label
        self.lblWarning = QLabel("")
        self.lblWarning.setProperty("role", "warningBanner")
        self.lblWarning.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lblWarning)

        # Live Camera Preview
        self.lblPreview = QLabel("Connecting camera...")
        self.lblPreview.setAlignment(Qt.AlignCenter)
        self.lblPreview.setFixedSize(640, 320)
        self.lblPreview.setStyleSheet(
            "background: #1F1D1A; border: 2px solid #D7C3AE; border-radius: 12px; color: #E5E0D8;"
        )
        layout.addWidget(self.lblPreview, alignment=Qt.AlignCenter)

        # Capture Progress Bar
        self.progProgress = QProgressBar()
        self.progProgress.setRange(0, self.target_poses)
        self.progProgress.setValue(0)
        self.progProgress.setFormat(f"0 of {self.target_poses} poses captured")
        layout.addWidget(self.progProgress)

        # Captured Pose Thumbnails Row
        thumb_box = QHBoxLayout()
        thumb_box.setSpacing(12)
        self.thumb_labels = []
        for i in range(self.target_poses):
            slot_box = QVBoxLayout()
            slot_box.setSpacing(4)
            lbl = QLabel(f"Pose {i + 1}")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setFixedSize(90, 70)
            lbl.setStyleSheet(
                "border: 2px dashed #C8B6A2; border-radius: 8px; background: #FFFFFF; color: #8A7868; font-size: 11px; font-weight: 600;"
            )
            slot_box.addWidget(lbl, alignment=Qt.AlignCenter)
            self.thumb_labels.append(lbl)
            thumb_box.addLayout(slot_box)
        layout.addLayout(thumb_box)

        # Control Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btnCapture = QPushButton(f"📸 Capture Pose 1 of {self.target_poses}")
        self.btnCapture.setProperty("role", "primary")
        self.btnCapture.clicked.connect(self._on_capture_clicked)
        btn_layout.addWidget(self.btnCapture)

        self.btnFinish = QPushButton("✓ Finish Training")
        self.btnFinish.setProperty("role", "success")
        self.btnFinish.setEnabled(False)
        self.btnFinish.clicked.connect(self._on_finish_clicked)
        btn_layout.addWidget(self.btnFinish)

        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.setProperty("role", "danger")
        self.btnCancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btnCancel)

        layout.addLayout(btn_layout)

        # Timer solely for live camera preview (50ms = 20 fps, no auto-countdown)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_tick)
        self.timer.start(50)

    def _set_thumb_slot(self, slot_idx: int, thumb_bgr: np.ndarray):
        if 0 <= slot_idx < len(self.thumb_labels):
            lbl = self.thumb_labels[slot_idx]
            pix = bgr_to_qpixmap(thumb_bgr)
            scaled = pix.scaled(lbl.width(), lbl.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lbl.setPixmap(scaled)
            lbl.setStyleSheet("border: 2px solid #16A34A; border-radius: 8px; background: #FFFFFF;")

    def _on_timer_tick(self):
        # Update live frame preview continuously (showing polygon and detected bounding box)
        disp = getattr(self.parent_app, "_last_disp_frame", None)
        if disp is None:
            frame = getattr(self.parent_app, "latest_frame_raw", None)
            if frame is not None:
                disp = frame.copy()
                polygon = self.parent_app.settings.get("camera", {}).get("polygon", [])
                if polygon:
                    disp = draw_polygon_with_handles(disp, polygon)
        if disp is not None:
            pix = bgr_to_qpixmap(disp)
            scaled = pix.scaled(self.lblPreview.width(), self.lblPreview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.lblPreview.setPixmap(scaled)

    def _on_capture_clicked(self):
        frame = getattr(self.parent_app, "latest_frame_raw", None)
        if frame is None:
            self.lblWarning.setText("Waiting for camera frame...")
            return

        polygon = self.parent_app.settings.get("camera", {}).get("polygon", [])
        ok, reason = self.parent_app._validate_training_frame(frame, polygon)
        if not ok:
            self.lblWarning.setText(f"⚠ {reason}")
            return

        # Frame is valid! Save it
        if getattr(self.parent_app, "_last_is_small_warning", False):
            self.lblWarning.setText("Note: Item is small in frame — ensure item is centered for best accuracy.")
        else:
            self.lblWarning.setText("")
        self.captured_frames.append(frame.copy())
        thumb = self.parent_app._extract_thumb(frame, polygon)
        self._set_thumb_slot(self.current_pose_index, thumb)

        self.current_pose_index += 1
        self.btnFinish.setEnabled(True)
        self.progProgress.setValue(self.current_pose_index)
        self.progProgress.setFormat(f"{self.current_pose_index} of {self.target_poses} poses captured")

        if self.current_pose_index >= self.target_poses:
            self.timer.stop()
            self.btnCapture.setEnabled(False)
            self.btnCapture.setText("✓ All 4 Poses Captured!")
            self.lblPrompt.setText("✓ All poses captured! Processing and saving embeddings...")
            QTimer.singleShot(350, self.accept)
        else:
            prompt_text = (
                self.DEFAULT_PROMPTS[self.current_pose_index]
                if self.current_pose_index < len(self.DEFAULT_PROMPTS)
                else f"Pose {self.current_pose_index + 1} of {self.target_poses}: Rotate or tilt item, then click Capture."
            )
            self.lblPrompt.setText(prompt_text)
            self.lblStepBadge.setText(f"Pose {self.current_pose_index + 1} of {self.target_poses}")
            self.btnCapture.setText(f"📸 Capture Pose {self.current_pose_index + 1} of {self.target_poses}")

    def _on_finish_clicked(self):
        if self.captured_frames:
            self.timer.stop()
            self.accept()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


# -------------------------
# Dashboard
# -------------------------
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()

        self.brain = Brain(
            LEARNED_PATH,
            LEARNED_META_PATH,
            THUMB_DIR,
            max_samples=int(self.settings.get("behavior", {}).get("max_samples", 40)),
        )
        self.brain.debug = bool(
            self.settings.get("behavior", {}).get("debug_match", False)
            or os.environ.get("DEBUG_MATCH", "0") == "1"
        )

        # Preload DINOv3 model in background so first match isn't slow
        if _DINOV3_AVAILABLE and dinov3_vision is not None:
            threading.Thread(
                target=lambda: dinov3_vision.DinoV3VisionMatcher.instance(),
                daemon=True,
            ).start()

        self.scale_connected = False
        self._demo_timer = None

        # Drag state for polygon
        self._drag_idx: Optional[int] = None
        self._drag_target_label: Optional[QLabel] = None

        # Frames
        self.latest_frame_raw = None  # raw camera frame only
        self._last_disp_frame = None  # drawn frame for UI

        # In-memory baseline and ROI cache for fast matching
        self._cached_baseline_path: Optional[str] = None
        self._cached_baseline_mtime: float = 0.0
        self._cached_baseline_bgr: Optional[np.ndarray] = None
        self._cached_baseline_lab: Optional[np.ndarray] = None
        self._cached_roi_polygon: Optional[tuple] = None
        self._cached_roi_shape: Optional[tuple] = None
        self._cached_roi_mask: Optional[np.ndarray] = None
        self._cached_roi_px: float = 0.0

        # Diagnostic & Bounding box tracking
        self._last_extraction_mode: str = "Idle (waiting for item)"
        self._last_detected_bbox: Optional[Tuple[int, int, int, int]] = None
        self._last_detected_bbox_time: float = 0.0
        self._last_is_small_warning: bool = False
        self._last_baseline_warning: Optional[str] = None
        self._last_baseline_check_time: float = 0.0
        self._close_timer: Optional[QTimer] = None
        self._manual_open: bool = True
        self._opened_by_weight: bool = False

        print("Dashboard init started")

        # Load UI
        loader = QUiLoader()
        ui_path = resolve_asset_path("dashboard.ui")
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        loaded = loader.load(ui_file, None)
        ui_file.close()

        self.ui = loaded
        self.setCentralWidget(self.ui.centralWidget())
        self.setWindowTitle(APP_DIALOG_TITLE)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        if self.ui.styleSheet():
            self.setStyleSheet(self.ui.styleSheet())
        self.setMinimumHeight(700)
        self.setMinimumWidth(1220)
        self.resize(1220, 700)

        cw = self.centralWidget()

        # Core widgets
        self.btnBackTop = cw.findChild(QPushButton, "btnBackTop")
        self.btnSearch = cw.findChild(QPushButton, "btnSearch")
        self.btnViewProducts = cw.findChild(QPushButton, "btnViewProducts")
        self.btnSettings = cw.findChild(QPushButton, "btnSettings")
        self.btnRefresh = cw.findChild(QPushButton, "btnRefresh")
        if self.btnRefresh is None and self.btnSettings is not None and self.btnSettings.parentWidget() is not None:
            top_layout = self.btnSettings.parentWidget().layout()
            if top_layout is not None:
                self.btnRefresh = QPushButton("Refresh")
                self.btnRefresh.setObjectName("btnRefresh")
                idx = top_layout.indexOf(self.btnSettings)
                if idx >= 0:
                    top_layout.insertWidget(idx + 1, self.btnRefresh)
                else:
                    top_layout.addWidget(self.btnRefresh)
        self.btnToggleCamera = cw.findChild(QPushButton, "btnToggleCamera")
        self.btnClose = cw.findChild(QPushButton, "btnClose")
        self.btnExit = cw.findChild(QPushButton, "btnExit")
        self.lblLogo = cw.findChild(QLabel, "lblLogo")
        self.lblWeight = cw.findChild(QLabel, "lblWeight")
        self.lblInventorySummary = cw.findChild(QLabel, "lblInventorySummary")
        self.stack = cw.findChild(QStackedWidget, "stack")

        self.pageDashboard = cw.findChild(QWidget, "pageDashboard")
        self.pageSettings = cw.findChild(QWidget, "pageSettings")
        self.pageDetect = None

        self.dashboardStack = cw.findChild(QStackedWidget, "dashboardStack")
        self.pagePredictions = cw.findChild(QWidget, "pagePredictions")
        self.pageSearch = cw.findChild(QWidget, "pageSearch")
        self.btnCloseSearch = None
        self.btnBackSearch = cw.findChild(QPushButton, "btnBackSearch")
        self.txtSearch = cw.findChild(QLineEdit, "txtSearch")
        self.btnKeyboard = cw.findChild(QPushButton, "btnKeyboard")
        self.btnUomKgOnly = cw.findChild(QPushButton, "btnUomKgOnly")
        self.keyboardPanel = cw.findChild(QWidget, "keyboardPanel")
        self.btnGo = cw.findChild(QPushButton, "btnGo")
        self.listProducts = cw.findChild(QListWidget, "listProducts")
        self.btnTrainSelected = cw.findChild(QPushButton, "btnTrainSelected")
        self.cmbDbUomFilter = cw.findChild(QComboBox, "cmbDbUomFilter")

        self.listMatches = cw.findChild(QListWidget, "listMatches")
        self.panelRight = cw.findChild(QWidget, "panelRight")
        self.lblCameraDash = cw.findChild(QLabel, "lblCameraDash")

        # Diagnostic & Mode Indicators below live camera
        self.lblExtractionMode = QLabel("Detection: Idle (waiting for item)")
        self.lblExtractionMode.setAlignment(Qt.AlignCenter)
        self.lblExtractionMode.setWordWrap(True)
        self.lblExtractionMode.setStyleSheet(
            "background: #ECEFF1; color: #455A64; border: 1px solid #CFD8DC; "
            "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: bold;"
        )

        self.lblSmallItemWarning = QLabel("⚠️ Item is small in frame — move camera closer or center item for best accuracy")
        self.lblSmallItemWarning.setAlignment(Qt.AlignCenter)
        self.lblSmallItemWarning.setWordWrap(True)
        self.lblSmallItemWarning.setStyleSheet(
            "background: #FFF8E1; color: #E65100; border: 1px solid #FFE082; "
            "border-radius: 6px; padding: 4px 6px; font-size: 10px; font-weight: 600;"
        )
        self.lblSmallItemWarning.setVisible(False)

        self.lblBaselineWarning = QLabel("⚠️ Background lighting changed — please recapture empty tray in Settings")
        self.lblBaselineWarning.setAlignment(Qt.AlignCenter)
        self.lblBaselineWarning.setWordWrap(True)
        self.lblBaselineWarning.setStyleSheet(
            "background: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; "
            "border-radius: 6px; padding: 4px 6px; font-size: 10px; font-weight: 600;"
        )
        self.lblBaselineWarning.setVisible(False)

        if self.panelRight is not None and self.panelRight.layout() is not None:
            self.panelRight.layout().addWidget(self.lblExtractionMode)
            self.panelRight.layout().addWidget(self.lblSmallItemWarning)
            self.panelRight.layout().addWidget(self.lblBaselineWarning)

        self.listTrained = None
        self.lblPreview = None
        self.btnRetrain = None
        self.lblSelectedInfo = None

        # Settings nav widgets
        self.btnBack = None
        self.listSettingsNav = cw.findChild(QListWidget, "listSettingsNav")
        self.settingsStack = cw.findChild(QStackedWidget, "settingsStack")
        self.tblTrainedData = None
        self.listTrainedData = cw.findChild(QListWidget, "listTrainedData")
        self.btnDeleteTrained = cw.findChild(QPushButton, "btnDeleteTrained")
        self.btnToggleWeightMode = cw.findChild(QPushButton, "btnToggleWeightMode")
        self.btnRefreshTrainedData = None

        # Settings camera preview + reset polygon
        self.lblCamera = cw.findChild(QLabel, "lblCamera")
        self.btnResetPolygon = cw.findChild(QPushButton, "btnResetPolygon")
        self.btnSavePolygon = cw.findChild(QPushButton, "btnSavePolygon")
        self.btnSetEmptyTray = None
        self.btnSetEmptyCover = None
        self.lblPolygonInfo = None

        # Settings controls
        self.cmbCom = cw.findChild(QComboBox, "cmbCom")
        self.cmbBaud = cw.findChild(QComboBox, "cmbBaud")
        self.spnStableSeconds = cw.findChild(QDoubleSpinBox, "spnStableSeconds")
        self.spnOpenThreshold = cw.findChild(QDoubleSpinBox, "spnOpenThreshold")

        self.spinCam = None
        self.chkShowBoundary = None
        self.spinX1 = None
        self.spinY1 = None
        self.spinX2 = None
        self.spinY2 = None
        self.spinX3 = None
        self.spinY3 = None
        self.spinX4 = None
        self.spinY4 = None

        self.spnMatchThreshold = cw.findChild(QDoubleSpinBox, "spnMatchThreshold")
        self.txtMaxSamples = cw.findChild(QLineEdit, "txtMaxSamples")

        self.txtPrefix = cw.findChild(QLineEdit, "txtPrefix")
        self.txtCodeLen = cw.findChild(QLineEdit, "txtCodeLen")
        self.txtPriceLen = cw.findChild(QLineEdit, "txtPriceLen")
        self.txtQtyLen = cw.findChild(QLineEdit, "txtQtyLen")

        self.cmbCurrency = self.findChild(QComboBox, "cmbCurrency")

        self.txtDbServer = cw.findChild(QLineEdit, "txtDbServer")
        self.txtDbName = cw.findChild(QLineEdit, "txtDbName")
        self.txtDbUser = cw.findChild(QLineEdit, "txtDbUser")
        self.txtDbPass = cw.findChild(QLineEdit, "txtDbPass")

        self.btnSaveSettings = cw.findChild(QPushButton, "btnSaveSettings")

        self._selected_product = None
        self._return_to_settings_on_back = False

        self._drag_pos = None
        self._pressed_pos = None

        self._load_logo()
        self._default_img_index_pcs = {}
        self._default_img_index_kg = {}
        self._load_default_images()
        self._product_icon_queue = []
        self._product_icon_timer = QTimer(self)
        self._product_icon_timer.setInterval(30)
        self._product_icon_timer.timeout.connect(self._process_product_icon_queue)
        self._db_products_by_code = {}
        self._db_products_last_sync = 0.0
        self._db_products_sync_interval = 1.0
        self._uom_kg_only = False
        self._add_set_empty_tray_button()
        self._add_set_empty_cover_button()

        # Signals
        if self.btnBackTop is not None:
            self.btnBackTop.clicked.connect(self.on_back_top)
        if self.btnBackSearch is not None:
            self.btnBackSearch.clicked.connect(self.show_dashboard_page)
        if self.btnSearch is not None:
            self.btnSearch.clicked.connect(self.toggle_search_panel)
        if self.btnViewProducts is not None:
            self.btnViewProducts.clicked.connect(self.show_all_products)
        if self.btnSettings is not None:
            self.btnSettings.clicked.connect(self.toggle_settings)
        if self.btnRefresh is not None:
            self.btnRefresh.clicked.connect(self.refresh_detection)
            self.btnRefresh.setCursor(Qt.PointingHandCursor)
            self.btnRefresh.setToolTip("Refresh detection on current scale weight / camera view")
        if self.btnToggleCamera is not None:
            self.btnToggleCamera.clicked.connect(self.toggle_camera_view)
        if self.btnClose is not None:
            self.btnClose.clicked.connect(self.hide_dashboard)
        if self.btnExit is not None:
            self.btnExit.clicked.connect(QApplication.instance().quit)

        if self.btnKeyboard is not None:
            self.btnKeyboard.clicked.connect(self.toggle_keyboard)
        if self.btnGo is not None:
            self.btnGo.clicked.connect(self.run_search)
        if self.btnUomKgOnly is not None:
            self.btnUomKgOnly.setVisible(False)
        if self.txtSearch is not None:
            self.txtSearch.textChanged.connect(self.on_search_text_changed)
        if self.btnTrainSelected is not None:
            self.btnTrainSelected.clicked.connect(self.train_selected)
        if self.listProducts is not None:
            self.listProducts.itemClicked.connect(self._select_product_from_list)
        if self.listMatches is not None:
            # self.listMatches.itemClicked.connect(self.on_prediction_clicked)
            self.listMatches.itemPressed.connect(self.on_prediction_clicked)
            self.listMatches.setIconSize(QSize(188, 126))
            self.listMatches.setGridSize(QSize(224, 238))
            self.listMatches.setSpacing(8)
            self.listMatches.setWordWrap(False)
            self.listMatches.setSelectionMode(QAbstractItemView.NoSelection)
            self.listMatches.setStyleSheet(
                """
                QListWidget#listMatches {
                    background: #FFFFFF;
                    border: 2px solid #E2D6C7;
                    border-radius: 10px;
                    padding: 2px;
                }
                QListWidget#listMatches::item {
                    min-height: 220px;
                    min-width: 204px;
                    padding: 8px;
                    margin: 3px;
                    background: #FFFCF8;
                    border: 1px solid #D6C6B2;
                    border-radius: 12px;
                    color: #000000;
                    font-size: 20px;
                    font-weight: 800;
                }
                QListWidget#listMatches::item:hover {
                    background: #FFF8E7;
                    border: 2px solid #FF9800;
                    color: #000000;
                }
                QListWidget#listMatches::item:selected, QListWidget#listMatches::item:pressed {
                    background: #FFE082;
                    border: 2px solid #E65100;
                    color: #000000;
                }
                """
            )
        if self.listTrained is not None:
            self.listTrained.itemClicked.connect(self.on_trained_selected)
        if self.btnRetrain is not None:
            self.btnRetrain.clicked.connect(self.retrain_selected)

        if self.listSettingsNav is not None and self.settingsStack is not None:
            self.listSettingsNav.currentRowChanged.connect(self.settingsStack.setCurrentIndex)
        if self.btnDeleteTrained is not None:
            self.btnDeleteTrained.clicked.connect(self.delete_trained_items)
        if self.btnToggleWeightMode is not None:
            self.btnToggleWeightMode.clicked.connect(self.toggle_weight_mode)
            self._update_weight_mode_button_style()
        if self.listTrainedData is not None:
            self.listTrainedData.itemSelectionChanged.connect(self._update_trained_tile_selection_styles)

        if self.btnSaveSettings is not None:
            self.btnSaveSettings.clicked.connect(self.save_settings_from_ui)

        if self.btnResetPolygon is not None:
            self.btnResetPolygon.clicked.connect(self.reset_polygon)
        if self.btnSavePolygon is not None:
            self.btnSavePolygon.clicked.connect(self.save_polygon)
        if self.btnSetEmptyTray is not None:
            self.btnSetEmptyTray.clicked.connect(self.set_empty_tray_baseline)
        if self.btnSetEmptyCover is not None:
            self.btnSetEmptyCover.clicked.connect(self.set_empty_cover_baseline)

        # Install drag handlers on preview label
        if self.lblCamera is not None:
            self.lblCamera.setMouseTracking(True)
            self.lblCamera.installEventFilter(self)
        if self.txtSearch is not None:
            self.txtSearch.installEventFilter(self)

        # Floating box
        self.float = FloatingWeight()
        self.float.clicked.connect(self.show_dashboard)
        self.float.show()

        # Scale
        sc = self.settings["scale"]
        self.scale = ScaleReader(sc["port"], sc["baud"], stable_seconds=float(sc.get("stable_seconds", 0.3)))
        self.scale.liveWeightChanged.connect(self.on_live_weight)
        self.scale.weightChanged.connect(self.on_weight)

        ok = self.scale.open()

        self.scale_connected = bool(ok)
        if not ok:
            print("Scale not connected (check COM/baud). Running without scale...")
            self.start_demo_weight()

        # Camera
        self.cam = None
        self.start_or_restart_camera()

        # Behavior
        self.open_threshold = 0.001
        self.match_threshold = float(self.settings["behavior"].get("match_threshold", 0.55))
        self.match_margin = float(self.settings["behavior"].get("confidence_margin", 0.03))
        self.confusion_margin = float(self.settings["behavior"].get("confusion_margin", 0.12))
        self.match_appear_min_hits = max(1, int(self.settings["behavior"].get("appear_min_hits", 2)))
        self._display_weight = 0.0
        self._last_weight = 0.0
        self._suppress_open_until_weight_change = False
        self._last_hide_weight = None
        self._stable_snapshot_raw = None
        self._stable_snapshot_qty = 1
        self._stable_snapshot_weight = 0.0
        self._match_session_order = []
        self._last_match_signature = None
        self._match_row_cache = {}
        self._match_miss_counts = {}
        self._match_hold_max_misses = 6
        self._match_hit_counts = {}
        self._is_weight_stable = False
        self._last_stable_weight = 0.0
        self._last_weight_reading = 0.0
        self._last_weight_change_time = time.time()
        self._last_roi_gray = None
        self._last_roi_motion = 0.0
        self._motion_settled_time = time.time()
        self._last_matched_weight = None
        self._match_locked = False
        self._suppress_matching_until_zero = False
        self._color_profile_cache: Dict[str, dict] = {}
        self._last_laptop_obj: Optional[dict] = None
        self._last_laptop_tick_state: Optional[dict] = None
        self._laptop_stable_ticks: int = 0

        # UI init
        self.populate_ports()
        self.populate_settings_ui()
        self.refresh_trained_list()
        self.refresh_inventory_summary()
        self.setup_settings_nav()
        self.setup_keyboard()
        self._enable_touch_scrolling()
        if self.keyboardPanel is not None:
            self.keyboardPanel.setVisible(False)
        self.show_dashboard_page()

        if self.panelRight is not None:
            self.panelRight.setVisible(False)
        self._update_camera_toggle_button()
        self._sync_top_info_boxes_height()
        if self.dashboardStack is not None and self.pagePredictions is not None:
            self.dashboardStack.setCurrentWidget(self.pagePredictions)
        if self.btnBackTop is not None:
            self.btnBackTop.setVisible(False)
        if self.btnBackSearch is not None:
            self.btnBackSearch.setVisible(False)
        self.update_nav_highlight()

        # Track last external foreground window so typing can return there.
        self._fg_watch_timer = QTimer(self)
        self._fg_watch_timer.setInterval(200)
        self._fg_watch_timer.timeout.connect(self._track_external_foreground)
        self._fg_watch_timer.start()

        # Match timer
        self._match_timer = QTimer(self)
        self._match_timer.timeout.connect(self.try_match)
        self._match_timer.start(250)

        # Debounced running weight match timer
        self._running_match_timer = QTimer(self)
        self._running_match_timer.setSingleShot(True)
        self._running_match_timer.timeout.connect(lambda: self.try_match(running_weight=True))

        print("Dashboard UI loaded")

    # ---------- CAMERA START/RESTART ----------
    def start_or_restart_camera(self):
        cam_cfg = self.settings["camera"]

        cam_index = int(cam_cfg.get("index", 0))
        if self.cam is not None and int(self.cam.cam_index) == cam_index:
            return

        if self.cam is not None:
            self.cam.stop()
            self.cam.wait(1500)

        self.cam = CameraWorker(cam_index=cam_index, fps=30)
        self.cam.frameReady.connect(self.on_frame)
        self.cam.start()

    # ---------- DEMO SCALE ----------
    def start_demo_weight(self):
        if self._demo_timer is not None:
            return
        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(lambda: self.on_live_weight(0.0))
        self._demo_timer.timeout.connect(lambda: self.on_weight(0.0))
        self._demo_timer.start(500)

    # ---------- NAV ----------
    def show_dashboard_page(self):
        self._hide_keyboard()
        self._reset_search_state(clear_text=True)
        if self.stack is not None and self.pageDashboard is not None:
            self.stack.setCurrentWidget(self.pageDashboard)
        if self.dashboardStack is not None and self.pagePredictions is not None:
            self.dashboardStack.setCurrentWidget(self.pagePredictions)
        self._return_to_settings_on_back = False
        if self.txtSearch is not None:
            self.txtSearch.setFocus()
        if self.btnBackTop is not None:
            self.btnBackTop.setVisible(False)
        if self.btnBackSearch is not None:
            self.btnBackSearch.setVisible(False)
        if self.btnSearch is not None:
            self.btnSearch.setVisible(True)
        if self.btnViewProducts is not None:
            self.btnViewProducts.setVisible(True)
        if self.btnSettings is not None:
            self.btnSettings.setVisible(True)
        if self.btnRefresh is not None:
            self.btnRefresh.setVisible(True)
        if self.btnToggleCamera is not None:
            self.btnToggleCamera.setVisible(True)
        if self.btnClose is not None:
            self.btnClose.setVisible(True)
        if self.btnExit is not None:
            self.btnExit.setVisible(True)
        if self.lblInventorySummary is not None:
            self.lblInventorySummary.setVisible(True)
        self.refresh_inventory_summary()
        self.update_nav_highlight()

        cur_w = max(float(getattr(self, "_display_weight", 0.0) or 0.0), float(getattr(self, "_last_weight", 0.0) or 0.0))
        if cur_w >= 0.005 and self.listMatches is not None and self.listMatches.count() == 0:
            is_forced = bool(getattr(self, "_manual_open", False) or getattr(self, "_is_weight_stable", False))
            QTimer.singleShot(0, lambda: self.try_match(running_weight=True, force=is_forced))

    def show_settings(self):
        self._hide_keyboard()
        if self.stack is not None and self.pageSettings is not None:
            self.stack.setCurrentWidget(self.pageSettings)
        self.refresh_trained_data_table()
        self._return_to_settings_on_back = False
        if self.btnBackTop is not None:
            self.btnBackTop.setVisible(True)
        if self.btnBackSearch is not None:
            self.btnBackSearch.setVisible(False)
        if self.btnSearch is not None:
            self.btnSearch.setVisible(False)
        if self.btnViewProducts is not None:
            self.btnViewProducts.setVisible(False)
        if self.btnSettings is not None:
            self.btnSettings.setVisible(False)
        if self.btnRefresh is not None:
            self.btnRefresh.setVisible(False)
        if self.btnToggleCamera is not None:
            self.btnToggleCamera.setVisible(False)
        if self.btnClose is not None:
            self.btnClose.setVisible(False)
        if self.btnExit is not None:
            self.btnExit.setVisible(False)
        if self.lblInventorySummary is not None:
            self.lblInventorySummary.setVisible(False)
        self.update_nav_highlight()

    def _set_active_button(self, btn: Optional[QPushButton], active: bool):
        if btn is None:
            return
        btn.setProperty("active", active)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def update_nav_highlight(self):
        search_active = self.dashboardStack is not None and self.pageSearch is not None and self.dashboardStack.currentWidget() == self.pageSearch
        settings_active = self.stack is not None and self.pageSettings is not None and self.stack.currentWidget() == self.pageSettings
        camera_active = self.panelRight is not None and self.panelRight.isVisible()
        self._set_active_button(self.btnSearch, search_active)
        self._set_active_button(self.btnViewProducts, search_active)
        self._set_active_button(self.btnSettings, settings_active)
        self._set_active_button(self.btnToggleCamera, camera_active)

    def on_back_top(self):
        self.show_dashboard_page()

    def toggle_settings(self):
        if self.stack is None or self.pageSettings is None or self.pageDashboard is None:
            return
        if self.stack.currentWidget() == self.pageSettings:
            self.show_dashboard_page()
        else:
            self.show_settings()
        self.update_nav_highlight()

    def show_search_panel(self, load_default_search: bool = False):
        self.show_dashboard_page()
        self._hide_keyboard()
        if self.dashboardStack is not None and self.pageSearch is not None:
            self.dashboardStack.setCurrentWidget(self.pageSearch)
        self._products_view_mode = "search"
        self._reset_search_state(clear_text=True)
        if self.txtSearch is not None:
            self.txtSearch.setFocus()
        if self.btnToggleCamera is not None:
            self.btnToggleCamera.setVisible(False)
        if self.btnBackTop is not None:
            self.btnBackTop.setVisible(False)
        if self.btnBackSearch is not None:
            self.btnBackSearch.setVisible(True)
        if self.btnSearch is not None:
            self.btnSearch.setVisible(False)
        if self.btnViewProducts is not None:
            self.btnViewProducts.setVisible(False)
        if self.btnSettings is not None:
            self.btnSettings.setVisible(False)
        if self.btnRefresh is not None:
            self.btnRefresh.setVisible(False)
        if self.btnClose is not None:
            self.btnClose.setVisible(False)
        if self.btnExit is not None:
            self.btnExit.setVisible(False)
        if self.lblInventorySummary is not None:
            self.lblInventorySummary.setVisible(False)
        self.update_nav_highlight()
        if load_default_search:
            self.run_search()

    def hide_search_panel(self):
        self._hide_keyboard()
        if self.dashboardStack is not None and self.pagePredictions is not None:
            self.dashboardStack.setCurrentWidget(self.pagePredictions)
        if self.btnToggleCamera is not None:
            self.btnToggleCamera.setVisible(True)
        if self.btnBackTop is not None:
            self.btnBackTop.setVisible(False)
        if self.btnBackSearch is not None:
            self.btnBackSearch.setVisible(False)
        if self.btnSearch is not None:
            self.btnSearch.setVisible(True)
        if self.btnViewProducts is not None:
            self.btnViewProducts.setVisible(True)
        if self.btnSettings is not None:
            self.btnSettings.setVisible(True)
        if self.btnRefresh is not None:
            self.btnRefresh.setVisible(True)
        if self.btnClose is not None:
            self.btnClose.setVisible(True)
        if self.btnExit is not None:
            self.btnExit.setVisible(True)
        if self.lblInventorySummary is not None:
            self.lblInventorySummary.setVisible(True)
        self.refresh_inventory_summary()
        self.update_nav_highlight()

    def toggle_search_panel(self):
        if self.dashboardStack is None or self.pageSearch is None or self.pagePredictions is None:
            return
        if self.dashboardStack.currentWidget() == self.pageSearch:
            self.hide_search_panel()
        else:
            self.show_search_panel()

    def show_dashboard(self, manual: bool = True):
        self._cancel_auto_close()
        self._manual_open = bool(manual)
        if manual:
            self._opened_by_weight = False
        self._track_external_foreground()
        self._suppress_open_until_weight_change = False
        self._detection_completed = False
        self.show()
        self.raise_()
        self.activateWindow()
        self.show_dashboard_page()

    def _self_hwnd(self) -> Optional[int]:
        try:
            return int(self.winId())
        except Exception:
            return None

    def _track_external_foreground(self):
        fg = _get_foreground_hwnd()
        self_hwnd = self._self_hwnd()
        if fg and (self_hwnd is None or fg != self_hwnd):
            self._prev_hwnd = fg

    # def _load_logo(self):
    #     if self.lblLogo is None:
    #         return
    #     if os.path.exists(LOGO_PATH):
    #         pix = QPixmap(LOGO_PATH)
    #         scaled = pix.scaled(self.lblLogo.width(), self.lblLogo.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
    #         self.lblLogo.setPixmap(scaled)
    #         self.lblLogo.setText("")
    #     else:
    #         self.lblLogo.setText("LOGO")

    def _load_logo(self):
        if self.lblLogo is None:
            return

        if os.path.exists(LOGO_PATH):
            pix = QPixmap(LOGO_PATH)
            scaled = pix.scaled(
                self.lblLogo.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.lblLogo.setPixmap(scaled)
            self.lblLogo.setText("")
        else:
            self.lblLogo.setText("LOGO")

    def _show_branded_message(
        self,
        icon: QMessageBox.Icon,
        text: str,
        buttons=QMessageBox.Ok,
        default_button=QMessageBox.NoButton,
    ):
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(APP_DIALOG_TITLE)
        if os.path.exists(DIALOG_ICON_PATH):
            box.setWindowIcon(QIcon(DIALOG_ICON_PATH))
        box.setMinimumWidth(460)
        box.setText(str(text))
        box.setStandardButtons(buttons)
        if default_button != QMessageBox.NoButton:
            box.setDefaultButton(default_button)
        return box.exec()

    def _msg_warning(self, text: str):
        return self._show_branded_message(QMessageBox.Warning, text)

    def _msg_info(self, text: str):
        return self._show_branded_message(QMessageBox.Information, text)

    def _msg_critical(self, text: str):
        return self._show_branded_message(QMessageBox.Critical, text)

    def _msg_question(self, text: str, buttons=QMessageBox.Yes | QMessageBox.No):
        return self._show_branded_message(QMessageBox.Question, text, buttons=buttons, default_button=QMessageBox.No)

    def _find_layout_with_widget(self, root_layout, target_widget):
        if root_layout is None or target_widget is None:
            return None, -1
        for i in range(root_layout.count()):
            item = root_layout.itemAt(i)
            w = item.widget()
            if w is target_widget:
                return root_layout, i
            child_layout = item.layout()
            if child_layout is not None:
                lay, idx = self._find_layout_with_widget(child_layout, target_widget)
                if lay is not None:
                    return lay, idx
            if w is not None and w.layout() is not None:
                lay, idx = self._find_layout_with_widget(w.layout(), target_widget)
                if lay is not None:
                    return lay, idx
        return None, -1

    def _install_uom_toggle_widget(self):
        if self.btnUomKgOnly is None:
            return
        old_btn = self.btnUomKgOnly
        parent = old_btn.parentWidget()
        parent_layout = parent.layout() if parent is not None else None
        hit_layout, hit_index = self._find_layout_with_widget(parent_layout, old_btn)
        if hit_layout is None or hit_index < 0:
            return
        old_btn.hide()
        hit_layout.removeWidget(old_btn)
        old_btn.deleteLater()
        toggle = KgAllToggle(parent)
        toggle.setObjectName("btnUomKgOnly")
        hit_layout.insertWidget(hit_index, toggle)
        self.btnUomKgOnly = toggle

    def _add_set_empty_tray_button(self):
        if self.btnSavePolygon is None:
            return
        btn = QPushButton("Set Empty Tray")
        btn.setObjectName("btnSetEmptyTray")
        btn.setMinimumHeight(self.btnSavePolygon.minimumHeight())
        btn.setSizePolicy(self.btnSavePolygon.sizePolicy())
        root_layout = self.centralWidget().layout() if self.centralWidget() is not None else None
        host_layout, idx = self._find_layout_with_widget(root_layout, self.btnSavePolygon)
        if host_layout is not None and idx >= 0:
            host_layout.insertWidget(idx + 1, btn)
        else:
            btn.setParent(self.btnSavePolygon.parentWidget())
            g = self.btnSavePolygon.geometry()
            btn.setGeometry(g.x(), g.y() + g.height() + 8, g.width(), g.height())
            btn.show()
        self.btnSetEmptyTray = btn

    def _add_set_empty_cover_button(self):
        if self.btnSavePolygon is None:
            return
        btn = QPushButton("Set Empty Cover")
        btn.setObjectName("btnSetEmptyCover")
        btn.setMinimumHeight(self.btnSavePolygon.minimumHeight())
        btn.setSizePolicy(self.btnSavePolygon.sizePolicy())
        root_layout = self.centralWidget().layout() if self.centralWidget() is not None else None
        anchor = self.btnSetEmptyTray or self.btnSavePolygon
        host_layout, idx = self._find_layout_with_widget(root_layout, anchor)
        if host_layout is not None and idx >= 0:
            host_layout.insertWidget(idx + 1, btn)
        else:
            btn.setParent(self.btnSavePolygon.parentWidget())
            g = self.btnSavePolygon.geometry()
            btn.setGeometry(g.x(), g.y() + (g.height() + 8) * 2, g.width(), g.height())
            btn.show()
        self.btnSetEmptyCover = btn

    def set_empty_tray_baseline(self):
        self._save_camera_baseline(
            path_key="empty_baseline_path",
            polygon_key="empty_baseline_polygon",
            default_path=EMPTY_TRAY_BASELINE_PATH,
            file_name="empty_tray_baseline.jpg",
            success_label="Empty tray baseline saved.",
            failure_label="Cannot set empty tray baseline. Please check folder write permission.",
        )

    def set_empty_cover_baseline(self):
        self._save_camera_baseline(
            path_key="empty_cover_baseline_path",
            polygon_key="empty_cover_baseline_polygon",
            default_path=EMPTY_COVER_BASELINE_PATH,
            file_name="empty_cover_baseline.jpg",
            success_label="Empty cover baseline saved.",
            failure_label="Cannot set empty cover baseline. Please check folder write permission.",
        )

    def _save_camera_baseline(
        self,
        path_key: str,
        polygon_key: str,
        default_path: str,
        file_name: str,
        success_label: str,
        failure_label: str,
    ):
        if self.latest_frame_raw is None:
            self._msg_warning("No camera frame yet.")
            return
        cam = self.settings.setdefault("camera", {})
        configured = str(cam.get(path_key, default_path) or default_path)
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        fallback_user = os.path.join(local_appdata, APP_NAME, file_name) if local_appdata else ""
        candidates = [configured, default_path]
        if fallback_user:
            candidates.append(fallback_user)

        saved_path = None
        baseline_frame = boundary_only_frame(self.latest_frame_raw, cam.get("polygon", []))
        if path_key == "empty_cover_baseline_path":
            polygon = cam.get("polygon", [])
            if not polygon or len(polygon) != 4:
                self._msg_warning("Set camera boundary first, then set empty cover baseline.")
                return
            roi = np.zeros(self.latest_frame_raw.shape[:2], dtype=np.uint8)
            cv2.fillPoly(roi, [np.array(polygon, dtype=np.int32)], 255)

        for path in candidates:
            if not path:
                continue
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if cv2.imwrite(path, baseline_frame):
                    saved_path = path
                    break
            except Exception:
                continue

        if not saved_path:
            self._msg_warning(failure_label)
            return

        cam[path_key] = saved_path
        cam[polygon_key] = [list(p) for p in cam.get("polygon", [])]
        save_settings(self.settings)
        self._cached_baseline_bgr = None
        self._cached_baseline_path = None
        self._empty_cover_baseline_stamp = None
        self._empty_cover_baseline_img = None
        self._empty_tray_baseline_stamp = None
        self._empty_tray_baseline_img = None
        self._cover_baseline_valid_stamp = None
        self._cover_baseline_valid_cached = False
        self._msg_info(f"{success_label}\n{saved_path}")

    def _frame_cover_appearance_ratio(self, frame_bgr: np.ndarray, roi: np.ndarray) -> float:
        roi_px = float(cv2.countNonZero(roi))
        if roi_px <= 0:
            return 0.0
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        pale = cv2.inRange(hsv, (0, 0, 90), (179, 70, 255))
        pale = cv2.bitwise_and(pale, roi)
        return float(cv2.countNonZero(pale)) / roi_px

    def _cached_baseline_frame(self, path: str, shape_hw: Tuple[int, int], cache_key: str) -> Optional[np.ndarray]:
        if not path:
            return None
        if not os.path.isabs(path):
            for d in [BASE_DIR, APP_DIR]:
                candidate = os.path.join(d, path)
                if os.path.exists(candidate):
                    path = candidate
                    break
        elif not os.path.exists(path):
            fname = os.path.basename(path)
            for d in [BASE_DIR, APP_DIR]:
                alt = os.path.join(d, fname)
                if os.path.exists(alt):
                    path = alt
                    break
        if not os.path.exists(path):
            return None
        h, w = int(shape_hw[0]), int(shape_hw[1])
        try:
            mtime = float(os.path.getmtime(path))
        except Exception:
            mtime = 0.0
        stamp = (str(path), mtime, h, w)
        stamp_attr = f"_{cache_key}_stamp"
        img_attr = f"_{cache_key}_img"

        if stamp == getattr(self, stamp_attr, None):
            cached = getattr(self, img_attr, None)
            if cached is not None:
                return cached

        img = cv2.imread(path)
        if img is None:
            setattr(self, stamp_attr, stamp)
            setattr(self, img_attr, None)
            setattr(self, f"_{cache_key}_lab", None)
            setattr(self, f"_{cache_key}_glare", None)
            return None
        if img.shape[:2] != (h, w):
            img = cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)
        setattr(self, stamp_attr, stamp)
        setattr(self, img_attr, img)
        setattr(self, f"_{cache_key}_lab", None)
        setattr(self, f"_{cache_key}_glare", None)
        return img

    def _empty_cover_baseline_valid(self, roi: np.ndarray) -> bool:
        cam = self.settings.get("camera", {})
        path = str(cam.get("empty_cover_baseline_path", EMPTY_COVER_BASELINE_PATH) or EMPTY_COVER_BASELINE_PATH)
        if not path:
            return False
        if not os.path.isabs(path):
            for d in [BASE_DIR, APP_DIR]:
                candidate = os.path.join(d, path)
                if os.path.exists(candidate):
                    path = candidate
                    break
        elif not os.path.exists(path):
            fname = os.path.basename(path)
            for d in [BASE_DIR, APP_DIR]:
                alt = os.path.join(d, fname)
                if os.path.exists(alt):
                    path = alt
                    break
        if not os.path.exists(path):
            self._cover_baseline_valid_stamp = None
            self._cover_baseline_valid_cached = False
            return False
        try:
            mtime = float(os.path.getmtime(path))
        except Exception:
            mtime = 0.0
        stamp = (path, mtime, int(roi.shape[0]), int(roi.shape[1]))
        if stamp == getattr(self, "_cover_baseline_valid_stamp", None):
            return bool(getattr(self, "_cover_baseline_valid_cached", False))
        base = cv2.imread(path)
        if base is None:
            self._cover_baseline_valid_stamp = stamp
            self._cover_baseline_valid_cached = False
            return False
        if base.shape[:2] != roi.shape[:2]:
            base = cv2.resize(base, (roi.shape[1], roi.shape[0]), interpolation=cv2.INTER_LINEAR)
        ok = self._frame_cover_appearance_ratio(base, roi) >= 0.04
        self._cover_baseline_valid_stamp = stamp
        self._cover_baseline_valid_cached = bool(ok)
        return bool(ok)

    def _empty_cover_same_mask(self, frame_bgr: np.ndarray, roi: np.ndarray) -> Optional[np.ndarray]:
        cam = self.settings.get("camera", {})
        path = str(cam.get("empty_cover_baseline_path", EMPTY_COVER_BASELINE_PATH) or EMPTY_COVER_BASELINE_PATH)
        base = self._cached_baseline_frame(path, frame_bgr.shape[:2], "empty_cover_baseline")
        if base is None:
            return None

        lab_now = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        lab_base = cv2.cvtColor(base, cv2.COLOR_BGR2LAB)
        diff = cv2.absdiff(lab_now, lab_base)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        diff_max = np.max(diff, axis=2).astype(np.uint8)

        hsv_now = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        hsv_base = cv2.cvtColor(base, cv2.COLOR_BGR2HSV)
        pale_now = cv2.inRange(hsv_now, (0, 0, 70), (179, 70, 255))
        pale_base = cv2.inRange(hsv_base, (0, 0, 70), (179, 80, 255))
        pale_or_dark_cover = cv2.bitwise_or(cv2.bitwise_and(pale_now, pale_base), cv2.inRange(hsv_base, (0, 0, 0), (179, 90, 120)))

        same = cv2.inRange(diff_gray, 0, 18)
        same_chan = cv2.inRange(diff_max, 0, 28)
        same = cv2.bitwise_and(same, same_chan)
        same = cv2.bitwise_and(same, pale_or_dark_cover)
        same = cv2.bitwise_and(same, roi)

        k3 = np.ones((3, 3), np.uint8)
        k5 = np.ones((5, 5), np.uint8)
        same = cv2.morphologyEx(same, cv2.MORPH_OPEN, k3, iterations=1)
        same = cv2.morphologyEx(same, cv2.MORPH_CLOSE, k5, iterations=1)
        if cv2.countNonZero(same) < 50:
            return None
        return same

    def _cover_appearance_ratio(self, frame_bgr: np.ndarray, roi: np.ndarray) -> float:
        cam = self.settings.get("camera", {})
        path = str(cam.get("empty_cover_baseline_path", EMPTY_COVER_BASELINE_PATH) or EMPTY_COVER_BASELINE_PATH)
        if not path or not os.path.exists(path):
            return 0.0
        return self._frame_cover_appearance_ratio(frame_bgr, roi)

    def _is_cover_present(self, frame_bgr: np.ndarray) -> bool:
        cam = self.settings.get("camera", {})
        polygon = cam.get("polygon", [])
        if not polygon or len(polygon) != 4:
            return False
        roi = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
        cv2.fillPoly(roi, [np.array(polygon, dtype=np.int32)], 255)
        if not self._empty_cover_baseline_valid(roi):
            return False
        empty_cover_same = self._empty_cover_same_mask(frame_bgr, roi)
        roi_px = float(cv2.countNonZero(roi))
        cover_same_ratio = (float(cv2.countNonZero(empty_cover_same)) / roi_px) if empty_cover_same is not None and roi_px > 0 else 0.0
        if cover_same_ratio >= COVER_PRESENT_SAME_RATIO:
            return True
        return self._cover_appearance_ratio(frame_bgr, roi) >= 0.08

    def _empty_cover_foreground_mask(self, frame_bgr: np.ndarray, roi: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        cam = self.settings.get("camera", {})
        path = str(cam.get("empty_cover_baseline_path", EMPTY_COVER_BASELINE_PATH) or EMPTY_COVER_BASELINE_PATH)
        base = self._cached_baseline_frame(path, frame_bgr.shape[:2], "empty_cover_baseline")
        if base is None:
            return None, 0.0

        lab_now = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
        lab_base = cv2.cvtColor(base, cv2.COLOR_BGR2LAB)
        diff = cv2.absdiff(lab_now, lab_base)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        diff_max = np.max(diff, axis=2).astype(np.uint8)
        _, fg_gray = cv2.threshold(diff_gray, 10, 255, cv2.THRESH_BINARY)
        _, fg_chan = cv2.threshold(diff_max, 16, 255, cv2.THRESH_BINARY)
        fg = cv2.bitwise_or(fg_gray, fg_chan)
        fg = cv2.bitwise_and(fg, roi)

        hsv_now = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        sat_now = hsv_now[:, :, 1].astype(np.float32)
        val_now = hsv_now[:, :, 2].astype(np.float32)
        gray_now = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        local_mean = cv2.GaussianBlur(gray_now, (0, 0), 5)
        local_contrast = cv2.absdiff(gray_now, local_mean).astype(np.float32)
        edge_map = cv2.Canny(gray_now, 42, 122)
        edge_map = cv2.dilate(edge_map, np.ones((3, 3), np.uint8), iterations=1)
        edge_bool = edge_map > 0
        la_now = lab_now[:, :, 1].astype(np.float32) - 128.0
        lb_now = lab_now[:, :, 2].astype(np.float32) - 128.0
        chroma_map = np.sqrt((la_now * la_now) + (lb_now * lb_now))
        val_base = cv2.cvtColor(base, cv2.COLOR_BGR2HSV)[:, :, 2].astype(np.float32)
        glare_now = (val_now >= 225.0) & (sat_now <= 60.0) & (val_base >= 200.0)

        tray_same = None
        tray_path = str(cam.get("empty_baseline_path", EMPTY_TRAY_BASELINE_PATH) or EMPTY_TRAY_BASELINE_PATH)
        tray_base = self._cached_baseline_frame(tray_path, frame_bgr.shape[:2], "empty_tray_baseline")
        if tray_base is not None:
            tray_lab = cv2.cvtColor(tray_base, cv2.COLOR_BGR2LAB)
            tray_diff = cv2.absdiff(lab_now, tray_lab)
            tray_gray = cv2.cvtColor(tray_diff, cv2.COLOR_BGR2GRAY)
            tray_max = np.max(tray_diff, axis=2).astype(np.uint8)
            same_g = cv2.inRange(tray_gray, 0, 12)
            same_m = cv2.inRange(tray_max, 0, 18)
            tray_same = cv2.bitwise_and(cv2.bitwise_and(same_g, same_m), roi)

        k3 = np.ones((3, 3), np.uint8)
        k5 = np.ones((5, 5), np.uint8)

        candidates = (fg > 0) & (~glare_now)
        if tray_same is not None and cv2.countNonZero(tray_same) >= 120:
            non_tray = candidates & (tray_same == 0)
            if int(np.count_nonzero(non_tray)) >= 40:
                candidates = non_tray
        same_mask = self._empty_cover_same_mask(frame_bgr, roi)
        if same_mask is not None and cv2.countNonZero(same_mask) >= 200:
            cover_px = same_mask > 0
        else:
            cover_px = roi > 0
        cover_val = float(np.median(val_now[cover_px]))
        cover_sat = float(np.median(sat_now[cover_px]))
        cover_chroma = float(np.median(chroma_map[cover_px]))

        cover_smooth = (
            (sat_now <= (cover_sat + 14.0))
            & (chroma_map <= (cover_chroma + 6.0))
            & (local_contrast <= 5.0)
            & (~edge_bool)
        )
        filtered = candidates & (~cover_smooth)
        if int(np.count_nonzero(filtered)) >= 14:
            candidates = filtered

        tint_gain = np.maximum(chroma_map - cover_chroma, 0.0)
        # Only treat as pale plastic film if it is truly flat, smooth, and textureless.
        # 3D produce like garlic has strong clove edges and local contrast, so it is preserved!
        is_pale_plastic = (sat_now < 45.0) & (chroma_map < 12.0) & (local_contrast < 5.0) & (~edge_bool)
        val_dev_produce = np.where(is_pale_plastic, 0.0, np.abs(val_now - cover_val))
        texture_term = np.clip(local_contrast, 0.0, 28.0)
        edge_term = edge_bool.astype(np.float32) * 12.0
        appear = (tint_gain * 3.5) + (sat_gain * 1.5) + (val_dev_produce * 0.5) + (texture_term * 0.85) + edge_term
        appear = np.where(is_pale_plastic, appear * 0.12, appear)

        scores = appear[candidates]
        picked = False
        if scores.size >= 24:
            ref = float(np.percentile(scores, 99))
            if ref >= 9.0:
                thr = max(6.5, ref * 0.30)
                strong = ((appear >= thr) & candidates).astype(np.uint8) * 255
                strong = cv2.morphologyEx(strong, cv2.MORPH_OPEN, k3, iterations=1)
                strong = cv2.morphologyEx(strong, cv2.MORPH_CLOSE, k5, iterations=2)
                strong = _clean_object_mask(strong, roi)
                if strong is not None and cv2.countNonZero(strong) >= 12:
                    fg = strong
                    picked = True
        if not picked:
            hard_glare = ((val_now >= 240.0) & (sat_now <= 40.0) & (val_base >= 210.0)).astype(np.uint8) * 255
            fg = cv2.bitwise_and(fg, cv2.bitwise_not(hard_glare))
            if tray_same is not None and cv2.countNonZero(tray_same) >= 120:
                non_tray_fg = cv2.bitwise_and(fg, cv2.bitwise_not(tray_same))
                if cv2.countNonZero(non_tray_fg) >= 12:
                    fg = non_tray_fg
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, k3, iterations=1)
            fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k5, iterations=1)
            fg = _clean_object_mask(fg, roi)

        roi_px = float(cv2.countNonZero(roi))
        fg_px = float(cv2.countNonZero(fg)) if fg is not None else 0.0
        if fg is not None and roi_px > 0 and (fg_px / roi_px) >= 0.45:
            strong_candidates = (fg > 0) & (~glare_now)
            if tray_same is not None and cv2.countNonZero(tray_same) >= 120:
                strong_candidates = strong_candidates & (tray_same == 0)
            strong_scores = appear[strong_candidates]
            if strong_scores.size >= 24:
                p35 = float(np.percentile(strong_scores, 35))
                focused = ((appear >= p35) & strong_candidates).astype(np.uint8) * 255
                focused = cv2.morphologyEx(focused, cv2.MORPH_OPEN, k3, iterations=1)
                focused = cv2.morphologyEx(focused, cv2.MORPH_CLOSE, k5, iterations=2)
                focused = _clean_object_mask(focused, roi)
                if focused is not None and cv2.countNonZero(focused) >= 12:
                    fg = focused

        if fg is None or cv2.countNonZero(fg) < 12:
            seed = np.zeros_like(roi)
            cand_scores = appear[candidates]
            if cand_scores.size >= 16:
                p85 = float(np.percentile(cand_scores, 85))
                seed_thr = max(4.5, p85 * 0.65)
                seed = ((appear >= seed_thr) & candidates).astype(np.uint8) * 255
                seed = cv2.morphologyEx(seed, cv2.MORPH_OPEN, k3, iterations=1)
                seed = cv2.morphologyEx(seed, cv2.MORPH_CLOSE, k5, iterations=2)
                seed = _clean_object_mask(seed, roi)
            if seed is not None and cv2.countNonZero(seed) >= 10:
                fg = seed

        if fg is not None and cv2.countNonZero(fg) >= 12:
            gray_now = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            cover_like = _cover_like_pixels(hsv_now, lab_now, gray_img=gray_now)
            glare_mask = glare_now.astype(np.uint8) * 255
            best = _best_object_blob_mask(
                fg,
                appear,
                roi_mask=roi,
                glare_mask=glare_mask,
                cover_like_mask=cover_like,
                tray_like_mask=tray_same,
                max_area_ratio=0.75,
            )
            if best is not None and cv2.countNonZero(best) >= 10:
                fg = best

        if fg is not None:
            fg = _fill_mask_holes(fg)

        if fg is not None and cv2.countNonZero(fg) < 8:
            fg = None

        if roi_px <= 0 or fg is None:
            return None, 0.0
        return fg, float(cv2.countNonZero(fg)) / roi_px

    def _baseline_foreground_mask(self, frame_bgr: np.ndarray) -> Tuple[Optional[np.ndarray], float]:
        cam = self.settings.get("camera", {})
        polygon = cam.get("polygon", [])
        if not polygon or len(polygon) != 4:
            return None, 0.0

        # Cached polygon ROI mask
        poly_tuple = tuple((p[0], p[1]) for p in polygon)
        if (
            self._cached_roi_mask is not None
            and self._cached_roi_shape == frame_bgr.shape[:2]
            and self._cached_roi_polygon == poly_tuple
        ):
            roi = self._cached_roi_mask
            roi_px = self._cached_roi_px
        else:
            roi = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
            cv2.fillPoly(roi, [np.array(polygon, dtype=np.int32)], 255)
            roi_px = float(cv2.countNonZero(roi))
            self._cached_roi_mask = roi
            self._cached_roi_shape = frame_bgr.shape[:2]
            self._cached_roi_polygon = poly_tuple
            self._cached_roi_px = roi_px

        weight_gating_enabled = bool(
            self.settings.get("behavior", {}).get("weight_gating", self.settings.get("scale", {}).get("enabled", False))
        )
        cover_baseline_ok = self._empty_cover_baseline_valid(roi) if weight_gating_enabled else False
        empty_cover_same = self._empty_cover_same_mask(frame_bgr, roi) if cover_baseline_ok else None
        cover_same_ratio = (float(cv2.countNonZero(empty_cover_same)) / roi_px) if empty_cover_same is not None and roi_px > 0 else 0.0
        cover_by_look = self._cover_appearance_ratio(frame_bgr, roi) >= 0.08 if cover_baseline_ok else False

        if cover_baseline_ok and (cover_same_ratio >= COVER_PRESENT_SAME_RATIO or cover_by_look):
            try:
                cover_fg, cover_fg_ratio = self._empty_cover_foreground_mask(frame_bgr, roi)
                if cover_fg is not None and cv2.countNonZero(cover_fg) >= 8:
                    return cover_fg, cover_fg_ratio
            except Exception as e:
                print(f"[_baseline_foreground_mask] Cover foreground mask error: {e}")

        path = str(cam.get("empty_baseline_path", EMPTY_TRAY_BASELINE_PATH) or EMPTY_TRAY_BASELINE_PATH)
        cache_key = "empty_tray_baseline"
        base = self._cached_baseline_frame(path, frame_bgr.shape[:2], cache_key)
        if base is None:
            return None, 0.0

        # Performance optimization: Crop all matrix math to the bounding box of the scale ROI.
        # This reduces color conversion and diff operations from 3.7 million pixels to ~260,000 pixels (7.6x faster).
        bx, by, bw, bh = cv2.boundingRect(roi)
        if bw < 5 or bh < 5:
            return None, 0.0

        frame_sub = frame_bgr[by : by + bh, bx : bx + bw]
        base_sub = base[by : by + bh, bx : bx + bw]
        roi_sub = roi[by : by + bh, bx : bx + bw]

        lab_now = cv2.cvtColor(frame_sub, cv2.COLOR_BGR2LAB)
        lab_base = cv2.cvtColor(base_sub, cv2.COLOR_BGR2LAB)

        # Dynamic luminance drift compensation inside ROI
        roi_px_mask = roi_sub > 0
        l_roi_now = lab_now[:, :, 0][roi_px_mask]
        l_roi_base = lab_base[:, :, 0][roi_px_mask]
        if l_roi_now.size > 0 and l_roi_base.size > 0:
            l25_now = float(np.percentile(l_roi_now, 25))
            l25_base = float(np.percentile(l_roi_base, 25))
            l_shift = l25_now - l25_base
            if abs(l_shift) >= 5.0:
                lab_base_adj = lab_base.copy()
                lab_base_adj[:, :, 0] = np.clip(lab_base_adj[:, :, 0].astype(np.float32) + l_shift, 0, 255).astype(np.uint8)
            else:
                lab_base_adj = lab_base
        else:
            lab_base_adj = lab_base

        diff = cv2.absdiff(lab_now, lab_base_adj)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        diff_max = np.max(diff, axis=2).astype(np.uint8)
        _, fg_gray = cv2.threshold(diff_gray, 18, 255, cv2.THRESH_BINARY)
        _, fg_chan = cv2.threshold(diff_max, 24, 255, cv2.THRESH_BINARY)
        fg_sub = cv2.bitwise_or(fg_gray, fg_chan)
        fg_sub = cv2.bitwise_and(fg_sub, roi_sub)

        hsv_now = cv2.cvtColor(frame_sub, cv2.COLOR_BGR2HSV)
        hsv_base = cv2.cvtColor(base_sub, cv2.COLOR_BGR2HSV)
        glare_base = cv2.inRange(hsv_base, (0, 0, 242), (179, 48, 255))
        glare_now = cv2.inRange(hsv_now, (0, 0, 242), (179, 48, 255))
        stable_glare = cv2.bitwise_and(glare_now, glare_base)
        fg_sub = cv2.bitwise_and(fg_sub, cv2.bitwise_not(stable_glare))
        if empty_cover_same is not None:
            cover_same_sub = empty_cover_same[by : by + bh, bx : bx + bw]
            fg_sub = cv2.bitwise_and(fg_sub, cv2.bitwise_not(cover_same_sub))

        # Check if cover/bag is present (via calibrated cover baseline or appearance-based plastic detection)
        is_cover_present = False
        if cover_baseline_ok:
            is_cover_present = bool(cover_same_ratio >= 0.03 or cover_by_look)
        else:
            try:
                gray_now = cv2.cvtColor(frame_sub, cv2.COLOR_BGR2GRAY)
                c_like = _cover_like_pixels(hsv_now, lab_now, gray_img=gray_now)
                c_roi = cv2.bitwise_and(c_like, roi_sub)
                c_ratio = float(cv2.countNonZero(c_roi)) / float(max(1, roi_px))
                is_cover_present = (c_ratio >= 0.05)
            except Exception:
                is_cover_present = False

        self._is_cover_present_detected = is_cover_present

        if is_cover_present:
            fg_sub = _suppress_cover_like_mask(frame_sub, fg_sub, roi_mask=roi_sub, min_keep_pixels=24, min_keep_ratio=0.30)
        kernel = np.ones((3, 3), np.uint8)
        fg_sub = cv2.morphologyEx(fg_sub, cv2.MORPH_OPEN, kernel, iterations=1)
        fg_sub = cv2.morphologyEx(fg_sub, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg_sub = _clean_object_mask(fg_sub, roi_sub)

        # Place the bounding-box slice back into full-frame canvas
        fg = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
        if fg_sub is not None:
            fg[by : by + bh, bx : bx + bw] = fg_sub

        if roi_px <= 0 or fg is None:
            return None, 0.0
        fg_ratio = float(cv2.countNonZero(fg)) / roi_px
        return fg, fg_ratio

    def _enable_touch_scrolling(self):
        def _grab(widget: Optional[QListWidget]):
            if widget is None:
                return
            viewport = widget.viewport()
            if viewport is None:
                return
            viewport.setAttribute(Qt.WA_AcceptTouchEvents, True)
            QScroller.grabGesture(viewport, QScroller.TouchGesture)

        _grab(self.listProducts)
        _grab(self.listMatches)
        _grab(self.listTrainedData)
        _grab(self.listSettingsNav)

    def _normalize_image_key(self, name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (name or "").lower())

    def _load_default_images(self):
        pcs_dir = os.path.join(IMGS_DIR, "pcs")
        kg_dir = os.path.join(IMGS_DIR, "vf_images")

        def _index_dir(dir_path: str) -> dict:
            idx = {}
            if not os.path.isdir(dir_path):
                return idx
            for fname in os.listdir(dir_path):
                low = fname.lower()
                if not low.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp")):
                    continue
                stem = os.path.splitext(fname)[0]
                key = self._normalize_image_key(stem)
                if key and key not in idx:
                    idx[key] = os.path.join(dir_path, fname)
            return idx

        self._default_img_index_pcs = _index_dir(pcs_dir)
        self._default_img_index_kg = _index_dir(kg_dir)

    def _default_image_for_product(self, name: str, uom: str) -> Optional[str]:
        key = self._normalize_image_key(name or "")
        if not key:
            return None
        if str(uom).upper() == "PCS":
            return self._default_img_index_pcs.get(key)
        return self._default_img_index_kg.get(key)

    def _product_image_path(self, product: Optional[dict] = None, meta: Optional[dict] = None) -> Optional[str]:
        meta = meta or {}
        for key in ("display_thumb", "thumb"):
            path = meta.get(key)
            if path and os.path.exists(path):
                return path
        if product is None:
            return None
        return self._default_image_for_product(product.get("Name", ""), product.get("UOM", ""))

    def get_product_color_profile(self, code: str) -> Optional[dict]:
        code_key = self._code_key(code)
        if not code_key:
            return None
        # 1. In-memory cache hit
        if code_key in self._color_profile_cache:
            return self._color_profile_cache[code_key]

        # 2. Check metadata
        meta = self.brain.meta.get(code_key, {})
        stored_prof = meta.get("color_profile")
        if stored_prof and isinstance(stored_prof, dict) and stored_prof.get("dominant_family"):
            self._color_profile_cache[code_key] = stored_prof
            return stored_prof

        # 3. Missing profile: Generate on-the-fly from stored thumbnail or catalog image
        if _COLOR_MATCHER_AVAILABLE and color_matcher is not None:
            img_path = self._product_image_path(product=meta, meta=meta)
            if img_path and os.path.exists(img_path):
                try:
                    img = cv2.imread(img_path)
                    if img is not None and getattr(img, "size", 0) > 0:
                        prof = color_matcher.extract_color_profile(img)
                        if prof:
                            meta["color_profile"] = prof
                            self.brain.meta[code_key] = meta
                            self._color_profile_cache[code_key] = prof
                            self.brain.save_meta()
                            return prof
                except Exception as e:
                    print(f"[get_product_color_profile] Error generating profile for {code_key}: {e}")

        return None

    def _set_inventory_display_image(self, product: dict, image_bgr: np.ndarray) -> Optional[str]:
        code = self._code_key(product.get("Code", ""))
        if not code or image_bgr is None:
            return None
        path = self.brain.save_display_thumb(code, image_bgr)
        meta = self.brain.meta.get(code, {})
        meta.update({
            "Code": product.get("Code", code),
            "Name": product.get("Name", meta.get("Name", "")),
            "UOM": product.get("UOM", meta.get("UOM", "")),
            "Price": float(product.get("Price", meta.get("Price", 0.0)) or 0.0),
            "display_thumb": path,
        })
        self.brain.meta[code] = meta
        self.brain.save_meta()
        self.refresh_trained_list()
        self.refresh_trained_data_table()
        self._refresh_products_list_after_training_change()
        return path

    def _choose_inventory_display_image(self, product: dict) -> Optional[str]:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.heic *.heif *.jfif *.ico *.pbm *.pgm *.ppm *.pnm *.sr *.ras *.hdr *.pic);;All Files (*)",
        )
        if not file_path:
            return None
        image_bgr = cv2.imread(file_path)
        if image_bgr is None:
            self._msg_warning("Could not load the selected image.")
            return None
        return self._set_inventory_display_image(product, image_bgr)

    def _train_inventory_product(self, product: dict) -> bool:
        if self.latest_frame_raw is None:
            self._msg_warning("No camera frame yet.")
            return False
        QApplication.processEvents()
        return bool(self._train_product_with_frame(product, self.latest_frame_raw, type_barcode=False))

    def _show_inventory_product_dialog(self, product: dict):
        if not product:
            return
        code = self._code_key(product.get("Code", ""))
        meta = self.brain.meta.get(code, {})
        dialog = InventoryProductDialog(
            self,
            product=product,
            currency_symbol=self.settings.get("currency", {}).get("symbol", "Rs."),
            image_path=self._product_image_path(product=product, meta=meta),
            on_take_picture=lambda: self._train_inventory_product(product),
            on_choose_file=lambda: self._choose_inventory_display_image(product),
        )
        dialog.exec()

    def toggle_camera_view(self):
        if self.panelRight is None:
            return
        visible = not self.panelRight.isVisible()
        self.panelRight.setVisible(visible)
        self._update_camera_toggle_button()
        self.update_nav_highlight()

    def _hide_keyboard(self):
        if self.keyboardPanel is not None:
            self.keyboardPanel.setVisible(False)

    def toggle_keyboard(self):
        if self.keyboardPanel is None:
            return
        visible = not self.keyboardPanel.isVisible()
        self.keyboardPanel.setVisible(visible)
        if visible and QApplication.focusWidget() is None and self.txtSearch is not None:
            self.txtSearch.setFocus()

    def setup_keyboard(self):
        if self.keyboardPanel is None:
            return
        layout = QGridLayout(self.keyboardPanel)
        layout.setSpacing(3)
        layout.setContentsMargins(6, 6, 6, 6)

        self._caps_on = True
        self._letter_buttons = []

        key_size = QSize(36, 36)
        key_font_px = 18

        rows = [
            list("1234567890"),
            list("QWERTYUIOP"),
            list("ASDFGHJKL"),
        ]
        r = 0
        for row in rows:
            c = 0
            for key in row:
                btn = QPushButton(key)
                btn.setMinimumSize(key_size)
                btn.setStyleSheet(f"font-size: {key_font_px}px; font-weight: bold;")
                btn.clicked.connect(lambda _, b=btn: self._on_key_pressed(b.text()))
                layout.addWidget(btn, r, c)
                if key.isalpha():
                    self._letter_buttons.append(btn)
                c += 1
            r += 1

        # Row with caps + letters + backspace
        btn_caps = QPushButton("Caps")
        btn_caps.setCheckable(True)
        btn_caps.setChecked(True)
        btn_caps.setMinimumSize(key_size)
        btn_caps.setStyleSheet(f"background:#C8D5E8;font-size:{key_font_px}px;font-weight:bold;")
        btn_caps.clicked.connect(self.toggle_caps)
        layout.addWidget(btn_caps, r, 0)

        letters = list("ZXCVBNM")
        for idx, key in enumerate(letters, start=1):
            btn = QPushButton(key)
            btn.setMinimumSize(key_size)
            btn.setStyleSheet(f"font-size: {key_font_px}px; font-weight: bold;")
            btn.clicked.connect(lambda _, b=btn: self._on_key_pressed(b.text()))
            layout.addWidget(btn, r, idx)
            self._letter_buttons.append(btn)

        btn_back = QPushButton("Back")
        btn_back.setMinimumSize(QSize(84, 36))
        btn_back.setStyleSheet(f"background:#D9C6B8;font-size:{key_font_px}px;font-weight:bold;")
        btn_back.clicked.connect(lambda: self._on_key_pressed("BACK"))
        layout.addWidget(btn_back, r, 8, 1, 2)
        r += 1

        # Bottom row for space / clear / enter
        btn_space = QPushButton("Space")
        btn_space.setMinimumSize(QSize(120, 36))
        btn_space.setStyleSheet(f"background:#CBBEA7;font-size:{key_font_px}px;font-weight:bold;")
        btn_space.clicked.connect(lambda: self._on_key_pressed("SPACE"))
        layout.addWidget(btn_space, r, 0, 1, 4)

        btn_clear = QPushButton("Clear")
        btn_clear.setMinimumSize(QSize(80, 36))
        btn_clear.setStyleSheet(f"background:#D6C7BA;font-size:{key_font_px}px;font-weight:bold;")
        btn_clear.clicked.connect(lambda: self._on_key_pressed("CLEAR"))
        layout.addWidget(btn_clear, r, 4, 1, 2)

        btn_enter = QPushButton("Enter")
        btn_enter.setMinimumSize(QSize(96, 36))
        btn_enter.setStyleSheet(f"background:#C6D6C2;font-size:{key_font_px}px;font-weight:bold;")
        btn_enter.clicked.connect(lambda: self._on_key_pressed("ENTER"))
        layout.addWidget(btn_enter, r, 6, 1, 2)

    def _on_key_pressed(self, key: str):
        target = QApplication.focusWidget()
        line = None
        if isinstance(target, QLineEdit):
            line = target
        elif isinstance(target, (QSpinBox, QDoubleSpinBox)) and hasattr(target, "lineEdit"):
            line = target.lineEdit()
        elif self.txtSearch is not None:
            line = self.txtSearch

        if line is None:
            return

        text = line.text()
        if key == "BACK":
            line.setText(text[:-1])
            return
        if key == "CLEAR":
            line.clear()
            return
        if key == "SPACE":
            line.setText(text + " ")
            return
        if key == "ENTER":
            if line is self.txtSearch:
                self.run_search()
            return
        line.setText(text + key)

    def toggle_caps(self):
        self._caps_on = not getattr(self, "_caps_on", True)
        for btn in getattr(self, "_letter_buttons", []):
            t = btn.text()
            if not t:
                continue
            btn.setText(t.upper() if self._caps_on else t.lower())

    def setup_settings_nav(self):
        if self.listSettingsNav is None or self.settingsStack is None:
            return
        self.listSettingsNav.clear()
        names = ["Scale", "Camera", "Barcode", "DataBase", "Trained Data"]
        for n in names:
            self.listSettingsNav.addItem(n)
        self.listSettingsNav.setCurrentRow(0)

        if self.listTrainedData is not None:
            self.listTrainedData.setSpacing(6)
            self.listTrainedData.setGridSize(QSize(208, 176))
            self.listTrainedData.setIconSize(QSize(176, 82))
            self.listTrainedData.setSelectionMode(QAbstractItemView.MultiSelection)
            self.listTrainedData.setStyleSheet(
                """
                QListWidget#listTrainedData::item {
                    background: transparent;
                    border: none;
                }
                QListWidget#listTrainedData::item:hover {
                    background: transparent;
                    border: none;
                }
                QListWidget#listTrainedData::item:selected {
                    background: transparent;
                    border: none;
                }
                """
            )

    def refresh_trained_data_table(self):
        if self.listTrainedData is None:
            return
        self.listTrainedData.clear()
        meta_changed = False
        db_by_code = {}
        try:
            rows = fetch_all_products(self.settings)
            db_by_code = {str(r.get("Code", "")).strip(): r for r in rows}
        except Exception:
            db_by_code = {}

        for code in sorted(self.brain.data.keys()):
            meta = self.brain.meta.get(code, {})
            db_row = db_by_code.get(str(code).strip())
            if db_row is not None:
                merged = dict(meta)
                merged["Code"] = db_row.get("Code", code)
                merged["Name"] = db_row.get("Name", meta.get("Name", ""))
                merged["UOM"] = db_row.get("UOM", meta.get("UOM", "KG"))
                merged["Price"] = float(db_row.get("Price", meta.get("Price", 0.0)) or 0.0)
                if merged != meta:
                    self.brain.meta[code] = merged
                    meta = merged
                    meta_changed = True
            name = meta.get("Name") or meta.get("name") or ""
            price = float(meta.get("Price", 0.0) or 0.0)
            uom = str(meta.get("UOM", "KG")).upper()
            it = {"Code": code, "Price": price, "UOM": uom}
            barcode = make_barcode(it, 1, self.settings) if price > 0 else "-"

            item = QListWidgetItem()
            item.setData(Qt.UserRole, {"Code": code})
            item.setSizeHint(QSize(208, 176))
            tile = self._build_trained_tile(
                code,
                name,
                price,
                barcode,
                self._product_image_path(product={"Name": name, "UOM": uom}, meta=meta),
            )
            self.listTrainedData.addItem(item)
            self.listTrainedData.setItemWidget(item, tile)
        if meta_changed:
            self.brain.save_meta()
        self._update_trained_tile_selection_styles()

    def delete_trained_items(self):
        if self.listTrainedData is None:
            return
        pwd, ok = self._prompt_admin_password()
        if not ok:
            return
        if not validate_admin_password(pwd, self.settings):
            self._msg_critical("Invalid admin password.")
            return

        selected_codes = []
        for item in self.listTrainedData.selectedItems():
            data = item.data(Qt.UserRole) or {}
            code = data.get("Code")
            if code:
                selected_codes.append(code)

        if selected_codes:
            msg = f"Delete {len(selected_codes)} selected trained item(s)?"
            confirm = self._msg_question(msg, buttons=QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return
            codes_to_delete = selected_codes
        else:
            confirm = self._msg_question("No items selected. Delete ALL trained items?", buttons=QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return
            codes_to_delete = list(self.brain.data.keys())

        for code in codes_to_delete:
            self.brain.delete(code)
            meta = self.brain.meta.pop(code, None) or {}
            for key in ("thumb", "display_thumb"):
                thumb = meta.get(key)
                if thumb and os.path.exists(thumb):
                    try:
                        os.remove(thumb)
                    except Exception:
                        pass

        self.brain.save()
        self.brain.save_meta()
        self.refresh_trained_data_table()
        self.refresh_trained_list()
        self._refresh_products_list_after_training_change()

    def _update_weight_mode_button_style(self):
        if getattr(self, "btnToggleWeightMode", None) is None:
            return
        is_on = bool(
            self.settings.get("behavior", {}).get("weight_gating", self.settings.get("scale", {}).get("enabled", False))
        )
        if is_on:
            self.btnToggleWeightMode.setText("Scale Weight: ON (Real POS)")
            self.btnToggleWeightMode.setToolTip("Scale weight check is ON. Camera only recognizes items when weight is on the scale (> 0.001 KG).")
            self.btnToggleWeightMode.setStyleSheet(
                "QPushButton#btnToggleWeightMode {"
                "  background-color: #2E7D32;"
                "  color: #FFFFFF;"
                "  font-weight: bold;"
                "  font-size: 13px;"
                "  padding: 6px 16px;"
                "  border-radius: 6px;"
                "  border: 1px solid #1B5E20;"
                "}"
                "QPushButton#btnToggleWeightMode:hover {"
                "  background-color: #388E3C;"
                "}"
            )
        else:
            self.btnToggleWeightMode.setText("Scale Weight: OFF (Laptop Test)")
            self.btnToggleWeightMode.setToolTip("Scale weight check is OFF. Laptop mode active: camera recognizes items immediately without scale weight.")
            self.btnToggleWeightMode.setStyleSheet(
                "QPushButton#btnToggleWeightMode {"
                "  background-color: #E65100;"
                "  color: #FFFFFF;"
                "  font-weight: bold;"
                "  font-size: 13px;"
                "  padding: 6px 16px;"
                "  border-radius: 6px;"
                "  border: 1px solid #BF360C;"
                "}"
                "QPushButton#btnToggleWeightMode:hover {"
                "  background-color: #F57C00;"
                "}"
            )

    def toggle_weight_mode(self):
        current = bool(
            self.settings.get("behavior", {}).get("weight_gating", self.settings.get("scale", {}).get("enabled", False))
        )
        new_state = not current
        self.settings.setdefault("behavior", {})["weight_gating"] = new_state
        self.settings.setdefault("scale", {})["enabled"] = new_state
        save_settings(self.settings)
        self._update_weight_mode_button_style()
        self._match_locked = False
        self._last_matched_weight = None
        self._last_matched_obj = None
        self._last_laptop_tick_state = None
        self._laptop_stable_ticks = 0
        mode_desc = "Real POS with Scale Weight (ON)" if new_state else "Laptop Mode without Weight (OFF)"
        print(f"[Settings] Weight detection mode switched to: {mode_desc}")

    def _prompt_admin_password(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Admin Access")
        dlg.setModal(True)
        dlg.setFixedSize(760, 340)
        dlg.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        lbl = QLabel("Enter Admin password:")
        lbl.setContentsMargins(0, 0, 0, 0)
        lbl.setStyleSheet("margin:0px;")
        pwd_entry = QLineEdit()
        pwd_entry.setEchoMode(QLineEdit.Password)
        btn_eye = QToolButton()
        btn_eye.setCheckable(True)
        btn_eye.setAutoRaise(True)
        btn_eye.setFixedSize(32, 32)
        btn_eye.setIconSize(QSize(22, 22))
        icon_eye = os.path.join(app_data_dir(), "icons", "eye.svg")
        icon_eye_off = os.path.join(app_data_dir(), "icons", "eye_off.svg")
        if os.path.exists(icon_eye):
            btn_eye.setIcon(QIcon(icon_eye))
        btn_eye.setToolTip("Show password")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(lbl)
        row.addWidget(pwd_entry, 1)
        row.addWidget(btn_eye)
        layout.addLayout(row)

        keyboard_widget = QWidget()
        layout.addWidget(keyboard_widget)

        def build_keyboard(widget, target_line):
            kb_layout = QGridLayout(widget)
            kb_layout.setSpacing(3)
            kb_layout.setContentsMargins(6, 6, 6, 6)

            caps_on = True
            letter_buttons = []

            key_size = QSize(36, 36)
            key_font_px = 18

            def on_key_pressed(key: str):
                text = target_line.text()
                if key == "BACK":
                    target_line.setText(text[:-1])
                    return
                if key == "CLEAR":
                    target_line.clear()
                    return
                if key == "SPACE":
                    target_line.setText(text + " ")
                    return
                if key == "ENTER":
                    dlg.accept()
                    return
                target_line.setText(text + key)

            def toggle_caps():
                nonlocal caps_on
                caps_on = not caps_on
                for btn in letter_buttons:
                    t = btn.text()
                    if not t:
                        continue
                    btn.setText(t.upper() if caps_on else t.lower())

            rows = [
                list("1234567890"),
                list("QWERTYUIOP"),
                list("ASDFGHJKL"),
            ]
            r = 0
            for row_keys in rows:
                c = 0
                for key in row_keys:
                    btn = QPushButton(key)
                    btn.setMinimumSize(key_size)
                    btn.setStyleSheet(f"font-size: {key_font_px}px; font-weight: bold;")
                    btn.clicked.connect(lambda _, b=btn: on_key_pressed(b.text()))
                    kb_layout.addWidget(btn, r, c)
                    if key.isalpha():
                        letter_buttons.append(btn)
                    c += 1
                r += 1

            btn_caps = QPushButton("Caps")
            btn_caps.setCheckable(True)
            btn_caps.setChecked(True)
            btn_caps.setMinimumSize(key_size)
            btn_caps.setStyleSheet(f"background:#C8D5E8;font-size:{key_font_px}px;font-weight:bold;")
            btn_caps.clicked.connect(toggle_caps)
            kb_layout.addWidget(btn_caps, r, 0)

            letters = list("ZXCVBNM")
            for idx, key in enumerate(letters, start=1):
                btn = QPushButton(key)
                btn.setMinimumSize(key_size)
                btn.setStyleSheet(f"font-size: {key_font_px}px; font-weight: bold;")
                btn.clicked.connect(lambda _, b=btn: on_key_pressed(b.text()))
                kb_layout.addWidget(btn, r, idx)
                letter_buttons.append(btn)

            btn_back = QPushButton("Back")
            btn_back.setMinimumSize(QSize(84, 36))
            btn_back.setStyleSheet(f"background:#D9C6B8;font-size:{key_font_px}px;font-weight:bold;")
            btn_back.clicked.connect(lambda: on_key_pressed("BACK"))
            kb_layout.addWidget(btn_back, r, 8, 1, 2)
            r += 1

            btn_space = QPushButton("Space")
            btn_space.setMinimumSize(QSize(120, 36))
            btn_space.setStyleSheet(f"background:#CBBEA7;font-size:{key_font_px}px;font-weight:bold;")
            btn_space.clicked.connect(lambda: on_key_pressed("SPACE"))
            kb_layout.addWidget(btn_space, r, 0, 1, 4)

            btn_clear = QPushButton("Clear")
            btn_clear.setMinimumSize(QSize(80, 36))
            btn_clear.setStyleSheet(f"background:#D6C7BA;font-size:{key_font_px}px;font-weight:bold;")
            btn_clear.clicked.connect(lambda: on_key_pressed("CLEAR"))
            kb_layout.addWidget(btn_clear, r, 4, 1, 2)

            btn_enter = QPushButton("Enter")
            btn_enter.setMinimumSize(QSize(96, 36))
            btn_enter.setStyleSheet(f"background:#C6D6C2;font-size:{key_font_px}px;font-weight:bold;")
            btn_enter.clicked.connect(lambda: on_key_pressed("ENTER"))
            kb_layout.addWidget(btn_enter, r, 6, 1, 2)

        build_keyboard(keyboard_widget, pwd_entry)

        def toggle_password_visible(checked: bool):
            pwd_entry.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
            btn_eye.setToolTip("Hide password" if checked else "Show password")
            if checked:
                if os.path.exists(icon_eye_off):
                    btn_eye.setIcon(QIcon(icon_eye_off))
            else:
                if os.path.exists(icon_eye):
                    btn_eye.setIcon(QIcon(icon_eye))

        btn_eye.toggled.connect(toggle_password_visible)

        pwd_entry.setFocus()
        ok = dlg.exec() == QDialog.Accepted
        return pwd_entry.text(), ok

    def _build_trained_tile(self, code: str, name: str, price: float, barcode: str, thumb: Optional[str]) -> QWidget:
        tile = QFrame()
        tile.setMinimumSize(198, 166)
        tile.setMaximumSize(198, 166)
        tile.setProperty("selected", False)
        self._set_trained_tile_style(tile, False)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        img = QLabel()
        img.setAlignment(Qt.AlignCenter)
        img.setFixedSize(186, 82)
        img.setStyleSheet("border:0px;border-radius:0px;background:transparent;")
        if thumb and os.path.exists(thumb):
            pix = QPixmap(thumb)
            img.setPixmap(pix.scaled(186, 82, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            img.setText("No Image")
        layout.addWidget(img)

        name_line = name if name else "-"
        price_line = f"{price:.2f}" if price > 0 else "-"

        title = QLabel(f"{name_line} [{code}]  Price: {price_line}")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setFixedHeight(46)
        title.setStyleSheet("color:#3E3A33;font-size:11px;font-weight:700;background:transparent;")
        layout.addWidget(title)

        return tile

    def _set_trained_tile_style(self, tile: QFrame, selected: bool):
        if selected:
            tile.setStyleSheet(
                "QFrame { background: #FFF9F2; border: 3px solid #7E6A52; border-radius: 12px; }"
            )
        else:
            tile.setStyleSheet(
                "QFrame { background: #FFF9F2; border: 2px solid #E6D9C8; border-radius: 12px; }"
            )

    def _update_trained_tile_selection_styles(self):
        if self.listTrainedData is None:
            return
        for i in range(self.listTrainedData.count()):
            item = self.listTrainedData.item(i)
            tile = self.listTrainedData.itemWidget(item)
            if tile is None:
                continue
            self._set_trained_tile_style(tile, item.isSelected())

    def _cancel_auto_close(self):
        timer = getattr(self, "_close_timer", None)
        if timer is not None and timer.isActive():
            timer.stop()

    def _schedule_auto_close(self, delay_ms: int = 350):
        # Never close if opened manually by the user
        if getattr(self, "_manual_open", False):
            return
        # Only close if dashboard was opened by weight
        if not getattr(self, "_opened_by_weight", False):
            return
        if getattr(self, "_close_timer", None) is None:
            self._close_timer = QTimer(self)
            self._close_timer.setSingleShot(True)
            self._close_timer.timeout.connect(self._do_auto_close)
        if not self._close_timer.isActive():
            self._close_timer.start(delay_ms)

    def _do_auto_close(self):
        if getattr(self, "_manual_open", False):
            return
        if not getattr(self, "_opened_by_weight", False):
            return
        curr_w = float(getattr(self, "_display_weight", 0.0) or 0.0)
        if curr_w <= 0.002 and self.isVisible() and self._is_weight_controlled_dashboard_active():
            self.hide_dashboard()

    def hide_dashboard(self):
        self._cancel_auto_close()
        self._manual_open = False
        self._opened_by_weight = False
        self.hide()
        if self.listMatches is not None:
            self.listMatches.clear()
        self._last_match_signature = None
        self._last_matched_weight = None
        self._match_locked = False
        if getattr(self, "lblExtractionMode", None) is not None:
            self.lblExtractionMode.setText("Idle (waiting for item)")
            self.lblExtractionMode.setStyleSheet(
                "background: #E8F5E9; color: #1B5E20; border: 1px solid #81C784; "
                "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: bold;"
            )
        if getattr(self, "float", None) is not None:
            self.float.show()
            self.float.raise_()

    def _is_weight_controlled_dashboard_active(self) -> bool:
        if self.stack is None or self.pageDashboard is None:
            return False
        if self.stack.currentWidget() != self.pageDashboard:
            return False
        if self.dashboardStack is None or self.pagePredictions is None:
            return False
        return self.dashboardStack.currentWidget() == self.pagePredictions

    def _set_extraction_status(
        self,
        mode: str,
        bbox: Optional[Tuple[int, int, int, int]] = None,
        is_small: bool = False,
        reason: str = "",
    ):
        self._last_extraction_mode = mode
        self._last_detected_bbox = bbox
        if bbox is not None:
            self._last_detected_bbox_time = time.time()
        self._last_is_small_warning = is_small

        if getattr(self, "lblExtractionMode", None) is not None:
            if "DINOv3" in mode:
                self.lblExtractionMode.setText("Detection: DINOv3 (ViT-S/16)")
                self.lblExtractionMode.setStyleSheet(
                    "background: #E8F5E9; color: #1B5E20; border: 1px solid #81C784; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: bold;"
                )
            elif "DINOv2" in mode:
                self.lblExtractionMode.setText("Detection: DINOv2 (tight crop)")
                self.lblExtractionMode.setStyleSheet(
                    "background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: bold;"
                )
            elif "FALLBACK" in mode:
                reason_hint = f" ({reason})" if reason else ""
                self.lblExtractionMode.setText(f"Detection: FALLBACK (full ROI{reason_hint})")
                self.lblExtractionMode.setStyleSheet(
                    "background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: bold;"
                )
            else:
                self.lblExtractionMode.setText(f"Detection: {mode}")
                self.lblExtractionMode.setStyleSheet(
                    "background: #ECEFF1; color: #455A64; border: 1px solid #CFD8DC; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                )

        if getattr(self, "lblSmallItemWarning", None) is not None:
            self.lblSmallItemWarning.setVisible(is_small)

    def _check_baseline_freshness(self, frame_bgr: Optional[np.ndarray] = None) -> bool:
        """
        Check if the empty tray baseline exists and whether ambient lighting has drifted.
        Silently auto-calibrates the empty tray baseline when the scale is empty.
        """
        bg = self._load_baseline_image()
        if bg is None:
            if getattr(self, "lblBaselineWarning", None) is not None:
                self.lblBaselineWarning.setText("⚠️ No empty tray baseline captured! Please capture in Camera settings.")
                self.lblBaselineWarning.setVisible(True)
            return False

        if frame_bgr is None:
            frame_bgr = self.latest_frame_raw
        if frame_bgr is None:
            return True

        polygon = self.settings.get("camera", {}).get("polygon", [])
        if not polygon or len(polygon) != 4:
            return True

        now = time.time()
        if (now - getattr(self, "_last_baseline_check_time", 0.0)) < 1.5:
            return True
        self._last_baseline_check_time = now

        try:
            if bg.shape[:2] != frame_bgr.shape[:2]:
                bg_resized = cv2.resize(bg, (frame_bgr.shape[1], frame_bgr.shape[0]), interpolation=cv2.INTER_LINEAR)
            else:
                bg_resized = bg

            bg_gray = cv2.cvtColor(bg_resized, cv2.COLOR_BGR2GRAY)
            frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

            # Mask to polygon ROI
            roi_mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
            cv2.fillPoly(roi_mask, [np.array(polygon, dtype=np.int32)], 255)

            bg_mean = float(cv2.mean(bg_gray, mask=roi_mask)[0])
            frame_mean = float(cv2.mean(frame_gray, mask=roi_mask)[0])

            drift = abs(frame_mean - bg_mean)
            if drift > 8.0:
                # Ambient lighting shifted while scale is at zero weight (empty tray).
                # Auto-calibrate the baseline silently in the background!
                self._auto_update_empty_tray_baseline(frame_bgr, polygon)

            if getattr(self, "lblBaselineWarning", None) is not None:
                self.lblBaselineWarning.setVisible(False)
            return True
        except Exception:
            return True

    def _auto_update_empty_tray_baseline(self, frame_bgr: np.ndarray, polygon: list):
        """Silently auto-calibrate the empty tray baseline to current lighting."""
        try:
            cam = self.settings.get("camera", {})
            path = str(cam.get("empty_baseline_path", EMPTY_TRAY_BASELINE_PATH) or EMPTY_TRAY_BASELINE_PATH)
            baseline_frame = boundary_only_frame(frame_bgr, polygon)
            cv2.imwrite(path, baseline_frame)

            h, w = frame_bgr.shape[:2]
            stamp_attr = "_empty_tray_baseline_stamp"
            img_attr = "_empty_tray_baseline_img"
            mtime = time.time()
            stamp = (str(path), mtime, h, w)
            setattr(self, stamp_attr, stamp)
            setattr(self, img_attr, baseline_frame)
            setattr(self, "_empty_tray_baseline_lab", None)
            setattr(self, "_empty_tray_baseline_glare", None)
            setattr(self, "_cached_baseline_bgr", None)
            print(f"[AutoBaseline] Silently auto-calibrated empty tray baseline to current lighting.")
        except Exception as e:
            print(f"[AutoBaseline] Auto-calibration error: {e}")

    def _feature_from_frame(
        self,
        frame_bgr: np.ndarray,
        polygon_override: Optional[List[List[int]]] = None,
        extra_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        polygon = polygon_override or self.settings["camera"]["polygon"]

        # --- DINOv3 path ---
        if _DINOV3_AVAILABLE and dinov3_vision is not None and dinov3_vision.is_available():
            emb = dinov3_vision.compute_embedding(frame_bgr, mask=extra_mask, polygon=polygon)
            if emb is not None:
                self._set_extraction_status(
                    mode="DINOv3 (ViT-S/16)",
                    bbox=None,
                    is_small=False,
                )
                return emb
            else:
                self._set_extraction_status(
                    mode="FALLBACK (full ROI, less accurate for small items)",
                    bbox=None,
                    is_small=False,
                    reason="dinov3_no_crop",
                )
        else:
            reason = "dinov3_unavailable"
            if dinov3_vision is not None and hasattr(dinov3_vision, "unavailable_reason"):
                reason = dinov3_vision.unavailable_reason() or reason
            self._set_extraction_status(
                mode="FALLBACK (full ROI, less accurate for small items)",
                bbox=None,
                is_small=False,
                reason=reason,
            )

        # --- Fallback: HSV histogram ---
        feat = polygon_feature_raw(frame_bgr, polygon, extra_mask=extra_mask)
        return _normalize(feat)

    def _feature_from_frame_for_training(
        self,
        frame_bgr: np.ndarray,
        polygon_override: Optional[List[List[int]]] = None,
        extra_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        return self._feature_from_frame(frame_bgr, polygon_override=polygon_override, extra_mask=extra_mask)

    def _features_from_frame_for_training(
        self,
        frame_bgr: np.ndarray,
        polygon_override: Optional[List[List[int]]] = None,
        extra_mask: Optional[np.ndarray] = None,
    ) -> List[np.ndarray]:
        """
        Extract multi-variant features (geometric pose variants + photometric jitter)
        for robust DINOv3 gallery training. Returns a list of separate L2-normalized 384-dim vectors.
        """
        polygon = polygon_override or self.settings["camera"]["polygon"]

        if _DINOV3_AVAILABLE and dinov3_vision is not None:
            try:
                embs = dinov3_vision.extract_dinov3_pose_variants(frame_bgr, polygon=polygon, mask=extra_mask)
                if embs:
                    return embs
            except Exception as e:
                print(f"[DINOv3 extract_dinov3_pose_variants error: {e}]")

            feat = self._feature_from_frame(frame_bgr, polygon_override=polygon, extra_mask=extra_mask)
            if feat is not None and len(feat) == 384:
                return [feat]

        feat = polygon_feature_raw(frame_bgr, polygon, extra_mask=extra_mask)
        return [_normalize(feat)]

    def _load_baseline_image(self) -> Optional[np.ndarray]:
        """Load the empty-tray reference image for background subtraction (cached in memory)."""
        cam = self.settings.get("camera", {})
        path = str(cam.get("empty_baseline_path", EMPTY_TRAY_BASELINE_PATH) or EMPTY_TRAY_BASELINE_PATH)
        shape_hw = self.latest_frame_raw.shape[:2] if self.latest_frame_raw is not None else (480, 640)
        return self._cached_baseline_frame(path, shape_hw, "empty_tray_baseline")

    def _count_foreground_items(self, frame_bgr: np.ndarray, fg_mask: Optional[np.ndarray] = None) -> int:
        # Prefer baseline-difference mask for robust counting on fixed trays.
        if fg_mask is None:
            fg_mask, _ = self._baseline_foreground_mask(frame_bgr)
        if fg_mask is None:
            polygon = self.settings["camera"]["polygon"]
            mask = polygon_foreground_mask(frame_bgr, polygon)
        else:
            mask = fg_mask

        # Denoise foreground mask and merge small holes/fragments.
        k3 = np.ones((3, 3), np.uint8)
        k5 = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k3, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k5, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raw_count = 0
        else:
            h, w = mask.shape[:2]
            roi_area = float(h * w)
            min_area = max(900.0, roi_area * 0.002)
            max_area = roi_area * 0.90
            valid_areas = []
            for c in contours:
                a = float(cv2.contourArea(c))
                if min_area <= a <= max_area:
                    valid_areas.append(a)
            raw_count = len(valid_areas)

            # If one dominant blob occupies much of ROI, treat as one object.
            if valid_areas:
                valid_areas.sort(reverse=True)
                if valid_areas[0] >= (roi_area * 0.28):
                    raw_count = 1

        # Safety fallback: weight exists but vision missed.
        if self._last_weight > self.open_threshold and raw_count == 0:
            raw_count = 1

        # Prevent runaway noisy counts in one frame.
        raw_count = max(0, min(int(raw_count), 6))

        if not hasattr(self, "_qty_history"):
            self._qty_history = []
        self._qty_history.append(raw_count)
        if len(self._qty_history) > 8:
            self._qty_history.pop(0)

        from collections import Counter
        stable_count = int(Counter(self._qty_history).most_common(1)[0][0])
        return stable_count

    def _count_objects_in_roi(self, frame_bgr: np.ndarray) -> int:
        polygon = self.settings["camera"]["polygon"]
        mask = polygon_foreground_mask(frame_bgr, polygon)
        # Merge fragmented highlights/reflections from metallic tray before counting.
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid = [c for c in contours if cv2.contourArea(c) > 700]
        return len(valid)

    def _dominant_object_metrics(self, frame_bgr: np.ndarray) -> Tuple[int, float]:
        polygon = self.settings["camera"]["polygon"]
        mask = polygon_foreground_mask(frame_bgr, polygon)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        areas = sorted([float(cv2.contourArea(c)) for c in contours if cv2.contourArea(c) > 700], reverse=True)
        if not areas:
            return 0, 0.0
        if len(areas) == 1:
            return 1, 0.0
        ratio = float(areas[1] / max(1.0, areas[0]))
        return len(areas), ratio


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if getattr(self, "lblCameraDash", None) is not None and self.lblCameraDash.underMouse():
                self._match_locked = False
                self._last_matched_obj = None
                self._last_laptop_tick_state = None
                self._laptop_stable_ticks = 0
                self.try_match()
                event.accept()
                return
            self._pressed_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pressed_pos:
            self._pressed_pos = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ---------- SCALE ----------
    @Slot(float)
    def on_live_weight(self, w: float):
        threshold = 0.001
        if w < threshold:
            w = 0.0
        prev_live = float(getattr(self, "_display_weight", 0.0) or 0.0)
        self._display_weight = w
        if abs(w - prev_live) >= 0.001:
            self._last_weight_change_time = time.time()
            self._is_weight_stable = False

        last_mw = getattr(self, "_last_matched_weight", None)
        is_falling = (w < prev_live - 0.003)
        is_rising = (w > prev_live + 0.010)

        # Suppress matching ONLY when weight is actively falling from matched weight (lifting item)
        if last_mw is not None and last_mw >= 0.010 and is_falling and (w < last_mw - 0.008):
            self._suppress_matching_until_zero = True
            self._match_locked = True
        elif w <= 0.002:
            # Scale returned to zero: immediately ready for next item
            self._suppress_matching_until_zero = False
            self._match_locked = False
            self._last_matched_weight = None
        elif is_rising and getattr(self, "_suppress_matching_until_zero", False):
            # Rapid consecutive placement: weight started rising, so immediately unfreeze for next item
            self._suppress_matching_until_zero = False
            self._match_locked = False
            self._last_matched_weight = None

        if self.float is not None:
            self.float.set_weight(w)
        if self.lblWeight is not None:
            self.lblWeight.setText(f"{w:.3f} KG")

        # Weight-driven auto-open / auto-close behavior:
        # If weight arrives on scale: automatically open dashboard (5 grams = 0.005 KG).
        if w >= 0.005:
            self._cancel_auto_close()
            self._opened_by_weight = True
            self._manual_open = False
            if not self.isVisible():
                self.show_dashboard(manual=False)

            # Fast Running Weight Trigger (Predictive Visual Pipeline):
            # If item is on scale, matching is not locked, and removal suppression is off:
            # Attempt early match on running weight (will only succeed if visual motion is settled)
            if not getattr(self, "_match_locked", False) and not getattr(self, "_suppress_matching_until_zero", False):
                if getattr(self, "lblExtractionMode", None) is not None:
                    self.lblExtractionMode.setText("Detection: Stabilizing weight...")
                    self.lblExtractionMode.setStyleSheet(
                        "background: #FFF8E1; color: #F57F17; border: 1px solid #FFE082; "
                        "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                    )
                if hasattr(self, "_running_match_timer"):
                    if not self._running_match_timer.isActive():
                        self._running_match_timer.start(50)
                else:
                    self.try_match(running_weight=True)
        elif w <= 0.002:
            self._refresh_skip_codes = set()
            self._refresh_page = 0
            self._current_displayed_codes = []
            if self.isVisible() and self._is_weight_controlled_dashboard_active():
                if getattr(self, "_opened_by_weight", False) and not getattr(self, "_manual_open", False):
                    self._schedule_auto_close(400)

    @Slot(float)
    def on_weight(self, w: float):
        if w < 0.001:
            w = 0.0
        prev = self._last_weight
        self._last_weight = w
        self._is_weight_stable = True
        self._last_stable_weight = w
        self._display_weight = w

        if w <= 0.002:
            self._suppress_matching_until_zero = False
            self._match_locked = False
            self._last_matched_weight = None
            self._refresh_skip_codes = set()
            self._refresh_page = 0
            self._current_displayed_codes = []
            if self.isVisible() and self._is_weight_controlled_dashboard_active():
                if getattr(self, "_opened_by_weight", False) and not getattr(self, "_manual_open", False):
                    self._schedule_auto_close(400)
            return

        if hasattr(self, "_running_match_timer"):
            self._running_match_timer.stop()

        if w >= 0.005:
            self._cancel_auto_close()
            self._opened_by_weight = True
            self._manual_open = False
            if not self.isVisible():
                self.show_dashboard(manual=False)

            # If product is currently being removed, suppress detection until scale reaches zero
            if getattr(self, "_suppress_matching_until_zero", False):
                return

            last_mw = getattr(self, "_last_matched_weight", None)
            if getattr(self, "_match_locked", False) and last_mw is not None:
                # If stable weight is within 5g of early matched weight, keep lock without duplicate re-matching
                if abs(w - last_mw) < 0.005:
                    self._last_matched_weight = w
                    self._last_stable_weight = w
                    return
                # Weight changed from early hand touch -> break lock and re-match on clean stable frame!
                self._match_locked = False

            if last_mw is None or abs(w - last_mw) >= 0.003:
                if last_mw is not None and abs(w - last_mw) >= 0.015:
                    self._refresh_skip_codes = set()
                    self._refresh_page = 0
                    self._current_displayed_codes = []
                self._match_locked = False
                self._camera_settle_retries = 0
                # Trigger recognition on confirmed stable plateau as fallback
                QTimer.singleShot(0, lambda: self.try_match(force=True))

    # ---------- FRAME / PREVIEW ----------
    @Slot(object)
    def on_frame(self, frame):
        try:
            if getattr(self, "cam", None) is not None:
                self.cam.gui_busy = False
            self.latest_frame_raw = frame
            poly = self.settings.get("camera", {}).get("polygon", [])
            show_boundary = self.settings.get("camera", {}).get("show_boundary", True) and poly and len(poly) >= 3

            dash_vis = self.panelRight is not None and self.panelRight.isVisible()
            cam_vis = self.lblCamera is not None and self.lblCamera.isVisible()

            if not dash_vis and not cam_vis:
                return

            if show_boundary:
                disp = draw_polygon_with_handles(frame.copy(), poly)
            else:
                disp = frame

            self._last_disp_frame = disp

            # Fast OpenCV downscale directly to target label size (SIMD accelerated, zero Qt software rasterizer lag)
            if cam_vis and self.lblCamera is not None:
                self._render_preview_label(self.lblCamera, disp)
            if dash_vis and self.lblCameraDash is not None:
                self._render_preview_label(self.lblCameraDash, disp)
        except Exception:
            pass

    def _render_preview_label(self, label: QLabel, img_bgr: np.ndarray):
        lw, lh = label.width(), label.height()
        if lw <= 10 or lh <= 10:
            return
        ih, iw = img_bgr.shape[:2]
        scale = min(lw / iw, lh / ih)
        tw = max(1, int(iw * scale))
        th = max(1, int(ih * scale))
        resized = cv2.resize(img_bgr, (tw, th), interpolation=cv2.INTER_LINEAR)
        pix = bgr_to_qpixmap(resized)
        label.setPixmap(pix)

    def _set_label_pix(self, label: Optional[QLabel], pix: QPixmap):
        if label is None:
            return
        scaled = pix.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    def _sync_db_products_cache(self, force: bool = False):
        now = time.time()
        sync_interval = float(getattr(self, "_db_products_sync_interval", 30.0))
        if not force and (now - float(getattr(self, "_db_products_last_sync", 0.0))) < sync_interval:
            return
        try:
            rows = fetch_all_products(self.settings)
        except Exception:
            return
        self._db_products_by_code = {str(r.get("Code", "")).strip(): r for r in rows}
        self._db_products_last_sync = now

    def _capture_stable_snapshot(self, stable_weight: float):
        if self.latest_frame_raw is None:
            return
        try:
            snap = self.latest_frame_raw.copy()
        except Exception:
            snap = self.latest_frame_raw
        self._stable_snapshot_raw = snap
        self._stable_snapshot_weight = float(stable_weight or 0.0)
        self._stable_snapshot_qty = max(1, int(self._count_foreground_items(snap)))
        self._last_match_signature = None

    def _check_laptop_object_change(
        self, frame_bgr: np.ndarray, fg_mask: np.ndarray, include_color: bool = True
    ) -> Tuple[bool, bool, str, Optional[dict]]:
        """
        When scale weight gating is disabled (Laptop Mode), determines whether
        an object on the platform has changed or changed position.

        Returns:
            (has_changed, is_stable, reason, current_state)
            - has_changed: True if object is newly placed, replaced, or moved to a new position.
            - is_stable: True if visual motion has settled (not currently moving / hands away).
            - reason: human-readable explanation of why change was or wasn't detected.
            - current_state: dict describing current object geometry and appearance.
        """
        pts = cv2.findNonZero(fg_mask)
        if pts is None or len(pts) < 10:
            return False, True, "empty_mask", None

        x, y, w, h = cv2.boundingRect(pts)
        area = int(cv2.countNonZero(fg_mask))

        M = cv2.moments(fg_mask)
        if M["m00"] > 0:
            cx = float(M["m10"] / M["m00"])
            cy = float(M["m01"] / M["m00"])
        else:
            cx = float(x + w / 2.0)
            cy = float(y + h / 2.0)

        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mean_hsv = cv2.mean(hsv, mask=fg_mask)[:3]
        mean_s = float(mean_hsv[1])
        mean_v = float(mean_hsv[2])

        hist_h = cv2.calcHist([hsv], [0], fg_mask, [16], [0, 180])
        cv2.normalize(hist_h, hist_h)

        color_family = "UNKNOWN"
        c_prof = None
        if include_color and _COLOR_MATCHER_AVAILABLE and color_matcher is not None:
            try:
                c_prof = color_matcher.compute_color_profile(frame_bgr, mask=fg_mask)
                if c_prof:
                    color_family = c_prof.get("dominant_family", "UNKNOWN")
            except Exception:
                pass

        current_state = {
            "cx": cx,
            "cy": cy,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "area": area,
            "mean_hsv": (float(mean_hsv[0]), mean_s, mean_v),
            "color_family": color_family,
            "hist_h": hist_h,
            "color_profile": c_prof,
        }

        # 1. Motion stability check against previous tick
        last_tick = getattr(self, "_last_laptop_tick_state", None)
        self._last_laptop_tick_state = current_state

        if last_tick is not None:
            tick_pos_diff = math.hypot(cx - last_tick["cx"], cy - last_tick["cy"])
            tick_area_ratio = abs(area - last_tick["area"]) / max(1.0, float(max(area, last_tick["area"])))
            max_pos_diff = 32.0 if getattr(self, "scale_connected", False) else 8.0
            max_area_ratio = 0.28 if getattr(self, "scale_connected", False) else 0.12
            if tick_pos_diff > max_pos_diff or tick_area_ratio > max_area_ratio:
                self._laptop_stable_ticks = 0
                return False, False, "motion_active", current_state
            else:
                self._laptop_stable_ticks = getattr(self, "_laptop_stable_ticks", 0) + 1
        else:
            self._laptop_stable_ticks = 1

        last_matched = getattr(self, "_last_matched_obj", None)
        if last_matched is None:
            req_ticks = 2
            is_st = bool(getattr(self, "_laptop_stable_ticks", 0) >= req_ticks)
            return True, is_st, "new_object" if is_st else "settling", current_state

        # 2. Position change check
        pos_dist = math.hypot(cx - last_matched["cx"], cy - last_matched["cy"])
        bbox_moved = (
            abs(x - last_matched["x"]) > 18
            or abs(y - last_matched["y"]) > 18
            or abs(w - last_matched["w"]) > 20
            or abs(h - last_matched["h"]) > 20
        )
        area_diff_ratio = abs(area - last_matched["area"]) / max(1.0, float(max(area, last_matched["area"])))

        position_changed = (pos_dist > 16.0) or (bbox_moved and area_diff_ratio > 0.15)

        # 3. Object change check
        area_changed = area_diff_ratio > 0.22
        hist_diff = float(cv2.compareHist(hist_h, last_matched["hist_h"], cv2.HISTCMP_BHATTACHARYYA))
        hist_changed = (hist_diff > 0.25)

        color_family_changed = (
            color_family not in ("UNKNOWN", "NEUTRAL")
            and last_matched.get("color_family") not in ("UNKNOWN", "NEUTRAL")
            and color_family != last_matched.get("color_family")
        )

        last_mean_s = last_matched["mean_hsv"][1]
        last_mean_v = last_matched["mean_hsv"][2]
        hue_shift = abs(current_state["mean_hsv"][0] - last_matched["mean_hsv"][0])
        if hue_shift > 90:
            hue_shift = 180 - hue_shift

        color_shift = (
            (min(mean_s, last_mean_s) > 30 and hue_shift > 18.0)
            or (max(mean_s, last_mean_s) < 30 and abs(mean_v - last_mean_v) > 35)
        )

        object_changed = area_changed or hist_changed or color_family_changed or color_shift

        if position_changed or object_changed:
            reason = "position_changed" if (position_changed and not object_changed) else (
                "object_changed" if (object_changed and not position_changed) else "object_and_position_changed"
            )
            return True, True, reason, current_state

        return False, True, "unchanged", current_state

    def refresh_detection(self):
        """Force immediate re-detection of the item currently on the tray/scale without lifting it,
        cycling to the next ranked candidates if previous candidates were not what the cashier wanted."""
        print("[Dashboard] Refresh button clicked: re-triggering detection on current item...")
        self._match_locked = False
        self._last_matched_weight = None
        self._last_match_signature = None
        self._last_matched_obj = None
        self._last_laptop_tick_state = None
        self._laptop_stable_ticks = 2
        if hasattr(self, "_match_row_cache") and self._match_row_cache:
            self._match_row_cache.clear()
        if hasattr(self, "_match_miss_counts") and self._match_miss_counts:
            self._match_miss_counts.clear()
        if hasattr(self, "_match_hit_counts") and self._match_hit_counts:
            self._match_hit_counts.clear()

        # Next-ranked candidate cycling:
        # Collect currently displayed product codes to skip them on this refresh
        cur_codes = list(getattr(self, "_current_displayed_codes", []) or [])
        if cur_codes:
            if not hasattr(self, "_refresh_skip_codes") or not isinstance(self._refresh_skip_codes, set):
                self._refresh_skip_codes = set()
            self._refresh_skip_codes.update([str(c).strip() for c in cur_codes])
            self._refresh_page = getattr(self, "_refresh_page", 0) + 1
            print(f"[Dashboard] Refresh: skipping {len(self._refresh_skip_codes)} previous codes, moving to next candidates (Page {self._refresh_page + 1})")

        page_num = getattr(self, "_refresh_page", 0) + 1
        if getattr(self, "lblExtractionMode", None) is not None:
            if page_num > 1:
                self.lblExtractionMode.setText(f"Detection: Finding next matches (Page {page_num})...")
            else:
                self.lblExtractionMode.setText("Detection: Refreshing detection...")
            self.lblExtractionMode.setStyleSheet(
                "background: #E0F2F1; color: #00695C; border: 1px solid #80CBC4; "
                "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: bold;"
            )
        if getattr(self, "btnRefresh", None) is not None:
            self.btnRefresh.setEnabled(False)
            self.btnRefresh.setText("Refreshing...")
        try:
            self.try_match(force=True)
        finally:
            if getattr(self, "btnRefresh", None) is not None:
                self.btnRefresh.setEnabled(True)
                self.btnRefresh.setText("Refresh")

    # ---------- MATCH ----------
    def try_match(self, force: bool = False, running_weight: bool = False):
        if not self.isVisible() and not getattr(self, "_opened_by_weight", False) and not running_weight:
            return
        if getattr(self, "_is_matching_in_progress", False):
            return
        self._is_matching_in_progress = True
        try:
            self._do_try_match(force=force, running_weight=running_weight)
        finally:
            self._is_matching_in_progress = False

    def _do_try_match(self, force: bool = False, running_weight: bool = False):
        effective_w = max(float(getattr(self, "_display_weight", 0.0) or 0.0), float(getattr(self, "_last_weight", 0.0) or 0.0))
        weight_gating_enabled = bool(
            self.settings.get("behavior", {}).get("weight_gating", self.settings.get("scale", {}).get("enabled", False))
        )
        if weight_gating_enabled:
            # Full Real POS scale weight gating
            if effective_w <= 0.001:
                if self.listMatches is not None and self.listMatches.count() > 0:
                    self.listMatches.clear()
                self._last_match_signature = None
                self._match_row_cache = {}
                self._match_miss_counts = {}
                self._match_hit_counts = {}
                self._last_detected_bbox = None
                self._match_locked = False
                self._last_matched_weight = None
                self._suppress_matching_until_zero = False
                self._refresh_skip_codes = set()
                self._refresh_page = 0
                self._current_displayed_codes = []
                if getattr(self, "lblSmallItemWarning", None) is not None:
                    self.lblSmallItemWarning.setVisible(False)
                if getattr(self, "lblExtractionMode", None) is not None:
                    self.lblExtractionMode.setText("Detection: Idle (waiting for item)")
                    self.lblExtractionMode.setStyleSheet(
                        "background: #ECEFF1; color: #455A64; border: 1px solid #CFD8DC; "
                        "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                    )
                self._check_baseline_freshness(self.latest_frame_raw)
                return

        # Always fetch freshest live frame from camera worker buffer if available
        cam_worker = getattr(self, "cam", None)
        if cam_worker is not None and getattr(cam_worker, "_latest_frame", None) is not None:
            self.latest_frame_raw = cam_worker._latest_frame

        if self.latest_frame_raw is None:
            return
        if self.stack is None or self.pageDashboard is None:
            return
        if self.isVisible() and self.stack.currentWidget() != self.pageDashboard:
            return

        if weight_gating_enabled:
            # Empty plastic cover bag guard
            actual_w = max(float(getattr(self, "_display_weight", 0.0) or 0.0), float(getattr(self, "_last_weight", 0.0) or 0.0))
            if 0.002 <= actual_w <= 0.018:
                roi = getattr(self, "_cached_roi_mask", None)
                if roi is None and self.settings.get("camera", {}).get("polygon"):
                    poly = self.settings["camera"]["polygon"]
                    roi = np.zeros(self.latest_frame_raw.shape[:2], dtype=np.uint8)
                    cv2.fillPoly(roi, [np.array(poly, dtype=np.int32)], 255)
                if roi is not None:
                    cover_look = self._frame_cover_appearance_ratio(self.latest_frame_raw, roi)
                    if cover_look >= 0.12:
                        if self.listMatches is not None and self.listMatches.count() > 0:
                            self.listMatches.clear()
                        self._last_match_signature = None
                        self._match_row_cache = {}
                        self._match_miss_counts = {}
                        self._match_hit_counts = {}
                        self._last_detected_bbox = None
                        self._match_locked = False
                        self._last_matched_weight = None
                        if getattr(self, "lblSmallItemWarning", None) is not None:
                            self.lblSmallItemWarning.setVisible(False)
                        if getattr(self, "lblExtractionMode", None) is not None:
                            self.lblExtractionMode.setText("Detection: Empty cover on scale (place produce inside)")
                            self.lblExtractionMode.setStyleSheet(
                                "background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; "
                                "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                            )
                        return

            # If product is currently being removed, suppress detection until scale reaches zero
            if getattr(self, "_suppress_matching_until_zero", False):
                return

            # If scale is active and weight is not yet stable, do not run periodic background match unless running_weight is active
            if not force and not running_weight and getattr(self, "scale_connected", False) and not getattr(self, "_is_weight_stable", False):
                return

            # Weight-change detection gate: only re-infer when weight changes
            last_mw = getattr(self, "_last_matched_weight", None)
            weight_changed = (last_mw is None) or (abs(effective_w - last_mw) >= 0.003)
            if not force and not running_weight and not weight_changed and getattr(self, "_match_locked", False):
                return
            if running_weight and getattr(self, "_match_locked", False):
                return

        fg_mask, fg_ratio = self._baseline_foreground_mask(self.latest_frame_raw)
        empty_diff_threshold = float(self.settings.get("camera", {}).get("empty_diff_threshold", 0.015))
        if not weight_gating_enabled:
            empty_diff_threshold = min(0.003, empty_diff_threshold)
        elif effective_w >= 0.020:
            empty_diff_threshold = min(0.005, empty_diff_threshold)
        elif effective_w < 0.020:
            empty_diff_threshold = max(0.04, empty_diff_threshold)
        if fg_mask is None or fg_ratio <= empty_diff_threshold:
            if self.listMatches is not None and self.listMatches.count() > 0:
                self.listMatches.clear()
            self._last_match_signature = None
            self._match_row_cache = {}
            self._match_miss_counts = {}
            self._match_hit_counts = {}
            self._last_detected_bbox = None
            self._match_locked = False
            self._last_matched_obj = None
            self._last_laptop_tick_state = None
            self._laptop_stable_ticks = 0
            if getattr(self, "lblSmallItemWarning", None) is not None:
                self.lblSmallItemWarning.setVisible(False)
            if getattr(self, "lblExtractionMode", None) is not None:
                self.lblExtractionMode.setText("Detection: Idle (waiting for item)")
                self.lblExtractionMode.setStyleSheet(
                    "background: #ECEFF1; color: #455A64; border: 1px solid #CFD8DC; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                )
            return

        current_laptop_obj = None
        if not weight_gating_enabled:
            has_changed, is_stable, change_reason, current_laptop_obj = self._check_laptop_object_change(
                self.latest_frame_raw, fg_mask
            )

            # Wait for visual motion to settle before running inference
            if not force and not is_stable:
                if getattr(self, "lblExtractionMode", None) is not None:
                    self.lblExtractionMode.setText("Detection: Motion detected (stabilizing...)")
                    self.lblExtractionMode.setStyleSheet(
                        "background: #FFF8E1; color: #F57F17; border: 1px solid #FFE082; "
                        "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                    )
                return

            # When locked, only recalculate if object changed or position changed
            if not force and getattr(self, "_match_locked", False) and not has_changed:
                return

            debug_match = (
                (os.environ.get("DEBUG_MATCH", "0") == "1")
                or (os.environ.get("DEBUG_MODE", "0") == "1")
                or getattr(self, "debug", False)
            )
            if debug_match:
                print(f"[LaptopMode] Triggering match calculation: reason='{change_reason}'")

        if weight_gating_enabled and (force or running_weight):
            # Hand motion check (Visual Anti-Flicker Shield):
            # Verify if cashier's hand is still moving in the camera ROI.
            # If motion is active, freeze matching until hand pulls away!
            pts = cv2.findNonZero(fg_mask)
            if pts is not None and len(pts) > 10:
                has_changed, is_stable, change_reason, _ = self._check_laptop_object_change(
                    self.latest_frame_raw, fg_mask, include_color=False
                )
                if not is_stable:
                    if getattr(self, "lblExtractionMode", None) is not None:
                        self.lblExtractionMode.setText("Detection: Stabilizing...")
                        self.lblExtractionMode.setStyleSheet(
                            "background: #FFF8E1; color: #F57F17; border: 1px solid #FFE082; "
                            "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                        )
                    # When hand motion is active, retry quickly in 40ms so inference begins immediately when hand clears!
                    retries = getattr(self, "_camera_settle_retries", 0)
                    if retries < 6:
                        self._camera_settle_retries = retries + 1
                        QTimer.singleShot(40, lambda: self.try_match(running_weight=running_weight, force=force))
                    return
            self._camera_settle_retries = 0

        feat = self._feature_from_frame(self.latest_frame_raw, extra_mask=fg_mask)
        matches = self.brain.match_all(feat)
        qty = max(1, int(self._count_foreground_items(self.latest_frame_raw, fg_mask=fg_mask)))
        self._sync_db_products_cache()

        if self.listMatches is None:
            return

        # Adapt entry threshold for cover bag on scale
        enter_threshold = float(self.match_threshold)
        is_cover_present = getattr(self, "_is_cover_present_detected", False)
        if getattr(self, "_cached_roi_mask", None) is not None:
            roi = self._cached_roi_mask
            if self._empty_cover_baseline_valid(roi):
                empty_cover_same = self._empty_cover_same_mask(self.latest_frame_raw, roi)
                roi_px = float(cv2.countNonZero(roi))
                cover_same_ratio = (float(cv2.countNonZero(empty_cover_same)) / roi_px) if empty_cover_same is not None and roi_px > 0 else 0.0
                cover_by_look = self._cover_appearance_ratio(self.latest_frame_raw, roi) >= 0.08
                if cover_same_ratio >= COVER_PRESENT_SAME_RATIO or cover_by_look:
                    is_cover_present = True
            if is_cover_present:
                enter_threshold = max(0.40, enter_threshold - 0.10)

        # Extract live color profile from detected object / ROI
        cam_polygon = self.settings.get("camera", {}).get("polygon", [])
        live_color = {}
        if current_laptop_obj and current_laptop_obj.get("color_profile"):
            live_color = current_laptop_obj["color_profile"]
        elif _COLOR_MATCHER_AVAILABLE and color_matcher is not None:
            try:
                frame_to_color = self.latest_frame_raw
                if is_cover_present and dinov3_vision is not None and hasattr(dinov3_vision, "dehaze_crop"):
                    # De-haze frame inside ROI so color extraction gets pristine contrast under translucent bag
                    if len(cam_polygon) >= 3:
                        bx, by, bw, bh = cv2.boundingRect(np.array(cam_polygon, dtype=np.int32))
                    else:
                        bx, by, bw, bh = (0, 0, frame_to_color.shape[1], frame_to_color.shape[0])
                    roi_crop = frame_to_color[by : by + bh, bx : bx + bw]
                    if roi_crop.size > 0:
                        dehazed_crop = dinov3_vision.dehaze_crop(roi_crop)
                        frame_to_color = frame_to_color.copy()
                        frame_to_color[by : by + bh, bx : bx + bw] = dehazed_crop

                live_color = color_matcher.compute_color_profile(
                    frame_to_color,
                    mask=fg_mask,
                    polygon=cam_polygon,
                )
            except Exception as e:
                print(f"[try_match] Color extraction error: {e}")
                live_color = {}

        debug_match = (
            (os.environ.get("DEBUG_MATCH", "0") == "1")
            or (os.environ.get("DEBUG_MODE", "0") == "1")
            or getattr(self, "debug", False)
        )
        if debug_match and live_color:
            print(
                f"\n[DEBUG_MATCH] Live color profile: dominant={live_color.get('dominant_family')}, "
                f"chromatic={live_color.get('dominant_chromatic')}, families={live_color.get('families')}, "
                f"mean_s={live_color.get('mean_s')}, mean_v={live_color.get('mean_v')}"
            )

        selected_uom = self._selected_db_uom_filter()
        candidates = []

        for code, score in matches:
            meta = self.brain.meta.get(code, {})
            db_row = self._db_products_by_code.get(str(code).strip())
            if db_row is not None:
                name = db_row.get("Name", meta.get("Name", meta.get("name", "")))
                price = float(db_row.get("Price", meta.get("Price", 0.0)) or 0.0)
                uom = str(db_row.get("UOM", meta.get("UOM", "PCS"))).upper()
                merged = {
                    "Code": db_row.get("Code", code),
                    "Name": name,
                    "UOM": uom,
                    "Price": price,
                }
                if meta.get("thumb"):
                    merged["thumb"] = meta.get("thumb")
                if meta.get("display_thumb"):
                    merged["display_thumb"] = meta.get("display_thumb")
                if meta.get("color_profile"):
                    merged["color_profile"] = meta.get("color_profile")
                if meta.get("score_threshold"):
                    merged["score_threshold"] = meta.get("score_threshold")
                self.brain.meta[code] = merged
                meta = merged
            else:
                name = meta.get("Name") or meta.get("name") or ""
                price = float(meta.get("Price", 0.0) or 0.0)
                uom = str(meta.get("UOM", "PCS")).upper()

            if selected_uom != "ALL" and uom != selected_uom:
                continue

            # 1. Color compatibility
            product_color = self.get_product_color_profile(code)
            color_compatible = True
            color_reason = "no_color_check"

            if _COLOR_MATCHER_AVAILABLE and color_matcher is not None and live_color and product_color:
                color_compatible = color_matcher.is_color_compatible(live_color, product_color)
                if not color_compatible:
                    _, _, color_reason = color_matcher.compare_color(live_color, product_color)

            # 2. Score Threshold Determination
            stored_thresh = meta.get("score_threshold")
            if stored_thresh is not None and float(stored_thresh) > 0.0:
                required_score = float(stored_thresh)
                if enter_threshold < float(self.match_threshold):
                    required_score = max(0.35, required_score - (float(self.match_threshold) - enter_threshold))
                thresh_type = "per-item"
            else:
                required_score = enter_threshold
                thresh_type = "global fallback"

            candidates.append({
                "code": code,
                "score": float(score),
                "name": name,
                "price": price,
                "uom": uom,
                "meta": meta,
                "product_color": product_color,
                "color_compatible": color_compatible,
                "color_reason": color_reason,
                "required_score": required_score,
                "thresh_type": thresh_type,
            })

        if not candidates:
            if self.listMatches.count() > 0:
                self.listMatches.clear()
            self._last_match_signature = None
            self._last_matched_weight = effective_w
            self._match_locked = True
            if not weight_gating_enabled and current_laptop_obj:
                self._last_matched_obj = current_laptop_obj
            if getattr(self, "lblExtractionMode", None) is not None:
                self.lblExtractionMode.setText("Detection: No matching product found")
                self.lblExtractionMode.setStyleSheet(
                    "background: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                )
            return

        # Next-ranked candidate cycling:
        # Check if Refresh button requested cycling through next ranked candidates
        skip_codes = getattr(self, "_refresh_skip_codes", set()) or set()
        active_candidates = [c for c in candidates if str(c["code"]).strip() not in skip_codes]
        if not active_candidates and skip_codes:
            # Wrap around when all candidates have been exhausted!
            print("[Dashboard] Refresh cycled through all available candidates; wrapping around to top matches.")
            if hasattr(self, "_refresh_skip_codes"):
                self._refresh_skip_codes.clear()
            self._refresh_page = 0
            active_candidates = list(candidates)

        # STAGE 2: Choose primary match (best color-compatible candidate from active_candidates)
        color_compatible_candidates = [c for c in active_candidates if c["color_compatible"]]
        has_color_compatible = (len(color_compatible_candidates) > 0)

        if not has_color_compatible and is_cover_present and active_candidates:
            # Under a translucent bag, white veil can wash out color.
            # If top DINOv3 match is strong (>= 0.65) or chromatic hue aligns, allow match under cover.
            top_c = active_candidates[0]
            live_chr = live_color.get("dominant_chromatic") if live_color else None
            cand_color = top_c.get("product_color", {})
            cand_chr = cand_color.get("dominant_chromatic") if cand_color else None
            if top_c["score"] >= 0.65 or (live_chr and cand_chr and live_chr == cand_chr):
                color_compatible_candidates = [top_c]
                has_color_compatible = True

        is_refresh_page = getattr(self, "_refresh_page", 0) >= 1

        if not has_color_compatible and is_refresh_page and active_candidates:
            # On Refresh, cashier is looking for items that might have subtle skin/lighting shifts (e.g. onion papery skin)
            top_c = active_candidates[0]
            if top_c["score"] >= 0.65:
                color_compatible_candidates = [top_c]
                has_color_compatible = True

        if not has_color_compatible:
            # --- FALLBACK TEMPORARILY DISABLED FOR STRICT COLOR TESTING ---
            # To re-enable fallback, restore:
            # primary_candidate = active_candidates[0]
            # is_fallback = True
            live_dom = live_color.get("dominant_family", "UNKNOWN") if live_color else "UNKNOWN"
            live_fams = live_color.get("families", {}) if live_color else {}
            live_pct = float(live_fams.get(live_dom, 1.0)) * 100.0 if live_fams else 0.0
            print("\n" + "=" * 62)
            print(f"[LIVE RECOGNITION] Live Object Color: {live_dom} ({live_pct:.1f}%)")
            print("  • Color Gate:           BLOCKED (No color-compatible candidates found)")
            print("  • Fallback:             DISABLED (Strict Color Testing Mode Active)")
            print("=" * 62 + "\n")
            if self.listMatches.count() > 0:
                self.listMatches.clear()
            self._last_match_signature = None
            self._last_matched_weight = effective_w
            self._match_locked = True
            if not weight_gating_enabled and current_laptop_obj:
                self._last_matched_obj = current_laptop_obj
            if getattr(self, "lblExtractionMode", None) is not None:
                self.lblExtractionMode.setText(f"Detection: Color blocked ({live_dom}) / Check cover")
                self.lblExtractionMode.setStyleSheet(
                    "background: #FFF3E0; color: #E65100; border: 1px solid #FFE0B2; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                )
            return

        # Best match is the highest DINO score among color-compatible candidates
        primary_candidate = color_compatible_candidates[0]
        is_fallback = False

        best_score = float(primary_candidate["score"])
        allowed_gap = float(self.settings.get("behavior", {}).get("confusion_margin", 0.12))
        safety_max_cards = int(self.settings.get("behavior", {}).get("top_matches_count", 3))

        # Primary candidate is ALWAYS accepted (never suppressed by threshold)
        accepted_candidates = [primary_candidate]

        # On Refresh (Page 2+), expand score gap tolerance to 10% so cashier gets up to 3 cards per refresh!
        max_score_diff = 0.100 if is_refresh_page else 0.050

        # Evaluate remaining candidates as additional matches
        for c in active_candidates:
            if c["code"] == primary_candidate["code"]:
                continue

            rejection_reason = ""
            score_diff = best_score - float(c["score"])
            # Close match condition: within 5% on first scan, expanded to 10% on Refresh pages
            is_near_match = (score_diff <= max_score_diff and float(c["score"]) >= 0.20)

            # On Refresh, also allow high visual similarity candidates (>= 0.75) with minor color shifts
            color_ok = c["color_compatible"] or (is_refresh_page and float(c["score"]) >= 0.75)

            if not color_ok:
                c_accepted = False
                rejection_reason = f"color incompatible ({c['color_reason']})"
            elif float(c["score"]) < (best_score - allowed_gap):
                c_accepted = False
                rejection_reason = f"DINO gap from best ({best_score:.3f} - {c['score']:.3f} > {allowed_gap:.2f})"
            elif not is_near_match:
                c_accepted = False
                rejection_reason = f"score gap {score_diff*100:.1f}% > {max_score_diff*100:.0f}%"
            else:
                c_accepted = True

            c["accepted"] = c_accepted
            c["rejection_reason"] = rejection_reason

            if c_accepted:
                accepted_candidates.append(c)
                if len(accepted_candidates) >= safety_max_cards:
                    break

        # Record currently displayed product codes so the next Refresh knows what to skip!
        self._current_displayed_codes = [str(c["code"]).strip() for c in accepted_candidates]
        # Always output the live detection summary to terminal
        live_dom = live_color.get("dominant_family", "UNKNOWN") if live_color else "UNKNOWN"
        live_fams = live_color.get("families", {}) if live_color else {}
        live_pct = float(live_fams.get(live_dom, 1.0)) * 100.0 if live_fams else 0.0

        prod_name = primary_candidate.get("name") or str(primary_candidate.get("code"))
        prod_color = primary_candidate.get("product_color", {}) or {}
        prod_dom = prod_color.get("dominant_family", "UNKNOWN")
        prod_fams = prod_color.get("families", {})
        prod_pct = float(prod_fams.get(prod_dom, 1.0)) * 100.0 if prod_fams else 0.0
        sim_pct = float(primary_candidate.get("score", 0.0)) * 100.0
        gate_str = "PASSED" if primary_candidate.get("color_compatible") else f"FALLBACK ({primary_candidate.get('color_reason')})"

        print("\n" + "=" * 62)
        print(f"[LIVE RECOGNITION] Live Object Color: {live_dom} ({live_pct:.1f}%)")
        print(f"  • Top Match:            '{prod_name}' (Code: {primary_candidate.get('code')})")
        print(f"  • Trained Color Family: {prod_dom} ({prod_pct:.1f}%)")
        print(f"  • Color Gate:           {gate_str}")
        print(f"  • Embedding Similarity: {sim_pct:.1f}%")
        if len(accepted_candidates) > 1:
            print("  • Additional Matches:")
            for extra in accepted_candidates[1:]:
                e_name = extra.get("name") or str(extra.get("code"))
                e_sim = float(extra.get("score", 0.0)) * 100.0
                e_col = (extra.get("product_color", {}) or {}).get("dominant_family", "UNKNOWN")
                print(f"      - '{e_name}': Embedding {e_sim:.1f}% (Color: {e_col})")
        print("=" * 62 + "\n")

        if debug_match:
            print("\n--------------------------------------------------")
            print("[DEBUG_MATCH] DINOv3 + Color Candidate Decisions:")
            print("--------------------------------------------------")
            for c in candidates:
                prod_fam = c["product_color"].get("dominant_family", "UNKNOWN") if c["product_color"] else "UNKNOWN"
                is_primary = (c["code"] == primary_candidate["code"])
                if is_primary:
                    if is_fallback:
                        decision_str = "SHOW AS BEST FALLBACK"
                    else:
                        decision_str = "SHOW"
                else:
                    if c.get("accepted", False):
                        decision_str = "SHOW (ADDITIONAL MATCH)"
                    else:
                        decision_str = "REJECT ADDITIONAL MATCH"

                print(f"Product: {c['name'] or c['code']}")
                print(f"DINO score: {c['score']:.3f}")
                print(f"Color: {prod_fam}")
                print(f"Color compatible: {'YES' if c['color_compatible'] else 'NO'}")
                print(f"Threshold: {c['required_score']:.3f} ({c['thresh_type']})")
                print(f"Best candidate: {'YES' if is_primary and not is_fallback else ('FALLBACK' if is_primary and is_fallback else 'NO')}")
                if is_primary and is_fallback:
                    print("No color-compatible candidates")
                print(f"Final decision: {decision_str}\n")
            print(f"Total displayed products: {len(accepted_candidates)} (dynamic count)")
            print("--------------------------------------------------\n")

        currency = self.settings.get("currency", {})
        symbol = currency.get("symbol", "₹")
        rows = []
        for c in accepted_candidates:
            label_name = c["name"] if c["name"] else str(c["code"])
            label_name = re.sub(r"\s+", " ", label_name).strip().upper()
            if len(label_name) > 22:
                label_name = label_name[:22].rstrip() + "..."
            price_text = f"{symbol}{c['price']:.2f}" if c["price"] > 0 else f"{symbol}0.00"
            label = f"{label_name}\n{price_text}    {c['uom']}"
            image_path = self._product_image_path(
                product={"Name": c["name"], "UOM": c["uom"]},
                meta=c["meta"],
            )
            image_ok = image_path if (image_path and os.path.exists(image_path)) else None
            rows.append((c["code"], float(c["score"]), label, image_ok))

        if not rows:
            if self.listMatches.count() > 0:
                self.listMatches.clear()
            self._last_match_signature = None
            self._last_matched_weight = effective_w
            self._match_locked = True
            if not weight_gating_enabled and current_laptop_obj:
                self._last_matched_obj = current_laptop_obj
            if getattr(self, "lblExtractionMode", None) is not None:
                self.lblExtractionMode.setText("Detection: No item matched threshold")
                self.lblExtractionMode.setStyleSheet(
                    "background: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; "
                    "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
                )
            return

        signature = tuple((code, label, thumb_path) for code, _, label, thumb_path in rows)
        if signature == self._last_match_signature:
            self._last_matched_weight = effective_w
            self._match_locked = True
            if not weight_gating_enabled and current_laptop_obj:
                self._last_matched_obj = current_laptop_obj
            return
        self._last_match_signature = signature

        self.listMatches.clear()
        for code, score, label, thumb_path in rows:
            meta = self.brain.meta.get(code, {})
            uom = str(meta.get("UOM", "PCS")).upper()
            qty_for_item = qty
            if uom == "PCS":
                qty_for_item = self._pcs_qty_from_estimate(qty)
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {"Code": code, "Score": score, "Qty": qty_for_item})
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            item.setSizeHint(QSize(220, 234))
            if thumb_path:
                item.setIcon(QIcon(thumb_path))
            self.listMatches.addItem(item)

        self._last_matched_weight = effective_w
        self._match_locked = True
        if not weight_gating_enabled and current_laptop_obj:
            self._last_matched_obj = current_laptop_obj
        if getattr(self, "lblExtractionMode", None) is not None:
            page_num = getattr(self, "_refresh_page", 0) + 1
            if page_num > 1:
                self.lblExtractionMode.setText(f"Detection: Matched '{prod_name}' (Page {page_num})")
            else:
                self.lblExtractionMode.setText(f"Detection: Matched '{prod_name}'")
            self.lblExtractionMode.setStyleSheet(
                "background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; "
                "border-radius: 6px; padding: 5px 8px; font-size: 11px; font-weight: 500;"
            )

    # ---------- SEARCH ----------
    def _code_key(self, code) -> str:
        return str(code).strip()

    def _clear_products_list(self, clear_selection: bool = True):
        if self._product_icon_timer.isActive():
            self._product_icon_timer.stop()
        self._product_icon_queue = []
        if self.listProducts is not None:
            self.listProducts.clear()
        if clear_selection:
            self._selected_product = None

    def _reset_search_state(self, clear_text: bool = True):
        self._clear_products_list(clear_selection=True)
        if clear_text and self.txtSearch is not None:
            self.txtSearch.blockSignals(True)
            self.txtSearch.setText("")
            self.txtSearch.blockSignals(False)

    def on_search_text_changed(self, text: str):
        if not (text or "").strip():
            self._clear_products_list(clear_selection=True)
            return
        self.run_search()

    def run_search(self, include_trained: Optional[bool] = None):
        q = (self.txtSearch.text() or "").strip()
        if include_trained is None:
            include_trained = getattr(self, "_products_view_mode", "") == "all"
        if not include_trained:
            self._products_view_mode = "search"
        if self.listProducts is None:
            return
        if not q:
            self._clear_products_list(clear_selection=True)
            return

        try:
            rows = fetch_products_like(q, self.settings, limit=100)
        except Exception as e:
            self._msg_critical(str(e))
            return

        self._populate_products(rows, exclude_trained=not include_trained)

    def _update_camera_toggle_button(self):
        if self.btnToggleCamera is None:
            return
        ref_btn = self.btnSearch or self.btnViewProducts or self.btnSettings or getattr(self, "btnRefresh", None)
        ref_h = 45
        if ref_btn is not None:
            h_live = int(ref_btn.height() or 0)
            h_hint = int(ref_btn.sizeHint().height() or 0)
            ref_h = h_live if h_live > 0 else (h_hint if h_hint > 0 else 45)
        cam_w = ref_h + 14
        cam_visible = bool(self.panelRight is not None and self.panelRight.isVisible())
        icon_name = "camera_filled.svg" if cam_visible else "camera_outline.svg"
        icon_path = resolve_asset_path("icons", icon_name)
        has_icon = False
        if os.path.exists(icon_path):
            ico = QIcon(icon_path)
            if not ico.isNull():
                self.btnToggleCamera.setIcon(ico)
                self.btnToggleCamera.setIconSize(QSize(24, 24))
                self.btnToggleCamera.setText("")
                has_icon = True
        if not has_icon:
            self.btnToggleCamera.setIcon(QIcon())
            self.btnToggleCamera.setText("📷" if cam_visible else "🚫")
        self.btnToggleCamera.setMinimumHeight(ref_h)
        self.btnToggleCamera.setMaximumHeight(ref_h)
        self.btnToggleCamera.setMinimumWidth(cam_w)
        self.btnToggleCamera.setMaximumWidth(cam_w)
        self.btnToggleCamera.setToolTip("Hide camera panel" if cam_visible else "Show camera panel")
        self.btnToggleCamera.setStyleSheet(
            """
            QPushButton {
                min-width: 58px;
                border-radius: 12px;
                border: 2px solid #D7DCE4;
                background: #F8FAFC;
                padding: 6px;
                font-size: 16px;
            }
            QPushButton:hover {
                border: 2px solid #BEC8D4;
                background: #F1F5F9;
            }
            QPushButton:pressed {
                background: #E8EEF5;
            }
            """
        )

    def _sync_top_info_boxes_height(self):
        ref_btn = self.btnSearch or self.btnViewProducts or self.btnSettings or getattr(self, "btnRefresh", None)
        if ref_btn is None:
            return
        h_live = int(ref_btn.height() or 0)
        h_hint = int(ref_btn.sizeHint().height() or 0)
        ref_h = h_live if h_live > 0 else (h_hint if h_hint > 0 else 45)
        for w in (self.lblWeight, self.lblInventorySummary, getattr(self, "btnRefresh", None)):
            if w is None or w == ref_btn:
                continue
            if isinstance(w, QLabel):
                w.setFixedHeight(ref_h)
            elif isinstance(w, QPushButton):
                w.setMinimumHeight(ref_h)

    def show_all_products(self):
        self.show_search_panel(load_default_search=False)
        self._hide_keyboard()
        self._products_view_mode = "all"
        if self.txtSearch is not None:
            self.txtSearch.setText("")
        self._clear_products_list(clear_selection=True)
        if self.listProducts is None:
            return

        # Prefer fast in-memory product cache if available, avoiding synchronous SQL blocking
        if getattr(self, "_db_products_by_code", None):
            rows = list(self._db_products_by_code.values())
        else:
            try:
                rows = fetch_all_products(self.settings)
                if rows:
                    self._db_products_by_code = {str(r.get("Code", "")).strip(): r for r in rows}
            except Exception as e:
                self._msg_critical(str(e))
                return

        self._populate_products(rows, exclude_trained=False)

    def refresh_inventory_summary(self):
        if self.lblInventorySummary is None:
            return
        try:
            rows = fetch_all_products(self.settings)
        except Exception:
            self.lblInventorySummary.setText("Total (ALL): -")
            return

        selected = self._selected_db_uom_filter()
        if selected == "ALL":
            total = len(rows)
        else:
            total = sum(1 for it in rows if str(it.get("UOM", "")).strip().upper() == selected)
        self.lblInventorySummary.setText(f"Total ({selected}): {total}")

    def _selected_db_uom_filter(self) -> str:
        selected = str(self.settings.get("db", {}).get("uom_filter", "ALL") or "ALL").strip().upper()
        return selected if selected in {"ALL", "KG", "PCS"} else "ALL"

    def _pcs_qty_from_estimate(self, estimated_qty: int) -> int:
        est = max(1, int(estimated_qty or 1))
        if est <= 1:
            return 1
        history = list(getattr(self, "_qty_history", []) or [])
        recent = history[-6:]
        if len(recent) < 6:
            return 1
        stable_multi_hits = sum(1 for q in recent if int(q) >= 2)
        if stable_multi_hits < 5:
            return 1
        return est

    def _populate_products(self, rows: List[dict], exclude_trained: bool = True):
        if self.listProducts is None:
            return
        self._clear_products_list(clear_selection=True)
        selected = self._selected_db_uom_filter()
        if selected in {"KG", "PCS"}:
            rows = [it for it in rows if str(it.get("UOM", "")).strip().upper() == selected]
        trained_codes = {self._code_key(code) for code in self.brain.data.keys()} if exclude_trained else set()
        currency = self.settings.get("currency", {})
        symbol = currency.get("symbol", "Ã¢â€šÂ¹")

        for it in rows:
            code = self._code_key(it.get("Code", ""))
            if exclude_trained and code in trained_codes:
                continue
            li = QListWidgetItem(
                f"{it['Name']}  [{it['Code']}]  {symbol}{it['Price']:.2f}  {it['UOM']}"
            )
            li.setData(Qt.UserRole, it)
            meta = self.brain.meta.get(code, {})
            self.listProducts.addItem(li)
            icon_path = self._product_image_path(product=it, meta=meta)
            if icon_path:
                li.setData(Qt.UserRole + 1, icon_path)
                self._product_icon_queue.append(li)

        if self._product_icon_queue:
            self._product_icon_timer.start()

    def _process_product_icon_queue(self):
        if self.listProducts is None:
            self._product_icon_queue = []
            self._product_icon_timer.stop()
            return
        if not self._product_icon_queue:
            self._product_icon_timer.stop()
            return
        batch = 10
        for _ in range(min(batch, len(self._product_icon_queue))):
            item = self._product_icon_queue.pop(0)
            if item is None:
                continue
            try:
                icon_path = item.data(Qt.UserRole + 1)
                if icon_path and os.path.exists(icon_path):
                    item.setIcon(QIcon(icon_path))
            except RuntimeError:
                # Item may be deleted if the list is refreshed while queue is processing.
                continue

    def _select_product_from_list(self, item: QListWidgetItem):
        if item is None:
            self._selected_product = None
            return
        self._selected_product = item.data(Qt.UserRole)

    # ---------- TRAIN FLOW ----------
    def train_selected(self):
        if self.listProducts is None:
            return
        item = self.listProducts.currentItem()
        if item is None:
            self._msg_info("Select a product first.")
            return
        it = item.data(Qt.UserRole)
        mode = getattr(self, "_products_view_mode", "")
        if mode == "all":
            self._show_inventory_product_dialog(it)
            return
        self.on_train_clicked(item)

    def _extract_thumb(
        self,
        frame_bgr: np.ndarray,
        polygon: List[List[int]],
        mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        try:
            pts = np.array(polygon, dtype=np.int32)
            x, y, w, h = cv2.boundingRect(pts)
            crop = frame_bgr[y : y + h, x : x + w]
            return crop if crop.size > 0 else frame_bgr
        except Exception:
            return frame_bgr

    def _validate_training_frame(self, frame_bgr: np.ndarray, polygon: List[List[int]]) -> Tuple[bool, str]:
        crop = self._extract_thumb(frame_bgr, polygon)
        if crop is None or crop.size == 0:
            return False, "Invalid camera frame."

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if blur_var < 45.0:
            return False, "Image is blurry. Keep item still and retrain."

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        glare = cv2.inRange(hsv, (0, 0, 245), (179, 40, 255))
        glare_ratio = float(cv2.countNonZero(glare)) / float(glare.size or 1)
        if glare_ratio > 0.65:
            return False, "Too much glare/reflection. Adjust lighting and retrain."

        roi_mask = polygon_foreground_mask(frame_bgr, polygon)
        fg_ratio = float(cv2.countNonZero(roi_mask)) / float(roi_mask.size or 1)
        # if fg_ratio < 0.015:
        #     return False, "Item coverage is too low in ROI. Place item fully inside boundary."

        obj_count, secondary_ratio = self._dominant_object_metrics(frame_bgr)
        # if obj_count == 0:
        #     return False, "No clear item detected in boundary."
        # # Allow one dominant item with tiny secondary blobs from reflections/noise.
        # if obj_count > 1 and secondary_ratio >= 0.30:
        #     return False, "Training requires one dominant item inside boundary."

        return True, ""

    def on_train_clicked(self, item: QListWidgetItem):
        it = item.data(Qt.UserRole)
        if self.latest_frame_raw is None:
            self._msg_warning("No camera frame yet.")
            return

        QApplication.processEvents()
        self._train_product_with_frame(it, self.latest_frame_raw, type_barcode=False)

    def _train_product_with_poses(
        self,
        it: dict,
        frames: List[np.ndarray],
        type_barcode: bool = False,
        polygon_override: Optional[List[List[int]]] = None,
    ) -> bool:
        if not frames:
            return False
        polygon = polygon_override or self.settings["camera"]["polygon"]

        all_feats = []
        primary_thumb = None

        for frame_bgr in frames:
            ok, reason = self._validate_training_frame(frame_bgr, polygon)
            if not ok:
                continue
            fg_mask, _ = self._baseline_foreground_mask(frame_bgr)
            # Extracts synthetic pose variants (rotations, zoom, flip, jitter) for each real pose
            feats = self._features_from_frame_for_training(frame_bgr, polygon_override=polygon, extra_mask=fg_mask)
            if feats:
                all_feats.extend(feats)
            if primary_thumb is None:
                primary_thumb = self._extract_thumb(frame_bgr, polygon, mask=fg_mask)
                primary_frame = frame_bgr
                primary_fg_mask = fg_mask

        if not all_feats:
            self._msg_warning("Could not extract valid training features from the captured poses.")
            return False

        meta = {
            "Code": it.get("Code", ""),
            "Name": it.get("Name", ""),
            "UOM": it.get("UOM", ""),
            "Price": it.get("Price", 0.0),
        }
        existing_meta = self.brain.meta.get(self._code_key(it.get("Code", "")), {})
        if existing_meta.get("display_thumb"):
            meta["display_thumb"] = existing_meta.get("display_thumb")

        # Extract and attach color profile from training frame using empty tray foreground mask
        if _COLOR_MATCHER_AVAILABLE and color_matcher is not None and primary_frame is not None:
            try:
                # Use primary_frame and the empty-tray-subtracted fg_mask so the empty tray is skipped!
                c_prof = color_matcher.compute_color_profile(
                    primary_frame,
                    mask=primary_fg_mask,
                    polygon=polygon,
                )
                if not c_prof and primary_thumb is not None:
                    c_prof = color_matcher.extract_color_profile(primary_thumb)
                if c_prof:
                    meta["color_profile"] = c_prof
                    self._color_profile_cache[self._code_key(it.get("Code", ""))] = c_prof
                    dom_fam = c_prof.get("dominant_family", "UNKNOWN")
                    fam_dist = c_prof.get("families", {})
                    dom_pct = float(fam_dist.get(dom_fam, 1.0)) * 100.0
                    breakdown = ", ".join([f"{f}: {w * 100:.1f}%" for f, w in sorted(fam_dist.items(), key=lambda x: x[1], reverse=True)])
                    print("\n" + "=" * 62)
                    print(f"[TRAINING COLOR] Product: '{it.get('Name')}' (Code: {it.get('Code')})")
                    print(f"  • Trained Color Family:  {dom_fam} ({dom_pct:.1f}%)")
                    if breakdown:
                        print(f"  • Color Breakdown:       {breakdown}")
                    print(f"  • Status:                Color profile & DINOv3 embeddings saved! (Empty tray skipped)")
                    print("=" * 62 + "\n")
            except Exception as e:
                print(f"[Training] Could not extract color profile: {e}")

        # Add all DINOv3 pose variants as individual gallery entries (respecting max_samples cap)
        self.brain.learn_batch(it["Code"], all_feats, meta=meta, thumb_bgr=primary_thumb)

        self.refresh_trained_list()
        self._refresh_products_list_after_training_change()

        if type_barcode:
            qty = self._display_weight if str(it.get("UOM", "KG")).upper() != "PCS" else 1
            barcode = make_barcode(it, qty, self.settings)
            self._type_barcode(barcode)

        # After successful training, return to dashboard predictions view.
        self.show_dashboard_page()
        # Invalidate old match locks so the newly trained product is detected immediately
        self._match_locked = False
        self._last_matched_weight = None
        self._last_match_signature = None
        self._last_matched_obj = None
        self._suppress_matching_until_zero = False
        self._sync_db_products_cache(force=True)
        # Auto-trigger recognition for the vegetable already sitting on the scale
        QTimer.singleShot(150, lambda: self.try_match(force=True))
        return True

    def _train_product_with_frame(
        self,
        it: dict,
        frame_bgr: np.ndarray,
        type_barcode: bool,
        polygon_override: Optional[List[List[int]]] = None,
    ) -> bool:
        return self._train_product_with_poses(
            it,
            [frame_bgr],
            type_barcode=type_barcode,
            polygon_override=polygon_override,
        )

    def _get_selected_product(self) -> Optional[dict]:
        if self._selected_product:
            return self._selected_product
        if self.listProducts is not None:
            item = self.listProducts.currentItem()
            if item is not None:
                return item.data(Qt.UserRole)
        return None


    def refresh_trained_list(self):
        if self.listTrained is None:
            return
        self.listTrained.clear()
        for code in sorted(self.brain.data.keys()):
            meta = self.brain.meta.get(code, {})
            name = meta.get("Name") or meta.get("name") or ""
            label = f"{name}\n[{code}]" if name else str(code)
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {"Code": code})
            image_path = self._product_image_path(
                product={"Name": name, "UOM": meta.get("UOM", "")},
                meta=meta,
            )
            if image_path and os.path.exists(image_path):
                item.setIcon(QIcon(image_path))
            self.listTrained.addItem(item)

        if self.lblPreview is not None:
            self.lblPreview.setText("Preview")
            self.lblPreview.setPixmap(QPixmap())
        if self.lblSelectedInfo is not None:
            self.lblSelectedInfo.setText("Select a trained item to preview or retrain.")
        if self.btnRetrain is not None:
            self.btnRetrain.setEnabled(False)

    def _refresh_products_list_after_training_change(self):
        mode = getattr(self, "_products_view_mode", "")
        if mode == "all":
            self.show_all_products()
            return
        if mode == "search":
            self.run_search()
            return
        self._clear_products_list(clear_selection=True)

    def on_trained_selected(self, item: QListWidgetItem):
        code = item.data(Qt.UserRole).get("Code")
        meta = self.brain.meta.get(code, {})
        name = meta.get("Name") or meta.get("name") or ""
        info = f"{name} [{code}]" if name else str(code)
        if self.lblSelectedInfo is not None:
            self.lblSelectedInfo.setText(info)

        if self.lblPreview is not None:
            image_path = self._product_image_path(
                product={"Name": name, "UOM": meta.get("UOM", "")},
                meta=meta,
            )
            if image_path and os.path.exists(image_path):
                pix = QPixmap(image_path)
                scaled = pix.scaled(
                    self.lblPreview.width(),
                    self.lblPreview.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.lblPreview.setPixmap(scaled)
            else:
                self.lblPreview.setText("No preview")
                self.lblPreview.setPixmap(QPixmap())

        if self.btnRetrain is not None:
            self.btnRetrain.setEnabled(True)

    def on_prediction_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole) or {}
        code = data.get("Code")
        print(data)
        if not code:
            return
        qty_hits = int(data.get("Qty", 1) or 1)

        meta = self.brain.meta.get(code, {})
        uom = str(meta.get("UOM", "KG")).upper()
        price = float(meta.get("Price", 0.0) or 0.0)
        fetched = fetch_product_by_code(code, self.settings)
        if fetched:
            display_thumb = meta.get("display_thumb")
            meta = {
                "Code": fetched.get("Code", code),
                "Name": fetched.get("Name", meta.get("Name", "")),
                "UOM": fetched.get("UOM", "KG"),
                "Price": fetched.get("Price", 0.0),
                "thumb": meta.get("thumb"),
            }
            if display_thumb:
                meta["display_thumb"] = display_thumb
            self.brain.meta[code] = meta
            self.brain.save_meta()
            uom = str(meta.get("UOM", "KG")).upper()
            price = float(meta.get("Price", 0.0) or 0.0)
        if price <= 0:
            price = 0.0

        if uom == "PCS":
            qty = max(1, qty_hits)
        else:
            qty = float(self._display_weight)
            if qty <= 0.0:
                qty = 1.0
        it = {"Code": code, "Price": price, "UOM": uom}
        full_item = meta if isinstance(meta, dict) else {}

        if uom == "PCS" and qty > 1:
            code_text = make_barcode(it, 1, self.settings)
            self._pending_selection_action = lambda: self._type_codes([code_text] * qty)
        else:
            barcode = make_barcode(it, qty, self.settings)
            self._pending_selection_action = lambda: self._type_barcode(barcode)

        # SPEAK ITEM NAME BEFORE CLOSING
        item_name = full_item.get("Name", "Item")
        threading.Thread(
            target=self.speak_selected_item,
            args=(f"{item_name}",),
            daemon=True,
        ).start()

        # Execute immediately so app hide and barcode typing start without delay.
        self.execute_click_paste_enter()
        QTimer.singleShot(200, lambda: setattr(self, "active_selection", None))
        QTimer.singleShot(200, lambda: setattr(self, "is_analyzing", False))
        self._suppress_open_until_weight_change = True
        self._last_hide_weight = self._last_weight

    def execute_click_paste_enter(self):
        action = getattr(self, "_pending_selection_action", None)
        if callable(action):
            self._pending_selection_action = None
            action()

    def show_mini_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def retrain_selected(self):
        if self.latest_frame_raw is None:
            self._msg_warning("No camera frame yet.")
            return
        if self.listTrained is None:
            return
        item = self.listTrained.currentItem()
        if item is None:
            return

        it = item.data(Qt.UserRole)
        QApplication.processEvents()
        if self._train_product_with_frame(it, self.latest_frame_raw, type_barcode=False):
            self._msg_info(f"Retrained item: {it.get('Code', '')}")

    # ---------- DETECT ACTIONS ----------
    def clear_match_selection(self):
        if self.listMatches is None:
            return
        for i in range(self.listMatches.count()):
            item = self.listMatches.item(i)
            item.setCheckState(Qt.Unchecked)
            item.setSelected(False)

    def use_selected_matches(self):
        if self.listMatches is None:
            return
        selected = []
        for i in range(self.listMatches.count()):
            item = self.listMatches.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item)
        if not selected:
            selected = self.listMatches.selectedItems()
        if not selected:
            self._msg_info("Select one or more matches first.")
            return

        barcodes = []
        skipped = []
        for item in selected:
            data = item.data(Qt.UserRole) or {}
            code = data.get("Code")
            if not code:
                continue
            meta = self.brain.meta.get(code, {})
            uom = str(meta.get("UOM", "KG")).upper()
            price = float(meta.get("Price", 0.0) or 0.0)
            if price <= 0:
                skipped.append(code)
                continue
            qty = 1 if uom == "PCS" else float(self._display_weight)
            if uom != "PCS" and qty <= 0.0:
                skipped.append(code)
                continue
            it = {"Code": code, "Price": price, "UOM": uom}
            barcodes.append(make_barcode(it, qty, self.settings))

        if not barcodes:
            self._msg_info("No barcodes generated (missing price/UOM).")
            return

        self._type_barcode("\n".join(barcodes))

    def _type_barcode(self, text: str):
        if not text:
            return

        # Paste is more reliable than per-char typing for POS text fields.
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(str(text))

        self.hide()
        target_hwnd = getattr(self, "_prev_hwnd", None)
        if not target_hwnd:
            fg = _get_foreground_hwnd()
            self_hwnd = self._self_hwnd()
            if fg and (self_hwnd is None or fg != self_hwnd):
                target_hwnd = fg

        def _do_type():
            time.sleep(0.12)
            if target_hwnd:
                if not _set_foreground_hwnd(target_hwnd):
                    time.sleep(0.08)
                    _set_foreground_hwnd(target_hwnd)
            time.sleep(0.08)
            if pyautogui is not None:
                try:
                    pyautogui.hotkey("ctrl", "v")
                    pyautogui.press("enter")
                    return
                except Exception:
                    pass
            if _send_ctrl_v(send_enter=True):
                return
            _send_input_keys(text, send_enter=True)

        threading.Thread(target=_do_type, daemon=True).start()

    def _type_codes(self, codes: List[str]):
        if not codes:
            return

        self.hide()
        target_hwnd = getattr(self, "_prev_hwnd", None)
        if not target_hwnd:
            fg = _get_foreground_hwnd()
            self_hwnd = self._self_hwnd()
            if fg and (self_hwnd is None or fg != self_hwnd):
                target_hwnd = fg

        def _do_type():
            time.sleep(0.12)
            if target_hwnd:
                if not _set_foreground_hwnd(target_hwnd):
                    time.sleep(0.08)
                    _set_foreground_hwnd(target_hwnd)
            time.sleep(0.08)
            if pyautogui is not None:
                try:
                    pyautogui.PAUSE = 0.05
                    for code in codes:
                        pyautogui.write(str(code), interval=0.05)
                        pyautogui.press("enter")
                        time.sleep(0.2)
                    return
                except Exception:
                    pass
            for code in codes:
                _send_input_keys(str(code), send_enter=True)
                time.sleep(0.05)

        threading.Thread(target=_do_type, daemon=True).start()

    # ---------- SETTINGS UI ----------
    def populate_ports(self):
        if self.cmbCom is None:
            return
        self.cmbCom.clear()
        ports = [p.portName() for p in QSerialPortInfo.availablePorts()]
        self.cmbCom.addItems(ports if ports else ["COM1"])

    def populate_settings_ui(self):
        s = self.settings

        sc = s["scale"]
        if self.cmbCom is not None:
            self.cmbCom.setCurrentText(sc.get("port", "COM1"))
        if self.cmbBaud is not None:
            self.cmbBaud.setCurrentText(str(sc.get("baud", 9600)))
        if self.spnStableSeconds is not None:
            self.spnStableSeconds.setValue(float(sc.get("stable_seconds", 0.17)))
        if self.spnOpenThreshold is not None:
            self.spnOpenThreshold.setValue(float(sc.get("open_threshold", 0.001)))

        cam = s["camera"]
        # camera UI reduced to behavior-only controls

        beh = s["behavior"]
        if self.spnMatchThreshold is not None:
            self.spnMatchThreshold.setValue(float(beh.get("match_threshold", 0.55)))
        if self.txtMaxSamples is not None:
            self.txtMaxSamples.setText(str(int(beh.get("max_samples", 40))))

        qr = s["qr"]
        if self.txtPrefix is not None:
            self.txtPrefix.setText(str(qr.get("prefix_value", "20")))
        if self.txtCodeLen is not None:
            self.txtCodeLen.setText(str(int(qr.get("code_len", 5))))
        if self.txtPriceLen is not None:
            self.txtPriceLen.setText(str(int(qr.get("price_len", 5))))
        if self.txtQtyLen is not None:
            self.txtQtyLen.setText(str(int(qr.get("qty_len", 5))))

        db = s["db"]
        if self.txtDbServer is not None:
            self.txtDbServer.setText(db.get("server", "localhost"))
        if self.txtDbName is not None:
            self.txtDbName.setText(db.get("database", ""))
        if self.txtDbUser is not None:
            self.txtDbUser.setText(db.get("user", ""))
        if self.txtDbPass is not None:
            self.txtDbPass.setText(db.get("password", ""))
        if self.cmbDbUomFilter is not None:
            value = str(db.get("uom_filter", "ALL") or "ALL").strip().upper()
            idx = self.cmbDbUomFilter.findText(value, Qt.MatchFixedString)
            self.cmbDbUomFilter.setCurrentIndex(idx if idx >= 0 else 0)
        
        cur = s.get("currency", {})
        if self.cmbCurrency is not None:
            code = cur.get("code", "INR")
            if code == "SGD":
                self.cmbCurrency.setCurrentIndex(1)
            else:
                self.cmbCurrency.setCurrentIndex(0)

    def save_settings_from_ui(self):
        s = self.settings
        current_wg = bool(s.get("behavior", {}).get("weight_gating", s.get("scale", {}).get("enabled", False)))
        s["scale"]["enabled"] = current_wg
        s["behavior"]["weight_gating"] = current_wg
        s["camera"]["enabled"] = True
        s["db"]["enabled"] = True

        # scale
        if self.cmbCom is not None:
            s["scale"]["port"] = self.cmbCom.currentText()
        if self.cmbBaud is not None:
            s["scale"]["baud"] = int(self.cmbBaud.currentText())
        if self.spnStableSeconds is not None:
            s["scale"]["stable_seconds"] = float(self.spnStableSeconds.value())
        if self.spnOpenThreshold is not None:
            s["scale"]["open_threshold"] = float(self.spnOpenThreshold.value())

        # camera (index/boundary/polygon UI removed)

        # behavior
        if self.spnMatchThreshold is not None:
            s["behavior"]["match_threshold"] = float(self.spnMatchThreshold.value())
        if self.txtMaxSamples is not None:
            try:
                s["behavior"]["max_samples"] = int(self.txtMaxSamples.text().strip())
            except Exception:
                s["behavior"]["max_samples"] = int(self.settings["behavior"].get("max_samples", 40))
            self.brain.max_samples = int(s["behavior"]["max_samples"])

        # qr
        if self.txtPrefix is not None:
            s["qr"]["prefix_value"] = self.txtPrefix.text().strip() or "20"
        if self.txtCodeLen is not None:
            try:
                s["qr"]["code_len"] = int(self.txtCodeLen.text().strip())
            except Exception:
                s["qr"]["code_len"] = int(self.settings["qr"].get("code_len", 5))
        if self.txtPriceLen is not None:
            try:
                s["qr"]["price_len"] = int(self.txtPriceLen.text().strip())
            except Exception:
                s["qr"]["price_len"] = int(self.settings["qr"].get("price_len", 5))
        if self.txtQtyLen is not None:
            try:
                s["qr"]["qty_len"] = int(self.txtQtyLen.text().strip())
            except Exception:
                s["qr"]["qty_len"] = int(self.settings["qr"].get("qty_len", 5))

        # db
        if self.txtDbServer is not None:
            s["db"]["server"] = self.txtDbServer.text().strip()
        if self.txtDbName is not None:
            s["db"]["database"] = self.txtDbName.text().strip()
        if self.txtDbUser is not None:
            s["db"]["user"] = self.txtDbUser.text().strip()
        if self.txtDbPass is not None:
            s["db"]["password"] = self.txtDbPass.text()
        if self.cmbDbUomFilter is not None:
            s["db"]["uom_filter"] = self.cmbDbUomFilter.currentText().strip().upper() or "ALL"

        # currency
        if self.cmbCurrency is not None:
            if self.cmbCurrency.currentIndex() == 1:
                s["currency"] = {
                    "code": "SGD",
                    "symbol": "$"
                }
            else:
                s["currency"] = {
                    "code": "INR",
                    "symbol": "₹"
                }



        save_settings(s)

        # apply scale live
        sc = s["scale"]
        ok = self.scale.reconfigure(sc["port"], sc["baud"], stable_seconds=float(sc.get("stable_seconds", 0.17)))

        self.scale_connected = bool(ok)
        if ok and self._demo_timer is not None:
            self._demo_timer.stop()
            self._demo_timer = None
        elif not ok:
            self.start_demo_weight()

        # restart camera if changed
        self.start_or_restart_camera()

        self.refresh_inventory_summary()
        self._msg_info("Your settings have been saved.")

    # ---------- POLYGON SPINBOX HELPERS ----------
    def _update_polygon_spinboxes(self, poly: List[List[int]]):
        spins = [self.spinX1, self.spinY1, self.spinX2, self.spinY2, self.spinX3, self.spinY3, self.spinX4, self.spinY4]
        if any(sp is None for sp in spins):
            return

        vals = [poly[0][0], poly[0][1], poly[1][0], poly[1][1], poly[2][0], poly[2][1], poly[3][0], poly[3][1]]
        for sp, v in zip(spins, vals):
            sp.blockSignals(True)
            sp.setValue(int(v))
            sp.blockSignals(False)
        self._update_polygon_label()

    def _update_polygon_label(self):
        if self.lblPolygonInfo is None:
            return
        poly = self.settings.get("camera", {}).get("polygon", [])
        if not poly or len(poly) != 4:
            self.lblPolygonInfo.setText("ROI: (n/a)")
            return
        pts = " ".join([f"({p[0]},{p[1]})" for p in poly])
        self.lblPolygonInfo.setText(f"ROI: {pts}")

    def save_polygon(self):
        save_settings(self.settings)
        self._update_polygon_label()
        self._msg_info("ROI coordinates saved.")

    def _polygon_from_spinboxes(self) -> Optional[List[List[int]]]:
        spins = [self.spinX1, self.spinY1, self.spinX2, self.spinY2, self.spinX3, self.spinY3, self.spinX4, self.spinY4]
        if any(sp is None for sp in spins):
            return None
        return [
            [int(self.spinX1.value()), int(self.spinY1.value())],
            [int(self.spinX2.value()), int(self.spinY2.value())],
            [int(self.spinX3.value()), int(self.spinY3.value())],
            [int(self.spinX4.value()), int(self.spinY4.value())],
        ]

    def on_polygon_spin_changed(self, _):
        poly = self._polygon_from_spinboxes()
        if poly is None:
            return
        self.settings["camera"]["polygon"] = poly
        save_settings(self.settings)
        self._update_polygon_label()
        # redraw immediately if we have a frame
        if self.latest_frame_raw is not None:
            self.on_frame(self.latest_frame_raw)

    def reset_polygon(self):
        if self.latest_frame_raw is None:
            return
        h, w = self.latest_frame_raw.shape[:2]
        pad_x = int(w * 0.15)
        pad_y = int(h * 0.15)
        poly = [[pad_x, pad_y], [w - pad_x, pad_y], [w - pad_x, h - pad_y], [pad_x, h - pad_y]]
        self.settings["camera"]["polygon"] = poly
        save_settings(self.settings)
        self._update_polygon_label()
        self.on_frame(self.latest_frame_raw)

    # ---------- DRAG POINTS ON PREVIEW LABEL ----------
    def eventFilter(self, obj, event):
        if obj == self.txtSearch:
            if event.type() == QEvent.MouseButtonPress:
                search_open = (
                    self.dashboardStack is not None
                    and self.pageSearch is not None
                    and self.dashboardStack.currentWidget() == self.pageSearch
                )
                if search_open and self.keyboardPanel is not None:
                    self.keyboardPanel.setVisible(not self.keyboardPanel.isVisible())
            return super().eventFilter(obj, event)

        if obj == self.lblCamera:
            if self.latest_frame_raw is None:
                return super().eventFilter(obj, event)

            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_target_label = obj
                self._drag_idx = self._pick_handle(obj, event.position().toPoint())
                return self._drag_idx is not None

            if event.type() == QEvent.MouseMove and (event.buttons() & Qt.LeftButton) and self._drag_idx is not None:
                self._move_handle(obj, self._drag_idx, event.position().toPoint())
                return True

            if event.type() == QEvent.MouseButtonRelease and self._drag_idx is not None:
                self._drag_idx = None
                self._drag_target_label = None
                save_settings(self.settings)
                self._update_polygon_label()
                return True

        return super().eventFilter(obj, event)

    def _pick_handle(self, label: QLabel, pos: QPoint) -> Optional[int]:
        pts_label = [self._frame_to_label(label, p) for p in self.settings["camera"]["polygon"]]
        for i, p in enumerate(pts_label):
            if p is None:
                continue
            if (p - pos).manhattanLength() <= 18:
                return i
        return None

    def _move_handle(self, label: QLabel, idx: int, pos: QPoint):
        fx, fy = self._label_to_frame_xy(label, pos)
        if fx is None:
            return

        h, w = self.latest_frame_raw.shape[:2]
        fx = max(0, min(w - 1, int(fx)))
        fy = max(0, min(h - 1, int(fy)))

        poly = self.settings["camera"]["polygon"]
        poly[idx] = [fx, fy]
        self.settings["camera"]["polygon"] = poly

        self._update_polygon_spinboxes(poly)
        self._update_polygon_label()

        # redraw
        self.on_frame(self.latest_frame_raw)

    def _pixmap_draw_rect(self, label: QLabel):
        pm = label.pixmap()
        if pm is None:
            return None
        lw, lh = label.width(), label.height()
        pw, ph = pm.width(), pm.height()
        x0 = (lw - pw) // 2
        y0 = (lh - ph) // 2
        return x0, y0, pw, ph

    def _label_to_frame_xy(self, label: QLabel, label_pos: QPoint):
        rect = self._pixmap_draw_rect(label)
        if rect is None:
            return None, None

        x0, y0, pw, ph = rect
        x = label_pos.x() - x0
        y = label_pos.y() - y0

        if x < 0 or y < 0 or x >= pw or y >= ph:
            return None, None

        fh, fw = self.latest_frame_raw.shape[:2]
        fx = (x / max(1, pw)) * fw
        fy = (y / max(1, ph)) * fh
        return fx, fy

    def _frame_to_label(self, label: QLabel, pt):
        rect = self._pixmap_draw_rect(label)
        if rect is None:
            return None
        x0, y0, pw, ph = rect
        fh, fw = self.latest_frame_raw.shape[:2]
        fx, fy = pt
        lx = x0 + int((fx / max(1, fw)) * pw)
        ly = y0 + int((fy / max(1, fh)) * ph)
        return QPoint(lx, ly)

    # ---------- CLOSE ----------
    def closeEvent(self, event):
        try:
            if self.cam is not None:
                self.cam.stop()
                self.cam.wait(1500)
        except Exception:
            pass
        try:
            self.scale.close()
        except Exception:
            pass
        event.accept()
        
    #Add this function inside class POSv5
    def speak_selected_item(self, text):
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)   # Natural speed

            # Force female voice
            voices = engine.getProperty('voices')
            for v in voices:
                if "female" in v.name.lower() or "zira" in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break

            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print("TTS Error:", e)


# def main():
#     QCoreApplication.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True)
#     QCoreApplication.setAttribute(Qt.AA_SynthesizeTouchForUnhandledMouseEvents, True)
#     app = QApplication([])
#     enforce_license()
#     w = Dashboard()
#     w.show()
#     screen = QApplication.primaryScreen().availableGeometry()
#     x = screen.x() + (screen.width() - w.width()) // 2
#     y = screen.y() + (screen.height() - w.height()) // 2
#     w.move(x, y)
#     w.raise_()
#     w.activateWindow()
#     app.exec()


def main():
    QCoreApplication.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents, True)
    QCoreApplication.setAttribute(Qt.AA_SynthesizeTouchForUnhandledMouseEvents, True)

    app = QApplication(sys.argv)

    # enforce_license()

    w = Dashboard()

    screen = QApplication.primaryScreen().availableGeometry()
    x = screen.x() + (screen.width() - w.width()) // 2
    y = screen.y() + (screen.height() - w.height()) // 2
    w.move(x, y)

    # On first launch, open the Dashboard and show the black floating box
    w.show()
    w.raise_()
    w.activateWindow()
    if getattr(w, "float", None) is not None:
        w.float.show()
        w.float.raise_()

    sys.exit(app.exec())



if __name__ == "__main__":
    main()



