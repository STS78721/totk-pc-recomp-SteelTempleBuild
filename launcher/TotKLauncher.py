"""The Legend of Zelda: Tears of the Kingdom - PC Recompiled (SteelTemple Edition)
Standalone Sony/Nixxes-style Launcher & Settings Manager.
"""

import os
import sys
import json
import re
import subprocess
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# --- Color Palette (Sony / Nixxes Inspired + Zonai Glow) ---
COLOR_BG_DARK = "#0a0c10"
COLOR_GOLD = "#ffd24d"
COLOR_GOLD_HOVER = "#fff2a3"
COLOR_WHITE = "#e8eaed"
COLOR_TEXT_DIM = "#8b949e"
COLOR_CARD = "#13171f"
COLOR_CARD_BORDER = "#252d3a"
COLOR_ACCENT_GREEN = "#1dd1a1"
COLOR_TAB_ACTIVE = "#1f2633"
COLOR_BUTTON_HOVER = "#2a3445"

GITHUB_URL = "https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild"
VERSION_STRING = "Beta 5e Hotfix"

def get_base_dir():
    """Return the base directory for assets (works for source and PyInstaller bundle)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

def find_game_dir():
    """Locate the directory containing totk.exe and totk.ini."""
    candidates = [
        Path.cwd(),
        Path.cwd() / "GAME",
        Path(__file__).resolve().parent,
        Path(__file__).resolve().parent / "GAME",
        Path(__file__).resolve().parent.parent / "GAME",
        Path(r"C:\Games\Tears of the Kingdom PC\GAME"),
    ]
    for c in candidates:
        if (c / "totk.exe").is_file() or (c / "totk.ini").is_file():
            return c
    return Path.cwd()

GAME_DIR = find_game_dir()
INI_PATH = GAME_DIR / "totk.ini"
CONFIG_PATH = GAME_DIR / "launcher_config.json"


# --- Config File & INI Handling ---
def load_launcher_config():
    if CONFIG_PATH.is_file():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"show_launcher": True}

def save_launcher_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Error saving launcher config: {e}")

def parse_ini(ini_file):
    """Parse totk.ini into key-value map."""
    values = {}
    if not ini_file.is_file():
        return values
    try:
        with open(ini_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith(('#', ';', '[')):
                    continue
                if '=' in s:
                    k, v = s.split('=', 1)
                    values[k.strip().lower()] = v.strip().split('#')[0].split(';')[0].strip()
    except Exception as e:
        print(f"Error reading {ini_file}: {e}")
    return values

def update_ini_setting(lines, key, new_val):
    """Update or uncomment key = new_val in lines list."""
    pat_active = re.compile(rf'^\s*{re.escape(key)}\s*=.*$', re.IGNORECASE)
    pat_commented = re.compile(rf'^\s*[#;]\s*{re.escape(key)}\s*=.*$', re.IGNORECASE)
    
    found = False
    for i, line in enumerate(lines):
        if pat_active.match(line):
            lines[i] = f"{key} = {new_val}\n"
            return True
    for i, line in enumerate(lines):
        if pat_commented.match(line):
            lines[i] = f"{key} = {new_val}\n"
            return True
    return False

def save_ini_settings(ini_file, updates):
    """Update settings in totk.ini preserving comments and layout."""
    if not ini_file.is_file():
        # Create fresh if missing
        with open(ini_file, "w", encoding="utf-8") as f:
            for k, v in updates.items():
                f.write(f"{k} = {v}\n")
        return True

    with open(ini_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for k, v in updates.items():
        if not update_ini_setting(lines, k, v):
            lines.append(f"{k} = {v}\n")

    with open(ini_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


# --- Sony / Nixxes Settings Dialog ---
class SonySettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Display & Graphics Settings")
        self.geometry("820x640")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        # Center on screen
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.ini_values = parse_ini(INI_PATH)
        self.vars = {}

        self.setup_ui()

    def get_val(self, key, default=""):
        return self.ini_values.get(key.lower(), default)

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self, bg=COLOR_CARD, height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title_lbl = tk.Label(header, text="GAME SETTINGS & GRAPHICS CONFIGURATION",
                             font=("Segoe UI", 12, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD)
        title_lbl.pack(side=tk.LEFT, padx=25, pady=18)

        # Style notebook
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Sony.TNotebook", background=COLOR_BG_DARK, borderwidth=0)
        style.configure("Sony.TNotebook.Tab", background=COLOR_CARD, foreground=COLOR_TEXT_DIM,
                        font=("Segoe UI", 10, "bold"), padding=[20, 10], borderwidth=0)
        style.map("Sony.TNotebook.Tab",
                  background=[("selected", COLOR_TAB_ACTIVE)],
                  foreground=[("selected", COLOR_GOLD)])

        self.notebook = ttk.Notebook(self, style="Sony.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.tab_display = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_upscale = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_graphics = tk.Frame(self.notebook, bg=COLOR_BG_DARK)
        self.tab_audio = tk.Frame(self.notebook, bg=COLOR_BG_DARK)

        self.notebook.add(self.tab_display, text="  DISPLAY  ")
        self.notebook.add(self.tab_upscale, text="  UPSCALING & PERFORMANCE  ")
        self.notebook.add(self.tab_graphics, text="  GRAPHICS & LIGHTING  ")
        self.notebook.add(self.tab_audio, text="  CONTROLS & AUDIO  ")

        self.build_display_tab()
        self.build_upscale_tab()
        self.build_graphics_tab()
        self.build_audio_tab()

        # Bottom Bar
        bottom_bar = tk.Frame(self, bg=COLOR_CARD, height=60)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        bottom_bar.pack_propagate(False)

        def make_btn(parent, text, cmd, is_primary=False):
            bg = COLOR_GOLD if is_primary else COLOR_BUTTON_HOVER
            fg = "#000000" if is_primary else COLOR_WHITE
            b = tk.Button(parent, text=text, font=("Segoe UI", 9, "bold"),
                          bg=bg, fg=fg, activebackground=COLOR_GOLD_HOVER,
                          activeforeground="#000000", bd=0, padx=18, pady=8,
                          cursor="hand2", command=cmd)
            return b

        btn_save = make_btn(bottom_bar, "SAVE & APPLY", self.save_and_close, is_primary=True)
        btn_save.pack(side=tk.RIGHT, padx=(10, 25), pady=12)

        btn_cancel = make_btn(bottom_bar, "CANCEL", self.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=10, pady=12)

        btn_default = make_btn(bottom_bar, "RESTORE DEFAULTS", self.restore_defaults)
        btn_default.pack(side=tk.LEFT, padx=25, pady=12)

    def create_row_dropdown(self, parent, label_text, var_key, options, default_val, desc=""):
        frame = tk.Frame(parent, bg=COLOR_BG_DARK, pady=8)
        frame.pack(fill=tk.X, padx=20)

        left = tk.Frame(frame, bg=COLOR_BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lbl = tk.Label(left, text=label_text, font=("Segoe UI", 10, "bold"), fg=COLOR_WHITE, bg=COLOR_BG_DARK)
        lbl.pack(anchor="w")
        if desc:
            dlbl = tk.Label(left, text=desc, font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_BG_DARK)
            dlbl.pack(anchor="w")

        val = self.get_val(var_key, default_val)
        var = tk.StringVar(value=val if val in options else default_val)
        self.vars[var_key] = var

        om = ttk.Combobox(frame, textvariable=var, values=options, state="readonly", width=24, font=("Segoe UI", 9))
        om.pack(side=tk.RIGHT, padx=5)
        return frame

    def create_row_toggle(self, parent, label_text, var_key, default_val="0", desc=""):
        frame = tk.Frame(parent, bg=COLOR_BG_DARK, pady=8)
        frame.pack(fill=tk.X, padx=20)

        left = tk.Frame(frame, bg=COLOR_BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        lbl = tk.Label(left, text=label_text, font=("Segoe UI", 10, "bold"), fg=COLOR_WHITE, bg=COLOR_BG_DARK)
        lbl.pack(anchor="w")
        if desc:
            dlbl = tk.Label(left, text=desc, font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_BG_DARK)
            dlbl.pack(anchor="w")

        curr = self.get_val(var_key, default_val)
        var = tk.StringVar(value="1" if curr in ("1", "true", "on") else "0")
        self.vars[var_key] = var

        cb = tk.Checkbutton(frame, variable=var, onvalue="1", offvalue="0",
                            bg=COLOR_BG_DARK, activebackground=COLOR_BG_DARK,
                            selectcolor=COLOR_CARD, bd=0, highlightthickness=0)
        cb.pack(side=tk.RIGHT, padx=5)
        return frame

    def create_row_slider(self, parent, label_text, var_key, from_, to_, default_val, unit="%", desc=""):
        frame = tk.Frame(parent, bg=COLOR_BG_DARK, pady=8)
        frame.pack(fill=tk.X, padx=20)

        left = tk.Frame(frame, bg=COLOR_BG_DARK)
        left.pack(side=tk.LEFT, fill=tk.X, expand=True)

        curr_raw = self.get_val(var_key, str(default_val))
        try:
            curr_val = int(curr_raw)
        except ValueError:
            curr_val = int(default_val)

        var = tk.IntVar(value=curr_val)
        self.vars[var_key] = var

        val_lbl = tk.Label(frame, text=f"{curr_val} {unit}", font=("Segoe UI", 9, "bold"),
                           fg=COLOR_GOLD, bg=COLOR_BG_DARK, width=8, anchor="e")
        val_lbl.pack(side=tk.RIGHT)

        lbl = tk.Label(left, text=label_text, font=("Segoe UI", 10, "bold"), fg=COLOR_WHITE, bg=COLOR_BG_DARK)
        lbl.pack(anchor="w")
        if desc:
            dlbl = tk.Label(left, text=desc, font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_BG_DARK)
            dlbl.pack(anchor="w")

        def on_slide(val):
            val_lbl.config(text=f"{int(float(val))} {unit}")

        slider = tk.Scale(frame, from_=from_, to=to_, orient=tk.HORIZONTAL, variable=var,
                          showvalue=0, bg=COLOR_BG_DARK, fg=COLOR_WHITE,
                          troughcolor=COLOR_CARD, highlightthickness=0, bd=0,
                          activebackground=COLOR_GOLD, length=160, command=on_slide)
        slider.pack(side=tk.RIGHT, padx=10)
        return frame

    def build_display_tab(self):
        f = self.tab_display
        self.create_row_toggle(f, "Exclusive Fullscreen", "fullscreen", "1", "Start directly in true fullscreen window.")
        self.create_row_dropdown(f, "Window Resolution", "window_size",
                                 ["3840x2160", "2560x1440", "1920x1080", "1280x720", "3440x1440", "5120x1440"],
                                 "1920x1080", "Target display resolution for rendering & window bounds.")
        self.create_row_dropdown(f, "Frame Rate Limit", "fps_limit",
                                 ["30", "60", "90", "120", "144", "display"], "120",
                                 "Max frame rate cap. 'display' automatically synchronizes with monitor Hz.")
        self.create_row_dropdown(f, "V-Sync / Presentation Mode", "vk_present",
                                 ["mailbox", "fifo", "immediate"], "mailbox",
                                 "Mailbox (Smooth low-latency VSync), FIFO (Strict VSync), Immediate (Tearing/Raw).")
        self.create_row_dropdown(f, "Aspect Ratio Behavior", "aspect",
                                 ["fit", "stretch"], "fit",
                                 "Fit preserves 16:9 picture with pillarboxes on ultrawide; stretch fills monitor.")
        self.create_row_slider(f, "Field of View (FOV)", "fov", 70, 140, 100, "%",
                               "Expands or narrows player camera view (100% is Switch default).")

    def build_upscale_tab(self):
        f = self.tab_upscale
        self.create_row_dropdown(f, "Upscaler Technology", "upscaler",
                                 ["dlss", "fsr4", "fsr", "xess", "bilinear", "off"], "dlss",
                                 "Deep Learning Super Sampling, FSR 4.1.2/1.0, Intel XeSS, or native rasterization.")
        self.create_row_dropdown(f, "DLSS Quality Preset", "upscaler_preset",
                                 ["dlaa", "quality", "balanced", "performance", "ultra_performance"], "quality",
                                 "DLAA renders native 100% scene. Quality (67%), Balanced (58%), Performance (50%).")
        self.create_row_dropdown(f, "DLSS Neural Model Generation", "dlss_preset",
                                 ["preset_m", "preset_k", "preset_j", "preset_l", "preset_e", "preset_c"], "preset_m",
                                 "Preset M is newest generation (v3.10). Preset K/J/L offer tuned ghosting profiles.")
        self.create_row_dropdown(f, "Frame Generation Mode", "fg_mode",
                                 ["off", "dlss_fg", "fsr3_fg", "fsr4_fg", "xefg"], "off",
                                 "Synthesize AI intermediate frames to double/multiply framerates.")
        self.create_row_dropdown(f, "Frame Gen Multiplier", "fg_mult",
                                 ["2x", "3x", "4x", "6x"], "2x",
                                 "Multi-Frame Generation (2x standard; 4x/6x supported on RTX 50 / XeFG).")
        self.create_row_dropdown(f, "Low Latency Mode", "reflex",
                                 ["boost", "on", "off"], "boost",
                                 "NVIDIA Reflex low latency (boost locks high GPU clocks to minimize input lag).")

    def build_graphics_tab(self):
        f = self.tab_graphics
        self.create_row_dropdown(f, "Sun Shadow Resolution", "shadow_res",
                                 ["game", "512", "768", "1024", "1536", "2048"], "1024",
                                 "Shadow map size (2048 is ultra crisp; game uses dynamic 400-960).")
        self.create_row_dropdown(f, "Shadow Cascade Range", "shadow_range",
                                 ["100", "150", "200", "300"], "200",
                                 "Moves shadow draw distance out into the horizon (200 = 320m, 300 = 480m).")
        self.create_row_slider(f, "Soft Sun Shadows (PCSS)", "pcss", 0, 200, 10, "%",
                               "Physically plausible penumbra width (0 = hard edge, 10-50 = realistic blur).")
        self.create_row_dropdown(f, "Ambient Occlusion (AO)", "ao_mode",
                                 ["native", "ssao", "hbao", "xegtao", "off"], "ssao",
                                 "Intel XeGTAO (Ground Truth), HBAO, SSAO Enhanced, or Native game shading.")
        self.create_row_slider(f, "Contact Shadows", "contact_shadows", 0, 100, 50, "%",
                               "Screen-space micro shadows under feet, pebbles, grass, and creases.")
        self.create_row_dropdown(f, "Anisotropic Texture Filtering", "aniso",
                                 ["game", "2", "4", "8", "16"], "16",
                                 "16x keeps distant ground, cliffs, and roads sharp at oblique angles.")
        self.create_row_dropdown(f, "Color Profile", "color_preset",
                                 ["default", "vivid", "clarity", "custom"], "default",
                                 "Custom tuning presets for vibrancy, gamma, contrast, and black level.")

    def build_audio_tab(self):
        f = self.tab_audio
        self.create_row_dropdown(f, "Audio Channels", "audio_channels",
                                 ["stereo", "surround51", "surround71"], "stereo",
                                 "Output speaker configuration.")
        self.create_row_dropdown(f, "Controller Button Prompts", "pad_layout",
                                 ["auto", "dualsense", "dualshock4", "xbox", "pc"], "auto",
                                 "Auto detects controller, or force DualSense, Xbox, or Keyboard icons.")
        self.create_row_toggle(f, "Direct Mouse Camera Aiming", "mouse_mode", "1",
                               "Allows direct 1:1 raw mouse input for archery and camera rotation.")

    def save_and_close(self):
        updates = {}
        for k, var in self.vars.items():
            updates[k] = str(var.get())
        if save_ini_settings(INI_PATH, updates):
            messagebox.showinfo("Settings Saved", "Settings successfully saved to totk.ini!")
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to write to totk.ini!")

    def restore_defaults(self):
        if messagebox.askyesno("Restore Defaults", "Reset all settings to recommended defaults?"):
            defaults = {
                "fullscreen": "1",
                "window_size": "1920x1080",
                "fps_limit": "120",
                "vk_present": "mailbox",
                "aspect": "fit",
                "fov": "100",
                "upscaler": "dlss",
                "upscaler_preset": "quality",
                "dlss_preset": "preset_m",
                "fg_mode": "off",
                "reflex": "boost",
                "shadow_res": "1024",
                "shadow_range": "200",
                "pcss": "10",
                "ao_mode": "ssao",
                "contact_shadows": "50",
                "aniso": "16",
                "color_preset": "default",
                "pad_layout": "auto"
            }
            for k, val in defaults.items():
                if k in self.vars:
                    self.vars[k].set(val)


# --- Sony-style Main Launcher Window ---
class SonyLauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("The Legend of Zelda: Tears of the Kingdom - PC Recompiled")
        self.geometry("1120x630")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)

        # Set taskbar icon if available
        ico_path = get_base_dir() / "totk.ico"
        if not ico_path.is_file():
            ico_path = GAME_DIR / "runtime" / "totk.ico"
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        # Center on screen
        self.update_idletasks()
        w = 1120
        h = 630
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.launcher_cfg = load_launcher_config()

        self.setup_background()
        self.setup_ui_overlay()

    def setup_background(self):
        bg_path = get_base_dir() / "background.jpg"
        if not bg_path.is_file():
            bg_path = Path(r"C:\Games\totk-pc-recomp-src\launcher\background.jpg")

        self.canvas = tk.Canvas(self, width=1120, height=630, highlightthickness=0, bg=COLOR_BG_DARK)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        if bg_path.is_file():
            try:
                im = Image.open(bg_path).convert("RGBA")
                im = im.resize((1120, 630), Image.Resampling.LANCZOS)
                
                # Apply custom dark gradient on left third for contrast
                gradient = Image.new("RGBA", (1120, 630), (0, 0, 0, 0))
                for gx in range(500):
                    alpha = int(220 * (1.0 - (gx / 500.0) ** 0.8))
                    for gy in range(630):
                        gradient.putpixel((gx, gy), (10, 12, 16, alpha))
                im = Image.alpha_composite(im, gradient)

                self.bg_img = ImageTk.PhotoImage(im)
                self.canvas.create_image(0, 0, image=self.bg_img, anchor="nw")
            except Exception as e:
                print(f"Error loading background image: {e}")

    def setup_ui_overlay(self):
        # 1. Title & Logo Header (Top-Left)
        self.canvas.create_text(70, 65, text="THE LEGEND OF ZELDA™",
                                font=("Segoe UI", 11, "bold"), fill=COLOR_GOLD, anchor="w")
        self.canvas.create_text(70, 105, text="TEARS OF THE KINGDOM",
                                font=("Impact", 36), fill=COLOR_WHITE, anchor="w")
        self.canvas.create_text(70, 142, text="PC RECOMPILED  ·  STEEL TEMPLE COMPLETE EDITION",
                                font=("Segoe UI", 10, "bold"), fill=COLOR_ACCENT_GREEN, anchor="w")

        # 2. Sony-style Main Menu Options (Left side)
        menu_items = [
            ("PLAY", self.launch_game, True),
            ("SETTINGS", self.open_settings, False),
            ("DIGITAL EXTRAS", self.open_extras, False),
            ("QUIT", self.destroy, False)
        ]

        start_y = 230
        gap = 62

        for i, (text, cmd, is_play) in enumerate(menu_items):
            y = start_y + (i * gap)
            default_color = COLOR_GOLD if is_play else COLOR_WHITE
            txt_id = self.canvas.create_text(70, y, text=text,
                                             font=("Segoe UI", 22, "bold"),
                                             fill=default_color, anchor="w", tags=f"btn_{i}")

            # Hover events
            def on_enter(e, tid=txt_id, ip=is_play):
                self.canvas.itemconfig(tid, fill=COLOR_GOLD_HOVER if ip else COLOR_GOLD)
                self.config(cursor="hand2")

            def on_leave(e, tid=txt_id, dc=default_color):
                self.canvas.itemconfig(tid, fill=dc)
                self.config(cursor="")

            def on_click(e, fn=cmd):
                fn()

            self.canvas.tag_bind(txt_id, "<Enter>", on_enter)
            self.canvas.tag_bind(txt_id, "<Leave>", on_leave)
            self.canvas.tag_bind(txt_id, "<Button-1>", on_click)

        # 3. Bottom Right Controls: Show Launcher Checkbox & Version
        self.show_launcher_var = tk.BooleanVar(value=self.launcher_cfg.get("show_launcher", True))

        def on_toggle_launcher():
            self.launcher_cfg["show_launcher"] = self.show_launcher_var.get()
            save_launcher_config(self.launcher_cfg)

        cb_frame = tk.Frame(self, bg="#000000", bd=0)
        cb = tk.Checkbutton(self.canvas, text="SHOW LAUNCHER", variable=self.show_launcher_var,
                            command=on_toggle_launcher, font=("Segoe UI", 9, "bold"),
                            fg=COLOR_WHITE, bg=COLOR_BG_DARK, activebackground=COLOR_BG_DARK,
                            activeforeground=COLOR_GOLD, selectcolor=COLOR_CARD, bd=0, highlightthickness=0)
        self.canvas.create_window(980, 560, window=cb, anchor="e")

        # Version Text
        self.canvas.create_text(980, 590, text=f"V {VERSION_STRING}",
                                font=("Segoe UI", 9, "bold"), fill=COLOR_TEXT_DIM, anchor="e")

        # GitHub Link Button on Canvas (Bottom-Center / Left)
        gh_btn = tk.Button(self.canvas, text="★ GitHub Repository (STS78721)",
                           font=("Segoe UI", 8, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD,
                           activebackground=COLOR_CARD_BORDER, activeforeground=COLOR_GOLD_HOVER,
                           bd=1, relief="solid", padx=10, pady=4, cursor="hand2",
                           command=lambda: webbrowser.open(GITHUB_URL))
        self.canvas.create_window(70, 580, window=gh_btn, anchor="w")

    def launch_game(self):
        exe_path = GAME_DIR / "totk.exe"
        if not exe_path.is_file():
            messagebox.showerror("Error", f"totk.exe not found at:\n{exe_path}")
            return

        try:
            subprocess.Popen([str(exe_path)], cwd=str(GAME_DIR))
            self.destroy()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to start totk.exe:\n{e}")

    def open_settings(self):
        SonySettingsDialog(self)

    def open_extras(self):
        # Open sleek popup menu with directory shortcuts & guides
        menu = tk.Menu(self, tearoff=0, bg=COLOR_CARD, fg=COLOR_WHITE,
                       activebackground=COLOR_GOLD, activeforeground="#000000",
                       font=("Segoe UI", 10, "bold"), bd=1)

        def open_dir(d, title):
            p = GAME_DIR / d
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))

        menu.add_command(label="🌐  Visit GitHub Repository", command=lambda: webbrowser.open(GITHUB_URL))
        menu.add_separator()
        menu.add_command(label="📁  Open Mods Folder (mods/)", command=lambda: open_dir("mods", "Mods"))
        menu.add_command(label="💾  Open Save Directory (profile/save/)", command=lambda: open_dir("profile/save", "Saves"))
        menu.add_command(label="🔮  Open Amiibo Dumps (amiibo/)", command=lambda: open_dir("amiibo", "Amiibo"))
        menu.add_separator()
        menu.add_command(label="🎮  View In-Game Controller Guide", command=self.open_controller_guide)

        # Show menu under mouse or button position
        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def open_controller_guide(self):
        guide_p = GAME_DIR / "CONTROLLER_GUIDE.txt"
        if guide_p.is_file():
            os.startfile(str(guide_p))
        else:
            messagebox.showinfo("Guide", "CONTROLLER_GUIDE.txt not found in game directory.")


def main():
    # If launched with --game or directly when show_launcher is disabled and shift isn't held
    cfg = load_launcher_config()
    
    # Check if user holds Shift key on Windows
    shift_pressed = False
    try:
        import ctypes
        shift_pressed = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0
    except Exception:
        pass

    if not cfg.get("show_launcher", True) and not shift_pressed and "--launcher" not in sys.argv:
        exe_path = GAME_DIR / "totk.exe"
        if exe_path.is_file():
            subprocess.Popen([str(exe_path)], cwd=str(GAME_DIR))
            sys.exit(0)

    app = SonyLauncherApp()
    app.mainloop()

if __name__ == "__main__":
    main()
