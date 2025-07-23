"""
Testing utilities for responsive UI components.

This module provides automated testing capabilities for responsive behavior,
including window resize tests, layout validation, and performance monitoring.
"""

from typing import List, Tuple, Dict, Any
from PyQt5.QtCore import QSize, QTimer, QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QApplication
from .responsive_components import LayoutValidator


class ResponsiveTestSuite(QObject):
    """Test suite for automated responsive behavior validation."""
    
    test_completed = pyqtSignal(str, bool, str)  # test_name, success, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
    def test_window_resize_scenarios(self, widget: QWidget, test_sizes: List[Tuple[int, int]] = None):
        """Test various window resize scenarios."""
        if test_sizes is None:
            test_sizes = [
                (800, 600),   # Minimum reasonable size
                (1024, 768),  # Standard size
                (1366, 768),  # Common laptop size
                (1920, 1080), # Full HD
                (2560, 1440), # 2K
            ]
        
        results = []
        for width, height in test_sizes:
            try:
                # Resize the widget
                widget.resize(width, height)
                QApplication.processEvents()  # Allow layout to update
                
                # Validate the layout
                issues = self.verify_no_clipped_components(widget)
                spacing_issues = self.verify_proper_spacing(widget)
                
                all_issues = issues + spacing_issues
                success = len(all_issues) == 0
                
                result = {
                    'size': (width, height),
                    'success': success,
                    'issues': all_issues
                }
                results.append(result)
                
                self.test_completed.emit(
                    f"Resize {width}x{height}", 
                    success, 
                    f"Issues: {len(all_issues)}" if all_issues else "OK"
                )
                
            except Exception as e:
                results.append({
                    'size': (width, height),
                    'success': False,
                    'issues': [f"Exception during resize: {str(e)}"]
                })
                self.test_completed.emit(f"Resize {width}x{height}", False, str(e))
        
        self.test_results['resize_scenarios'] = results
        return results
    
    def verify_no_clipped_components(self, widget: QWidget) -> List[str]:
        """Ensure no components are clipped or overlapping."""
        issues = []
        
        # Get widget geometry
        widget_rect = widget.rect()
        
        # Check all child widgets
        for child in widget.findChildren(QWidget):
            if not child.isVisible():
                continue
                
            child_rect = child.geometry()
            
            # Check if child extends beyond parent bounds
            if not widget_rect.contains(child_rect):
                issues.append(f"Widget {child.objectName() or type(child).__name__} extends beyond parent bounds")
            
            # Check minimum size constraints
            min_size = child.minimumSize()
            if child_rect.width() < min_size.width():
                issues.append(f"Widget {child.objectName() or type(child).__name__} width ({child_rect.width()}) < minimum ({min_size.width()})")
            if child_rect.height() < min_size.height():
                issues.append(f"Widget {child.objectName() or type(child).__name__} height ({child_rect.height()}) < minimum ({min_size.height()})")
        
        return issues
    
    def verify_proper_spacing(self, widget: QWidget) -> List[str]:
        """Ensure spacing remains proportional."""
        issues = []
        
        # Check layout spacing
        if widget.layout():
            layout = widget.layout()
            spacing = layout.spacing()
            
            # Warn if spacing is too small for the widget size
            widget_area = widget.width() * widget.height()
            if widget_area > 500000 and spacing < 10:  # Large widget with small spacing
                issues.append(f"Layout spacing ({spacing}) may be too small for widget size")
            
            # Check margins
            margins = layout.contentsMargins()
            if all(m == 0 for m in [margins.left(), margins.top(), margins.right(), margins.bottom()]):
                if widget_area > 100000:  # Large widget with no margins
                    issues.append("Large widget has no layout margins - content may touch edges")
        
        return issues
    
    def test_high_dpi_compatibility(self, widget: QWidget, scale_factors: List[float] = None):
        """Test widget behavior at different DPI scales."""
        if scale_factors is None:
            scale_factors = [1.0, 1.25, 1.5, 2.0]
        
        results = []
        original_size = widget.size()
        
        for scale in scale_factors:
            try:
                # Simulate DPI scaling by adjusting widget size
                scaled_width = int(original_size.width() * scale)
                scaled_height = int(original_size.height() * scale)
                
                widget.resize(scaled_width, scaled_height)
                QApplication.processEvents()
                
                # Validate layout at this scale
                issues = LayoutValidator.validate_widget_tree(widget)
                success = len(issues) == 0
                
                result = {
                    'scale': scale,
                    'success': success,
                    'issues': issues
                }
                results.append(result)
                
                self.test_completed.emit(
                    f"DPI Scale {scale}x", 
                    success, 
                    f"Issues: {len(issues)}" if issues else "OK"
                )
                
            except Exception as e:
                results.append({
                    'scale': scale,
                    'success': False,
                    'issues': [f"Exception at scale {scale}: {str(e)}"]
                })
                self.test_completed.emit(f"DPI Scale {scale}x", False, str(e))
        
        # Restore original size
        widget.resize(original_size)
        QApplication.processEvents()
        
        self.test_results['high_dpi'] = results
        return results
    
    def test_font_size_variations(self, widget: QWidget, font_scales: List[float] = None):
        """Test widget behavior with different font sizes."""
        if font_scales is None:
            font_scales = [0.8, 1.0, 1.2, 1.5, 2.0]
        
        results = []
        original_font = widget.font()
        original_size = original_font.pointSize()
        
        for scale in font_scales:
            try:
                # Apply font scaling
                new_font = widget.font()
                new_font.setPointSize(int(original_size * scale))
                widget.setFont(new_font)
                
                # Apply to all children
                for child in widget.findChildren(QWidget):
                    child_font = child.font()
                    child_font.setPointSize(int(child_font.pointSize() * scale))
                    child.setFont(child_font)
                
                QApplication.processEvents()
                
                # Validate layout with new font sizes
                issues = self.verify_no_clipped_components(widget)
                success = len(issues) == 0
                
                result = {
                    'font_scale': scale,
                    'success': success,
                    'issues': issues
                }
                results.append(result)
                
                self.test_completed.emit(
                    f"Font Scale {scale}x", 
                    success, 
                    f"Issues: {len(issues)}" if issues else "OK"
                )
                
            except Exception as e:
                results.append({
                    'font_scale': scale,
                    'success': False,
                    'issues': [f"Exception at font scale {scale}: {str(e)}"]
                })
                self.test_completed.emit(f"Font Scale {scale}x", False, str(e))
        
        # Restore original font
        widget.setFont(original_font)
        for child in widget.findChildren(QWidget):
            child.setFont(original_font)
        QApplication.processEvents()
        
        self.test_results['font_variations'] = results
        return results
    
    def run_comprehensive_test(self, widget: QWidget) -> Dict[str, Any]:
        """Run all responsive tests on a widget."""
        print(f"Starting comprehensive responsive test for {type(widget).__name__}")
        
        # Run all test categories
        resize_results = self.test_window_resize_scenarios(widget)
        dpi_results = self.test_high_dpi_compatibility(widget)
        font_results = self.test_font_size_variations(widget)
        
        # Run enhanced validation tests
        layout_issues = LayoutValidator.validate_widget_tree(widget)
        fixed_size_issues = LayoutValidator.detect_fixed_size_constraints(widget)
        pattern_issues = LayoutValidator.validate_responsive_patterns(widget)
        
        # Compile summary
        total_tests = len(resize_results) + len(dpi_results) + len(font_results)
        passed_tests = sum(1 for r in resize_results if r['success']) + \
                      sum(1 for r in dpi_results if r['success']) + \
                      sum(1 for r in font_results if r['success'])
        
        all_validation_issues = layout_issues + fixed_size_issues + pattern_issues
        
        summary = {
            'widget_type': type(widget).__name__,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'success_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'layout_issues': layout_issues,
            'fixed_size_issues': fixed_size_issues,
            'pattern_issues': pattern_issues,
            'total_validation_issues': len(all_validation_issues),
            'resize_results': resize_results,
            'dpi_results': dpi_results,
            'font_results': font_results
        }
        
        self.test_results['comprehensive'] = summary
        
        print(f"Responsive test completed: {passed_tests}/{total_tests} tests passed")
        if all_validation_issues:
            print(f"Validation issues found: {len(all_validation_issues)}")
            for issue in all_validation_issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
            if len(all_validation_issues) > 5:
                print(f"  ... and {len(all_validation_issues) - 5} more issues")
        
        return summary
    
    def create_test_report(self, widget: QWidget, output_file: str = None) -> str:
        """Create a detailed test report for a widget."""
        results = self.run_comprehensive_test(widget)
        
        report_lines = [
            f"# Responsive UI Test Report",
            f"**Widget:** {results['widget_type']}",
            f"**Date:** {QApplication.instance().property('test_date') or 'Unknown'}",
            f"",
            f"## Summary",
            f"- **Total Tests:** {results['total_tests']}",
            f"- **Passed Tests:** {results['passed_tests']}",
            f"- **Success Rate:** {results['success_rate']:.1%}",
            f"- **Validation Issues:** {results['total_validation_issues']}",
            f"",
            f"## Test Results",
            f""
        ]
        
        # Add resize test results
        if results['resize_results']:
            report_lines.extend([
                f"### Window Resize Tests",
                f"| Size | Status | Issues |",
                f"|------|--------|--------|"
            ])
            for result in results['resize_results']:
                size_str = f"{result['size'][0]}x{result['size'][1]}"
                status = "✅ Pass" if result['success'] else "❌ Fail"
                issues = len(result['issues'])
                report_lines.append(f"| {size_str} | {status} | {issues} |")
            report_lines.append("")
        
        # Add validation issues
        if results['total_validation_issues'] > 0:
            report_lines.extend([
                f"### Validation Issues",
                f""
            ])
            
            if results['layout_issues']:
                report_lines.extend([
                    f"**Layout Issues:**",
                    *[f"- {issue}" for issue in results['layout_issues']],
                    f""
                ])
            
            if results['fixed_size_issues']:
                report_lines.extend([
                    f"**Fixed Size Issues:**",
                    *[f"- {issue}" for issue in results['fixed_size_issues']],
                    f""
                ])
            
            if results['pattern_issues']:
                report_lines.extend([
                    f"**Pattern Issues:**",
                    *[f"- {issue}" for issue in results['pattern_issues']],
                    f""
                ])
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                print(f"Test report saved to: {output_file}")
            except Exception as e:
                print(f"Failed to save report to {output_file}: {e}")
        
        return report_text


class PerformanceMonitor:
    """Monitor performance during responsive operations."""
    
    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
        self._baseline_memory = None
    
    def measure_resize_performance(self, widget: QWidget, sizes: List[Tuple[int, int]]) -> Dict[str, float]:
        """Measure time taken for resize operations."""
        import time
        
        times = []
        memory_usage = []
        
        # Record baseline memory
        baseline_memory = self.get_memory_usage()
        
        for width, height in sizes:
            start_time = time.perf_counter()
            start_memory = self.get_memory_usage()
            
            widget.resize(width, height)
            QApplication.processEvents()
            
            end_time = time.perf_counter()
            end_memory = self.get_memory_usage()
            
            times.append(end_time - start_time)
            if isinstance(start_memory, dict) and isinstance(end_memory, dict):
                memory_delta = end_memory.get('rss_mb', 0) - start_memory.get('rss_mb', 0)
                memory_usage.append(memory_delta)
        
        avg_time = sum(times) / len(times) if times else 0
        max_time = max(times) if times else 0
        min_time = min(times) if times else 0
        avg_memory_delta = sum(memory_usage) / len(memory_usage) if memory_usage else 0
        
        results = {
            'average_resize_time': avg_time,
            'max_resize_time': max_time,
            'min_resize_time': min_time,
            'total_operations': len(sizes),
            'average_memory_delta_mb': avg_memory_delta,
            'baseline_memory': baseline_memory
        }
        
        self.measurements['resize_performance'] = times
        self.measurements['memory_usage'] = memory_usage
        return results
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get current memory usage statistics."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss // 1024 // 1024,  # Resident Set Size in MB
                'vms_mb': memory_info.vms // 1024 // 1024,  # Virtual Memory Size in MB
            }
        except ImportError:
            return {'error': 'psutil not available for memory monitoring'}
    
    def profile_layout_calculations(self, widget: QWidget, iterations: int = 100) -> Dict[str, float]:
        """Profile layout calculation performance."""
        import time
        
        if not widget.layout():
            return {'error': 'Widget has no layout to profile'}
        
        layout = widget.layout()
        times = []
        
        # Force initial layout
        widget.updateGeometry()
        QApplication.processEvents()
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            
            # Trigger layout recalculation
            layout.invalidate()
            layout.activate()
            QApplication.processEvents()
            
            end_time = time.perf_counter()
            times.append(end_time - start_time)
        
        return {
            'average_layout_time': sum(times) / len(times),
            'max_layout_time': max(times),
            'min_layout_time': min(times),
            'total_iterations': iterations
        }
    
    def detect_memory_leaks(self, widget: QWidget, operations: int = 50) -> Dict[str, Any]:
        """Detect potential memory leaks during repeated operations."""
        import time
        
        initial_memory = self.get_memory_usage()
        memory_samples = [initial_memory.get('rss_mb', 0)]
        
        # Perform repeated resize operations
        sizes = [(800, 600), (1024, 768), (1200, 900)]
        
        for i in range(operations):
            size = sizes[i % len(sizes)]
            widget.resize(*size)
            QApplication.processEvents()
            
            # Sample memory every 10 operations
            if i % 10 == 0:
                current_memory = self.get_memory_usage()
                memory_samples.append(current_memory.get('rss_mb', 0))
        
        final_memory = self.get_memory_usage()
        
        # Analyze memory trend
        if len(memory_samples) > 2:
            memory_growth = memory_samples[-1] - memory_samples[0]
            avg_growth_per_sample = memory_growth / (len(memory_samples) - 1)
        else:
            memory_growth = 0
            avg_growth_per_sample = 0
        
        return {
            'initial_memory_mb': initial_memory.get('rss_mb', 0),
            'final_memory_mb': final_memory.get('rss_mb', 0),
            'total_memory_growth_mb': memory_growth,
            'average_growth_per_operation_mb': avg_growth_per_sample,
            'memory_samples': memory_samples,
            'potential_leak': memory_growth > 10  # Flag if growth > 10MB
        }