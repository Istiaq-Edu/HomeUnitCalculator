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
    ScrollArea, SmoothMode,
    FluentIconBase, StrongBodyLabel
)

from src.core.utils import resource_path
from src.core.add_month_manager import AddMonthManager
from src.ui.custom_widgets import (
    CustomLineEdit, AutoScrollArea, CollapsibleSection, KpiChipBar,
    CalculatorTheme, calculator_card_style, apply_card_shadow,
    section_header_style, section_divider_style, results_highlight_style,
    input_style, primary_button_style, caption_label_style
)
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
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(56)
        self.setMaximumHeight(56)
        
        self.meter_input = CustomLineEdit()
        self.meter_input.setObjectName(f"meter_edit_{pair_index}")
        numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))
        self.meter_input.setValidator(numeric_validator)
        self.meter_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.meter_input.setMinimumWidth(100)
        
        self.diff_input = CustomLineEdit()
        self.diff_input.setObjectName(f"diff_edit_{pair_index}")
        self.diff_input.setValidator(numeric_validator)
        self.diff_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.diff_input.setMinimumWidth(100)
        
        self.meter_input.focusInEvent = self._create_focus_handler(self.meter_input)
        self.diff_input.focusInEvent = self._create_focus_handler(self.diff_input)
        
        # Remove button — clean, minimal
        self.remove_button = PushButton()
        self.remove_button.setIcon(FluentIcon.CLOSE.icon(color=QColor(255, 255, 255)))
        self.remove_button.setIconSize(QSize(14, 14))
        self.remove_button.setFixedSize(28, 28)
        self.remove_button.clicked.connect(self._on_remove_clicked)
        self.remove_button.setToolTip("")
        self.remove_button.setStyleSheet("""
            PushButton {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 0px;
            }
            PushButton:hover {
                background-color: rgba(255, 80, 80, 0.25);
                border-color: rgba(255, 80, 80, 0.40);
            }
            PushButton:pressed {
                background-color: rgba(255, 80, 80, 0.15);
                border-color: rgba(255, 80, 80, 0.30);
            }
        """)
        
        layout = QGridLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(0)

        # Labels — compact, with accent color for the number
        meter_label = BodyLabel(f"Meter {pair_index + 1}")
        meter_label.setObjectName("meter_label")
        meter_label.setStyleSheet("""
            font-weight: bold;
            color: #49C6FF;
            font-size: 11px;
            margin: 0px;
            background: transparent;
            border: none;
        """)
        diff_label = BodyLabel(f"Difference {pair_index + 1}")
        diff_label.setObjectName("diff_label")
        diff_label.setStyleSheet("""
            font-weight: bold;
            color: #FFB74D;
            font-size: 11px;
            margin: 0px;
            background: transparent;
            border: none;
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

        layout.addWidget(meter_label, 0, 0)
        layout.addWidget(diff_label, 0, 1)
        meter_wrap = QWidget()
        meter_wrap.setStyleSheet("background: transparent; border: none;")
        meter_wrap_l = QHBoxLayout(meter_wrap)
        meter_wrap_l.setContentsMargins(4, 0, 4, 0)
        meter_wrap_l.setSpacing(0)
        meter_wrap_l.addWidget(self.meter_input)
        diff_wrap = QWidget()
        diff_wrap.setStyleSheet("background: transparent; border: none;")
        diff_wrap_l = QHBoxLayout(diff_wrap)
        diff_wrap_l.setContentsMargins(4, 0, 4, 0)
        diff_wrap_l.setSpacing(0)
        diff_wrap_l.addWidget(self.diff_input)
        layout.addWidget(meter_wrap, 1, 0)
        layout.addWidget(diff_wrap, 1, 1)
        layout.setColumnMinimumWidth(2, 8)
        spacer = QSpacerItem(8, 1, QSizePolicy.Fixed, QSizePolicy.Minimum)
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
        
        # Apply styling — transparent bg, subtle bottom border to separate rows
        self.setStyleSheet("""
            ReadingPairWidget {
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                margin: 0px;
            }
            ReadingPairWidget:hover {
                background: rgba(255, 255, 255, 0.06);
                border-bottom: 1px solid rgba(255, 255, 255, 0.12);
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
    """Composite button with a left icon and bold text — styled with accent blue."""
    def __init__(self, text: str, on_click):
        super().__init__()
        self.on_click = on_click
        self.setObjectName("add_pair_btn")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        try:
            icon = FluentIcon.ADD.icon(color=QColor(255, 255, 255))
            icon_label.setPixmap(icon.pixmap(18, 18))
        except Exception:
            icon_label.setText("+")
            icon_label.setStyleSheet("color: white; font-weight: bold;")
        icon_label.setFixedSize(18, 18)
        icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = BodyLabel(text)
        text_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px; background: transparent; border: none;")
        text_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout.addStretch(1)
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)
        layout.addSpacing(6)
        layout.addWidget(text_label, 0, Qt.AlignVCenter)
        layout.addStretch(1)

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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        radius = 8

        if self._hover:
            bg = QColor(80, 80, 80, 180)
            border = QColor(120, 120, 120, 200)
        else:
            bg = QColor(60, 60, 60, 120)
            border = QColor(90, 90, 90, 140)

        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(r, radius, radius)
        return

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.on_click:
            self.on_click()
        return super().mouseReleaseEvent(event)


class ResultCard(QWidget):
    """Individual result card with icon, title, and value — no panel background."""
    
    def __init__(self, title, icon, theme_color, value_label=None):
        super().__init__()
        self.title = title
        self.theme_color = theme_color
        self.value_label = value_label
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(64)
        self.setMaximumHeight(64)
        self.setFixedHeight(64)
        
        self.setAttribute(Qt.WA_Hover, False)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        dark_accent = _darken_color(self.theme_color, 0.40)
        vivid_accent = _lighten_color(self.theme_color, 0.25)

        self.setObjectName("result_card")

        # Direct layout on the card itself — no inner panel, no background box
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(8)
        
        # Icon
        icon_label = QLabel()
        if isinstance(icon, FluentIconBase):
            pixmap = icon.icon().pixmap(28, 28)
        else:
            pixmap = icon.pixmap(28, 28) if hasattr(icon, 'pixmap') else QPixmap()
        
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
        
        icon_chip = QWidget()
        icon_chip.setObjectName("icon_chip")
        icon_chip.setFixedSize(36, 36)
        icon_chip.setAttribute(Qt.WA_StyledBackground, True)
        chip_bg_rgba = _rgba_from_hex(self.theme_color, 0.14)
        icon_chip.setStyleSheet(f"""
            #icon_chip {{
                background-color: {chip_bg_rgba};
                border-radius: 8px;
                border: none;
            }}
        """)
        icon_chip.setGraphicsEffect(None)

        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        chip_layout = QVBoxLayout(icon_chip)
        chip_layout.setContentsMargins(3, 3, 3, 3)
        chip_layout.setSpacing(0)
        chip_layout.addWidget(icon_label, 1, Qt.AlignCenter)
        
        # Title — no background
        title_label = CaptionLabel(title)
        title_label.setStyleSheet("""
            color: #FFFFFF;
            font-weight: bold;
            font-size: 13px;
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        
        # Value — no background
        if value_label:
            self.display_label = value_label
            self.display_label.setStyleSheet(f"""
                color: {vivid_accent};
                font-size: 28px;
                font-weight: 700;
                background: transparent;
                border: none;
            """)
            self.display_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        else:
            self.display_label = BodyLabel("0")
            self.display_label.setStyleSheet(f"""
                color: {vivid_accent};
                font-size: 28px;
                font-weight: 700;
                background: transparent;
                border: none;
            """)
            self.display_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Title + value row
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_row.addWidget(title_label, 1)
        header_row.addStretch(1)
        header_row.addWidget(self.display_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        header_row.setAlignment(title_label, Qt.AlignVCenter)
        header_row.setAlignment(self.display_label, Qt.AlignVCenter)
        
        layout.addWidget(icon_chip)
        layout.addLayout(header_row, 1)
        layout.setAlignment(icon_chip, Qt.AlignVCenter)
        layout.setAlignment(header_row, Qt.AlignVCenter)
        
        # No panel, no background box — just a thin bottom border to separate cards
        self.setStyleSheet(f"""
            #result_card {{
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }}
        """)
        
        self._setup_animations()
    
    def enterEvent(self, event):
        return
    
    def leaveEvent(self, event):
        return
    
    def event(self, e):
        if e.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True
        return super().event(e)
    
    def _setup_animations(self):
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_animation.setDuration(300)
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, '_opacity_animation'):
            self._opacity_animation.start()
    
    def update_value(self, value):
        if self.value_label:
            self.value_label.setText(str(value))
        else:
            self.display_label.setText(str(value))
        self._pulse_effect()
    
    def _pulse_effect(self):
        """Brief opacity flash when value updates."""
        try:
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0.4)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
        except Exception:
            pass


class FinalAmountCard(QWidget):
    """Final Amount card — no inner panel, no background box behind text."""
    
    def __init__(self, value_label):
        super().__init__()
        self.value_label = value_label
        
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(110)
        self.setMaximumHeight(110)
        self.setFixedHeight(110)
        
        self.setAttribute(Qt.WA_Hover, False)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("final_amount_card")
        
        # Direct layout — no inner panel
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(14)
        
        # Icon
        icon_label = QLabel()
        money_icon = FluentIcon.SHOPPING_CART
        pixmap = money_icon.icon().pixmap(44, 44)
        
        if not pixmap.isNull():
            colored_pixmap = QPixmap(pixmap.size())
            colored_pixmap.fill(Qt.transparent)
            painter = QPainter(colored_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(colored_pixmap.rect(), QColor("#0078D4"))
            painter.end()
            icon_label.setPixmap(colored_pixmap)
        
        theme_color = "#0078D4"
        dark_accent = _darken_color(theme_color, 0.40)

        icon_chip = QWidget()
        icon_chip.setObjectName("final_amount_icon_chip")
        icon_chip.setFixedSize(56, 56)
        icon_chip.setAttribute(Qt.WA_StyledBackground, True)
        chip_bg_rgba2 = _rgba_from_hex(theme_color, 0.14)
        icon_chip.setStyleSheet(f"""
            #final_amount_icon_chip {{
                background-color: {chip_bg_rgba2};
                border-radius: 12px;
                border: none;
            }}
        """)
        icon_chip.setGraphicsEffect(None)

        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        chip_layout2 = QVBoxLayout(icon_chip)
        chip_layout2.setContentsMargins(6, 6, 6, 6)
        chip_layout2.setSpacing(0)
        chip_layout2.addWidget(icon_label, 1, Qt.AlignCenter)
        
        # Content — title, value, subtitle — all transparent bg
        content_layout = QVBoxLayout()
        content_layout.setSpacing(6)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = CaptionLabel("Final Amount")
        title_label.setStyleSheet("""
            color: #FFFFFF;
            font-weight: bold;
            font-size: 16px;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)
        
        subtitle_label = CaptionLabel("Total utility cost")
        subtitle_label.setStyleSheet("""
            color: #aaaaaa;
            font-size: 11px;
            font-style: italic;
            background: transparent;
            border: none;
        """)
        
        vivid_blue = _lighten_color(theme_color, 0.18)
        self.value_label.setStyleSheet(f"""
            color: {vivid_blue};
            font-size: 40px;
            font-weight: 800;
            background: transparent;
            border: none;
        """)
        self.value_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        content_layout.addWidget(title_label, 0, Qt.AlignHCenter)
        content_layout.addWidget(self.value_label, 1, Qt.AlignHCenter | Qt.AlignVCenter)
        content_layout.addWidget(subtitle_label, 0, Qt.AlignHCenter)
        
        layout.addWidget(icon_chip)
        layout.addLayout(content_layout, 1)
        layout.setAlignment(icon_chip, Qt.AlignVCenter)
        layout.setAlignment(content_layout, Qt.AlignVCenter)
        
        # Subtle blue tint background + neutral 1px top separator
        self.setStyleSheet(f"""
            #final_amount_card {{
                background-color: rgba(0, 120, 212, 0.08);
                border: none;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }}
        """)
        
        self._setup_premium_animations()
    
    def enterEvent(self, event):
        return

    def leaveEvent(self, event):
        return

    def event(self, e):
        if e.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True
        return super().event(e)
    
    def _setup_premium_animations(self):
        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_animation.setDuration(300)
        self._opacity_animation.setStartValue(0.0)
        self._opacity_animation.setEndValue(1.0)
        self._opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, '_opacity_animation'):
            self._opacity_animation.start()
    
    def update_value(self, value):
        self.value_label.setText(str(value))
        self._premium_update_effect()
    
    def _premium_update_effect(self):
        """Brief opacity flash when value updates."""
        try:
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            effect = QGraphicsOpacityEffect(self)
            self.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(300)
            anim.setStartValue(0.4)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
        except Exception:
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

        # ── Tab background ──────────────────────────────────────────────
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {CalculatorTheme.TAB_BG};")

        # ── Scroll area ─────────────────────────────────────────────────
        self.main_scroll_area = ScrollArea()
        self.main_scroll_area.setWidgetResizable(True)
        self.main_scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_scroll_area.setStyleSheet(f"ScrollArea {{ background-color: {CalculatorTheme.TAB_BG}; border: none; }}")
        try:
            self.main_scroll_area.enableTransparentBackground()
        except Exception:
            pass

        # Disable QFluentWidgets smooth scrolling — it causes a slidy/laggy feel
        # Fall back to native Qt wheel scrolling which is immediate and grippy
        try:
            self.main_scroll_area.setSmoothMode(SmoothMode.NO_SMOOTH, Qt.Vertical)
        except Exception:
            pass

        scroll_content_widget = QWidget()
        scroll_content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll_content_widget.setStyleSheet(f"background-color: {CalculatorTheme.TAB_BG};")

        main_layout = QVBoxLayout(scroll_content_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ── 1. Actions (collapsible, expanded by default) ──────────────
        actions_content = QWidget()
        actions_content.setObjectName("actions_card")
        actions_content.setStyleSheet(calculator_card_style("actions_card"))
        actions_content.setAttribute(Qt.WA_StyledBackground, True)
        actions_content.setFocusPolicy(Qt.NoFocus)
        actions_content.setAttribute(Qt.WA_Hover, False)
        actions_content.setMouseTracking(False)
        self._load_data_group = actions_content
        actions_content.installEventFilter(self)

        actions_layout = QVBoxLayout(actions_content)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)

        # Two distinct containers stacked vertically
        load_data_container = self._create_load_data_container()
        actions_layout.addWidget(load_data_container)

        actions_section = CollapsibleSection("\u26a1 Actions", actions_content, expanded=False)
        main_layout.addWidget(actions_section)

        # ── 2. Main Calculation card ────────────────────────────────────
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

    def create_unified_calculator_card(self):
        """Create the unified Main Calculation card — side-by-side inputs
        and results in one polished card. Save buttons are in the Room Calculations section.
        """
        # ── Outer card ──────────────────────────────────────────────────
        card = QWidget()
        card.setObjectName("unified_calculator_card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFocusPolicy(Qt.NoFocus)
        card.setAttribute(Qt.WA_Hover, False)
        card.setMouseTracking(False)
        card.setStyleSheet(calculator_card_style("unified_calculator_card"))
        self._billing_unified_group = card
        card.installEventFilter(self)
        apply_card_shadow(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(8)

        # ── Title row: icon + title left, period bar right ──────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.setContentsMargins(0, 0, 0, 0)

        title = TitleLabel("\U0001f4ca Main Calculation")
        title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #0078D4;
            letter-spacing: 1px;
            background: transparent;
            border: none;
        """)
        title_row.addWidget(title)
        title_row.addStretch(1)

        # Period bar — Month/Year inline, styled as a pill
        period_bar = QWidget()
        period_bar.setAttribute(Qt.WA_StyledBackground, True)
        period_bar.setStyleSheet("""
            background-color: rgba(0, 120, 212, 0.18);
            border: 1px solid rgba(0, 120, 212, 0.40);
            border-radius: 8px;
        """)
        period_layout = QHBoxLayout(period_bar)
        period_layout.setContentsMargins(10, 4, 10, 4)
        period_layout.setSpacing(8)

        month_label = BodyLabel("Month:")
        month_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none; font-size: 12px;")
        self.month_combo = ComboBox()
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setMinimumWidth(120)

        year_label = BodyLabel("Year:")
        year_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none; font-size: 12px;")
        self.year_spinbox = SpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self._apply_no_select_to_spinbox(self.year_spinbox)
        self.year_spinbox.setFocusPolicy(Qt.NoFocus)
        self.year_spinbox.setMinimumWidth(90)
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

        period_layout.addWidget(month_label)
        period_layout.addWidget(self.month_combo)
        period_layout.addSpacing(4)
        period_layout.addWidget(year_label)
        period_layout.addWidget(self.year_spinbox)
        title_row.addWidget(period_bar)

        # Add Next Month button
        add_next_month_btn = PrimaryPushButton("Add Next Month")
        add_next_month_btn.setIcon(FluentIcon.ADD.icon(color=QColor(255, 255, 255)))
        add_next_month_btn.setIconSize(QSize(18, 18))
        add_next_month_btn.clicked.connect(self.add_month_action)
        add_next_month_btn.setToolTip("Copy current month's final readings as next month's previous readings")
        add_next_month_btn.setFixedHeight(34)
        add_next_month_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #FF8C00;
                border: 1px solid #FF8C00;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                qproperty-iconSize: 18px 18px;
                padding: 6px 14px 6px 32px;
            }
            PrimaryPushButton:hover { background-color: #FF7F00; border-color: #FF7F00; }
            PrimaryPushButton:pressed { background-color: #FF6600; border-color: #FF6600; }
        """)
        add_next_month_btn.setMinimumWidth(150)
        title_row.addWidget(add_next_month_btn)

        card_layout.addLayout(title_row)

        # Main divider
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet("color: #0078D4; background-color: #0078D4; border: none; max-height: 2px; margin: 0px 0px 2px 0px;")
        card_layout.addWidget(sep)

        # ════════════════════════════════════════════════════════════════
        # TWO-COLUMN BODY: Inputs (left) | Results (right)
        # ════════════════════════════════════════════════════════════════
        body = QHBoxLayout()
        body.setSpacing(20)

        # ── LEFT: Inputs ────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(8)

        # Reading Pairs header
        rp_title = BodyLabel("\U0001f4cf Reading Pairs")
        rp_title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #49C6FF;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """)
        left.addWidget(rp_title)
        rp_sep = QFrame()
        rp_sep.setFrameShape(QFrame.HLine)
        rp_sep.setFrameShadow(QFrame.Plain)
        rp_sep.setStyleSheet("color: #49C6FF; background-color: #49C6FF; border: none; max-height: 1px; margin: 0px 0px 4px 0px;")
        left.addWidget(rp_sep)

        pairs_scroll = ScrollArea()
        pairs_scroll.setWidgetResizable(True)
        pairs_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pairs_scroll.setMinimumHeight(110)
        pairs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pairs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pairs_scroll.setStyleSheet("ScrollArea { background: transparent; border: none; }")

        pairs_container = QWidget()
        pairs_container.setStyleSheet("background: transparent; border: none;")
        pairs_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.pairs_layout = QVBoxLayout(pairs_container)
        self.pairs_layout.setSpacing(4)
        self.pairs_layout.setContentsMargins(4, 2, 4, 10)
        pairs_scroll.setWidget(pairs_container)
        left.addWidget(pairs_scroll, 0, Qt.AlignTop)
        self.pairs_scroll = pairs_scroll

        self._pairs_fixed_gap = 6
        left.addSpacing(self._pairs_fixed_gap)
        self._pairs_btn_top_gap = 8
        add_pair_button = AddPairButton("Add Reading Pair", lambda: self.add_reading_pair())
        button_holder = QWidget()
        button_holder.setStyleSheet("background: transparent; border: none;")
        bh_layout = QVBoxLayout(button_holder)
        bh_layout.setContentsMargins(0, self._pairs_btn_top_gap, 0, 0)
        bh_layout.setSpacing(0)
        bh_layout.addWidget(add_pair_button)
        left.addWidget(button_holder)
        self._pairs_add_button = add_pair_button

        # Additional Amount header
        aa_title = BodyLabel("\U0001f4b0 Additional Amount")
        aa_title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #0078D4;
            background: transparent;
            border: none;
            padding: 0;
            margin: 0;
        """)
        left.addWidget(aa_title)
        aa_sep = QFrame()
        aa_sep.setFrameShape(QFrame.HLine)
        aa_sep.setFrameShadow(QFrame.Plain)
        aa_sep.setStyleSheet("color: #0078D4; background-color: #0078D4; border: none; max-height: 1px; margin: 0px 0px 4px 0px;")
        left.addWidget(aa_sep)

        aa_row = QHBoxLayout()
        aa_row.setContentsMargins(0, 0, 0, 0)
        aa_row.setSpacing(8)
        self.additional_amount_input = CustomLineEdit()
        self.additional_amount_input.setObjectName("main_additional_amount_input")
        self.additional_amount_input.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))
        currency_label = CaptionLabel("TK")
        currency_label.setStyleSheet("font-weight: bold; color: #0078D4; font-size: 13px; padding: 6px 10px; background-color: rgba(0, 120, 212, 0.12); border: 1px solid rgba(0, 120, 212, 0.25); border-radius: 8px;")
        aa_row.addWidget(self.additional_amount_input, 1)
        aa_row.addWidget(currency_label)
        left.addLayout(aa_row)

        # Calculate button — full width, prominent
        self.main_calculate_button = PrimaryPushButton("Calculate")
        self.main_calculate_button.setIcon(FluentIcon.ACCEPT_MEDIUM.icon(color=QColor(255, 255, 255)))
        self.main_calculate_button.setIconSize(QSize(20, 20))
        self.main_calculate_button.clicked.connect(self.calculate_main)
        self.main_calculate_button.setToolTip("Calculate total units, per-unit cost, and final amount from meter readings")
        self.main_calculate_button.setFixedHeight(40)
        self.main_calculate_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_calculate_button.setStyleSheet(primary_button_style() + """
            PrimaryPushButton {
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
                text-align: center;
                font-size: 15px;
            }
        """)
        left.addSpacing(4)
        left.addWidget(self.main_calculate_button)
        left.addStretch(1)

        body.addLayout(left, 1)

        # ── RIGHT: Results ──────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(4)

        results_title = TitleLabel("\u2705 Calculation Results")
        results_title.setAlignment(Qt.AlignCenter)
        results_title.setStyleSheet("""
            font-size: 18px;
            font-weight: 800;
            color: #81C784;
            letter-spacing: 0.8px;
            background: transparent;
            border: none;
            margin: 0px 0px 2px 0px;
        """)
        right.addWidget(results_title)

        results_sep = QFrame()
        results_sep.setFrameShape(QFrame.HLine)
        results_sep.setFrameShadow(QFrame.Plain)
        results_sep.setStyleSheet("color: #81C784; background-color: #81C784; border: none; max-height: 2px; margin: 0px 0px 2px 0px;")
        right.addWidget(results_sep)

        # Result cards — no background boxes
        self.total_unit_value_label = BodyLabel("0")
        self.total_diff_value_label = BodyLabel("0")
        self.per_unit_cost_value_label = BodyLabel("0.00")
        self.additional_amount_value_label = BodyLabel("0")

        right.addWidget(ResultCard("Total Units", FluentIcon.TILES, "#4FC3F7", self.total_unit_value_label))
        right.addWidget(ResultCard("Total Difference", FluentIcon.REMOVE, "#FFB74D", self.total_diff_value_label))
        right.addWidget(ResultCard("Per Unit Cost", FluentIcon.SHOPPING_CART, "#81C784", self.per_unit_cost_value_label))
        right.addWidget(ResultCard("Added Amount", FluentIcon.ADD, "#BA68C8", self.additional_amount_value_label))
        right.addWidget(ResultCard("Total Cost", FluentIcon.UP, "#26A69A"))

        self.in_total_value_label = BodyLabel("0.00")
        self.final_amount_card = FinalAmountCard(self.in_total_value_label)
        right.addWidget(self.final_amount_card)

        right.addStretch(1)

        body.addLayout(right, 1)

        card_layout.addLayout(body)

        # Keep reference for external code
        self.results_group_widget = card

        return card

    def _create_load_data_container(self):
        """Container 1: Load Data — Month/Year selection, source, and load button."""
        container = QWidget()
        container.setObjectName("load_data_container")
        container.setAttribute(Qt.WA_StyledBackground, True)
        container.setFocusPolicy(Qt.NoFocus)
        container.setAttribute(Qt.WA_Hover, False)
        container.setMouseTracking(False)
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        container.setStyleSheet("""
            #load_data_container {{
                background-color: {bg};
                border: 1px solid {border};
                border-left: 3px solid {accent};
                border-radius: {radius}px;
            }}
        """.format(
            bg=CalculatorTheme.CARD_BG,
            border=CalculatorTheme.CARD_BORDER,
            accent=CalculatorTheme.ACCENT_ACTIONS,
            radius=CalculatorTheme.CARD_RADIUS
        ))

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Month
        load_month_label = BodyLabel("Month:")
        load_month_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
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
        load_year_label.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none;")
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
            PrimaryPushButton {{
                color: white;
                background-color: {primary};
                border: 1px solid {primary};
                border-radius: {radius}px;
                font-weight: 600;
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
            }}
            PrimaryPushButton:hover {{
                background-color: {hover};
                border-color: {hover};
            }}
            PrimaryPushButton:pressed {{
                background-color: {pressed};
                border-color: {pressed};
            }}
        """.format(
            primary=CalculatorTheme.BTN_PRIMARY,
            hover=CalculatorTheme.BTN_PRIMARY_HOVER,
            pressed=CalculatorTheme.BTN_PRIMARY_PRESSED,
            radius=CalculatorTheme.BTN_RADIUS
        ))
        load_button.setMinimumWidth(120)
        load_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout.addSpacing(12)
        layout.addWidget(load_button, 1)

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
        section.setStyleSheet("background: transparent; border: none;")
        section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        section.setStyleSheet(calculator_card_style("rooms_section"))
        apply_card_shadow(section)
        section.setAttribute(Qt.WA_StyledBackground, True)
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
        title.setStyleSheet(section_header_style(CalculatorTheme.ACCENT_ROOMS).replace(
            str(CalculatorTheme.HEADER_SIZE) + "px", "26px"
        ).replace("bold", "800") + "letter-spacing: 0.5px; background: transparent; border: none;")

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
        sep.setStyleSheet("border: none; " + section_divider_style(CalculatorTheme.ACCENT_ROOMS))
        layout.addWidget(sep)

        # Room cards container (FlowLayout expands naturally, outer scroll handles scrolling)
        rooms_card_container = QWidget()
        rooms_card_container.setStyleSheet("background: transparent; border: none;")
        rooms_card_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.rooms_scroll_layout = FlowLayout(rooms_card_container)
        self.rooms_scroll_layout.setSpacing(8)
        layout.addWidget(rooms_card_container)

        # Calculate Room Bills button + Save buttons in one row
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        self.calculate_rooms_button = PrimaryPushButton("Calculate Room Bills")
        self.calculate_rooms_button.clicked.connect(self.calculate_rooms)
        self.calculate_rooms_button.setIcon(FluentIcon.ACCEPT_MEDIUM.icon(color=QColor(255, 255, 255)))
        self.calculate_rooms_button.setIconSize(QSize(20, 20))
        self.calculate_rooms_button.setFixedHeight(40)
        self.calculate_rooms_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calculate_rooms_button.setEnabled(False)
        self.calculate_rooms_button.setToolTip("Calculate meter readings first")
        self.calculate_rooms_button.setStyleSheet(primary_button_style() + """
            PrimaryPushButton {
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
                text-align: center;
            }
            PrimaryPushButton:disabled {
                background: #555;
                border-color: #444;
                color: #999;
            }
        """)
        bottom_row.addWidget(self.calculate_rooms_button, 2)

        # Save buttons
        pdf_button = PrimaryPushButton("Save PDF")
        pdf_button.setIcon(FluentIcon.DOCUMENT.icon(color=QColor(255, 255, 255)))
        pdf_button.setIconSize(QSize(18, 18))
        pdf_button.setFixedHeight(40)
        pdf_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pdf_button.clicked.connect(self.main_window.save_to_pdf)
        pdf_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #d32f2f;
                border: 1px solid #d32f2f;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                qproperty-iconSize: 18px 18px;
                padding: 8px 12px 8px 30px;
                text-align: center;
            }
            PrimaryPushButton:hover { background-color: #f44336; border-color: #f44336; }
            PrimaryPushButton:pressed { background-color: #b71c1c; border-color: #b71c1c; }
        """)
        bottom_row.addWidget(pdf_button, 1)

        csv_button = PrimaryPushButton("Save CSV")
        csv_button.setIcon(FluentIcon.SAVE.icon(color=QColor(255, 255, 255)))
        csv_button.setIconSize(QSize(18, 18))
        csv_button.setFixedHeight(40)
        csv_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        csv_button.clicked.connect(self.main_window.save_calculation_to_csv)
        csv_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #388e3c;
                border: 1px solid #388e3c;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                qproperty-iconSize: 18px 18px;
                padding: 8px 12px 8px 30px;
                text-align: center;
            }
            PrimaryPushButton:hover { background-color: #4caf50; border-color: #4caf50; }
            PrimaryPushButton:pressed { background-color: #2e7d32; border-color: #2e7d32; }
        """)
        bottom_row.addWidget(csv_button, 1)

        cloud_button = PrimaryPushButton("Save Cloud")
        cloud_button.setIcon(FluentIcon.CLOUD.icon(color=QColor(255, 255, 255)))
        cloud_button.setIconSize(QSize(18, 18))
        cloud_button.setFixedHeight(40)
        cloud_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cloud_button.clicked.connect(self.main_window.save_calculation_to_supabase)
        cloud_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #7b1fa2;
                border: 1px solid #7b1fa2;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                qproperty-iconSize: 18px 18px;
                padding: 8px 12px 8px 30px;
                text-align: center;
            }
            PrimaryPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9c27b0, stop:1 #7b1fa2); border-color: #9c27b0; }
            PrimaryPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a1b9a, stop:1 #4a148c); border-color: #6a1b9a; }
        """)
        bottom_row.addWidget(cloud_button, 1)

        self._save_buttons_row = bottom_row
        layout.addLayout(bottom_row)

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
                CardWidget { background-color: #2b2b2b; border: 1px solid #3d3d3d; border-radius: 8px; }
                CardWidget:hover { background-color: #2b2b2b; border: 1px solid #3d3d3d; }
            """)
            outer_layout = QVBoxLayout(room_group)
            outer_layout.setSpacing(8)
            outer_layout.setContentsMargins(16, 12, 16, 16)

            title = TitleLabel(f"Room {i+1}")
            title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFB86B; letter-spacing: 0.5px; margin: 0px; background: transparent;")
            outer_layout.addWidget(title)

            header_line = QFrame()
            header_line.setFrameShape(QFrame.HLine)
            header_line.setFrameShadow(QFrame.Plain)
            header_line.setStyleSheet("color: #FFB86B; background-color: #FFB86B; border: none; max-height: 2px; margin: 2px 0px 4px 0px;")
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
            pl.setStyleSheet("font-weight: bold; color: #ffffff; background: transparent; border: none; font-size: 12px;")
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
                container.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid rgba({r},{g},{b},0.15);")
                cl = QHBoxLayout(container)
                cl.setContentsMargins(10, 4, 10, 4)
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
        """Update button style based on selected data source.
        Both sources use the same neutral dark style — no color coding.
        """
        self.load_source_button.setStyleSheet("""
            DropDownPushButton {{
                color: white;
                background-color: #3d3d3d;
                border: 1px solid #4a4a4a;
                border-radius: {radius}px;
                font-weight: 600;
                qproperty-iconSize: 20px 20px;
                padding: 8px 40px 8px 36px;
            }}
            DropDownPushButton:hover {{
                background-color: #454545;
                border-color: #555555;
            }}
            DropDownPushButton:pressed {{
                background-color: #353535;
                border-color: #404040;
            }}
            DropDownPushButton::menu-indicator {{
                subcontrol-position: right center;
                subcontrol-origin: padding;
                right: 8px;
            }}
        """.format(radius=CalculatorTheme.BTN_RADIUS))

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
