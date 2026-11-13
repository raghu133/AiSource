# # import customtkinter as ctk
# # import os
# # import cv2
# # import tkinter as tk
# # from tkinter import messagebox, filedialog
# # from PIL import Image, ImageTk
# # import db_functions
# # import time
# # from datetime import datetime, timedelta
# # import threading
# # import json
# # import shutil
# # import history_logger
# # import weighing_scale
# # import sys

# # from app_config import DB_CONFIG
# # # Try importing matplotlib for Pie Chart; handle gracefully if missing
# # try:
# #     from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# #     import matplotlib.pyplot as plt
# #     HAS_MATPLOTLIB = True
# # except ImportError:
# #     HAS_MATPLOTLIB = False


# # # BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # # SETTINGS_PATH = os.path.join(BASE_DIR, "config", "app_settings.json")

# # import sys

# # APP_NAME = "AI_POS"


# # import sys

# # def get_app_base_dir():
# #     if getattr(sys, "frozen", False):
# #         return os.path.dirname(sys.executable)
# #     return os.path.dirname(os.path.abspath(__file__))

# # BASE_DIR = get_app_base_dir()

# # def get_app_data_dir():
# #     if sys.platform == "win32":
# #         return os.path.join(os.environ["APPDATA"], APP_NAME)
# #     return os.path.expanduser(f"~/.{APP_NAME.lower()}")

# # APP_DATA_DIR = get_app_data_dir()
# # CONFIG_DIR = os.path.join(APP_DATA_DIR, "config")
# # os.makedirs(CONFIG_DIR, exist_ok=True)

# # CONFIG_PATH = os.path.join(CONFIG_DIR, "db_config.json")


# # SETTINGS_PATH = os.path.join(CONFIG_DIR, "app_settings.json")



# # def load_app_settings():
# #     if os.path.exists(SETTINGS_PATH):
# #         with open(SETTINGS_PATH, "r") as f:
# #             return json.load(f)
# #     return {}

# # def save_app_settings(data):
# #     os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
# #     with open(SETTINGS_PATH, "w") as f:
# #         json.dump(data, f, indent=4)

# # # BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # FIXED_SQL_SERVER = "localhost"

# # class HoverableCard(ctk.CTkFrame):
# #     def __init__(self, master, normal_color, hover_color, **kwargs):
# #         super().__init__(master, fg_color=normal_color, **kwargs)
# #         self.normal_color = normal_color
# #         self.hover_color = hover_color
# #         self.bind("<Enter>", lambda e: self.configure(fg_color=self.hover_color))
# #         self.bind("<Leave>", lambda e: self.configure(fg_color=self.normal_color))

# # class SettingsUI:
# #     def __init__(self, parent, colors, main_app):
# #         self.parent = parent
# #         self.colors = colors
# #         self.main_app = main_app

        
        
# #         # Canvas size MUST come first
# #         self.canvas_w, self.canvas_h = 480, 360

# #         # ROI corner points (4 handles)
# #         self.tl = [0, 0]                     # top-left
# #         self.tr = [self.canvas_w, 0]         # top-right
# #         self.bl = [0, self.canvas_h]         # bottom-left
# #         self.br = [self.canvas_w - 1, self.canvas_h - 1] # bottom-right
        
# #         self.current_uom_filter = "ALL ITEM"
# #         self.search_query = ""
# #         self.roi_active = False
        
# #         # QR Settings Defaults
# #         self.qr_prefix_on = ctk.StringVar(value="OFF")
# #         self.qr_prefix_val = "20"
# #         self.qr_code_len = 5
# #         self.qr_price_len = 5
# #         self.qr_qty_len = 5
# #         self.qr_currency = "USD"

# #         self.app_settings = load_app_settings()
        
# #         self.canvas_w, self.canvas_h = 480, 360
# #         self.active_handle = None
# #         self.pt1, self.pt2 = [0,0], [0,0] # Init placeholders
        
        
# #         self.current_page = 0
# #         self.history_filter_val = ctk.StringVar(value="LiveNow")
        
# #         # Sidebar Init
# #         self.sidebar = ctk.CTkFrame(self.parent, width=180, fg_color=self.colors["OCEAN"], corner_radius=0)
# #         self.sidebar.pack(side="left", fill="y")
        
# #         self.content_area = ctk.CTkFrame(self.parent, fg_color="transparent")
# #         self.content_area.pack(side="right", fill="both", expand=True)

# #         self.setup_sidebar()
# #         self.show_dashboard()

# #     def setup_sidebar(self):
# #         # ===== LOGO SECTION =====
# #         img_logo_path = os.path.join(BASE_DIR, "iLogic.webp")

# #         logo_frame = ctk.CTkFrame(
# #             self.sidebar,
# #             fg_color="transparent"
# #         )
# #         logo_frame.pack(fill="x", pady=(25, 15))

# #         if os.path.exists(img_logo_path):
# #             try:
# #                 raw_img = Image.open(img_logo_path)
# #                 logo_ctk = ctk.CTkImage(raw_img, size=(130, 130))
# #                 ctk.CTkLabel(
# #                     logo_frame,
# #                     image=logo_ctk,
# #                     text=""
# #                 ).pack()
# #             except:
# #                 pass

# #         ctk.CTkLabel(
# #             logo_frame,
# #             text="iLogic POS",
# #             font=("Segoe UI", 20, "bold"),
# #             text_color="white"
# #         ).pack(pady=(10, 0))

# #         # ===== DIVIDER =====
# #         ctk.CTkFrame(
# #             self.sidebar,
# #             height=1,
# #             fg_color="#2a2a2a"
# #         ).pack(fill="x", padx=20, pady=15)

# #         # ===== NAVIGATION =====
# #         nav_items = [
# #             ("📊  Dashboard", self.show_dashboard),
# #             ("🛒  View Products", self.show_view_product),
# #             ("⚖︎  Weight Setting", self.show_weight_setting),
# #             ("📷  Camera Setting", self.show_camera_settings),
# #             # ("⛶  QR Setting", self.show_qr_settings),
# #             ("🙎🏻‍♂️  About", self.show_about),
# #             ("⚙️  Database Setting", self.show_database_setting)
# #         ]

# #         for text, cmd in nav_items:
# #             btn = ctk.CTkButton(
# #                 self.sidebar,
# #                 text=text,
# #                 anchor="w",
# #                 height=44,                       # ⬅ Bigger button
# #                 font=("Segoe UI", 14),
# #                 fg_color="transparent",
# #                 hover_color=self.colors["NAVY"],
# #                 text_color="white",
# #                 command=cmd
# #             )
# #             btn.pack(fill="x", padx=20, pady=4)

# #         # ===== EXIT BUTTON =====
# #         ctk.CTkButton(
# #             self.sidebar,
# #             text="⏻  Exit",
# #             height=45,
# #             font=("Segoe UI", 14, "bold"),
# #             fg_color=self.colors["CORAL"],
# #             hover_color="#c0392b",
# #             command=self.main_app.show_main_view
# #         ).pack(side="bottom", fill="x", padx=20, pady=25)

# #     # def setup_sidebar(self):
# #     #     img_logo_path = os.path.join(BASE_DIR, "iLogic.webp")
# #     #     if os.path.exists(img_logo_path):
# #     #         try:
# #     #             raw_img = Image.open(img_logo_path)
# #     #             logo_ctk = ctk.CTkImage(raw_img, size=(150, 100))
# #     #             ctk.CTkLabel(self.sidebar, image=logo_ctk, text="").pack(pady=20)
# #     #         except:
# #     #             ctk.CTkLabel(self.sidebar, text="iLogic SETTINGS", font=("Arial", 18, "bold"), text_color="white").pack(pady=20)
# #     #     else:
# #     #         ctk.CTkLabel(self.sidebar, text="iLogic SETTINGS", font=("Arial", 18, "bold"), text_color="white").pack(pady=20)

# #     #     nav_items = [
# #     #         ("📊 DASHBOARD", self.show_dashboard),
# #     #         ("🛒 VIEW PRODUCT", self.show_view_product),
# #     #         ("⚖︎ WEIGHT SETTING", self.show_weight_setting),
# #     #         ("📷 CAMERA SETTING", self.show_camera_settings),
# #     #         ("🧹 HISTORY", self.show_history),
# #     #         ("⛶ QR SETTING", self.show_qr_settings),
# #     #         ("🙎🏻‍♂️ ABOUT", self.show_about),
# #     #         ("⚙️ DATABASE SETTING", self.show_database_setting)
# #     #     ]
# #     #     for text, cmd in nav_items:
# #     #         ctk.CTkButton(self.sidebar, text=text, anchor="w", fg_color="transparent", 
# #     #                       hover_color=self.colors["NAVY"], command=cmd).pack(fill="x", padx=10, pady=2)
# #     #     ctk.CTkButton(self.sidebar, text="➜] EXIT", fg_color=self.colors["CORAL"], 
# #     #                   command=self.main_app.show_main_view).pack(side="bottom", fill="x", padx=10, pady=20)

# #     def clear_content(self):
# #         self.roi_active = False
# #         for widget in self.content_area.winfo_children():
# #             widget.destroy()

# #     def get_product_image_path(self, description, uom):
# #         if uom == "KG":
# #             path = os.path.join(BASE_DIR, "vf_images", f"{description}.webp")
# #             return path if os.path.exists(path) else None
# #         elif uom == "PCS":
# #             path = os.path.join(BASE_DIR, "pcs", f"{description}.jpeg")
# #             return path if os.path.exists(path) else None
# #         return None


# #     def show_database_setting(self):
# #         self.clear_content()

# #         ctk.CTkLabel(
# #             self.content_area,
# #             text="DATABASE SETTINGS",
# #             font=("Arial", 22, "bold"),
# #             text_color="white"
# #         ).pack(anchor="w", padx=20, pady=15)

# #         box = ctk.CTkFrame(self.content_area, fg_color=self.colors["OCEAN"], corner_radius=12)
# #         box.pack(fill="x", padx=20, pady=10)

# #         from app_config import CONFIG_PATH

# #         cfg_path = CONFIG_PATH
# #         if os.path.exists(cfg_path):
# #             with open(cfg_path, "r") as f:
# #                 cfg = json.load(f)
# #         else:
# #             cfg_path = os.path.join(BASE_DIR, "config", "db_config.json")

# #             if os.path.exists(cfg_path):
# #                 with open(cfg_path, "r") as f:
# #                     cfg = json.load(f)
# #             else:
# #                 cfg = {
# #                     "database": "",
# #                     "username": "",
# #                     "password": ""
# #                 }

# #         self.db_entries = {}

# #         fields = [
# #             ("Database Name", "database"),
# #             ("Username", "username"),
# #             ("Password", "password")
# #         ]

# #         for label, key in fields:
# #             row = ctk.CTkFrame(box, fg_color="transparent")
# #             row.pack(fill="x", padx=20, pady=8)

# #             ctk.CTkLabel(row, text=label, width=160, anchor="w", text_color="white").pack(side="left")
# #             ent = ctk.CTkEntry(row, width=300, show="*" if key == "password" else None)
# #             ent.insert(0, cfg.get(key, ""))
# #             ent.pack(side="left", padx=10)

# #             self.db_entries[key] = ent

# #         btns = ctk.CTkFrame(box, fg_color="transparent")
# #         btns.pack(pady=20)

# #         ctk.CTkButton(btns, text="TEST CONNECTION", fg_color="#457B9D",
# #                     command=self.test_db_connection).pack(side="left", padx=10)

# #         ctk.CTkButton(btns, text="SAVE SETTINGS", fg_color="#2ECC71",
# #                     command=self.save_db_settings).pack(side="left", padx=10)
        
# #         # --- CAMERA TRAINING RESET (DANGER ZONE) ---
# #         danger_box = ctk.CTkFrame(
# #             self.content_area,
# #             fg_color="#2B0F0F",
# #             corner_radius=12
# #         )
# #         danger_box.pack(fill="x", padx=20, pady=(30, 10))

# #         ctk.CTkLabel(
# #             danger_box,
# #             text="DANGER ZONE",
# #             font=("Arial", 14, "bold"),
# #             text_color="#FF6B6B"
# #         ).pack(pady=(10, 5))

# #         ctk.CTkLabel(
# #             danger_box,
# #             text="This will permanently delete all trained camera data",
# #             text_color="white"
# #         ).pack(pady=(0, 10))

# #         ctk.CTkButton(
# #             danger_box,
# #             text="🗑️ DELETE CAMERA TRAINING DATA",
# #             height=40,
# #             fg_color="#E63946",
# #             hover_color="#C53030",
# #             command=self.confirm_clear_camera_data
# #         ).pack(pady=(0, 15))

# #     def save_db_settings(self):
# #         cfg = {
# #             "driver": "ODBC Driver 17 for SQL Server",  # FIXED
# #             "server": FIXED_SQL_SERVER,  # FIXED
# #             "database": self.db_entries["database"].get().strip(),
# #             "user": self.db_entries["username"].get().strip(),
# #             "password": self.db_entries["password"].get(),
# #         }

# #         ok, msg = db_functions.test_connection(cfg)
# #         if not ok:
# #             messagebox.showerror("Connection Failed", msg)
# #             return

# #         DB_CONFIG.update(cfg)
# #         # os.makedirs(os.path.join(BASE_DIR, "config"), exist_ok=True)
# #         # with open(os.path.join(BASE_DIR, "config", "db_config.json"), "w") as f:
# #         #     json.dump({
# #         #         "database": cfg["database"],
# #         #         "username": cfg["user"],
# #         #         "password": cfg["password"],
# #         #     }, f, indent=4)
# #         from app_config import CONFIG_PATH

# #         with open(CONFIG_PATH, "w") as f:
# #             json.dump({
# #                 "database": cfg["database"],
# #                 "username": cfg["user"],
# #                 "password": cfg["password"],
# #             }, f, indent=4)

# #         messagebox.showinfo("Connected", "Database connected and saved")

# #         threading.Thread(
# #             target=self.main_app._load_products_thread,
# #             daemon=True
# #         ).start()

# #     def test_db_connection(self):
# #         cfg = {
# #             "driver": "ODBC Driver 17 for SQL Server",
# #             "server": FIXED_SQL_SERVER,
# #             "database": self.db_entries["database"].get().strip(),
# #             "user": self.db_entries["username"].get().strip(),
# #             "password": self.db_entries["password"].get(),
# #         }

# #         ok, msg = db_functions.test_connection(cfg)
# #         if ok:
# #             messagebox.showinfo("Success", "SQL Server connected successfully")
# #         else:
# #             messagebox.showerror("Failed", msg)

# #     # --- DASHBOARD LOGIC (LAYOUT: TOP=Table, BOTTOM=Btn, NO INSTRUCTIONS) ---
# #     def show_dashboard(self):
# #         self.clear_content()

# #         # Header
# #         ctk.CTkLabel(
# #             self.content_area,
# #             text="🧠 BRAIN DASHBOARD",
# #             font=("Segoe UI", 24, "bold"),
# #             text_color="white"
# #         ).pack(anchor="w", padx=20, pady=(15, 5))

# #         # Get trained items
# #         trained_items = []
# #         if hasattr(self.main_app, "camera") and hasattr(self.main_app.camera, "get_learned_items"):
# #             trained_items = self.main_app.camera.get_learned_items()

# #         ctk.CTkLabel(
# #             self.content_area,
# #             text=f"BRAIN LOADED: {len(trained_items)} ITEMS",
# #             font=("Arial", 16, "bold"),
# #             text_color="#FFD700"
# #         ).pack(anchor="w", padx=20, pady=(0, 10))

# #         # Search bar
# #         search_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
# #         search_frame.pack(fill="x", padx=20, pady=5)

# #         self.brain_search = ctk.CTkEntry(
# #             search_frame,
# #             placeholder_text="Search trained item..."
# #         )
# #         self.brain_search.pack(side="left", padx=5)

# #         ctk.CTkButton(
# #             search_frame,
# #             text="SEARCH",
# #             command=self.render_brain_boxes
# #         ).pack(side="left", padx=5)

# #         # Scrollable box area
# #         self.brain_box_area = ctk.CTkScrollableFrame(
# #             self.content_area,
# #             fg_color="transparent"
# #         )
# #         self.brain_box_area.pack(fill="both", expand=True, padx=20, pady=10)

# #         # Training button
# #         ctk.CTkButton(
# #             self.content_area,
# #             text="➕ TRAIN NEW ITEM",
# #             font=("Arial", 18, "bold"),
# #             fg_color="#FFD700",
# #             text_color="black",
# #             hover_color="#E5C100",
# #             height=60,
# #             command=self.open_training_popup
# #         ).pack(pady=20)

# #         self.render_brain_boxes()

# #     def render_brain_boxes(self):
# #         for w in self.brain_box_area.winfo_children():
# #             w.destroy()

# #         query = self.dashboard_search.get().upper() if hasattr(self, "dashboard_search") else ""

# #         items = []
# #         if hasattr(self.main_app.camera, "get_learned_items"):
# #             items = self.main_app.camera.get_learned_items()

# #         if query:
# #             items = [i for i in items if query in str(i.get("Code", "")).upper()]

# #         # Grid setup
# #         for i in range(4):
# #             self.brain_box_area.grid_columnconfigure(i, weight=1)

# #         for idx, item in enumerate(items):
# #             card = HoverableCard(
# #                 self.brain_box_area,
# #                 normal_color=self.colors["OCEAN"],
# #                 hover_color="#2A456E",
# #                 corner_radius=12
# #             )
# #             card.grid(row=idx // 4, column=idx % 4, padx=10, pady=10, sticky="nsew")

# #             code = item.get("Code", "N/A")
# #             uom = item.get("UOM", "-")

# #             ctk.CTkLabel(card, text="🧠", font=("Arial", 28)).pack(pady=(10, 0))
# #             ctk.CTkLabel(card, text=f"CODE: {code}", font=("Arial", 13, "bold"), text_color="#FFD700").pack()
# #             ctk.CTkLabel(card, text=f"UOM: {uom}", text_color="white").pack(pady=(0, 5))

# #             ctk.CTkButton(
# #                 card,
# #                 text="FORGET",
# #                 fg_color="#E63946",
# #                 hover_color="#C53030",
# #                 command=lambda c=code: self.main_app.camera.forget_item(c)
# #             ).pack(pady=(5, 10))

# #     def open_training_popup(self):
# #         """Pop up for Taking Picture or Inserting Picture"""
# #         t = ctk.CTkToplevel(self.parent)
# #         t.title("Select Action")
# #         t.geometry("400x300")
# #         t.attributes("-topmost", True)
        
# #         ctk.CTkLabel(t, text="CHOOSE ACTION", font=("Arial", 20, "bold")).pack(pady=20)
# #         # 1. Take Picture
# #         ctk.CTkButton(t, text="📸 TAKE PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#2ECC71",
# #                       command=lambda: [t.destroy(), self.open_camera_capture()]).pack(pady=10)
# #         # 2. Insert Picture
# #         ctk.CTkButton(t, text="📂 INSERT PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#457B9D",
# #                       command=lambda: [t.destroy(), self.upload_picture()]).pack(pady=10)
# #         ctk.CTkButton(t, text="CANCEL", width=280, fg_color=self.colors["CORAL"], command=t.destroy).pack(pady=20)

# #     # --- FUNCTION 1: CAPTURE FROM CAMERA ---
# #     def open_camera_capture(self):
# #         p = tk.Toplevel(self.parent)
# #         p.geometry("500x600"); p.title("Camera Capture"); p.configure(bg="black")
# #         lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
# #         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# #         def update_stream():
# #             if not p.winfo_exists():
# #                 cap.release(); return
# #             ret, frame = cap.read()
# #             if ret:
# #                 rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
# #                 img = ImageTk.PhotoImage(Image.fromarray(rgb))
# #                 lbl_video.configure(image=img); lbl_video.image = img
# #             p.after(20, update_stream)
# #         def snap_photo():
# #             ret, frame = cap.read()
# #             if ret:
# #                 cap.release(); p.destroy(); self.show_save_form(frame)
# #         ctk.CTkButton(p, text="SNAP", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
# #         update_stream()

# #     # --- FUNCTION 2: UPLOAD FROM FILE ---
# #     def upload_picture(self):
# #         file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp")])
# #         if file_path:
# #             img = cv2.imread(file_path)
# #             if img is not None: self.show_save_form(img)

# #     def show_save_form(self, image_data):
# #         self.clear_content()
# #         sc = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"]); sc.pack(fill="both", expand=True, padx=20, pady=10)
# #         rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]; ratio = 250 / h
# #         rgb = cv2.resize(rgb, (int(w*ratio), 250)); prev_img = ctk.CTkImage(Image.fromarray(rgb), size=(int(w*ratio), 250))
# #         ctk.CTkLabel(sc, image=prev_img, text="").pack(pady=10)
# #         existing_codes = [int(i['Code']) for i in self.main_app.all_products if str(i['Code']).isdigit()]
# #         next_code = str(max(existing_codes) + 1) if existing_codes else "1001"
# #         form_fields = [("InventoryCode", next_code), ("Description", ""), ("Barcode", ""), ("UOM", "KG"), ("RetailPrice", "0.00"), ("BrandCode", "001")]
# #         entries = {}
# #         for idx, (lbl, default_val) in enumerate(form_fields):
# #             ctk.CTkLabel(sc, text=lbl, text_color="white").pack(anchor="w", padx=20, pady=(5,0))
# #             e = ctk.CTkEntry(sc, width=400); e.insert(0, default_val); e.pack(padx=20, pady=(0,10)); entries[lbl] = e
# #         def commit_save():
# #             d = {
# #                 "InventoryCode": entries["InventoryCode"].get(), "Description": entries["Description"].get(), "Barcode": entries["Barcode"].get(), 
# #                 "UOM": entries["UOM"].get().upper(), "RetailPrice": float(entries["RetailPrice"].get() or 0), "BrandCode": entries["BrandCode"].get(), 
# #                 "CreateDate": datetime.now().strftime("%Y-%m-%d"), "InActive": 0
# #             }
# #             if db_functions.insert_inventory(d) == "SUCCESS":
# #                 fname = f"{d['Description']}.webp" if d["UOM"]=="KG" else f"{d['Description']}.jpeg"
# #                 save_dir = "vf_images" if d["UOM"]=="KG" else "pcs"
# #                 save_path = os.path.join(BASE_DIR, save_dir, fname)
# #                 cv2.imwrite(save_path, image_data)
                
# #                 # --- FIX: SAFE RELOAD WITHOUT CRASHING ---
# #                 # 1. Reload DB Products (Safe)
# #                 if hasattr(self.main_app, "_load_products_thread"):
# #                     threading.Thread(target=self.main_app._load_products_thread, daemon=True).start()
                
# #                 # 2. Attempt to Reload Camera (Safe Check)
# #                 if hasattr(self.main_app, "camera"):
# #                     # Check for common method names since 'refresh_db' is missing
# #                     if hasattr(self.main_app.camera, "load_data"):
# #                         threading.Thread(target=self.main_app.camera.load_data, daemon=True).start()
# #                     elif hasattr(self.main_app.camera, "load_features"):
# #                         threading.Thread(target=self.main_app.camera.load_features, daemon=True).start()
# #                     # If no method found, skip silently to prevent crash

# #                 time.sleep(0.5) 
# #                 self.show_dashboard() 

# #                 messagebox.showinfo("Success", "Product Saved & System Refreshed!")
# #             else: messagebox.showerror("Error", "DB Insert Failed")
# #         ctk.CTkButton(sc, text="SAVE PRODUCT", height=45, fg_color="#2ECC71", command=commit_save).pack(pady=20)
# #         ctk.CTkButton(sc, text="CANCEL", height=30, fg_color="gray", command=self.show_dashboard).pack(pady=5)

# #     # def update_scale_logic(self, _=None):
# #     #     try:
# #     #         new_port = self.opt_com.get()
# #     #         new_baud = int(self.opt_baud.get())
# #     #         new_protocol = self.opt_protocol.get()

# #     #         # ✅ Save to persistent settings ONLY
# #     #         self.app_settings.setdefault("weight", {}).update({
# #     #             "port": new_port,
# #     #             "baud": new_baud,
# #     #             "protocol": new_protocol
# #     #         })
# #     #         save_app_settings(self.app_settings)

# #     #         messagebox.showinfo(
# #     #             "Saved",
# #     #             "Scale settings saved successfully.\nRestart the application to apply changes."
# #     #         )

# #     #     except Exception as e:
# #     #         messagebox.showerror("Scale Error", str(e))


# #     def update_scale_logic(self, _=None):
# #         try:
# #             new_port = self.opt_com.get()
# #             new_baud = int(self.opt_baud.get())
# #             new_protocol = self.opt_protocol.get()  # stored only, not used here

# #             # 1️⃣ Save settings
# #             self.app_settings.setdefault("weight", {}).update({
# #                 "port": new_port,
# #                 "baud": new_baud,
# #                 "protocol": new_protocol
# #             })
# #             save_app_settings(self.app_settings)

# #             # 2️⃣ LIVE update scale (NO restart, NO new thread)
# #             if hasattr(self.main_app, "scale") and self.main_app.scale:
# #                 self.main_app.scale.update_config(
# #                     port=new_port,
# #                     baudrate=new_baud
# #                 )

# #         except Exception as e:
# #             messagebox.showerror("Scale Error", str(e))

# #     def show_weight_setting(self):
# #         self.clear_content()
# #         scroll = ctk.CTkScrollableFrame(
# #             self.content_area, fg_color="transparent"
# #         )
# #         scroll.pack(fill="both", expand=True, padx=20, pady=10)

# #         ctk.CTkLabel(
# #             scroll, text="DEVICE SETTING",
# #             font=("Arial", 22, "bold"),
# #             text_color="white"
# #         ).pack(anchor="w", pady=10)

# #         box1 = ctk.CTkFrame(
# #             scroll, fg_color=self.colors["OCEAN"], corner_radius=12
# #         )
# #         box1.pack(fill="x", pady=5)

# #         # ================= SCALE SETTINGS =================

# #         # 🔹 Load persisted weight settings
# #         wt = self.app_settings.get("weight", {})

# #         saved_port = wt.get("port", "COM1")
# #         saved_baud = str(wt.get("baud", "9600"))
# #         saved_protocol = wt.get("protocol", "RS232")

# #         # ---------- Protocol ----------
# #         f1 = ctk.CTkFrame(box1, fg_color="transparent")
# #         f1.pack(pady=10, padx=15, fill="x")

# #         ctk.CTkLabel(
# #             f1, text="Scale Setting:",
# #             width=140, anchor="w",
# #             text_color="white"
# #         ).pack(side="left")

# #         self.opt_protocol = ctk.CTkOptionMenu(
# #             f1, values=["RS232", "RS249"],
# #             command=self.update_scale_logic
# #         )
# #         self.opt_protocol.set(saved_protocol)
# #         self.opt_protocol.pack(side="left", padx=20)

# #         # ---------- COM Port ----------
# #         f2 = ctk.CTkFrame(box1, fg_color="transparent")
# #         f2.pack(pady=10, padx=15, fill="x")

# #         ctk.CTkLabel(
# #             f2, text="Serial Port Setting:",
# #             width=140, anchor="w",
# #             text_color="white"
# #         ).pack(side="left")

# #         self.opt_com = ctk.CTkOptionMenu(
# #             f2,
# #             values=[f"COM{i}" for i in range(1, 11)],
# #             command=self.update_scale_logic
# #         )
# #         self.opt_com.set(saved_port)
# #         self.opt_com.pack(side="left", padx=20)

# #         # ---------- Baud Rate ----------
# #         f3 = ctk.CTkFrame(box1, fg_color="transparent")
# #         f3.pack(pady=10, padx=15, fill="x")

# #         ctk.CTkLabel(
# #             f3, text="Baud Rate Setting:",
# #             width=140, anchor="w",
# #             text_color="white"
# #         ).pack(side="left")

# #         self.opt_baud = ctk.CTkOptionMenu(
# #             f3,
# #             values=["1200","2400","4800","9600","19200","38400","115200"],
# #             command=self.update_scale_logic
# #         )
# #         self.opt_baud.set(saved_baud)
# #         self.opt_baud.pack(side="left", padx=20)

# #         # ================= UNIT SETTINGS =================

# #         ctk.CTkLabel(
# #             scroll, text="UNIT SETTING",
# #             font=("Arial", 22, "bold"),
# #             text_color="white"
# #         ).pack(anchor="w", pady=(25, 10))

# #         box2 = ctk.CTkFrame(
# #             scroll, fg_color=self.colors["OCEAN"], corner_radius=12
# #         )
# #         box2.pack(fill="x", pady=5)

# #         f_u = ctk.CTkFrame(box2, fg_color="transparent")
# #         f_u.pack(pady=20, padx=15, fill="x")

# #         ctk.CTkLabel(
# #             f_u, text="Print Unit Setting (Ratio):",
# #             width=180, anchor="w",
# #             text_color="white"
# #         ).pack(side="left")

# #         ctk.CTkOptionMenu(
# #             f_u, values=["KG", "Pound", "Viss", "Gram", "15kg", "30kg"]
# #         ).pack(side="left", padx=20)

# #     def show_view_product(self):
# #         self.clear_content()
# #         self.current_uom_filter = "ALL ITEM"; self.search_query = ""; self.current_page = 0
# #         ctk.CTkLabel(self.content_area, text="PRODUCT INVENTORY", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
# #         f_bar = ctk.CTkFrame(self.content_area, fg_color="transparent"); f_bar.pack(fill="x", padx=15, pady=5)
# #         self.uom_selector = ctk.CTkSegmentedButton(f_bar, values=["ALL ITEM", "KG", "PCS"], command=self.filter_by_uom)
# #         self.uom_selector.set(self.current_uom_filter); self.uom_selector.pack(side="left")
# #         self.search_entry = ctk.CTkEntry(f_bar, placeholder_text="Code or Name...", width=140); self.search_entry.pack(side="left", padx=15)
# #         ctk.CTkButton(f_bar, text="SEARCH", width=70, command=self.apply_search).pack(side="left")
# #         self.grid_container = ctk.CTkFrame(self.content_area, fg_color="transparent"); self.grid_container.pack(fill="both", expand=True, padx=15)
# #         pg = ctk.CTkFrame(self.content_area, fg_color="transparent", height=40); pg.pack(fill="x", side="bottom", pady=10)
# #         ctk.CTkButton(pg, text="<< PREV", width=100, command=self.prev_page, fg_color=self.colors["OCEAN"]).pack(side="left", padx=40)
# #         self.lbl_page = ctk.CTkLabel(pg, text="PAGE 1", font=("Arial", 12, "bold"), text_color="white"); self.lbl_page.pack(side="left", expand=True)
# #         ctk.CTkButton(pg, text="NEXT >>", width=100, command=self.next_page, fg_color=self.colors["OCEAN"]).pack(side="right", padx=40)
# #         self.render_grid()

# #     def apply_search(self): 
# #         self.search_query = self.search_entry.get().upper()
# #         self.current_page = 0
# #         self.render_grid()

# #     def filter_by_uom(self, v): self.current_uom_filter = v; self.current_page = 0; self.render_grid()
    
# #     def next_page(self):
# #         items = [i for i in self.main_app.all_products if (self.current_uom_filter == "ALL ITEM" or i['UOM'] == self.current_uom_filter)]
# #         if self.search_query: 
# #             items = [i for i in items if self.search_query in str(i['Code']).upper() or self.search_query in str(i['Name']).upper()]
# #         if self.current_page < max(1, (len(items)+9)//10) - 1: self.current_page += 1; self.render_grid()
    
# #     def prev_page(self):
# #         if self.current_page > 0: self.current_page -= 1; self.render_grid()
    
# #     def render_grid(self):
# #         for w in self.grid_container.winfo_children(): w.destroy()
# #         # Responsive grid setup
# #         for i in range(5): self.grid_container.grid_columnconfigure(i, weight=1)
        
# #         items = [i for i in self.main_app.all_products if (self.current_uom_filter == "ALL ITEM" or i['UOM'] == self.current_uom_filter)]
        
# #         # --- MODIFIED SEARCH LOGIC: CODE OR DESCRIPTION ---
# #         if self.search_query: 
# #             items = [i for i in items if self.search_query in str(i['Code']).upper() or self.search_query in str(i['Name']).upper()]
            
# #         start = self.current_page * 10
# #         self.lbl_page.configure(text=f"PAGE {self.current_page + 1} OF {max(1, (len(items)+9)//10)}")
        
# #         for i, item in enumerate(items[start:start+10]):
# #             card = HoverableCard(self.grid_container, normal_color=self.colors["OCEAN"], hover_color="#2A456E", corner_radius=10)
# #             card.grid(row=i//5, column=i%5, padx=8, pady=8, sticky="nsew") # Responsive sticky
# #             path = self.get_product_image_path(item['Name'], item['UOM'])
# #             if path:
# #                 try: 
# #                     img = ctk.CTkImage(Image.open(path), size=(100, 80)); 
# #                     lbl=ctk.CTkLabel(card, image=img, text=""); lbl.image=img; lbl.pack(pady=(10,5))
# #                 except: ctk.CTkLabel(card, text="IMG ERR", text_color="red").pack(pady=20)
# #             else: ctk.CTkLabel(card, text="🖼️", font=("Arial",12)).pack(pady=15)
# #             ctk.CTkLabel(card, text=item['Code'], font=("Arial",12,"bold"), text_color="#FFD700").pack()
# #             ctk.CTkLabel(card, text=(item['Name'][:13]+".." if len(item['Name'])>15 else item['Name']), font=("Arial",11), text_color="white").pack()
            
# #             # --- MODIFIED: EDIT BUTTON INSTEAD OF SELECT ---
# #             ctk.CTkButton(
# #                 card,
# #                 text="EDIT IMAGE",
# #                 fg_color="#F39C12", # Orange for edit
# #                 hover_color="#D68910",
# #                 height=35, # Bigger
# #                 width=140, # Bigger
# #                 font=("Arial", 12, "bold"),
# #                 command=lambda i=item: self.open_edit_image_popup(i)
# #             ).pack(pady=(10, 10))

# #     def open_edit_image_popup(self, item):
# #         """ Pop up to Edit Image (Take New or Upload New) """
# #         t = ctk.CTkToplevel(self.parent)
# #         t.title("Edit Product Image")
# #         t.geometry("400x320")
# #         t.attributes("-topmost", True)
        
# #         ctk.CTkLabel(t, text=f"EDIT IMAGE: {item['Name']}", font=("Arial", 16, "bold")).pack(pady=15)
        
# #         # 1. Take Picture
# #         ctk.CTkButton(t, text="📸 TAKE NEW PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#2ECC71",
# #                       command=lambda: [t.destroy(), self.edit_camera_capture(item)]).pack(pady=10)
# #         # 2. Insert Picture
# #         ctk.CTkButton(t, text="📂 UPLOAD NEW PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#457B9D",
# #                       command=lambda: [t.destroy(), self.edit_upload_picture(item)]).pack(pady=10)
        
# #         ctk.CTkButton(t, text="CANCEL", width=280, fg_color=self.colors["CORAL"], command=t.destroy).pack(pady=20)

# #     def edit_camera_capture(self, item):
# #         p = tk.Toplevel(self.parent)
# #         p.geometry("500x600"); p.title(f"Snap: {item['Name']}"); p.configure(bg="black")
# #         lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
# #         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# #         def update_stream():
# #             if not p.winfo_exists(): cap.release(); return
# #             ret, frame = cap.read()
# #             if ret:
# #                 rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
# #                 img = ImageTk.PhotoImage(Image.fromarray(rgb))
# #                 lbl_video.configure(image=img); lbl_video.image = img
# #             p.after(20, update_stream)
# #         def snap_photo():
# #             ret, frame = cap.read()
# #             if ret:
# #                 cap.release(); p.destroy(); self.save_edited_image(item, frame)
# #         ctk.CTkButton(p, text="SNAP & SAVE", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
# #         update_stream()

# #     def edit_upload_picture(self, item):
# #         file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp")])
# #         if file_path:
# #             img = cv2.imread(file_path)
# #             if img is not None: self.save_edited_image(item, img)

# #     def save_edited_image(self, item, image_data):
# #         # Determine path based on item details
# #         uom = item.get('UOM', 'KG')
# #         name = item.get('Name', 'Unknown')
        
# #         folder = "vf_images" if uom == "KG" else "pcs"
# #         ext = ".webp" if uom == "KG" else ".jpeg"
        
# #         # Ensure directory exists
# #         save_dir = os.path.join(BASE_DIR, folder)
# #         if not os.path.exists(save_dir): os.makedirs(save_dir)
        
# #         save_path = os.path.join(save_dir, f"{name}{ext}")
        
# #         try:
# #             cv2.imwrite(save_path, image_data)
            
# #             # --- FIX: SAFE RELOAD WITHOUT CRASHING ---
# #             # 1. Reload DB Products
# #             if hasattr(self.main_app, "_load_products_thread"):
# #                 threading.Thread(target=self.main_app._load_products_thread, daemon=True).start()
            
# #             # 2. Attempt to Reload Camera (Safe Check)
# #             if hasattr(self.main_app, "camera"):
# #                  # Check for common method names since 'refresh_db' is missing
# #                  if hasattr(self.main_app.camera, "load_data"):
# #                      threading.Thread(target=self.main_app.camera.load_data, daemon=True).start()
# #                  elif hasattr(self.main_app.camera, "load_features"):
# #                      threading.Thread(target=self.main_app.camera.load_features, daemon=True).start()

# #             time.sleep(0.3)
# #             self.render_grid() # Refresh grid in View Product
            
# #             messagebox.showinfo("Success", "Product image updated successfully!")
# #         except Exception as e:
# #             messagebox.showerror("Error", f"Failed to save image: {e}")

# #     # --- SHOW CAMERA SETTINGS (With ROI) ---

# #     def show_camera_settings(self):
# #         self.clear_content()
# #         scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
# #         scroll.pack(fill="both", expand=True, padx=15)

# #         ctk.CTkLabel(scroll, text="VISION BOUNDARY CONFIGURATION", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
# #         ctk.CTkLabel(scroll, text="DRAG CIRCLES TO ADJUST", font=("Arial", 12), text_color="yellow").pack()

# #         self.roi_canvas = tk.Canvas(scroll, width=self.canvas_w, height=self.canvas_h, bg="black", highlightthickness=0)
# #         self.roi_canvas.pack(pady=10)

# #         # --- Full camera ROI (4 corner handles) ---
# #         self.tl = [0, 0]
# #         self.tr = [self.canvas_w, 0]
# #         self.bl = [0, self.canvas_h]
# #         self.br = [self.canvas_w, self.canvas_h]

# #         # 🔹 Load ROI from persistent settings
# #         cam_cfg = self.app_settings.get("camera", {})
# #         cx, cy, cw, ch = cam_cfg.get("roi", [0, 0, 640, 480])

# #         # Apply to camera object
# #         try:
# #             self.main_app.camera.roi = (int(cx), int(cy), int(cw), int(ch))
# #         except Exception:
# #             pass

# #         # Scale ROI to canvas coords
# #         sx, sy = self.canvas_w / 640.0, self.canvas_h / 480.0
# #         self.pt1, self.pt2 = [cx * sx, cy * sy], [(cx + cw) * sx, (cy + ch) * sy]

# #         # Update corner handles
# #         self.tl = [self.pt1[0], self.pt1[1]]
# #         self.tr = [self.pt2[0], self.pt1[1]]
# #         self.bl = [self.pt1[0], self.pt2[1]]
# #         self.br = [self.pt2[0], self.pt2[1]]

# #         # Bind drag events
# #         self.roi_canvas.bind("<Button-1>", self.on_roi_press)
# #         self.roi_canvas.bind("<B1-Motion>", self.on_roi_drag)

# #         # Save button
# #         ctk.CTkButton(scroll, text="SAVE VISION BOUNDARY", fg_color="#2ECC71", height=100, command=self.save_roi).pack(pady=10)

# #         self.roi_active = True
# #         self.update_roi_preview()
    
# #     # def show_camera_settings(self):
# #     #     self.clear_content()
# #     #     scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
# #     #     scroll.pack(fill="both", expand=True, padx=15)

# #     #     ctk.CTkLabel(scroll, text="VISION BOUNDARY CONFIGURATION", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
# #     #     ctk.CTkLabel(scroll, text="DRAG CIRCLES TO ADJUST", font=("Arial", 12), text_color="yellow").pack()

# #     #     self.roi_canvas = tk.Canvas(scroll, width=self.canvas_w, height=self.canvas_h, bg="black", highlightthickness=0)
# #     #     self.roi_canvas.pack(pady=10)

# #     #     # FULL camera ROI (4 corner handles)
# #     #     self.tl = [0, 0]
# #     #     self.tr = [self.canvas_w, 0]
# #     #     self.bl = [0, self.canvas_h]
# #     #     self.br = [self.canvas_w, self.canvas_h]

# #     #     roi_cfg = os.path.join(BASE_DIR, "camera_roi_config.txt")
# #     #     if os.path.exists(roi_cfg):
# #     #         try:
# #     #             with open(roi_cfg,"r") as f:
# #     #                 vals=tuple(map(int,f.read().strip().split(",")))
# #     #                 if len(vals)==4:
# #     #                     self.main_app.camera.roi = vals
# #     #         except:
# #     #             pass

# #     #     cx, cy, cw, ch = self.main_app.camera.roi
# #     #     sx, sy = self.canvas_w/640, self.canvas_h/480
# #     #     self.pt1, self.pt2 = [cx*sx, cy*sy], [(cx+cw)*sx, (cy+ch)*sy]

# #     #     # 🔥 IMPORTANT: Update corner handles from pt1/pt2
# #     #     self.tl = [self.pt1[0], self.pt1[1]]
# #     #     self.tr = [self.pt2[0], self.pt1[1]]
# #     #     self.bl = [self.pt1[0], self.pt2[1]]
# #     #     self.br = [self.pt2[0], self.pt2[1]]

# #     #     self.roi_canvas.bind("<Button-1>", self.on_roi_press)
# #     #     self.roi_canvas.bind("<B1-Motion>", self.on_roi_drag)

# #     #     ctk.CTkButton(scroll, text="SAVE VISION BOUNDARY", fg_color="#2ECC71",text_color="black",height=40, command=self.save_roi).pack(pady=10)

# #     #     self.roi_active=True
# #     #     self.update_roi_preview()



# #     def on_roi_press(self, e):
# #         r = 12  # hit radius

# #         def hit(p):
# #             return abs(e.x - p[0]) <= r and abs(e.y - p[1]) <= r

# #         if hit(self.tl):
# #             self.active_handle = "tl"
# #         elif hit(self.tr):
# #             self.active_handle = "tr"
# #         elif hit(self.bl):
# #             self.active_handle = "bl"
# #         elif hit(self.br):
# #             self.active_handle = "br"
# #         else:
# #             self.active_handle = None

        
# #     # def on_roi_drag(self, e):
# #     #     if self.active_handle=="pt1": self.pt1 = [max(0,min(e.x, self.pt2[0]-10)), max(0,min(e.y, self.pt2[1]-10))]
# #     #     elif self.active_handle=="pt2": self.pt2 = [max(self.pt1[0]+10,min(e.x, self.canvas_w)), max(self.pt1[1]+10,min(e.y, self.canvas_h))]
    
# #     def on_roi_drag(self, e):
# #         x = max(0, min(e.x, self.canvas_w))
# #         y = max(0, min(e.y, self.canvas_h))

# #         if self.active_handle == "tl":
# #             # Prevent crossing BR
# #             x = min(x, self.br[0] - 1)
# #             y = min(y, self.br[1] - 1)

# #             self.tl = [x, y]
# #             self.tr[1] = y
# #             self.bl[0] = x

# #         elif self.active_handle == "tr":
# #             # Prevent crossing BL
# #             x = max(x, self.tl[0] + 1)
# #             y = min(y, self.br[1] - 1)

# #             self.tr = [x, y]
# #             self.tl[1] = y
# #             self.br[0] = x

# #         elif self.active_handle == "bl":
# #             # Prevent crossing TR
# #             x = min(x, self.br[0] - 1)
# #             y = max(y, self.tl[1] + 1)

# #             self.bl = [x, y]
# #             self.tl[0] = x
# #             self.br[1] = y

# #         elif self.active_handle == "br":
# #             # Prevent crossing TL
# #             x = max(x, self.tl[0] + 1)
# #             y = max(y, self.tl[1] + 1)

# #             self.br = [x, y]
# #             self.tr[0] = x
# #             self.bl[1] = y

    
# #     def update_roi_preview(self):
# #         if not self.roi_active or not self.roi_canvas.winfo_exists():
# #             return

# #         fr = self.main_app.camera.get_frame(draw_box=False)

# #         if fr is not None:
# #             # Crop center area (same as your existing logic)
# #             fr = fr[
# #                 int(fr.shape[0] * 0.2):int(fr.shape[0] * 0.8),
# #                 int(fr.shape[1] * 0.2):int(fr.shape[1] * 0.8)
# #             ]

# #             try:
# #                 prev = cv2.resize(fr, (self.canvas_w, self.canvas_h))
# #                 img_tk = ImageTk.PhotoImage(
# #                     Image.fromarray(cv2.cvtColor(prev, cv2.COLOR_BGR2RGB))
# #                 )

# #                 self.roi_canvas.delete("all")
# #                 self.roi_canvas.create_image(0, 0, anchor="nw", image=img_tk)
# #                 self.roi_canvas.image = img_tk
                
# #                 # Ensure BR is inside canvas (clickable)
# #                 self.br[0] = min(self.br[0], self.canvas_w - 1)
# #                 self.br[1] = min(self.br[1], self.canvas_h - 1)

# #                 # Draw green ROI rectangle
# #                 self.roi_canvas.create_rectangle(
# #                     self.tl[0], self.tl[1],
# #                     self.br[0], self.br[1],
# #                     outline="#00FF00",
# #                     width=2
# #                 )

# #                 # Draw 4 red corner handles
# #                 for p in (self.tl, self.tr, self.bl, self.br):
# #                     self.roi_canvas.create_oval(
# #                         p[0] - 8, p[1] - 8,
# #                         p[0] + 8, p[1] + 8,
# #                         fill="red",
# #                         outline="white"
# #                     )

# #             except Exception as e:
# #                 print("ROI preview error:", e)

# #         if self.roi_active:
# #             self.parent.after(40, self.update_roi_preview)

# #     # def save_roi(self):
# #     #     if not self.roi_active:
# #     #         return

# #     #     # Convert canvas coords back to camera coords
# #     #     sx, sy = self.canvas_w / 640.0, self.canvas_h / 480.0
# #     #     cx = int(max(0, min(640, round(self.pt1[0] / sx))))
# #     #     cy = int(max(0, min(480, round(self.pt1[1] / sy))))
# #     #     cw = int(max(1, min(640, round((self.pt2[0] - self.pt1[0]) / sx))))
# #     #     ch = int(max(1, min(480, round((self.pt2[1] - self.pt1[1]) / sy))))

# #     #     # Update camera object
# #     #     try:
# #     #         self.main_app.camera.roi = (cx, cy, cw, ch)
# #     #     except Exception:
# #     #         pass

# #     #     # Save to app_settings.json
# #     #     self.app_settings.setdefault("camera", {})["roi"] = [cx, cy, cw, ch]
# #     #     save_app_settings(self.app_settings)

# #     #     # Show confirmation
# #     #     msg = ctk.CTkLabel(self.content_area, text="✅ Vision boundary saved!", text_color="#2ECC71", font=("Arial", 14, "bold"))
# #     #     msg.pack(pady=8)
# #     #     self.parent.after(2000, lambda: msg.destroy())


# #     def save_roi(self):
# #         # Use tl and br (NOT pt1/pt2)
# #         sx, sy = 640/self.canvas_w, 480/self.canvas_h

# #         nx = int(self.tl[0] * sx)
# #         ny = int(self.tl[1] * sy)
# #         nw = int((self.tr[0] - self.tl[0]) * sx)
# #         nh = int((self.bl[1] - self.tl[1]) * sy)

# #         try:
# #             # with open(os.path.join(BASE_DIR, "camera_roi_config.txt"), "w") as f:
# #             #     f.write(f"{nx},{ny},{nw},{nh}")
# #             roi_path = os.path.join(CONFIG_DIR, "camera_roi_config.txt")
# #             with open(roi_path, "w") as f:
# #                 f.write(f"{nx},{ny},{nw},{nh}")
# #         except:
# #             pass

# #         self.main_app.camera.roi = (nx, ny, nw, nh)
# #         messagebox.showinfo("Saved", "Boundary Saved.")



# #     def confirm_clear_camera_data(self):
# #         popup = ctk.CTkToplevel(self.parent)
# #         popup.title("ADMIN VERIFICATION")
# #         popup.geometry("340x230")
# #         popup.grab_set()
# #         popup.attributes("-topmost", True)

# #         ctk.CTkLabel(
# #             popup,
# #             text="ADMIN PASSWORD REQUIRED",
# #             font=("Arial", 15, "bold"),
# #             text_color="red"
# #         ).pack(pady=20)

# #         pwd_entry = ctk.CTkEntry(
# #             popup,
# #             width=220,
# #             show="*"
# #         )
# #         pwd_entry.pack(pady=10)

# #         def verify_and_delete():
# #             password = pwd_entry.get().strip()

# #             if not password:
# #                 messagebox.showwarning("Missing", "Please enter password")
# #                 return

# #             if not db_functions.validate_admin_password(password):
# #                 messagebox.showerror(
# #                     "ACCESS DENIED",
# #                     "Invalid ADMIN password"
# #                 )
# #                 return

# #             popup.destroy()

# #             if hasattr(self.main_app, "camera") and self.main_app.camera:
# #                 ok = self.main_app.camera.clear_learned_data()
# #                 if ok:
# #                     messagebox.showinfo(
# #                         "SUCCESS",
# #                         "Camera training JSON data deleted successfully"
# #                     )
# #                 else:
# #                     messagebox.showerror(
# #                         "ERROR",
# #                         "Failed to delete training data"
# #                     )
# #             else:
# #                 messagebox.showerror(
# #                     "ERROR",
# #                     "Camera module not initialized"
# #                 )

# #         ctk.CTkButton(
# #             popup,
# #             text="CONFIRM DELETE",
# #             fg_color="#E63946",
# #             height=40,
# #             command=verify_and_delete
# #         ).pack(pady=20)

# #         ctk.CTkButton(
# #             popup,
# #             text="CANCEL",
# #             fg_color="gray",
# #             command=popup.destroy
# #         ).pack()

# #     def clear_learned_data(self):
# #         try:
# #             if not os.path.exists(self.training_data_dir):
# #                 return True

# #             for f in os.listdir(self.training_data_dir):
# #                 if f.endswith(".json"):
# #                     os.remove(os.path.join(self.training_data_dir, f))

# #             return True
# #         except Exception as e:
# #             print("Delete error:", e)
# #             return False

# #     # --- SHOW HISTORY (Split 2 Grids) ---
# #     def show_history(self):
# #         self.clear_content()

# #         # ================================
# #         # GRID 1: MAIN WINDOW ACTIVE ITEM
# #         # ================================
        
# #         ctk.CTkLabel(self.content_area, text="CURRENT SELECTION (FROM MAIN WINDOW)", font=("Arial", 18, "bold"), text_color="#FFD700").pack(anchor="w", padx=20, pady=(15, 5))
        
# #         # Grid 1 container (Scrollable, smaller height)
# #         self.selection_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"], height=120)
# #         self.selection_scroll.pack(fill="x", padx=20, pady=5)
        
# #         # Headers for Top Grid
# #         top_headers = ["BARCODE / QR", "DATE", "TIME", "DESCRIPTION", "UOM"]
# #         for col, h in enumerate(top_headers):
# #             ctk.CTkLabel(self.selection_scroll, text=h, font=("Arial", 12, "bold"), text_color="#FFD700").grid(row=0, column=col, padx=15, pady=8, sticky="w")
        
# #         sep = ctk.CTkFrame(self.selection_scroll, height=2, fg_color="white")
# #         sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 5))

# #         # Check Active Selection from Main App
# #         active_item = self.main_app.active_selection
# #         if active_item:
# #             # Grab details
# #             # Barcode: stored in main app label (generated string)
# #             barcode = "N/A"
# #             if hasattr(self.main_app, 'lbl_qr_string'):
# #                 barcode = self.main_app.lbl_qr_string.cget("text")
            
# #             description = active_item.get("Name", "Unknown")
# #             uom = active_item.get("UOM", "-")
            
# #             now = datetime.now()
# #             date_str = now.strftime("%Y-%m-%d")
# #             time_str = now.strftime("%H:%M:%S")

# #             row_data = [barcode, date_str, time_str, description, uom]
# #             for c, v in enumerate(row_data):
# #                 ctk.CTkLabel(self.selection_scroll, text=str(v), text_color="white", font=("Arial", 11)).grid(row=2, column=c, padx=15, pady=4, sticky="w")
# #         else:
# #              ctk.CTkLabel(self.selection_scroll, text="No item currently selected in main window.", text_color="silver").grid(row=2, column=0, columnspan=5, pady=20)


# #         # ================================
# #         # GRID 2: TRAINING DATA HISTORY
# #         # ================================

# #         # Header + Filter Frame for History
# #         top_bar = ctk.CTkFrame(self.content_area, fg_color="transparent")
# #         top_bar.pack(fill="x", padx=20, pady=(20, 10))
        
# #         ctk.CTkLabel(top_bar, text="TRAINING HISTORY", font=("Arial", 20, "bold"), text_color="white").pack(side="left")
        
# #         # Filter Logic
# #         filter_box = ctk.CTkOptionMenu(top_bar, values=["LiveNow", "Yesterday", "Last Week"], variable=self.history_filter_val, 
# #                                        command=lambda v: self.render_history_table(), width=130)
# #         filter_box.pack(side="right")
# #         ctk.CTkLabel(top_bar, text="Filter By:", text_color="silver").pack(side="right", padx=10)
        
# #         # Table Container (Scrollable)
# #         self.history_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"])
# #         self.history_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
# #         self.render_history_table()

# #     def render_history_table(self):
# #         # Clear current
# #         for widget in self.history_scroll.winfo_children():
# #             widget.destroy()
            
# #         # Headers
# #         headers = ["DATE", "TIME", "CODE", "UOM", "QTY / WEIGHT"]
# #         for col, h in enumerate(headers):
# #             ctk.CTkLabel(self.history_scroll, text=h, font=("Arial", 12, "bold"), text_color="#FFD700").grid(row=0, column=col, padx=15, pady=8, sticky="w")
        
# #         # Add a Separator
# #         sep = ctk.CTkFrame(self.history_scroll, height=2, fg_color="white")
# #         sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 5))

# #         # Get Raw Data from Main Logger (permanent storage)
# #         raw_history = history_logger.get_history() # Expected list of dicts: date, time, code, uom, qty
        
# #         # Apply Date Filter
# #         filtered_data = []
# #         filter_mode = self.history_filter_val.get()
# #         now = datetime.now()
# #         today_str = now.strftime("%Y-%m-%d")
# #         yest_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
# #         week_cutoff = (now - timedelta(days=7))

# #         for item in raw_history:
# #             # Assume item['date'] is YYYY-MM-DD
# #             d_str = item.get('date', "")
            
# #             include = False
# #             if filter_mode == "LiveNow":
# #                 if d_str == today_str: include = True
# #             elif filter_mode == "Yesterday":
# #                 if d_str == yest_str: include = True
# #             elif filter_mode == "Last Week":
# #                 try:
# #                     d_obj = datetime.strptime(d_str, "%Y-%m-%d")
# #                     if d_obj >= week_cutoff: include = True
# #                 except: pass
            
# #             if include:
# #                 filtered_data.append(item)
        
# #         # Sort desc (latest first) if not already
# #         # Render Rows
# #         if not filtered_data:
# #             ctk.CTkLabel(self.history_scroll, text="No records found for selected period.", text_color="silver").grid(row=2, column=0, columnspan=5, pady=20)
# #         else:
# #             for r, row_data in enumerate(filtered_data, 2):
# #                 vals = [row_data.get('date'), row_data.get('time'), row_data.get('code'), row_data.get('uom'), row_data.get('qty')]
# #                 bg = "#1F2B3E" if r % 2 == 0 else "transparent" # Striped rows optional, simple transparent here
                
# #                 for c, v in enumerate(vals):
# #                     ctk.CTkLabel(self.history_scroll, text=str(v), text_color="white", font=("Arial", 11)).grid(row=r, column=c, padx=15, pady=4, sticky="w")

# #     # --- SHOW QR SETTINGS (With Live Preview) ---
# #     def update_qr_preview_logic(self, _=None):
# #         self.app_settings.setdefault("qr", {}).update({
# #             "prefix_enabled": self.qr_prefix_on.get() == "ON",
# #             "prefix_value": self.opt_prefix_val.get(),
# #             "code_len": int(self.opt_code_digit.get()),
# #             "price_len": int(self.opt_price_digit.get()),
# #             "qty_len": int(self.opt_qty_digit.get())
# #         })
# #         save_app_settings(self.app_settings)
# #         prefix = self.opt_prefix_val.get() if self.qr_prefix_on.get() == "ON" else ""
# #         icode = "03451".zfill(int(self.opt_code_digit.get()))[:int(self.opt_code_digit.get())]
# #         iprice = "00024".zfill(int(self.opt_price_digit.get()))[:int(self.opt_price_digit.get())]
# #         iqty = "000797".zfill(int(self.opt_qty_digit.get()))[:int(self.opt_qty_digit.get())]
# #         self.lbl_qr_preview.configure(text=f"{prefix}{icode}{iprice}{iqty}")

# #     def show_qr_settings(self):
# #         self.clear_content(); scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent"); scroll.pack(fill="both", expand=True, padx=20, pady=10)
# #         ctk.CTkLabel(scroll, text="QR & BARCODE FORMAT CONFIG", font=("Arial", 22, "bold"), text_color="white").pack(anchor="w", pady=10)
# #         form = ctk.CTkFrame(scroll, fg_color=self.colors["OCEAN"], corner_radius=12); form.pack(fill="x", pady=10)
        
# #         r1 = ctk.CTkFrame(form, fg_color="transparent"); r1.pack(fill="x", padx=15, pady=8)
# #         ctk.CTkLabel(r1, text="Prefix Default (e.g. 20):", width=160, anchor="w", text_color="white").pack(side="left")
# #         ctk.CTkSwitch(r1, text="", variable=self.qr_prefix_on, onvalue="ON", offvalue="OFF", command=self.update_qr_preview_logic).pack(side="left", padx=5)
# #         self.opt_prefix_val = ctk.CTkOptionMenu(r1, values=[str(i) for i in range(20,91)], command=self.update_qr_preview_logic); self.opt_prefix_val.set("20"); self.opt_prefix_val.pack(side="left", padx=20)
        
# #         r2 = ctk.CTkFrame(form, fg_color="transparent"); r2.pack(fill="x", padx=15, pady=8)
# #         ctk.CTkLabel(r2, text="Inventory Code Length:", width=160, anchor="w", text_color="white").pack(side="left")
# #         self.opt_code_digit = ctk.CTkOptionMenu(r2, values=["4","5","6"], command=self.update_qr_preview_logic); self.opt_code_digit.set("5"); self.opt_code_digit.pack(side="left", padx=20)
        
# #         r3 = ctk.CTkFrame(form, fg_color="transparent"); r3.pack(fill="x", padx=15, pady=8)
# #         ctk.CTkLabel(r3, text="Currency / Price Digits:", width=160, anchor="w", text_color="white").pack(side="left")
# #         ctk.CTkOptionMenu(r3, values=["USD","IND","EUR","SGD","MYR"]).pack(side="left", padx=5)
# #         self.opt_price_digit = ctk.CTkOptionMenu(r3, values=["4","5","6"], width=80, command=self.update_qr_preview_logic); self.opt_price_digit.set("5"); self.opt_price_digit.pack(side="left", padx=10)
        
# #         r4 = ctk.CTkFrame(form, fg_color="transparent"); r4.pack(fill="x", padx=15, pady=8)
# #         ctk.CTkLabel(r4, text="Weight/Qty Length:", width=160, anchor="w", text_color="white").pack(side="left")
# #         self.opt_qty_digit = ctk.CTkOptionMenu(r4, values=["4","5","6"], command=self.update_qr_preview_logic); self.opt_qty_digit.set("5"); self.opt_qty_digit.pack(side="left", padx=20)
        
# #         preview = ctk.CTkFrame(scroll, fg_color="#000", border_width=2, border_color=self.colors["GOLD"]); preview.pack(fill="x", pady=20)
# #         ctk.CTkLabel(preview, text="GENERATION PREVIEW", font=("Arial", 10, "bold"), text_color=self.colors["GOLD"]).pack(pady=5)
# #         self.lbl_qr_preview = ctk.CTkLabel(preview, text="200345100024000797", font=("Courier", 24, "bold"), text_color="white"); self.lbl_qr_preview.pack(pady=10)
# #         self.update_qr_preview_logic()

# #     def show_about(self):
# #         self.clear_content()

# #         sc = ctk.CTkScrollableFrame(
# #             self.content_area, fg_color="transparent"
# #         )
# #         sc.pack(fill="both", expand=True, padx=20, pady=10)

# #         about_items = [
# #             ("about1.jpeg", "Manual checkouts slow you down and frustrate customers. Our AI-powered billing system automates product lookup, applies discounts, and eliminates human errors — ensuring faster and smarter checkouts.", "left"),
# #             ("about2.jpeg", "Guesswork leads to overstocking or stockouts. iLogic AI POS gives you live inventory tracking, automated reorder alerts, and AI-based demand forecasting to keep your shelves stocked smartly.", "right"),
# #             ("about3.jpeg", "Make transactions faster and frictionless. Accept all payment types including cash, cards, QR, e-wallets, and split billing — seamlessly integrated with your POS.", "left"),
# #         ]

# #         for img_name, desc, align in about_items:
# #             row = ctk.CTkFrame(sc, fg_color="transparent")
# #             row.pack(fill="x", pady=20)

# #             path = os.path.join(BASE_DIR, "about", img_name)
# #             if not os.path.exists(path):
# #                 continue

# #             img = ctk.CTkImage(Image.open(path), size=(370, 220))
# #             img_lbl = ctk.CTkLabel(row, image=img, text="")
# #             img_lbl.image = img   # 🔴 IMPORTANT

# #             text_lbl = ctk.CTkLabel(
# #                 row,
# #                 text=desc,
# #                 font=("Arial", 25),
# #                 text_color="#CCCCCC",
# #                 wraplength=380,
# #                 justify="left"
# #             )

# #             if align == "left":
# #                 img_lbl.pack(side="left", padx=(0, 20))
# #                 text_lbl.pack(side="left", expand=True, anchor="w")
# #             else:
# #                 text_lbl.pack(side="left", expand=True, anchor="e", padx=(0, 20))
# #                 img_lbl.pack(side="right")

# #         # Footer title
# #         ctk.CTkLabel(
# #             sc,
# #             text="iLogic POS System - V5.0",
# #             font=("Arial", 16, "bold"),
# #             text_color=self.colors["GOLD"]
# #         ).pack(pady=30)

# # def launch_settings(main_app): 
# #     main_app.show_settings_view()

# import customtkinter as ctk
# import os
# import cv2
# import tkinter as tk
# from tkinter import messagebox, filedialog
# from PIL import Image, ImageTk
# import db_functions
# import time
# from datetime import datetime, timedelta
# import threading
# import json
# import shutil
# import history_logger
# import weighing_scale
# import sys

# from app_config import DB_CONFIG
# # Try importing matplotlib for Pie Chart; handle gracefully if missing
# try:
#     from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#     import matplotlib.pyplot as plt
#     HAS_MATPLOTLIB = True
# except ImportError:
#     HAS_MATPLOTLIB = False


# # BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # SETTINGS_PATH = os.path.join(BASE_DIR, "config", "app_settings.json")

# def get_app_data_dir():
#     app_name = "AI_POS"
#     if sys.platform == "win32":
#         return os.path.join(os.environ["APPDATA"], app_name)
#     else:
#         return os.path.expanduser(f"~/.{app_name.lower()}")

# APP_DATA_DIR = get_app_data_dir()
# CONFIG_DIR = os.path.join(APP_DATA_DIR, "config")
# os.makedirs(CONFIG_DIR, exist_ok=True)

# SETTINGS_PATH = os.path.join(CONFIG_DIR, "app_settings.json")



# def load_app_settings():
#     if os.path.exists(SETTINGS_PATH):
#         with open(SETTINGS_PATH, "r") as f:
#             return json.load(f)
#     return {}

# def save_app_settings(data):
#     os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
#     with open(SETTINGS_PATH, "w") as f:
#         json.dump(data, f, indent=4)

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# FIXED_SQL_SERVER = "localhost"

# class HoverableCard(ctk.CTkFrame):
#     def __init__(self, master, normal_color, hover_color, **kwargs):
#         super().__init__(master, fg_color=normal_color, **kwargs)
#         self.normal_color = normal_color
#         self.hover_color = hover_color
#         self.bind("<Enter>", lambda e: self.configure(fg_color=self.hover_color))
#         self.bind("<Leave>", lambda e: self.configure(fg_color=self.normal_color))

# class SettingsUI:
#     def __init__(self, parent, colors, main_app):
#         self.parent = parent
#         self.colors = colors
#         self.main_app = main_app

        
        
#         # Canvas size MUST come first
#         self.canvas_w, self.canvas_h = 480, 360

#         # ROI corner points (4 handles)
#         self.tl = [0, 0]                     # top-left
#         self.tr = [self.canvas_w, 0]         # top-right
#         self.bl = [0, self.canvas_h]         # bottom-left
#         self.br = [self.canvas_w - 1, self.canvas_h - 1] # bottom-right
        
#         self.current_uom_filter = "ALL ITEM"
#         self.search_query = ""
#         self.roi_active = False
        
#         # QR Settings Defaults
#         self.qr_prefix_on = ctk.StringVar(value="OFF")
#         self.qr_prefix_val = "20"
#         self.qr_code_len = 5
#         self.qr_price_len = 5
#         self.qr_qty_len = 5
#         self.qr_currency = "USD"

#         self.app_settings = load_app_settings()
        
#         self.canvas_w, self.canvas_h = 480, 360
#         self.active_handle = None
#         self.pt1, self.pt2 = [0,0], [0,0] # Init placeholders
        
        
#         self.current_page = 0
#         self.history_filter_val = ctk.StringVar(value="LiveNow")
        
#         # Sidebar Init
#         self.sidebar = ctk.CTkFrame(self.parent, width=180, fg_color=self.colors["OCEAN"], corner_radius=0)
#         self.sidebar.pack(side="left", fill="y")
        
#         self.content_area = ctk.CTkFrame(self.parent, fg_color="transparent")
#         self.content_area.pack(side="right", fill="both", expand=True)

#         self.setup_sidebar()
#         self.show_dashboard()

#     def setup_sidebar(self):
#         # ===== LOGO SECTION =====
#         img_logo_path = os.path.join(BASE_DIR, "iLogic.webp")

#         logo_frame = ctk.CTkFrame(
#             self.sidebar,
#             fg_color="transparent"
#         )
#         logo_frame.pack(fill="x", pady=(25, 15))

#         if os.path.exists(img_logo_path):
#             try:
#                 raw_img = Image.open(img_logo_path)
#                 logo_ctk = ctk.CTkImage(raw_img, size=(130, 130))
#                 ctk.CTkLabel(
#                     logo_frame,
#                     image=logo_ctk,
#                     text=""
#                 ).pack()
#             except:
#                 pass

#         ctk.CTkLabel(
#             logo_frame,
#             text="iLogic POS",
#             font=("Segoe UI", 20, "bold"),
#             text_color="white"
#         ).pack(pady=(10, 0))

#         # ===== DIVIDER =====
#         ctk.CTkFrame(
#             self.sidebar,
#             height=1,
#             fg_color="#2a2a2a"
#         ).pack(fill="x", padx=20, pady=15)

#         # ===== NAVIGATION =====
#         nav_items = [
#             ("📊  Dashboard", self.show_dashboard),
#             ("🛒  View Products", self.show_view_product),
#             ("⚖︎  Weight Setting", self.show_weight_setting),
#             ("📷  Camera Setting", self.show_camera_settings),
#             # ("⛶  QR Setting", self.show_qr_settings),
#             ("🙎🏻‍♂️  About", self.show_about),
#             ("⚙️  Database Setting", self.show_database_setting)
#         ]

#         for text, cmd in nav_items:
#             btn = ctk.CTkButton(
#                 self.sidebar,
#                 text=text,
#                 anchor="w",
#                 height=44,                       # ⬅ Bigger button
#                 font=("Segoe UI", 14),
#                 fg_color="transparent",
#                 hover_color=self.colors["NAVY"],
#                 text_color="white",
#                 command=cmd
#             )
#             btn.pack(fill="x", padx=20, pady=4)

#         # ===== EXIT BUTTON =====
#         ctk.CTkButton(
#             self.sidebar,
#             text="⏻  Exit",
#             height=45,
#             font=("Segoe UI", 14, "bold"),
#             fg_color=self.colors["CORAL"],
#             hover_color="#c0392b",
#             command=self.main_app.show_main_view
#         ).pack(side="bottom", fill="x", padx=20, pady=25)

#     def clear_content(self):
#         self.roi_active = False
#         for widget in self.content_area.winfo_children():
#             widget.destroy()

#     def get_product_image_path(self, description, uom):
#         if uom == "KG":
#             path = os.path.join(BASE_DIR, "vf_images", f"{description}.webp")
#             return path if os.path.exists(path) else None
#         elif uom == "PCS":
#             path = os.path.join(BASE_DIR, "pcs", f"{description}.jpeg")
#             return path if os.path.exists(path) else None
#         return None


#     def show_database_setting(self):
#         self.clear_content()

#         ctk.CTkLabel(
#             self.content_area,
#             text="DATABASE SETTINGS",
#             font=("Arial", 22, "bold"),
#             text_color="white"
#         ).pack(anchor="w", padx=20, pady=15)

#         box = ctk.CTkFrame(self.content_area, fg_color=self.colors["OCEAN"], corner_radius=12)
#         box.pack(fill="x", padx=20, pady=10)

#         cfg_path = os.path.join(BASE_DIR, "config", "db_config.json")
#         if os.path.exists(cfg_path):
#             with open(cfg_path, "r") as f:
#                 cfg = json.load(f)
#         else:
#             cfg_path = os.path.join(BASE_DIR, "config", "db_config.json")

#             if os.path.exists(cfg_path):
#                 with open(cfg_path, "r") as f:
#                     cfg = json.load(f)
#             else:
#                 cfg = {
#                     "database": "",
#                     "username": "",
#                     "password": ""
#                 }

#         self.db_entries = {}

#         fields = [
#             ("Database Name", "database"),
#             ("Username", "username"),
#             ("Password", "password")
#         ]

#         for label, key in fields:
#             row = ctk.CTkFrame(box, fg_color="transparent")
#             row.pack(fill="x", padx=20, pady=8)

#             ctk.CTkLabel(row, text=label, width=160, anchor="w", text_color="white").pack(side="left")
#             ent = ctk.CTkEntry(row, width=300, show="*" if key == "password" else None)
#             ent.insert(0, cfg.get(key, ""))
#             ent.pack(side="left", padx=10)

#             self.db_entries[key] = ent

#         btns = ctk.CTkFrame(box, fg_color="transparent")
#         btns.pack(pady=20)

#         ctk.CTkButton(btns, text="TEST CONNECTION", fg_color="#457B9D",
#                     command=self.test_db_connection).pack(side="left", padx=10)

#         ctk.CTkButton(btns, text="SAVE SETTINGS", fg_color="#2ECC71",
#                     command=self.save_db_settings).pack(side="left", padx=10)
        
#         # --- CAMERA TRAINING RESET (DANGER ZONE) ---
#         danger_box = ctk.CTkFrame(
#             self.content_area,
#             fg_color="#2B0F0F",
#             corner_radius=12
#         )
#         danger_box.pack(fill="x", padx=20, pady=(30, 10))

#         ctk.CTkLabel(
#             danger_box,
#             text="DANGER ZONE",
#             font=("Arial", 14, "bold"),
#             text_color="#FF6B6B"
#         ).pack(pady=(10, 5))

#         ctk.CTkLabel(
#             danger_box,
#             text="This will permanently delete all trained camera data",
#             text_color="white"
#         ).pack(pady=(0, 10))

#         ctk.CTkButton(
#             danger_box,
#             text="🗑️ DELETE CAMERA TRAINING DATA",
#             height=40,
#             fg_color="#E63946",
#             hover_color="#C53030",
#             command=self.confirm_clear_camera_data
#         ).pack(pady=(0, 15))

#     def save_db_settings(self):
#         cfg = {
#             "driver": "ODBC Driver 17 for SQL Server",  # FIXED
#             "server": FIXED_SQL_SERVER,  # FIXED
#             "database": self.db_entries["database"].get().strip(),
#             "user": self.db_entries["username"].get().strip(),
#             "password": self.db_entries["password"].get(),
#         }

#         ok, msg = db_functions.test_connection(cfg)
#         if not ok:
#             messagebox.showerror("Connection Failed", msg)
#             return

#         DB_CONFIG.update(cfg)
#         os.makedirs(os.path.join(BASE_DIR, "config"), exist_ok=True)
#         with open(os.path.join(BASE_DIR, "config", "db_config.json"), "w") as f:
#             json.dump({
#                 "database": cfg["database"],
#                 "username": cfg["user"],
#                 "password": cfg["password"],
#             }, f, indent=4)

#         messagebox.showinfo("Connected", "Database connected and saved")

#         threading.Thread(
#             target=self.main_app._load_products_thread,
#             daemon=True
#         ).start()

#     def test_db_connection(self):
#         cfg = {
#             "driver": "ODBC Driver 17 for SQL Server",
#             "server": FIXED_SQL_SERVER,
#             "database": self.db_entries["database"].get().strip(),
#             "user": self.db_entries["username"].get().strip(),
#             "password": self.db_entries["password"].get(),
#         }

#         ok, msg = db_functions.test_connection(cfg)
#         if ok:
#             messagebox.showinfo("Success", "SQL Server connected successfully")
#         else:
#             messagebox.showerror("Failed", msg)

#     # --- DASHBOARD LOGIC (LAYOUT: TOP=Table, BOTTOM=Btn, NO INSTRUCTIONS) ---
#     def show_dashboard(self):
#         self.clear_content()

#         # Header
#         ctk.CTkLabel(
#             self.content_area,
#             text="🧠 BRAIN DASHBOARD",
#             font=("Segoe UI", 24, "bold"),
#             text_color="white"
#         ).pack(anchor="w", padx=20, pady=(15, 5))

#         # Get trained items
#         trained_items = []
#         if hasattr(self.main_app, "camera") and hasattr(self.main_app.camera, "get_learned_items"):
#             trained_items = self.main_app.camera.get_learned_items()

#         ctk.CTkLabel(
#             self.content_area,
#             text=f"BRAIN LOADED: {len(trained_items)} ITEMS",
#             font=("Arial", 16, "bold"),
#             text_color="#FFD700"
#         ).pack(anchor="w", padx=20, pady=(0, 10))

#         # Search bar
#         search_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
#         search_frame.pack(fill="x", padx=20, pady=5)

#         self.brain_search = ctk.CTkEntry(
#             search_frame,
#             placeholder_text="Search trained item..."
#         )
#         self.brain_search.pack(side="left", padx=5)

#         ctk.CTkButton(
#             search_frame,
#             text="SEARCH",
#             command=self.render_brain_boxes
#         ).pack(side="left", padx=5)

#         # Scrollable box area
#         self.brain_box_area = ctk.CTkScrollableFrame(
#             self.content_area,
#             fg_color="transparent"
#         )
#         self.brain_box_area.pack(fill="both", expand=True, padx=20, pady=10)

#         # Training button
#         ctk.CTkButton(
#             self.content_area,
#             text="➕ TRAIN NEW ITEM",
#             font=("Arial", 18, "bold"),
#             fg_color="#FFD700",
#             text_color="black",
#             hover_color="#E5C100",
#             height=60,
#             command=self.open_training_popup
#         ).pack(pady=20)

#         self.render_brain_boxes()

#     def render_brain_boxes(self):
#         for w in self.brain_box_area.winfo_children():
#             w.destroy()

#         query = self.dashboard_search.get().upper() if hasattr(self, "dashboard_search") else ""

#         items = []
#         if hasattr(self.main_app.camera, "get_learned_items"):
#             items = self.main_app.camera.get_learned_items()

#         if query:
#             items = [i for i in items if query in str(i.get("Code", "")).upper()]

#         # Grid setup
#         for i in range(4):
#             self.brain_box_area.grid_columnconfigure(i, weight=1)

#         for idx, item in enumerate(items):
#             card = HoverableCard(
#                 self.brain_box_area,
#                 normal_color=self.colors["OCEAN"],
#                 hover_color="#2A456E",
#                 corner_radius=12
#             )
#             card.grid(row=idx // 4, column=idx % 4, padx=10, pady=10, sticky="nsew")

#             code = item.get("Code", "N/A")
#             uom = item.get("UOM", "-")

#             ctk.CTkLabel(card, text="🧠", font=("Arial", 28)).pack(pady=(10, 0))
#             ctk.CTkLabel(card, text=f"CODE: {code}", font=("Arial", 13, "bold"), text_color="#FFD700").pack()
#             ctk.CTkLabel(card, text=f"UOM: {uom}", text_color="white").pack(pady=(0, 5))

#             ctk.CTkButton(
#                 card,
#                 text="FORGET",
#                 fg_color="#E63946",
#                 hover_color="#C53030",
#                 command=lambda c=code: self.main_app.camera.forget_item(c)
#             ).pack(pady=(5, 10))

#     def open_training_popup(self):
#         """Pop up for Taking Picture or Inserting Picture"""
#         t = ctk.CTkToplevel(self.parent)
#         t.title("Select Action")
#         t.geometry("400x300")
#         t.attributes("-topmost", True)
        
#         ctk.CTkLabel(t, text="CHOOSE ACTION", font=("Arial", 20, "bold")).pack(pady=20)
#         # 1. Take Picture
#         ctk.CTkButton(t, text="📸 TAKE PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#2ECC71",
#                       command=lambda: [t.destroy(), self.open_camera_capture()]).pack(pady=10)
#         # 2. Insert Picture
#         ctk.CTkButton(t, text="📂 INSERT PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#457B9D",
#                       command=lambda: [t.destroy(), self.upload_picture()]).pack(pady=10)
#         ctk.CTkButton(t, text="CANCEL", width=280, fg_color=self.colors["CORAL"], command=t.destroy).pack(pady=20)

#     # --- FUNCTION 1: CAPTURE FROM CAMERA ---
#     # def open_camera_capture(self):
#     #     p = tk.Toplevel(self.parent)
#     #     p.geometry("500x600"); p.title("Camera Capture"); p.configure(bg="black")
#     #     lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
#     #     cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#     #     def update_stream():
#     #         if not p.winfo_exists():
#     #             cap.release(); return
#     #         ret, frame = cap.read()
#     #         if ret:
#     #             rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
#     #             img = ImageTk.PhotoImage(Image.fromarray(rgb))
#     #             lbl_video.configure(image=img); lbl_video.image = img
#     #         p.after(20, update_stream)
#     #     def snap_photo():
#     #         ret, frame = cap.read()
#     #         if ret:
#     #             cap.release(); p.destroy(); self.show_save_form(frame)
#     #     ctk.CTkButton(p, text="SNAP", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
#     #     update_stream()

#     def open_camera_capture(self):
#         p = tk.Toplevel(self.parent)
#         p.geometry("500x600"); p.title("Camera Capture"); p.configure(bg="black")
#         lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
#         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#         roi_cfg = os.path.join(BASE_DIR, "camera_roi_config.txt")

#         roi = None
#         if os.path.exists(roi_cfg):
#             try:
#                 with open(roi_cfg, "r") as f:
#                     roi = tuple(map(int, f.read().strip().split(",")))
#             except:
#                 roi = None
#         if roi and hasattr(self.main_app, "camera"):
#             self.main_app.camera.roi_color_size = roi

#         def update_stream():
#             if not p.winfo_exists():
#                 cap.release(); return
#             # ret, frame = cap.read()
#             # if ret:
#             #     rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
#             ret, frame = cap.read()
#             if ret:
#                 if roi:
#                     x, y, w, h = roi
#                     cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

#                 rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))

#                 img = ImageTk.PhotoImage(Image.fromarray(rgb))
#                 lbl_video.configure(image=img); lbl_video.image = img
#             p.after(20, update_stream)
#         def snap_photo():
#             # ret, frame = cap.read()
#             # if ret:
#             #     cap.release(); p.destroy(); self.show_save_form(frame)
#             ret, frame = cap.read()
#             if ret:
#                 if roi:
#                     x, y, w, h = roi
#                     frame = frame[y:y+h, x:x+w]   # 👈 APPLY FIXED BOUNDARY

#                 cap.release()
#                 p.destroy()
#                 self.show_save_form(frame)

#         ctk.CTkButton(p, text="SNAP", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
#         update_stream()



#     # --- FUNCTION 2: UPLOAD FROM FILE ---
#     def upload_picture(self):
#         file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp")])
#         if file_path:
#             img = cv2.imread(file_path)
#             if img is not None: self.show_save_form(img)

#     def show_save_form(self, image_data):
#         self.clear_content()
#         sc = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"]); sc.pack(fill="both", expand=True, padx=20, pady=10)
#         rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]; ratio = 250 / h
#         rgb = cv2.resize(rgb, (int(w*ratio), 250)); prev_img = ctk.CTkImage(Image.fromarray(rgb), size=(int(w*ratio), 250))
#         ctk.CTkLabel(sc, image=prev_img, text="").pack(pady=10)
#         existing_codes = [int(i['Code']) for i in self.main_app.all_products if str(i['Code']).isdigit()]
#         next_code = str(max(existing_codes) + 1) if existing_codes else "1001"
#         form_fields = [("InventoryCode", next_code), ("Description", ""), ("Barcode", ""), ("UOM", "KG"), ("RetailPrice", "0.00"), ("BrandCode", "001")]
#         entries = {}
#         for idx, (lbl, default_val) in enumerate(form_fields):
#             ctk.CTkLabel(sc, text=lbl, text_color="white").pack(anchor="w", padx=20, pady=(5,0))
#             e = ctk.CTkEntry(sc, width=400); e.insert(0, default_val); e.pack(padx=20, pady=(0,10)); entries[lbl] = e
#         def commit_save():
#             d = {
#                 "InventoryCode": entries["InventoryCode"].get(), "Description": entries["Description"].get(), "Barcode": entries["Barcode"].get(), 
#                 "UOM": entries["UOM"].get().upper(), "RetailPrice": float(entries["RetailPrice"].get() or 0), "BrandCode": entries["BrandCode"].get(), 
#                 "CreateDate": datetime.now().strftime("%Y-%m-%d"), "InActive": 0
#             }
#             if db_functions.insert_inventory(d) == "SUCCESS":
#                 fname = f"{d['Description']}.webp" if d["UOM"]=="KG" else f"{d['Description']}.jpeg"
#                 save_dir = "vf_images" if d["UOM"]=="KG" else "pcs"
#                 save_path = os.path.join(BASE_DIR, save_dir, fname)
#                 cv2.imwrite(save_path, image_data)
                
#                 # --- FIX: SAFE RELOAD WITHOUT CRASHING ---
#                 # 1. Reload DB Products (Safe)
#                 if hasattr(self.main_app, "_load_products_thread"):
#                     threading.Thread(target=self.main_app._load_products_thread, daemon=True).start()
                
#                 # 2. Attempt to Reload Camera (Safe Check)
#                 if hasattr(self.main_app, "camera"):
#                     # Check for common method names since 'refresh_db' is missing
#                     if hasattr(self.main_app.camera, "load_data"):
#                         threading.Thread(target=self.main_app.camera.load_data, daemon=True).start()
#                     elif hasattr(self.main_app.camera, "load_features"):
#                         threading.Thread(target=self.main_app.camera.load_features, daemon=True).start()
#                     # If no method found, skip silently to prevent crash

#                 time.sleep(0.5) 
#                 self.show_dashboard() 

#                 messagebox.showinfo("Success", "Product Saved & System Refreshed!")
#             else: messagebox.showerror("Error", "DB Insert Failed")
#         ctk.CTkButton(sc, text="SAVE PRODUCT", height=45, fg_color="#2ECC71", command=commit_save).pack(pady=20)
#         ctk.CTkButton(sc, text="CANCEL", height=30, fg_color="gray", command=self.show_dashboard).pack(pady=5)

#     def update_scale_logic(self, _=None):
#         try:
#             new_port = self.opt_com.get()
#             new_baud = int(self.opt_baud.get())
#             new_protocol = self.opt_protocol.get()  # stored only, not used here

#             # 1️⃣ Save settings
#             self.app_settings.setdefault("weight", {}).update({
#                 "port": new_port,
#                 "baud": new_baud,
#                 "protocol": new_protocol
#             })
#             save_app_settings(self.app_settings)

#             # 2️⃣ LIVE update scale (NO restart, NO new thread)
#             if hasattr(self.main_app, "scale") and self.main_app.scale:
#                 self.main_app.scale.update_config(
#                     port=new_port,
#                     baudrate=new_baud
#                 )

#         except Exception as e:
#             messagebox.showerror("Scale Error", str(e))

#     def show_weight_setting(self):
#         self.clear_content()
#         scroll = ctk.CTkScrollableFrame(
#             self.content_area, fg_color="transparent"
#         )
#         scroll.pack(fill="both", expand=True, padx=20, pady=10)

#         ctk.CTkLabel(
#             scroll, text="DEVICE SETTING",
#             font=("Arial", 22, "bold"),
#             text_color="white"
#         ).pack(anchor="w", pady=10)

#         box1 = ctk.CTkFrame(
#             scroll, fg_color=self.colors["OCEAN"], corner_radius=12
#         )
#         box1.pack(fill="x", pady=5)

#         # ================= SCALE SETTINGS =================

#         # 🔹 Load persisted weight settings
#         wt = self.app_settings.get("weight", {})

#         saved_port = wt.get("port", "COM1")
#         saved_baud = str(wt.get("baud", "9600"))
#         saved_protocol = wt.get("protocol", "RS232")

#         # ---------- Protocol ----------
#         f1 = ctk.CTkFrame(box1, fg_color="transparent")
#         f1.pack(pady=10, padx=15, fill="x")

#         ctk.CTkLabel(
#             f1, text="Scale Setting:",
#             width=140, anchor="w",
#             text_color="white"
#         ).pack(side="left")

#         self.opt_protocol = ctk.CTkOptionMenu(
#             f1, values=["RS232", "RS249"],
#             command=self.update_scale_logic
#         )
#         self.opt_protocol.set(saved_protocol)
#         self.opt_protocol.pack(side="left", padx=20)

#         # ---------- COM Port ----------
#         f2 = ctk.CTkFrame(box1, fg_color="transparent")
#         f2.pack(pady=10, padx=15, fill="x")

#         ctk.CTkLabel(
#             f2, text="Serial Port Setting:",
#             width=140, anchor="w",
#             text_color="white"
#         ).pack(side="left")

#         self.opt_com = ctk.CTkOptionMenu(
#             f2,
#             values=[f"COM{i}" for i in range(1, 11)],
#             command=self.update_scale_logic
#         )
#         self.opt_com.set(saved_port)
#         self.opt_com.pack(side="left", padx=20)

#         # ---------- Baud Rate ----------
#         f3 = ctk.CTkFrame(box1, fg_color="transparent")
#         f3.pack(pady=10, padx=15, fill="x")

#         ctk.CTkLabel(
#             f3, text="Baud Rate Setting:",
#             width=140, anchor="w",
#             text_color="white"
#         ).pack(side="left")

#         self.opt_baud = ctk.CTkOptionMenu(
#             f3,
#             values=["1200","2400","4800","9600","19200","38400","115200"],
#             command=self.update_scale_logic
#         )
#         self.opt_baud.set(saved_baud)
#         self.opt_baud.pack(side="left", padx=20)

#         # ================= UNIT SETTINGS =================

#         ctk.CTkLabel(
#             scroll, text="UNIT SETTING",
#             font=("Arial", 22, "bold"),
#             text_color="white"
#         ).pack(anchor="w", pady=(25, 10))

#         box2 = ctk.CTkFrame(
#             scroll, fg_color=self.colors["OCEAN"], corner_radius=12
#         )
#         box2.pack(fill="x", pady=5)

#         f_u = ctk.CTkFrame(box2, fg_color="transparent")
#         f_u.pack(pady=20, padx=15, fill="x")

#         ctk.CTkLabel(
#             f_u, text="Print Unit Setting (Ratio):",
#             width=180, anchor="w",
#             text_color="white"
#         ).pack(side="left")

#         ctk.CTkOptionMenu(
#             f_u, values=["KG", "Pound", "Viss", "Gram", "15kg", "30kg"]
#         ).pack(side="left", padx=20)

#     def show_view_product(self):
#         self.clear_content()
#         self.current_uom_filter = "ALL ITEM"; self.search_query = ""; self.current_page = 0
#         ctk.CTkLabel(self.content_area, text="PRODUCT INVENTORY", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
#         f_bar = ctk.CTkFrame(self.content_area, fg_color="transparent"); f_bar.pack(fill="x", padx=15, pady=5)
#         self.uom_selector = ctk.CTkSegmentedButton(f_bar, values=["ALL ITEM", "KG", "PCS"], command=self.filter_by_uom)
#         self.uom_selector.set(self.current_uom_filter); self.uom_selector.pack(side="left")
#         self.search_entry = ctk.CTkEntry(f_bar, placeholder_text="Code or Name...", width=140); self.search_entry.pack(side="left", padx=15)
#         ctk.CTkButton(f_bar, text="SEARCH", width=70, command=self.apply_search).pack(side="left")
#         self.grid_container = ctk.CTkFrame(self.content_area, fg_color="transparent"); self.grid_container.pack(fill="both", expand=True, padx=15)
#         pg = ctk.CTkFrame(self.content_area, fg_color="transparent", height=40); pg.pack(fill="x", side="bottom", pady=10)
#         ctk.CTkButton(pg, text="<< PREV", width=100, command=self.prev_page, fg_color=self.colors["OCEAN"]).pack(side="left", padx=40)
#         self.lbl_page = ctk.CTkLabel(pg, text="PAGE 1", font=("Arial", 12, "bold"), text_color="white"); self.lbl_page.pack(side="left", expand=True)
#         ctk.CTkButton(pg, text="NEXT >>", width=100, command=self.next_page, fg_color=self.colors["OCEAN"]).pack(side="right", padx=40)
#         self.render_grid()

#     def apply_search(self): 
#         self.search_query = self.search_entry.get().upper()
#         self.current_page = 0
#         self.render_grid()

#     def filter_by_uom(self, v): self.current_uom_filter = v; self.current_page = 0; self.render_grid()
    
#     def next_page(self):
#         items = [i for i in self.main_app.all_products if (self.current_uom_filter == "ALL ITEM" or i['UOM'] == self.current_uom_filter)]
#         if self.search_query: 
#             items = [i for i in items if self.search_query in str(i['Code']).upper() or self.search_query in str(i['Name']).upper()]
#         if self.current_page < max(1, (len(items)+9)//10) - 1: self.current_page += 1; self.render_grid()
    
#     def prev_page(self):
#         if self.current_page > 0: self.current_page -= 1; self.render_grid()
    
#     def render_grid(self):
#         for w in self.grid_container.winfo_children(): w.destroy()
#         # Responsive grid setup
#         for i in range(5): self.grid_container.grid_columnconfigure(i, weight=1)
        
#         items = [i for i in self.main_app.all_products if (self.current_uom_filter == "ALL ITEM" or i['UOM'] == self.current_uom_filter)]
        
#         # --- MODIFIED SEARCH LOGIC: CODE OR DESCRIPTION ---
#         if self.search_query: 
#             items = [i for i in items if self.search_query in str(i['Code']).upper() or self.search_query in str(i['Name']).upper()]
            
#         start = self.current_page * 10
#         self.lbl_page.configure(text=f"PAGE {self.current_page + 1} OF {max(1, (len(items)+9)//10)}")
        
#         for i, item in enumerate(items[start:start+10]):
#             card = HoverableCard(self.grid_container, normal_color=self.colors["OCEAN"], hover_color="#2A456E", corner_radius=10)
#             card.grid(row=i//5, column=i%5, padx=8, pady=8, sticky="nsew") # Responsive sticky
#             path = self.get_product_image_path(item['Name'], item['UOM'])
#             if path:
#                 try: 
#                     img = ctk.CTkImage(Image.open(path), size=(100, 80)); 
#                     lbl=ctk.CTkLabel(card, image=img, text=""); lbl.image=img; lbl.pack(pady=(10,5))
#                 except: ctk.CTkLabel(card, text="IMG ERR", text_color="red").pack(pady=20)
#             else: ctk.CTkLabel(card, text="🖼️", font=("Arial",12)).pack(pady=15)
#             ctk.CTkLabel(card, text=item['Code'], font=("Arial",12,"bold"), text_color="#FFD700").pack()
#             ctk.CTkLabel(card, text=(item['Name'][:13]+".." if len(item['Name'])>15 else item['Name']), font=("Arial",11), text_color="white").pack()
            
#             # --- MODIFIED: EDIT BUTTON INSTEAD OF SELECT ---
#             ctk.CTkButton(
#                 card,
#                 text="EDIT IMAGE",
#                 fg_color="#F39C12", # Orange for edit
#                 hover_color="#D68910",
#                 height=35, # Bigger
#                 width=140, # Bigger
#                 font=("Arial", 12, "bold"),
#                 command=lambda i=item: self.open_edit_image_popup(i)
#             ).pack(pady=(10, 10))

#     def open_edit_image_popup(self, item):
#         """ Pop up to Edit Image (Take New or Upload New) """
#         t = ctk.CTkToplevel(self.parent)
#         t.title("Edit Product Image")
#         t.geometry("400x320")
#         t.attributes("-topmost", True)
        
#         ctk.CTkLabel(t, text=f"EDIT IMAGE: {item['Name']}", font=("Arial", 16, "bold")).pack(pady=15)
        
#         # 1. Take Picture
#         ctk.CTkButton(t, text="📸 TAKE NEW PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#2ECC71",
#                       command=lambda: [t.destroy(), self.edit_camera_capture(item)]).pack(pady=10)
#         # 2. Insert Picture
#         ctk.CTkButton(t, text="📂 UPLOAD NEW PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#457B9D",
#                       command=lambda: [t.destroy(), self.edit_upload_picture(item)]).pack(pady=10)
        
#         ctk.CTkButton(t, text="CANCEL", width=280, fg_color=self.colors["CORAL"], command=t.destroy).pack(pady=20)

#     def edit_camera_capture(self, item):
#         p = tk.Toplevel(self.parent)
#         p.geometry("500x600"); p.title(f"Snap: {item['Name']}"); p.configure(bg="black")
#         lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
#         cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
#         def update_stream():
#             if not p.winfo_exists(): cap.release(); return
#             ret, frame = cap.read()
#             if ret:
#                 rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
#                 img = ImageTk.PhotoImage(Image.fromarray(rgb))
#                 lbl_video.configure(image=img); lbl_video.image = img
#             p.after(20, update_stream)
#         def snap_photo():
#             ret, frame = cap.read()
#             if ret:
#                 cap.release(); p.destroy(); self.save_edited_image(item, frame)
#         ctk.CTkButton(p, text="SNAP & SAVE", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
#         update_stream()

#     def edit_upload_picture(self, item):
#         file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp")])
#         if file_path:
#             img = cv2.imread(file_path)
#             if img is not None: self.save_edited_image(item, img)

#     def save_edited_image(self, item, image_data):
#         # Determine path based on item details
#         uom = item.get('UOM', 'KG')
#         name = item.get('Name', 'Unknown')
        
#         folder = "vf_images" if uom == "KG" else "pcs"
#         ext = ".webp" if uom == "KG" else ".jpeg"
        
#         # Ensure directory exists
#         save_dir = os.path.join(BASE_DIR, folder)
#         if not os.path.exists(save_dir): os.makedirs(save_dir)
        
#         save_path = os.path.join(save_dir, f"{name}{ext}")
        
#         try:
#             cv2.imwrite(save_path, image_data)
            
#             # --- FIX: SAFE RELOAD WITHOUT CRASHING ---
#             # 1. Reload DB Products
#             if hasattr(self.main_app, "_load_products_thread"):
#                 threading.Thread(target=self.main_app._load_products_thread, daemon=True).start()
            
#             # 2. Attempt to Reload Camera (Safe Check)
#             if hasattr(self.main_app, "camera"):
#                  # Check for common method names since 'refresh_db' is missing
#                  if hasattr(self.main_app.camera, "load_data"):
#                      threading.Thread(target=self.main_app.camera.load_data, daemon=True).start()
#                  elif hasattr(self.main_app.camera, "load_features"):
#                      threading.Thread(target=self.main_app.camera.load_features, daemon=True).start()

#             time.sleep(0.3)
#             self.render_grid() # Refresh grid in View Product
            
#             messagebox.showinfo("Success", "Product image updated successfully!")
#         except Exception as e:
#             messagebox.showerror("Error", f"Failed to save image: {e}")

#     # --- SHOW CAMERA SETTINGS (With ROI) ---
    
#     def show_camera_settings(self):
#         self.clear_content()
#         scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
#         scroll.pack(fill="both", expand=True, padx=15)

#         ctk.CTkLabel(scroll, text="VISION BOUNDARY CONFIGURATION", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
#         ctk.CTkLabel(scroll, text="DRAG CIRCLES TO ADJUST", font=("Arial", 12), text_color="yellow").pack()

#         self.roi_canvas = tk.Canvas(scroll, width=self.canvas_w, height=self.canvas_h, bg="black", highlightthickness=0)
#         self.roi_canvas.pack(pady=10)

#         # FULL camera ROI (4 corner handles)
#         self.tl = [0, 0]
#         self.tr = [self.canvas_w, 0]
#         self.bl = [0, self.canvas_h]
#         self.br = [self.canvas_w, self.canvas_h]

#         roi_cfg = os.path.join(BASE_DIR, "camera_roi_config.txt")
#         if os.path.exists(roi_cfg):
#             try:
#                 with open(roi_cfg,"r") as f:
#                     vals=tuple(map(int,f.read().strip().split(",")))
#                     if len(vals)==4:
#                         self.main_app.camera.roi = vals
#             except:
#                 pass

#         cx, cy, cw, ch = self.main_app.camera.roi
#         sx, sy = self.canvas_w/640, self.canvas_h/480
#         self.pt1, self.pt2 = [cx*sx, cy*sy], [(cx+cw)*sx, (cy+ch)*sy]

#         # 🔥 IMPORTANT: Update corner handles from pt1/pt2
#         self.tl = [self.pt1[0], self.pt1[1]]
#         self.tr = [self.pt2[0], self.pt1[1]]
#         self.bl = [self.pt1[0], self.pt2[1]]
#         self.br = [self.pt2[0], self.pt2[1]]

#         self.roi_canvas.bind("<Button-1>", self.on_roi_press)
#         self.roi_canvas.bind("<B1-Motion>", self.on_roi_drag)

#         ctk.CTkButton(scroll, text="SAVE VISION BOUNDARY", fg_color="#2ECC71",text_color="black",height=40, command=self.save_roi).pack(pady=10)

#         self.roi_active=True
#         self.update_roi_preview()



#     def on_roi_press(self, e):
#         r = 12  # hit radius

#         def hit(p):
#             return abs(e.x - p[0]) <= r and abs(e.y - p[1]) <= r

#         if hit(self.tl):
#             self.active_handle = "tl"
#         elif hit(self.tr):
#             self.active_handle = "tr"
#         elif hit(self.bl):
#             self.active_handle = "bl"
#         elif hit(self.br):
#             self.active_handle = "br"
#         else:
#             self.active_handle = None

        
#     # def on_roi_drag(self, e):
#     #     if self.active_handle=="pt1": self.pt1 = [max(0,min(e.x, self.pt2[0]-10)), max(0,min(e.y, self.pt2[1]-10))]
#     #     elif self.active_handle=="pt2": self.pt2 = [max(self.pt1[0]+10,min(e.x, self.canvas_w)), max(self.pt1[1]+10,min(e.y, self.canvas_h))]
    
#     def on_roi_drag(self, e):
#         x = max(0, min(e.x, self.canvas_w))
#         y = max(0, min(e.y, self.canvas_h))

#         if self.active_handle == "tl":
#             # Prevent crossing BR
#             x = min(x, self.br[0] - 1)
#             y = min(y, self.br[1] - 1)

#             self.tl = [x, y]
#             self.tr[1] = y
#             self.bl[0] = x

#         elif self.active_handle == "tr":
#             # Prevent crossing BL
#             x = max(x, self.tl[0] + 1)
#             y = min(y, self.br[1] - 1)

#             self.tr = [x, y]
#             self.tl[1] = y
#             self.br[0] = x

#         elif self.active_handle == "bl":
#             # Prevent crossing TR
#             x = min(x, self.br[0] - 1)
#             y = max(y, self.tl[1] + 1)

#             self.bl = [x, y]
#             self.tl[0] = x
#             self.br[1] = y

#         elif self.active_handle == "br":
#             # Prevent crossing TL
#             x = max(x, self.tl[0] + 1)
#             y = max(y, self.tl[1] + 1)

#             self.br = [x, y]
#             self.tr[0] = x
#             self.bl[1] = y

    
#     def update_roi_preview(self):
#         if not self.roi_active or not self.roi_canvas.winfo_exists():
#             return

#         fr = self.main_app.camera.get_frame(draw_box=False)

#         if fr is not None:
#             # Crop center area (same as your existing logic)
#             # fr = fr[
#             #     int(fr.shape[0] * 0.2):int(fr.shape[0] * 0.8),
#             #     int(fr.shape[1] * 0.2):int(fr.shape[1] * 0.8)
#             # ]

#             try:
#                 prev = cv2.resize(fr, (self.canvas_w, self.canvas_h))
#                 img_tk = ImageTk.PhotoImage(
#                     Image.fromarray(cv2.cvtColor(prev, cv2.COLOR_BGR2RGB))
#                 )

#                 self.roi_canvas.delete("all")
#                 self.roi_canvas.create_image(0, 0, anchor="nw", image=img_tk)
#                 self.roi_canvas.image = img_tk
                
#                 # Ensure BR is inside canvas (clickable)
#                 self.br[0] = min(self.br[0], self.canvas_w - 1)
#                 self.br[1] = min(self.br[1], self.canvas_h - 1)

#                 # Draw green ROI rectangle
#                 self.roi_canvas.create_rectangle(
#                     self.tl[0], self.tl[1],
#                     self.br[0], self.br[1],
#                     outline="#00FF00",
#                     width=2
#                 )

#                 # Draw 4 red corner handles
#                 for p in (self.tl, self.tr, self.bl, self.br):
#                     self.roi_canvas.create_oval(
#                         p[0] - 8, p[1] - 8,
#                         p[0] + 8, p[1] + 8,
#                         fill="red",
#                         outline="white"
#                     )

#             except Exception as e:
#                 print("ROI preview error:", e)

#         if self.roi_active:
#             self.parent.after(40, self.update_roi_preview)

#     def save_roi(self):
#         # Use tl and br (NOT pt1/pt2)
#         sx, sy = 640/self.canvas_w, 480/self.canvas_h

#         nx = int(self.tl[0] * sx)
#         ny = int(self.tl[1] * sy)
#         nw = int((self.tr[0] - self.tl[0]) * sx)
#         nh = int((self.bl[1] - self.tl[1]) * sy)

#         try:
#             with open(os.path.join(BASE_DIR, "camera_roi_config.txt"), "w") as f:
#                 f.write(f"{nx},{ny},{nw},{nh}")
#         except:
#             pass

#         self.main_app.camera.roi = (nx, ny, nw, nh)
#         messagebox.showinfo("Saved", "Boundary Saved.")



#     def confirm_clear_camera_data(self):
#         popup = ctk.CTkToplevel(self.parent)
#         popup.title("ADMIN VERIFICATION")
#         popup.geometry("340x230")
#         popup.grab_set()
#         popup.attributes("-topmost", True)

#         ctk.CTkLabel(
#             popup,
#             text="ADMIN PASSWORD REQUIRED",
#             font=("Arial", 15, "bold"),
#             text_color="red"
#         ).pack(pady=20)

#         pwd_entry = ctk.CTkEntry(
#             popup,
#             width=220,
#             show="*"
#         )
#         pwd_entry.pack(pady=10)

#         def verify_and_delete():
#             password = pwd_entry.get().strip()

#             if not password:
#                 messagebox.showwarning("Missing", "Please enter password")
#                 return

#             if not db_functions.validate_admin_password(password):
#                 messagebox.showerror(
#                     "ACCESS DENIED",
#                     "Invalid ADMIN password"
#                 )
#                 return

#             popup.destroy()

#             if hasattr(self.main_app, "camera") and self.main_app.camera:
#                 ok = self.main_app.camera.clear_learned_data()
#                 if ok:
#                     messagebox.showinfo(
#                         "SUCCESS",
#                         "Camera training JSON data deleted successfully"
#                     )
#                 else:
#                     messagebox.showerror(
#                         "ERROR",
#                         "Failed to delete training data"
#                     )
#             else:
#                 messagebox.showerror(
#                     "ERROR",
#                     "Camera module not initialized"
#                 )

#         ctk.CTkButton(
#             popup,
#             text="CONFIRM DELETE",
#             fg_color="#E63946",
#             height=40,
#             command=verify_and_delete
#         ).pack(pady=20)

#         ctk.CTkButton(
#             popup,
#             text="CANCEL",
#             fg_color="gray",
#             command=popup.destroy
#         ).pack()

#     def clear_learned_data(self):
#         try:
#             if not os.path.exists(self.training_data_dir):
#                 return True

#             for f in os.listdir(self.training_data_dir):
#                 if f.endswith(".json"):
#                     os.remove(os.path.join(self.training_data_dir, f))

#             return True
#         except Exception as e:
#             print("Delete error:", e)
#             return False

#     # --- SHOW HISTORY (Split 2 Grids) ---
#     def show_history(self):
#         self.clear_content()

#         # ================================
#         # GRID 1: MAIN WINDOW ACTIVE ITEM
#         # ================================
        
#         ctk.CTkLabel(self.content_area, text="CURRENT SELECTION (FROM MAIN WINDOW)", font=("Arial", 18, "bold"), text_color="#FFD700").pack(anchor="w", padx=20, pady=(15, 5))
        
#         # Grid 1 container (Scrollable, smaller height)
#         self.selection_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"], height=120)
#         self.selection_scroll.pack(fill="x", padx=20, pady=5)
        
#         # Headers for Top Grid
#         top_headers = ["BARCODE / QR", "DATE", "TIME", "DESCRIPTION", "UOM"]
#         for col, h in enumerate(top_headers):
#             ctk.CTkLabel(self.selection_scroll, text=h, font=("Arial", 12, "bold"), text_color="#FFD700").grid(row=0, column=col, padx=15, pady=8, sticky="w")
        
#         sep = ctk.CTkFrame(self.selection_scroll, height=2, fg_color="white")
#         sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 5))

#         # Check Active Selection from Main App
#         active_item = self.main_app.active_selection
#         if active_item:
#             # Grab details
#             # Barcode: stored in main app label (generated string)
#             barcode = "N/A"
#             if hasattr(self.main_app, 'lbl_qr_string'):
#                 barcode = self.main_app.lbl_qr_string.cget("text")
            
#             description = active_item.get("Name", "Unknown")
#             uom = active_item.get("UOM", "-")
            
#             now = datetime.now()
#             date_str = now.strftime("%Y-%m-%d")
#             time_str = now.strftime("%H:%M:%S")

#             row_data = [barcode, date_str, time_str, description, uom]
#             for c, v in enumerate(row_data):
#                 ctk.CTkLabel(self.selection_scroll, text=str(v), text_color="white", font=("Arial", 11)).grid(row=2, column=c, padx=15, pady=4, sticky="w")
#         else:
#              ctk.CTkLabel(self.selection_scroll, text="No item currently selected in main window.", text_color="silver").grid(row=2, column=0, columnspan=5, pady=20)


#         # ================================
#         # GRID 2: TRAINING DATA HISTORY
#         # ================================

#         # Header + Filter Frame for History
#         top_bar = ctk.CTkFrame(self.content_area, fg_color="transparent")
#         top_bar.pack(fill="x", padx=20, pady=(20, 10))
        
#         ctk.CTkLabel(top_bar, text="TRAINING HISTORY", font=("Arial", 20, "bold"), text_color="white").pack(side="left")
        
#         # Filter Logic
#         filter_box = ctk.CTkOptionMenu(top_bar, values=["LiveNow", "Yesterday", "Last Week"], variable=self.history_filter_val, 
#                                        command=lambda v: self.render_history_table(), width=130)
#         filter_box.pack(side="right")
#         ctk.CTkLabel(top_bar, text="Filter By:", text_color="silver").pack(side="right", padx=10)
        
#         # Table Container (Scrollable)
#         self.history_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"])
#         self.history_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
#         self.render_history_table()

#     def render_history_table(self):
#         # Clear current
#         for widget in self.history_scroll.winfo_children():
#             widget.destroy()
            
#         # Headers
#         headers = ["DATE", "TIME", "CODE", "UOM", "QTY / WEIGHT"]
#         for col, h in enumerate(headers):
#             ctk.CTkLabel(self.history_scroll, text=h, font=("Arial", 12, "bold"), text_color="#FFD700").grid(row=0, column=col, padx=15, pady=8, sticky="w")
        
#         # Add a Separator
#         sep = ctk.CTkFrame(self.history_scroll, height=2, fg_color="white")
#         sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 5))

#         # Get Raw Data from Main Logger (permanent storage)
#         raw_history = history_logger.get_history() # Expected list of dicts: date, time, code, uom, qty
        
#         # Apply Date Filter
#         filtered_data = []
#         filter_mode = self.history_filter_val.get()
#         now = datetime.now()
#         today_str = now.strftime("%Y-%m-%d")
#         yest_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
#         week_cutoff = (now - timedelta(days=7))

#         for item in raw_history:
#             # Assume item['date'] is YYYY-MM-DD
#             d_str = item.get('date', "")
            
#             include = False
#             if filter_mode == "LiveNow":
#                 if d_str == today_str: include = True
#             elif filter_mode == "Yesterday":
#                 if d_str == yest_str: include = True
#             elif filter_mode == "Last Week":
#                 try:
#                     d_obj = datetime.strptime(d_str, "%Y-%m-%d")
#                     if d_obj >= week_cutoff: include = True
#                 except: pass
            
#             if include:
#                 filtered_data.append(item)
        
#         # Sort desc (latest first) if not already
#         # Render Rows
#         if not filtered_data:
#             ctk.CTkLabel(self.history_scroll, text="No records found for selected period.", text_color="silver").grid(row=2, column=0, columnspan=5, pady=20)
#         else:
#             for r, row_data in enumerate(filtered_data, 2):
#                 vals = [row_data.get('date'), row_data.get('time'), row_data.get('code'), row_data.get('uom'), row_data.get('qty')]
#                 bg = "#1F2B3E" if r % 2 == 0 else "transparent" # Striped rows optional, simple transparent here
                
#                 for c, v in enumerate(vals):
#                     ctk.CTkLabel(self.history_scroll, text=str(v), text_color="white", font=("Arial", 11)).grid(row=r, column=c, padx=15, pady=4, sticky="w")

#     # --- SHOW QR SETTINGS (With Live Preview) ---
#     def update_qr_preview_logic(self, _=None):
#         self.app_settings.setdefault("qr", {}).update({
#             "prefix_enabled": self.qr_prefix_on.get() == "ON",
#             "prefix_value": self.opt_prefix_val.get(),
#             "code_len": int(self.opt_code_digit.get()),
#             "price_len": int(self.opt_price_digit.get()),
#             "qty_len": int(self.opt_qty_digit.get())
#         })
#         save_app_settings(self.app_settings)
#         prefix = self.opt_prefix_val.get() if self.qr_prefix_on.get() == "ON" else ""
#         icode = "03451".zfill(int(self.opt_code_digit.get()))[:int(self.opt_code_digit.get())]
#         iprice = "00024".zfill(int(self.opt_price_digit.get()))[:int(self.opt_price_digit.get())]
#         iqty = "000797".zfill(int(self.opt_qty_digit.get()))[:int(self.opt_qty_digit.get())]
#         self.lbl_qr_preview.configure(text=f"{prefix}{icode}{iprice}{iqty}")

#     def show_qr_settings(self):
#         self.clear_content(); scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent"); scroll.pack(fill="both", expand=True, padx=20, pady=10)
#         ctk.CTkLabel(scroll, text="QR & BARCODE FORMAT CONFIG", font=("Arial", 22, "bold"), text_color="white").pack(anchor="w", pady=10)
#         form = ctk.CTkFrame(scroll, fg_color=self.colors["OCEAN"], corner_radius=12); form.pack(fill="x", pady=10)
        
#         r1 = ctk.CTkFrame(form, fg_color="transparent"); r1.pack(fill="x", padx=15, pady=8)
#         ctk.CTkLabel(r1, text="Prefix Default (e.g. 20):", width=160, anchor="w", text_color="white").pack(side="left")
#         ctk.CTkSwitch(r1, text="", variable=self.qr_prefix_on, onvalue="ON", offvalue="OFF", command=self.update_qr_preview_logic).pack(side="left", padx=5)
#         self.opt_prefix_val = ctk.CTkOptionMenu(r1, values=[str(i) for i in range(20,91)], command=self.update_qr_preview_logic); self.opt_prefix_val.set("20"); self.opt_prefix_val.pack(side="left", padx=20)
        
#         r2 = ctk.CTkFrame(form, fg_color="transparent"); r2.pack(fill="x", padx=15, pady=8)
#         ctk.CTkLabel(r2, text="Inventory Code Length:", width=160, anchor="w", text_color="white").pack(side="left")
#         self.opt_code_digit = ctk.CTkOptionMenu(r2, values=["4","5","6"], command=self.update_qr_preview_logic); self.opt_code_digit.set("5"); self.opt_code_digit.pack(side="left", padx=20)
        
#         r3 = ctk.CTkFrame(form, fg_color="transparent"); r3.pack(fill="x", padx=15, pady=8)
#         ctk.CTkLabel(r3, text="Currency / Price Digits:", width=160, anchor="w", text_color="white").pack(side="left")
#         ctk.CTkOptionMenu(r3, values=["USD","IND","EUR","SGD","MYR"]).pack(side="left", padx=5)
#         self.opt_price_digit = ctk.CTkOptionMenu(r3, values=["4","5","6"], width=80, command=self.update_qr_preview_logic); self.opt_price_digit.set("5"); self.opt_price_digit.pack(side="left", padx=10)
        
#         r4 = ctk.CTkFrame(form, fg_color="transparent"); r4.pack(fill="x", padx=15, pady=8)
#         ctk.CTkLabel(r4, text="Weight/Qty Length:", width=160, anchor="w", text_color="white").pack(side="left")
#         self.opt_qty_digit = ctk.CTkOptionMenu(r4, values=["4","5","6"], command=self.update_qr_preview_logic); self.opt_qty_digit.set("5"); self.opt_qty_digit.pack(side="left", padx=20)
        
#         preview = ctk.CTkFrame(scroll, fg_color="#000", border_width=2, border_color=self.colors["GOLD"]); preview.pack(fill="x", pady=20)
#         ctk.CTkLabel(preview, text="GENERATION PREVIEW", font=("Arial", 10, "bold"), text_color=self.colors["GOLD"]).pack(pady=5)
#         self.lbl_qr_preview = ctk.CTkLabel(preview, text="200345100024000797", font=("Courier", 24, "bold"), text_color="white"); self.lbl_qr_preview.pack(pady=10)
#         self.update_qr_preview_logic()

#     def show_about(self):
#         self.clear_content()

#         sc = ctk.CTkScrollableFrame(
#             self.content_area, fg_color="transparent"
#         )
#         sc.pack(fill="both", expand=True, padx=20, pady=10)

#         about_items = [
#             ("about1.jpeg", "Manual checkouts slow you down and frustrate customers. Our AI-powered billing system automates product lookup, applies discounts, and eliminates human errors — ensuring faster and smarter checkouts.", "left"),
#             ("about2.jpeg", "Guesswork leads to overstocking or stockouts. iLogic AI POS gives you live inventory tracking, automated reorder alerts, and AI-based demand forecasting to keep your shelves stocked smartly.", "right"),
#             ("about3.jpeg", "Make transactions faster and frictionless. Accept all payment types including cash, cards, QR, e-wallets, and split billing — seamlessly integrated with your POS.", "left"),
#         ]

#         for img_name, desc, align in about_items:
#             row = ctk.CTkFrame(sc, fg_color="transparent")
#             row.pack(fill="x", pady=20)

#             path = os.path.join(BASE_DIR, "about", img_name)
#             if not os.path.exists(path):
#                 continue

#             img = ctk.CTkImage(Image.open(path), size=(370, 220))
#             img_lbl = ctk.CTkLabel(row, image=img, text="")
#             img_lbl.image = img   # 🔴 IMPORTANT

#             text_lbl = ctk.CTkLabel(
#                 row,
#                 text=desc,
#                 font=("Arial", 25),
#                 text_color="#CCCCCC",
#                 wraplength=380,
#                 justify="left"
#             )

#             if align == "left":
#                 img_lbl.pack(side="left", padx=(0, 20))
#                 text_lbl.pack(side="left", expand=True, anchor="w")
#             else:
#                 text_lbl.pack(side="left", expand=True, anchor="e", padx=(0, 20))
#                 img_lbl.pack(side="right")

#         # Footer title
#         ctk.CTkLabel(
#             sc,
#             text="iLogic POS System - V5.0",
#             font=("Arial", 16, "bold"),
#             text_color=self.colors["GOLD"]
#         ).pack(pady=30)

# def launch_settings(main_app): 
#     main_app.show_settings_view()


import customtkinter as ctk
import os
import cv2
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import db_functions
import time
from datetime import datetime, timedelta
import threading
import json
import shutil
import history_logger
import weighing_scale
import sys
import numpy as np

from app_config import DB_CONFIG
# Try importing matplotlib for Pie Chart; handle gracefully if missing
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SETTINGS_PATH = os.path.join(BASE_DIR, "config", "app_settings.json")

def get_app_data_dir():
    app_name = "AI_POS"
    if sys.platform == "win32":
        return os.path.join(os.environ["APPDATA"], app_name)
    else:
        return os.path.expanduser(f"~/.{app_name.lower()}")

APP_DATA_DIR = get_app_data_dir()
CONFIG_DIR = os.path.join(APP_DATA_DIR, "config")
os.makedirs(CONFIG_DIR, exist_ok=True)

SETTINGS_PATH = os.path.join(CONFIG_DIR, "app_settings.json")



def load_app_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    return {}

def save_app_settings(data):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(data, f, indent=4)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FIXED_SQL_SERVER = "localhost"

class HoverableCard(ctk.CTkFrame):
    def __init__(self, master, normal_color, hover_color, **kwargs):
        super().__init__(master, fg_color=normal_color, **kwargs)
        self.normal_color = normal_color
        self.hover_color = hover_color
        self.bind("<Enter>", lambda e: self.configure(fg_color=self.hover_color))
        self.bind("<Leave>", lambda e: self.configure(fg_color=self.normal_color))

class SettingsUI:
    def __init__(self, parent, colors, main_app):
        self.parent = parent
        self.colors = colors
        self.main_app = main_app

        
        
        # Canvas size MUST come first
        self.canvas_w, self.canvas_h = 480, 360

        # ROI corner points (4 handles)
        self.tl = [0, 0]                     # top-left
        self.tr = [self.canvas_w, 0]         # top-right
        self.bl = [0, self.canvas_h]         # bottom-left
        self.br = [self.canvas_w - 1, self.canvas_h - 1] # bottom-right
        
        self.current_uom_filter = "ALL ITEM"
        self.search_query = ""
        self.roi_active = False
        
        # QR Settings Defaults
        self.qr_prefix_on = ctk.StringVar(value="OFF")
        self.qr_prefix_val = "20"
        self.qr_code_len = 5
        self.qr_price_len = 5
        self.qr_qty_len = 6
        self.qr_currency = "USD"

        self.app_settings = load_app_settings()
        
        self.canvas_w, self.canvas_h = 480, 360
        self.active_handle = None
        self.pt1, self.pt2 = [0,0], [0,0] # Init placeholders
        
        
        self.current_page = 0
        self.history_filter_val = ctk.StringVar(value="LiveNow")
        
        # Sidebar Init
        self.sidebar = ctk.CTkFrame(self.parent, width=180, fg_color=self.colors["OCEAN"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        self.content_area = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.content_area.pack(side="right", fill="both", expand=True)

        self.setup_sidebar()
        self.show_dashboard()

    def setup_sidebar(self):
        # ===== LOGO SECTION =====
        img_logo_path = os.path.join(BASE_DIR, "iLogic.webp")

        logo_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )
        logo_frame.pack(fill="x", pady=(25, 15))

        if os.path.exists(img_logo_path):
            try:
                raw_img = Image.open(img_logo_path)
                logo_ctk = ctk.CTkImage(raw_img, size=(130, 130))
                ctk.CTkLabel(
                    logo_frame,
                    image=logo_ctk,
                    text=""
                ).pack()
            except:
                pass

        ctk.CTkLabel(
            logo_frame,
            font=("Segoe UI", 20, "bold"),
            text_color="white"
        ).pack(pady=(10, 0))

        # ===== DIVIDER =====
        ctk.CTkFrame(
            self.sidebar,
            height=1,
            fg_color="#2a2a2a"
        ).pack(fill="x", padx=20, pady=15)

        # ===== NAVIGATION =====
        nav_items = [
            ("📊  Dashboard", self.show_dashboard),
            ("🛒  View Products", self.show_view_product),
            ("⚖︎  Weight Setting", self.show_weight_setting),
            ("📷  Camera Setting", self.show_camera_settings),
            ("⛶  QR Setting", self.show_qr_settings),
            ("🙎🏻‍♂️  About", self.show_about),
            ("⚙️  Database Setting", self.show_database_setting)
        ]

        for text, cmd in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                anchor="w",
                height=44,                       # ⬅ Bigger button
                font=("Segoe UI", 18),
                fg_color="transparent",
                hover_color=self.colors["NAVY"],
                text_color="white",
                command=cmd
            )
            btn.pack(fill="x", padx=20, pady=4)

        # ===== EXIT BUTTON =====
        ctk.CTkButton(
            self.sidebar,
            text="⏻  Exit",
            height=45,
            font=("Segoe UI", 14, "bold"),
            fg_color=self.colors["CORAL"],
            hover_color="#c0392b",
            command=self.main_app.show_main_view
        ).pack(side="bottom", fill="x", padx=20, pady=25)

    # def setup_sidebar(self):
    #     img_logo_path = os.path.join(BASE_DIR, "iLogic.webp")
    #     if os.path.exists(img_logo_path):
    #         try:
    #             raw_img = Image.open(img_logo_path)
    #             logo_ctk = ctk.CTkImage(raw_img, size=(150, 100))
    #             ctk.CTkLabel(self.sidebar, image=logo_ctk, text="").pack(pady=20)
    #         except:
    #             ctk.CTkLabel(self.sidebar, text="iLogic SETTINGS", font=("Arial", 18, "bold"), text_color="white").pack(pady=20)
    #     else:
    #         ctk.CTkLabel(self.sidebar, text="iLogic SETTINGS", font=("Arial", 18, "bold"), text_color="white").pack(pady=20)

    #     nav_items = [
    #         ("📊 DASHBOARD", self.show_dashboard),
    #         ("🛒 VIEW PRODUCT", self.show_view_product),
    #         ("⚖︎ WEIGHT SETTING", self.show_weight_setting),
    #         ("📷 CAMERA SETTING", self.show_camera_settings),
    #         ("🧹 HISTORY", self.show_history),
    #         ("⛶ QR SETTING", self.show_qr_settings),
    #         ("🙎🏻‍♂️ ABOUT", self.show_about),
    #         ("⚙️ DATABASE SETTING", self.show_database_setting)
    #     ]
    #     for text, cmd in nav_items:
    #         ctk.CTkButton(self.sidebar, text=text, anchor="w", fg_color="transparent", 
    #                       hover_color=self.colors["NAVY"], command=cmd).pack(fill="x", padx=10, pady=2)
    #     ctk.CTkButton(self.sidebar, text="➜] EXIT", fg_color=self.colors["CORAL"], 
    #                   command=self.main_app.show_main_view).pack(side="bottom", fill="x", padx=10, pady=20)

    def clear_content(self):
        self.roi_active = False
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def get_product_image_path(self, description, uom):
        if uom == "KG":
            path = os.path.join(BASE_DIR, "vf_images", f"{description}.webp")
            return path if os.path.exists(path) else None
        elif uom == "PCS":
            path = os.path.join(BASE_DIR, "pcs", f"{description}.jpeg")
            return path if os.path.exists(path) else None
        return None


    def show_database_setting(self):
        self.clear_content()

        ctk.CTkLabel(
            self.content_area,
            text="DATABASE SETTINGS",
            font=("Arial", 22, "bold"),
            text_color="white"
        ).pack(anchor="w", padx=20, pady=15)

        box = ctk.CTkFrame(self.content_area, fg_color=self.colors["OCEAN"], corner_radius=12)
        box.pack(fill="x", padx=20, pady=10)

        cfg_path = os.path.join(BASE_DIR, "config", "db_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
        else:
            cfg_path = os.path.join(BASE_DIR, "config", "db_config.json")

            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    cfg = json.load(f)
            else:
                cfg = {
                    "database": "",
                    "username": "",
                    "password": ""
                }

        self.db_entries = {}

        fields = [
            ("Database Name", "database"),
            ("Username", "username"),
            ("Password", "password")
        ]

        for label, key in fields:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=8)

            ctk.CTkLabel(row, text=label, width=160, anchor="w", text_color="white").pack(side="left")
            ent = ctk.CTkEntry(row, width=300, show="*" if key == "password" else None)
            ent.insert(0, cfg.get(key, ""))
            ent.pack(side="left", padx=10)

            self.db_entries[key] = ent

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.pack(pady=20)

        ctk.CTkButton(btns, text="TEST CONNECTION", fg_color="#457B9D",
                    command=self.test_db_connection).pack(side="left", padx=10)

        ctk.CTkButton(btns, text="SAVE SETTINGS", fg_color="#2ECC71",
                    command=self.save_db_settings).pack(side="left", padx=10)
        
        # --- CAMERA TRAINING RESET (DANGER ZONE) ---
        danger_box = ctk.CTkFrame(
            self.content_area,
            fg_color="#2B0F0F",
            corner_radius=12
        )
        danger_box.pack(fill="x", padx=20, pady=(30, 10))

        ctk.CTkLabel(
            danger_box,
            text="DANGER ZONE",
            font=("Arial", 14, "bold"),
            text_color="#FF6B6B"
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            danger_box,
            text="This will permanently delete all trained camera data",
            text_color="white"
        ).pack(pady=(0, 10))

        ctk.CTkButton(
            danger_box,
            text="🗑️ DELETE CAMERA TRAINING DATA",
            height=40,
            fg_color="#E63946",
            hover_color="#C53030",
            command=self.confirm_clear_camera_data
        ).pack(pady=(0, 15))

    def save_db_settings(self):
        cfg = {
            "driver": "ODBC Driver 17 for SQL Server",  # FIXED
            "server": FIXED_SQL_SERVER,  # FIXED
            "database": self.db_entries["database"].get().strip(),
            "user": self.db_entries["username"].get().strip(),
            "password": self.db_entries["password"].get(),
        }

        ok, msg = db_functions.test_connection(cfg)
        if not ok:
            messagebox.showerror("Connection Failed", msg)
            return

        DB_CONFIG.update(cfg)
        os.makedirs(os.path.join(BASE_DIR, "config"), exist_ok=True)
        with open(os.path.join(BASE_DIR, "config", "db_config.json"), "w") as f:
            json.dump({
                "database": cfg["database"],
                "username": cfg["user"],
                "password": cfg["password"],
            }, f, indent=4)

        messagebox.showinfo("Connected", "Database connected and saved")

        threading.Thread(
            target=self.main_app._load_products_thread,
            daemon=True
        ).start()

    def test_db_connection(self):
        cfg = {
            "driver": "ODBC Driver 17 for SQL Server",
            "server": FIXED_SQL_SERVER,
            "database": self.db_entries["database"].get().strip(),
            "user": self.db_entries["username"].get().strip(),
            "password": self.db_entries["password"].get(),
        }

        ok, msg = db_functions.test_connection(cfg)
        if ok:
            messagebox.showinfo("Success", "SQL Server connected successfully")
        else:
            messagebox.showerror("Failed", msg)

    # --- DASHBOARD LOGIC (LAYOUT: TOP=Table, BOTTOM=Btn, NO INSTRUCTIONS) ---
    def show_dashboard(self):
        self.clear_content()

        # Header
        ctk.CTkLabel(
            self.content_area,
            text="🧠 BRAIN DASHBOARD",
            font=("Segoe UI", 24, "bold"),
            text_color="white"
        ).pack(anchor="w", padx=20, pady=(15, 5))

        # Get trained items
        trained_items = []
        if hasattr(self.main_app, "camera") and hasattr(self.main_app.camera, "get_learned_items"):
            trained_items = self.main_app.camera.get_learned_items()

        ctk.CTkLabel(
            self.content_area,
            text=f"BRAIN LOADED: {len(trained_items)} ITEMS",
            font=("Arial", 16, "bold"),
            text_color="#FFD700"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Search bar
        search_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=5)

        self.brain_search = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search trained item..."
        )
        self.brain_search.pack(side="left", padx=5)

        ctk.CTkButton(
            search_frame,
            text="SEARCH",
            command=self.render_brain_boxes
        ).pack(side="left", padx=5)

        # Scrollable box area
        self.brain_box_area = ctk.CTkScrollableFrame(
            self.content_area,
            fg_color="transparent"
        )
        self.brain_box_area.pack(fill="both", expand=True, padx=20, pady=10)

        # Training button
        ctk.CTkButton(
            self.content_area,
            text="➕ TRAIN NEW ITEM",
            font=("Arial", 18, "bold"),
            fg_color="#FFD700",
            text_color="black",
            hover_color="#E5C100",
            height=60,
            command=self.open_training_popup
        ).pack(pady=20)

        self.render_brain_boxes()

    def render_brain_boxes(self):
        for w in self.brain_box_area.winfo_children():
            w.destroy()

        query = self.dashboard_search.get().upper() if hasattr(self, "dashboard_search") else ""

        items = []
        if hasattr(self.main_app.camera, "get_learned_items"):
            items = self.main_app.camera.get_learned_items()

        if query:
            items = [i for i in items if query in str(i.get("Code", "")).upper()]

        # Grid setup
        for i in range(4):
            self.brain_box_area.grid_columnconfigure(i, weight=1)

        for idx, item in enumerate(items):
            card = HoverableCard(
                self.brain_box_area,
                normal_color=self.colors["OCEAN"],
                hover_color="#2A456E",
                corner_radius=12
            )
            card.grid(row=idx // 4, column=idx % 4, padx=10, pady=10, sticky="nsew")

            code = item.get("Code", "N/A")
            uom = item.get("UOM", "-")

            ctk.CTkLabel(card, text="🧠", font=("Arial", 28)).pack(pady=(10, 0))
            ctk.CTkLabel(card, text=f"CODE: {code}", font=("Arial", 13, "bold"), text_color="#FFD700").pack()
            ctk.CTkLabel(card, text=f"UOM: {uom}", text_color="white").pack(pady=(0, 5))

            ctk.CTkButton(
                card,
                text="FORGET",
                fg_color="#E63946",
                hover_color="#C53030",
                command=lambda c=code: self.main_app.camera.forget_item(c)
            ).pack(pady=(5, 10))

    def open_training_popup(self):
        """Pop up for Taking Picture or Inserting Picture"""
        t = ctk.CTkToplevel(self.parent)
        t.title("Select Action")
        t.geometry("400x300")
        t.attributes("-topmost", True)
        
        ctk.CTkLabel(t, text="CHOOSE ACTION", font=("Arial", 20, "bold")).pack(pady=20)
        # 1. Take Picture
        ctk.CTkButton(t, text="📸 TAKE PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#2ECC71",
                      command=lambda: [t.destroy(), self.open_camera_capture()]).pack(pady=10)
        # 2. Insert Picture
        ctk.CTkButton(t, text="📂 INSERT PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#457B9D",
                      command=lambda: [t.destroy(), self.upload_picture()]).pack(pady=10)
        ctk.CTkButton(t, text="CANCEL", width=280, fg_color=self.colors["CORAL"], command=t.destroy).pack(pady=20)

    # --- FUNCTION 1: CAPTURE FROM CAMERA ---
    def open_camera_capture(self):
        p = tk.Toplevel(self.parent)
        p.geometry("500x600"); p.title("Camera Capture"); p.configure(bg="black")
        lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        roi_cfg = os.path.join(BASE_DIR, "camera_roi_config.txt")

        roi = None
        if os.path.exists(roi_cfg):
            try:
                with open(roi_cfg, "r") as f:
                    roi = tuple(map(int, f.read().strip().split(",")))
            except:
                roi = None
        if roi and hasattr(self.main_app, "camera"):
            self.main_app.camera.roi_color_size = roi

        def update_stream():
            if not p.winfo_exists():
                cap.release(); return
            # ret, frame = cap.read()
            # if ret:
            #     rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
            
            ret, frame = cap.read()
            if ret:
                if roi:
                    pts = np.array(list(zip(roi[0::2], roi[1::2])), dtype=np.int32)
                    cv2.polylines(frame, [pts], isClosed=True, color=(0,255,0), thickness=2)

                rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))

                img = ImageTk.PhotoImage(Image.fromarray(rgb))
                lbl_video.configure(image=img); lbl_video.image = img
            p.after(20, update_stream)
        def snap_photo():
            # ret, frame = cap.read()
            # if ret:
            #     cap.release(); p.destroy(); self.show_save_form(frame)
            ret, frame = cap.read()
            if ret:
                if roi:
                    xs = roi[0::2]
                    ys = roi[1::2]
                    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                    pts = np.array(list(zip(roi[0::2], roi[1::2])), dtype=np.int32)

                    cv2.fillPoly(mask, [pts], 255)
                    result = cv2.bitwise_and(frame, frame, mask=mask)

                    x,y,w,h = cv2.boundingRect(pts)
                    frame = result[y:y+h, x:x+w]


                cap.release()
                p.destroy()
                self.show_save_form(frame)

        ctk.CTkButton(p, text="SNAP", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
        update_stream()

    # --- FUNCTION 2: UPLOAD FROM FILE ---
    def upload_picture(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp")])
        if file_path:
            img = cv2.imread(file_path)
            if img is not None: self.show_save_form(img)

    def show_save_form(self, image_data):
        self.clear_content()
        sc = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"]); sc.pack(fill="both", expand=True, padx=20, pady=10)
        rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB); h, w = rgb.shape[:2]; ratio = 250 / h
        rgb = cv2.resize(rgb, (int(w*ratio), 250)); prev_img = ctk.CTkImage(Image.fromarray(rgb), size=(int(w*ratio), 250))
        ctk.CTkLabel(sc, image=prev_img, text="").pack(pady=10)
        existing_codes = [int(i['Code']) for i in self.main_app.all_products if str(i['Code']).isdigit()]
        next_code = str(max(existing_codes) + 1) if existing_codes else "1001"
        form_fields = [("InventoryCode", next_code), ("Description", ""), ("Barcode", ""), ("UOM", "KG"), ("RetailPrice", "0.00"), ("BrandCode", "001")]
        entries = {}
        for idx, (lbl, default_val) in enumerate(form_fields):
            ctk.CTkLabel(sc, text=lbl, text_color="white").pack(anchor="w", padx=20, pady=(5,0))
            e = ctk.CTkEntry(sc, width=400); e.insert(0, default_val); e.pack(padx=20, pady=(0,10)); entries[lbl] = e
        def commit_save():
            d = {
                "InventoryCode": entries["InventoryCode"].get(), "Description": entries["Description"].get(), "Barcode": entries["Barcode"].get(), 
                "UOM": entries["UOM"].get().upper(), "RetailPrice": float(entries["RetailPrice"].get() or 0), "BrandCode": entries["BrandCode"].get(), 
                "CreateDate": datetime.now().strftime("%Y-%m-%d"), "InActive": 0
            }
            if db_functions.insert_inventory(d) == "SUCCESS":
                fname = f"{d['Description']}.webp" if d["UOM"]=="KG" else f"{d['Description']}.jpeg"
                save_dir = "vf_images" if d["UOM"]=="KG" else "pcs"
                save_path = os.path.join(BASE_DIR, save_dir, fname)
                cv2.imwrite(save_path, image_data)
                
                # --- FIX: SAFE RELOAD WITHOUT CRASHING ---
                # 1. Reload DB Products (Safe)
                if hasattr(self.main_app, "_load_products_thread"):
                    threading.Thread(target=self.main_app._load_products_thread, daemon=True).start()
                
                # 2. Attempt to Reload Camera (Safe Check)
                if hasattr(self.main_app, "camera"):
                    # Check for common method names since 'refresh_db' is missing
                    if hasattr(self.main_app.camera, "load_data"):
                        threading.Thread(target=self.main_app.camera.load_data, daemon=True).start()
                    elif hasattr(self.main_app.camera, "load_features"):
                        threading.Thread(target=self.main_app.camera.load_features, daemon=True).start()
                    # If no method found, skip silently to prevent crash

                time.sleep(0.5) 
                self.show_dashboard() 

                messagebox.showinfo("Success", "Product Saved & System Refreshed!")
            else: messagebox.showerror("Error", "DB Insert Failed")
        ctk.CTkButton(sc, text="SAVE PRODUCT", height=45, fg_color="#2ECC71", command=commit_save).pack(pady=20)
        ctk.CTkButton(sc, text="CANCEL", height=30, fg_color="gray", command=self.show_dashboard).pack(pady=5)

    # def update_scale_logic(self, _=None):
    #     try:
    #         new_port = self.opt_com.get()
    #         new_baud = int(self.opt_baud.get())
    #         new_protocol = self.opt_protocol.get()

    #         # ✅ Save to persistent settings ONLY
    #         self.app_settings.setdefault("weight", {}).update({
    #             "port": new_port,
    #             "baud": new_baud,
    #             "protocol": new_protocol
    #         })
    #         save_app_settings(self.app_settings)

    #         messagebox.showinfo(
    #             "Saved",
    #             "Scale settings saved successfully.\nRestart the application to apply changes."
    #         )

    #     except Exception as e:
    #         messagebox.showerror("Scale Error", str(e))


    def update_scale_logic(self, _=None):
        try:
            new_port = self.opt_com.get()
            new_baud = int(self.opt_baud.get())
            new_protocol = self.opt_protocol.get()  # stored only, not used here

            # 1️⃣ Save settings
            self.app_settings.setdefault("weight", {}).update({
                "port": new_port,
                "baud": new_baud,
                "protocol": new_protocol
            })
            save_app_settings(self.app_settings)

            # 2️⃣ LIVE update scale (NO restart, NO new thread)
            if hasattr(self.main_app, "scale") and self.main_app.scale:
                self.main_app.scale.update_config(
                    port=new_port,
                    baudrate=new_baud
                )

        except Exception as e:
            messagebox.showerror("Scale Error", str(e))

    def show_weight_setting(self):
        self.clear_content()
        scroll = ctk.CTkScrollableFrame(
            self.content_area, fg_color="transparent"
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(
            scroll, text="DEVICE SETTING",
            font=("Arial", 22, "bold"),
            text_color="white"
        ).pack(anchor="w", pady=10)

        box1 = ctk.CTkFrame(
            scroll, fg_color=self.colors["OCEAN"], corner_radius=12
        )
        box1.pack(fill="x", pady=5)

        # ================= SCALE SETTINGS =================

        # 🔹 Load persisted weight settings
        wt = self.app_settings.get("weight", {})

        saved_port = wt.get("port", "COM1")
        saved_baud = str(wt.get("baud", "9600"))
        saved_protocol = wt.get("protocol", "RS232")

        # ---------- Protocol ----------
        f1 = ctk.CTkFrame(box1, fg_color="transparent")
        f1.pack(pady=10, padx=15, fill="x")

        ctk.CTkLabel(
            f1, text="Scale Setting:",
            width=140, anchor="w",
            text_color="white"
        ).pack(side="left")

        self.opt_protocol = ctk.CTkOptionMenu(
            f1, values=["RS232", "RS249"],
            command=self.update_scale_logic
        )
        self.opt_protocol.set(saved_protocol)
        self.opt_protocol.pack(side="left", padx=20)

        # ---------- COM Port ----------
        f2 = ctk.CTkFrame(box1, fg_color="transparent")
        f2.pack(pady=10, padx=15, fill="x")

        ctk.CTkLabel(
            f2, text="Serial Port Setting:",
            width=140, anchor="w",
            text_color="white"
        ).pack(side="left")

        self.opt_com = ctk.CTkOptionMenu(
            f2,
            values=[f"COM{i}" for i in range(1, 11)],
            command=self.update_scale_logic
        )
        self.opt_com.set(saved_port)
        self.opt_com.pack(side="left", padx=20)

        # ---------- Baud Rate ----------
        f3 = ctk.CTkFrame(box1, fg_color="transparent")
        f3.pack(pady=10, padx=15, fill="x")

        ctk.CTkLabel(
            f3, text="Baud Rate Setting:",
            width=140, anchor="w",
            text_color="white"
        ).pack(side="left")

        self.opt_baud = ctk.CTkOptionMenu(
            f3,
            values=["1200","2400","4800","9600","19200","38400","115200"],
            command=self.update_scale_logic
        )
        self.opt_baud.set(saved_baud)
        self.opt_baud.pack(side="left", padx=20)

        # ================= UNIT SETTINGS =================

        ctk.CTkLabel(
            scroll, text="UNIT SETTING",
            font=("Arial", 22, "bold"),
            text_color="white"
        ).pack(anchor="w", pady=(25, 10))

        box2 = ctk.CTkFrame(
            scroll, fg_color=self.colors["OCEAN"], corner_radius=12
        )
        box2.pack(fill="x", pady=5)

        f_u = ctk.CTkFrame(box2, fg_color="transparent")
        f_u.pack(pady=20, padx=15, fill="x")

        ctk.CTkLabel(
            f_u, text="Print Unit Setting (Ratio):",
            width=180, anchor="w",
            text_color="white"
        ).pack(side="left")

        ctk.CTkOptionMenu(
            f_u, values=["KG", "Pound", "Viss", "Gram", "15kg", "30kg"]
        ).pack(side="left", padx=20)

    def show_view_product(self):
        self.clear_content()
        self.current_uom_filter = "ALL ITEM"; self.search_query = ""; self.current_page = 0
        ctk.CTkLabel(self.content_area, text="PRODUCT INVENTORY", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
        f_bar = ctk.CTkFrame(self.content_area, fg_color="transparent"); f_bar.pack(fill="x", padx=15, pady=5)
        self.uom_selector = ctk.CTkSegmentedButton(f_bar, values=["ALL ITEM", "KG", "PCS"], command=self.filter_by_uom)
        self.uom_selector.set(self.current_uom_filter); self.uom_selector.pack(side="left")
        self.search_entry = ctk.CTkEntry(f_bar, placeholder_text="Code or Name...", width=140); self.search_entry.pack(side="left", padx=15)
        ctk.CTkButton(f_bar, text="SEARCH", width=70, command=self.apply_search).pack(side="left")
        self.grid_container = ctk.CTkFrame(self.content_area, fg_color="transparent"); self.grid_container.pack(fill="both", expand=True, padx=15)
        pg = ctk.CTkFrame(self.content_area, fg_color="transparent", height=40); pg.pack(fill="x", side="bottom", pady=10)
        ctk.CTkButton(pg, text="<< PREV", width=100, command=self.prev_page, fg_color=self.colors["OCEAN"]).pack(side="left", padx=40)
        self.lbl_page = ctk.CTkLabel(pg, text="PAGE 1", font=("Arial", 12, "bold"), text_color="white"); self.lbl_page.pack(side="left", expand=True)
        ctk.CTkButton(pg, text="NEXT >>", width=100, command=self.next_page, fg_color=self.colors["OCEAN"]).pack(side="right", padx=40)
        self.render_grid()

    def apply_search(self): 
        self.search_query = self.search_entry.get().upper()
        self.current_page = 0
        self.render_grid()

    def filter_by_uom(self, v): self.current_uom_filter = v; self.current_page = 0; self.render_grid()
    
    def next_page(self):
        items = [i for i in self.main_app.all_products if (self.current_uom_filter == "ALL ITEM" or i['UOM'] == self.current_uom_filter)]
        if self.search_query: 
            items = [i for i in items if self.search_query in str(i['Code']).upper() or self.search_query in str(i['Name']).upper()]
        if self.current_page < max(1, (len(items)+9)//10) - 1: self.current_page += 1; self.render_grid()
    
    def prev_page(self):
        if self.current_page > 0: self.current_page -= 1; self.render_grid()
    
    def render_grid(self):
        for w in self.grid_container.winfo_children(): w.destroy()
        # Responsive grid setup
        for i in range(5): self.grid_container.grid_columnconfigure(i, weight=1)
        
        items = [i for i in self.main_app.all_products if (self.current_uom_filter == "ALL ITEM" or i['UOM'] == self.current_uom_filter)]
        
        # --- MODIFIED SEARCH LOGIC: CODE OR DESCRIPTION ---
        if self.search_query: 
            items = [i for i in items if self.search_query in str(i['Code']).upper() or self.search_query in str(i['Name']).upper()]
            
        start = self.current_page * 10
        self.lbl_page.configure(text=f"PAGE {self.current_page + 1} OF {max(1, (len(items)+9)//10)}")
        
        for i, item in enumerate(items[start:start+10]):
            card = HoverableCard(self.grid_container, normal_color=self.colors["OCEAN"], hover_color="#2A456E", corner_radius=10)
            card.grid(row=i//5, column=i%5, padx=8, pady=8, sticky="nsew") # Responsive sticky
            path = self.get_product_image_path(item['Name'], item['UOM'])
            if path:
                try: 
                    img = ctk.CTkImage(Image.open(path), size=(100, 80)); 
                    lbl=ctk.CTkLabel(card, image=img, text=""); lbl.image=img; lbl.pack(pady=(10,5))
                except: ctk.CTkLabel(card, text="IMG ERR", text_color="red").pack(pady=20)
            else: ctk.CTkLabel(card, text="🖼️", font=("Arial",12)).pack(pady=15)
            ctk.CTkLabel(card, text=item['Code'], font=("Arial",12,"bold"), text_color="#FFD700").pack()
            ctk.CTkLabel(card, text=(item['Name'][:13]+".." if len(item['Name'])>15 else item['Name']), font=("Arial",11), text_color="white").pack()
            
            # --- MODIFIED: EDIT BUTTON INSTEAD OF SELECT ---
            ctk.CTkButton(
                card,
                text="EDIT IMAGE",
                fg_color="#F39C12", # Orange for edit
                hover_color="#D68910",
                height=35, # Bigger
                width=140, # Bigger
                font=("Arial", 12, "bold"),
                command=lambda i=item: self.open_edit_image_popup(i)
            ).pack(pady=(10, 10))

    def open_edit_image_popup(self, item):
        """ Pop up to Edit Image (Take New or Upload New) """
        t = ctk.CTkToplevel(self.parent)
        t.title("Edit Product Image")
        t.geometry("400x320")
        t.attributes("-topmost", True)
        
        ctk.CTkLabel(t, text=f"EDIT IMAGE: {item['Name']}", font=("Arial", 16, "bold")).pack(pady=15)
        
        # 1. Take Picture
        ctk.CTkButton(t, text="📸 TAKE NEW PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#2ECC71",
                      command=lambda: [t.destroy(), self.edit_camera_capture(item)]).pack(pady=10)
        # 2. Insert Picture
        ctk.CTkButton(t, text="📂 UPLOAD NEW PICTURE", height=50, width=280, font=("Arial", 14, "bold"), fg_color="#457B9D",
                      command=lambda: [t.destroy(), self.edit_upload_picture(item)]).pack(pady=10)
        
        ctk.CTkButton(t, text="CANCEL", width=280, fg_color=self.colors["CORAL"], command=t.destroy).pack(pady=20)

    def edit_camera_capture(self, item):
        p = tk.Toplevel(self.parent)
        p.geometry("500x600"); p.title(f"Snap: {item['Name']}"); p.configure(bg="black")
        lbl_video = tk.Label(p, bg="black"); lbl_video.pack(pady=10)
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        def update_stream():
            if not p.winfo_exists(): cap.release(); return
            ret, frame = cap.read()
            if ret:
                rgb = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (480, 360))
                img = ImageTk.PhotoImage(Image.fromarray(rgb))
                lbl_video.configure(image=img); lbl_video.image = img
            p.after(20, update_stream)
        def snap_photo():
            ret, frame = cap.read()
            if ret:
                cap.release(); p.destroy(); self.save_edited_image(item, frame)
        ctk.CTkButton(p, text="SNAP & SAVE", height=40, fg_color="#2ECC71", command=snap_photo).pack(pady=20)
        update_stream()

    def edit_upload_picture(self, item):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.webp")])
        if file_path:
            img = cv2.imread(file_path)
            if img is not None: self.save_edited_image(item, img)

    def save_edited_image(self, item, image_data):
        # Determine path based on item details
        uom = item.get('UOM', 'KG')
        name = item.get('Name', 'Unknown')
        
        folder = "vf_images" if uom == "KG" else "pcs"
        ext = ".webp" if uom == "KG" else ".jpeg"
        
        # Ensure directory exists
        save_dir = os.path.join(BASE_DIR, folder)
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        
        save_path = os.path.join(save_dir, f"{name}{ext}")
        
        try:
            cv2.imwrite(save_path, image_data)
            
            # --- FIX: SAFE RELOAD WITHOUT CRASHING ---
            # 1. Reload DB Products
            if hasattr(self.main_app, "_load_products_thread"):
                threading.Thread(target=self.main_app._load_products_thread, daemon=True).start()
            
            # 2. Attempt to Reload Camera (Safe Check)
            if hasattr(self.main_app, "camera"):
                 # Check for common method names since 'refresh_db' is missing
                 if hasattr(self.main_app.camera, "load_data"):
                     threading.Thread(target=self.main_app.camera.load_data, daemon=True).start()
                 elif hasattr(self.main_app.camera, "load_features"):
                     threading.Thread(target=self.main_app.camera.load_features, daemon=True).start()

            time.sleep(0.3)
            self.render_grid() # Refresh grid in View Product
            
            messagebox.showinfo("Success", "Product image updated successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {e}")

    # --- SHOW CAMERA SETTINGS (With ROI) ---

    # def show_camera_settings(self):
    #     self.clear_content()
    #     scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
    #     scroll.pack(fill="both", expand=True, padx=15)

    #     ctk.CTkLabel(scroll, text="VISION BOUNDARY CONFIGURATION", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
    #     ctk.CTkLabel(scroll, text="DRAG CIRCLES TO ADJUST", font=("Arial", 12), text_color="yellow").pack()

    #     self.roi_canvas = tk.Canvas(scroll, width=self.canvas_w, height=self.canvas_h, bg="black", highlightthickness=0)
    #     self.roi_canvas.pack(pady=10)

    #     # --- Full camera ROI (4 corner handles) ---
    #     self.tl = [0, 0]
    #     self.tr = [self.canvas_w, 0]
    #     self.bl = [0, self.canvas_h]
    #     self.br = [self.canvas_w, self.canvas_h]

    #     # 🔹 Load ROI from persistent settings
    #     cam_cfg = self.app_settings.get("camera", {})
    #     cx, cy, cw, ch = cam_cfg.get("roi", [0, 0, 640, 480])

    #     # Apply to camera object
    #     try:
    #         self.main_app.camera.roi = (int(cx), int(cy), int(cw), int(ch))
    #     except Exception:
    #         pass

    #     # Scale ROI to canvas coords
    #     sx, sy = self.canvas_w / 640.0, self.canvas_h / 480.0
    #     self.pt1, self.pt2 = [cx * sx, cy * sy], [(cx + cw) * sx, (cy + ch) * sy]

    #     # Update corner handles
    #     self.tl = [self.pt1[0], self.pt1[1]]
    #     self.tr = [self.pt2[0], self.pt1[1]]
    #     self.bl = [self.pt1[0], self.pt2[1]]
    #     self.br = [self.pt2[0], self.pt2[1]]

    #     # Bind drag events
    #     self.roi_canvas.bind("<Button-1>", self.on_roi_press)
    #     self.roi_canvas.bind("<B1-Motion>", self.on_roi_drag)

    #     # Save button
    #     ctk.CTkButton(scroll, text="SAVE VISION BOUNDARY", fg_color="#2ECC71", height=100, command=self.save_roi).pack(pady=10)

    #     self.roi_active = True
    #     self.update_roi_preview()
    
    def show_camera_settings(self):
        self.clear_content()
        scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15)

        ctk.CTkLabel(scroll, text="VISION BOUNDARY CONFIGURATION", font=("Arial", 22, "bold"), text_color="white").pack(pady=10)
        ctk.CTkLabel(scroll, text="DRAG CIRCLES TO ADJUST", font=("Arial", 12), text_color="yellow").pack()

        self.roi_canvas = tk.Canvas(scroll, width=self.canvas_w, height=self.canvas_h, bg="black", highlightthickness=0)
        self.roi_canvas.pack(pady=10)

        # FULL camera ROI (4 corner handles)
        self.tl = [0, 0]
        self.tr = [self.canvas_w, 0]
        self.bl = [0, self.canvas_h]
        self.br = [self.canvas_w, self.canvas_h]

        roi_cfg = os.path.join(BASE_DIR, "camera_roi_config.txt")
        if os.path.exists(roi_cfg):
            try:
                with open(roi_cfg, "r") as f:
                    v = list(map(int, f.read().strip().split(",")))
                    if len(v) == 8:
                        self.tl = [v[0], v[1]]
                        self.tr = [v[2], v[3]]
                        self.br = [v[4], v[5]]
                        self.bl = [v[6], v[7]]
            except Exception as e:
                print("ROI load error:", e)

        # # 🔥 IMPORTANT: Update corner handles from pt1/pt2
        # self.tl = [self.pt1[0], self.pt1[1]]
        # self.tr = [self.pt2[0], self.pt1[1]]
        # self.bl = [self.pt1[0], self.pt2[1]]
        # self.br = [self.pt2[0], self.pt2[1]]

        self.roi_canvas.bind("<Button-1>", self.on_roi_press)
        self.roi_canvas.bind("<B1-Motion>", self.on_roi_drag)

        ctk.CTkButton(scroll, text="SAVE VISION BOUNDARY", fg_color="#2ECC71",text_color="black",height=40, command=self.save_roi).pack(pady=10)

        self.roi_active=True
        self.update_roi_preview()



    def on_roi_press(self, e):
        self.drag_start = (e.x, e.y)
        self.active_handle = None

        r = 10  # handle hit radius

        def hit(p):
            return abs(e.x - p[0]) <= r and abs(e.y - p[1]) <= r

        # Corner resize
        if hit(self.tl):
            self.active_handle = "tl"
        elif hit(self.tr):
            self.active_handle = "tr"
        elif hit(self.bl):
            self.active_handle = "bl"
        elif hit(self.br):
            self.active_handle = "br"

        # Move whole ROI (clicked inside rectangle)
        elif self.tl[0] < e.x < self.br[0] and self.tl[1] < e.y < self.br[1]:
            self.active_handle = "move"


        
    # def on_roi_drag(self, e):
    #     if self.active_handle=="pt1": self.pt1 = [max(0,min(e.x, self.pt2[0]-10)), max(0,min(e.y, self.pt2[1]-10))]
    #     elif self.active_handle=="pt2": self.pt2 = [max(self.pt1[0]+10,min(e.x, self.canvas_w)), max(self.pt1[1]+10,min(e.y, self.canvas_h))]
    
    def on_roi_drag(self, e):
        if not self.active_handle:
            return

        x = max(0, min(e.x, self.canvas_w))
        y = max(0, min(e.y, self.canvas_h))

        dx = x - self.drag_start[0]
        dy = y - self.drag_start[1]

        if self.active_handle == "move":
            for p in (self.tl, self.tr, self.br, self.bl):
                p[0] += dx
                p[1] += dy
            self.drag_start = (x, y)
            return

        if self.active_handle == "tl":
            self.tl = [x, y]
        elif self.active_handle == "tr":
            self.tr = [x, y]
        elif self.active_handle == "br":
            self.br = [x, y]
        elif self.active_handle == "bl":
            self.bl = [x, y]

        self.drag_start = (x, y)

    
    def update_roi_preview(self):
        if not self.roi_active or not self.roi_canvas.winfo_exists():
            return

        fr = self.main_app.camera.get_frame(draw_box=False)

        if fr is not None:
            # Crop center area (same as your existing logic)
            # fr = fr[
            #     int(fr.shape[0] * 0.2):int(fr.shape[0] * 0.8),
            #     int(fr.shape[1] * 0.2):int(fr.shape[1] * 0.8)
            # ]

            try:
                prev = cv2.resize(fr, (self.canvas_w, self.canvas_h))
                img_tk = ImageTk.PhotoImage(
                    Image.fromarray(cv2.cvtColor(prev, cv2.COLOR_BGR2RGB))
                )

                self.roi_canvas.delete("all")
                self.roi_canvas.create_image(0, 0, anchor="nw", image=img_tk)
                self.roi_canvas.image = img_tk
                
                # Ensure BR is inside canvas (clickable)
                self.br[0] = min(self.br[0], self.canvas_w - 1)
                self.br[1] = min(self.br[1], self.canvas_h - 1)

                self.roi_canvas.create_polygon(
                    self.tl[0], self.tl[1],
                    self.tr[0], self.tr[1],
                    self.br[0], self.br[1],
                    self.bl[0], self.bl[1],
                    outline="#00FF00",
                    width=2,
                    fill=""
                )


                # Draw 4 red corner handles
                for p in (self.tl, self.tr, self.bl, self.br):
                    self.roi_canvas.create_oval(
                        p[0] - 8, p[1] - 8,
                        p[0] + 8, p[1] + 8,
                        fill="red",
                        outline="white"
                    )

            except Exception as e:
                print("ROI preview error:", e)

        if self.roi_active:
            self.parent.after(40, self.update_roi_preview)

    # def save_roi(self):
    #     if not self.roi_active:
    #         return

    #     # Convert canvas coords back to camera coords
    #     sx, sy = self.canvas_w / 640.0, self.canvas_h / 480.0
    #     cx = int(max(0, min(640, round(self.pt1[0] / sx))))
    #     cy = int(max(0, min(480, round(self.pt1[1] / sy))))
    #     cw = int(max(1, min(640, round((self.pt2[0] - self.pt1[0]) / sx))))
    #     ch = int(max(1, min(480, round((self.pt2[1] - self.pt1[1]) / sy))))

    #     # Update camera object
    #     try:
    #         self.main_app.camera.roi = (cx, cy, cw, ch)
    #     except Exception:
    #         pass

    #     # Save to app_settings.json
    #     self.app_settings.setdefault("camera", {})["roi"] = [cx, cy, cw, ch]
    #     save_app_settings(self.app_settings)

    #     # Show confirmation
    #     msg = ctk.CTkLabel(self.content_area, text="✅ Vision boundary saved!", text_color="#2ECC71", font=("Arial", 14, "bold"))
    #     msg.pack(pady=8)
    #     self.parent.after(2000, lambda: msg.destroy())


    def save_roi(self):
        pts = [
            int(self.tl[0]), int(self.tl[1]),
            int(self.tr[0]), int(self.tr[1]),
            int(self.br[0]), int(self.br[1]),
            int(self.bl[0]), int(self.bl[1]),
        ]

        with open(os.path.join(BASE_DIR, "camera_roi_config.txt"), "w") as f:
            f.write(",".join(map(str, pts)))

        messagebox.showinfo("Saved", "Vision boundary saved.")



    def confirm_clear_camera_data(self):
        popup = ctk.CTkToplevel(self.parent)
        popup.title("ADMIN VERIFICATION")
        popup.geometry("340x230")
        popup.grab_set()
        popup.attributes("-topmost", True)

        ctk.CTkLabel(
            popup,
            text="ADMIN PASSWORD REQUIRED",
            font=("Arial", 15, "bold"),
            text_color="red"
        ).pack(pady=20)

        pwd_entry = ctk.CTkEntry(
            popup,
            width=220,
            show="*"
        )
        pwd_entry.pack(pady=10)

        def verify_and_delete():
            password = pwd_entry.get().strip()

            if not password:
                messagebox.showwarning("Missing", "Please enter password")
                return

            if not db_functions.validate_admin_password(password):
                messagebox.showerror(
                    "ACCESS DENIED",
                    "Invalid ADMIN password"
                )
                return

            popup.destroy()

            if hasattr(self.main_app, "camera") and self.main_app.camera:
                ok = self.main_app.camera.clear_learned_data()
                if ok:
                    messagebox.showinfo(
                        "SUCCESS",
                        "Camera training JSON data deleted successfully"
                    )
                else:
                    messagebox.showerror(
                        "ERROR",
                        "Failed to delete training data"
                    )
            else:
                messagebox.showerror(
                    "ERROR",
                    "Camera module not initialized"
                )

        ctk.CTkButton(
            popup,
            text="CONFIRM DELETE",
            fg_color="#E63946",
            height=40,
            command=verify_and_delete
        ).pack(pady=20)

        ctk.CTkButton(
            popup,
            text="CANCEL",
            fg_color="gray",
            command=popup.destroy
        ).pack()

    def clear_learned_data(self):
        try:
            if not os.path.exists(self.training_data_dir):
                return True

            for f in os.listdir(self.training_data_dir):
                if f.endswith(".json"):
                    os.remove(os.path.join(self.training_data_dir, f))

            return True
        except Exception as e:
            print("Delete error:", e)
            return False

    # --- SHOW HISTORY (Split 2 Grids) ---
    def show_history(self):
        self.clear_content()

        # ================================
        # GRID 1: MAIN WINDOW ACTIVE ITEM
        # ================================
        
        ctk.CTkLabel(self.content_area, text="CURRENT SELECTION (FROM MAIN WINDOW)", font=("Arial", 18, "bold"), text_color="#FFD700").pack(anchor="w", padx=20, pady=(15, 5))
        
        # Grid 1 container (Scrollable, smaller height)
        self.selection_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"], height=120)
        self.selection_scroll.pack(fill="x", padx=20, pady=5)
        
        # Headers for Top Grid
        top_headers = ["BARCODE / QR", "DATE", "TIME", "DESCRIPTION", "UOM"]
        for col, h in enumerate(top_headers):
            ctk.CTkLabel(self.selection_scroll, text=h, font=("Arial", 12, "bold"), text_color="#FFD700").grid(row=0, column=col, padx=15, pady=8, sticky="w")
        
        sep = ctk.CTkFrame(self.selection_scroll, height=2, fg_color="white")
        sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 5))

        # Check Active Selection from Main App
        active_item = self.main_app.active_selection
        if active_item:
            # Grab details
            # Barcode: stored in main app label (generated string)
            barcode = "N/A"
            if hasattr(self.main_app, 'lbl_qr_string'):
                barcode = self.main_app.lbl_qr_string.cget("text")
            
            description = active_item.get("Name", "Unknown")
            uom = active_item.get("UOM", "-")
            
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            row_data = [barcode, date_str, time_str, description, uom]
            for c, v in enumerate(row_data):
                ctk.CTkLabel(self.selection_scroll, text=str(v), text_color="white", font=("Arial", 11)).grid(row=2, column=c, padx=15, pady=4, sticky="w")
        else:
             ctk.CTkLabel(self.selection_scroll, text="No item currently selected in main window.", text_color="silver").grid(row=2, column=0, columnspan=5, pady=20)


        # ================================
        # GRID 2: TRAINING DATA HISTORY
        # ================================

        # Header + Filter Frame for History
        top_bar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(top_bar, text="TRAINING HISTORY", font=("Arial", 20, "bold"), text_color="white").pack(side="left")
        
        # Filter Logic
        filter_box = ctk.CTkOptionMenu(top_bar, values=["LiveNow", "Yesterday", "Last Week"], variable=self.history_filter_val, 
                                       command=lambda v: self.render_history_table(), width=130)
        filter_box.pack(side="right")
        ctk.CTkLabel(top_bar, text="Filter By:", text_color="silver").pack(side="right", padx=10)
        
        # Table Container (Scrollable)
        self.history_scroll = ctk.CTkScrollableFrame(self.content_area, fg_color=self.colors["OCEAN"])
        self.history_scroll.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.render_history_table()

    def render_history_table(self):
        # Clear current
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
            
        # Headers
        headers = ["DATE", "TIME", "CODE", "UOM", "QTY / WEIGHT"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(self.history_scroll, text=h, font=("Arial", 12, "bold"), text_color="#FFD700").grid(row=0, column=col, padx=15, pady=8, sticky="w")
        
        # Add a Separator
        sep = ctk.CTkFrame(self.history_scroll, height=2, fg_color="white")
        sep.grid(row=1, column=0, columnspan=5, sticky="ew", padx=10, pady=(0, 5))

        # Get Raw Data from Main Logger (permanent storage)
        raw_history = history_logger.get_history() # Expected list of dicts: date, time, code, uom, qty
        
        # Apply Date Filter
        filtered_data = []
        filter_mode = self.history_filter_val.get()
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        yest_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        week_cutoff = (now - timedelta(days=7))

        for item in raw_history:
            # Assume item['date'] is YYYY-MM-DD
            d_str = item.get('date', "")
            
            include = False
            if filter_mode == "LiveNow":
                if d_str == today_str: include = True
            elif filter_mode == "Yesterday":
                if d_str == yest_str: include = True
            elif filter_mode == "Last Week":
                try:
                    d_obj = datetime.strptime(d_str, "%Y-%m-%d")
                    if d_obj >= week_cutoff: include = True
                except: pass
            
            if include:
                filtered_data.append(item)
        
        # Sort desc (latest first) if not already
        # Render Rows
        if not filtered_data:
            ctk.CTkLabel(self.history_scroll, text="No records found for selected period.", text_color="silver").grid(row=2, column=0, columnspan=5, pady=20)
        else:
            for r, row_data in enumerate(filtered_data, 2):
                vals = [row_data.get('date'), row_data.get('time'), row_data.get('code'), row_data.get('uom'), row_data.get('qty')]
                bg = "#1F2B3E" if r % 2 == 0 else "transparent" # Striped rows optional, simple transparent here
                
                for c, v in enumerate(vals):
                    ctk.CTkLabel(self.history_scroll, text=str(v), text_color="white", font=("Arial", 11)).grid(row=r, column=c, padx=15, pady=4, sticky="w")

    # --- SHOW QR SETTINGS (With Live Preview) ---
    def update_qr_preview_logic(self, _=None):
        self.app_settings.setdefault("qr", {}).update({
            "prefix_enabled": self.qr_prefix_on.get() == "ON",
            "prefix_value": self.opt_prefix_val.get(),
            "code_len": int(self.opt_code_digit.get()),
            "price_len": int(self.opt_price_digit.get()),
            "qty_len": int(self.opt_qty_digit.get())
        })
        save_app_settings(self.app_settings)
        prefix = self.opt_prefix_val.get() if self.qr_prefix_on.get() == "ON" else ""
        icode = "03451".zfill(int(self.opt_code_digit.get()))[:int(self.opt_code_digit.get())]
        iprice = "00024".zfill(int(self.opt_price_digit.get()))[:int(self.opt_price_digit.get())]
        iqty = "000797".zfill(int(self.opt_qty_digit.get()))[:int(self.opt_qty_digit.get())]
        self.lbl_qr_preview.configure(text=f"{prefix}{icode}{iprice}{iqty}")

    def show_qr_settings(self):
        self.clear_content(); scroll = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent"); scroll.pack(fill="both", expand=True, padx=20, pady=10)
        ctk.CTkLabel(scroll, text="QR & BARCODE FORMAT CONFIG", font=("Arial", 22, "bold"), text_color="white").pack(anchor="w", pady=10)
        form = ctk.CTkFrame(scroll, fg_color=self.colors["OCEAN"], corner_radius=12); form.pack(fill="x", pady=10)
        
        r1 = ctk.CTkFrame(form, fg_color="transparent"); r1.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(r1, text="Prefix Default (e.g. 20):", width=160, anchor="w", text_color="white").pack(side="left")
        ctk.CTkSwitch(r1, text="", variable=self.qr_prefix_on, onvalue="ON", offvalue="OFF", command=self.update_qr_preview_logic).pack(side="left", padx=5)
        self.opt_prefix_val = ctk.CTkOptionMenu(r1, values=[str(i) for i in range(20,91)], command=self.update_qr_preview_logic); self.opt_prefix_val.set("20"); self.opt_prefix_val.pack(side="left", padx=20)
        
        r2 = ctk.CTkFrame(form, fg_color="transparent"); r2.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(r2, text="Inventory Code Length:", width=160, anchor="w", text_color="white").pack(side="left")
        self.opt_code_digit = ctk.CTkOptionMenu(r2, values=["4","5","6"], command=self.update_qr_preview_logic); self.opt_code_digit.set("5"); self.opt_code_digit.pack(side="left", padx=20)
        
        r3 = ctk.CTkFrame(form, fg_color="transparent"); r3.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(r3, text="Currency / Price Digits:", width=160, anchor="w", text_color="white").pack(side="left")
        ctk.CTkOptionMenu(r3, values=["USD","IND","EUR","SGD","MYR"]).pack(side="left", padx=5)
        self.opt_price_digit = ctk.CTkOptionMenu(r3, values=["4","5","6"], width=80, command=self.update_qr_preview_logic); self.opt_price_digit.set("5"); self.opt_price_digit.pack(side="left", padx=10)
        
        r4 = ctk.CTkFrame(form, fg_color="transparent"); r4.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(r4, text="Weight/Qty Length:", width=160, anchor="w", text_color="white").pack(side="left")
        self.opt_qty_digit = ctk.CTkOptionMenu(r4, values=["4","5","6"], command=self.update_qr_preview_logic); self.opt_qty_digit.set("6"); self.opt_qty_digit.pack(side="left", padx=20)
        
        preview = ctk.CTkFrame(scroll, fg_color="#000", border_width=2, border_color=self.colors["GOLD"]); preview.pack(fill="x", pady=20)
        ctk.CTkLabel(preview, text="GENERATION PREVIEW", font=("Arial", 10, "bold"), text_color=self.colors["GOLD"]).pack(pady=5)
        self.lbl_qr_preview = ctk.CTkLabel(preview, text="200345100024000797", font=("Courier", 24, "bold"), text_color="white"); self.lbl_qr_preview.pack(pady=10)
        self.update_qr_preview_logic()

    def show_about(self):
        self.clear_content()
        ABOUT_FONT = ("Arial", 18)

        sc = ctk.CTkScrollableFrame(
            self.content_area, fg_color="transparent"
        )
        sc.pack(fill="both", expand=True, padx=20, pady=10)

        screen_width = self.content_area.winfo_screenwidth()


        # Text width based on screen (safe)
        text_wrap = int(screen_width * 0.45)

        about_items = [
        (
            "about1.jpeg",
            "Manual checkouts slow you down and frustrate customers. Our AI-powered billing system automates product lookup, applies discounts, and eliminates human errors — ensuring faster and smarter checkouts.",
            "left"
        ),

        (
            "about2.jpeg",
            lambda parent: (
                text := ctk.CTkTextbox(
                    parent,
                    wrap="word",
                    fg_color="transparent",
                    border_width=0,
                    text_color="white",
                    font=ABOUT_FONT,
                    width=600,
                    height=140
                ),
                text.insert("end", "Guesswork leads to overstocking or stockouts. iLogic "),
                text.insert("end", "AI POS", "highlight"),
                text.insert(
                    "end",
                    " gives you live inventory tracking, automated reorder alerts, and AI-based demand forecasting to keep your shelves stocked smartly."
                ),
                text.tag_config("highlight", foreground="yellow"),
                text.configure(state="disabled"),
                text.pack(anchor="w", fill="x")
            ),
            "right"
        ),

        (
            "about3.jpeg",
            "Make transactions faster and frictionless. Accept all payment types including cash, cards, QR, e-wallets, and split billing — seamlessly integrated with your POS.",
            "left"
        ),
    ]



        for img_name, desc, align in about_items:
            row = ctk.CTkFrame(sc, fg_color="transparent")
            row.pack(fill="x", pady=25)

            path = os.path.join(BASE_DIR, "about", img_name)
            if not os.path.exists(path):
                continue

            # img = ctk.CTkImage(Image.open(path), size=(400, 220))
            # img_lbl = ctk.CTkLabel(row, image=img, text="")
            # img_lbl.image = img
            
            # # White frame (border)
            # img_frame = ctk.CTkFrame(
            #     row,
            #     fg_color="white",
            #     corner_radius=6   # optional
            # )

            # # padding INSIDE the frame (this is the key fix)
            # inner_frame = ctk.CTkFrame(
            #     img_frame,
            #     fg_color="transparent"
            # )
            # inner_frame.pack(padx=6, pady=6)

            # img = ctk.CTkImage(Image.open(path), size=(400, 220))
            # img_lbl = ctk.CTkLabel(inner_frame, image=img, text="")
            # img_lbl.image = img
            # img_lbl.pack()
            

            # ---- White frame (top layer) ----
            img_frame = ctk.CTkFrame(
                row,
                fg_color="purple",
                corner_radius=6
            )

            # ---- Inner padding frame ----
            inner_frame = ctk.CTkFrame(
                img_frame,
                fg_color="transparent"
            )
            inner_frame.pack(padx=8, pady=8)

            img = ctk.CTkImage(Image.open(path), size=(400, 220))
            img_lbl = ctk.CTkLabel(inner_frame, image=img, text="")
            img_lbl.image = img
            img_lbl.pack()


            


            # ---------- FIX START ----------
            if callable(desc):
                text_frame = ctk.CTkFrame(row, fg_color="transparent")
                desc(text_frame)   # ✅ call lambda to create labels
            else:
                text_frame = ctk.CTkLabel(
                    row,
                    text=desc,
                    font=("Arial", 28),
                    text_color="white",
                    wraplength=text_wrap,
                    justify="left"
                )
            # ---------- FIX END ----------

            if align == "left":
                # img_lbl.pack(side="left", padx=(0, 30))
                img_frame.pack(side="left", padx=(0, 30))
                text_frame.pack(side="left", expand=True, anchor="w")
            else:
                text_frame.pack(side="left", expand=True, anchor="e", padx=(0, 30))
                # img_lbl.pack(side="right")
                img_frame.pack(side="right")
             


        ctk.CTkLabel(
            sc,
            text="iLogic POS System - V5.0",
            font=("Arial", 16, "bold"),
            text_color=self.colors["GOLD"]
        ).pack(pady=30)

def launch_settings(main_app): 
    main_app.show_settings_view()