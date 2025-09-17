# PyInstaller hook for realtime package
from PyInstaller.utils.hooks import collect_all

# Collect all realtime modules and data
datas, binaries, hiddenimports = collect_all('realtime')

# Add specific imports that are causing issues
hiddenimports += [
    'realtime.exceptions',
    'realtime.channel',
    'realtime.connection',
    'realtime.message',
    'realtime.transformers',
]

# Try to add the specific classes that are failing to import
try:
    import realtime
    if hasattr(realtime, 'AuthorizationError'):
        hiddenimports.append('realtime.AuthorizationError')
    if hasattr(realtime, 'NotConnectedError'):
        hiddenimports.append('realtime.NotConnectedError')
except ImportError:
    pass