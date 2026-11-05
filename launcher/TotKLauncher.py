"""The Legend of Zelda: Tears of the Kingdom - PC Recompiled (SteelTemple Edition)
Standalone Sony/Nixxes-style Launcher & Settings Manager.
"""

import os
import sys
import json
import re
import subprocess
import webbrowser
import threading
import urllib.request
import urllib.error
import ctypes
from ctypes import wintypes
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# --- Color Palette (Sony / Nixxes Inspired + Zonai Glow) ---
COLOR_BG_DARK = "#0a0c10"
COLOR_GOLD = "#ffd24d"
COLOR_GOLD_HOVER = "#fff2a3"
COLOR_WHITE = "#ffffff"
COLOR_TEXT_DIM = "#9ba3af"
COLOR_CARD = "#12161f"
COLOR_CARD_BORDER = "#252e3d"
COLOR_ACCENT_GREEN = "#1dd1a1"
COLOR_TAB_ACTIVE = "#1f2736"
COLOR_BUTTON_HOVER = "#2a3547"
COLOR_TRACK_BG = "#263040"
COLOR_TRACK_ACTIVE = "#ffd24d"

GITHUB_URL = "https://github.com/STS78721/totk-pc-recomp-SteelTempleBuild"
VERSION_STRING = "Beta 5e Hotfix"
RELEASES_API_URL = "https://api.github.com/repos/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest"

class _DEVMODE(ctypes.Structure):
    _fields_ = [("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
                ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
                ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
                ("dmOrientation", ctypes.c_short), ("dmPaperSize", ctypes.c_short),
                ("dmPaperLength", ctypes.c_short), ("dmPaperWidth", ctypes.c_short),
                ("dmScale", ctypes.c_short), ("dmCopies", ctypes.c_short),
                ("dmDefaultSource", ctypes.c_short), ("dmPrintQuality", ctypes.c_short),
                ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
                ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
                ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
                ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
                ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD),
                ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
                ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
                ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD)]

class _RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

class _MONITORINFOEX(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", _RECT), ("rcWork", _RECT),
                ("dwFlags", wintypes.DWORD), ("szDevice", wintypes.WCHAR * 32)]

def enumerate_displays():
    """Return connected active Win32 monitors in EnumDisplayMonitors order."""
    displays = []
    try:
        user32 = ctypes.windll.user32
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                           ctypes.POINTER(_RECT), wintypes.LPARAM)
        user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(_MONITORINFOEX)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL
        user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(_DEVMODE)]
        user32.EnumDisplaySettingsW.restype = wintypes.BOOL
        user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(_RECT), callback_type, wintypes.LPARAM]
        user32.EnumDisplayMonitors.restype = wintypes.BOOL

        def visit(handle, _dc, _rect, _data):
            info = _MONITORINFOEX()
            info.cbSize = ctypes.sizeof(info)
            if not user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                return True
            mode = _DEVMODE()
            mode.dmSize = ctypes.sizeof(mode)
            user32.EnumDisplaySettingsW(info.szDevice, -1, ctypes.byref(mode))
            width = mode.dmPelsWidth or (info.rcMonitor.right - info.rcMonitor.left)
            height = mode.dmPelsHeight or (info.rcMonitor.bottom - info.rcMonitor.top)
            index = len(displays) + 1
            primary = bool(info.dwFlags & 1)
            displays.append({
                "index": index, "device": info.szDevice, "width": int(width), "height": int(height),
                "resolution": f"{width}x{height}", "refresh": int(mode.dmDisplayFrequency or 60),
                "left": int(info.rcMonitor.left), "top": int(info.rcMonitor.top),
                "monitor_width": int(info.rcMonitor.right - info.rcMonitor.left),
                "monitor_height": int(info.rcMonitor.bottom - info.rcMonitor.top), "primary": primary,
            })
            return True

        callback = callback_type(visit)
        user32.EnumDisplayMonitors(None, None, callback, 0)
    except Exception:
        pass
    if not displays:
        resolution, refresh = _detect_primary_display_mode()
        width, height = (int(part) for part in resolution.split("x", 1))
        displays.append({"index": 1, "device": "PRIMARY", "width": width, "height": height,
                         "resolution": resolution, "refresh": refresh, "left": 0, "top": 0,
                         "monitor_width": width, "monitor_height": height, "primary": True})
    return displays

def display_label(display):
    suffix = " (Primary)" if display["primary"] else ""
    return f"Display {display['index']}: {display['resolution']}{suffix}"

def place_window_on_monitor(window, monitor):
    """Center a Tk window in a monitor's work area using Win32 screen coordinates."""
    window.update_idletasks()
    width, height = window.winfo_width(), window.winfo_height()
    left = monitor["left"] + max(0, (monitor["monitor_width"] - width) // 2)
    top = monitor["top"] + max(0, (monitor["monitor_height"] - height) // 2)
    try:
        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int, wintypes.UINT]
        user32.SetWindowPos.restype = wintypes.BOOL
        hwnd = user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT: Tk's outer window, including its title bar.
        if not hwnd or not user32.SetWindowPos(hwnd, None, left, top, width, height, 0x0014):
            window.geometry(f"{width}x{height}+{left}+{top}")
    except Exception:
        window.geometry(f"{width}x{height}+{left}+{top}")

def play_ui_sound(kind):
    """Play a bundled short UI chime asynchronously when sound is enabled."""
    if not getattr(play_ui_sound, "enabled", True):
        return
    try:
        import winsound
        filename = "hover.wav" if kind == "hover" else "click.wav"
        sound_path = get_base_dir() / "sounds" / filename
        winsound.PlaySound(str(sound_path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass

def _detect_primary_display_mode():
    """Read the current primary display mode from Win32, with safe fallbacks."""
    try:
        mode = _DEVMODE()
        mode.dmSize = ctypes.sizeof(mode)
        if ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(mode)):
            if mode.dmPelsWidth and mode.dmPelsHeight:
                return f"{mode.dmPelsWidth}x{mode.dmPelsHeight}", int(mode.dmDisplayFrequency or 60)
    except Exception:
        pass
    return "1920x1080", 60

def detect_primary_display():
    """Read the current primary display mode from Win32, with safe fallbacks."""
    primary = next((display for display in enumerate_displays() if display["primary"]), None)
    return (primary["resolution"], primary["refresh"]) if primary else _detect_primary_display_mode()

def detect_gpu():
    """Return the first Windows video controller's name and vendor."""
    try:
        command = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, text=True, timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        names = json.loads(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else []
        if isinstance(names, str):
            names = [names]
        if names:
            # Prefer the discrete vendor when a system has both an integrated and discrete adapter.
            names.sort(key=lambda name: (not any(v in name.lower() for v in ("nvidia", "geforce", "amd", "radeon")), name))
            name = names[0]
            low = name.lower()
            vendor = "NVIDIA" if any(v in low for v in ("nvidia", "geforce")) else "AMD" if any(v in low for v in ("amd", "radeon")) else "Intel" if "intel" in low else "Other"
            return name, vendor
    except Exception:
        pass
    return "GPU not detected", "Other"

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
    pat_active = re.compile(rf'^\s*{re.escape(key)}\s*=.*$', re.IGNORECASE)
    pat_commented = re.compile(rf'^\s*[#;]\s*{re.escape(key)}\s*=.*$', re.IGNORECASE)
    
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
    if not ini_file.is_file():
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


# --- High-Contrast Custom Slider (Sony / Nixxes Style) ---
class SonySlider(tk.Canvas):
    """Modern, high-visibility interactive slider with active fill and glow thumb."""
    def __init__(self, parent, from_, to_, initial, on_change=None, width=190, height=28, **kwargs):
        super().__init__(parent, width=width, height=height, bg=COLOR_BG_DARK, highlightthickness=0, **kwargs)
        self.from_ = from_
        self.to_ = to_
        self.val = int(initial)
        self.on_change = on_change
        self.w = width
        self.h = height
        self.pad = 12
        self.track_w = self.w - (2 * self.pad)
        self.y_mid = self.h // 2
        self.is_hovered = False

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<MouseWheel>", self.on_scroll)
        self.draw()

    def val_to_x(self, v):
        span = self.to_ - self.from_
        if span == 0:
            return self.pad
        frac = (v - self.from_) / float(span)
        return self.pad + (frac * self.track_w)

    def x_to_val(self, x):
        clamped_x = max(self.pad, min(x, self.w - self.pad))
        frac = (clamped_x - self.pad) / float(self.track_w)
        v = self.from_ + (frac * (self.to_ - self.from_))
        return int(round(v))

    def set(self, v):
        self.val = max(self.from_, min(self.to_, int(v)))
        self.draw()
        if self.on_change:
            self.on_change(self.val)

    def get(self):
        return self.val

    def on_click(self, e):
        self.set(self.x_to_val(e.x))

    def on_drag(self, e):
        self.set(self.x_to_val(e.x))

    def on_enter(self, e):
        self.is_hovered = True
        self.config(cursor="hand2")
        self.draw()

    def on_leave(self, e):
        self.is_hovered = False
        self.config(cursor="")
        self.draw()

    def on_scroll(self, e):
        step = 5 if (self.to_ - self.from_) > 50 else 1
        delta = step if e.delta > 0 else -step
        self.set(self.val + delta)

    def draw(self):
        self.delete("all")
        tx = self.val_to_x(self.val)
        
        # Inactive background track (clearly visible slate)
        self.create_line(self.pad, self.y_mid, self.w - self.pad, self.y_mid,
                         fill=COLOR_TRACK_BG, width=6, capstyle="round")
        
        # Active progress fill (bright gold)
        if tx > self.pad:
            self.create_line(self.pad, self.y_mid, tx, self.y_mid,
                             fill=COLOR_TRACK_ACTIVE, width=6, capstyle="round")
        
        # Glowing thumb ring
        r = 9 if not self.is_hovered else 10
        outer_color = COLOR_GOLD_HOVER if self.is_hovered else COLOR_GOLD
        self.create_oval(tx - r, self.y_mid - r, tx + r, self.y_mid + r,
                         fill=outer_color, outline="#ffffff", width=1.5)
        
        # Thumb center core
        self.create_oval(tx - 3, self.y_mid - 3, tx + 3, self.y_mid + 3,
                         fill=COLOR_BG_DARK, outline="")


# --- Sony / Nixxes Settings Dialog ---
class SonySettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Display & Graphics Settings")
        self.geometry("860x650")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)
        self.transient(parent)
        self.grab_set()

        self.ini_values = parse_ini(INI_PATH)
        self.vars = {}
        self.parent_app = parent
        self.monitors = enumerate_displays()
        saved_device = parent.launcher_cfg.get("target_display")
        self.target_monitor = next((monitor for monitor in self.monitors if monitor["device"] == saved_device),
                                   next((monitor for monitor in self.monitors if monitor["primary"]), self.monitors[0]))
        self.display_resolution, self.display_refresh = self.target_monitor["resolution"], self.target_monitor["refresh"]
        self.gpu_name, self.gpu_vendor = "Detecting GPU…", "Other"

        self.setup_ui()
        place_window_on_monitor(self, self.target_monitor)

    def get_val(self, key, default=""):
        return self.ini_values.get(key.lower(), default)

    def _detect_gpu_async(self):
        name, vendor = detect_gpu()
        self.after(0, lambda: self._show_gpu(name, vendor))

    def _show_gpu(self, name, vendor):
        self.gpu_name, self.gpu_vendor = name, vendor
        self.gpu_header.config(text=f"Detected: {name}", fg=COLOR_ACCENT_GREEN if vendor != "Other" else COLOR_TEXT_DIM)
        self._update_upscaler_advice()

    def _update_upscaler_advice(self, *_args):
        if not hasattr(self, "upscaler_note") or "upscaler" not in self.vars:
            return
        selected = self.vars["upscaler"].get()
        if selected == "dlss" and self.gpu_vendor != "NVIDIA":
            text, color = "DLSS requires an NVIDIA GPU. Consider AMD FSR or Intel XeSS.", COLOR_GOLD
        elif self.gpu_vendor == "AMD" and selected == "xess":
            text, color = "XeSS is available; AMD FSR is also a good match for this GPU.", COLOR_TEXT_DIM
        elif self.gpu_vendor == "Intel" and selected in ("fsr", "fsr4"):
            text, color = "Intel XeSS is also available and may suit this GPU well.", COLOR_TEXT_DIM
        else:
            text, color = "", COLOR_TEXT_DIM
        self.upscaler_note.config(text=text, fg=color)

    def setup_ui(self):
        # Header banner
        header = tk.Frame(self, bg=COLOR_CARD, height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        title_lbl = tk.Label(header, text="GAME SETTINGS & GRAPHICS CONFIGURATION",
                             font=("Segoe UI", 12, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD)
        title_lbl.pack(side=tk.LEFT, padx=25, pady=18)
        self.gpu_header = tk.Label(header, text="Detected: Detecting GPU…", font=("Segoe UI", 9), fg=COLOR_TEXT_DIM, bg=COLOR_CARD)
        self.gpu_header.pack(side=tk.RIGHT, padx=20)

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
        threading.Thread(target=self._detect_gpu_async, daemon=True).start()

        # Bottom Bar
        bottom_bar = tk.Frame(self, bg=COLOR_CARD, height=64)
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
        btn_save.pack(side=tk.RIGHT, padx=(10, 25), pady=14)

        btn_cancel = make_btn(bottom_bar, "CANCEL", self.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=10, pady=14)

        btn_default = make_btn(bottom_bar, "RESTORE DEFAULTS", self.restore_defaults)
        btn_default.pack(side=tk.LEFT, padx=25, pady=14)

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

        lbl = tk.Label(left, text=label_text, font=("Segoe UI", 10, "bold"), fg=COLOR_WHITE, bg=COLOR_BG_DARK)
        lbl.pack(anchor="w")
        if desc:
            dlbl = tk.Label(left, text=desc, font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_BG_DARK)
            dlbl.pack(anchor="w")

        curr_raw = self.get_val(var_key, str(default_val))
        try:
            curr_val = int(curr_raw)
        except ValueError:
            curr_val = int(default_val)

        var = tk.IntVar(value=curr_val)
        self.vars[var_key] = var

        # High-contrast rounded pill badge for value
        pill_frame = tk.Frame(frame, bg=COLOR_CARD, bd=1, relief="solid", padx=8, pady=3)
        pill_frame.pack(side=tk.RIGHT, padx=(10, 0))

        val_lbl = tk.Label(pill_frame, text=f"{curr_val} {unit}", font=("Segoe UI", 9, "bold"),
                           fg=COLOR_GOLD, bg=COLOR_CARD, width=7, anchor="center")
        val_lbl.pack()

        def on_slide(new_val):
            val_lbl.config(text=f"{new_val} {unit}")
            var.set(new_val)

        slider = SonySlider(frame, from_, to_, curr_val, on_change=on_slide, width=190, height=28)
        slider.pack(side=tk.RIGHT, padx=5)
        return frame

    def build_display_tab(self):
        f = self.tab_display
        monitor_row = tk.Frame(f, bg=COLOR_BG_DARK, pady=8)
        monitor_row.pack(fill=tk.X, padx=20)
        tk.Label(monitor_row, text="Target Display Monitor", font=("Segoe UI", 10, "bold"),
                 fg=COLOR_WHITE, bg=COLOR_BG_DARK).pack(side=tk.LEFT, anchor="w")
        self.monitor_labels = {display_label(monitor): monitor for monitor in self.monitors}
        self.target_display_var = tk.StringVar(value=display_label(self.target_monitor))
        self.monitor_combo = ttk.Combobox(monitor_row, textvariable=self.target_display_var,
                                          values=list(self.monitor_labels), state="readonly", width=32,
                                          font=("Segoe UI", 9))
        self.monitor_combo.pack(side=tk.RIGHT, padx=5)
        self.monitor_combo.bind("<<ComboboxSelected>>", self.on_monitor_changed)
        self.create_row_toggle(f, "Exclusive Fullscreen", "fullscreen", "1", "Start directly in true fullscreen window.")
        resolutions = ["3840x2160", "2560x1440", "1920x1080", "1280x720", "3440x1440", "5120x1440"]
        if self.display_resolution not in resolutions:
            resolutions.insert(0, self.display_resolution)
        self.create_row_dropdown(f, "Window Resolution", "window_size",
                                 resolutions, self.get_val("window_size", self.display_resolution), "Target display resolution for rendering & window bounds.")
        self.resolution_combo = f.winfo_children()[-1].winfo_children()[-1]
        frame_rates = sorted(set(["30", "60", "90", "120", "144", str(self.display_refresh), "display"]),
                             key=lambda value: (value == "display", int(value) if value != "display" else 999))
        self.create_row_dropdown(f, "Frame Rate Limit", "fps_limit",
                                 frame_rates, self.get_val("fps_limit", str(self.display_refresh)),
                                 "Max frame rate cap. 'display' automatically synchronizes with monitor Hz.")
        self.fps_combo = f.winfo_children()[-1].winfo_children()[-1]

    def on_monitor_changed(self, _event=None):
        self.target_monitor = self.monitor_labels.get(self.target_display_var.get(), self.target_monitor)
        self.display_resolution = self.target_monitor["resolution"]
        self.display_refresh = self.target_monitor["refresh"]
        resolution_values = list(self.resolution_combo.cget("values"))
        if self.display_resolution not in resolution_values:
            resolution_values.insert(0, self.display_resolution)
        self.resolution_combo.configure(values=resolution_values)
        self.vars["window_size"].set(self.display_resolution)
        fps_values = list(self.fps_combo.cget("values"))
        refresh = str(self.display_refresh)
        if refresh not in fps_values:
            fps_values.insert(-1, refresh)
        self.fps_combo.configure(values=fps_values)
        self.vars["fps_limit"].set(refresh)
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
        self.upscaler_note = tk.Label(f, text="", font=("Segoe UI", 8), fg=COLOR_GOLD, bg=COLOR_BG_DARK, anchor="w")
        self.upscaler_note.pack(fill=tk.X, padx=22, pady=(0, 4))
        self.vars["upscaler"].trace_add("write", self._update_upscaler_advice)
        self._update_upscaler_advice()
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
        sound_row = tk.Frame(f, bg=COLOR_BG_DARK, pady=8)
        sound_row.pack(fill=tk.X, padx=20)
        self.sound_effects_var = tk.BooleanVar(value=self.parent_app.launcher_cfg.get("launcher_sound_effects", True))
        tk.Checkbutton(sound_row, text="Launcher Sound Effects", variable=self.sound_effects_var,
                       font=("Segoe UI", 10, "bold"), fg=COLOR_WHITE, bg=COLOR_BG_DARK,
                       activebackground=COLOR_BG_DARK, activeforeground=COLOR_GOLD,
                       selectcolor=COLOR_CARD, bd=0, highlightthickness=0, cursor="hand2").pack(side=tk.LEFT)

    def save_and_close(self):
        updates = {}
        for k, var in self.vars.items():
            updates[k] = str(var.get())
        if save_ini_settings(INI_PATH, updates):
            self.parent_app.launcher_cfg["target_display"] = self.target_monitor["device"]
            self.parent_app.launcher_cfg["launcher_sound_effects"] = self.sound_effects_var.get()
            save_launcher_config(self.parent_app.launcher_cfg)
            play_ui_sound.enabled = self.sound_effects_var.get()
            self.parent_app.move_to_monitor(self.target_monitor)
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
            self.sound_effects_var.set(True)


# --- Sony-style Main Launcher Window ---
class SonyLauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("The Legend of Zelda: Tears of the Kingdom - PC Recompiled")
        self.geometry("1120x630")
        self.resizable(False, False)
        self.configure(bg=COLOR_BG_DARK)

        ico_path = get_base_dir() / "totk.ico"
        if not ico_path.is_file():
            ico_path = GAME_DIR / "runtime" / "totk.ico"
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        # Clean graceful exit
        self.protocol("WM_DELETE_WINDOW", self.safe_quit)

        # Center on screen
        self.update_idletasks()
        w = 1120
        h = 630
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.launcher_cfg = load_launcher_config()
        play_ui_sound.enabled = bool(self.launcher_cfg.get("launcher_sound_effects", True))

        self.setup_background()
        self.setup_ui_overlay()
        monitor = next((entry for entry in enumerate_displays()
                        if entry["device"] == self.launcher_cfg.get("target_display")), None)
        if monitor:
            self.move_to_monitor(monitor)

    def move_to_monitor(self, monitor):
        place_window_on_monitor(self, monitor)

    def safe_quit(self):
        """Clean and instant exit preventing Tcl 9 alloc panics."""
        os._exit(0)

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
                
                # Apply custom dark gradient on left third and bottom for high contrast
                gradient = Image.new("RGBA", (1120, 630), (0, 0, 0, 0))
                for gx in range(540):
                    alpha = int(225 * (1.0 - (gx / 540.0) ** 0.8))
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
            ("QUIT", self.safe_quit, False)
        ]

        start_y = 230
        gap = 62

        for i, (text, cmd, is_play) in enumerate(menu_items):
            y = start_y + (i * gap)
            default_color = COLOR_GOLD if is_play else COLOR_WHITE
            txt_id = self.canvas.create_text(70, y, text=text,
                                             font=("Segoe UI", 22, "bold"),
                                             fill=default_color, anchor="w", tags=f"btn_{i}")

            def on_enter(e, tid=txt_id, ip=is_play):
                play_ui_sound("hover")
                self.canvas.itemconfig(tid, fill=COLOR_GOLD_HOVER if ip else COLOR_GOLD)
                self.config(cursor="hand2")

            def on_leave(e, tid=txt_id, dc=default_color):
                self.canvas.itemconfig(tid, fill=dc)
                self.config(cursor="")

            def on_click(e, fn=cmd):
                play_ui_sound("click")
                fn()

            self.canvas.tag_bind(txt_id, "<Enter>", on_enter)
            self.canvas.tag_bind(txt_id, "<Leave>", on_leave)
            self.canvas.tag_bind(txt_id, "<Button-1>", on_click)

        # 3. Bottom Right Controls in High-Contrast Frosted Dark Card
        footer_card = tk.Frame(self, bg=COLOR_CARD, bd=1, relief="solid", padx=16, pady=10)
        
        self.show_launcher_var = tk.BooleanVar(value=self.launcher_cfg.get("show_launcher", True))

        def on_toggle_launcher():
            self.launcher_cfg["show_launcher"] = self.show_launcher_var.get()
            save_launcher_config(self.launcher_cfg)

        cb = tk.Checkbutton(footer_card, text="SHOW LAUNCHER", variable=self.show_launcher_var,
                            command=on_toggle_launcher, font=("Segoe UI", 10, "bold"),
                            fg=COLOR_WHITE, bg=COLOR_CARD, activebackground=COLOR_CARD,
                            activeforeground=COLOR_GOLD, selectcolor=COLOR_CARD_BORDER,
                            bd=0, highlightthickness=0, cursor="hand2")
        cb.pack(anchor="e")

        # Crisp, high-contrast version label
        ver_lbl = tk.Label(footer_card, text=f"V {VERSION_STRING}",
                           font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD)
        ver_lbl.pack(anchor="e", pady=(4, 0))

        self.update_status = tk.Label(footer_card, text="", font=("Segoe UI", 8), fg=COLOR_ACCENT_GREEN,
                                      bg=COLOR_CARD, wraplength=230, justify="right")
        self.update_status.pack(anchor="e", pady=(4, 0))
        update_btn = tk.Button(footer_card, text="CHECK FOR UPDATES", font=("Segoe UI", 8, "bold"),
                               fg=COLOR_WHITE, bg=COLOR_BUTTON_HOVER, activebackground=COLOR_GOLD,
                               activeforeground="#000000", bd=0, padx=10, pady=5, cursor="hand2",
                               command=self.check_for_updates)
        update_btn.pack(anchor="e", pady=(6, 0))

        self.canvas.create_window(1050, 565, window=footer_card, anchor="se")

        # GitHub Link Button on Canvas (Bottom-Left)
        gh_btn = tk.Button(self.canvas, text="★ GitHub Repository (STS78721)",
                           font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD,
                           activebackground=COLOR_CARD_BORDER, activeforeground=COLOR_GOLD_HOVER,
                           bd=1, relief="solid", padx=14, pady=6, cursor="hand2",
                           command=lambda: webbrowser.open(GITHUB_URL))
        self.canvas.create_window(70, 570, window=gh_btn, anchor="w")

    def launch_game(self):
        exe_path = GAME_DIR / "totk.exe"
        if not exe_path.is_file():
            messagebox.showerror("Error", f"totk.exe not found at:\n{exe_path}")
            return

        try:
            subprocess.Popen([str(exe_path)], cwd=str(GAME_DIR))
            self.safe_quit()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to start totk.exe:\n{e}")

    def check_for_updates(self):
        self.update_status.config(text="Checking GitHub Releases…", fg=COLOR_TEXT_DIM)
        threading.Thread(target=self._check_releases_worker, daemon=True).start()

    def _check_releases_worker(self):
        try:
            request = urllib.request.Request(RELEASES_API_URL, headers={"Accept": "application/vnd.github+json",
                                                                        "User-Agent": "TotKLauncher"})
            with urllib.request.urlopen(request, timeout=12) as response:
                release = json.loads(response.read().decode("utf-8"))
            tag = release.get("tag_name", "").strip()
            title = release.get("name", "").strip() or tag
            page = release.get("html_url", GITHUB_URL + "/releases/latest")
            if not tag:
                raise ValueError("The latest release did not include a version tag.")
            self.after(0, lambda: self._show_release_result(tag, title, page))
        except Exception as exc:
            detail = str(exc)
            self.after(0, lambda: self.update_status.config(text=f"Update check failed: {detail}", fg="#ff7373"))

    def _show_release_result(self, tag, title, page):
        release_version = title.split(":", 1)[0].strip()
        if (tag.casefold() == VERSION_STRING.casefold() or title.casefold() == VERSION_STRING.casefold()
                or release_version.casefold() == VERSION_STRING.casefold()):
            self.update_status.config(text=f"You are on the latest build ({VERSION_STRING})!", fg=COLOR_ACCENT_GREEN)
            return
        self.update_status.config(text=f"Update available: {title}", fg=COLOR_GOLD)
        dialog = tk.Toplevel(self)
        dialog.title("Update Available")
        dialog.configure(bg=COLOR_BG_DARK)
        dialog.resizable(False, False)
        dialog.transient(self)
        tk.Label(dialog, text=f"A newer build is available:\n{title}", font=("Segoe UI", 11, "bold"),
                 fg=COLOR_WHITE, bg=COLOR_BG_DARK, padx=28, pady=22).pack()
        actions = tk.Frame(dialog, bg=COLOR_BG_DARK)
        actions.pack(pady=(0, 20))
        tk.Button(actions, text="Download on GitHub", command=lambda: (webbrowser.open(page), dialog.destroy()),
                  font=("Segoe UI", 9, "bold"), fg="#000000", bg=COLOR_GOLD, bd=0, padx=14, pady=8,
                  cursor="hand2").pack(side=tk.LEFT, padx=6)
        tk.Button(actions, text="Later", command=dialog.destroy, font=("Segoe UI", 9), fg=COLOR_WHITE,
                  bg=COLOR_BUTTON_HOVER, bd=0, padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=6)
        dialog.update_idletasks()
        dialog.geometry(f"+{self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2}+"
                        f"{self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2}")

    def open_settings(self):
        SonySettingsDialog(self)

    def open_extras(self):
        menu = tk.Menu(self, tearoff=0, bg=COLOR_CARD, fg=COLOR_WHITE,
                       activebackground=COLOR_GOLD, activeforeground="#000000",
                       font=("Segoe UI", 10, "bold"), bd=1)

        def open_dir(d, title):
            p = GAME_DIR / d
            p.mkdir(parents=True, exist_ok=True)
            os.startfile(str(p))

        menu.add_command(label="🌐  Visit GitHub Repository", command=lambda: webbrowser.open(GITHUB_URL))
        menu.add_command(label="⬆  Check for Updates", command=self.check_for_updates)
        menu.add_separator()
        menu.add_command(label="📁  Open Mods Folder (mods/)", command=lambda: open_dir("mods", "Mods"))
        menu.add_command(label="💾  Open Save Directory (profile/save/)", command=lambda: open_dir("profile/save", "Saves"))
        menu.add_command(label="🔮  Open Amiibo Dumps (amiibo/)", command=lambda: open_dir("amiibo", "Amiibo"))
        menu.add_separator()
        menu.add_command(label="🎮  View In-Game Controller Guide", command=self.open_controller_guide)

        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def open_controller_guide(self):
        guide_p = GAME_DIR / "CONTROLLER_GUIDE.txt"
        if guide_p.is_file():
            os.startfile(str(guide_p))
        else:
            messagebox.showinfo("Guide", "CONTROLLER_GUIDE.txt not found in game directory.")


def main():
    cfg = load_launcher_config()
    
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
            os._exit(0)

    app = SonyLauncherApp()
    app.mainloop()

if __name__ == "__main__":
    main()
