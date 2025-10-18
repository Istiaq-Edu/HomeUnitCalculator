"""
Performance Comparison Tool
Compares startup performance before and after optimizations
"""

import json
import os
import sys
import time
from datetime import datetime

RESULTS_FILE = "performance_results.json"

def load_results():
    """Load previous performance results"""
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    return {"measurements": []}

def save_results(results):
    """Save performance results"""
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)

def measure_startup():
    """Measure application startup time"""
    print("Measuring startup performance...")
    print("=" * 60)
    
    measurements = {}
    start_total = time.time()
    
    # Measure imports
    print("Measuring imports...")
    
    start = time.time()
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    measurements['pyqt5_import'] = time.time() - start
    print(f"  PyQt5: {measurements['pyqt5_import']:.3f}s")
    
    start = time.time()
    from qfluentwidgets import FluentWindow, setTheme, Theme
    measurements['qfluentwidgets_import'] = time.time() - start
    print(f"  QFluentWidgets: {measurements['qfluentwidgets_import']:.3f}s")
    
    start = time.time()
    try:
        from reportlab.lib.pagesizes import letter
        measurements['reportlab_import'] = time.time() - start
        print(f"  reportlab: {measurements['reportlab_import']:.3f}s")
    except ImportError:
        measurements['reportlab_import'] = 0
        print(f"  reportlab: (deferred)")
    
    start = time.time()
    try:
        from PIL import Image
        measurements['pil_import'] = time.time() - start
        print(f"  PIL: {measurements['pil_import']:.3f}s")
    except ImportError:
        measurements['pil_import'] = 0
        print(f"  PIL: (deferred)")
    
    start = time.time()
    try:
        from supabase import create_client
        measurements['supabase_import'] = time.time() - start
        print(f"  supabase: {measurements['supabase_import']:.3f}s")
    except ImportError:
        measurements['supabase_import'] = 0
        print(f"  supabase: (not available)")
    
    # Measure application creation
    print("\nMeasuring application creation...")
    
    start = time.time()
    from src.core.HomeUnitCalculator import MeterCalculationApp
    measurements['app_import'] = time.time() - start
    print(f"  Import app: {measurements['app_import']:.3f}s")
    
    start = time.time()
    app = QApplication(sys.argv)
    measurements['qapp_creation'] = time.time() - start
    print(f"  Create QApplication: {measurements['qapp_creation']:.3f}s")
    
    start = time.time()
    window = MeterCalculationApp()
    measurements['window_creation'] = time.time() - start
    print(f"  Create window: {measurements['window_creation']:.3f}s")
    
    start = time.time()
    window.show()
    measurements['window_show'] = time.time() - start
    print(f"  Show window: {measurements['window_show']:.3f}s")
    
    measurements['total'] = time.time() - start_total
    
    print("\n" + "=" * 60)
    print(f"TOTAL STARTUP TIME: {measurements['total']:.3f}s")
    print("=" * 60)
    
    return measurements

def compare_results(current, previous):
    """Compare current results with previous measurements"""
    if not previous:
        print("\nNo previous measurements to compare.")
        return
    
    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    
    metrics = [
        ('pyqt5_import', 'PyQt5 Import'),
        ('qfluentwidgets_import', 'QFluentWidgets Import'),
        ('reportlab_import', 'reportlab Import'),
        ('pil_import', 'PIL Import'),
        ('supabase_import', 'supabase Import'),
        ('app_import', 'App Import'),
        ('qapp_creation', 'QApplication Creation'),
        ('window_creation', 'Window Creation'),
        ('window_show', 'Window Show'),
        ('total', 'TOTAL'),
    ]
    
    print(f"{'Metric':<30} {'Previous':<12} {'Current':<12} {'Change':<12} {'%':<8}")
    print("-" * 80)
    
    for key, label in metrics:
        prev_val = previous.get(key, 0)
        curr_val = current.get(key, 0)
        
        if prev_val > 0:
            change = curr_val - prev_val
            percent = (change / prev_val) * 100
            
            # Color coding
            if change < -0.1:  # Improvement
                symbol = "✓"
                color = "green"
            elif change > 0.1:  # Regression
                symbol = "✗"
                color = "red"
            else:  # No significant change
                symbol = "="
                color = "yellow"
            
            print(f"{label:<30} {prev_val:>10.3f}s {curr_val:>10.3f}s {change:>+10.3f}s {percent:>+6.1f}% {symbol}")
        else:
            print(f"{label:<30} {'N/A':<12} {curr_val:>10.3f}s {'N/A':<12} {'N/A':<8}")
    
    print("-" * 80)
    
    # Summary
    prev_total = previous.get('total', 0)
    curr_total = current.get('total', 0)
    if prev_total > 0:
        improvement = prev_total - curr_total
        improvement_pct = (improvement / prev_total) * 100
        
        print(f"\nOVERALL IMPROVEMENT: {improvement:+.3f}s ({improvement_pct:+.1f}%)")
        
        if improvement > 0:
            print(f"✓ Application is {improvement:.3f}s FASTER")
        elif improvement < 0:
            print(f"✗ Application is {abs(improvement):.3f}s SLOWER")
        else:
            print(f"= No significant change")

def main():
    """Main entry point"""
    print("Home Unit Calculator - Performance Measurement Tool")
    print("=" * 60)
    
    # Load previous results
    results_data = load_results()
    previous_measurement = results_data['measurements'][-1] if results_data['measurements'] else None
    
    if previous_measurement:
        print(f"\nPrevious measurement: {previous_measurement.get('timestamp', 'Unknown')}")
        print(f"Previous total time: {previous_measurement.get('total', 0):.3f}s")
    else:
        print("\nNo previous measurements found. This will be the baseline.")
    
    print("\nStarting measurement in 3 seconds...")
    time.sleep(3)
    
    # Measure current performance
    current_measurement = measure_startup()
    current_measurement['timestamp'] = datetime.now().isoformat()
    
    # Compare with previous
    if previous_measurement:
        compare_results(current_measurement, previous_measurement)
    
    # Save results
    results_data['measurements'].append(current_measurement)
    save_results(results_data)
    
    print(f"\nResults saved to {RESULTS_FILE}")
    print("\nTo see all measurements, check the JSON file.")
    print("To run another measurement, execute this script again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMeasurement cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError during measurement: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
