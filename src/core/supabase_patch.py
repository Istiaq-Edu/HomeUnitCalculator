# Patch for Supabase/realtime import issues in PyInstaller
import sys

# Create mock classes for missing realtime imports
class AuthorizationError(Exception):
    """Mock AuthorizationError for realtime compatibility"""
    pass

class NotConnectedError(Exception):
    """Mock NotConnectedError for realtime compatibility"""
    pass

# Patch the realtime module if it exists but is missing these classes
try:
    import realtime
    if not hasattr(realtime, 'AuthorizationError'):
        realtime.AuthorizationError = AuthorizationError
    if not hasattr(realtime, 'NotConnectedError'):
        realtime.NotConnectedError = NotConnectedError
except ImportError:
    # Create a mock realtime module if it doesn't exist
    import types
    realtime_mock = types.ModuleType('realtime')
    realtime_mock.AuthorizationError = AuthorizationError
    realtime_mock.NotConnectedError = NotConnectedError
    sys.modules['realtime'] = realtime_mock

print("Supabase/realtime compatibility patch applied")