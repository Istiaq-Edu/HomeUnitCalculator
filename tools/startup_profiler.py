"""
Startup Performance Profiler for Home Unit Calculator
Measures initialization time for each component
"""

import time
import sys
import os
import argparse
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


def _parse_args():
    parser = argparse.ArgumentParser(description="Profile startup time for HomeUnitCalculator")
    parser.add_argument(
        "--event-loop-ms",
        type=int,
        default=800,
        help="Run Qt event loop for N ms to include first paint/layout cost (default: 800). Use 0 to skip.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Do not show the window (still constructs it).",
    )
    return parser.parse_args()


def profile_startup():
    """Profile the application startup"""
    args = _parse_args()
    profiler = StartupProfiler()
    
    print("Starting Home Unit Calculator with profiling...\n")
    
    # Measure imports
    with profiler.measure("Import PyQt5"):
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QTimer
    
    with profiler.measure("Import QFluentWidgets"):
        from qfluentwidgets import FluentWindow, setTheme, Theme

    with profiler.measure("Import application (core.HomeUnitCalculator)"):
        from src.core.HomeUnitCalculator import MeterCalculationApp
    
    # Create QApplication
    with profiler.measure("Create QApplication"):
        app = QApplication(sys.argv)
    
    # Create main window
    with profiler.measure("Create MeterCalculationApp"):
        window = MeterCalculationApp()
    
    # Show window
    if not args.no_show:
        with profiler.measure("Show window"):
            window.show()
    else:
        window.hide()

    if args.event_loop_ms > 0:
        with profiler.measure(f"Run event loop ({args.event_loop_ms}ms)"):
            QTimer.singleShot(args.event_loop_ms, app.quit)
            app.exec_()
    
    # Print summary
    profiler.print_summary()
    
    # Run app (comment out for profiling only)
    # sys.exit(app.exec_())

if __name__ == "__main__":
    profile_startup()
