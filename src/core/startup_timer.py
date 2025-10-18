"""
Simple startup timer to measure application initialization time
"""
import time
import sys

class StartupTimer:
    """Measures and logs startup time"""
    
    _start_time = None
    _checkpoints = []
    
    @classmethod
    def start(cls):
        """Start the timer"""
        cls._start_time = time.time()
        cls._checkpoints = []
        cls.checkpoint("Application started")
    
    @classmethod
    def checkpoint(cls, label):
        """Record a checkpoint"""
        if cls._start_time is None:
            cls.start()
        
        elapsed = time.time() - cls._start_time
        cls._checkpoints.append((label, elapsed))
    
    @classmethod
    def finish(cls):
        """Finish timing and print results"""
        if cls._start_time is None:
            return
        
        total_time = time.time() - cls._start_time
        cls.checkpoint("Application ready")
        
        print("\n" + "="*60)
        print("STARTUP PERFORMANCE")
        print("="*60)
        
        for label, elapsed in cls._checkpoints:
            print(f"[{elapsed:6.3f}s] {label}")
        
        print("="*60)
        print(f"TOTAL: {total_time:.3f}s")
        print("="*60 + "\n")
        
        return total_time

# Auto-start when module is imported
StartupTimer.start()
