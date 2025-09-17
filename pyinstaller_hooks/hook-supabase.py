# PyInstaller hook for supabase package
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all supabase modules and data
datas, binaries, hiddenimports = collect_all('supabase')

# Add all supabase submodules
hiddenimports += collect_submodules('supabase')

# Add specific modules that might be missed
hiddenimports += [
    'supabase.client',
    'supabase.lib',
    'gotrue',
    'gotrue.errors',
    'postgrest',
    'postgrest.exceptions',
    'storage3',
    'realtime',
]