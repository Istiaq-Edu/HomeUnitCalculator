# PyInstaller hook for the supabase package
#
# Goal: keep the bundle lean by only collecting Python submodules that the
# supabase client needs for CRUD/Storage operations. Avoid pulling package
# data and binaries that significantly increase the EXE size.
#
# Notes:
# - We intentionally do NOT pull in the "realtime" package here. The app does
#   not use realtime streaming; a compatibility shim exists in the codebase to
#   prevent import-time failures if something probes for realtime symbols.
# - If you encounter a ModuleNotFoundError at runtime for a specific submodule,
#   add just that submodule to the list below rather than using collect_all.

from PyInstaller.utils.hooks import collect_submodules

# Only collect Python submodules (no package data/binaries)
hiddenimports = collect_submodules("supabase") + [
    # Core dependencies commonly used by supabase client:
    "supabase_auth",
    "supabase_auth.errors",
    "postgrest",
    "postgrest.exceptions",
    "storage3",
]

# Keep these empty to avoid bundling extra assets/binaries
datas = []
binaries = []
