# PyInstaller hook for realtime package
from PyInstaller.utils.hooks import collect_all

# Collect all realtime modules and data
datas, binaries, hiddenimports = collect_all('realtime')

# Ensure key submodules are included explicitly (module names only)
hiddenimports += [
    'realtime.exceptions',
    'realtime.channel',
    'realtime.connection',
    'realtime.message',
    'realtime.transformers',
]