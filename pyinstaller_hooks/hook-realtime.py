# PyInstaller hook for the "realtime" package
#
# Purpose:
#   This hook is intentionally a no-op to prevent PyInstaller from auto-including
#   the "realtime" package and its submodules into the bundle. The application
#   does not use realtime streaming features and provides its own compatibility
#   shim to satisfy any optional imports at runtime.
#
# Impact:
#   - Keeps the bundled executable smaller by avoiding unnecessary modules/data.
#   - Safe for this project because a runtime shim ensures imports won't break.
#
# If you later decide to use realtime features, remove this hook or replace it
# with a hook that collects only the submodules you actually need.

# Explicitly avoid adding anything
hiddenimports = []
datas = []
binaries = []

# Proactively exclude these modules in case other hooks try to pull them in
excludedimports = [
    "realtime",
    "realtime.connection",
    "realtime.channel",
    "realtime.message",
    "realtime.transformers",
]
