"""Builds TOTK's native MKW-style Windows Setup Wizard: build/installer/TotK-Setup-Wizard.exe.

Uses the static SDL3, libzstd, and llvm-mingw toolchain, embeds Roboto-Medium.ttf and runtime/totk.ico,
and optionally packs a clean distribution directory as a compressed TOTKPKG1 trailer.

Usage:
    python tools/installer/build.py [--payload DIR] [--out PATH] [--level 15]
"""

import argparse
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

try:
    from compression import zstd
except ImportError:
    zstd = None

ROOT = Path(__file__).resolve().parents[2]
MKW_WIN = Path(r"C:\Games\MKW PC\upstream-mkw-recomp\build\win")
OUT = ROOT / "build" / "installer"
MAGIC = b"TOTKPKG1"

SKIP_PAYLOAD_NAMES = {
    "totk.ini",
    "totk.exe.bak",
    "pipeline-cache.bin",
    "pipeline-keys.bin",
    "shader-answers.bin",
    "shader-prepared.bin",
    "shader-programs.bin",
    "seed-answers.bin",
    "seed-programs.bin",
    "unins000.exe",
}
SKIP_PAYLOAD_DIRS = {"logs", "profile", "build-cache", "shader-cache", "__pycache__"}


def find_toolchain() -> tuple[Path, Path, Path]:
    sdl = Path(os.environ.get("TOTK_SDL_STATIC", str(MKW_WIN / "sdl-static")))
    deps = Path(os.environ.get("TOTK_DEPS", str(MKW_WIN / "deps")))
    llvm = Path(os.environ.get("TOTK_LLVM_MINGW", str(MKW_WIN / "llvm-mingw")))
    for p, desc in [(sdl / "lib/libSDL3.a", "static SDL3"), (deps / "lib/libzstd.a", "static libzstd"),
                    (llvm / "bin/x86_64-w64-mingw32-clang++.exe", "llvm-mingw clang++")]:
        if not p.is_file():
            sys.exit(f"missing {desc}: {p}")
    return sdl, deps, llvm


def write_font_header(ttf_path: Path, dst: Path) -> None:
    data = ttf_path.read_bytes()
    if dst.is_file() and f"kRobotoMediumTtfLen = {len(data)};" in dst.read_text(encoding="utf-8", errors="ignore"):
        return
    chunks = [", ".join(f"0x{b:02x}" for b in data[i : i + 20]) for i in range(0, len(data), 20)]
    body = (
        "#pragma once\n"
        f"static const unsigned int kRobotoMediumTtfLen = {len(data)};\n"
        "static const unsigned char kRobotoMediumTtf[] = {\n    "
        + ",\n    ".join(chunks)
        + "\n};\n"
    )
    dst.write_text(body, encoding="utf-8", newline="\n")


def repo_version() -> str:
    ver_file = ROOT / "VERSION"
    if ver_file.is_file():
        v = ver_file.read_text(encoding="utf-8", errors="ignore").strip()
        if v:
            return v
    return "Beta 6.3"


def compile_wizard(sdl: Path, deps: Path, llvm: Path, out_exe: Path, ver_str: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    font_hdr = OUT / "roboto_font.h"
    write_font_header(ROOT / "runtime/ui/fonts/Roboto-Medium.ttf", font_hdr)

    shutil.copy2(ROOT / "runtime/totk.ico", OUT / "setup.ico")
    (OUT / "setup.rc").write_text('1 ICON "setup.ico"\n1 24 "setup.manifest"\n', encoding="utf-8")
    (OUT / "setup.manifest").write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n'
        '  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>'
        '<requestedExecutionLevel level="asInvoker" uiAccess="false"/></requestedPrivileges></security></trustInfo>\n'
        '  <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>'
        '<dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">PerMonitorV2</dpiAwareness>'
        '<activeCodePage xmlns="http://schemas.microsoft.com/SMI/2019/WindowsSettings">UTF-8</activeCodePage>'
        '</windowsSettings></application>\n'
        '  <dependency><dependentAssembly><assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" '
        'version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>'
        '</dependentAssembly></dependency>\n</assembly>\n',
        encoding="utf-8",
    )

    windres = llvm / "bin/x86_64-w64-mingw32-windres.exe"
    clangxx = llvm / "bin/x86_64-w64-mingw32-clang++.exe"
    res = OUT / "setup.res.o"
    subprocess.run([str(windres), "-O", "coff", "-I", str(OUT), str(OUT / "setup.rc"), "-o", str(res)], check=True)

    imgui = ROOT / "runtime/third_party/imgui"
    backends = ROOT / "tools/installer/backends"
    srcs = [
        ROOT / "tools/installer/installer.cpp",
        imgui / "imgui.cpp",
        imgui / "imgui_draw.cpp",
        imgui / "imgui_tables.cpp",
        imgui / "imgui_widgets.cpp",
        backends / "imgui_impl_sdl3.cpp",
        backends / "imgui_impl_sdlrenderer3.cpp",
    ]

    out_exe.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(clangxx),
        "-std=c++20",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Wno-missing-field-initializers",
        "-mwindows",
        "-static",
        "-DUNICODE",
        f'-DTOTK_SETUP_VERSION="{ver_str}"',
        f"-I{sdl / 'include'}",
        f"-I{imgui}",
        f"-I{ROOT / 'tools/installer'}",
        f"-I{deps / 'include'}",
        f"-I{OUT}",
        *[str(s) for s in srcs],
        str(res),
        "-o",
        str(out_exe),
        f"-L{sdl / 'lib'}",
        "-lSDL3",
        str(deps / "lib/libzstd.a"),
        "-lsetupapi",
        "-lwinmm",
        "-limm32",
        "-lversion",
        "-lole32",
        "-loleaut32",
        "-luuid",
        "-lgdi32",
        "-luser32",
        "-lshell32",
        "-ladvapi32",
        "-lcfgmgr32",
    ]
    subprocess.run(cmd, check=True)
    print(f"built {out_exe} ({out_exe.stat().st_size / 1048576:.2f} MiB)")


def append_payload(exe_path: Path, payload_dir: Path, level: int) -> None:
    if zstd is None:
        sys.exit("Python 3.14+ compression.zstd required for --payload packing")
    files = []
    for p in sorted(payload_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(payload_dir)
        if any(part.lower() in SKIP_PAYLOAD_DIRS for part in rel.parts):
            continue
        if p.name.lower() in SKIP_PAYLOAD_NAMES:
            continue
        files.append((rel.as_posix(), p))

    stub = exe_path.read_bytes()
    payload_offset = len(stub)
    toc = bytearray(struct.pack("<I", len(files)))
    # Placeholder offsets patched once TOC size is known
    toc_len = 4 + sum(2 + len(rel.encode("utf-8")) + 24 for rel, _ in files)
    cur_offset = payload_offset + toc_len
    comp_blobs = []
    raw_total = 0
    comp_total = 0
    for rel, fp in files:
        raw = fp.read_bytes()
        comp = zstd.compress(raw, level=level)
        rel_b = rel.encode("utf-8")
        toc += struct.pack("<H", len(rel_b)) + rel_b + struct.pack("<QQQ", cur_offset, len(comp), len(raw))
        cur_offset += len(comp)
        comp_blobs.append(comp)
        raw_total += len(raw)
        comp_total += len(comp)

    with exe_path.open("wb") as f:
        f.write(stub)
        f.write(toc)
        for blob in comp_blobs:
            f.write(blob)
        f.write(struct.pack("<Q8s", payload_offset, MAGIC))
    print(f"packed {len(files)} files: {raw_total / 1048576:.1f} MiB -> {comp_total / 1048576:.1f} MiB "
          f"(exe {exe_path.stat().st_size / 1048576:.1f} MiB)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--payload", type=Path, help="Optional clean game folder to pack as TOTKPKG1 trailer")
    ap.add_argument("--out", type=Path, default=OUT / "TotK-Setup-Wizard.exe")
    ap.add_argument("--version", default=repo_version(), help="Version label shown in installer header")
    ap.add_argument("--level", type=int, default=15)
    args = ap.parse_args()

    sdl, deps, llvm = find_toolchain()
    ver = args.version or repo_version()
    compile_wizard(sdl, deps, llvm, args.out.resolve(), ver)
    if args.payload:
        append_payload(args.out.resolve(), args.payload.resolve(), args.level)


if __name__ == "__main__":
    main()
