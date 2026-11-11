"""Controller UI Manager for TOTK PC Recompiled Installer.

Configures native recomp controller button prompt overlays (PlayStation 5 DualSense,
PlayStation 4 DualShock 4, Xbox Series / One, PC Keyboard & Mouse, or Nintendo Switch)
with accurate action-diamond layouts and 60+ FPS quick-menu compatibility.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict

CONTROLLER_UI_CHOICES: List[Dict[str, str]] = [
    {
        "id": "dualsense",
        "name": "PlayStation 5 DualSense (Native Recomp)",
        "desc": "Native PS5 Cross/Circle/Square/Triangle + Create/Options prompts with non-inverted action diamond",
        "prompts": "dualsense",
    },
    {
        "id": "dualshock4",
        "name": "PlayStation 4 DualShock 4 (Native Recomp)",
        "desc": "Native PS4 Cross/Circle/Square/Triangle + Share/Options prompts with non-inverted action diamond",
        "prompts": "dualshock4",
    },
    {
        "id": "xbox",
        "name": "Xbox Series / One (Native Recomp)",
        "desc": "Native Xbox A/B/X/Y + View/Menu prompts with Xbox action diamond",
        "prompts": "xbox",
    },
    {
        "id": "pc",
        "name": "PC Keyboard & Mouse (Native Recomp)",
        "desc": "Native keyboard & mouse keycap prompts following your bindings",
        "prompts": "pc",
    },
    {
        "id": "nintendo_default",
        "name": "Nintendo Switch (Original)",
        "desc": "Original Switch Pro Controller / Joy-Con prompts",
        "prompts": "nintendo",
    },
]


def _set_ini_key(lines: list[str], key: str, val: str) -> None:
    pat_active = re.compile(rf"^\s*{re.escape(key)}\s*=.*$", re.IGNORECASE)
    pat_commented = re.compile(rf"^\s*[#;]\s*{re.escape(key)}\s*=.*$", re.IGNORECASE)
    for idx, line in enumerate(lines):
        if pat_active.match(line):
            lines[idx] = f"{key} = {val}"
            return
    for idx, line in enumerate(lines):
        if pat_commented.match(line):
            lines[idx] = f"{key} = {val}"
            return
    lines.append(f"{key} = {val}")


def install_controller_ui(choice_id: str, target_game_dir: str) -> bool:
    """Configure native controller prompts in totk.ini and build the RomFS overlay if needed."""
    game_dir = Path(target_game_dir)
    mods_dir = game_dir / "mods"
    if mods_dir.is_dir():
        for item in mods_dir.iterdir():
            if item.is_dir() and any(tag in item.name.lower() for tag in ("ps5 ui", "xbox ui")):
                shutil.rmtree(item, ignore_errors=True)

    choice = next((c for c in CONTROLLER_UI_CHOICES if c["id"] == choice_id), CONTROLLER_UI_CHOICES[-1])
    prompts_val = choice["prompts"]

    ini_path = game_dir / "totk.ini"
    lines = ini_path.read_text(encoding="utf-8", errors="ignore").splitlines() if ini_path.is_file() else []
    _set_ini_key(lines, "pad_layout", "auto")
    _set_ini_key(lines, "prompts", prompts_val)
    ini_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if prompts_val == "nintendo":
        return True

    style = "pc" if prompts_val == "pc" else f"{prompts_val}-label"
    out_dir = game_dir / f"romfs-patches-{style}"
    if (out_dir / "manifest.tsv").is_file():
        return True

    romfs = game_dir / "romfs"
    launcher = game_dir / "TotKLauncher.exe"
    if (romfs / "romfs.bin").is_file() and (romfs / "index.json").is_file() and launcher.is_file():
        try:
            idx = json.loads((romfs / "index.json").read_text(encoding="utf-8"))
            paths = {e.get("path", "") for e in idx.get("files", [])}
            version = "v143" if "UI/LayoutArchive/Common.Product.140.Nin_NX_NVN.blarc.zs" in paths else "v121"
            res = subprocess.run(
                [str(launcher), "--run-prompts-patcher", style, version, str(romfs), str(out_dir)],
                cwd=str(game_dir),
                capture_output=True,
                text=True,
                timeout=900,
            )
            return res.returncode == 0 and (out_dir / "manifest.tsv").is_file()
        except Exception:
            return False
    return True
