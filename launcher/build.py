"""Builds TOTK's native MKW-style Windows Launcher: launcher/dist/TotKLauncher.exe.

Uses static SDL3, Dear ImGui, and llvm-mingw toolchain, embeds Roboto-Medium.ttf,
hover.wav, click.wav, default_totk.ini, and launcher/totk.ico.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_DIR = ROOT / "launcher"
OUT_BUILD = LAUNCHER_DIR / "build" / "native"
OUT_DIST = LAUNCHER_DIR / "dist"
MKW_WIN = Path(os.environ.get("TOTK_MKW_WIN", r"C:\Games\MKW PC\upstream-mkw-recomp\build\win"))


def find_toolchain() -> tuple[Path, Path]:
    sdl = Path(os.environ.get("TOTK_SDL_STATIC", str(MKW_WIN / "sdl-static")))
    llvm = Path(os.environ.get("TOTK_LLVM_MINGW", str(MKW_WIN / "llvm-mingw")))
    for p, desc in [
        (sdl / "lib/libSDL3.a", "static SDL3"),
        (llvm / "bin/x86_64-w64-mingw32-clang++.exe", "llvm-mingw clang++"),
    ]:
        if not p.is_file():
            sys.exit(f"missing {desc}: {p}")
    return sdl, llvm


def format_byte_array(var_name: str, data: bytes) -> str:
    chunks = [", ".join(f"0x{b:02x}" for b in data[i : i + 20]) for i in range(0, len(data), 20)]
    return (
        f"static const unsigned int {var_name}Len = {len(data)};\n"
        f"static const unsigned char {var_name}[] = {{\n    "
        + (",\n    ".join(chunks) if chunks else "0x00")
        + "\n};\n"
    )


def write_assets_header(dst: Path) -> None:
    font_data = (ROOT / "runtime/ui/fonts/Roboto-Medium.ttf").read_bytes()
    hover_data = (LAUNCHER_DIR / "sounds/hover.wav").read_bytes()
    click_data = (LAUNCHER_DIR / "sounds/click.wav").read_bytes()
    default_ini_data = (LAUNCHER_DIR / "default_totk.ini").read_bytes() + b"\x00"

    marker = (
        f"// len:{len(font_data)}:{len(hover_data)}:{len(click_data)}:{len(default_ini_data)}\n"
    )
    if dst.is_file():
        first_line = dst.read_text(encoding="utf-8", errors="ignore").splitlines()[0:1]
        if first_line and first_line[0] + "\n" == marker:
            return

    body = (
        marker
        + "#pragma once\n\n"
        + format_byte_array("kRobotoMediumTtf", font_data)
        + "\n"
        + format_byte_array("kHoverWav", hover_data)
        + "\n"
        + format_byte_array("kClickWav", click_data)
        + "\n"
        + format_byte_array("kDefaultTotkIni", default_ini_data)
    )
    dst.write_text(body, encoding="utf-8", newline="\n")


def repo_version() -> str:
    ver_file = ROOT / "VERSION"
    if ver_file.is_file():
        v = ver_file.read_text(encoding="utf-8", errors="ignore").strip()
        if v:
            return v
    return "Beta 6.3"


def compile_launcher(sdl: Path, llvm: Path, out_exe: Path, ver_str: str) -> None:
    OUT_BUILD.mkdir(parents=True, exist_ok=True)
    OUT_DIST.mkdir(parents=True, exist_ok=True)

    assets_hdr = OUT_BUILD / "launcher_assets.h"
    write_assets_header(assets_hdr)

    ico_src = LAUNCHER_DIR / "totk.ico"
    if not ico_src.is_file():
        ico_src = ROOT / "runtime/totk.ico"
    shutil.copy2(ico_src, OUT_BUILD / "launcher.ico")

    (OUT_BUILD / "launcher.rc").write_text(
        '1 ICON "launcher.ico"\n1 24 "launcher.manifest"\n', encoding="utf-8"
    )
    (OUT_BUILD / "launcher.manifest").write_text(
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
    subprocess.run(
        [str(windres), str(OUT_BUILD / "launcher.rc"), "-O", "coff", "-o", str(OUT_BUILD / "launcher_res.o")],
        check=True,
        cwd=OUT_BUILD,
    )

    imgui_dir = ROOT / "runtime/third_party/imgui"
    backends_dir = ROOT / "tools/installer/backends"
    srcs = [
        LAUNCHER_DIR / "totk_launcher.cpp",
        imgui_dir / "imgui.cpp",
        imgui_dir / "imgui_draw.cpp",
        imgui_dir / "imgui_tables.cpp",
        imgui_dir / "imgui_widgets.cpp",
        backends_dir / "imgui_impl_sdl3.cpp",
        backends_dir / "imgui_impl_sdlrenderer3.cpp",
    ]
    objs = []
    common_flags = [
        "-std=c++20",
        "-O2",
        "-DNDEBUG",
        f"-I{OUT_BUILD}",
        f"-I{sdl / 'include'}",
        f"-I{imgui_dir}",
        f"-I{backends_dir}",
        "-DIMGUI_DISABLE_OBSOLETE_FUNCTIONS",
        "-DUNICODE",
        "-D_UNICODE",
        f'-DTOTK_LAUNCHER_VERSION="{ver_str}"',
    ]
    for src in srcs:
        obj = OUT_BUILD / (src.stem + ".obj")
        subprocess.run([str(clangxx), *common_flags, "-c", str(src), "-o", str(obj)], check=True)
        objs.append(str(obj))

    link_libs = [
        f"-L{sdl / 'lib'}",
        "-lSDL3",
        "-luser32",
        "-lgdi32",
        "-limm32",
        "-lole32",
        "-loleaut32",
        "-lshell32",
        "-lsetupapi",
        "-lversion",
        "-luuid",
        "-ladvapi32",
        "-lwinmm",
        "-lwinhttp",
        "-ldwmapi",
        "-static",
        "-static-libstdc++",
        "-static-libgcc",
        "-mwindows",
    ]
    subprocess.run(
        [str(clangxx), *objs, str(OUT_BUILD / "launcher_res.o"), "-o", str(out_exe), *link_libs],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_DIST / "TotKLauncher.exe")
    args = ap.parse_args()
    sdl, llvm = find_toolchain()
    ver = repo_version()
    compile_launcher(sdl, llvm, args.out, ver)
    mb = args.out.stat().st_size / (1024 * 1024)
    print(f"built {args.out} ({mb:.2f} MiB)")


if __name__ == "__main__":
    main()
