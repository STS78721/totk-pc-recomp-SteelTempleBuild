"""Headless RomFS & UI mod patcher helper invoked by TotKLauncher.exe."""

import compression.zstd as zstd
import importlib.util
import json
from pathlib import Path
import re
import runpy
import shutil
import struct
import sys


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _resolve_tool(name: str) -> Path:
    base = _base_dir()
    for candidate in (base / "tools" / name, base.parent / "tools" / name, base / name):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find patcher tool {name}")


def _load_ultrawide_module():
    path = _resolve_tool("ultrawide_layout.py")
    spec = importlib.util.spec_from_file_location("ultrawide_layout", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _sarc_members(data: bytes) -> dict[str, tuple[int, int]]:
    assert data[:4] == b"SARC" and data[6:8] == b"\xff\xfe"
    header, size, start = struct.unpack_from("<HxxII", data, 4)
    assert size == len(data) and data[header:header + 4] == b"SFAT"
    count = struct.unpack_from("<H", data, header + 6)[0]
    names = header + 12 + count * 16
    assert data[names:names + 4] == b"SFNT"
    names += 8
    out: dict[str, tuple[int, int]] = {}
    for i in range(count):
        node = header + 12 + i * 16
        _, attribute, lo, hi = struct.unpack_from("<4I", data, node)
        offset = names + (attribute & 0xFFFFFF) * 4
        name = data[offset:data.index(0, offset, start)].decode()
        out[name] = (start + lo, start + hi)
    return out


def _find_zstd_dict(romfs_dir: Path) -> bytes | None:
    pack_dir = romfs_dir / "Pack"
    zs_dict = romfs_dir / "Pack/ZsDic.pack.zs"
    if not zs_dict.is_file() and pack_dir.is_dir():
        for p in pack_dir.glob("*ZsDic*.zs"):
            zs_dict = p
            break
    if not zs_dict.is_file():
        return None
    raw = zstd.decompress(zs_dict.read_bytes())
    members = _sarc_members(raw)
    for k, (lo, hi) in members.items():
        if "common" in k.lower() or "pack" in k.lower():
            return bytes(raw[lo:hi])
    return None


def patch_installed_ui_mods(game_dir: Path, resolution: str, romfs_path: Path | None = None) -> int:
    mods_dir = game_dir / "mods"
    if not mods_dir.is_dir():
        return 0
    m = re.match(r"^\s*(\d+)\s*x\s*(\d+)\s*$", resolution)
    if not m:
        return 0
    width, height = int(m.group(1)), int(m.group(2))
    aspect = width / max(1, height)
    if abs(aspect - (16.0 / 9.0)) < 0.03:
        return restore_installed_ui_mods(game_dir)

    uw = _load_ultrawide_module()
    romfs_dir = romfs_path or (game_dir / "romfs")
    zd = _find_zstd_dict(romfs_dir) if romfs_dir.is_dir() else None
    zdict = zstd.ZstdDict(zd) if zd else None

    patched_count = 0
    for blarc_zs in mods_dir.rglob("Common.Product.*.blarc.zs"):
        if ".disabled" in str(blarc_zs).lower():
            continue
        bak = blarc_zs.with_name(blarc_zs.name + ".bak_16_9")
        if not bak.is_file():
            shutil.copy2(blarc_zs, bak)
        src_bytes = bak.read_bytes()
        try:
            frame_dict_id = zstd.get_frame_info(src_bytes).dictionary_id
            decompressed = bytearray(
                zstd.decompress(src_bytes, zstd_dict=zdict if frame_dict_id and zdict else None)
            )
            members = _sarc_members(decompressed)
            uw.apply(decompressed, members, width, height, hud_corner=True)
            recompressed = zstd.compress(
                bytes(decompressed),
                level=15,
                zstd_dict=zdict if frame_dict_id and zdict else None,
            )
            blarc_zs.write_bytes(recompressed)
            patched_count += 1
        except (Exception, SystemExit) as exc:
            print(f"[patch_installed_ui_mods] skipped {blarc_zs.name}: {exc}", file=sys.stderr)
    return patched_count


def restore_installed_ui_mods(game_dir: Path) -> int:
    mods_dir = game_dir / "mods"
    if not mods_dir.is_dir():
        return 0
    restored = 0
    for bak in mods_dir.rglob("*.bak_16_9"):
        orig = bak.with_name(bak.name[: -len(".bak_16_9")])
        shutil.copy2(bak, orig)
        bak.unlink(missing_ok=True)
        restored += 1
    return restored


def _run_make_romfs_patches(argv: list[str]) -> int:
    script = _resolve_tool("make_romfs_patches.py")
    tools_dir = str(script.parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    old_argv = sys.argv
    sys.argv = [str(script)] + argv
    try:
        runpy.run_path(str(script), run_name="__main__")
        return 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        return code
    finally:
        sys.argv = old_argv


def main() -> int:
    if len(sys.argv) >= 6 and sys.argv[1] == "--run-ultrawide-patcher":
        resolution, version, romfs_s, out_s = sys.argv[2:6]
        out_dir = Path(out_s)
        game_dir = out_dir.parent
        cmd = ["--version", version, "--romfs", romfs_s, "--out", out_s, "--aspect", resolution]
        reuse_dir = game_dir / "romfs-patches"
        if reuse_dir.is_dir() and reuse_dir.resolve() != out_dir.resolve():
            cmd += ["--reuse", str(reuse_dir)]
        rc = _run_make_romfs_patches(cmd)
        if rc == 0:
            patch_installed_ui_mods(game_dir, resolution, Path(romfs_s))
        return rc

    if len(sys.argv) >= 6 and sys.argv[1] == "--run-prompts-patcher":
        style, version, romfs_s, out_s = sys.argv[2:6]
        out_dir = Path(out_s)
        game_dir = out_dir.parent
        cmd = ["--version", version, "--romfs", romfs_s, "--out", out_s, "--prompts", style]
        if len(sys.argv) >= 8 and sys.argv[6] == "--aspect":
            cmd += ["--aspect", sys.argv[7]]
        reuse_dir = game_dir / "romfs-patches"
        if reuse_dir.is_dir() and reuse_dir.resolve() != out_dir.resolve():
            cmd += ["--reuse", str(reuse_dir)]
        return _run_make_romfs_patches(cmd)

    if len(sys.argv) >= 3 and sys.argv[1] == "--restore-ui-mods":
        count = restore_installed_ui_mods(Path(sys.argv[2]))
        print(json.dumps({"status": "pass", "restored": count}))
        return 0

    print(
        "Usage:\n"
        "  TotKPatcher --run-ultrawide-patcher <WxH> <ver> <romfs> <out>\n"
        "  TotKPatcher --run-prompts-patcher <style> <ver> <romfs> <out> [--aspect WxH]\n"
        "  TotKPatcher --restore-ui-mods <game_dir>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
