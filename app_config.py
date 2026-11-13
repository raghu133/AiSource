import os

APP_NAME = "AI_Trainer"

def app_data_dir() -> str:
    if os.name == "nt":
        return os.path.join(os.environ.get("APPDATA", os.getcwd()), APP_NAME)
    return os.path.expanduser(f"~/.{APP_NAME.lower()}")

APP_DIR = app_data_dir()
os.makedirs(APP_DIR, exist_ok=True)

SETTINGS_PATH = os.path.join(APP_DIR, "settings.json")
LEARNED_PATH  = os.path.join(APP_DIR, "learned_data.json")
