# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for AI_Trainer_v3 (main3.py).
Builds a standalone distribution folder containing the Meta DINOv3 ViT-S/16 ONNX
vision embeddings engine, PySide6 UI, assets, license manager, and required runtime dependencies.
Pure visual embeddings mode (no color gating, no YOLO cropper).
"""

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs

block_cipher = None

# Base directory (works inside PyInstaller build and standalone Python)
project_dir = os.path.abspath(SPECPATH if "SPECPATH" in locals() else os.getcwd())

# 1. Core UI and branding assets
datas = [
    (os.path.join(project_dir, "dashboard.ui"), "."),
    (os.path.join(project_dir, "logo.png"), "."),
    (os.path.join(project_dir, "iLogo.png"), "."),
]

# 2. Config, baseline, database, and learned state files (if present)
for optional_file in [
    ".env",
    "license_db.sqlite",
    "settings.json",
    "empty_tray_baseline.jpg",
    "empty_cover_baseline.jpg",
    "learned_meta.json",
    "learned_data_dinov3.json",
]:
    full_path = os.path.join(project_dir, optional_file)
    if os.path.exists(full_path):
        datas.append((full_path, "."))

# 3. Asset directories (icons, thumbnails, reference images)
for optional_dir in ["icons", "thumbs", "Imgs"]:
    dir_path = os.path.join(project_dir, optional_dir)
    if os.path.exists(dir_path):
        datas.append((dir_path, optional_dir))

# 4. Meta DINOv3 ONNX model files strictly needed by main3.py
# Excludes legacy SigLIP (~800MB), unused YOLO models (~52MB), and duplicate tensor weights (~86MB)
models_dir = os.path.join(project_dir, "models")
required_models = [
    "dinov3_vits16.onnx",
    "model.onnx_data",
    "dinov3_meta.json",
    "DINOV3_LICENSE.txt",
]
if os.path.exists(models_dir):
    for f in required_models:
        f_path = os.path.join(models_dir, f)
        if os.path.exists(f_path):
            datas.append((f_path, "models"))

# 5. Collect ONNX Runtime dynamic libraries (.dll)
binaries = []
try:
    binaries += collect_dynamic_libs("onnxruntime")
except Exception:
    pass

# 6. Explicit hidden imports for PySide6, Serial, TTS, Encryption & Helper modules
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtUiTools",
    "PySide6.QtSerialPort",
    "onnxruntime",
    "pyodbc",
    "pyttsx3",
    "pyttsx3.drivers",
    "pyttsx3.drivers.sapi5",
    "pyautogui",
    "cryptography",
    "cryptography.fernet",
    "dotenv",
    "machine_id",
    "licence_manager",
    "dinov3_vision",
    "color_matcher",
    "dino_vision",
    "dino_embedding",
    "qr_utils",
    "sqlite3",
]

hiddenimports = list(dict.fromkeys(hiddenimports))

# 7. Exclude heavy unused packages to prevent multi-gigabyte bloat and long build times
excludes = [
    "torch",
    "torchvision",
    "transformers",
    "ultralytics",
    "scipy",
    "matplotlib",
    "sentencepiece",
    "polars",
    "_polars_runtime",
    "pyarrow",
    "pandas",
    "tensorboard",
    "PyQt5",
    "PyQt6",
    "tkinter",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQml",
    "PySide6.Qt3DCore",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSensors",
    "PySide6.QtWebSockets",
]

# Application icon (prefer .ico for Windows PE executable)
ico_path = os.path.join(project_dir, "logo.ico")
icon_file = ico_path if os.path.exists(ico_path) else None

a = Analysis(
    ["main3.py"],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI_Trainer_v3",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AI_Trainer_v3",
)
