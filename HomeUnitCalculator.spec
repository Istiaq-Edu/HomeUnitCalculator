# -*- mode: python ; coding: utf-8 -*-

import os

# Read version from APP_VERSION env var (set by GitHub Actions workflow)
# Falls back to a default for local builds
_app_version = os.environ.get("APP_VERSION", "1.0.0")
_parts = _app_version.split(".")
while len(_parts) < 4:
    _parts.append("0")
_version_info = tuple(int(p) if p.isdigit() else 0 for p in _parts[:4])

# Write a version.txt file that gets bundled as data
# The about page reads this at runtime to display the correct version
_version_txt = os.path.join(os.getcwd(), "version.txt")
with open(_version_txt, "w", encoding="utf-8") as _f:
    _f.write(_app_version)

# Build Windows exe version info using PyInstaller's own classes
# (passing the VSVersionInfo object directly avoids file format/eval issues)
_version_obj = None
try:
    from PyInstaller.utils.win32.versioninfo import (
        VSVersionInfo, FixedFileInfo, StringFileInfo,
        StringTable, StringStruct, VarFileInfo, VarStruct,
    )
    _version_obj = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=_version_info,
            prodvers=_version_info,
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([
                StringTable('040904B0', [
                    StringStruct('CompanyName', 'Istiaq-Edu'),
                    StringStruct('FileDescription', 'Home Unit Calculator'),
                    StringStruct('FileVersion', _app_version),
                    StringStruct('ProductName', 'Home Unit Calculator'),
                    StringStruct('ProductVersion', _app_version),
                ])
            ]),
            VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
        ]
    )
except Exception:
    # Non-Windows or PyInstaller without win32 module — skip version info
    pass


a = Analysis(
    ['src\\core\\HomeUnitCalculator.py'],
    pathex=[],
    binaries=[],
    datas=[('icons', 'icons'), ('version.txt', '.')],
    hiddenimports=['src.core.oauth_credentials'],
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
    version=_version_obj,
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
