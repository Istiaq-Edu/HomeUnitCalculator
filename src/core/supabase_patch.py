# Comprehensive patch for Supabase/realtime import issues in PyInstaller
import sys
import types

# Determine whether the realtime package and its transformer are already available.
_have_realtime = False
_have_transformer = False
try:
    import realtime  # type: ignore
    _have_realtime = True
    try:
        from realtime.transformers import convert_change_data  # type: ignore
        _have_transformer = True
    except Exception:
        _have_transformer = False
except Exception:
    _have_realtime = False

# Mock classes for realtime functionality
class Socket:
    """Mock Socket class"""
    def __init__(self, *args, **kwargs):
        pass
    
    def connect(self, *args, **kwargs):
        pass
    
    def disconnect(self, *args, **kwargs):
        pass

class Channel:
    """Mock Channel class"""
    def __init__(self, *args, **kwargs):
        pass
    
    def subscribe(self, *args, **kwargs):
        return self
    
    def unsubscribe(self, *args, **kwargs):
        pass

class Message:
    """Mock Message class"""
    def __init__(self, *args, **kwargs):
        pass

class AuthorizationError(Exception):
    """Mock AuthorizationError for realtime compatibility"""
    pass

class NotConnectedError(Exception):
    """Mock NotConnectedError for realtime compatibility"""
    pass

class AsyncRealtimeChannel:
    """Mock AsyncRealtimeChannel for realtime compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class AsyncRealtimeClient:
    """Mock AsyncRealtimeClient for realtime compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class RealtimeChannelOptions:
    """Mock RealtimeChannelOptions for realtime compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class RealtimeChannel:
    """Mock RealtimeChannel for realtime compatibility"""
    def __init__(self, *args, **kwargs):
        pass

class RealtimeClient:
    """Mock RealtimeClient for realtime compatibility"""
    def __init__(self, *args, **kwargs):
        pass

# If realtime is present and has the required transformer, do nothing.
if _have_realtime and _have_transformer:
    # Keep runtime clean when full realtime support is available.
    # No patching is necessary.
    pass
else:
    # Build minimal/fallback pieces as needed.
    # Create mock submodules (used if the whole package is missing) or targeted transformer shim.
    def _make_transformers_module():
        mod = types.ModuleType('realtime.transformers')
        # Provide a very lenient pass-through implementation. Supabase client often expects
        # this function to normalize change payloads. For our app (which does not rely
        # on realtime streams), a pass-through keeps imports from failing.
        def convert_change_data(*args, **kwargs):  # type: ignore[override]
            # Try common argument names; otherwise return the first positional
            return (
                kwargs.get('record')
                or kwargs.get('data')
                or (args[0] if args else None)
            )
        mod.convert_change_data = convert_change_data  # type: ignore[attr-defined]
        return mod

    if not _have_realtime:
        # Full mock of the realtime package and its common submodules
        connection_mock = types.ModuleType('realtime.connection')
        connection_mock.Socket = Socket

        channel_mock = types.ModuleType('realtime.channel')
        channel_mock.Channel = Channel

        message_mock = types.ModuleType('realtime.message')
        message_mock.Message = Message

        transformers_mock = _make_transformers_module()

        exceptions_mock = types.ModuleType('realtime.exceptions')
        exceptions_mock.AuthorizationError = AuthorizationError
        exceptions_mock.NotConnectedError = NotConnectedError

        # Create the main realtime module
        realtime_mock = types.ModuleType('realtime')
        realtime_mock.AuthorizationError = AuthorizationError
        realtime_mock.NotConnectedError = NotConnectedError
        realtime_mock.AsyncRealtimeChannel = AsyncRealtimeChannel
        realtime_mock.AsyncRealtimeClient = AsyncRealtimeClient
        realtime_mock.RealtimeChannelOptions = RealtimeChannelOptions
        realtime_mock.RealtimeChannel = RealtimeChannel
        realtime_mock.RealtimeClient = RealtimeClient
        realtime_mock.Socket = Socket
        realtime_mock.Channel = Channel
        realtime_mock.Message = Message

        # Register all modules in sys.modules
        sys.modules['realtime'] = realtime_mock
        sys.modules['realtime.connection'] = connection_mock
        sys.modules['realtime.channel'] = channel_mock
        sys.modules['realtime.message'] = message_mock
        sys.modules['realtime.transformers'] = transformers_mock
        sys.modules['realtime.exceptions'] = exceptions_mock

        print("Supabase realtime: full compatibility mock applied (package missing).")
    else:
        # Realtime exists but its transformers module or symbol is missing — inject only the shim.
        sys.modules['realtime.transformers'] = _make_transformers_module()
        print("Supabase realtime: injected transformers shim with convert_change_data().")