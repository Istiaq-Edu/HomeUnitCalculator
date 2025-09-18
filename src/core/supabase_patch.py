# Comprehensive patch for Supabase/realtime import issues in PyInstaller
import sys
import types

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

# Create mock submodules
connection_mock = types.ModuleType('realtime.connection')
connection_mock.Socket = Socket

channel_mock = types.ModuleType('realtime.channel')
channel_mock.Channel = Channel

message_mock = types.ModuleType('realtime.message')
message_mock.Message = Message

transformers_mock = types.ModuleType('realtime.transformers')

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

print("Comprehensive Supabase/realtime compatibility patch applied with full module structure")