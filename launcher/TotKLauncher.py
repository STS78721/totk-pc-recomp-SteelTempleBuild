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
import runpy
import urllib.request
import urllib.error
import ctypes
import shutil
import tempfile
import zipfile
import time
import base64
from datetime import datetime
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
VERSION_STRING = "Beta 5h"
RELEASES_API_URL = "https://api.github.com/repos/STS78721/totk-pc-recomp-SteelTempleBuild/releases/latest"
MOD_DISABLED_SUFFIX = ".disabled"

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
    if os.name != "nt":
        resolution = os.environ.get("TOTK_DISPLAY_RESOLUTION", "1280x800")
        try:
            width, height = (int(part) for part in resolution.lower().split("x", 1))
        except (TypeError, ValueError):
            width, height = 1280, 800
        return [{"index": 1, "device": "PRIMARY", "width": width, "height": height,
                 "resolution": f"{width}x{height}", "refresh": 60, "left": 0, "top": 0,
                 "monitor_width": width, "monitor_height": height, "primary": True}]
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

def open_folder(path):
    """Open a folder with the host desktop's file manager."""
    path = str(path)
    try:
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            opener = shutil.which("xdg-open") or shutil.which("gio")
            if opener:
                subprocess.Popen([opener, "open", path] if Path(opener).name == "gio" else [opener, path])
    except (OSError, subprocess.SubprocessError):
        pass

def place_window_on_monitor(window, monitor):
    """Center a Tk window in a monitor's work area using Win32 screen coordinates."""
    window.update_idletasks()
    width, height = window.winfo_width(), window.winfo_height()
    if os.name != "nt":
        window.geometry(f"{width}x{height}+0+0")
        return
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
    if os.name != "nt":
        return os.environ.get("TOTK_DISPLAY_RESOLUTION", "1280x800"), 60
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
    if os.name != "nt":
        return "GPU detection unavailable on this platform", "Other"
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
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent)
    else:
        candidates.insert(0, Path(__file__).resolve().parent)
    for c in candidates:
        if (c / "totk.exe").is_file() or (c / "totk.ini").is_file():
            return c
    return Path.cwd()

GAME_DIR = find_game_dir()
INI_PATH = GAME_DIR / "totk.ini"
CONFIG_PATH = GAME_DIR / "launcher_config.json"
MODS_DIR = GAME_DIR / "mods"


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

UPDATE_FILES = {"totk.exe", "totklauncher.exe", "totk.ini", "totk.ini.example", "controller_guide.txt"}

def merge_update_ini(current_ini, update_ini, output_ini):
    """Preserve every existing user setting and add only new keys from an update's totk.ini."""
    current_ini, update_ini, output_ini = Path(current_ini), Path(update_ini), Path(output_ini)
    if not current_ini.is_file():
        shutil.copy2(update_ini, output_ini)
        return
    lines = current_ini.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
    existing = set(parse_ini(current_ini))
    additions = []
    for line in update_ini.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";", "[")) or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip().lower()
        if key and key not in existing:
            additions.append(line.rstrip("\r\n"))
            existing.add(key)
    if additions:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += "\n"
        lines.extend(["\n# New settings supplied by the update; existing values were preserved.\n"]
                     + [line + "\n" for line in additions])
    output_ini.write_text("".join(lines), encoding="utf-8")

def extract_update_archive(archive_path, stage_dir):
    """Validate the official flat update archive and stage only recognized root files."""
    archive_path, stage_dir = Path(archive_path), Path(stage_dir)
    selected = {}
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"Update archive CRC check failed for {bad_member}.")
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            path = Path(name.replace("\\", "/"))
            if path.is_absolute() or len(path.parts) != 1 or ".." in path.parts:
                raise ValueError(f"Unexpected path in update archive: {name}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError(f"Symbolic links are not allowed in updates: {name}")
            key = path.name.casefold()
            if key not in UPDATE_FILES:
                continue
            if key in selected:
                raise ValueError(f"Duplicate update file: {name}")
            if info.file_size <= 0:
                raise ValueError(f"Update file is empty: {name}")
            selected[key] = info
        for required in ("totk.exe", "totklauncher.exe"):
            if required not in selected:
                raise ValueError(f"Update archive is missing {required}.")
        if selected["totk.exe"].file_size < 1024 * 1024 or selected["totklauncher.exe"].file_size < 1024 * 1024:
            raise ValueError("Update executable is unexpectedly small.")
        for key, info in selected.items():
            target_name = {"totk.exe": "totk.exe", "totklauncher.exe": "TotKLauncher.exe",
                           "totk.ini": "totk.ini", "totk.ini.example": "totk.ini.example",
                           "controller_guide.txt": "CONTROLLER_GUIDE.txt"}[key]
            target = stage_dir / target_name
            if key == "totk.ini":
                incoming = stage_dir / "_update_totk.ini"
                with archive.open(info) as source, incoming.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
                merge_update_ini(GAME_DIR / "totk.ini", incoming, stage_dir / "totk.ini")
                incoming.unlink(missing_ok=True)
            else:
                with archive.open(info) as source, target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
    return sorted(("TotKLauncher.exe" if path.name.casefold() == "totklauncher.exe" else
                   "CONTROLLER_GUIDE.txt" if path.name.casefold() == "controller_guide.txt" else path.name)
                  for path in stage_dir.iterdir() if path.is_file() and path.name.casefold() in UPDATE_FILES)

def validate_update_game_executable(exe_path, game_dir, timeout=120):
    """Require the staged game binary to pass the active v1.4.3 loader probe before installation."""
    exe_path, game_dir = Path(exe_path), Path(game_dir)
    command = [str(exe_path), "--exefs", str(game_dir / "exefs"), "--romfs", str(game_dir / "romfs"),
               "--profile", str(game_dir / "profile"), "--probe-loader"]
    result = subprocess.run(command, cwd=str(game_dir), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=timeout)
    output = result.stdout + "\n" + result.stderr
    if (result.returncode != 0 or not re.search(r"game\s+1\.4\.3\b", output, re.IGNORECASE)
            or "probe-loader: passed (0 failures)" not in output):
        excerpt = output[-1800:].strip()
        raise RuntimeError("The update executable did not pass the required game 1.4.3 loader probe. "
                           "No GAME files were changed.\n" + excerpt)
    return output

def scan_mod_folders(mods_dir=MODS_DIR):
    """List immediate mod directories, including folders disabled with the .disabled suffix."""
    mods_dir = Path(mods_dir)
    mods_dir.mkdir(parents=True, exist_ok=True)
    found = []
    for folder in mods_dir.iterdir():
        if not folder.is_dir():
            continue
        disabled = folder.name.casefold().endswith(MOD_DISABLED_SUFFIX)
        name = folder.name[:-len(MOD_DISABLED_SUFFIX)] if disabled else folder.name
        if not name:
            continue
        found.append({"name": name, "path": folder, "enabled": not disabled})
    return sorted(found, key=lambda mod: (mod["name"].casefold(), mod["name"], not mod["enabled"]))

def set_mod_folder_enabled(folder, enabled):
    """Enable or disable one mod by restoring or appending the reserved suffix."""
    folder = Path(folder)
    is_disabled = folder.name.casefold().endswith(MOD_DISABLED_SUFFIX)
    if bool(enabled) == (not is_disabled):
        return folder
    if enabled:
        target = folder.with_name(folder.name[:-len(MOD_DISABLED_SUFFIX)])
    else:
        target = folder.with_name(folder.name + MOD_DISABLED_SUFFIX)
    if target.exists():
        raise FileExistsError(f"Cannot rename mod because '{target.name}' already exists.")
    return folder.rename(target)


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
        preset_box = tk.LabelFrame(f, text=" Presets ", font=("Segoe UI", 9, "bold"),
                                   fg=COLOR_GOLD, bg=COLOR_BG_DARK, bd=1,
                                   highlightthickness=1, highlightbackground=COLOR_CARD_BORDER,
                                   padx=12, pady=8, labelanchor="nw")
        preset_box.pack(fill=tk.X, padx=20, pady=(10, 4))
        self.handheld_preset_status = tk.Label(
            preset_box, text="Balanced handheld settings for Steam Deck and similar devices.",
            font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_BG_DARK, anchor="w")
        self.handheld_preset_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(preset_box, text="STEAM DECK / HANDHELD PRESET", command=self.apply_handheld_preset,
                  font=("Segoe UI", 8, "bold"), fg="#000000", bg=COLOR_GOLD,
                  activebackground=COLOR_GOLD_HOVER, bd=0, padx=12, pady=7,
                  cursor="hand2").pack(side=tk.RIGHT, padx=(10, 0))
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
        self.resolution_combo.bind("<<ComboboxSelected>>", self.on_resolution_changed)
        frame_rates = sorted(set(["30", "60", "90", "120", "144", str(self.display_refresh), "display"]),
                             key=lambda value: (value == "display", int(value) if value != "display" else 999))
        if "40" not in frame_rates:
            frame_rates.append("40")
        self.create_row_dropdown(f, "Frame Rate Limit", "fps_limit",
                                 frame_rates, self.get_val("fps_limit", str(self.display_refresh)),
                                 "Max frame rate cap. 'display' automatically synchronizes with monitor Hz.")
        self.fps_combo = f.winfo_children()[-1].winfo_children()[-1]

        self.ultrawide_card = tk.Frame(f, bg=COLOR_CARD, padx=14, pady=10,
                                       highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        uw_left = tk.Frame(self.ultrawide_card, bg=COLOR_CARD)
        uw_left.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ultrawide_title = tk.Label(uw_left, text="Ultrawide HUD layout available",
                                        font=("Segoe UI", 10, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD)
        self.ultrawide_title.pack(anchor="w")
        self.ultrawide_status = tk.Label(uw_left, text="Generate a matching layout patch from the installed RomFS.",
                                         font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_CARD,
                                         wraplength=340, justify="left")
        self.ultrawide_status.pack(anchor="w", pady=(3, 0))
        self.ultrawide_button = tk.Button(self.ultrawide_card, text="APPLY ULTRAWIDE HUD FIX",
                                          command=self.apply_ultrawide_patch, font=("Segoe UI", 9, "bold"),
                                          fg="#000000", bg=COLOR_GOLD, activebackground=COLOR_GOLD_HOVER,
                                          bd=0, padx=12, pady=8, cursor="hand2")
        self.ultrawide_button.pack(side=tk.RIGHT, padx=(12, 0))
        self.update_ultrawide_card()

    def apply_handheld_preset(self):
        """Apply Steam Deck-friendly settings to the pending dialog values."""
        preset = {
            "window_size": "1280x800",
            "fps_limit": "40",
            "upscaler": "fsr",
            "upscaler_preset": "balanced",
            "shadow_res": "768",
            "shadow_range": "100",
        }
        for key, value in preset.items():
            variable = self.vars.get(key)
            if variable is None:
                continue
            combo = self.resolution_combo if key == "window_size" else self.fps_combo if key == "fps_limit" else None
            if combo is not None:
                values = list(combo.cget("values"))
                if value not in values:
                    values.append(value)
                    combo.configure(values=values)
            variable.set(value)
        self.update_ultrawide_card()
        self.handheld_preset_status.config(
            text="Handheld preset selected. Choose SAVE & APPLY to write it to totk.ini.",
            fg=COLOR_ACCENT_GREEN)

    @staticmethod
    def apply_handheld_preset_values(values):
        """Pure helper for applying the handheld preset to a settings mapping."""
        values.update({"window_size": "1280x800", "fps_limit": "40", "upscaler": "fsr",
                       "upscaler_preset": "balanced", "shadow_res": "768", "shadow_range": "100"})
        return values

    @staticmethod
    def ultrawide_kind(resolution):
        try:
            width, height = (int(part) for part in resolution.lower().split("x", 1))
            ratio = width / height
        except (ValueError, ZeroDivisionError):
            return None
        if 3.3 <= ratio <= 3.8:
            return "32:9"
        if 2.25 <= ratio <= 2.55:
            return "21:9"
        return None

    def update_ultrawide_card(self):
        kind = self.ultrawide_kind(self.vars["window_size"].get())
        if kind:
            self.ultrawide_title.config(text=f"{kind} Ultrawide HUD layout available")
            self.ultrawide_card.pack(fill=tk.X, padx=20, pady=(5, 10))
        else:
            self.ultrawide_card.pack_forget()

    def on_resolution_changed(self, _event=None):
        self.update_ultrawide_card()
        res = self.vars["window_size"].get()
        if not self.ultrawide_kind(res):
            try:
                restore_installed_ui_mods(GAME_DIR)
            except Exception:
                pass

    def apply_ultrawide_patch(self):
        resolution = self.vars["window_size"].get()
        kind = self.ultrawide_kind(resolution)
        if not kind:
            self.update_ultrawide_card()
            return
        romfs = GAME_DIR / "romfs"
        index_path = romfs / "index.json"
        image_path = romfs / "romfs.bin"
        if not index_path.is_file() or not image_path.is_file():
            self.ultrawide_status.config(text="Installed RomFS (romfs/index.json and romfs/romfs.bin) was not found.",
                                         fg="#ff7b7b")
            return
        try:
            romfs_index = json.loads(index_path.read_text(encoding="utf-8"))
            paths = {entry.get("path", "") for entry in romfs_index.get("files", [])}
            version = "v143" if "UI/LayoutArchive/Common.Product.140.Nin_NX_NVN.blarc.zs" in paths else "v121"
        except (OSError, ValueError, TypeError) as exc:
            self.ultrawide_status.config(text=f"Could not read the RomFS index: {exc}", fg="#ff7b7b")
            return
        bundle_tool = get_base_dir() / "tools" / "make_romfs_patches.py"
        if not bundle_tool.is_file():
            bundle_tool = get_base_dir().parent / "tools" / "make_romfs_patches.py"
        if not bundle_tool.is_file():
            self.ultrawide_status.config(text="The bundled HUD patch tool was not found.", fg="#ff7b7b")
            return
        out = GAME_DIR / f"romfs-patches-{resolution}"
        self.ultrawide_button.config(state=tk.DISABLED, text="APPLYING…")
        self.ultrawide_status.config(text="Building the HUD layout from the installed RomFS…", fg=COLOR_TEXT_DIM)
        threading.Thread(target=self._ultrawide_patch_worker,
                         args=(resolution, kind, version, bundle_tool, romfs, out), daemon=True).start()

    def _ultrawide_patch_worker(self, resolution, kind, version, tool_path, romfs, out):
        try:
            if getattr(sys, "frozen", False):
                command = [sys.executable, "--run-ultrawide-patcher", resolution, version, str(romfs), str(out)]
            else:
                command = [sys.executable, str(Path(__file__).resolve()), "--run-ultrawide-patcher",
                           resolution, version, str(romfs), str(out)]
            result = subprocess.run(command, cwd=str(GAME_DIR), capture_output=True, text=True, timeout=900)
            if result.returncode != 0 or not (out / "manifest.tsv").is_file():
                detail = (result.stderr or result.stdout or "Patch tool failed without diagnostic output.").strip()
                raise RuntimeError(detail[-1200:])
            message = f"Ultrawide {kind} HUD patch applied successfully!"
            if "PATCHED_MODS=" in (result.stdout or ""):
                try:
                    for line in result.stdout.splitlines():
                        if line.startswith("PATCHED_MODS="):
                            cnt = int(line.split("=")[1].strip())
                            if cnt > 0:
                                message += f" (and adapted {cnt} UI mod(s))"
                            break
                except Exception:
                    pass
            color = COLOR_ACCENT_GREEN
        except Exception as exc:
            message = f"Could not apply the HUD patch: {exc}"
            color = "#ff7b7b"
        try:
            self.after(0, lambda: self._finish_ultrawide_patch(message, color))
        except tk.TclError:
            pass

    def _finish_ultrawide_patch(self, message, color):
        self.ultrawide_button.config(state=tk.NORMAL, text="APPLY ULTRAWIDE HUD FIX")
        self.ultrawide_status.config(text=message, fg=color)

    def on_monitor_changed(self, _event=None):
        self.target_monitor = self.monitor_labels.get(self.target_display_var.get(), self.target_monitor)
        self.display_resolution = self.target_monitor["resolution"]
        self.display_refresh = self.target_monitor["refresh"]
        resolution_values = list(self.resolution_combo.cget("values"))
        if self.display_resolution not in resolution_values:
            resolution_values.insert(0, self.display_resolution)
        self.resolution_combo.configure(values=resolution_values)
        self.vars["window_size"].set(self.display_resolution)
        self.update_ultrawide_card()
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
        warm_frame = tk.Frame(f, bg=COLOR_CARD, padx=14, pady=10,
                              highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
        warm_frame.pack(fill=tk.X, padx=20, pady=(8, 10))
        self.warm_status = tk.Label(warm_frame, text="Warm the saved Vulkan pipeline cache before playing.",
                                    font=("Segoe UI", 8), fg=COLOR_TEXT_DIM, bg=COLOR_CARD,
                                    wraplength=440, justify="left")
        self.warm_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.warm_button = tk.Button(warm_frame, text="⚡ PRE-WARM VULKAN SHADERS",
                                     command=self.prewarm_shaders, font=("Segoe UI", 8, "bold"),
                                     fg="#000000", bg=COLOR_GOLD, activebackground=COLOR_GOLD_HOVER,
                                     bd=0, padx=12, pady=8, cursor="hand2")
        self.warm_button.pack(side=tk.RIGHT, padx=(10, 0))

    def prewarm_shaders(self):
        if getattr(self, "warm_process_active", False):
            return
        exe = GAME_DIR / "totk.exe"
        if not exe.is_file():
            messagebox.showerror("Shader Pre-Warm", f"totk.exe was not found at:\n{exe}", parent=self)
            return
        self.warm_process_active = True
        self.warm_button.config(state=tk.DISABLED, text="PRE-WARMING…")
        self.warm_status.config(text="Compiling Vulkan pipeline cache for stutter-free gameplay...",
                                fg=COLOR_GOLD)
        threading.Thread(target=self._prewarm_worker, args=(exe,), daemon=True).start()

    def _prewarm_worker(self, exe):
        try:
            process = subprocess.Popen([str(exe), "--warm-shaders"], cwd=str(GAME_DIR),
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace", bufsize=1)
            self.warm_shader_process = process
            for _line in process.stdout:
                pass
            code = process.wait()
            if code == 0:
                message, color = "✅ Shaders optimized and pre-warmed! Ready for butter-smooth play.", COLOR_ACCENT_GREEN
            else:
                message, color = f"Shader pre-warm failed (exit code {code}). See GAME/logs for details.", "#ff7373"
        except Exception as exc:
            message, color = f"Shader pre-warm failed: {exc}", "#ff7373"
        try:
            self.after(0, lambda: self._finish_prewarm(message, color))
        except tk.TclError:
            pass

    def _finish_prewarm(self, message, color):
        self.warm_process_active = False
        self.warm_button.config(state=tk.NORMAL, text="⚡ PRE-WARM VULKAN SHADERS")
        self.warm_status.config(text=message, fg=color)

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


# --- Standalone 1-click Mod Manager ---
class ModsManagerDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("TotK Mod Manager")
        self.geometry("720x500")
        self.minsize(600, 380)
        self.configure(bg=COLOR_BG_DARK)
        self.transient(parent)
        self.parent_app = parent
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        header = tk.Frame(self, bg=COLOR_CARD, padx=22, pady=14)
        header.pack(fill=tk.X)
        tk.Label(header, text="MOD MANAGER", font=("Segoe UI", 14, "bold"),
                 fg=COLOR_GOLD, bg=COLOR_CARD).pack(anchor="w")
        tk.Label(header, text="Toggle installed mods. Disabled folders are kept as <mod>.disabled.",
                 font=("Segoe UI", 9), fg=COLOR_TEXT_DIM, bg=COLOR_CARD).pack(anchor="w", pady=(3, 0))

        list_frame = tk.Frame(self, bg=COLOR_BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=14)
        self.list_canvas = tk.Canvas(list_frame, bg=COLOR_BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.list_canvas.yview)
        self.list_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.rows = tk.Frame(self.list_canvas, bg=COLOR_BG_DARK)
        self.rows_window = self.list_canvas.create_window((0, 0), window=self.rows, anchor="nw")
        self.rows.bind("<Configure>", lambda _e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all")))
        self.list_canvas.bind("<Configure>", lambda e: self.list_canvas.itemconfigure(self.rows_window, width=e.width))

        footer = tk.Frame(self, bg=COLOR_CARD, height=62, padx=18)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        tk.Button(footer, text="OPEN MODS FOLDER", command=self.open_mods_folder,
                  font=("Segoe UI", 9, "bold"), fg="#000000", bg=COLOR_GOLD,
                  activebackground=COLOR_GOLD_HOVER, bd=0, padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, pady=12)
        tk.Button(footer, text="REFRESH", command=self.refresh,
                  font=("Segoe UI", 9, "bold"), fg=COLOR_WHITE, bg=COLOR_BUTTON_HOVER,
                  activebackground=COLOR_GOLD, bd=0, padx=14, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=10, pady=12)
        tk.Button(footer, text="CLOSE", command=self.destroy,
                  font=("Segoe UI", 9, "bold"), fg=COLOR_WHITE, bg=COLOR_BUTTON_HOVER,
                  activebackground=COLOR_GOLD, bd=0, padx=14, pady=8, cursor="hand2").pack(side=tk.RIGHT, pady=12)

        self.refresh()
        monitor = next((item for item in enumerate_displays()
                        if item["device"] == parent.launcher_cfg.get("target_display")), None)
        if monitor:
            place_window_on_monitor(self, monitor)

    def refresh(self):
        for child in self.rows.winfo_children():
            child.destroy()
        mods = scan_mod_folders()
        if not mods:
            tk.Label(self.rows, text="No mod folders found yet. Open the folder below and drop mods into it.",
                     font=("Segoe UI", 10), fg=COLOR_TEXT_DIM, bg=COLOR_BG_DARK,
                     wraplength=540, justify="left").pack(anchor="w", padx=10, pady=18)
            return
        for mod in mods:
            row = tk.Frame(self.rows, bg=COLOR_CARD, padx=12, pady=10,
                           highlightthickness=1, highlightbackground=COLOR_CARD_BORDER)
            row.pack(fill=tk.X, pady=4)
            enabled = tk.BooleanVar(value=mod["enabled"])
            check = tk.Checkbutton(row, text=mod["name"], variable=enabled,
                                   command=lambda path=mod["path"], var=enabled: self.toggle_mod(path, var),
                                   font=("Segoe UI", 10, "bold"), fg=COLOR_WHITE, bg=COLOR_CARD,
                                   activebackground=COLOR_CARD, activeforeground=COLOR_GOLD,
                                   selectcolor=COLOR_TAB_ACTIVE, bd=0, highlightthickness=0, cursor="hand2")
            check.pack(side=tk.LEFT, anchor="w")
            label = "ENABLED" if mod["enabled"] else "DISABLED"
            color = COLOR_ACCENT_GREEN if mod["enabled"] else COLOR_GOLD
            tk.Label(row, text=label, font=("Segoe UI", 8, "bold"), fg=color,
                     bg=COLOR_CARD).pack(side=tk.RIGHT, padx=8)

    def toggle_mod(self, folder, variable):
        try:
            set_mod_folder_enabled(folder, variable.get())
            self.refresh()
        except OSError as exc:
            messagebox.showerror("Mod Toggle Failed", str(exc), parent=self)
            self.refresh()

    def open_mods_folder(self):
        try:
            MODS_DIR.mkdir(parents=True, exist_ok=True)
            open_folder(MODS_DIR)
        except Exception as exc:
            messagebox.showerror("Cannot Open Mods Folder", str(exc), parent=self)


def create_save_snapshot(profile_dir, backups_dir=None, suffix=""):
    """Copy profile/save to a uniquely named snapshot beneath profile/backups."""
    profile_dir = Path(profile_dir)
    save_dir = profile_dir / "save"
    backups_dir = Path(backups_dir) if backups_dir else profile_dir / "backups"
    if not save_dir.is_dir():
        raise FileNotFoundError(f"Save folder not found: {save_dir}")
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = f"save_{stamp}" + (f"_{suffix}" if suffix else "")
    destination = backups_dir / base
    index = 2
    while destination.exists():
        destination = backups_dir / f"{base}_{index}"
        index += 1
    shutil.copytree(save_dir, destination)
    return destination

def restore_save_snapshot(profile_dir, snapshot_dir):
    """Create a pre-restore safety snapshot and replace profile/save transactionally."""
    profile_dir, snapshot_dir = Path(profile_dir), Path(snapshot_dir)
    save_dir, backups_dir = profile_dir / "save", profile_dir / "backups"
    try:
        snapshot_dir.resolve().relative_to(backups_dir.resolve())
    except ValueError:
        raise ValueError("The selected snapshot is outside the profile backup folder.") from None
    if not snapshot_dir.is_dir() or not any(snapshot_dir.iterdir()):
        raise ValueError("The selected snapshot is missing or empty.")
    safety = create_save_snapshot(profile_dir, backups_dir, "before-restore")
    staged = profile_dir / f".save-restore-{os.getpid()}-{time.time_ns()}"
    old = profile_dir / f".save-previous-{os.getpid()}-{time.time_ns()}"
    try:
        shutil.copytree(snapshot_dir, staged)
        if save_dir.exists():
            save_dir.rename(old)
        staged.rename(save_dir)
        if old.exists():
            shutil.rmtree(old)
    except Exception:
        if not save_dir.exists() and old.exists():
            old.rename(save_dir)
        shutil.rmtree(staged, ignore_errors=True)
        raise
    return safety

def find_running_game_processes():
    """Find running TotK game processes, excluding the similarly named launcher."""
    if os.name == "nt":
        target = str((GAME_DIR / "totk.exe").resolve())
        escaped_target = target.replace("'", "''")
        command = (
            "$target = '" + escaped_target + "'; "
            "$items = @(Get-CimInstance Win32_Process -Filter \"Name='totk.exe'\" | "
            "Where-Object { $_.ExecutablePath -and "
            "[String]::Equals([IO.Path]::GetFullPath($_.ExecutablePath), $target, "
            "[StringComparison]::OrdinalIgnoreCase) } | "
            "Select-Object ProcessId, ExecutablePath); "
            "if ($items.Count -eq 1) { $items[0] | ConvertTo-Json -Compress } "
            "else { $items | ConvertTo-Json -Compress }"
        )
        try:
            result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                    capture_output=True, text=True, timeout=8,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode == 0:
                output = result.stdout.strip()
                if not output:
                    return []
                items = json.loads(output)
                if isinstance(items, dict):
                    items = [items]
                return [{"pid": item.get("ProcessId"), "path": item.get("ExecutablePath")}
                        for item in items if isinstance(item, dict)]
        except Exception:
            pass

        # If CIM is unavailable, the exact image-name filter still cannot match TotKLauncher.exe.
        try:
            result = subprocess.run(["tasklist.exe", "/FI", "IMAGENAME eq totk.exe", "/FO", "CSV", "/NH"],
                                    capture_output=True, text=True, timeout=5,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode == 0 and '"totk.exe"' not in result.stdout.casefold():
                return []
            if result.returncode == 0:
                return [{"pid": None, "path": str(GAME_DIR / "totk.exe")}]
        except Exception:
            pass
        return [{"pid": None, "path": str(GAME_DIR / "totk.exe")}]

    checked = False
    processes = []
    for name in ("totk", "totk.exe"):
        try:
            result = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True, timeout=3)
            checked = True
            if result.returncode == 0:
                for pid in result.stdout.split():
                    try:
                        path = os.readlink(f"/proc/{int(pid)}/exe")
                    except (OSError, ValueError):
                        path = None
                    processes.append({"pid": pid, "path": path})
        except Exception:
            pass
    return processes if checked else [{"pid": None, "path": None}]


def game_process_running():
    """Best-effort check that the installed TotK game is closed."""
    return bool(find_running_game_processes())


def game_process_warning(action):
    """Build an actionable message describing the process blocking a save operation."""
    processes = find_running_game_processes()
    if not processes:
        return None
    details = []
    for process in processes:
        label = []
        if process.get("pid") is not None:
            label.append(f"PID {process['pid']}")
        if process.get("path"):
            label.append(str(process["path"]))
        details.append(" — ".join(label) if label else "TotK game process (path unavailable)")
    return f"A TotK game process is still running:\n" + "\n".join(details) + f"\nClose it before {action}."


class SaveBackupVaultDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Save Backup Vault")
        self.geometry("680x460")
        self.minsize(560, 360)
        self.configure(bg=COLOR_BG_DARK)
        self.transient(parent)
        self.profile_dir = GAME_DIR / "profile"
        self.backups_dir = self.profile_dir / "backups"
        self.snapshots = []

        header = tk.Frame(self, bg=COLOR_CARD, padx=20, pady=14)
        header.pack(fill=tk.X)
        tk.Label(header, text="SAVE BACKUP VAULT", font=("Segoe UI", 13, "bold"),
                 fg=COLOR_GOLD, bg=COLOR_CARD).pack(anchor="w")
        tk.Label(header, text="Snapshots are stored in GAME/profile/backups/.",
                 font=("Segoe UI", 9), fg=COLOR_TEXT_DIM, bg=COLOR_CARD).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg=COLOR_BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=14)
        tk.Label(body, text="Available snapshots", font=("Segoe UI", 10, "bold"),
                 fg=COLOR_WHITE, bg=COLOR_BG_DARK).pack(anchor="w", pady=(0, 8))
        self.snapshot_list = tk.Listbox(body, bg=COLOR_CARD, fg=COLOR_WHITE, selectbackground=COLOR_TAB_ACTIVE,
                                        selectforeground=COLOR_GOLD, font=("Segoe UI", 9),
                                        highlightthickness=1, highlightbackground=COLOR_CARD_BORDER,
                                        activestyle="none")
        self.snapshot_list.pack(fill=tk.BOTH, expand=True)

        footer = tk.Frame(self, bg=COLOR_CARD, padx=14, pady=12)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Button(footer, text="CREATE BACKUP SNAPSHOT", command=self.create_snapshot,
                  font=("Segoe UI", 8, "bold"), fg="#000000", bg=COLOR_GOLD,
                  activebackground=COLOR_GOLD_HOVER, bd=0, padx=12, pady=8).pack(side=tk.LEFT)
        tk.Button(footer, text="RESTORE BACKUP", command=self.restore_snapshot,
                  font=("Segoe UI", 8, "bold"), fg=COLOR_WHITE, bg=COLOR_BUTTON_HOVER,
                  activebackground=COLOR_GOLD, bd=0, padx=12, pady=8).pack(side=tk.LEFT, padx=8)
        tk.Button(footer, text="OPEN BACKUPS FOLDER", command=self.open_backups,
                  font=("Segoe UI", 8, "bold"), fg=COLOR_WHITE, bg=COLOR_BUTTON_HOVER,
                  activebackground=COLOR_GOLD, bd=0, padx=12, pady=8).pack(side=tk.RIGHT)
        self.refresh()

    def refresh(self):
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots = sorted((p for p in self.backups_dir.iterdir() if p.is_dir() and p.name.startswith("save_")),
                                key=lambda p: p.name, reverse=True)
        self.snapshot_list.delete(0, tk.END)
        for snapshot in self.snapshots:
            self.snapshot_list.insert(tk.END, snapshot.name)
        if not self.snapshots:
            self.snapshot_list.insert(tk.END, "No save snapshots yet")

    def create_snapshot(self):
        warning = game_process_warning("creating a save snapshot")
        if warning:
            messagebox.showwarning("Close the Game First", warning, parent=self)
            return
        try:
            snapshot = create_save_snapshot(self.profile_dir, self.backups_dir)
            self.refresh()
            messagebox.showinfo("Backup Created", f"Save snapshot created:\n{snapshot.name}", parent=self)
        except Exception as exc:
            messagebox.showerror("Backup Failed", str(exc), parent=self)

    def restore_snapshot(self):
        selection = self.snapshot_list.curselection()
        if not selection or selection[0] >= len(self.snapshots):
            messagebox.showinfo("Select a Backup", "Select a save snapshot to restore.", parent=self)
            return
        warning = game_process_warning("restoring a save snapshot")
        if warning:
            messagebox.showwarning("Close the Game First", warning, parent=self)
            return
        snapshot = self.snapshots[selection[0]]
        if not messagebox.askyesno("Confirm Save Restore",
                                   f"Restore {snapshot.name}? The current save will first be backed up automatically.",
                                   parent=self):
            return
        try:
            safety = restore_save_snapshot(self.profile_dir, snapshot)
            self.refresh()
            messagebox.showinfo("Backup Restored", f"Restored {snapshot.name}.\nCurrent save snapshot: {safety.name}",
                                parent=self)
        except Exception as exc:
            messagebox.showerror("Restore Failed", str(exc), parent=self)

    def open_backups(self):
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        open_folder(self.backups_dir)


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
        self.update_action_btn = tk.Button(
            footer_card, text="⚡ UPDATE NOW (1-CLICK)", command=self.apply_latest_update,
            font=("Segoe UI", 8, "bold"), fg="#000000", bg=COLOR_GOLD,
            activebackground=COLOR_GOLD_HOVER, bd=0, padx=10, pady=6, cursor="hand2")
        self.update_action_btn.pack_forget()
        self.latest_release = None
        self.update_in_progress = False

        self.canvas.create_window(1050, 565, window=footer_card, anchor="se")

        # GitHub Link Button on Canvas (Bottom-Left)
        gh_btn = tk.Button(self.canvas, text="★ GitHub Repository (STS78721)",
                           font=("Segoe UI", 9, "bold"), fg=COLOR_GOLD, bg=COLOR_CARD,
                           activebackground=COLOR_CARD_BORDER, activeforeground=COLOR_GOLD_HOVER,
                           bd=1, relief="solid", padx=14, pady=6, cursor="hand2",
                           command=lambda: webbrowser.open(GITHUB_URL))
        self.canvas.create_window(70, 570, window=gh_btn, anchor="w")

    def launch_game(self):
        if os.name == "nt":
            exe_path = GAME_DIR / "totk.exe"
            command = [str(exe_path)]
        else:
            native_path = GAME_DIR / "totk"
            exe_path = native_path if native_path.is_file() else GAME_DIR / "totk.exe"
            if exe_path.suffix.lower() == ".exe":
                wine = os.environ.get("TOTK_WINE") or shutil.which("wine") or shutil.which("wine64")
                if not wine and os.environ.get("STEAM_COMPAT_DATA_PATH"):
                    messagebox.showerror("Launch Error", "Steam Proton is active, but this launcher cannot discover "
                                         "the Proton runtime from outside the game's Steam launch context. Launch "
                                         "the game through Steam or set TOTK_WINE to a Wine/Proton executable.")
                    return
                if not wine:
                    messagebox.showerror("Launch Error", "No native totk binary or Wine/Proton executable was found.")
                    return
                command = [wine, str(exe_path)]
            else:
                command = [str(exe_path)]
        if not exe_path.is_file():
            messagebox.showerror("Error", f"Game executable not found at:\n{exe_path}")
            return

        # Pre-flight game data validation: prevent console flash/crash for users missing exefs or romfs
        missing = []
        has_exefs = (GAME_DIR / "exefs").is_dir() and (
            (GAME_DIR / "exefs" / "main.npdm").is_file() or (GAME_DIR / "exefs" / "main").is_file()
        )
        if not has_exefs:
            missing.append("• exefs/ folder (contains main.npdm, main, etc. from your v1.4.3 update dump)")

        has_romfs = (GAME_DIR / "romfs").is_dir() and (
            (GAME_DIR / "romfs" / "romfs.bin").is_file() or (GAME_DIR / "romfs-index.bin").is_file() or
            any((GAME_DIR / "romfs").iterdir())
        )
        if not has_romfs:
            missing.append("• romfs/ folder (contains base game + update game assets or romfs.bin)")

        if missing:
            details = "\n".join(missing)
            msg = (
                "Cannot start Tears of the Kingdom because essential game files are missing:\n\n"
                f"{details}\n\n"
                f"Please copy your dumped game folders directly into:\n{GAME_DIR}\n\n"
                "Would you like to open the game folder now so you can paste them in?"
            )
            if messagebox.askyesno("Missing Game Files", msg, icon="warning", parent=self):
                open_folder(GAME_DIR)
            return

        try:
            subprocess.Popen(command, cwd=str(GAME_DIR))
            self.safe_quit()
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to start totk.exe:\n{e}")

    def check_for_updates(self):
        self.latest_release = None
        self.update_action_btn.pack_forget()
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
            assets = release.get("assets", [])
            tag_clean = tag.replace("-", "").replace(".", "")
            candidates = [
                f"SteelTemple-TotK-{tag}-Update.zip",
                f"SteelTemple-TotK-{tag_clean}-Update.zip",
                f"SteelTemple-TotK-Update-{tag}.zip",
                f"totk-pc-recomp-{tag}-update.zip",
            ]
            asset = next((item for item in assets for cand in candidates if item.get("name", "").casefold() == cand.casefold()), None)
            if not asset:
                asset = next((item for item in assets if "update" in item.get("name", "").lower() and item.get("name", "").lower().endswith(".zip")), None)
            asset_name = asset.get("name") if asset else f"SteelTemple-TotK-{tag}-Update.zip"
            asset_url = asset.get("browser_download_url") if asset else None
            self.after(0, lambda: self._show_release_result(tag, title, page, asset_url, asset_name))
        except Exception as exc:
            detail = str(exc)
            self.after(0, lambda: self.update_status.config(text=f"Update check failed: {detail}", fg="#ff7373"))

    def _show_release_result(self, tag, title, page, asset_url=None, asset_name=None):
        release_version = title.split(":", 1)[0].strip()
        if (tag.casefold() == VERSION_STRING.casefold() or title.casefold() == VERSION_STRING.casefold()
                or release_version.casefold() == VERSION_STRING.casefold()):
            self.update_status.config(text=f"You are on the latest build ({VERSION_STRING})!", fg=COLOR_ACCENT_GREEN)
            self.update_action_btn.pack_forget()
            return
        if not asset_url:
            self.update_status.config(text=f"Update found ({title}), but its update ZIP is missing.", fg="#ff7373")
            self.update_action_btn.pack_forget()
            return
        self.latest_release = {"tag": tag, "title": title, "page": page,
                               "asset_url": asset_url, "asset_name": asset_name}
        self.update_status.config(text="")
        self.update_action_btn.pack(anchor="e", pady=(5, 0))
        self.update_action_btn.config(state=tk.NORMAL)

    def apply_latest_update(self):
        if self.update_in_progress or not self.latest_release:
            return
        warning = game_process_warning("applying a launcher/game update")
        if warning:
            messagebox.showwarning("Close the Game First", warning, parent=self)
            return
        if not messagebox.askyesno("Install Update", f"Download and apply {self.latest_release['title']} now?",
                                   parent=self):
            return
        self.update_in_progress = True
        self.update_action_btn.config(state=tk.DISABLED, text="DOWNLOADING UPDATE…")
        self.update_status.config(text="Connecting to GitHub Releases…", fg=COLOR_TEXT_DIM)
        threading.Thread(target=self._download_update_worker, args=(self.latest_release.copy(),), daemon=True).start()

    def _download_update_worker(self, release):
        stage = None
        try:
            GAME_DIR.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".totk-update-", dir=GAME_DIR))
            archive_path = stage / release["asset_name"]
            request = urllib.request.Request(release["asset_url"], headers={"User-Agent": "TotKLauncher",
                                                                            "Accept": "application/octet-stream"})
            with urllib.request.urlopen(request, timeout=60) as response, archive_path.open("wb") as output:
                total = int(response.headers.get("Content-Length", "0") or 0)
                downloaded = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    downloaded += len(block)
                    if total:
                        percent = min(100, downloaded * 100 // total)
                        self._set_update_status(f"Downloading update… {percent}%", COLOR_TEXT_DIM)
            self._set_update_status("Validating update archive…", COLOR_TEXT_DIM)
            files = extract_update_archive(archive_path, stage)
            archive_path.unlink(missing_ok=True)
            if not {"totk.exe", "TotKLauncher.exe"}.issubset(set(files)):
                raise ValueError("The validated update is missing a required executable.")
            self._set_update_status("Checking updated game files against the installed 1.4.3 content…", COLOR_TEXT_DIM)
            validate_update_game_executable(stage / "totk.exe", GAME_DIR)
            self.after(0, lambda: self._update_ready(release, stage, files))
        except Exception as exc:
            if stage:
                shutil.rmtree(stage, ignore_errors=True)
            detail = str(exc)
            self.after(0, lambda: self._update_failed(detail))

    def _set_update_status(self, text, color):
        try:
            self.after(0, lambda: self.update_status.config(text=text, fg=color))
        except tk.TclError:
            pass

    def _update_failed(self, detail):
        self.update_in_progress = False
        self.update_action_btn.config(state=tk.NORMAL, text="⚡ UPDATE NOW (1-CLICK)")
        self.update_status.config(text=f"Update failed: {detail}", fg="#ff7373")

    def _update_ready(self, release, stage, files):
        if not messagebox.askyesno("Update Ready", f"{release['title']} is downloaded and validated. "
                                   "Install it now? The launcher will close, replace the files, then restart.",
                                   parent=self):
            shutil.rmtree(stage, ignore_errors=True)
            self.update_in_progress = False
            self.update_action_btn.config(state=tk.NORMAL, text="⚡ UPDATE NOW (1-CLICK)")
            self.update_status.config(text="Update downloaded; installation cancelled.", fg=COLOR_TEXT_DIM)
            return
        try:
            self._start_update_relauncher(stage, release["title"])
            os._exit(0)
        except Exception as exc:
            shutil.rmtree(stage, ignore_errors=True)
            self._update_failed(str(exc))

    def _start_update_relauncher(self, stage, title):
        def ps_quote(value):
            return "'" + str(value).replace("'", "''") + "'"
        game_path = ps_quote(GAME_DIR.resolve())
        stage_path = ps_quote(Path(stage).resolve())
        title_text = ps_quote(title)
        script = f"""
$ErrorActionPreference = 'Stop'
$game = {game_path}
$stage = {stage_path}
$rollback = Join-Path $stage '_rollback'
New-Item -ItemType Directory -Force -Path $rollback | Out-Null
$changed = [System.Collections.Generic.List[string]]::new()
try {{
    Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 700
    foreach ($name in @('totk.exe','totk.ini','totk.ini.example','CONTROLLER_GUIDE.txt','TotKLauncher.exe')) {{
        $source = Join-Path $stage $name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {{ continue }}
        $target = Join-Path $game $name
        $backup = Join-Path $rollback $name
        if (Test-Path -LiteralPath $target -PathType Leaf) {{ Copy-Item -LiteralPath $target -Destination $backup -Force }}
        $changed.Add($name)
        $newFile = $target + '.update-new'
        Copy-Item -LiteralPath $source -Destination $newFile -Force
        Move-Item -LiteralPath $newFile -Destination $target -Force
    }}
}} catch {{
    try {{ Add-Type -AssemblyName System.Windows.Forms }} catch {{}}
    for ($i = $changed.Count - 1; $i -ge 0; $i--) {{
        $name = $changed[$i]; $target = Join-Path $game $name; $backup = Join-Path $rollback $name
        if (Test-Path -LiteralPath $backup -PathType Leaf) {{ Copy-Item -LiteralPath $backup -Destination $target -Force }}
        else {{ Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue }}
    }}
    [System.Windows.Forms.MessageBox]::Show(('Update failed and changes were rolled back: ' + $_.Exception.Message), 'Update Failed') | Out-Null
    exit 1
}}
try {{ Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show(({title_text} + ' installed successfully. The launcher will restart.'), 'Update Complete') | Out-Null }} catch {{}}
Start-Process -FilePath (Join-Path $game 'TotKLauncher.exe') -WorkingDirectory $game
Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
"""
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        flags = getattr(subprocess, "DETACHED_PROCESS", 0)
        subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden",
                          "-EncodedCommand", encoded], cwd=str(GAME_DIR), creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def open_settings(self):
        SonySettingsDialog(self)

    def open_extras(self):
        menu = tk.Menu(self, tearoff=0, bg=COLOR_CARD, fg=COLOR_WHITE,
                       activebackground=COLOR_GOLD, activeforeground="#000000",
                       font=("Segoe UI", 10, "bold"), bd=1)

        def open_dir(d, title):
            p = GAME_DIR / d
            p.mkdir(parents=True, exist_ok=True)
            open_folder(p)

        menu.add_command(label="🌐  Visit GitHub Repository", command=lambda: webbrowser.open(GITHUB_URL))
        menu.add_command(label="⬆  Check for Updates", command=self.check_for_updates)
        menu.add_command(label="🧩  Open Mod Manager", command=self.open_mod_manager)
        menu.add_command(label="🛡  Save Backup Vault", command=self.open_save_backup_vault)
        menu.add_separator()
        menu.add_command(label="📁  Open Mods Folder (mods/)", command=lambda: open_dir("mods", "Mods"))
        menu.add_command(label="💾  Open Save Directory (profile/save/)", command=lambda: open_dir("profile/save", "Saves"))
        menu.add_command(label="🔮  Open Amiibo Dumps (amiibo/)", command=lambda: open_dir("amiibo", "Amiibo"))
        menu.add_separator()
        menu.add_command(label="🎮  View In-Game Controller Guide", command=self.open_controller_guide)

        menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())

    def open_mod_manager(self):
        ModsManagerDialog(self)

    def open_save_backup_vault(self):
        SaveBackupVaultDialog(self)

    def open_controller_guide(self):
        guide_p = GAME_DIR / "CONTROLLER_GUIDE.txt"
        if guide_p.is_file():
            if os.name == "nt":
                os.startfile(str(guide_p))
            else:
                open_folder(guide_p.parent)
        else:
            messagebox.showinfo("Guide", "CONTROLLER_GUIDE.txt not found in game directory.")


def patch_installed_ui_mods(game_dir, resolution, romfs_path=None):
    """Scans game_dir/mods for any UI/prompt mods that bundle Common.Product.*.blarc.zs (or .blarc)
    and patches their layout to match the target ultrawide resolution."""
    mods_dir = Path(game_dir) / "mods"
    if not mods_dir.is_dir():
        return 0
    if "x" not in resolution.lower():
        return 0
    try:
        width, height = (int(v) for v in resolution.lower().split("x"))
    except ValueError:
        return 0
    if abs(width / height - 16 / 9) < 0.01:
        return 0
    
    romfs_dir = Path(romfs_path) if romfs_path else Path(game_dir) / "romfs"
    index_path = romfs_dir / "index.json"
    bin_path = romfs_dir / "romfs.bin"
    if not index_path.is_file() or not bin_path.is_file():
        return 0
    
    try:
        import struct
        import importlib.util
        import compression.zstd as zstd
        index_data = json.loads(index_path.read_text(encoding="utf-8"))
        files = {f["path"]: f for f in index_data.get("files", [])}
        if "Pack/ZsDic.pack.zs" not in files:
            return 0
        with bin_path.open("rb") as img:
            f = files["Pack/ZsDic.pack.zs"]
            img.seek(f["offset"])
            pack_raw = img.read(f["size"])
        pack = zstd.decompress(pack_raw)
        
        header, size, start = struct.unpack_from('<HxxII', pack, 4)
        count = struct.unpack_from('<H', pack, header + 6)[0]
        names = header + 12 + count * 16 + 8
        dictionaries = {}
        for i in range(count):
            node = header + 12 + i * 16
            _, attribute, lo, hi = struct.unpack_from('<4I', pack, node)
            offset = names + (attribute & 0xffffff) * 4
            d = zstd.ZstdDict(pack[start + lo:start + hi])
            dictionaries[d.dict_id] = d
    except Exception:
        return 0

    candidates = [
        get_base_dir() / "tools" / "ultrawide_layout.py",
        get_base_dir().parent / "tools" / "ultrawide_layout.py"
    ]
    tool = next((p for p in candidates if p.is_file()), None)
    if not tool:
        return 0
    
    try:
        spec = importlib.util.spec_from_file_location("ultrawide_layout", tool)
        ultrawide = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ultrawide)
    except Exception:
        return 0

    patched_count = 0
    for blarc_path in mods_dir.rglob("Common.Product.*.blarc.zs"):
        if blarc_path.name.endswith(".bak_16_9"):
            continue
        try:
            bak_path = blarc_path.with_name(blarc_path.name + ".bak_16_9")
            if not bak_path.is_file():
                bak_path.write_bytes(blarc_path.read_bytes())
            
            raw_to_patch = bak_path.read_bytes()
            frame = zstd.get_frame_info(raw_to_patch)
            d = dictionaries.get(frame.dictionary_id)
            if not d:
                continue
            blarc_decomp = bytearray(zstd.decompress(raw_to_patch, zstd_dict=d))
            
            b_header, b_size, b_start = struct.unpack_from('<HxxII', blarc_decomp, 4)
            b_count = struct.unpack_from('<H', blarc_decomp, b_header + 6)[0]
            b_names = b_header + 12 + b_count * 16 + 8
            members = {}
            for i in range(b_count):
                node = b_header + 12 + i * 16
                _, attribute, lo, hi = struct.unpack_from('<4I', blarc_decomp, node)
                offset = b_names + (attribute & 0xffffff) * 4
                name = blarc_decomp[offset:blarc_decomp.index(0, offset, b_start)].decode()
                members[name] = (b_start + lo, b_start + hi)
            
            ultrawide.apply(blarc_decomp, members, width, height)
            recompressed = zstd.compress(blarc_decomp, level=19, zstd_dict=d)
            blarc_path.write_bytes(recompressed)
            patched_count += 1
        except Exception:
            continue
    return patched_count


def restore_installed_ui_mods(game_dir):
    """Restores any backed-up 16:9 vanilla UI mod files if reverting to standard 16:9."""
    mods_dir = Path(game_dir) / "mods"
    if not mods_dir.is_dir():
        return 0
    restored = 0
    for bak_path in mods_dir.rglob("*.bak_16_9"):
        orig_path = bak_path.with_name(bak_path.name[:-9])
        try:
            orig_path.write_bytes(bak_path.read_bytes())
            restored += 1
        except Exception:
            pass
    return restored


def main():
    if len(sys.argv) >= 6 and sys.argv[1] == "--run-ultrawide-patcher":
        resolution, version, romfs, out = sys.argv[2:6]
        candidates = [get_base_dir() / "tools" / "make_romfs_patches.py",
                      get_base_dir().parent / "tools" / "make_romfs_patches.py"]
        tool = next((path for path in candidates if path.is_file()), None)
        if tool is None:
            raise FileNotFoundError("Bundled tools/make_romfs_patches.py was not found.")
        sys.argv = [str(tool), "--version", version, "--aspect", resolution, "--romfs", romfs, "--out", out]
        runpy.run_path(str(tool), run_name="__main__")
        try:
            cnt = patch_installed_ui_mods(GAME_DIR, resolution, romfs)
            print(f"PATCHED_MODS={cnt}")
        except Exception as exc:
            print(f"PATCHED_MODS=0 (error: {exc})")
        return

    cfg = load_launcher_config()
    
    shift_pressed = False
    try:
        import ctypes
        shift_pressed = False
        if os.name == "nt":
            try:
                shift_pressed = (ctypes.windll.user32.GetAsyncKeyState(0x10) & 0x8000) != 0
            except Exception:
                pass
    except Exception:
        pass

    if not cfg.get("show_launcher", True) and not shift_pressed and "--launcher" not in sys.argv:
        exe_path = GAME_DIR / "totk.exe"
        has_exefs = (GAME_DIR / "exefs").is_dir() and (
            (GAME_DIR / "exefs" / "main.npdm").is_file() or (GAME_DIR / "exefs" / "main").is_file()
        )
        if exe_path.is_file() and has_exefs:
            if os.name != "nt" and exe_path.suffix.lower() == ".exe":
                wine = os.environ.get("TOTK_WINE") or shutil.which("wine") or shutil.which("wine64")
                if not wine:
                    return
                subprocess.Popen([wine, str(exe_path)], cwd=str(GAME_DIR))
            else:
                subprocess.Popen([str(exe_path)], cwd=str(GAME_DIR))
            os._exit(0)

    app = SonyLauncherApp()
    app.mainloop()

if __name__ == "__main__":
    main()
