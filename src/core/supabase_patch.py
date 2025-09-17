# Comprehensive patch for Supabase/realtime import issues in PyInstaller
import sys
import types

# Create mock classes for all missing realtime imports
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

# Create a comprehensive mock realtime module
realtime_mock = types.ModuleType('realtime')
realtime_mock.AuthorizationError = AuthorizationError
realtime_mock.NotConnectedError = NotConnectedError
realtime_mock.AsyncRealtimeChannel = AsyncRealtimeChannel
realtime_mock.AsyncRealtimeClient = AsyncRealtimeClient
realtime_mock.RealtimeChannelOptions = RealtimeChannelOptions
realtime_mock.RealtimeChannel = RealtimeChannel
realtime_mock.RealtimeClient = RealtimeClient

# Always replace the realtime module to ensure consistency
sys.modules['realtime'] = realtime_mock

print("Comprehensive Supabase/realtime compatibility patch applied")