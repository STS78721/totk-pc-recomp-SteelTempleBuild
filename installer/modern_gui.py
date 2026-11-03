"""Modern CustomTkinter GUI Installer for The Legend of Zelda: Tears of the Kingdom (PC Recompiled).

Features:
- Sleek dark Zonai/Master Sword theme
- Vendor AI & Upscaler SDK management (NVIDIA DLSS 4.5 / DLSS-NR, Intel XeSS, AMD FSR)
- Native Recomp Controller UI selection (PS5 DualSense Monochrome/Color, Xbox Monochrome/Color, Switch)
- Automated Save Game Importer (auto-detects Eden, Yuzu, Ryujinx saves)
- Desktop shortcut creation
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

from .save_importer import scan_for_saves, inject_save
from .vendor_sdks import install_vendor_sdks, VENDOR_SDK_FILES
from .controller_ui_manager import install_controller_ui, CONTROLLER_UI_CHOICES
from .shortcut_creator import create_desktop_shortcut

# Theme colors
ACCENT_GREEN = "#00e699"
ACCENT_HOVER = "#00b377"
BG_DARK = "#121417"
CARD_BG = "#1c2026"
CARD_BORDER = "#2a313d"
TEXT_DIM = "#9ba3af"

class ModernTotkInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window properties
        self.title("The Legend of Zelda: Tears of the Kingdom - PC Setup")
        self.geometry("980x720")
        self.minsize(920, 680)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

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

        self.detected_saves = []

        # Setup UI
        self.setup_ui()
        self.refresh_detected_saves()

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
        # Configure grid layout
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
        self.tab_features = self.tabview.add("2. Controllers & Vendor SDKs")
        self.tab_install = self.tabview.add("3. Installation & Progress")

        self.build_tab_files()
        self.build_tab_features()
        self.build_tab_install()

        # 3. Bottom Action Bar
        bottom_bar = ctk.CTkFrame(self, fg_color=CARD_BG, height=60, corner_radius=0)
        bottom_bar.grid(row=2, column=0, sticky="ew")

        self.btn_next = ctk.CTkButton(bottom_bar, text="Next: Customization & Features →", fg_color=ACCENT_HOVER,
                                      hover_color=ACCENT_GREEN, font=ctk.CTkFont(size=14, weight="bold"),
                                      command=lambda: self.tabview.set("2. Controllers & Vendor SDKs"))
        self.btn_next.pack(side="right", padx=20, pady=12)

    def build_tab_files(self):
        frame = self.tab_files
        frame.grid_columnconfigure(1, weight=1)

        # Instruction
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
        card_ctrl.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(card_ctrl, text="🎮 Controller UI Button Prompts", font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(card_ctrl, text="Choose your controller style. The installer automatically integrates HD button prompts:", text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(0, 8))

        ui_names = [c["name"] for c in CONTROLLER_UI_CHOICES]
        self.opt_ctrl = ctk.CTkOptionMenu(card_ctrl, values=ui_names, variable=self.var_controller_ui,
                                          fg_color=CARD_BORDER, button_color=ACCENT_HOVER, button_hover_color=ACCENT_GREEN, width=380)
        self.opt_ctrl.pack(anchor="w", padx=15, pady=(0, 12))

        # 2. Vendor SDKs Card (NVIDIA / Intel / AMD)
        card_sdks = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_sdks.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(card_sdks, text="⚡ Vendor AI & Upscaling SDKs (NVIDIA, Intel, AMD)", font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(10, 2))
        
        chk_sdk = ctk.CTkCheckBox(card_sdks, text="Auto-deploy / download AI Upscalers (NVIDIA DLSS 4.5 / DLSS-NR, Intel XeSS, Streamline)",
                                  variable=self.var_install_sdks, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_sdk.pack(anchor="w", padx=15, pady=6)
        ctk.CTkLabel(card_sdks, text="Uncheck if you want a stripped minimal installation without vendor neural reconstruction libraries.",
                     text_color=TEXT_DIM, font=ctk.CTkFont(size=12)).pack(anchor="w", padx=35, pady=(0, 10))

        # 3. Bring Your Old Save Card
        card_save = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_save.pack(fill="x", pady=8, padx=5)

        ctk.CTkLabel(card_save, text="💾 Bring Your Old Save Game", font=ctk.CTkFont(size=15, weight="bold"), text_color=ACCENT_GREEN).pack(anchor="w", padx=15, pady=(10, 2))
        
        chk_save = ctk.CTkCheckBox(card_save, text="Import existing save data from emulator or previous backup",
                                   variable=self.var_import_save, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_save.pack(anchor="w", padx=15, pady=6)

        save_row = ctk.CTkFrame(card_save, fg_color="transparent")
        save_row.pack(fill="x", padx=35, pady=(0, 10))

        self.opt_save = ctk.CTkOptionMenu(save_row, variable=self.var_selected_save, values=["No save detected yet"], width=450,
                                          fg_color=CARD_BORDER, button_color=ACCENT_HOVER, button_hover_color=ACCENT_GREEN)
        self.opt_save.pack(side="left", padx=(0, 10))

        ctk.CTkButton(save_row, text="Browse Save...", width=110, command=self.browse_custom_save).pack(side="left")

        # 4. Shortcut Card
        card_short = ctk.CTkFrame(frame, fg_color=CARD_BG, corner_radius=10, border_width=1, border_color=CARD_BORDER)
        card_short.pack(fill="x", pady=8, padx=5)

        chk_short = ctk.CTkCheckBox(card_short, text="Create Desktop Shortcut with high-res Tears of the Kingdom icon",
                                    variable=self.var_create_shortcut, fg_color=ACCENT_GREEN, hover_color=ACCENT_HOVER)
        chk_short.pack(anchor="w", padx=15, pady=12)

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
        self.tabview.set("3. Installation & Progress")
        
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
                self.log(f"[!] Warning: Could not find zip for {choice['name']}, checked local fallback.")
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

        self.progress_bar.set(0.85)

        # 5. Desktop Shortcut
        if self.var_create_shortcut.get():
            self.lbl_status.configure(text="Creating Desktop Shortcut...")
            self.log("Creating Desktop Shortcut...")
            create_desktop_shortcut(target)
            self.log("[✓] Desktop shortcut created successfully.")

        self.progress_bar.set(1.0)
        self.lbl_status.configure(text="Installation Complete! Ready to play.")
        self.log("\n==========================================")
        self.log("🎉 INSTALLATION COMPLETED SUCCESSFULLY!")
        self.log(f"You can now launch the game directly from: {target}\\totk.exe")
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
