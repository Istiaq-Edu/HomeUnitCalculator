"""
Responsive UI components and infrastructure for the Home Unit Calculator.

This module provides the core infrastructure for making UI components responsive,
including base classes, configuration systems, and validation utilities.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QWidget, QSizePolicy, QLayout


@dataclass
class ResponsiveConfig:
    """Configuration for responsive behavior of UI components."""
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    size_policy_h: QSizePolicy.Policy = QSizePolicy.Expanding
    size_policy_v: QSizePolicy.Policy = QSizePolicy.Preferred
    stretch_factor: int = 1


class ComponentRegistry:
    """Registry for tracking and managing responsive component configurations."""
    
    def __init__(self):
        self.components: Dict[str, ResponsiveConfig] = {}
    
    def register_component(self, name: str, config: ResponsiveConfig):
        """Register a component with its responsive configuration."""
        self.components[name] = config
    
    def apply_config(self, widget: QWidget, name: str):
        """Apply registered configuration to a widget."""
        if name in self.components:
            config = self.components[name]
            widget.setSizePolicy(config.size_policy_h, config.size_policy_v)
            
            if config.min_width is not None:
                widget.setMinimumWidth(config.min_width)
            if config.max_width is not None:
                widget.setMaximumWidth(config.max_width)
            if config.min_height is not None:
                widget.setMinimumHeight(config.min_height)
            if config.max_height is not None:
                widget.setMaximumHeight(config.max_height)
    
    def get_config(self, name: str) -> Optional[ResponsiveConfig]:
        """Get configuration for a registered component."""
        return self.components.get(name)
    
    def apply_config_to_multiple(self, widgets: List[QWidget], config_name: str):
        """Apply the same configuration to multiple widgets."""
        for widget in widgets:
            self.apply_config(widget, config_name)
    
    def create_configured_widget(self, widget_class, config_name: str, *args, **kwargs):
        """Create a widget with a specific configuration applied."""
        widget = widget_class(*args, **kwargs)
        self.apply_config(widget, config_name)
        return widget
    
    def list_configurations(self) -> List[str]:
        """List all registered configuration names."""
        return list(self.components.keys())
    
    def update_config(self, name: str, **kwargs):
        """Update an existing configuration with new values."""
        if name in self.components:
            config = self.components[name]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def clone_config(self, source_name: str, target_name: str, **overrides):
        """Clone an existing configuration with optional overrides."""
        if source_name in self.components:
            source_config = self.components[source_name]
            new_config = ResponsiveConfig(
                min_width=source_config.min_width,
                max_width=source_config.max_width,
                min_height=source_config.min_height,
                max_height=source_config.max_height,
                size_policy_h=source_config.size_policy_h,
                size_policy_v=source_config.size_policy_v,
                stretch_factor=source_config.stretch_factor
            )
            
            # Apply overrides
            for key, value in overrides.items():
                if hasattr(new_config, key):
                    setattr(new_config, key, value)
            
            self.components[target_name] = new_config


class ResponsiveDialog(QDialog):
    """Base dialog class with responsive behavior and content-based sizing."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setSizeGripEnabled(True)  # Allow manual resizing
        
        # Remove any fixed size constraints
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)  # Qt's QWIDGETSIZE_MAX
        
        # Set responsive size policies
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
    
    def showEvent(self, event):
        """Override to adjust size and center on parent when shown."""
        super().showEvent(event)
        self.adjustSize()  # Size to content
        self.centerOnParent()
    
    def centerOnParent(self):
        """Center dialog on parent window."""
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.center().x() - self.width() // 2,
                parent_geo.center().y() - self.height() // 2
            )


class LayoutValidator:
    """Validates responsive layout configurations and detects issues."""
    
    @staticmethod
    def validate_size_policies(widget: QWidget) -> List[str]:
        """Check for problematic size policy combinations."""
        issues = []
        policy = widget.sizePolicy()
        
        # Check for conflicting fixed policies and size constraints
        if policy.horizontalPolicy() == QSizePolicy.Fixed:
            if hasattr(widget, '_fixed_width_set'):
                issues.append(f"Widget {widget.objectName()} uses both Fixed policy and setFixedWidth")
        
        if policy.verticalPolicy() == QSizePolicy.Fixed:
            if hasattr(widget, '_fixed_height_set'):
                issues.append(f"Widget {widget.objectName()} uses both Fixed policy and setFixedHeight")
        
        # Check for minimum size larger than maximum size
        min_size = widget.minimumSize()
        max_size = widget.maximumSize()
        if min_size.width() > max_size.width() and max_size.width() > 0:
            issues.append(f"Widget {widget.objectName()} minimum width ({min_size.width()}) > maximum width ({max_size.width()})")
        if min_size.height() > max_size.height() and max_size.height() > 0:
            issues.append(f"Widget {widget.objectName()} minimum height ({min_size.height()}) > maximum height ({max_size.height()})")
        
        return issues
    
    @staticmethod
    def validate_layout_hierarchy(layout: QLayout) -> List[str]:
        """Check for layout hierarchy issues."""
        issues = []
        
        # Check for proper stretch factor usage
        total_stretch = 0
        item_count = layout.count()
        
        for i in range(item_count):
            item = layout.itemAt(i)
            if item and item.widget():
                # For layouts that support stretch factors
                if hasattr(layout, 'stretch'):
                    stretch = layout.stretch(i) if hasattr(layout, 'stretch') else 0
                    total_stretch += stretch
        
        # Warn if no stretch factors are set but layout could benefit from them
        if total_stretch == 0 and item_count > 1:
            issues.append(f"Layout has {item_count} items but no stretch factors set - consider using stretch for better responsiveness")
        
        return issues
    
    @staticmethod
    def validate_widget_tree(widget: QWidget) -> List[str]:
        """Recursively validate an entire widget tree for responsive issues."""
        issues = []
        
        # Validate current widget
        issues.extend(LayoutValidator.validate_size_policies(widget))
        
        # Validate layout if present
        if widget.layout():
            issues.extend(LayoutValidator.validate_layout_hierarchy(widget.layout()))
        
        # Recursively validate children
        for child in widget.findChildren(QWidget):
            if child.parent() == widget:  # Only direct children
                issues.extend(LayoutValidator.validate_size_policies(child))
                if child.layout():
                    issues.extend(LayoutValidator.validate_layout_hierarchy(child.layout()))
        
        return issues
    
    @staticmethod
    def detect_fixed_size_constraints(widget: QWidget) -> List[str]:
        """Detect widgets with problematic fixed size constraints."""
        issues = []
        
        # Check for fixed sizes that might prevent responsiveness
        min_size = widget.minimumSize()
        max_size = widget.maximumSize()
        
        # Check for overly restrictive minimum sizes
        if min_size.width() > 500:
            issues.append(f"Widget {widget.objectName()} has large minimum width: {min_size.width()}")
        if min_size.height() > 300:
            issues.append(f"Widget {widget.objectName()} has large minimum height: {min_size.height()}")
        
        # Check for overly restrictive maximum sizes
        if max_size.width() < 800 and max_size.width() > 0:
            issues.append(f"Widget {widget.objectName()} has small maximum width: {max_size.width()}")
        if max_size.height() < 600 and max_size.height() > 0:
            issues.append(f"Widget {widget.objectName()} has small maximum height: {max_size.height()}")
        
        return issues
    
    @staticmethod
    def validate_responsive_patterns(widget: QWidget) -> List[str]:
        """Validate common responsive design patterns."""
        issues = []
        
        # Check for proper use of stretch factors in layouts
        if widget.layout():
            layout = widget.layout()
            if hasattr(layout, 'count') and layout.count() > 1:
                # Check if layout could benefit from stretch factors
                has_stretch = False
                for i in range(layout.count()):
                    if hasattr(layout, 'stretch') and layout.stretch(i) > 0:
                        has_stretch = True
                        break
                
                if not has_stretch:
                    issues.append(f"Layout in {widget.objectName()} could benefit from stretch factors for better space distribution")
        
        # Check for proper size policy usage
        policy = widget.sizePolicy()
        if policy.horizontalPolicy() == QSizePolicy.Fixed and policy.verticalPolicy() == QSizePolicy.Fixed:
            issues.append(f"Widget {widget.objectName()} uses Fixed size policy in both directions - consider making at least one direction flexible")
        
        return issues


# Global registry instance
responsive_registry = ComponentRegistry()

# Pre-register common component configurations
responsive_registry.register_component("expanding_card", ResponsiveConfig(
    size_policy_h=QSizePolicy.Expanding,
    size_policy_v=QSizePolicy.Preferred,
    min_width=200
))

responsive_registry.register_component("flexible_button", ResponsiveConfig(
    size_policy_h=QSizePolicy.Preferred,
    size_policy_v=QSizePolicy.Fixed,
    min_height=32
))

responsive_registry.register_component("content_dialog", ResponsiveConfig(
    size_policy_h=QSizePolicy.Preferred,
    size_policy_v=QSizePolicy.Preferred,
    min_width=300,
    min_height=200
))

responsive_registry.register_component("responsive_image", ResponsiveConfig(
    size_policy_h=QSizePolicy.Expanding,
    size_policy_v=QSizePolicy.Expanding,
    min_width=50,
    min_height=50
))

responsive_registry.register_component("form_input", ResponsiveConfig(
    size_policy_h=QSizePolicy.Expanding,
    size_policy_v=QSizePolicy.Preferred,
    min_height=24
))

responsive_registry.register_component("action_button", ResponsiveConfig(
    size_policy_h=QSizePolicy.Expanding,
    size_policy_v=QSizePolicy.Fixed,
    min_height=36
))

responsive_registry.register_component("icon_button", ResponsiveConfig(
    size_policy_h=QSizePolicy.Preferred,
    size_policy_v=QSizePolicy.Preferred,
    min_width=32,
    min_height=32
))