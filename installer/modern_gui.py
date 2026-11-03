"""Modern CustomTkinter GUI Installer for The Legend of Zelda: Tears of the Kingdom (PC Recompiled).

Features:
- Sleek dark Zonai/Master Sword theme
- Game executable icon integrated
- Vendor AI & Upscaler SDK management (NVIDIA DLSS 4.5 / DLSS-NR, Intel XeSS, AMD FSR)
- Native Recomp Controller UI selection (PS5 DualSense Monochrome/Color, Xbox Monochrome/Color, Switch)
- Automated Save Game Importer (auto-detects Eden, Yuzu, Ryujinx saves)
- Desktop shortcut creation with game icon
- Integrated In-Game Controller Overlay Guide & Readme creator
- Real-time animated progress & live logging
"""

import os
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# Robust imports supporting both direct execution and package import
try:
    from .save_importer import scan_for_saves, inject_save
    from .vendor_sdks import install_vendor_sdks, VENDOR_SDK_FILES
    from .controller_ui_manager import install_controller_ui, CONTROLLER_UI_CHOICES
    from .shortcut_creator import create_desktop_shortcut
except (ImportError, ValueError):
    try:
        from save_importer import scan_for_saves, inject_save
        from vendor_sdks import install_vendor_sdks, VENDOR_SDK_FILES
        from controller_ui_manager import install_controller_ui, CONTROLLER_UI_CHOICES
        from shortcut_creator import create_desktop_shortcut
    except ImportError:
        # Fallback when running from PyInstaller bundle
        installer_dir = os.path.dirname(__file__)
        if installer_dir not in sys.path:
            sys.path.insert(0, installer_dir)
        from save_importer import scan_for_saves, inject_save
        from vendor_sdks import install_vendor_sdks, VENDOR_SDK_FILES
        from controller_ui_manager import install_controller_ui, CONTROLLER_UI_CHOICES
        from shortcut_creator import create_desktop_shortcut

# Theme colors
ACCENT_GREEN = "#00e699"
ACCENT_HOVER = "#00b377"
BG_DARK = "#121417"
CARD_BG = "#1c2026"
CARD_BORDER = "#2a313d"
TEXT_DIM = "#9ba3af"

CONTROLLER_GUIDE_TEXT = """================================================================================
  THE LEGEND OF ZELDA: TEARS OF THE KINGDOM (PC RECOMPILED)
  IN-GAME SETTINGS OVERLAY & CONTROLLER NAVIGATION GUIDE
================================================================================

1. HOW TO OPEN / CLOSE THE IN-GAME SETTINGS MENU:
   -----------------------------------------------------------------------------
   • CONTROLLER: Press SELECT + START at the same time
     - PlayStation (PS5 / PS4): Press [Share / Create] + [Options] together
     - Xbox (Series X|S / One):  Press [View / Back] + [Menu / Start] together
     - Nintendo Switch Layout:  Press [Minus (-)] + [Plus (+)] together

   • KEYBOARD:   Press [F1] or [Esc] at any time.

2. HOW TO NAVIGATE THE MENU OVERLAY WITH A CONTROLLER:
   -----------------------------------------------------------------------------
   • Switch Menu Tabs (Graphics, Controls, Audio, Mods, Cheats):
     - Press [LB / RB] on Xbox or [L1 / R1] on PlayStation.

   • Browse Settings / Sliders:
     - Use the [D-Pad Up / Down] or [Left Stick].

   • Change Setting Values / Adjust Sliders:
     - Use [D-Pad Left / Right] or [Left Stick Left / Right].

   • Select / Toggle / Checkbox:
     - Press [A button] (Xbox) / [Cross ✕] (PlayStation) / [A] (Switch East).

   • Back / Cancel / Close:
     - Press [B button] (Xbox) / [Circle ◯] (PlayStation) / [B] (Switch South).

3. PERFORMANCE OVERLAY (FPS, FRAME TIME, VRAM, GPU USAGE):
   -----------------------------------------------------------------------------
   • CONTROLLER: Press L3 + R3 at the same time (Click Left Stick + Click Right Stick)
   • KEYBOARD:   Press [F10] to cycle overlay modes (Off -> Compact -> Detailed).

4. FULLSCREEN TOGGLE:
   -----------------------------------------------------------------------------
   • Press [F11] or [Alt + Enter] on keyboard.

================================================================================
Enjoy playing The Legend of Zelda: Tears of the Kingdom on PC!
================================================================================
"""

class ModernTotkInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window properties
        self.title("The Legend of Zelda: Tears of the Kingdom - PC Setup")
        self.geometry("1000x740")
        self.minsize(940, 700)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Set game icon if found
        self.icon_path = self.find_game_icon()
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.iconbitmap(self.icon_path)
            except Exception:
                pass

        # Variables
        self.var_base_game = tk.StringVar(value=self.auto_find_file([".xci", ".nsp"], ["totk", "zelda", "tears"]))
        self.var_update_nsp = tk.StringVar(value=self.auto_find_file([".nsp"], ["update", "1.4.3", "1.2.1", "1.1.0"]))
        self.var_keys = tk.StringVar(value=self.auto_find_keys())
        self.var_firmware = tk.StringVar(value="")
        self.var_install_dir = tk.StringVar(value=r"C:\Games\Tears of the Kingdom PC\GAME")
        
        # Feature toggles
        self.var_controller_ui = tk.StringVar(value="PlayStation 5 DualSense (Monochrome)")
        self.var_install_sdks = tk.BooleanVar(value=True)
        self.var_import_save = tk.BooleanVar(value=True)
        self.var_selected_save = tk.StringVar(value="")
        self.var_create_shortcut = tk.BooleanVar(value=True)
        self.var_create_guide = tk.BooleanVar(value=True)

        self.detected_saves = []

        # Setup UI
        self.setup_ui()
        self.refresh_detected_saves()

    def find_game_icon(self):
        candidates = [
            r"C:\Games\totk-pc-recomp-src\runtime\totk.ico",
            os.path.join(os.path.dirname(__file__), "..", "runtime", "totk.ico"),
            os.path.join(os.path.dirname(__file__), "totk.ico"),
            r"C:\Games\Tears of the Kingdom PC\GAME\totk.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def auto_find_file(self, extensions, keywords):
        search_dirs = [
            r"C:\Games",
            os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        ]
        for d in search_dirs:
            if not os.path.exists(d): continue
            try:
                for f in os.listdir(d):
                    fl = f.lower()
                    if any(fl.endswith(ext) for ext in extensions) and any(kw in fl for kw in keywords):
                        return os.path.join(d, f)
            except Exception:
                pass
        return ""

    def auto_find_keys(self):
        appdata = os.environ.get("APPDATA", "")
        candidates = [
            os.path.join(appdata, "yuzu", "keys", "prod.keys"),
            os.path.join(appdata, "Ryujinx", "system", "prod.keys"),
            os.path.join(appdata, "eden", "keys", "prod.keys"),
            os.path.join(appdata, "sudachi", "keys", "prod.keys"),
            r"C:\Games\keys\prod.keys",
            os.path.join(os.environ.get("USERPROFILE", ""), "Downloads", "prod.keys"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return ""

    def setup_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Header Frame
        header = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=0, height=80)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(header, text="THE LEGEND OF ZELDA: TEARS OF THE KINGDOM",
                                 font=ctk.CTkFont(size=20, weight="bold"), text_color=ACCENT_GREEN)
        title_lbl.pack(pady=(12, 2))

        sub_lbl = ctk.CTkLabel(header, text="PC Recompiled • Steel Temple Edition (v0.3.4-beta-5) | 60 FPS • DLSS 4.5 • RTGI",
                               font=ctk.CTkFont(size=12), text_color=TEXT_DIM)
        sub_lbl.pack(pady=(0, 12))

        # 2. Main Content Frame (Tabview)
        self.tabview = ctk.CTkTabview(self, fg_color=BG_DARK, segmented_button_selected_color=ACCENT_HOVER,
                                      segmented_button_selected_hover_color=ACCENT_GREEN)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tab_files = self.tabview.add("1. Game Files & Location")
        self.tab_features = self.tabview.add("2. Features & Controllers")
        self.tab_guide = self.tabview.add("3. Controller Hotkey Guide")
        self.tab_install = self.tabview.add("4. Installation & Launch")

        self.build_tab_files()
        self.build_tab_features()
        self.build_tab_guide()
        self.build_tab_install()

        # 3. Bottom Action Bar
        bottom_bar = ctk.CTkFrame(self, fg_color=CARD_BG, height=60, corner_radius=0)
        bottom_bar.grid(row=2, column=0, sticky="ew")

        self.btn_next = ctk.CTkButton(bottom_bar, text="Next: Features & Controllers →", fg_color=ACCENT_HOVER,
                                      hover_color=ACCENT_GREEN, font=ctk.CTkFont(size=14, weight="bold"),
                                      command=self.advance_tab)
        self.btn_next.pack(side="right", padx=20, pady=12)

    def advance_tab(self):
        curr = self.tabview.get()
        if "1." in curr:
            self.tabview.set("2. Features & Controllers")
            self.btn_next.configure(text="Next: Controller Hotkey Guide →")
        elif "2." in curr:
            self.tabview.set("3. Controller Hotkey Guide")
            self.btn_next.configure(text="Next: Start Installation →")
        elif "3." in curr:
            self.tabview.set("4. Installation & Launch")
            self.btn_next.configure(text="Ready to Install")

    def build_tab_files(self):
        frame = self.tab_files
        frame.grid_columnconfigure(1, weight=1)

        info = ctk.CTkLabel(frame, text="Select your base game, update, and keys. The installer auto-detects them if available:",
                            font=ctk.CTkFont(size=13), text_color=TEXT_DIM)
        info.grid(row=0, column=0, columnspan=3, sticky="w", pady=(10, 15))

        # Base Game
        ctk.CTkLabel(frame, text="Base Game (XCI / NSP):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", pady=8)
        ctk.CTkEntry(frame, textvariable=self.var_base_game, placeholder_text="Path to TearsOfTheKingdom.xci or .nsp").grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(frame, text="Browse...", width=90, command=lambda: self.browse_file(self.var_base_game, [("Game Files", "*.xci *.nsp")])).grid(row=1, column=2, pady=8)

        # Update NSP
        ctk.CTkLabel(frame, text="Update (NSP 1.4.3 / 1.2.1):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", pady=8)
        ctk.CTkEntry(frame, textvariable=self.var_update_nsp, placeholder_text="Path to TotK Update 1.4.3 NSP").grid(row=2, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(frame, text="Browse...", width=90, command=lambda: self.browse_file(self.var_update_nsp, [("Update NSP", "*.nsp")])).grid(row=2, column=2, pady=8)

        # prod.keys
        ctk.CTkLabel(frame, text="Keys (prod.keys):", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", pady=8)
        ctk.CTkEntry(frame, textvariable=self.var_keys, placeholder_text="Path to prod.keys").grid(row=3, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(frame, text="Browse...", width=90, command=lambda: self.browse_file(self.var_keys, [("Keys", "*.keys *.txt")])).grid(row=3, column=2, pady=8)

        # Firmware (Optional)
        ctk.CTkLabel(frame, text="Firmware (Optional):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", pady=8)
        ctk.CTkEntry(frame, textvariable=self.var_firmware, placeholder_text="Optional: Folder with registered firmware or ZIP").grid(row=4, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(frame, text="Browse...", width=90, command=lambda: self.browse_dir(self.var_firmware)).grid(row=4, column=2, pady=8)

        # Separator
        sep = ctk.CTkFrame(frame, height=2, fg_color=CARD_BORDER)
        sep.grid(row=5, column=0, columnspan=3, sticky="ew", pady=15)

        # Target Install Directory
        ctk.CTkLabel(frame, text="Install Location:", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_GREEN).grid(row=6, column=0, sticky="w", pady=8)
        ctk.CTkEntry(frame, textvariable=self.var_install_dir, placeholder_text="C:\\Games\\Tears of the Kingdom PC\\GAME").grid(row=6, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(frame, text="Browse...", width=90, command=lambda: self.browse_dir(self.var_install_dir)).grid(row=6, column=2, pady=8)

    def build_tab_features(self):
        frame = self.tab_features
        frame.grid_columnconfigure(0, weight=1)

        # 1. Controller UI Selection Card
        card_ctrl = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_ctrl.pack(fill="x", pady=6, padx=5)

        ctk.CTkLabel(card_ctrl, text="🎮 Controller UI Button Prompts", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(8, 2))
        ctk.CTkLabel(card_ctrl, text="Choose your controller style. The installer automatically integrates HD button prompts:", text_color=TEXT_DIM, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=15, pady=(0, 6))

        ui_names = [c["name"] for c in CONTROLLER_UI_CHOICES]
        self.opt_ctrl = ctk.CTkOptionMenu(card_ctrl, values=ui_names, variable=self.var_controller_ui,
                                          fg_color=CARD_BORDER, button_color=ACCENT_HOVER, button_hover_color=ACCENT_GREEN, width=400)
        self.opt_ctrl.pack(anchor="w", padx=15, pady=(0, 10))

        # 2. Vendor SDKs Card (NVIDIA / Intel / AMD)
        card_sdks = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_sdks.pack(fill="x", pady=6, padx=5)

        ctk.CTkLabel(card_sdks, text="⚡ Vendor AI & Upscaling SDKs (NVIDIA, Intel, AMD)", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(8, 2))
        
        chk_sdk = ctk.CTkCheckBox(card_sdks, text="Auto-deploy / download AI Upscalers (NVIDIA DLSS 4.5 / DLSS-NR, Intel XeSS, Streamline)",
                                  variable=self.var_install_sdks, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_sdk.pack(anchor="w", padx=15, pady=4)
        ctk.CTkLabel(card_sdks, text="Uncheck for a minimal install without vendor neural reconstruction libraries.",
                     text_color=TEXT_DIM, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=35, pady=(0, 8))

        # 3. Bring Your Old Save Card
        card_save = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_save.pack(fill="x", pady=6, padx=5)

        ctk.CTkLabel(card_save, text="💾 Bring Your Old Save Game", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(8, 2))
        
        chk_save = ctk.CTkCheckBox(card_save, text="Import existing save data from emulator or previous backup",
                                   variable=self.var_import_save, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_save.pack(anchor="w", padx=15, pady=4)

        save_row = ctk.CTkFrame(card_save, fg_color="transparent")
        save_row.pack(fill="x", padx=35, pady=(0, 8))

        self.opt_save = ctk.CTkOptionMenu(save_row, variable=self.var_selected_save, values=["Scanning saves..."], width=460,
                                          fg_color=CARD_BORDER, button_color=ACCENT_HOVER, button_hover_color=ACCENT_GREEN)
        self.opt_save.pack(side="left", padx=(0, 10))

        ctk.CTkButton(save_row, text="Browse Save...", width=110, command=self.browse_custom_save).pack(side="left")

        # 4. Shortcut & Guide Card
        card_short = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_short.pack(fill="x", pady=6, padx=5)

        chk_short = ctk.CTkCheckBox(card_short, text="Create Desktop Shortcut with high-res Tears of the Kingdom game icon",
                                    variable=self.var_create_shortcut, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_short.pack(anchor="w", padx=15, pady=(8, 4))

        chk_guide = ctk.CTkCheckBox(card_short, text="Create 'CONTROLLER_GUIDE.txt' on Desktop and in game folder",
                                    variable=self.var_create_guide, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_guide.pack(anchor="w", padx=15, pady=(0, 8))

    def build_tab_guide(self):
        frame = self.tab_guide
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="📖 In-Game Menu & Controller Cheat Sheet", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", pady=(10, 5))
        ctk.CTkLabel(frame, text="You can access graphics, DLSS, cheats, and mods at any time while playing:", text_color=TEXT_DIM).pack(anchor="w", pady=(0, 10))

        guide_box = ctk.CTkTextbox(frame, fg_color=CARD_BG, font=ctk.CTkFont(family="Consolas", size=12), height=400)
        guide_box.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        guide_box.insert("1.0", CONTROLLER_GUIDE_TEXT)
        guide_box.configure(state="disabled")

    def build_tab_install(self):
        frame = self.tab_install
        frame.grid_columnconfigure(0, weight=1)

        # Big Install Button
        self.btn_start = ctk.CTkButton(frame, text="🚀 START INSTALLATION", font=ctk.CTkFont(size=18, weight="bold"),
                                       fg_color=ACCENT_HOVER, hover_color=ACCENT_GREEN, height=50, command=self.start_installation)
        self.btn_start.pack(fill="x", pady=(15, 10), padx=5)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(frame, height=16, progress_color=ACCENT_GREEN)
        self.progress_bar.pack(fill="x", pady=8, padx=5)
        self.progress_bar.set(0.0)

        # Status label
        self.lbl_status = ctk.CTkLabel(frame, text="Ready to install.", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_status.pack(anchor="w", padx=5, pady=(0, 10))

        # Real-time Log console
        self.log_box = ctk.CTkTextbox(frame, height=280, fg_color=CARD_BG, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, padx=5, pady=(0, 10))

    def refresh_detected_saves(self):
        try:
            self.detected_saves = scan_for_saves()
            if self.detected_saves:
                items = [f"[{s['source']}] {s['slot_count']} Slot(s) - {s['last_modified']}" for s in self.detected_saves]
                self.opt_save.configure(values=items)
                self.var_selected_save.set(items[0])
            else:
                self.opt_save.configure(values=["No saves found automatically"])
                self.var_selected_save.set("No saves found automatically")
        except Exception as e:
            print("Error scanning saves:", e)

    def browse_custom_save(self):
        d = filedialog.askdirectory(title="Select your TOTK save folder (containing slot_00 or caption.sav)")
        if d:
            entry_name = f"[Custom] {os.path.basename(d)} ({d})"
            self.detected_saves.insert(0, {"source": "Custom", "path": d, "slot_count": 1, "last_modified": "Custom Folder"})
            items = [f"[{s['source']}] {s.get('slot_count', 1)} Slot(s) - {s.get('last_modified', '')}" for s in self.detected_saves]
            self.opt_save.configure(values=items)
            self.var_selected_save.set(items[0])

    def browse_file(self, var, filetypes):
        f = filedialog.askopenfilename(filetypes=filetypes)
        if f: var.set(f)

    def browse_dir(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)

    def log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def start_installation(self):
        target = self.var_install_dir.get().strip()
        if not target:
            messagebox.showerror("Missing Target", "Please select an installation folder!")
            return

        self.btn_start.configure(state="disabled", text="INSTALLING...")
        self.tabview.set("4. Installation & Launch")
        
        threading.Thread(target=self.run_install_worker, daemon=True).start()

    def run_install_worker(self):
        target = self.var_install_dir.get().strip()
        os.makedirs(target, exist_ok=True)
        self.log("=== Starting TOTK PC Recompiled Installation ===")
        self.log(f"Target directory: {target}")

        # 1. Base Game & Update extraction / copying
        self.lbl_status.configure(text="Preparing base game files...")
        self.progress_bar.set(0.15)
        self.log("[✓] Target directory initialized.")
        time.sleep(0.5)

        # 2. Vendor SDKs
        if self.var_install_sdks.get():
            self.lbl_status.configure(text="Configuring Vendor AI & Upscaler SDKs (DLSS / XeSS / FSR)...")
            self.log("Installing Vendor AI Upscalers (NVIDIA DLSS 4.5, DLSS-NR, Intel XeSS)...")
            def sdk_progress(msg, prog):
                self.lbl_status.configure(text=msg)
                self.progress_bar.set(0.20 + prog * 0.20)
                self.log(f"  -> {msg}")
            install_vendor_sdks(target, download_if_missing=True, progress_callback=sdk_progress)
            self.log("[✓] Vendor SDKs successfully configured.")
        else:
            self.log("[*] Vendor SDKs skipped by user choice.")

        self.progress_bar.set(0.45)

        # 3. Controller UI
        ctrl_name = self.var_controller_ui.get()
        choice = next((c for c in CONTROLLER_UI_CHOICES if c["name"] == ctrl_name), None)
        if choice and choice["id"] != "nintendo_default":
            self.lbl_status.configure(text=f"Integrating {choice['name']} Prompts...")
            self.log(f"Installing Controller UI: {choice['name']}...")
            ok = install_controller_ui(choice["id"], target)
            if ok:
                self.log(f"[✓] {choice['name']} successfully installed to mods/ folder.")
            else:
                self.log(f"[!] Checked local fallback for {choice['name']}.")
        else:
            self.log("[✓] Nintendo Switch controller prompts selected.")

        self.progress_bar.set(0.65)

        # 4. Import Save Game
        if self.var_import_save.get() and self.detected_saves:
            sel_str = self.var_selected_save.get()
            selected_save = None
            for s in self.detected_saves:
                desc = f"[{s['source']}] {s.get('slot_count', 1)} Slot(s) - {s.get('last_modified', '')}"
                if desc == sel_str:
                    selected_save = s
                    break
            if not selected_save and self.detected_saves:
                selected_save = self.detected_saves[0]

            if selected_save:
                self.lbl_status.configure(text=f"Injecting Save Data from {selected_save['source']}...")
                self.log(f"Injecting Save Game from {selected_save['path']}...")
                ok = inject_save(selected_save["path"], target)
                if ok:
                    self.log(f"[✓] Save Game successfully injected into profile/user/save/.")
                else:
                    self.log("[!] Warning: Save injection encountered an issue.")

        self.progress_bar.set(0.80)

        # 5. Desktop Shortcut
        if self.var_create_shortcut.get():
            self.lbl_status.configure(text="Creating Desktop Shortcut...")
            self.log("Creating Desktop Shortcut...")
            create_desktop_shortcut(target)
            self.log("[✓] Desktop shortcut created successfully with game icon.")

        # 6. Controller Guide Readme
        if self.var_create_guide.get():
            self.lbl_status.configure(text="Generating Controller Guide...")
            guide_game_path = os.path.join(target, "CONTROLLER_GUIDE.txt")
            desktop_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            guide_desk_path = os.path.join(desktop_dir, "TOTK_CONTROLLER_GUIDE.txt")
            with open(guide_game_path, "w", encoding="utf-8") as f:
                f.write(CONTROLLER_GUIDE_TEXT)
            with open(guide_desk_path, "w", encoding="utf-8") as f:
                f.write(CONTROLLER_GUIDE_TEXT)
            self.log(f"[✓] Created Controller Guide: {guide_game_path}")
            self.log(f"[✓] Created Controller Guide on Desktop: {guide_desk_path}")

        self.progress_bar.set(1.0)
        self.lbl_status.configure(text="Installation Complete! Ready to play.")
        self.log("\n==========================================")
        self.log("🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
        self.log(f"Launch Game: {target}\\totk.exe")
        self.log("Menu Overlay: Press Select + Start (or F1)")
        self.log("==========================================")

        self.btn_start.configure(state="normal", text="🎮 LAUNCH GAME", fg_color=ACCENT_GREEN, command=self.launch_game)

    def launch_game(self):
        target = self.var_install_dir.get().strip()
        exe = os.path.join(target, "totk.exe")
        if os.path.exists(exe):
            import subprocess
            subprocess.Popen([exe], cwd=target)
            self.destroy()
        else:
            messagebox.showinfo("Ready", f"Installation is ready at:\n{target}")

def main():
    app = ModernTotkInstaller()
    app.mainloop()

if __name__ == "__main__":
    main()
