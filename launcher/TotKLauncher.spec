# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules


a = Analysis(
    ['TotKLauncher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('background.jpg', '.'),
        ('totk.ico', '.'),
        ('sounds', 'sounds'),
        ('../tools/make_romfs_patches.py', 'tools'),
        ('../tools/ultrawide_layout.py', 'tools'),
        ('../tools/button_icons.py', 'tools'),
    ],
    hiddenimports=collect_submodules('fontTools') + [
        'compression.zstd',
        'argparse',
        'hashlib',
        'importlib.util',
        'struct',
        'math',
        'io',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'numpy', 'matplotlib', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TotKLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['totk.ico'],
)
