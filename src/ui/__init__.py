"""
UI module for the Home Unit Calculator.

This module provides all UI components including responsive infrastructure,
custom widgets, dialogs, and layout management.
"""

from .responsive_components import (
    ResponsiveConfig,
    ComponentRegistry,
    ResponsiveDialog,
    LayoutValidator,
    responsive_registry
)

from .responsive_testing import (
    ResponsiveTestSuite,
    PerformanceMonitor
)

from .responsive_image import (
    ResponsiveImageLabel,
    ResponsiveImagePreviewGrid
)

from .flow_layout import FlowLayout
from .custom_widgets import (
    CustomLineEdit,
    LeftIconButton,
    AutoScrollArea,
    CustomNavButton,
    FluentProgressDialog
)

__all__ = [
    # Responsive infrastructure
    'ResponsiveConfig',
    'ComponentRegistry', 
    'ResponsiveDialog',
    'LayoutValidator',
    'responsive_registry',
    
    # Testing utilities
    'ResponsiveTestSuite',
    'PerformanceMonitor',
    
    # Responsive image components
    'ResponsiveImageLabel',
    'ResponsiveImagePreviewGrid',
    
    # Layout components
    'FlowLayout',
    
    # Custom widgets
    'CustomLineEdit',
    'LeftIconButton', 
    'AutoScrollArea',
    'CustomNavButton',
    'FluentProgressDialog'
]