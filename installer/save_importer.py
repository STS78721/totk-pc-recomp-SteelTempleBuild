"""Save Importer for TOTK PC Recompiled.

Discovers existing save files from standard Switch emulators (Eden, Yuzu, Ryujinx, Sudachi, Suyu, Torzu)
or custom user directories/archives, and automatically injects them into the PC Recompiled save structure.
"""

import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

TOTK_TITLE_ID = "0100f2c0115b6000"
RECOMP_SAVE_SUBPATH = os.path.join("profile", "user", "save", "0000000000000000", "0100F2C0115B6000")

def get_emulator_search_paths() -> List[Dict[str, str]]:
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    userprofile = os.environ.get("USERPROFILE", "")

    candidates = [
        {"name": "Eden", "path": os.path.join(appdata, "eden", "nand", "user", "save")},
        {"name": "Yuzu", "path": os.path.join(appdata, "yuzu", "nand", "user", "save")},
        {"name": "Ryujinx", "path": os.path.join(appdata, "Ryujinx", "bis", "user", "save")},
        {"name": "Sudachi", "path": os.path.join(appdata, "sudachi", "nand", "user", "save")},
        {"name": "Suyu", "path": os.path.join(appdata, "suyu", "nand", "user", "save")},
        {"name": "Torzu", "path": os.path.join(appdata, "torzu", "nand", "user", "save")},
        {"name": "Previous TOTK Recomp", "path": r"C:\Games\Tears of the Kingdom PC\GAME\profile\user\save"},
        {"name": "Desktop TOTK Recomp", "path": os.path.join(userprofile, "Desktop", "Emulators", "TOTK RECOMPILED", "profile", "user", "save")},
    ]
    return [c for c in candidates if os.path.exists(c["path"])]

def scan_for_saves() -> List[Dict]:
    """Scans for valid TOTK save directories across known emulator paths."""
    found_saves = []
    search_paths = get_emulator_search_paths()

    for item in search_paths:
        base_dir = item["path"]
        source_name = item["name"]

        for root, dirs, files in os.walk(base_dir):
            # Check if this directory or any parent is TOTK
            # In TOTK saves, directories often have slot_00, slot_01 or numerical folders with caption.sav / progress.sav
            has_sav = any(f.endswith(".sav") for f in files)
            if has_sav and ("caption.sav" in files or "progress.sav" in files):
                parent_folder = os.path.dirname(root)
                # Check if this is a slot directory or the main save container
                # Determine newest modified timestamp
                latest_mtime = max(os.path.getmtime(os.path.join(root, f)) for f in files if f.endswith(".sav"))
                dt_str = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M:%S")

                # Count slots in parent_folder
                slots = []
                if os.path.exists(parent_folder):
                    for d in os.listdir(parent_folder):
                        dp = os.path.join(parent_folder, d)
                        if os.path.isdir(dp) and any(os.path.exists(os.path.join(dp, f)) for f in ["caption.sav", "progress.sav"]):
                            slots.append(d)

                save_root = parent_folder if len(slots) > 1 else root
                slot_count = len(slots) if len(slots) > 1 else 1

                # Avoid duplicates
                if not any(s["path"] == save_root for s in found_saves):
                    found_saves.append({
                        "source": source_name,
                        "path": save_root,
                        "last_modified": dt_str,
                        "mtime": latest_mtime,
                        "slot_count": slot_count
                    })

    # Sort newest first
    found_saves.sort(key=lambda x: x["mtime"], reverse=True)
    return found_saves

def inject_save(source_path: str, target_game_dir: str) -> bool:
    """Copies all save files/slots from source_path to the target Recomp save folder."""
    if not os.path.exists(source_path):
        return False

    dest_dir = os.path.join(target_game_dir, RECOMP_SAVE_SUBPATH)
    os.makedirs(dest_dir, exist_ok=True)

    # If source is a zip file
    if source_path.lower().endswith(".zip"):
        with zipfile.ZipFile(source_path, "r") as z:
            z.extractall(dest_dir)
        return True

    # If source is a folder
    if os.path.isdir(source_path):
        # Check if source directly contains slot folders (0, 1, 2... or slot_00) or .sav files
        entries = os.listdir(source_path)
        has_direct_sav = any(e.endswith(".sav") for e in entries)

        if has_direct_sav:
            # Single slot or root save
            slot_dir = os.path.join(dest_dir, "0")
            os.makedirs(slot_dir, exist_ok=True)
            for f in entries:
                src_f = os.path.join(source_path, f)
                if os.path.isfile(src_f):
                    shutil.copy2(src_f, os.path.join(slot_dir, f))
        else:
            # Copy all child folders / slots
            for item in entries:
                src_item = os.path.join(source_path, item)
                dst_item = os.path.join(dest_dir, item)
                if os.path.isdir(src_item):
                    if os.path.exists(dst_item):
                        shutil.rmtree(dst_item)
                    shutil.copytree(src_item, dst_item)
                elif os.path.isfile(src_item):
                    shutil.copy2(src_item, dst_item)
        return True

    return False
