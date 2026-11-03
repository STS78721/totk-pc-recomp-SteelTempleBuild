"""Controller UI Manager for TOTK PC Recompiled Installer.

Manages controller prompts selection:
- PlayStation 5 DualSense (Monochrome)
- PlayStation 5 DualSense (Color)
- Xbox Series / One (Monochrome)
- Xbox Series / One (Color)
- Nintendo Switch (Default Original)
"""

import os
import shutil
import zipfile
from typing import List, Dict, Optional

CONTROLLER_UI_CHOICES = [
    {
        "id": "ps5_monochrome",
        "name": "PlayStation 5 DualSense (Monochrome)",
        "desc": "Official PS5 dark theme button icons (✕, ◯, ◻, △)",
        "zip": "UI Overhaul - Default Controls - Monochrome Style 189 2.6 2026-11-03T10-58Z pe088zWnm.zip",
        "folder": "mods/PS5 UI - Default - Monochrome"
    },
    {
        "id": "ps5_color",
        "name": "PlayStation 5 DualSense (Color)",
        "desc": "PlayStation icons with colored shapes (Blue Cross, Red Circle, etc.)",
        "zip": "UI Overhaul - Default Controls - Color Style 189 2.6 2026-11-03T10-57Z AX4HHEdTi.zip",
        "folder": "mods/PS5 UI - Default - Color"
    },
    {
        "id": "xbox_monochrome",
        "name": "Xbox Series / One (Monochrome)",
        "desc": "Xbox modern controller prompts (A, B, X, Y)",
        "zip": "UI Overhaul - Default Controls - Monochrome Style 189 2.6 2026-11-03T10-58Z pe088zWnm.zip",
        "folder": "mods/Xbox UI - Default - Monochrome"
    },
    {
        "id": "xbox_color",
        "name": "Xbox Series / One (Color)",
        "desc": "Xbox prompts with colored buttons (Green A, Red B, Blue X, Yellow Y)",
        "zip": "UI Overhaul - Default Controls - Color Style 189 2.6 2026-11-03T10-57Z AX4HHEdTi.zip",
        "folder": "mods/Xbox UI - Default - Color"
    },
    {
        "id": "nintendo_default",
        "name": "Nintendo Switch (Original)",
        "desc": "Original Switch Pro Controller / Joy-Con prompts",
        "zip": None,
        "folder": None
    }
]

def find_ui_source_zip(zip_name: str) -> Optional[str]:
    """Finds the source zip file for the controller mod."""
    candidates = [
        r"C:\Users\debee\Desktop\Controller UI",
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "Controller UI"),
        r"C:\Games\controller_mods",
        os.path.join(os.path.dirname(__file__), "..", "mods"),
    ]
    for c in candidates:
        full = os.path.join(c, zip_name)
        if os.path.exists(full):
            return full
    return None

def install_controller_ui(choice_id: str, target_game_dir: str) -> bool:
    """Installs the selected controller UI into target_game_dir/mods."""
    mods_dir = os.path.join(target_game_dir, "mods")
    os.makedirs(mods_dir, exist_ok=True)

    # 1. First, remove any existing controller UI mods to prevent conflicts
    for item in os.listdir(mods_dir):
        if any(tag in item.lower() for tag in ["ps5 ui", "xbox ui", "dualsense"]):
            item_path = os.path.join(mods_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)

    # 2. If Nintendo Switch original, nothing more to install
    if choice_id == "nintendo_default":
        return True

    # 3. Find the selected choice
    choice = next((c for c in CONTROLLER_UI_CHOICES if c["id"] == choice_id), None)
    if not choice or not choice["zip"] or not choice["folder"]:
        return False

    zip_path = find_ui_source_zip(choice["zip"])
    if not zip_path:
        # Check if already pre-extracted in another game folder
        fallback_src = os.path.join(r"C:\Games\Tears of the Kingdom PC\GAME\mods", os.path.basename(choice["folder"]))
        if os.path.exists(fallback_src):
            dst = os.path.join(mods_dir, os.path.basename(choice["folder"]))
            shutil.copytree(fallback_src, dst)
            return True
        return False

    # Extract the specific folder from the zip
    prefix = choice["folder"] + "/"
    with zipfile.ZipFile(zip_path, "r") as z:
        for member in z.namelist():
            if member.startswith(prefix):
                z.extract(member, target_game_dir)

    return True
