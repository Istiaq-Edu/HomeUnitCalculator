import sys
import json
import os
import csv
import traceback
from datetime import datetime

from PyQt5.QtCore import QRegExp, Qt, QTimer, QEvent, QSize
from PyQt5.QtGui import QRegExpValidator, QIcon, QPixmap, QColor, QPainter, QLinearGradient, QBrush, QPen, QPalette, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFormLayout, QMessageBox, QSizePolicy,
    QGridLayout, QBoxLayout, QFrame, QMenu, QAction, QSpinBox, QComboBox, QLineEdit,
    QGraphicsDropShadowEffect, QSpacerItem, QLayout

)
from postgrest.exceptions import APIError
from qfluentwidgets import (
    ComboBox, SpinBox, PrimaryPushButton,
    CardWidget, TitleLabel, BodyLabel, CaptionLabel,
    FluentIcon, PushButton, DropDownPushButton, RoundMenu, Action,
    ScrollArea,
    FluentIconBase, StrongBodyLabel
)

from src.core.utils import resource_path
from src.core.add_month_manager import AddMonthManager
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CollapsibleSection, KpiChipBar
from src.ui.flow_layout import FlowLayout

def _clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(round(v))))

def _hex_to_rgb(hex_color: str):
    c = hex_color.strip().lstrip('#')
    if len(c) == 3:
        c = ''.join([ch*2 for ch in c])
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)
    return (r, g, b)

def _rgb_to_hex(rgb):
    return '#%02X%02X%02X' % tuple(_clamp(x) for x in rgb)

def _mix_colors(c1_hex: str, c2_hex: str, ratio: float):
    # ratio 0.0 => c1, 1.0 => c2
    r1, g1, b1 = _hex_to_rgb(c1_hex)
    r2, g2, b2 = _hex_to_rgb(c2_hex)
    r = r1*(1-ratio) + r2*ratio
    g = g1*(1-ratio) + g2*ratio
    b = b1*(1-ratio) + b2*ratio
    return _rgb_to_hex((r, g, b))

def _lighten_color(hex_color: str, ratio: float = 0.75):
    # Blend toward white
    return _mix_colors(hex_color, '#FFFFFF', ratio)

def _darken_color(hex_color: str, ratio: float = 0.35):
    # Blend toward black
    return _mix_colors(hex_color, '#000000', ratio)

def _rgba_from_hex(hex_color: str, alpha: float):
    """Return an rgba() string for Qt StyleSheets given a #RRGGBB color and an alpha 0..1."""
    r, g, b = _hex_to_rgb(hex_color)
    # Qt supports CSS-like rgba(r,g,b,a) with a as 0..1 float
    return f"rgba({r}, {g}, {b}, {alpha})"

class ReadingPairWidget(QWidget):
    """Widget that combines meter and difference inputs in a single row with remove button."""
    
    def __init__(self, pair_index, on_remove_callback):
        super().__init__()
        self.pair_index = pair_index
        self.on_remove_callback = on_remove_callback
        
        # Set responsive size policy and constraints
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(58)  # More compact row height
        self.setMaximumHeight(58)  # Fixed compact height
        
        # Create the input widgets with responsive behavior
        self.meter_input = CustomLineEdit()
        self.meter_input.setObjectName(f"meter_edit_{pair_index}")
        numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))  # only whole numbers
        self.meter_input.setValidator(numeric_validator)
        # Remove placeholder text as per requirement
        self.meter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.meter_input.setMinimumWidth(100)  # Minimum width to prevent collapse
        
        self.diff_input = CustomLineEdit()
        self.diff_input.setObjectName(f"diff_edit_{pair_index}")
        self.diff_input.setValidator(numeric_validator)
        # Remove placeholder text as per requirement
        self.diff_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.diff_input.setMinimumWidth(100)  # Minimum width to prevent collapse
        
        # Connect focus events to ensure visibility in scroll area
        self.meter_input.focusInEvent = self._create_focus_handler(self.meter_input)
        self.diff_input.focusInEvent = self._create_focus_handler(self.diff_input)
        
        # Create remove button with square glass-like background and curved corners
        self.remove_button = PushButton()
        # White close icon
        self.remove_button.setIcon(FluentIcon.CLOSE.icon(color=QColor(255, 255, 255)))
        self.remove_button.setIconSize(QSize(14, 14))
        self.remove_button.setFixedSize(22, 22)  # Square size; height will sync after layout
        self.remove_button.clicked.connect(self._on_remove_clicked)
        # No tooltip on remove button
        self.remove_button.setToolTip("")
        # Square glass-like background with curved corners - no red circle
        self.remove_button.setStyleSheet("""
            PushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: white;
                font-weight: bold;
                padding: 0px; /* center the icon within square button */
            }
            PushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
            }
            PushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.25);
            }
        """)
        
        # Grid layout for perfect alignment (labels row 0, inputs row 1, button at row 1)
        layout = QGridLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(1)

        # Labels
        meter_label = BodyLabel(f"Meter {pair_index + 1} Reading:")
        meter_label.setObjectName("meter_label")
        meter_label.setStyleSheet("""
            font-weight: bold; 
            color: #ffffff;
            font-size: 12px;
            margin: 0px;
        """)
        diff_label = BodyLabel(f"Difference {pair_index + 1} Reading:")
        diff_label.setObjectName("diff_label")
        diff_label.setStyleSheet("""
            font-weight: bold; 
            color: #ffffff;
            font-size: 12px;
            margin: 0px;
        """)

        # Slimmer inputs
        try:
            self.meter_input.setStyleSheet(self.meter_input.styleSheet() + "\nQLineEdit{padding-left:8px; padding-right:8px; padding-top:0px; padding-bottom:0px; min-height:14px;}")
        except Exception:
            pass
        try:
            self.diff_input.setStyleSheet(self.diff_input.styleSheet() + "\nQLineEdit{padding-left:8px; padding-right:8px; padding-top:0px; padding-bottom:0px; min-height:14px;}")
        except Exception:
            pass

        # Place items
        layout.addWidget(meter_label, 0, 0)
        layout.addWidget(diff_label, 0, 1)
        # Wrap inputs with an inner layout to add horizontal padding without shrinking columns
        meter_wrap = QWidget()
        meter_wrap_l = QHBoxLayout(meter_wrap)
        meter_wrap_l.setContentsMargins(8, 0, 8, 0)  # left/right breathing space (even)
        meter_wrap_l.setSpacing(0)
        meter_wrap_l.addWidget(self.meter_input)
        diff_wrap = QWidget()
        diff_wrap_l = QHBoxLayout(diff_wrap)
        diff_wrap_l.setContentsMargins(8, 0, 8, 0)  # even with meter side
        diff_wrap_l.setSpacing(0)
        diff_wrap_l.addWidget(self.diff_input)
        layout.addWidget(meter_wrap, 1, 0)
        layout.addWidget(diff_wrap, 1, 1)
        # Spacer between input and remove button: align with grid spacing for consistency
        layout.setColumnMinimumWidth(2, 12)
        spacer = QSpacerItem(12, 1, QSizePolicy.Fixed, QSizePolicy.Minimum)
        layout.addItem(spacer, 0, 2, 2, 1)

        # Remove button aligned with input row center
        try:
            self.remove_button.setFixedHeight(self.meter_input.sizeHint().height())
        except Exception:
            pass
        layout.addWidget(self.remove_button, 1, 3, alignment=Qt.AlignVCenter | Qt.AlignLeft)
        # Ensure columns stretch evenly and button column remains minimal
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 0)
        layout.setColumnStretch(3, 0)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)

        # After layout, sync button height with input actual height to guarantee alignment
        QTimer.singleShot(0, self._align_controls)
        
        # Apply enhanced styling to the pair widget itself
        self.setStyleSheet("""
            ReadingPairWidget {
                background-color: #323232;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
                margin: 1px 0px;
            }
            ReadingPairWidget:hover {
                background-color: #3a3a3a;
                border: 1px solid #5a5a5a;
            }
        """)
    
    def _align_controls(self):
        """Ensure the remove button vertically matches the input height."""
        try:
            input_h = max(self.meter_input.height(), self.meter_input.sizeHint().height())
            # Keep the remove button perfectly square and centered
            self.remove_button.setFixedHeight(input_h)
            self.remove_button.setFixedWidth(input_h)
        except Exception:
            pass
        
    def _on_remove_clicked(self):
        """Handle remove button click."""
        if self.on_remove_callback:
            self.on_remove_callback(self)
    
    def get_meter_value(self):
        """Get the meter input value."""
        return self.meter_input.text()
    
    def set_meter_value(self, value):
        """Set the meter input value."""
        self.meter_input.setText(str(value))
    
    def get_diff_value(self):
        """Get the difference input value."""
        return self.diff_input.text()
    
    def set_diff_value(self, value):
        """Set the difference input value."""
        self.diff_input.setText(str(value))
    
    def _create_focus_handler(self, widget):
        """Create a focus handler that ensures the widget is visible in the scroll area."""
        original_focus_in = widget.focusInEvent
        
        def focus_handler(event):
            # Call the original focus handler
            original_focus_in(event)
            # Find the main tab and ensure this widget is visible
            parent = self.parent()
            while parent and not hasattr(parent, 'ensure_widget_visible'):
                parent = parent.parent()
            if parent and hasattr(parent, 'ensure_widget_visible'):
                parent.ensure_widget_visible(self)
        
        return focus_handler


class AddPairButton(QWidget):
    """Composite button with a left white icon and bold white text (no overlap)."""
    def __init__(self, text: str, on_click):
        super().__init__()
        self.on_click = on_click
        self.setObjectName("add_pair_btn")
        # Ensure QSS background is painted on QWidget
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)  # center contents horizontally

        # Left icon (white)
        icon_label = QLabel()
        try:
            icon = FluentIcon.ADD.icon(color=QColor(255, 255, 255))
            icon_label.setPixmap(icon.pixmap(20, 20))
        except Exception:
            icon_label.setText("+")
            icon_label.setStyleSheet("color: white; font-weight: bold;")
        icon_label.setFixedSize(20, 20)
        icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        icon_label.setAlignment(Qt.AlignCenter)

        # Text (bold white)
        text_label = BodyLabel(text)
        text_label.setStyleSheet("font-weight: bold; color: white; font-size: 14px;")
        text_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout.addStretch(1)
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)
        layout.addSpacing(8)
        layout.addWidget(text_label, 0, Qt.AlignVCenter)
        layout.addStretch(1)

        # Keep text labels white regardless of theme
        self.setStyleSheet("#add_pair_btn { color: white; }")

    def enterEvent(self, event):
        self._hover = True
        self.update()
        return super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        return super().leaveEvent(event)

    def paintEvent(self, event):
        # Custom paint to ensure full-width blue button with rounded corners
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        radius = 8

        grad = QLinearGradient(r.topLeft(), r.bottomLeft())
        if self._hover:
            grad.setColorAt(0, QColor("#1084d8"))
            grad.setColorAt(1, QColor("#106ebe"))
            border = QColor("#1084d8")
        else:
            grad.setColorAt(0, QColor("#0078D4"))
            grad.setColorAt(1, QColor("#005a9e"))
            border = QColor("#0078D4")

        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(border, 2))
        painter.drawRoundedRect(r, radius, radius)
        # Do not call base class paintEvent afterwards to avoid overwriting our background
        # super().paintEvent(event)
        return

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_click:
            self.on_click()
        return super().mouseReleaseEvent(event)


class ResultCard(QWidget):
    """Individual result card with icon, title, and value display with enhanced styling."""
    
    def __init__(self, title, icon, theme_color, value_label=None):
        super().__init__()
        self.title = title
        self.theme_color = theme_color
        self.value_label = value_label  # Reference to existing label
        
        # Set size policy and constraints (expand horizontally; height sized to fit large text/icon)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(90)
        self.setMaximumHeight(90)
        self.setFixedHeight(90)
        # No maximum width so it can expand horizontally with the window
        
        # Disable interactive hover/focus like billing containers
        self.setAttribute(Qt.WA_Hover, False)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        # Ensure stylesheet background is painted on QWidget
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Fill background from palette/QSS
        self.setAutoFillBackground(True)
        
        # Compute light/dark variants for background/value
        light_bg = _lighten_color(self.theme_color, 0.92)
        dark_accent = _darken_color(self.theme_color, 0.40)
        vivid_accent = _lighten_color(self.theme_color, 0.25)  # brighter number color

        # Assign a stable object name for precise QSS targeting
        self.setObjectName("result_card")

        # Root layout (no padding); inner 'panel' draws background & padding
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        panel = QWidget()
        panel.setObjectName("result_card_panel")
        panel.setAttribute(Qt.WA_StyledBackground, True)
        panel.setAutoFillBackground(True)
        # Fix the panel's height so content never expands it vertically
        panel.setMinimumHeight(90)
        panel.setMaximumHeight(90)
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(24, 6, 24, 6)
        panel_layout.setSpacing(10)
        
        # Icon section with enhanced styling
        icon_label = QLabel()
        if isinstance(icon, FluentIconBase):
            pixmap = icon.icon().pixmap(30, 30)
        else:
            pixmap = icon.pixmap(30, 30) if hasattr(icon, 'pixmap') else QPixmap()
        
        # Apply theme color to icon with better rendering
        if not pixmap.isNull():
            colored_pixmap = QPixmap(pixmap.size())
            colored_pixmap.fill(Qt.transparent)
            painter = QPainter(colored_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(colored_pixmap.rect(), QColor(theme_color))
            painter.end()
            icon_label.setPixmap(colored_pixmap)
        
        # Create a rounded "chip" container to get smooth corners (like the cards)
        icon_chip = QWidget()
        icon_chip.setObjectName("icon_chip")
        icon_chip.setFixedSize(40, 40)
        icon_chip.setAttribute(Qt.WA_StyledBackground, True)
        icon_chip.setAutoFillBackground(True)
        chip_bg_rgba = _rgba_from_hex(self.theme_color, 0.10)
        icon_chip.setStyleSheet(f"""
            #icon_chip {{
                background-color: {chip_bg_rgba};
                border-radius: 12px;  /* 48px -> radius 12 for clean AA */
                border: 1px solid {dark_accent}; /* opaque solid border */
            }}
        """)
        # No shadow to avoid dotted edges on borders
        icon_chip.setGraphicsEffect(None)

        # Center the glyph inside the chip
        icon_label.setAlignment(Qt.AlignCenter)
        chip_layout = QVBoxLayout(icon_chip)
        chip_layout.setContentsMargins(4, 4, 4, 4)
        chip_layout.setSpacing(0)
        chip_layout.addWidget(icon_label, 1, Qt.AlignCenter)
        
        # Title with enhanced styling
        title_label = CaptionLabel(title)
        title_label.setStyleSheet(
            """
            color: #FFFFFF; 
            font-weight: bold; 
            font-size: 13px;
            letter-spacing: 0.5px;
        """
        )
        
        # Value with improved typography (bigger & brighter)
        if value_label:
            self.display_label = value_label
            self.display_label.setStyleSheet(f"""
                color: {vivid_accent}; 
                font-size: 40px; 
                font-weight: 700;
                line-height: 1.2;
            """)
            self.display_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        else:
            self.display_label = BodyLabel("0")
            self.display_label.setStyleSheet(f"""
                color: {vivid_accent}; 
                font-size: 44px; 
                font-weight: 700;
                line-height: 1.2;
            """)
            self.display_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Header row: title left, value right (directly beside the icon)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)
        header_row.addWidget(title_label, 1)
        header_row.addStretch(1)
        header_row.addWidget(self.display_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        # Ensure vertical centering with the icon
        header_row.setAlignment(title_label, Qt.AlignVCenter)
        header_row.setAlignment(self.display_label, Qt.AlignVCenter)
        
        # Place icon and header row in the same horizontal line for perfect vertical alignment
        panel_layout.addWidget(icon_chip)
        panel_layout.addLayout(header_row, 1)
        panel_layout.setAlignment(icon_chip, Qt.AlignVCenter)
        panel_layout.setAlignment(header_row, Qt.AlignVCenter)
        outer_layout.addWidget(panel)
        
        # Style the inner panel to ensure background renders
        frosted_bg = _rgba_from_hex(self.theme_color, 0.16)
        panel_border = _rgba_from_hex(self.theme_color, 0.35)
        panel.setStyleSheet(f"""
            #result_card_panel {{
                background-color: {frosted_bg};
                border: 1px solid {panel_border};
                border-radius: 12px;
            }}
        """)
        # Remove panel shadow to avoid band-like separators between thin cards
        panel.setGraphicsEffect(None)
        
        # Add subtle entrance animation
        self._setup_animations()
    
    def enterEvent(self, event):
        """Do not invoke base CardWidget hover behavior."""
        return  # No-op to keep static appearance

    def leaveEvent(self, event):
        """Do not invoke base CardWidget hover behavior."""
        return  # No-op to keep static appearance

    def event(self, e):
        """Swallow hover events to prevent CardWidget's hover visuals."""
        if e.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True
        return super().event(e)
    
    def _setup_animations(self):
        """Setup subtle animations for the card."""
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        
        # Opacity animation for smooth appearance
        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_animation.setDuration(300)
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def showEvent(self, event):
        """Override show event to trigger entrance animation."""
        super().showEvent(event)
        if hasattr(self, '_opacity_animation'):
            self._opacity_animation.start()
    
    def update_value(self, value):
        """Update the displayed value with smooth transition."""
        if self.value_label:
            self.value_label.setText(str(value))
        else:
            self.display_label.setText(str(value))
        
        # Add subtle pulse effect when value updates
        self._pulse_effect()
    
    def _pulse_effect(self):
        """Add a subtle pulse effect when value updates."""
        # Disabled to prevent geometry animation warnings
        pass


class FinalAmountCard(QWidget):
    """Special Final Amount card with prominent styling, animations, and enhanced visual appeal."""
    
    def __init__(self, value_label):
        super().__init__()
        self.value_label = value_label
        
        # Set size policy and constraints (fixed vertically at 120px, can expand horizontally)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(120)
        self.setMaximumHeight(120)
        self.setFixedHeight(120)
        
        # Disable interactive hover/focus like billing containers
        self.setAttribute(Qt.WA_Hover, False)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        # Ensure stylesheet background is painted on QWidget
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        # Match stylesheet id selector
        self.setObjectName("final_amount_card")
        
        # Root layout (no padding); inner 'panel' draws background & padding
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        panel = QWidget()
        panel.setObjectName("final_amount_panel")
        panel.setAttribute(Qt.WA_StyledBackground, True)
        panel.setAutoFillBackground(True)
        # Fix inner panel to match card height so it doesn't expand vertically
        panel.setMinimumHeight(120)
        panel.setMaximumHeight(120)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(28, 14, 28, 14)  # extra horizontal padding
        layout.setSpacing(16)
        
        # Icon section with enhanced money/total icon
        icon_label = QLabel()
        money_icon = FluentIcon.SHOPPING_CART  # Use shopping cart icon for final amount
        pixmap = money_icon.icon().pixmap(48, 48)  # Even larger icon
        
        # Apply accent color to icon with better rendering
        if not pixmap.isNull():
            colored_pixmap = QPixmap(pixmap.size())
            colored_pixmap.fill(Qt.transparent)
            painter = QPainter(colored_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(colored_pixmap.rect(), QColor("#0078D4"))  # Accent color
            painter.end()
            icon_label.setPixmap(colored_pixmap)
        
        # Compute theme tints (blue theme) and frosted variants
        theme_color = "#0078D4"
        light_bg = _lighten_color(theme_color, 0.90)
        dark_accent = _darken_color(theme_color, 0.40)
        icon_bg_rgba = _rgba_from_hex(theme_color, 0.18)
        border_rgba = _rgba_from_hex(theme_color, 0.45)

        # Use a rounded chip container for smooth corners
        icon_chip = QWidget()
        icon_chip.setObjectName("final_amount_icon_chip")
        icon_chip.setFixedSize(64, 64)
        icon_chip.setAttribute(Qt.WA_StyledBackground, True)
        icon_chip.setAutoFillBackground(True)
        chip_bg_rgba2 = _rgba_from_hex(theme_color, 0.10)
        icon_chip.setStyleSheet(f"""
            #final_amount_icon_chip {{
                background-color: {chip_bg_rgba2};
                border-radius: 16px;  /* 64px -> radius 16 for clean AA */
                border: 1px solid {dark_accent}; /* opaque solid border */
            }}
        """)
        # No shadow to avoid dotted edges on borders
        icon_chip.setGraphicsEffect(None)

        icon_label.setAlignment(Qt.AlignCenter)
        chip_layout2 = QVBoxLayout(icon_chip)
        chip_layout2.setContentsMargins(8, 8, 8, 8)
        chip_layout2.setSpacing(0)
        chip_layout2.addWidget(icon_label, 1, Qt.AlignCenter)
        
        # Content section with header row (title left, number right)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title with enhanced typography
        title_label = CaptionLabel("Final Amount")
        title_label.setStyleSheet("""
            color: #FFFFFF; 
            font-weight: bold; 
            font-size: 16px;
            letter-spacing: 1px;
        """)
        
        # Subtitle with better styling
        subtitle_label = CaptionLabel("Total utility cost")
        subtitle_label.setStyleSheet("""
            color: #aaaaaa; 
            font-size: 12px;
            font-style: italic;
            margin-bottom: 4px;
        """)
        
        # Value with premium typography (bigger & brighter)
        vivid_blue = _lighten_color(theme_color, 0.18)
        self.value_label.setStyleSheet(f"""
            color: {vivid_blue}; 
            font-size: 44px; 
            font-weight: 800;
            line-height: 1.1;
        """)
        self.value_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        # Center title and value vertically stacked
        content_layout.addWidget(title_label, 0, Qt.AlignHCenter)
        content_layout.addWidget(self.value_label, 0, Qt.AlignHCenter)
        content_layout.addWidget(subtitle_label, 0, Qt.AlignHCenter)
        content_layout.addStretch()
        
        # Add to panel then to outer layout
        layout.addWidget(icon_chip)
        layout.addLayout(content_layout, 1)
        layout.setAlignment(icon_chip, Qt.AlignVCenter)
        layout.setAlignment(content_layout, Qt.AlignVCenter)
        outer_layout.addWidget(panel)
        
        # Style the inner panel to ensure background renders
        frosted_bg = _rgba_from_hex(theme_color, 0.14)
        panel_border = _rgba_from_hex(theme_color, 0.45)
        panel.setStyleSheet(f"""
            #final_amount_panel {{
                background-color: {frosted_bg};
                border: 2px solid {panel_border};
                border-radius: 12px;  /* match parent rounding */
            }}
        """)
        # Remove panel shadow for visual consistency with thin cards
        panel.setGraphicsEffect(None)
        
        # Setup premium animations
        self._setup_premium_animations()
    
    def enterEvent(self, event):
        """Do not invoke base CardWidget hover behavior."""
        return  # No-op to keep static appearance

    def leaveEvent(self, event):
        """Do not invoke base CardWidget hover behavior."""
        return  # No-op to keep static appearance

    def event(self, e):
        """Swallow hover events to prevent CardWidget's hover visuals."""
        if e.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True
        return super().event(e)
    
    def _setup_premium_animations(self):
        """Setup premium animations for the final amount card."""
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        
        # Only use opacity animation (geometry animation causes warnings)
        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_animation.setDuration(300)
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def showEvent(self, event):
        """Override show event to trigger entrance animation."""
        super().showEvent(event)
        if hasattr(self, '_opacity_animation'):
            self._opacity_animation.start()
    
    def update_value(self, value):
        """Update the displayed value with premium animation effects."""
        self.value_label.setText(str(value))
        self._premium_update_effect()
    
    def _premium_update_effect(self):
        """Add premium visual effects when value updates."""
        # Disabled to prevent animation warnings
        pass


class MainTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref 

        self.month_combo = None
        self.year_spinbox = None
        self.meter_entries = []
        self.diff_entries = []
        self.reading_pairs = []  # List of ReadingPairWidget instances
        self.additional_amount_input = None
        self.total_unit_value_label = None
        self.total_diff_value_label = None
        self.per_unit_cost_value_label = None
        self.additional_amount_value_label = None
        self.in_total_value_label = None
        self.main_calculate_button = None
        self.save_to_cloud_button = None # New button for saving to cloud
        
        self.load_month_combo = None
        self.load_year_spinbox = None
        
        # Initialize AddMonthManager
        self.add_month_manager = None  # Will be initialized after main window is fully set up

        # Store references to layout components for responsive behavior
        self.left_column_widget = None
        self.right_column_widget = None
        self.content_layout = None
        self.main_scroll_area = None
        self.pairs_scroll = None
        self.results_group_widget = None
        self._results_group_locked_height = None
        self._billing_unified_group = None
        self._no_select_lineedits = set()
        self._no_focus_spinboxes = set()

        # Room calculation attributes
        self.room_entries = []
        self.rooms_scroll_layout = None
        self.rooms_scroll_area = None
        self.num_rooms_spinbox = None
        self.calculate_rooms_button = None

        self.init_ui()

    def resizeEvent(self, event):
        """Handle window resize events to adjust layout responsively."""
        super().resizeEvent(event)
        self.adjust_responsive_layout()
        # Re-apply pairs scroll exact height to prevent vertical drift
        try:
            QTimer.singleShot(0, self.update_pairs_scroll_height)
        except Exception:
            pass

    def adjust_responsive_layout(self):
        """Adjust layout based on current window size. Vertical flow layout needs no column adjustments."""
        pass
    
    def ensure_widget_visible(self, widget):
        """Ensure a widget is visible in the most appropriate scroll area."""
        if not widget:
            return
        # Prefer the inner Reading Pairs scroll area if the widget is inside it
        if self.pairs_scroll and self.pairs_scroll.widget():
            parent = widget.parent()
            while parent is not None:
                if parent == self.pairs_scroll.widget() or parent == self.pairs_scroll:
                    self.pairs_scroll.ensureWidgetVisible(widget)
                    return
                parent = parent.parent()
        # Fallback to main page scroll area
        if self.main_scroll_area:
            self.main_scroll_area.ensureWidgetVisible(widget)

    def eventFilter(self, obj, event):
        """Swallow mouse clicks on the billing and load containers' backgrounds only, not their children."""
        try:
            if (obj is getattr(self, '_billing_unified_group', None) or
                obj is getattr(self, '_load_data_group', None)) and event.type() in (
                QEvent.MouseButtonPress,
                QEvent.MouseButtonRelease,
                QEvent.MouseButtonDblClick,
            ):
                return True  # ignore clicks on empty area of the container
            # Prevent selection highlight for spinbox lineEdits we track
            if obj in self._no_select_lineedits:
                if event.type() in (QEvent.FocusIn, QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
                    obj.deselect()
                    obj.setCursorPosition(len(obj.text()))
                    return False
                if event.type() == QEvent.KeyPress and (event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_A:
                    # Block Ctrl+A select all
                    return True
            # Swallow focus for tracked spinboxes to avoid focus underline/box-color
            if obj in self._no_focus_spinboxes and event.type() == QEvent.FocusIn:
                return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _apply_no_select_to_spinbox(self, spinbox):
        """Disable text selection and focus underline for a SpinBox safely.

        - Do not change geometry or base styles.
        - Remove focus so focus-underlines don't appear.
        - Make inner editor selection invisible and auto-deselect on interactions.
        - When arrows change the value, clear selection and focus.
        """
        try:
            # Prevent focus state so underline color doesn't appear
            spinbox.setFocusPolicy(Qt.NoFocus)
            self._no_focus_spinboxes.add(spinbox)
            spinbox.installEventFilter(self)
            le = None
            if hasattr(spinbox, 'lineEdit'):
                try:
                    le = spinbox.lineEdit()
                except Exception:
                    le = None
            if le is None:
                le = spinbox.findChild(QLineEdit)
            if le is None:
                # Defer if not ready yet
                QTimer.singleShot(0, lambda: self._apply_no_select_to_spinbox(spinbox))
                return
            # Inner editor should also not accept focus
            le.setFocusPolicy(Qt.NoFocus)
            le.installEventFilter(self)
            # Make selection invisible on the editor only (doesn't change box layout)
            try:
                pal = le.palette()
                pal.setColor(QPalette.Highlight, QColor(0, 0, 0, 0))
                pal.setColor(QPalette.HighlightedText, pal.color(QPalette.Text))
                le.setPalette(pal)
            except Exception:
                pass
            # Clear selection initially and after interactions
            def _clear_sel():
                try:
                    le.deselect(); le.setCursorPosition(len(le.text()))
                except Exception:
                    pass
            _clear_sel()
            try:
                le.selectionChanged.connect(_clear_sel)
            except Exception:
                pass
            # When arrows change value, clear selection/focus immediately after
            try:
                spinbox.valueChanged.connect(lambda *_: QTimer.singleShot(0, lambda: (spinbox.clearFocus(), _clear_sel())))
            except Exception:
                pass
        except Exception:
            pass

    def init_ui(self):
        # ── Root layout ─────────────────────────────────────────────────
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        # ── Scroll area ─────────────────────────────────────────────────
        self.main_scroll_area = ScrollArea()
        self.main_scroll_area.setWidgetResizable(True)
        self.main_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content_widget = QWidget()
        scroll_content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        main_layout = QVBoxLayout(scroll_content_widget)
        main_layout.setSpacing(24)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ── 1. Actions (collapsible, expanded by default) ──────────────
        actions_content = QWidget()
        actions_content.setStyleSheet("""
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 12px;
        """)
        actions_content.setAttribute(Qt.WA_StyledBackground, True)
        actions_content.setAutoFillBackground(True)
        actions_content.setFocusPolicy(Qt.NoFocus)
        actions_content.setAttribute(Qt.WA_Hover, False)
        actions_content.setMouseTracking(False)
        self._load_data_group = actions_content
        actions_content.installEventFilter(self)

        actions_layout = QVBoxLayout(actions_content)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        # Three distinct containers stacked vertically
        load_data_container = self._create_load_data_container()
        actions_layout.addWidget(load_data_container)

        save_options_container = self._create_save_options_container()
        actions_layout.addWidget(save_options_container)

        add_next_month_container = self._create_add_next_month_container()
        actions_layout.addWidget(add_next_month_container)

        actions_section = CollapsibleSection("\u26a1 Actions", actions_content, expanded=True)
        main_layout.addWidget(actions_section)

        # ── 2. Unified Billing & Calculation card ───────────────────────
        unified_card = self.create_unified_calculator_card()
        main_layout.addWidget(unified_card)

        # ── 3. Room Calculations section ────────────────────────────────
        rooms_section = self._create_rooms_section()
        main_layout.addWidget(rooms_section)

        # ── Scroll area setup ───────────────────────────────────────────
        self.main_scroll_area.setWidget(scroll_content_widget)
        root_layout.addWidget(self.main_scroll_area)

        # ── Initialize reading pairs ────────────────────────────────────
        for _ in range(3):
            self.add_reading_pair()

        QTimer.singleShot(50, self.update_pairs_scroll_height)

        # ── Final theming ───────────────────────────────────────────────
        self._apply_consistent_theming()

    def create_billing_and_reading_container(self):
        """Create the unified 'Billing Period And Meter Reading' card containing all three sections."""
        # Use a plain QWidget so the outer container has no interactive hover/press visuals
        unified_group = QWidget()
        unified_group.setObjectName("billing_meter_container")
        # Force static appearance on hover for the outer container only
        # Ensure style background is painted
        unified_group.setAttribute(Qt.WA_StyledBackground, True)
        # Do not take focus or track hover/mouse at the container level
        unified_group.setFocusPolicy(Qt.NoFocus)
        unified_group.setAttribute(Qt.WA_Hover, False)
        unified_group.setMouseTracking(False)
        # Do not intercept clicks; instead, we swallow only container background clicks via eventFilter
        self._billing_unified_group = unified_group
        unified_group.installEventFilter(self)
        unified_group.setStyleSheet(
            """
            #billing_meter_container {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
            #billing_meter_container:hover, #billing_meter_container:pressed {
                background-color: #2b2b2b; /* same as normal */
                border: 1px solid #3d3d3d;
            }
            """
        )
        # Hug content vertically; don't stretch when the window is tall
        unified_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Remove fixed minimum height to allow dynamic sizing based on content
        
        # Remove border from main container since individual sections will have thick borders
        
        unified_layout = QVBoxLayout(unified_group)
        unified_layout.setContentsMargins(20, 20, 20, 20)
        unified_layout.setSpacing(16)
        
        # Main title for the unified card
        main_title = TitleLabel("Billing Period & Meter Reading")
        main_title.setAlignment(Qt.AlignCenter)
        main_title.setStyleSheet("""
            font-size: 28px;
            font-weight: 800;
            color: #0078D4;
            letter-spacing: 1px;
            margin: 8px 0px;
        """)
        unified_layout.addWidget(main_title)
        
        main_line = QFrame()
        main_line.setFrameShape(QFrame.HLine)
        main_line.setFrameShadow(QFrame.Plain)
        main_line.setStyleSheet("""
            color: #0078D4;
            background-color: #0078D4;
            border: none;
            height: 2px;
            margin: 4px 20px;
        """)
        unified_layout.addWidget(main_line)
        
        # Section 1: Billing Period (frosted, no hover)
        # Use a plain QWidget (not CardWidget) so no interactive state/overlay is drawn
        period_box = QWidget()
        period_box.setObjectName("billing_period_box")
        period_box.setStyleSheet("""
            #billing_period_box { 
                background: transparent; 
                border: none; 
                margin: 8px 0px; 
                padding: 0px; 
            }
            #billing_period_box:hover, #billing_period_box:pressed { 
                background: transparent; 
                border: none; 
            }
        """)
        # Inner frosted panel
        period_outer_layout = QVBoxLayout(period_box)
        period_outer_layout.setContentsMargins(0, 0, 0, 0)
        period_outer_layout.setSpacing(0)
        period_inner = QWidget()
        period_inner.setObjectName("billing_period_inner")
        # Ensure style background with alpha is rendered
        period_inner.setAttribute(Qt.WA_StyledBackground, True)
        # Prevent hover/focus visual changes on the container itself
        period_inner.setFocusPolicy(Qt.NoFocus)
        period_inner.setAttribute(Qt.WA_Hover, False)
        period_inner.setMouseTracking(False)
        period_inner.setStyleSheet("""
            #billing_period_inner {
                background-color: rgba(255, 255, 255, 0.14); /* subtle frost */
                border: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 12px;
            }
            #billing_period_inner:hover, #billing_period_inner:pressed { 
                background-color: rgba(255, 255, 255, 0.14); 
                border: 1px solid rgba(255, 255, 255, 0.28); 
            }
        """)
        period_outer_layout.addWidget(period_inner)
        # Apply subtle drop shadow for frosted effect
        _shadow1 = QGraphicsDropShadowEffect(self)
        _shadow1.setBlurRadius(18)
        _shadow1.setOffset(0, 2)
        _shadow1.setColor(QColor(0, 0, 0, 120))
        period_inner.setGraphicsEffect(_shadow1)
        period_layout = QVBoxLayout(period_inner)
        period_layout.setContentsMargins(16, 12, 16, 12)
        period_layout.setSpacing(8)
        
        period_title = BodyLabel("Billing Period")
        period_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #0078D4;
            margin: 4px 0px;
        """)
        period_layout.addWidget(period_title)
        # Thin separator line under Billing Period heading
        period_sep = QFrame()
        period_sep.setFrameShape(QFrame.HLine)
        period_sep.setFrameShadow(QFrame.Plain)
        period_sep.setStyleSheet("""
            color: #1084d8;
            background-color: #1084d8;
            border: none;
            height: 3px;
            margin: 2px 0px 6px 0px;
        """)
        period_layout.addWidget(period_sep)
        
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)
        controls_layout.addStretch(1)

        month_label = BodyLabel("Month:")
        month_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.month_combo = ComboBox()
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])

        year_label = BodyLabel("Year:")
        year_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.year_spinbox = SpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        # Apply safe selection suppression that doesn't affect layout or focus visuals
        self._apply_no_select_to_spinbox(self.year_spinbox)
        # Do not allow focus so the box color doesn't change; arrows remain clickable
        self.year_spinbox.setFocusPolicy(Qt.NoFocus)
        QTimer.singleShot(0, lambda: (self.year_spinbox.lineEdit() and self.year_spinbox.lineEdit().setFocusPolicy(Qt.NoFocus)))
        # Make the value bold to match month combo text weight (inline)
        try:
            le = self.year_spinbox.lineEdit() if hasattr(self.year_spinbox, 'lineEdit') else None
            if le is None:
                QTimer.singleShot(0, lambda: (
                    self.year_spinbox.lineEdit() and self.year_spinbox.lineEdit().setFont(self.year_spinbox.lineEdit().font().setBold(True))
                ))
            else:
                f = le.font()
                f.setBold(True)
                le.setFont(f)
        except Exception:
            pass

        controls_layout.addWidget(month_label)
        controls_layout.addWidget(self.month_combo)
        controls_layout.addSpacing(20)
        controls_layout.addWidget(year_label)
        controls_layout.addWidget(self.year_spinbox)
        controls_layout.addStretch(1)
        
        period_layout.addLayout(controls_layout)
        unified_layout.addWidget(period_box)
        
        # Section 2: Reading Pairs (frosted, no hover)
        # Use a plain QWidget (not CardWidget) so no interactive state/overlay is drawn
        pairs_box = QWidget()
        pairs_box.setObjectName("reading_pairs_box")
        pairs_box.setStyleSheet("""
            #reading_pairs_box { 
                background: transparent; 
                border: none; 
                margin: 8px 0px; 
                padding: 0px; 
            }
            #reading_pairs_box:hover, #reading_pairs_box:pressed { 
                background: transparent; 
                border: none; 
            }
        """)
        pairs_outer_layout = QVBoxLayout(pairs_box)
        pairs_outer_layout.setContentsMargins(0, 0, 0, 0)
        pairs_outer_layout.setSpacing(0)
        pairs_inner = QWidget()
        pairs_inner.setObjectName("reading_pairs_inner")
        pairs_inner.setAttribute(Qt.WA_StyledBackground, True)
        # Prevent vertical stretching; let it hug its content
        pairs_inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Prevent hover/focus visual changes on the container itself
        pairs_inner.setFocusPolicy(Qt.NoFocus)
        pairs_inner.setAttribute(Qt.WA_Hover, False)
        pairs_inner.setMouseTracking(False)
        pairs_inner.setStyleSheet("""
            #reading_pairs_inner {
                background-color: rgba(255, 255, 255, 0.14); /* subtle frost */
                border: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 12px;
            }
            #reading_pairs_inner:hover, #reading_pairs_inner:pressed { 
                background-color: rgba(255, 255, 255, 0.14); 
                border: 1px solid rgba(255, 255, 255, 0.28); 
            }
        """)
        pairs_outer_layout.addWidget(pairs_inner)
        _shadow2 = QGraphicsDropShadowEffect(self)
        _shadow2.setBlurRadius(18)
        _shadow2.setOffset(0, 2)
        _shadow2.setColor(QColor(0, 0, 0, 120))
        pairs_inner.setGraphicsEffect(_shadow2)
        pairs_layout = QVBoxLayout(pairs_inner)
        pairs_layout.setContentsMargins(16, 8, 16, 10)  # keep some baseline padding
        pairs_layout.setSpacing(12)  # more space between scroll and button
        
        pairs_title = BodyLabel("Reading Pairs")
        pairs_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #0078D4;
            margin: 4px 0px;
        """)
        pairs_layout.addWidget(pairs_title)
        # Thin separator line under Reading Pairs heading
        pairs_sep = QFrame()
        pairs_sep.setFrameShape(QFrame.HLine)
        pairs_sep.setFrameShadow(QFrame.Plain)
        pairs_sep.setStyleSheet("""
            color: #1084d8;
            background-color: #1084d8;
            border: none;
            height: 3px;
            margin: 2px 0px 6px 0px;
        """)
        pairs_layout.addWidget(pairs_sep)
        
        # Container for pairs (no scrolling - expands to fit content)
        pairs_scroll = ScrollArea()
        pairs_scroll.setObjectName("reading_pairs_scroll")
        pairs_scroll.setWidgetResizable(True)
        pairs_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Fixed height to prevent expanding
        # Dynamic height calculation: base height + (number of pairs * pair height)
        pairs_scroll.setMinimumHeight(110)  # Base height for at least one pair
        # Remove maximum height constraint to allow proper expansion
        pairs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # No vertical scroll bar
        pairs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # No horizontal scroll bar
        # Use QFluentWidgets default styling (no custom QSS)
        pairs_container = QWidget()
        pairs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pairs_layout = QVBoxLayout(pairs_container)
        self.pairs_layout.setSpacing(2)
        self.pairs_layout.setContentsMargins(4, 2, 4, 10)  # add more bottom padding for visual gap
        # No stretch: content should hug the bottom of the scroll area to reduce gap to the button
        pairs_scroll.setWidget(pairs_container)
        # Do not give stretch so it won't claim extra vertical space; keep it top-aligned
        pairs_layout.addWidget(pairs_scroll, 0, Qt.AlignTop)
        self.pairs_scroll = pairs_scroll
        # Keep references used for precise height locking
        self._pairs_inner_widget = pairs_inner
        self._pairs_title_label = pairs_title
        self._pairs_sep_line = pairs_sep
        
        # Add Reading Pair composite button (icon on the left of text, no overlap)
        # Insert a fixed spacer above the button and a holder with a top margin to ensure visible gap
        self._pairs_fixed_gap = 12
        pairs_layout.addSpacing(self._pairs_fixed_gap)
        self._pairs_btn_top_gap = 14
        add_pair_button = AddPairButton("Add Reading Pair", lambda: self.add_reading_pair())
        button_holder = QWidget()
        _btn_holder_layout = QVBoxLayout(button_holder)
        _btn_holder_layout.setContentsMargins(0, self._pairs_btn_top_gap, 0, 0)
        _btn_holder_layout.setSpacing(0)
        _btn_holder_layout.addWidget(add_pair_button)
        pairs_layout.addWidget(button_holder)
        self._pairs_add_button = add_pair_button
        
        unified_layout.addWidget(pairs_box)
        
        # Section 3: Additional Amount (frosted, no hover)
        # Use a plain QWidget (not CardWidget) so no interactive state/overlay is drawn
        amount_box = QWidget()
        amount_box.setObjectName("additional_amount_box")
        amount_box.setStyleSheet("""
            #additional_amount_box { 
                background: transparent; 
                border: none; 
                margin: 8px 0px; 
                padding: 0px; 
            }
            #additional_amount_box:hover, #additional_amount_box:pressed { 
                background: transparent; 
                border: none; 
            }
        """)
        amount_outer_layout = QVBoxLayout(amount_box)
        amount_outer_layout.setContentsMargins(0, 0, 0, 0)
        amount_outer_layout.setSpacing(0)
        amount_inner = QWidget()
        amount_inner.setObjectName("additional_amount_inner")
        amount_inner.setAttribute(Qt.WA_StyledBackground, True)
        # Prevent hover/focus visual changes on the container itself
        amount_inner.setFocusPolicy(Qt.NoFocus)
        amount_inner.setAttribute(Qt.WA_Hover, False)
        amount_inner.setMouseTracking(False)
        amount_inner.setStyleSheet("""
            #additional_amount_inner {
                background-color: rgba(255, 255, 255, 0.14); /* subtle frost */
                border: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 12px;
            }
            #additional_amount_inner:hover, #additional_amount_inner:pressed { 
                background-color: rgba(255, 255, 255, 0.14); 
                border: 1px solid rgba(255, 255, 255, 0.28); 
            }
        """)
        amount_outer_layout.addWidget(amount_inner)
        _shadow3 = QGraphicsDropShadowEffect(self)
        _shadow3.setBlurRadius(18)
        _shadow3.setOffset(0, 2)
        _shadow3.setColor(QColor(0, 0, 0, 120))
        amount_inner.setGraphicsEffect(_shadow3)
        amount_layout = QVBoxLayout(amount_inner)
        amount_layout.setContentsMargins(16, 12, 16, 12)
        amount_layout.setSpacing(8)

        amount_title = BodyLabel("Additional Amount:")
        amount_title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #0078D4;
            margin: 4px 0px;
        """)
        amount_layout.addWidget(amount_title)
        # Thin separator line under Additional Amount heading
        amount_sep = QFrame()
        amount_sep.setFrameShape(QFrame.HLine)
        amount_sep.setFrameShadow(QFrame.Plain)
        amount_sep.setStyleSheet("""
            color: #1084d8;
            background-color: #1084d8;
            border: none;
            height: 3px;
            margin: 2px 0px 6px 0px;
        """)
        amount_layout.addWidget(amount_sep)
        
        self.additional_amount_input = CustomLineEdit()
        self.additional_amount_input.setObjectName("main_additional_amount_input")
        self.additional_amount_input.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))
        
        currency_label = CaptionLabel("TK")
        currency_label.setStyleSheet("""
            font-weight: bold;
            color: #ffffff;
            font-size: 12px;
            padding: 8px 4px;
        """)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.additional_amount_input, 1)
        input_layout.addWidget(currency_label)
        input_layout.setSpacing(8)

        amount_layout.addLayout(input_layout)
        unified_layout.addWidget(amount_box)
        
        # No tooltip on the outer billing container
        return unified_group

    def create_additional_amount_group(self):
        amount_group = CardWidget()
        amount_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # amount_group.setFixedHeight(110) # Removed for responsiveness
        amount_layout = QVBoxLayout(amount_group)
        amount_layout.setContentsMargins(16, 12, 16, 12)  # Increased margins
        amount_layout.setSpacing(8)  # Increased spacing
        amount_layout.setDirection(QBoxLayout.TopToBottom)

        amount_label = BodyLabel("Additional Amount:")
        amount_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #0078D4;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        """)
        amount_layout.addWidget(amount_label)
        
        self.additional_amount_input = CustomLineEdit()
        self.additional_amount_input.setObjectName("main_additional_amount_input")
        self.additional_amount_input.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))
        
        currency_label = CaptionLabel("TK")
        currency_label.setStyleSheet("""
            font-weight: bold;
            color: #ffffff;
            font-size: 12px;
            padding: 8px 4px;
        """)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.additional_amount_input, 1)
        input_layout.addWidget(currency_label)
        input_layout.setSpacing(8)

        amount_layout.addLayout(input_layout)
        amount_group.setToolTip("Enter any additional amount to be added to the total bill")
        return amount_group

    def create_reading_pairs_container(self):
        """Create the reading pairs container with dynamic pair management and responsive behavior."""
        pairs_group = CardWidget()
        # Set responsive size policy and constraints
        pairs_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pairs_group.setMinimumHeight(200)  # Minimum height to prevent collapse
        pairs_group.setMaximumHeight(400)  # Maximum height to prevent excessive growth
        pairs_layout = QVBoxLayout(pairs_group)
        pairs_layout.setContentsMargins(8, 8, 8, 8)
        pairs_layout.setSpacing(4)
        
        # Title and separator
        pairs_title = TitleLabel("Reading Pairs")
        pairs_title.setAlignment(Qt.AlignCenter)
        pairs_title.setStyleSheet("""
            font-size: 26px;
            font-weight: 800;
            color: #0078D4;
            letter-spacing: 1px;
            margin: 8px 0px;
        """)
        pairs_layout.addWidget(pairs_title)
        
        pairs_line = QFrame()
        pairs_line.setFrameShape(QFrame.HLine)
        pairs_line.setFrameShadow(QFrame.Plain)
        pairs_line.setStyleSheet("""
            color: #0078D4;
            background-color: #0078D4;
            border: none;
            height: 2px;
            margin: 4px 20px;
        """)
        pairs_layout.addWidget(pairs_line)
        
        # Scroll area for pairs with responsive behavior
        pairs_scroll = AutoScrollArea()
        pairs_scroll.setWidgetResizable(True)
        pairs_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pairs_scroll.setMinimumHeight(120)  # Minimum height for at least one pair
        pairs_container = QWidget()
        pairs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pairs_layout = QVBoxLayout(pairs_container)
        self.pairs_layout.setSpacing(8)
        pairs_scroll.setWidget(pairs_container)
        pairs_layout.addWidget(pairs_scroll, 1)  # Give scroll area stretch factor
        
        # Add Reading Pair button with white icon and bold text
        add_pair_button = PrimaryPushButton("Add Reading Pair")
        add_pair_button.setIcon(FluentIcon.ADD)
        add_pair_button.clicked.connect(self.add_reading_pair)
        add_pair_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078D4, stop:1 #005a9e);
                border: 2px solid #0078D4;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 20px;
                text-align: center;
            }
            PrimaryPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1084d8, stop:1 #106ebe);
                border-color: #1084d8;
            }
            PrimaryPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #005a9e, stop:1 #004578);
                border-color: #005a9e;
            }
        """)
        pairs_layout.addWidget(add_pair_button)
        
        return pairs_group

    def add_reading_pair(self):
        """Add a new reading pair."""
        pair_index = len(self.reading_pairs)
        pair_widget = ReadingPairWidget(pair_index, self.remove_reading_pair)
        
        # Append to the end (we no longer use a bottom stretch spacer)
        self.pairs_layout.addWidget(pair_widget)
        self.reading_pairs.append(pair_widget)
        
        # Add to existing meter_entries and diff_entries arrays for compatibility
        self.meter_entries.append(pair_widget.meter_input)
        self.diff_entries.append(pair_widget.diff_input)
        
        # Update scroll area height after adding pair
        self.update_pairs_scroll_height()
        
        # Re-configure navigation whenever widgets change
        if hasattr(self, 'setup_navigation_main_tab'):
            self.setup_navigation_main_tab()
    
    def remove_reading_pair(self, pair_widget):
        """Remove a reading pair."""
        if pair_widget in self.reading_pairs:
            # Remove from tracking lists
            pair_index = self.reading_pairs.index(pair_widget)
            self.reading_pairs.remove(pair_widget)
            
            # Remove from meter_entries and diff_entries arrays
            if pair_widget.meter_input in self.meter_entries:
                self.meter_entries.remove(pair_widget.meter_input)
            if pair_widget.diff_input in self.diff_entries:
                self.diff_entries.remove(pair_widget.diff_input)
            
            # Remove from layout and delete widget
            self.pairs_layout.removeWidget(pair_widget)
            pair_widget.setParent(None)
            pair_widget.deleteLater()
            
            # Update indices for remaining pairs
            self.update_pair_indices()
            
            # Update scroll area height after removing pair
            self.update_pairs_scroll_height()
            
            # Re-configure navigation whenever widgets change
            if hasattr(self, 'setup_navigation_main_tab'):
                self.setup_navigation_main_tab()
    
    def update_pair_indices(self):
        """Update the indices and labels of all reading pairs after removal."""
        for i, pair_widget in enumerate(self.reading_pairs):
            pair_widget.pair_index = i
            # Update object names
            pair_widget.meter_input.setObjectName(f"meter_edit_{i}")
            pair_widget.diff_input.setObjectName(f"diff_edit_{i}")
            
            # Update labels using object names (robust against layout structure changes)
            meter_label = pair_widget.findChild(BodyLabel, "meter_label")
            if meter_label:
                meter_label.setText(f"Meter {i + 1} Reading:")
            diff_label = pair_widget.findChild(BodyLabel, "diff_label")
            if diff_label:
                diff_label.setText(f"Difference {i + 1} Reading:")
    
    def update_pairs_scroll_height(self):
        """Update the scroll area height based on the number of reading pairs."""
        if not hasattr(self, 'pairs_scroll') or not self.pairs_scroll:
            return
            
        num_pairs = len(self.reading_pairs)
        if num_pairs == 0:
            return
            
        # Calculate optimal height strictly for the rows area (exclude title and separator)
        try:
            # Use sizeHint/minimumHeight to be robust even before widget is shown
            ph_hint = self.reading_pairs[0].sizeHint().height()
            ph_min = self.reading_pairs[0].minimumHeight()
            pair_height = max(1, ph_hint, ph_min)
        except Exception:
            pair_height = 58  # fallback
        spacing = 2
        try:
            spacing = max(0, self.pairs_layout.spacing())
        except Exception:
            pass
        top = bottom = 0
        try:
            _, top, _, bottom = self.pairs_layout.getContentsMargins()
        except Exception:
            pass
        padding = max(0, top + bottom)
        
        # Total content height inside the scroll viewport (no title/sep area)
        total_content_height = (num_pairs * pair_height) + ((num_pairs - 1) * spacing) + padding
        
        # Set reasonable limits
        min_height = max(58, pair_height + padding)  # Minimum for one pair
        
        # Calculate ideal height (no maximum limit since we don't want scroll bars)
        ideal_height = max(min_height, total_content_height)
        
        # Apply the calculated height - both min and max to exact size
        self.pairs_scroll.setMinimumHeight(ideal_height)
        self.pairs_scroll.setMaximumHeight(ideal_height)  # Set exact height to prevent scrolling
        try:
            self.pairs_scroll.setFixedHeight(ideal_height)
        except Exception:
            pass
        
        # Additionally lock the entire inner section height (title + sep + pairs + button)
        try:
            header_h = 0
            if hasattr(self, '_pairs_title_label') and self._pairs_title_label:
                header_h += self._pairs_title_label.sizeHint().height()
            if hasattr(self, '_pairs_sep_line') and self._pairs_sep_line:
                header_h += self._pairs_sep_line.sizeHint().height()
            button_h = 0
            if hasattr(self, '_pairs_add_button') and self._pairs_add_button:
                button_h = self._pairs_add_button.sizeHint().height()
            # Spacing between: title|sep, sep|scroll, scroll|button
            try:
                vspace = max(0, pairs_layout.spacing()) if (pairs_layout := self._pairs_title_label.parentWidget().layout()) else 4
            except Exception:
                vspace = 4
            inter_spacing = vspace * 3  # title|sep, sep|scroll, scroll|button
            # Margins of the pairs_layout (top+bottom)
            try:
                _, top2, _, bottom2 = pairs_layout.getContentsMargins()
            except Exception:
                top2 = bottom2 = 0
            # Include the explicit spacing we inserted above the button
            extra_btn_gap = getattr(self, '_pairs_btn_top_gap', 10)
            extra_fixed_gap = getattr(self, '_pairs_fixed_gap', 0)
            total_inner_h = header_h + ideal_height + extra_fixed_gap + extra_btn_gap + button_h + inter_spacing + top2 + bottom2
            if hasattr(self, '_pairs_inner_widget') and self._pairs_inner_widget:
                self._pairs_inner_widget.setMinimumHeight(total_inner_h)
                self._pairs_inner_widget.setMaximumHeight(total_inner_h)
        except Exception:
            pass
        
        # Force layout update
        self.pairs_scroll.updateGeometry()
        if self.pairs_scroll.parent():
            self.pairs_scroll.parent().updateGeometry()

    def get_additional_amount(self):
        try:
            return float(self.additional_amount_input.text()) if self.additional_amount_input.text() else 0.0
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric value for the additional amount.")
            return 0.0

    def create_results_group(self):
        # Create a titled QWidget (non-interactive) to group all result cards together
        results_group = QWidget()
        # Horizontal: expand; Vertical: fixed to sizeHint (won't stretch on fullscreen)
        results_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Keep the outer container static on hover (no interactive hover effect)
        results_group.setObjectName("results_group_container")
        # Ensure style background is painted and interaction is disabled
        results_group.setAttribute(Qt.WA_StyledBackground, True)
        results_group.setFocusPolicy(Qt.NoFocus)
        results_group.setAttribute(Qt.WA_Hover, False)
        results_group.setMouseTracking(False)
        results_group.setStyleSheet(
            """
            #results_group_container {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
            """
        )
        group_layout = QVBoxLayout(results_group)
        group_layout.setContentsMargins(20, 20, 20, 20)
        group_layout.setSpacing(10)

        # Title and separator for the group
        group_title = TitleLabel("Calculation Results")
        group_title.setAlignment(Qt.AlignCenter)
        group_title.setStyleSheet(
            """
            font-size: 28px;
            font-weight: 800;
            color: #0078D4;
            letter-spacing: 1px;
            margin: 8px 0px;
            """
        )
        group_layout.addWidget(group_title)

        group_line = QFrame()
        group_line.setFrameShape(QFrame.HLine)
        group_line.setFrameShadow(QFrame.Plain)
        group_line.setStyleSheet(
            """
            color: #0078D4;
            background-color: #0078D4;
            border: none;
            height: 2px;
            margin: 4px 20px;
            """
        )
        group_layout.addWidget(group_line)

        # Inner container for the individual cards
        results_container = QWidget()
        results_layout = QVBoxLayout(results_container)
        results_layout.setSpacing(6)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Create individual result labels first (to maintain existing variable names)
        self.total_unit_value_label = BodyLabel("0")
        self.total_diff_value_label = BodyLabel("0")
        self.per_unit_cost_value_label = BodyLabel("0.00")
        self.additional_amount_value_label = BodyLabel("0")

        # Create individual result cards with themed colors
        # Total Units Card (Blue)
        total_units_card = ResultCard(
            "Total Units",
            FluentIcon.TILES,
            "#4FC3F7",
            self.total_unit_value_label,
        )
        results_layout.addWidget(total_units_card)

        # Total Difference Card (Orange)
        total_diff_card = ResultCard(
            "Total Difference",
            FluentIcon.REMOVE,
            "#FFB74D",
            self.total_diff_value_label,
        )
        results_layout.addWidget(total_diff_card)

        # Per Unit Cost Card (Green)
        per_unit_cost_card = ResultCard(
            "Per Unit Cost",
            FluentIcon.SHOPPING_CART,
            "#81C784",
            self.per_unit_cost_value_label,
        )
        results_layout.addWidget(per_unit_cost_card)

        # Added Amount Card (Purple)
        added_amount_card = ResultCard(
            "Added Amount",
            FluentIcon.ADD,
            "#BA68C8",
            self.additional_amount_value_label,
        )
        results_layout.addWidget(added_amount_card)

        # Total Cost Card (Teal) - calculated value, no existing label
        self.total_cost_card = ResultCard(
            "Total Cost",
            FluentIcon.UP,
            "#26A69A",
        )
        results_layout.addWidget(self.total_cost_card)

        # Final Amount card (Blue accent) - include inside this group
        self.in_total_value_label = BodyLabel("0.00")
        self.final_amount_card = FinalAmountCard(self.in_total_value_label)
        results_layout.addWidget(self.final_amount_card)

        # Add stretch to push cards to top inside the container
        # No stretch so the group height hugs the content and doesn't expand vertically

        # Add inner container to the titled group
        group_layout.addWidget(results_container)

        # Do not lock height here; we will lock to content once after initial layout/show.
        return results_group

    def create_unified_calculator_card(self):
        """Create a unified card combining billing, reading pairs, additional amount, and results."""
        # ── Outer card ──────────────────────────────────────────────────
        card = QWidget()
        card.setObjectName("unified_calculator_card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFocusPolicy(Qt.NoFocus)
        card.setAttribute(Qt.WA_Hover, False)
        card.setMouseTracking(False)
        card.setStyleSheet("""
            #unified_calculator_card {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        self._billing_unified_group = card
        card.installEventFilter(self)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        # ── Title ───────────────────────────────────────────────────────
        title = TitleLabel("\U0001f4ca Billing & Calculation")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px; font-weight: 800; color: #0078D4;
            letter-spacing: 1px; margin: 8px 0px;
        """)
        card_layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet("color: #0078D4; background-color: #0078D4; border: none; height: 2px; margin: 4px 20px;")
        card_layout.addWidget(sep)

        # ── Two-column body ─────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(16)

        # Left column: inputs
        left = QWidget()
        left.setStyleSheet("background: transparent; border: none;")
        left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # -- Billing Period subsection --
        left_layout.addWidget(self._make_frosted_subsection(
            "Billing Period", self._build_billing_period_content()))

        # -- Reading Pairs subsection --
        left_layout.addWidget(self._make_frosted_subsection(
            "Reading Pairs", self._build_reading_pairs_content()))

        # -- Additional Amount subsection --
        left_layout.addWidget(self._make_frosted_subsection(
            "Additional Amount", self._build_additional_amount_content()))

        # Right column: results
        right = QWidget()
        right.setStyleSheet("background: transparent; border: none;")
        right.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        results_group = self.create_results_group()
        self.results_group_widget = results_group
        right_layout.addWidget(results_group, 0, Qt.AlignTop)
        right_layout.addStretch(1)

        body.addWidget(left, 3)
        body.addWidget(right, 2)
        card_layout.addLayout(body)

        # ── Calculate button ────────────────────────────────────────────
        self.main_calculate_button = PrimaryPushButton("Calculate")
        self.main_calculate_button.setIcon(FluentIcon.ACCEPT_MEDIUM.icon(color=QColor(255, 255, 255)))
        self.main_calculate_button.setIconSize(QSize(20, 20))
        self.main_calculate_button.clicked.connect(self.calculate_main)
        self.main_calculate_button.setFixedHeight(40)
        self.main_calculate_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_calculate_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0078D4, stop:1 #005a9e);
                border: 2px solid #0078D4; border-radius: 8px; font-weight: 600; font-size: 14px;
                qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center; margin: 0px;
            }
            PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1084d8, stop:1 #106ebe); border-color: #1084d8; }
            PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #005a9e, stop:1 #004578); border-color: #005a9e; }
        """)
        card_layout.addWidget(self.main_calculate_button)

        return card

    def _make_frosted_subsection(self, title_text, content_widget):
        """Wrap a content widget in a frosted glass subsection with a title."""
        outer = QWidget()
        outer.setStyleSheet("background: transparent; border: none;")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        inner = QWidget()
        inner.setAttribute(Qt.WA_StyledBackground, True)
        inner.setFocusPolicy(Qt.NoFocus)
        inner.setAttribute(Qt.WA_Hover, False)
        inner.setMouseTracking(False)
        inner.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.28);
            border-radius: 12px;
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 120))
        inner.setGraphicsEffect(shadow)

        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(16, 12, 16, 12)
        inner_layout.setSpacing(8)

        lbl = BodyLabel(title_text)
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078D4; margin: 4px 0px; background: transparent; border: none;")
        inner_layout.addWidget(lbl)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("color: #1084d8; background-color: #1084d8; border: none; height: 3px; margin: 2px 0px 6px 0px;")
        inner_layout.addWidget(line)

        inner_layout.addWidget(content_widget)
        outer_layout.addWidget(inner)
        return outer

    def _build_billing_period_content(self):
        """Build the billing period input content widget."""
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(w)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        month_label = BodyLabel("Month:")
        month_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
        self.month_combo = ComboBox()
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])

        year_label = BodyLabel("Year:")
        year_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
        self.year_spinbox = SpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self._apply_no_select_to_spinbox(self.year_spinbox)
        self.year_spinbox.setFocusPolicy(Qt.NoFocus)

        layout.addWidget(month_label)
        layout.addWidget(self.month_combo)
        layout.addSpacing(20)
        layout.addWidget(year_label)
        layout.addWidget(self.year_spinbox)
        layout.addStretch(1)
        return w

    def _build_reading_pairs_content(self):
        """Build the reading pairs content widget."""
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        pairs_scroll = ScrollArea()
        pairs_scroll.setWidgetResizable(True)
        pairs_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pairs_scroll.setMinimumHeight(110)
        pairs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pairs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        pairs_container = QWidget()
        pairs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pairs_layout = QVBoxLayout(pairs_container)
        self.pairs_layout.setSpacing(2)
        self.pairs_layout.setContentsMargins(4, 2, 4, 10)
        pairs_scroll.setWidget(pairs_container)
        layout.addWidget(pairs_scroll, 0, Qt.AlignTop)
        self.pairs_scroll = pairs_scroll

        self._pairs_fixed_gap = 12
        layout.addSpacing(self._pairs_fixed_gap)
        self._pairs_btn_top_gap = 14
        add_pair_button = AddPairButton("Add Reading Pair", lambda: self.add_reading_pair())
        button_holder = QWidget()
        bh_layout = QVBoxLayout(button_holder)
        bh_layout.setContentsMargins(0, self._pairs_btn_top_gap, 0, 0)
        bh_layout.setSpacing(0)
        bh_layout.addWidget(add_pair_button)
        layout.addWidget(button_holder)
        self._pairs_add_button = add_pair_button

        return w

    def _build_additional_amount_content(self):
        """Build the additional amount input content widget."""
        w = QWidget()
        w.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.additional_amount_input = CustomLineEdit()
        self.additional_amount_input.setObjectName("main_additional_amount_input")
        self.additional_amount_input.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))

        currency_label = CaptionLabel("TK")
        currency_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 12px; padding: 8px 4px; background: transparent; border: none;")

        layout.addWidget(self.additional_amount_input, 1)
        layout.addWidget(currency_label)
        return w

    def _create_load_data_container(self):
        """Container 1: Load Data — Month/Year selection, source, and load button."""
        container = QWidget()
        container.setObjectName("load_data_container")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setAutoFillBackground(True)
        container.setFocusPolicy(Qt.NoFocus)
        container.setAttribute(Qt.WA_Hover, False)
        container.setMouseTracking(False)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        container.setStyleSheet("""
            #load_data_container {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-left: 3px solid #3d3d3d;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Month
        load_month_label = BodyLabel("Month:")
        load_month_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.load_month_combo = ComboBox()
        self.load_month_combo.addItems([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])
        self.load_month_combo.setCurrentIndex(datetime.now().month - 1)
        self.load_month_combo.setMinimumWidth(140)
        self.load_month_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Year
        load_year_label = BodyLabel("Year:")
        load_year_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.load_year_spinbox = SpinBox()
        self.load_year_spinbox.setRange(2000, 2100)
        self.load_year_spinbox.setValue(datetime.now().year)
        self._apply_no_select_to_spinbox(self.load_year_spinbox)
        self.load_year_spinbox.setFocusPolicy(Qt.NoFocus)
        QTimer.singleShot(0, lambda: (self.load_year_spinbox.lineEdit() and self.load_year_spinbox.lineEdit().setFocusPolicy(Qt.NoFocus)))
        self.load_year_spinbox.setMinimumWidth(100)
        self.load_year_spinbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        try:
            le2 = self.load_year_spinbox.lineEdit() if hasattr(self.load_year_spinbox, 'lineEdit') else None
            if le2 is None:
                QTimer.singleShot(0, lambda: (
                    self.load_year_spinbox.lineEdit() and self.load_year_spinbox.lineEdit().setFont(self.load_year_spinbox.lineEdit().font().setBold(True))
                ))
            else:
                f2 = le2.font()
                f2.setBold(True)
                le2.setFont(f2)
        except Exception:
            pass

        layout.addWidget(load_month_label, 0)
        layout.addWidget(self.load_month_combo, 2)
        layout.addSpacing(12)
        layout.addWidget(load_year_label, 0)
        layout.addWidget(self.load_year_spinbox, 1)

        # Source dropdown button
        self.main_window.load_info_source_combo.setVisible(False)
        current_source = self.main_window.load_info_source_combo.currentText()
        if "Cloud" in current_source:
            initial_icon = FluentIcon.CLOUD
            initial_label = "Load from Cloud"
        else:
            initial_icon = FluentIcon.DOCUMENT
            initial_label = "Load from CSV"

        self.load_source_button = DropDownPushButton(initial_icon, initial_label)
        self.load_source_button.setFixedHeight(36)
        try:
            self.load_source_button.setIcon(initial_icon.icon(color=QColor(255, 255, 255)))
        except Exception:
            pass
        self.load_source_button.setIconSize(QSize(20, 20))
        self.load_source_button.setMinimumWidth(180)
        self.load_source_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        menu = RoundMenu(parent=self.load_source_button)
        def _set_source(text, icon, label):
            self.main_window.load_info_source_combo.setCurrentText(text)
            try:
                qicon = icon.icon(color=QColor(255, 255, 255)) if hasattr(icon, 'icon') else icon
            except Exception:
                qicon = icon
            self.load_source_button.setIcon(qicon)
            self.load_source_button.setText(label)
            self._update_source_button_color(label)
        menu.addAction(Action(FluentIcon.DOCUMENT, "Load from CSV", triggered=lambda: _set_source("Load from PC (CSV)", FluentIcon.DOCUMENT, "Load from CSV")))
        menu.addAction(Action(FluentIcon.CLOUD, "Load from Cloud", triggered=lambda: _set_source("Load from Cloud", FluentIcon.CLOUD, "Load from Cloud")))
        self.load_source_button.setMenu(menu)
        self._update_source_button_color(initial_label)

        layout.addSpacing(12)
        layout.addWidget(self.load_source_button, 2)

        # Load button
        load_button = PrimaryPushButton("Load")
        load_button.setIcon(FluentIcon.DOWNLOAD.icon(color=QColor(255, 255, 255)))
        load_button.setIconSize(QSize(20, 20))
        load_button.clicked.connect(self.load_info_to_inputs)
        load_button.setFixedHeight(36)
        load_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 6px;
                font-weight: 600;
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
            }
            PrimaryPushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            PrimaryPushButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
        """)
        load_button.setMinimumWidth(120)
        load_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addSpacing(12)
        layout.addWidget(load_button, 1)

        return container

    def _create_save_options_container(self):
        """Container 2: Save Options — PDF, CSV, and Cloud save buttons."""
        container = QWidget()
        container.setObjectName("save_options_container")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setAutoFillBackground(True)
        container.setFocusPolicy(Qt.NoFocus)
        container.setAttribute(Qt.WA_Hover, False)
        container.setMouseTracking(False)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        container.setStyleSheet("""
            #save_options_container {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Top hairline separator
        top_sep = QFrame()
        top_sep.setFrameShape(QFrame.HLine)
        top_sep.setFrameShadow(QFrame.Plain)
        top_sep.setStyleSheet("color: #3d3d3d; background-color: #3d3d3d; border: none; height: 1px;")
        layout.addWidget(top_sep)

        # Buttons row
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        buttons_row.setContentsMargins(0, 4, 0, 0)

        # Save PDF
        pdf_button = PrimaryPushButton("Save PDF")
        pdf_button.setIcon(FluentIcon.DOCUMENT.icon(color=QColor(255, 255, 255)))
        pdf_button.setIconSize(QSize(20, 20))
        pdf_button.setFixedHeight(40)
        pdf_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_button.clicked.connect(self.main_window.save_to_pdf)
        pdf_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d32f2f, stop:1 #b71c1c);
                border: 2px solid #d32f2f; border-radius: 8px; font-weight: 600; font-size: 14px;
                qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center;
            }
            PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f44336, stop:1 #d32f2f); border-color: #f44336; }
            PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b71c1c, stop:1 #8f1414); border-color: #b71c1c; }
        """)

        # Save CSV
        csv_button = PrimaryPushButton("Save CSV")
        csv_button.setIcon(FluentIcon.SAVE.icon(color=QColor(255, 255, 255)))
        csv_button.setIconSize(QSize(20, 20))
        csv_button.setFixedHeight(40)
        csv_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        csv_button.clicked.connect(self.main_window.save_calculation_to_csv)
        csv_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #388e3c, stop:1 #2e7d32);
                border: 2px solid #388e3c; border-radius: 8px; font-weight: 600; font-size: 14px;
                qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center;
            }
            PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4caf50, stop:1 #388e3c); border-color: #4caf50; }
            PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2e7d32, stop:1 #1b5e20); border-color: #2e7d32; }
        """)

        # Save Cloud
        cloud_button = PrimaryPushButton("Save Cloud")
        cloud_button.setIcon(FluentIcon.CLOUD.icon(color=QColor(255, 255, 255)))
        cloud_button.setIconSize(QSize(20, 20))
        cloud_button.setFixedHeight(40)
        cloud_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cloud_button.clicked.connect(self.main_window.save_calculation_to_supabase)
        cloud_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7b1fa2, stop:1 #6a1b9a);
                border: 2px solid #7b1fa2; border-radius: 8px; font-weight: 600; font-size: 14px;
                qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center;
            }
            PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9c27b0, stop:1 #7b1fa2); border-color: #9c27b0; }
            PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a1b9a, stop:1 #4a148c); border-color: #6a1b9a; }
        """)

        buttons_row.addWidget(pdf_button, 1)
        buttons_row.addWidget(csv_button, 1)
        buttons_row.addWidget(cloud_button, 1)
        self._save_buttons_row = buttons_row
        layout.addLayout(buttons_row)

        return container

    def _create_add_next_month_container(self):
        """Container 3: Add Next Month — single centered button."""
        container = QWidget()
        container.setObjectName("add_next_month_container")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setAutoFillBackground(True)
        container.setFocusPolicy(Qt.NoFocus)
        container.setAttribute(Qt.WA_Hover, False)
        container.setMouseTracking(False)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        container.setStyleSheet("""
            #add_next_month_container {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Dotted separator
        dotted_sep = QFrame()
        dotted_sep.setFrameShape(QFrame.HLine)
        dotted_sep.setFrameShadow(QFrame.Plain)
        dotted_sep.setStyleSheet("color: #4a4a4a; background-color: #4a4a4a; border: none; height: 1px;")
        layout.addWidget(dotted_sep)

        # Centered button
        add_next_month_button = PrimaryPushButton("Add Next Month")
        add_next_month_button.setIcon(FluentIcon.ADD.icon(color=QColor(255, 255, 255)))
        add_next_month_button.setIconSize(QSize(20, 20))
        add_next_month_button.clicked.connect(self.add_month_action)
        add_next_month_button.setFixedHeight(36)
        add_next_month_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #FF8C00;
                border: 1px solid #FF8C00;
                border-radius: 6px;
                font-weight: 600;
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
            }
            PrimaryPushButton:hover {
                background-color: #FF7F00;
                border-color: #FF7F00;
            }
            PrimaryPushButton:pressed {
                background-color: #FF6600;
                border-color: #FF6600;
            }
        """)
        add_next_month_button.setMinimumWidth(240)
        add_next_month_button.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(0)
        button_row.addStretch(1)
        button_row.addWidget(add_next_month_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        return container

        
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def calculate_main(self):
        try:
            def _to_int_safe(txt: str) -> int:
                """Convert text to int, accepting float strings (e.g. '123.0').

                Returns 0 for empty strings and raises ValueError for truly invalid
                formats so that the outer except can handle the error display."""
                if not txt or not txt.strip():
                    return 0
                try:
                    return int(txt)
                except ValueError:
                    try:
                        return int(float(txt))  # Handles "123.0"
                    except ValueError:
                        raise

            meter_readings = [_to_int_safe(meter_edit.text()) for meter_edit in self.meter_entries]
            diff_readings = [_to_int_safe(diff_edit.text()) for diff_edit in self.diff_entries]
            additional_amount = self.get_additional_amount()

            total_unit = sum(meter_readings)
            total_diff = sum(diff_readings)
            per_unit_cost = (total_unit / total_diff) if total_diff != 0 else 0.0 # Ensure float division
            total_cost = total_unit  # Total cost before additional amount
            in_total = total_unit + additional_amount

            self.total_unit_value_label.setText(f"{int(total_unit)}")
            self.total_diff_value_label.setText(f"{int(total_diff)}")
            self.per_unit_cost_value_label.setText(f"{per_unit_cost:.2f} TK")
            self.additional_amount_value_label.setText(f"{int(additional_amount)} TK")
            self.total_cost_card.update_value(f"{int(total_cost)} TK")
            self.in_total_value_label.setText(f"{int(in_total)} TK")

            # Enable room calculation button
            if self.calculate_rooms_button:
                self.calculate_rooms_button.setEnabled(True)
                self.calculate_rooms_button.setToolTip("")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for all readings.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}\n{traceback.format_exc()}")

    # ── Room Calculation Methods ─────────────────────────────────────────

    def _create_rooms_section(self):
        """Create the Room Calculations section with spinbox, room cards grid, and calculate button."""
        section = QWidget()
        section.setObjectName("rooms_section")
        section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        section.setStyleSheet("""
            #rooms_section {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        section.setAttribute(Qt.WA_StyledBackground, True)
        section.setAutoFillBackground(True)
        section.setFocusPolicy(Qt.NoFocus)
        section.setAttribute(Qt.WA_Hover, False)
        section.setMouseTracking(False)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header with title and spinbox
        header = QWidget()
        header.setStyleSheet("background: transparent; border: none;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        title = TitleLabel("\U0001f3e0 Room Calculations")
        title.setStyleSheet("""
            font-size: 26px; font-weight: 800; color: #0078D4;
            letter-spacing: 0.5px; background: transparent; border: none;
        """)

        rooms_label = BodyLabel("Number of Rooms:")
        rooms_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")

        self.num_rooms_spinbox = SpinBox()
        self.num_rooms_spinbox.setRange(1, 20)
        self.num_rooms_spinbox.setValue(11)
        self.num_rooms_spinbox.setFocusPolicy(Qt.NoFocus)
        self.num_rooms_spinbox.valueChanged.connect(self.update_room_inputs)
        self._apply_no_select_to_spinbox(self.num_rooms_spinbox)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(rooms_label)
        header_layout.addWidget(self.num_rooms_spinbox)
        layout.addWidget(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet("color: #0078D4; background-color: #0078D4; border: none; height: 2px; margin: 4px 0px;")
        layout.addWidget(sep)

        # Room cards container (FlowLayout expands naturally, outer scroll handles scrolling)
        rooms_card_container = QWidget()
        rooms_card_container.setStyleSheet("background: transparent; border: none;")
        rooms_card_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.rooms_scroll_layout = FlowLayout(rooms_card_container)
        self.rooms_scroll_layout.setSpacing(8)
        layout.addWidget(rooms_card_container)

        # Calculate Room Bills button
        self.calculate_rooms_button = PrimaryPushButton("Calculate Room Bills")
        self.calculate_rooms_button.clicked.connect(self.calculate_rooms)
        self.calculate_rooms_button.setIcon(FluentIcon.ACCEPT_MEDIUM.icon(color=QColor(255, 255, 255)))
        self.calculate_rooms_button.setIconSize(QSize(20, 20))
        self.calculate_rooms_button.setFixedHeight(40)
        self.calculate_rooms_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calculate_rooms_button.setEnabled(False)
        self.calculate_rooms_button.setToolTip("Calculate meter readings first")
        self.calculate_rooms_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0078D4, stop:1 #005a9e);
                border: 2px solid #0078D4; border-radius: 8px; font-weight: 600; font-size: 14px;
                qproperty-iconSize: 20px 20px; padding: 8px 16px 8px 36px; text-align: center; margin: 0px;
            }
            PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1084d8, stop:1 #106ebe); border-color: #1084d8; }
            PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #005a9e, stop:1 #004578); border-color: #005a9e; }
            PrimaryPushButton:disabled { background: #555; border-color: #444; color: #999; }
        """)
        layout.addWidget(self.calculate_rooms_button)

        # Initial room cards
        self.update_room_inputs()

        return section

    def update_room_inputs(self):
        """Create or refresh room card widgets based on num_rooms_spinbox value."""
        from src.core.utils import _clear_layout
        _clear_layout(self.rooms_scroll_layout)
        self.room_entries = []

        num_rooms = self.num_rooms_spinbox.value()
        numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))

        for i in range(num_rooms):
            room_group = CardWidget()
            room_group.setObjectName(f"room_{i}_card")
            room_group.setStyleSheet("""
                CardWidget { background-color: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 10px; }
                CardWidget:hover { background-color: #2b2b2b; border: 1px solid #3d3d3d; }
            """)
            outer_layout = QVBoxLayout(room_group)
            outer_layout.setSpacing(10)
            outer_layout.setContentsMargins(16, 12, 16, 16)

            title = TitleLabel(f"Room {i+1}")
            title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0078D4; letter-spacing: 0.5px; margin: 0px; background: transparent;")
            outer_layout.addWidget(title)

            header_line = QFrame()
            header_line.setFrameShape(QFrame.HLine)
            header_line.setFrameShadow(QFrame.Plain)
            header_line.setStyleSheet("color: #0078D4; background-color: #0078D4; border: none; height: 2px; margin: 2px 0px 4px 0px;")
            outer_layout.addWidget(header_line)

            room_group.setMinimumWidth(280)
            room_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            present_entry = CustomLineEdit()
            present_entry.setObjectName(f"room_{i}_present")
            present_entry.setPlaceholderText("0")
            present_entry.setValidator(numeric_validator)

            previous_entry = CustomLineEdit()
            previous_entry.setObjectName(f"room_{i}_previous")
            previous_entry.setPlaceholderText("0")
            previous_entry.setValidator(numeric_validator)

            real_unit_label = CaptionLabel("N/A")
            real_unit_label.setStyleSheet("color:#4FC3F7; font-weight:bold; background:transparent;")
            real_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            unit_bill_label = CaptionLabel("N/A")
            unit_bill_label.setStyleSheet("color:#FFB74D; font-weight:bold; background:transparent;")
            unit_bill_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            gas_bill_entry = CustomLineEdit()
            gas_bill_entry.setObjectName(f"room_{i}_gas_bill")
            gas_bill_entry.setValidator(numeric_validator)

            water_bill_entry = CustomLineEdit()
            water_bill_entry.setObjectName(f"room_{i}_water_bill")
            water_bill_entry.setValidator(numeric_validator)

            house_rent_entry = CustomLineEdit()
            house_rent_entry.setObjectName(f"room_{i}_house_rent")
            house_rent_entry.setValidator(numeric_validator)

            grand_total_label = StrongBodyLabel("N/A")
            grand_total_label.setStyleSheet("color:#81C784; font-weight:bold; background:transparent;")
            grand_total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Units row
            units_row = QWidget()
            units_row.setStyleSheet("background: transparent; border: none;")
            units_row_layout = QGridLayout(units_row)
            units_row_layout.setContentsMargins(0, 0, 0, 0)
            units_row_layout.setSpacing(8)

            pl = BodyLabel("Present Unit")
            pl.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
            units_row_layout.addWidget(pl, 0, 0)
            units_row_layout.addWidget(present_entry, 1, 0)

            prl = BodyLabel("Previous Unit")
            prl.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
            units_row_layout.addWidget(prl, 0, 1)
            units_row_layout.addWidget(previous_entry, 1, 1)
            outer_layout.addWidget(units_row)

            # Gas, Water, Rent
            for label_text, entry in [("Gas Bill", gas_bill_entry), ("Water Bill", water_bill_entry), ("House Rent", house_rent_entry)]:
                w = QWidget()
                w.setStyleSheet("background: transparent; border: none;")
                wl = QVBoxLayout(w)
                wl.setContentsMargins(0, 0, 0, 0)
                wl.setSpacing(4)
                lbl = BodyLabel(label_text)
                lbl.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
                wl.addWidget(lbl)
                wl.addWidget(entry)
                outer_layout.addWidget(w)

            # Frosted result rows
            for result_label, result_title, color in [
                (real_unit_label, "Real Unit", "#4FC3F7"),
                (unit_bill_label, "Unit Bill", "#FFB74D"),
                (grand_total_label, "Grand Total", "#81C784"),
            ]:
                r, g, b = _hex_to_rgb(color)
                container = QWidget()
                container.setAttribute(Qt.WA_StyledBackground, True)
                container.setAutoFillBackground(True)
                container.setStyleSheet(f"background-color: rgba({r},{g},{b},0.14); border: 1px solid rgba({r},{g},{b},0.45); border-radius: 6px;")
                cl = QHBoxLayout(container)
                cl.setContentsMargins(12, 8, 12, 8)
                cl.setSpacing(8)
                t = BodyLabel(result_title)
                t.setStyleSheet(f"color:{color}; font-weight:bold; background:transparent; border:none;")
                cl.addWidget(t)
                cl.addStretch()
                result_label.setStyleSheet(f"color:{color}; font-weight:bold; background:transparent; border:none; font-size:14px;")
                result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                cl.addWidget(result_label)
                outer_layout.addWidget(container)

            self.room_entries.append({
                'present_entry': present_entry,
                'previous_entry': previous_entry,
                'gas_bill_entry': gas_bill_entry,
                'water_bill_entry': water_bill_entry,
                'house_rent_entry': house_rent_entry,
                'real_unit_label': real_unit_label,
                'unit_bill_label': unit_bill_label,
                'grand_total_label': grand_total_label,
                'room_group': room_group,
            })

            self.rooms_scroll_layout.addWidget(room_group)

        self.setup_navigation_rooms_tab()

    def calculate_rooms(self):
        """Calculate room bills using the per-unit cost from meter calculation."""
        try:
            per_unit_cost_text = self.per_unit_cost_value_label.text().strip()
            value_to_process = ""
            if ':' in per_unit_cost_text:
                parts = per_unit_cost_text.split(':', 1)
                if len(parts) > 1:
                    value_to_process = parts[1].strip()
            else:
                value_to_process = per_unit_cost_text

            if not value_to_process:
                raise ValueError(f"Per unit cost value is empty. Original: '{per_unit_cost_text}'")

            cleaned = value_to_process.lower().replace("tk", "").strip()
            if not cleaned:
                raise ValueError(f"Per unit cost value is non-numeric after cleaning.")

            per_unit_cost = float(cleaned)

            def _to_int_safe(txt):
                if not txt or not txt.strip():
                    return 0
                try:
                    return int(txt)
                except ValueError:
                    return int(float(txt))

            for i, room in enumerate(self.room_entries):
                present_text = room['present_entry'].text().strip()
                previous_text = room['previous_entry'].text().strip()

                # Skip empty rooms
                if not present_text and not previous_text:
                    continue

                try:
                    present_unit = _to_int_safe(present_text)
                    previous_unit = _to_int_safe(previous_text)
                except ValueError:
                    raise ValueError(f"Non-numeric input in Room {i+1}.")

                if present_unit < 0 or previous_unit < 0:
                    raise ValueError(f"Negative readings not allowed in Room {i+1}.")
                if present_unit < previous_unit:
                    raise ValueError(f"Present reading cannot be less than previous in Room {i+1}.")

                real_unit = present_unit - previous_unit
                unit_bill = round(real_unit * per_unit_cost, 2)

                def _to_amount(txt, name):
                    if not txt:
                        return 0.0
                    v = float(txt)
                    if v < 0:
                        raise ValueError(f"{name} cannot be negative in Room {i+1}: {v}")
                    return v

                gas = _to_amount(room['gas_bill_entry'].text().strip(), "Gas Bill")
                water = _to_amount(room['water_bill_entry'].text().strip(), "Water Bill")
                rent = _to_amount(room['house_rent_entry'].text().strip(), "House Rent")

                grand_total = unit_bill + gas + water + rent

                room['real_unit_label'].setText(f"{real_unit}")
                room['unit_bill_label'].setText(f"{int(unit_bill + 0.5)} TK")
                room['grand_total_label'].setText(f"{int(grand_total + 0.5)} TK")

        except ValueError as ve:
            QMessageBox.warning(self, "Calculation Error", f"Error in room calculation: {ve}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}\n{traceback.format_exc()}")

    def load_room_data_from_csv_row(self, row, room_index):
        """Load room data from a CSV row into the specified room card."""
        if room_index >= len(self.room_entries):
            return
        room = self.room_entries[room_index]

        def get_csv_value(row_dict, key, default):
            for k, v in row_dict.items():
                if k.strip().lower() == key.strip().lower():
                    s = v.strip() if isinstance(v, str) else ""
                    if s.upper() == "N/A":
                        s = "0"
                    return s if s else default
            return default

        try:
            room['present_entry'].setText(get_csv_value(row, "Present Unit", "0"))
            room['previous_entry'].setText(get_csv_value(row, "Previous Unit", "0"))
            room['gas_bill_entry'].setText(get_csv_value(row, "Gas Bill", "0.00"))
            room['water_bill_entry'].setText(get_csv_value(row, "Water Bill", "0.00"))
            room['house_rent_entry'].setText(get_csv_value(row, "House Rent", "0.00"))
        except Exception as e:
            QMessageBox.critical(self, "Load Room Data Error", f"Failed to load room data for room {room_index+1}: {e}")

    def load_room_data_from_supabase_rows(self, room_records, auto_calculate=True):
        """Load room data from Supabase records into the UI."""
        if not room_records:
            self.num_rooms_spinbox.setValue(1)
            self.clear_room_inputs()
            return

        self.num_rooms_spinbox.setValue(len(room_records))

        def _to_number_str_safe(val):
            if val == '' or val is None:
                return ''
            try:
                if isinstance(val, int):
                    return str(val)
                elif isinstance(val, float):
                    return str(int(val)) if val.is_integer() else f"{val:g}"
                elif isinstance(val, str):
                    if val.isdigit():
                        return val
                    num = float(val)
                    return str(int(num)) if num.is_integer() else f"{num:g}"
                else:
                    num = float(val)
                    return str(int(num)) if num.is_integer() else f"{num:g}"
            except (ValueError, TypeError):
                return str(val)

        for i, record in enumerate(room_records):
            if i >= len(self.room_entries):
                break

            data = record.get("room_data", {})
            room_id = record.get("id")
            room = self.room_entries[i]

            new_title = data.get('room_name', f"Room {i+1}")
            title_label = room['room_group'].findChild(TitleLabel)
            if title_label:
                title_label.setText(new_title)

            room['present_entry'].setText(_to_number_str_safe(data.get('present_unit', '')))
            room['previous_entry'].setText(_to_number_str_safe(data.get('previous_unit', '')))
            room['gas_bill_entry'].setText(_to_number_str_safe(data.get('gas_bill', '')))
            room['water_bill_entry'].setText(_to_number_str_safe(data.get('water_bill', '')))
            room['house_rent_entry'].setText(_to_number_str_safe(data.get('house_rent', '')))
            room['supabase_id'] = room_id

        if auto_calculate:
            self.calculate_rooms()

    def clear_room_inputs(self):
        """Clear all room input fields and result labels."""
        for i, room in enumerate(self.room_entries):
            room['present_entry'].clear()
            room['previous_entry'].clear()
            room['gas_bill_entry'].clear()
            room['water_bill_entry'].clear()
            room['house_rent_entry'].clear()
            room['real_unit_label'].setText("N/A")
            room['unit_bill_label'].setText("N/A")
            room['grand_total_label'].setText("N/A")
            title_label = room['room_group'].findChild(TitleLabel)
            if title_label:
                title_label.setText(f"Room {i+1}")
            if 'supabase_id' in room:
                del room['supabase_id']

    def get_room_data_for_supabase(self):
        """Collect all room data for Supabase storage."""
        room_data_list = []
        errors = []
        for i, room in enumerate(self.room_entries):
            try:
                title_label = room['room_group'].findChild(TitleLabel)
                room_name = title_label.text() if title_label else f"Room {i+1}"

                present = int(room['present_entry'].text() or "0")
                previous = int(room['previous_entry'].text() or "0")
                gas = float(room['gas_bill_entry'].text() or "0.0")
                water = float(room['water_bill_entry'].text() or "0.0")
                rent = float(room['house_rent_entry'].text() or "0.0")

                real_text = room['real_unit_label'].text()
                bill_text = room['unit_bill_label'].text()
                total_text = room['grand_total_label'].text()

                real_unit = int(real_text) if real_text.isdigit() else 0
                unit_bill = float(bill_text.replace(" TK", "").strip()) if bill_text and bill_text not in ["N/A", "Incomplete"] else 0.0
                grand_total = float(total_text.replace(" TK", "").strip()) if total_text and total_text not in ["N/A", "Incomplete"] else 0.0

                room_data_list.append({
                    "room_name": room_name,
                    "present_unit": present,
                    "previous_unit": previous,
                    "real_unit": real_unit,
                    "unit_bill": unit_bill,
                    "gas_bill": gas,
                    "water_bill": water,
                    "house_rent": rent,
                    "grand_total": grand_total,
                })
            except Exception as e:
                errors.append(f"Room {i+1}: {e}")

        if errors:
            QMessageBox.warning(self, "Partial Data Collected", "Some rooms had errors:\n\n" + "\n".join(errors))
        return room_data_list

    def get_all_room_bill_totals(self):
        """Calculate totals across all rooms."""
        totals = {"total_house_rent": 0.0, "total_water_bill": 0.0, "total_gas_bill": 0.0, "total_room_unit_bill": 0.0}
        for room in self.room_entries:
            try:
                totals["total_house_rent"] += float(room['house_rent_entry'].text() or '0.0')
                totals["total_water_bill"] += float(room['water_bill_entry'].text() or '0.0')
                totals["total_gas_bill"] += float(room['gas_bill_entry'].text() or '0.0')
                bill_text = room['unit_bill_label'].text()
                if bill_text and bill_text not in ["N/A", "Incomplete"]:
                    totals["total_room_unit_bill"] += float(bill_text.replace(" TK", "").strip())
            except (ValueError, Exception):
                pass
        return totals

    def setup_navigation_rooms_tab(self):
        """Configure focus navigation for room input fields."""
        nav_sequence = []
        for room in self.room_entries:
            nav_sequence.extend([
                room['present_entry'],
                room['previous_entry'],
                room['gas_bill_entry'],
                room['water_bill_entry'],
                room['house_rent_entry'],
            ])

        if not nav_sequence:
            return

        length = len(nav_sequence)
        for idx, widget in enumerate(nav_sequence):
            next_idx = (idx + 1) % length
            prev_idx = (idx - 1) % length
            widget.next_widget_on_enter = nav_sequence[next_idx]
            widget.down_widget = nav_sequence[next_idx]
            widget.up_widget = nav_sequence[prev_idx]

    def _update_source_button_color(self, source_text):
        """Update button color based on selected data source.
        
        Args:
            source_text: The label text of the selected source ("Load from Cloud" or "Load from CSV")
        """
        if "Cloud" in source_text:
            # Apply purple styling for Cloud
            self.load_source_button.setStyleSheet("""
                DropDownPushButton {
                    color: white;
                    background-color: #6C5CE7;
                    border: 1px solid #6C5CE7;
                    border-radius: 6px;
                    font-weight: 600;
                    qproperty-iconSize: 20px 20px;
                    padding: 8px 40px 8px 36px;
                }
                DropDownPushButton:hover {
                    background-color: #5A4FCF;
                    border-color: #5A4FCF;
                }
                DropDownPushButton:pressed {
                    background-color: #4834D4;
                    border-color: #4834D4;
                }
                DropDownPushButton::menu-indicator {
                    subcontrol-position: right center;
                    subcontrol-origin: padding;
                    right: 8px;
                }
            """)
        else:  # CSV
            # Apply green styling for CSV
            self.load_source_button.setStyleSheet("""
                DropDownPushButton {
                    color: white;
                    background-color: #2e7d32;
                    border: 1px solid #2e7d32;
                    border-radius: 6px;
                    font-weight: 600;
                    qproperty-iconSize: 20px 20px;
                    padding: 8px 40px 8px 36px;
                }
                DropDownPushButton:hover {
                    background-color: #43a047;
                    border-color: #43a047;
                }
                DropDownPushButton:pressed {
                    background-color: #1b5e20;
                    border-color: #1b5e20;
                }
                DropDownPushButton::menu-indicator {
                    subcontrol-position: right center;
                    subcontrol-origin: padding;
                    right: 8px;
                }
            """)

    def sync_source_button_display(self):
        """Sync the dropdown button display with the combo box selection."""
        current_source = self.main_window.load_info_source_combo.currentText()
        if "Cloud" in current_source:
            self.load_source_button.setIcon(FluentIcon.CLOUD.icon(color=QColor(255, 255, 255)))
            self.load_source_button.setText("Load from Cloud")
            self._update_source_button_color("Load from Cloud")
        else:
            self.load_source_button.setIcon(FluentIcon.DOCUMENT.icon(color=QColor(255, 255, 255)))
            self.load_source_button.setText("Load from CSV")
            self._update_source_button_color("Load from CSV")

    def load_info_to_inputs(self):
        source = self.main_window.load_info_source_combo.currentText()
        selected_month = self.load_month_combo.currentText()
        selected_year = self.load_year_spinbox.value()

        if source == "Load from PC (CSV)":
            self.load_info_to_inputs_from_csv(selected_month, selected_year)
        elif source == "Load from Cloud":
            if self.main_window.supabase_manager.is_client_initialized() and self.main_window.check_internet_connectivity():
                self.load_info_to_inputs_from_supabase(selected_month, selected_year)
            elif not self.main_window.supabase_manager.is_client_initialized():
                QMessageBox.warning(self, "Supabase Not Configured", "Supabase is not configured. Please go to the 'Supabase Config' tab.")
            else: # No internet
                 QMessageBox.warning(self, "Network Error", 
                                  "No internet connection detected. Please check your network and try again.")
        else:
            QMessageBox.warning(self, "Unknown Source", "Please select a valid source to load data from.")

    def _get_csv_value(self, row_dict, key_name, default_if_missing_or_empty):
        """Helper to safely get a value from a CSV row, case-insensitively."""
        for k_original, v_original in row_dict.items():
            if k_original.strip().lower() == key_name.strip().lower():
                stripped_v = v_original.strip() if isinstance(v_original, str) else ""
                # Replace "N/A" with "0"
                if stripped_v.upper() == "N/A":
                    stripped_v = "0"
                return stripped_v if stripped_v else default_if_missing_or_empty
        return default_if_missing_or_empty

    def load_info_to_inputs_from_csv(self, selected_month, selected_year):
        filename = "meter_calculation_history.csv"
        selected_month_year_str_ui = f"{selected_month} {selected_year}"
        
        if not os.path.exists(filename):
            QMessageBox.warning(self, "File Not Found", f"{filename} does not exist.")
            return

        try:
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                all_rows = list(reader) # Read all rows into memory
                
                main_data_row = None
                room_data_rows = []

                # Find the main data row first
                for i, row in enumerate(all_rows):
                    csv_month_year_str = self._get_csv_value(row, "Month", "")
                    if csv_month_year_str.strip().lower() == selected_month_year_str_ui.lower():
                        main_data_row = row
                        # If this row also contains room data (which it should for the first room), add it
                        if self._get_csv_value(row, "Room Name", ""): # Check if room data exists in this row
                            room_data_rows.append(row)
                        
                        # Now, collect subsequent room-only rows
                        for j in range(i + 1, len(all_rows)):
                            next_row = all_rows[j]
                            next_month_val = self._get_csv_value(next_row, "Month", "")
                            if not next_month_val.strip(): # If Month is empty, it's a room-only row
                                room_data_rows.append(next_row)
                            else: # Found a new main entry, stop collecting room rows
                                break
                        break # Found main data and collected all associated rooms, exit outer loop

                if not main_data_row:
                    QMessageBox.warning(self, "Data Not Found", f"No data found for {selected_month_year_str_ui} in {filename}.")
                    return
                
                # Load main tab data
                self.month_combo.setCurrentText(selected_month)
                self.year_spinbox.setValue(selected_year)
                
                meter_values_csv = [self._get_csv_value(main_data_row, f"Meter-{i+1}", "0") for i in range(10)]
                diff_values_csv = [self._get_csv_value(main_data_row, f"Diff-{i+1}", "0") for i in range(10)]
                
                # Filter out trailing "0"s to set spinbox counts correctly
                num_meters = len(meter_values_csv)
                while num_meters > 0 and meter_values_csv[num_meters-1] == "0":
                    num_meters -=1
                num_meters = max(1, num_meters) # At least 1

                num_diffs = len(diff_values_csv)
                while num_diffs > 0 and diff_values_csv[num_diffs-1] == "0":
                    num_diffs -=1
                num_diffs = max(1, num_diffs)

                # Determine how many pairs we need
                num_pairs_needed = max(num_meters, num_diffs)
                
                # Ensure we have enough reading pairs
                while len(self.reading_pairs) < num_pairs_needed:
                    self.add_reading_pair()
                
                # Remove excess pairs if we have too many
                while len(self.reading_pairs) > num_pairs_needed:
                    if self.reading_pairs:
                        self.remove_reading_pair(self.reading_pairs[-1])

                # Load meter values into the pairs
                for i, val_str in enumerate(meter_values_csv[:num_meters]):
                    if i < len(self.reading_pairs):
                        # Normalize numeric values so that "123.0" → "123" while preserving
                        # any truly non-integer strings (unlikely given validators).
                        display_val = str(val_str)
                        try:
                            num_val = float(val_str)
                            # If the float is effectively an int (e.g. 123.0) drop the decimal part
                            if num_val.is_integer():
                                display_val = str(int(num_val))
                        except (ValueError, TypeError):
                            # Leave display_val as-is if it is not a plain number
                            pass
                        self.reading_pairs[i].set_meter_value(display_val)
                
                # Load diff values into the pairs
                for i, val_str in enumerate(diff_values_csv[:num_diffs]):
                    if i < len(self.reading_pairs):
                        display_val = str(val_str)
                        try:
                            num_val = float(val_str)
                            if num_val.is_integer():
                                display_val = str(int(num_val))
                        except (ValueError, TypeError):
                            pass
                        self.reading_pairs[i].set_diff_value(display_val)
                    
                self.additional_amount_input.setText(self._get_csv_value(main_data_row, "Added Amount", "0"))

                # Load room tab data
                if room_data_rows:
                    self.num_rooms_spinbox.setValue(len(room_data_rows))
                    # This will trigger update_room_inputs in RoomsTab, creating the necessary widgets

                    for i, room_row in enumerate(room_data_rows):
                        if hasattr(self, 'load_room_data_from_csv_row'):
                            self.load_room_data_from_csv_row(room_row, i)
                        else:
                            print("Warning: rooms_tab_instance does not have load_room_data_from_csv_row method.")
                    
                    # After loading all room data, trigger calculation for rooms
                    self.calculate_rooms()
                else:
                    # If no room data found, ensure rooms tab is reset or has default number of rooms
                    self.num_rooms_spinbox.setValue(1) # Or a sensible default
                    self.calculate_rooms() # Recalculate with default rooms

                QMessageBox.information(self, "Load Successful", f"Data for {selected_month_year_str_ui} loaded into input fields from CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load data from CSV: {e}\n{traceback.format_exc()}")

    def load_info_to_inputs_from_supabase(self, selected_month, selected_year):
        if not self.main_window.supabase_manager.is_client_initialized():
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized.")
            return

        try:
            # Fetch main calculation data
            main_calc_record = self.main_window.supabase_manager.get_main_calculation_by_month_year(
                month=selected_month, 
                year=selected_year
            )

            if not main_calc_record:
                QMessageBox.warning(self, "Data Not Found", f"No data found for {selected_month} {selected_year} in the cloud.")
                return

            main_data = main_calc_record.get("main_data", {})
            if isinstance(main_data, str):
                try:
                    main_data = json.loads(main_data)
                except json.JSONDecodeError:
                    main_data = {}

            # Load main tab data
            self.month_combo.setCurrentText(selected_month)
            self.year_spinbox.setValue(selected_year)
            
            meter_values = main_data.get("meter_readings", [])
            diff_values = main_data.get("diff_readings", [])
            
            # Handle both dictionary and list formats
            if isinstance(meter_values, dict):
                # Convert dictionary to list (sorted by key to maintain order)
                meter_list = [meter_values.get(f'meter_{i+1}', 0) for i in range(len(meter_values))]
                meter_values = meter_list
                
            if isinstance(diff_values, dict):
                # Convert dictionary to list (sorted by key to maintain order)
                diff_list = [diff_values.get(f'diff_{i+1}', 0) for i in range(len(diff_values))]
                diff_values = diff_list
            
            num_meters = len(meter_values)
            num_diffs = len(diff_values)
            
            # Determine how many pairs we need
            num_pairs_needed = max(num_meters, num_diffs)
            
            # Ensure we have enough reading pairs
            while len(self.reading_pairs) < num_pairs_needed:
                self.add_reading_pair()
            
            # Remove excess pairs if we have too many
            while len(self.reading_pairs) > num_pairs_needed:
                if self.reading_pairs:
                    self.remove_reading_pair(self.reading_pairs[-1])
            
            # Load meter values into the pairs
            for i, val in enumerate(meter_values):
                if i < len(self.reading_pairs):
                    # Normalize numeric values so that "123.0" → "123" while preserving
                    # any truly non-integer strings (unlikely given validators).
                    display_val = str(val)
                    try:
                        num_val = float(val)
                        # If the float is effectively an int (e.g. 123.0) drop the decimal part
                        if num_val.is_integer():
                            display_val = str(int(num_val))
                    except (ValueError, TypeError):
                        # Leave display_val as-is if it is not a plain number
                        pass
                    self.reading_pairs[i].set_meter_value(display_val)
            
            # Load diff values into the pairs
            for i, val in enumerate(diff_values):
                if i < len(self.reading_pairs):
                    display_val = str(val)
                    try:
                        num_val = float(val)
                        if num_val.is_integer():
                            display_val = str(int(num_val))
                    except (ValueError, TypeError):
                        pass
                    self.reading_pairs[i].set_diff_value(display_val)
                
            # Support both legacy 'added_amount' and new 'additional_amount' keys
            add_amt = main_data.get("additional_amount", main_data.get("added_amount", "0"))
            self.additional_amount_input.setText(str(add_amt))

            # Fetch and load room data
            main_calc_id = main_calc_record.get("id")
            if main_calc_id:
                room_records = self.main_window.supabase_manager.get_room_calculations(main_calc_id)
                if room_records:
                    # RoomsTab already provides a helper that takes the full list.
                    if hasattr(self, 'load_room_data_from_supabase_rows'):
                        self.load_room_data_from_supabase_rows(room_records)
                    else:
                        # Fallback: minimal per-record population to avoid data loss
                        self.num_rooms_spinbox.setValue(len(room_records))
                        for i, room_rec in enumerate(room_records):
                            room_data = room_rec.get("room_data", {})
                            if isinstance(room_data, str):
                                try:
                                    room_data = json.loads(room_data)
                                except json.JSONDecodeError:
                                    room_data = {}
                            # Directly call setter fields if loader helper missing
                            if i < len(self.room_entries):
                                re = self.room_entries[i]
                                re['present_entry'].setText(str(room_data.get('present_unit', '')))
                                re['previous_entry'].setText(str(room_data.get('previous_unit', '')))
                                re['gas_bill_entry'].setText(str(room_data.get('gas_bill', '')))
                                re['water_bill_entry'].setText(str(room_data.get('water_bill', '')))
                                re['house_rent_entry'].setText(str(room_data.get('house_rent', '')))
                    # After populating, ensure calculations refresh
                    self.calculate_rooms()

            self.calculate_main() # Recalculate results based on loaded data

            # Recalculate room bills now that per-unit cost is up-to-date
            if hasattr(self, 'calculate_rooms'):
                try:
                    self.calculate_rooms()
                except Exception as calc_err:
                    # Log but don't block main load flow; user will see message from RoomsTab
                    print(f"Warning: rooms_tab_instance.calculate_rooms raised: {calc_err}")

            QMessageBox.information(self, "Load Successful", f"Data for {selected_month} {selected_year} loaded from the cloud.")

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load data from Cloud: {e}\n{traceback.format_exc()}")

    def add_month_action(self):
        """Handle Add Month button click to prepare data for next billing period."""
        if self.add_month_manager is None:
            # Initialize AddMonthManager if not already done
            self.add_month_manager = AddMonthManager(
                self.main_window.supabase_manager, 
                self.main_window
            )
        
        # Execute the Add Month workflow
        success = self.add_month_manager.execute_add_month(parent_widget=self)
        
        if success:
            # Trigger main tab calculation to update results display
            self.calculate_main()

    def setup_navigation_main_tab(self):
        """Configure Enter / Up / Down focus navigation for Main tab fields.

        Order:
            meter-1 → diff-1 → meter-2 → diff-2 → … → meter-N → diff-N → additional_amount

        • Enter / Down moves focus to next widget in the sequence (wrap-around).
        • Up moves focus to the previous widget in the sequence (wrap-around).
        """
        if not (self.meter_entries or self.diff_entries or self.additional_amount_input):
            return  # Nothing to wire up yet

        meters = self.meter_entries
        diffs = self.diff_entries
        aa    = self.additional_amount_input

        # ── Enter / Return sequence (already OK) ────────────────────────────
        enter_seq = []
        max_len = max(len(meters), len(diffs))
        for i in range(max_len):
            if i < len(meters):
                enter_seq.append(meters[i])
            if i < len(diffs):
                enter_seq.append(diffs[i])
        if aa:
            enter_seq.append(aa)

        # ── Up / Down sequences (column-wise) ──────────────────────────────
        #   Up:  … m2 → m1 → AA → d3 → d2 → d1 → m3 … (wrap)
        up_seq = list(reversed(meters))
        if aa:
            up_seq.append(aa)
        up_seq.extend(reversed(diffs))

        down_seq = list(reversed(up_seq))

        # Helper to link navigation for a given mapping list
        def _link_sequence(seq, attr_name):
            if not seq:
                return
            length = len(seq)
            for idx, w in enumerate(seq):
                nxt = seq[(idx + 1) % length]
                setattr(w, attr_name, nxt)

        # Apply mappings
        _link_sequence(enter_seq, 'next_widget_on_enter')
        _link_sequence(up_seq,    'up_widget')
        _link_sequence(down_seq,  'down_widget')

        # Ensure initial focus inside the tab if none is currently in sequence
        if self.focusWidget() not in enter_seq:
            enter_seq[0].setFocus()

    def add_theme_toggle_button(self, btn):
        """Insert the theme toggle button into the saved row."""
        if hasattr(self, "_save_buttons_row") and self._save_buttons_row is not None:
            btn.setParent(self)
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # add before final stretch (index -1)
            self._save_buttons_row.insertWidget(self._save_buttons_row.count()-1, btn, 1)
    
    def _apply_consistent_theming(self):
        """Apply consistent theming and ensure proper dark/light theme support."""
        from qfluentwidgets import isDarkTheme, Theme
        
        # Detect current theme
        is_dark = isDarkTheme()
        
        # Apply theme-aware styling to the main tab
        if is_dark:
            self._apply_dark_theme_styling()
        else:
            self._apply_light_theme_styling()
        
        # Apply consistent accent colors throughout
        self._apply_accent_colors()
    
    def _apply_dark_theme_styling(self):
        """Apply dark theme specific styling."""
        self.setStyleSheet("""
            MainTab {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QWidget {
                background-color: transparent;
            }
            
            BodyLabel, CaptionLabel, TitleLabel {
                color: #ffffff;
            }
        """)
    
    def _apply_light_theme_styling(self):
        """Apply light theme specific styling."""
        self.setStyleSheet("""
            MainTab {
                background-color: #f5f5f5;
                color: #000000;
            }
            
            QWidget {
                background-color: transparent;
            }
            
            BodyLabel, CaptionLabel, TitleLabel {
                color: #000000;
            }
        """)
    
    def _apply_accent_colors(self):
        """Apply consistent accent colors across all themed elements."""
        # This method ensures all themed elements use the same accent color
        accent_color = "#0078D4"
        
        # Update any dynamically created elements with consistent accent colors
        for card in self.findChildren(ResultCard):
            if hasattr(card, 'theme_color'):
                # Maintain individual card colors but ensure consistency
                pass
        
        # Ensure final amount card uses accent color
        if hasattr(self, 'final_amount_card'):
            self.final_amount_card.setStyleSheet(self.final_amount_card.styleSheet().replace(
                "#0078D4", accent_color
            ))
    
    def update_theme(self):
        """Update theme when system theme changes."""
        self._apply_consistent_theming()
        
        # Refresh all child widgets to apply new theme
        for widget in self.findChildren(QWidget):
            widget.update()
    
    def add_subtle_animations(self):
        """Add subtle animations and transitions for interactive elements."""
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        
        # Add entrance animations for all cards
        cards = self.findChildren(CardWidget)
        for i, card in enumerate(cards):
            if not hasattr(card, '_entrance_animation'):
                animation = QPropertyAnimation(card, b"windowOpacity")
                animation.setDuration(300 + (i * 50))  # Staggered animation
                animation.setStartValue(0.0)
                animation.setEndValue(1.0)
                animation.setEasingCurve(QEasingCurve.OutCubic)
                card._entrance_animation = animation
                animation.start()
    
    def showEvent(self, event):
        """Override show event to trigger entrance animations."""
        super().showEvent(event)
        # Delay animations slightly to ensure proper layout
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.add_subtle_animations)

    # Dummy classes for testing purposes
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow

    class DummyMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.load_info_source_combo = QComboBox()
            self.load_info_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
            self.supabase = None
            self.check_internet_connectivity = lambda: True

        def setup_navigation(self):
            pass

    app = QApplication(sys.argv)
    main_window = DummyMainWindow()
    main_tab_widget = MainTab(main_window)
    main_tab_widget.setWindowTitle("MainTab Test")
    main_tab_widget.setGeometry(100, 100, 800, 600)
    main_tab_widget.show()
    sys.exit(app.exec_())
