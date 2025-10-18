"""
Startup Performance Profiler for Home Unit Calculator
Measures initialization time for each component
"""

import time
import sys
import os
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class StartupProfiler:
    def __init__(self):
        self.timings = {}
        self.start_time = time.time()
        self.last_checkpoint = self.start_time
    
    @contextmanager
    def measure(self, label):
        """Context manager to measure execution time"""
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            self.timings[label] = elapsed
            delta_from_last = time.time() - self.last_checkpoint
            self.last_checkpoint = time.time()
            print(f"[{time.time() - self.start_time:6.2f}s] {label}: {elapsed:.3f}s (Δ{delta_from_last:.3f}s)")
    
    def print_summary(self):
        """Print summary of all timings"""
        total = time.time() - self.start_time
        print("\n" + "="*60)
        print("STARTUP PERFORMANCE SUMMARY")
        print("="*60)
        
        # Sort by time (descending)
        sorted_timings = sorted(self.timings.items(), key=lambda x: x[1], reverse=True)
        
        for label, elapsed in sorted_timings:
            percentage = (elapsed / total) * 100
            bar_length = int(percentage / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            print(f"{label:40s} {elapsed:6.3f}s [{bar:50s}] {percentage:5.1f}%")
        
        print("="*60)
        print(f"{'TOTAL STARTUP TIME':40s} {total:6.3f}s")
        print("="*60)

def profile_startup():
    """Profile the application startup"""
    profiler = StartupProfiler()
    
    print("Starting Home Unit Calculator with profiling...\n")
    
    # Measure imports
    with profiler.measure("Import PyQt5"):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
    
    with profiler.measure("Import QFluentWidgets"):
        from qfluentwidgets import FluentWindow, setTheme, Theme
    
    with profiler.measure("Import reportlab"):
        from reportlab.lib.pagesizes import letter
    
    with profiler.measure("Import PIL"):
        from PIL import Image
    
    with profiler.measure("Import supabase"):
        from supabase import create_client
    
    with profiler.measure("Import application modules"):
        from src.core.HomeUnitCalculator import MeterCalculationApp
    
    # Create QApplication
    with profiler.measure("Create QApplication"):
        app = QApplication(sys.argv)
    
    # Create main window
    with profiler.measure("Create MeterCalculationApp"):
        window = MeterCalculationApp()
    
    # Show window
    with profiler.measure("Show window"):
        window.show()
    
    # Print summary
    profiler.print_summary()
    
    # Run app (comment out for profiling only)
    # sys.exit(app.exec_())

if __name__ == "__main__":
    profile_startup()
