"""Vendor SDK Manager for TOTK PC Recompiled.

Handles deployment and optional downloading of vendor-specific AI and upscaler libraries:
- NVIDIA: DLSS (Super Resolution), DLSS-NR (Neural Reconstruction), DLSS-FG (Frame Generation)
- Intel: XeSS (Super Sampling & Frame Generation)
- AMD: FSR 3 / FidelityFX SDK
"""

import os
import shutil
import urllib.request
import urllib.error
from typing import Callable, Optional, Dict, List

VENDOR_SDK_FILES = [
    # NVIDIA AI / DLSS stack
    {"name": "nvngx_dlss.dll", "desc": "NVIDIA DLSS 4.5 / Super Resolution", "vendor": "NVIDIA"},
    {"name": "nvngx_dlssnr.dll", "desc": "NVIDIA DLSS-NR Neural Reconstruction", "vendor": "NVIDIA"},
    {"name": "UltraCamVk.nvngx.dll", "desc": "NVIDIA NGX DLSS-NR Vulkan Bridge", "vendor": "NVIDIA"},
    {"name": "nvngx_dlssg.dll", "desc": "NVIDIA DLSS Frame Generation", "vendor": "NVIDIA"},
    {"name": "sl.common.dll", "desc": "NVIDIA Streamline Common", "vendor": "NVIDIA"},
    {"name": "sl.dlss.dll", "desc": "NVIDIA Streamline DLSS plugin", "vendor": "NVIDIA"},
    {"name": "sl.dlss_g.dll", "desc": "NVIDIA Streamline DLSS-G plugin", "vendor": "NVIDIA"},
    {"name": "sl.dlss_nr.dll", "desc": "NVIDIA Streamline DLSS-NR plugin", "vendor": "NVIDIA"},
    {"name": "sl.interposer.dll", "desc": "NVIDIA Streamline Interposer", "vendor": "NVIDIA"},
    {"name": "sl.reflex.dll", "desc": "NVIDIA Reflex Low Latency", "vendor": "NVIDIA"},
    
    # Intel XeSS stack
    {"name": "libxess.dll", "desc": "Intel XeSS Super Sampling SDK", "vendor": "Intel"},
    {"name": "libxess_fg.dll", "desc": "Intel XeSS Frame Generation", "vendor": "Intel"},
    {"name": "libxell.dll", "desc": "Intel Low Latency", "vendor": "Intel"},
    {"name": "libxess_dx11.dll", "desc": "Intel XeSS DX11 Bridge", "vendor": "Intel"},
]

# Official fallback mirrors / download endpoints
VENDOR_DOWNLOAD_MIRRORS = {
    "libxess.dll": "https://raw.githubusercontent.com/intel/xess/main/bin/libxess.dll",
    # Add other direct vendor release URLs or mirrors
}

def find_local_sdk_cache(dll_name: str) -> Optional[str]:
    """Searches common local paths for pre-existing vendor DLLs."""
    search_dirs = [
        r"C:\Games\Tears of the Kingdom PC\GAME",
        r"C:\Games\releases-steeltemple\staging-beta4\bin",
        os.path.join(os.path.dirname(__file__), "..", "bin"),
        os.path.join(os.path.dirname(__file__), "..", "sdk"),
    ]
    for s_dir in search_dirs:
        candidate = os.path.join(s_dir, dll_name)
        if os.path.exists(candidate) and os.path.getsize(candidate) > 1024:
            return candidate
    return None

def install_vendor_sdks(target_game_dir: str, download_if_missing: bool = True,
                        progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, bool]:
    """Installs vendor SDKs into target_game_dir.
    
    Returns a dictionary of {dll_name: success_bool}.
    """
    os.makedirs(target_game_dir, exist_ok=True)
    results = {}
    total = len(VENDOR_SDK_FILES)

    for i, sdk in enumerate(VENDOR_SDK_FILES):
        dll_name = sdk["name"]
        dest_path = os.path.join(target_game_dir, dll_name)
        progress = (i / total)

        if progress_callback:
            progress_callback(f"Configuring {sdk['desc']}...", progress)

        # 1. Check if already at destination
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
            results[dll_name] = True
            continue

        # 2. Check local caches
        local_src = find_local_sdk_cache(dll_name)
        if local_src:
            try:
                shutil.copy2(local_src, dest_path)
                results[dll_name] = True
                continue
            except Exception as e:
                print(f"Error copying local SDK {dll_name}: {e}")

        # 3. Optional auto-download from vendor mirror
        if download_if_missing and dll_name in VENDOR_DOWNLOAD_MIRRORS:
            if progress_callback:
                progress_callback(f"Downloading {sdk['desc']}...", progress)
            try:
                url = VENDOR_DOWNLOAD_MIRRORS[dll_name]
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 TOTK-Setup'})
                with urllib.request.urlopen(req, timeout=15) as resp, open(dest_path, 'wb') as out_f:
                    shutil.copyfileobj(resp, out_f)
                results[dll_name] = True
                continue
            except Exception as e:
                print(f"Download failed for {dll_name}: {e}")

        results[dll_name] = os.path.exists(dest_path)

    if progress_callback:
        progress_callback("Vendor SDKs configured.", 1.0)

    return results
