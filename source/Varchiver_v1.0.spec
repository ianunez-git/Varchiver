# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['Varchiver_v1.0.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('varchiver_logo.png', '.'),
        ('varchiver.ico', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Varchiver',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=['varchiver.ico'],
)
