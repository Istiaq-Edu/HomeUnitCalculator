# -*- mode: python ; coding: utf-8 -*-

import os

# Read version from APP_VERSION env var (set by GitHub Actions workflow)
# Falls back to a default for local builds
_app_version = os.environ.get("APP_VERSION", "1.0.0")

# Write version to a text file that gets bundled into the exe
# The about page reads this at runtime to display the correct version
_version_txt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "version.txt")
with open(_version_txt, "w", encoding="utf-8") as _f:
    _f.write(_app_version)


a = Analysis(
    ['src\\core\\HomeUnitCalculator.py'],
    pathex=[],
    binaries=[],
    datas=[('icons', 'icons'), ('version.txt', '.')],
    hiddenimports=[],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'IPython',
        'matplotlib',
        'numpy',
        'pytest',
        'scipy',
        '_pytest',
        'tkinter',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HomeUnitCalculator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode — crash.log captures errors via excepthook
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icons\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HomeUnitCalculator',
)
