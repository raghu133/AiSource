import json
import os
from copy import deepcopy
from typing import Any, Dict
from app_config import SETTINGS_PATH

DEFAULT_SETTINGS: Dict[str, Any] = {
    "scale": {
        "enabled": True,
        "port": "COM1",
        "baud": 9600,
        "stable_seconds": 0.5,
        "open_threshold_kg": 0.005
    },
    "camera": {
        "enabled": True,
        "index": 0,
        "roi": [80, 60, 480, 360],
        "capture_on_train": True
    },
    "boundary": {
        "match_threshold": 0.55,
        "stickiness_frames": 6,
        "max_samples_per_item": 40
    },
    "qr": {
        "prefix_value": "20",
        "code_len": 5,
        "price_len": 5,
        "qty_len": 6,
        "pcs_qty_scale": 10000,
        "kg_qty_scale": 100000
    },
    "currency": {
        "code": "INR",     # INR | SGD
        "symbol": "₹"
    },
    "db": {
        "enabled": False,
        "driver": "ODBC Driver 17 for SQL Server",
        "server": "localhost\\SQLEXPRESS",
        "database": "",
        "user": "",
        "password": "",
        "table": "tblInventory",
        "col_code": "InventoryCode",
        "col_name": "Description",
        "col_uom": "UOM",
        "col_brand": "BrandCode",
        "col_price": "RetailPrice"
    },
    "pos": {
        "mode": "clipboard",     # clipboard | autotype
        "autotype_enter": False
    }
}

def _deep_merge(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst

def load_settings() -> dict:
    s = deepcopy(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            _deep_merge(s, user)
        except Exception:
            pass
    return s

def save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
