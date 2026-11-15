# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['totk_patcher.py'],
    pathex=['.', '../tools'],
    binaries=[],
    datas=[
        ('../tools/make_romfs_patches.py', 'tools'),
        ('../tools/ultrawide_layout.py', 'tools'),
        ('../tools/button_icons.py', 'tools'),
    ],
    hiddenimports=['fontTools', 'fontTools.ttLib', 'compression.zstd', 'ultrawide_layout', 'button_icons'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PIL', 'numpy', 'matplotlib'],
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
    name='TotKPatcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['totk.ico'],
)
