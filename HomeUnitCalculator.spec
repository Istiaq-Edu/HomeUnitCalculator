# -*- mode: python ; coding: utf-8 -*-

# HomeUnitCalculator.spec
# Curated PyInstaller spec to minimize one-file EXE size by:
# - Excluding unused Qt modules (WebEngine, WebChannel, NetworkAuth).
# - Including only essential Qt plugins (platforms/qwindows, imageformats/qpng/qjpeg).
# - Dropping Qt translations.
# - Using project hooks in pyinstaller_hooks/ for lean supabase handling.

import sys
from pathlib import Path

# Ensure relative paths resolve from this spec's directory
spec_root = Path(__file__).resolve().parent
sys.path.insert(0, str(spec_root))

block_cipher = None

# Optional: add project root to Python path for Analysis
pathex = [str(spec_root)]

# Main analysis
a = Analysis(
    ['src/core/HomeUnitCalculator.py'],
    pathex=pathex,
    binaries=[],
    datas=[('icons', 'icons')],  # include the icons directory
    hiddenimports=[
        # Runtime shim to avoid bundling realtime while keeping imports safe
        'src.core.supabase_patch',
    ],
    hookspath=['pyinstaller_hooks'],
    excludes=[
        # Trim unused Qt components
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebChannel',
        'PyQt5.QtNetworkAuth',

        # Not used by this app
        'tkinter',
    ],
    # Optimize .pyc (0, 1, or 2). 1 is generally safe and can shave a bit.
    optimize=1,
    noarchive=False,
)

# Remove Qt translations entirely to save size
try:
    from PyInstaller.utils.hooks.qt import remove_qt_translations
    remove_qt_translations(a)
except Exception:
    # If PyInstaller's qt helper API changes, keep going without translation stripping
    pass

# Curate Qt plugin binaries:
# - Only the Windows platform plugin and PNG/JPEG imageformat plugins are included.
# - Add additional plugins here if runtime indicates they are needed.
try:
    from PyInstaller.utils.hooks.qt import qt_plugins_binaries
    qt_bins = []
    # Core platform (Windows)
    qt_bins += qt_plugins_binaries('PyQt5', 'platforms', ['qwindows'])
    # Image formats: PNG and JPEG are commonly needed
    qt_bins += qt_plugins_binaries('PyQt5', 'imageformats', ['qpng', 'qjpeg'])
    # Optional Windows Vista style plugin (uncomment if you need it)
    # qt_bins += qt_plugins_binaries('PyQt5', 'styles', ['qwindowsvistastyle'])

    a.binaries += qt_bins
except Exception:
    # If the helper fails, fall back to whatever the standard hooks collect.
    # This may increase size but keeps the build functional.
    pass

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-file build: pass binaries/zipfiles/datas directly to EXE (no COLLECT)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HomeUnitCalculator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,   # keep symbols on Windows; strip is more effective on Linux
    upx=False,     # user requested no compression
    console=False, # GUI app
    icon=str(spec_root / 'icons' / 'icon.png'),  # resolved via spec_root; robust when overriding dist/work paths
)

# Usage:
#   pyinstaller HomeUnitCalculator.spec
#   # or override dist/work paths explicitly (useful in CI):
#   pyinstaller --distpath HomeUnitCalculator/dist --workpath HomeUnitCalculator/build HomeUnitCalculator/HomeUnitCalculator.spec
# The output EXE will be created at dist/HomeUnitCalculator.exe (or at the overridden --distpath)
