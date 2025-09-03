from PyQt5.QtCore import Qt, QEvent, QPoint, QTimer, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QCursor, QColor, QKeySequence
from PyQt5.QtWidgets import (
    QSizePolicy, QDialog, QVBoxLayout, QLabel, QProgressBar, QScrollBar, QAbstractScrollArea, QShortcut
)
from qfluentwidgets import LineEdit, ScrollArea, SpinBox, PushButton, TableWidget, SmoothMode

from src.core.utils import resource_path

# Custom QLineEdit class for improved input handling and navigation
class CustomLineEdit(LineEdit):
    def __init__(self, *args, **kwargs):
        # Call the parent class constructor
        super().__init__(*args, **kwargs)
        # Set size policy to expanding horizontally
        # Apply dark theme palette to ensure contrast with CardWidget backgrounds
        self.setStyleSheet(
            """
            QLineEdit {
                background-color: #2f2f2f;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #0078D4;
            }
            """
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Initialize next and previous widget references
        self.next_widget_on_enter = None # For Enter/Return key
        self.up_widget = None
        self.down_widget = None

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Left or key == Qt.Key_Right:
            super().keyPressEvent(event) # Default QLineEdit behavior for Left/Right arrows
            return

        target_widget = None
        if key == Qt.Key_Up:
            target_widget = self.up_widget or self.findNextWidget(forward=False)
        elif key == Qt.Key_Down:
            target_widget = self.down_widget or self.findNextWidget(forward=True)
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            target_widget = self.next_widget_on_enter or self.findNextWidget(forward=True)
        
        if target_widget:
            target_widget.setFocus()
            event.accept()
            return
        elif key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter):
            # If Up, Down, Enter, Return was pressed but no target_widget is defined,
            # accept the event to prevent default Qt focus changes.
            event.accept()
            return
        
        # For any other keys not handled above (e.g. character input, Tab, etc.)
        super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.ensureWidgetVisible()

    def ensureWidgetVisible(self):
        # Ensure that this widget is visible within its parent ScrollArea
        parent = self.parent()
        while parent and not isinstance(parent, ScrollArea):
            parent = parent.parent()
        if parent:
            parent.ensureWidgetVisible(self)


    def moveFocus(self, forward=True):
        current = self.focusWidget()
        if current:
            next_widget = self.findNextWidget(forward)
            if next_widget:
                next_widget.setFocus()
            else:
                print("No valid next widget found")

    def findNextWidget(self, forward=True):
        parent_widget = self.parentWidget()
        if parent_widget is None:
            return None
        
        widgets = []
        w = parent_widget.focusProxy() or parent_widget
        start = w
        while True:
            if isinstance(w, CustomLineEdit):
                widgets.append(w)
            w = w.nextInFocusChain()
            if w is start:
                break
        
        try:
            current_index = widgets.index(self)
        except ValueError:
            return None
        
        if not widgets:
            return None

        if forward:
            next_index = (current_index + 1) % len(widgets)
        else:
            next_index = (current_index - 1 + len(widgets)) % len(widgets)
        
        return widgets[next_index]

# ------------------------------------------------------------------
# LeftIconButton - composite widget to display an icon on the left and
# a PrimaryPushButton text on the right. Solves icon/text overlap seen
# in QFluentWidgets default PushButton for certain glyphs.
# ------------------------------------------------------------------
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QWidget, QHBoxLayout
from qfluentwidgets import PrimaryPushButton, BodyLabel, FluentIcon

class LeftIconButton(QWidget):
    """A button that shows a Fluent icon in a fixed 20×20 area on the left
    and text inside a PrimaryPushButton on the right.  Exposes the
    ``clicked`` signal of the inner button so it can be used transparently
    as a normal button.
    """

    def __init__(self, icon: FluentIcon, text: str, color: str = "#2e7d32", parent=None):
        super().__init__(parent)
        self._icon = icon
        self.button = PrimaryPushButton(text)
        # self.button.setMinimumHeight(40)  # Removed for responsiveness
        self.button.setIconSize(QSize(1, 1))  # effectively hide default icon
        self.button.setProperty("color", color)
        self.button.setStyleSheet(self.get_stylesheet(color))

        self._icon_label = BodyLabel()
        # FluentIcon returns QIcon via .icon() method
        # Calculate icon size based on button font size for proportional scaling
        button_font = self.button.font()
        icon_size = max(16, int(button_font.pointSize() * 1.2))  # Scale with font size
        self._icon_label.setPixmap(self._icon.icon().pixmap(icon_size, icon_size))
        
        # Use proportional sizing instead of fixed size
        self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._icon_label.setMinimumWidth(icon_size + 6)  # Icon size + padding
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setProperty("color", color)
        self._icon_label.setStyleSheet(f"background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {{{self._lighten(color, 1.1)}}}, stop:1 {{{self._lighten(color, 0.9)}}}); border-top-left-radius:4px;border-bottom-left-radius:4px;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._icon_label)
        layout.addWidget(self.button, 1)

    # Re-expose inner button signals/properties -------------------------------------------------
    @property
    def clicked(self):
        """Qt signal of the inner button so you can do myBtn.clicked.connect(...)"""
        return self.button.clicked
    def setEnabled(self, enabled: bool):  # noqa: N802
        self.button.setEnabled(enabled)

    def setIconSize(self, size: QSize):  # noqa: N802
        # Update stored icon pixmap to requested size
        self._icon_label.setPixmap(self._icon.icon().pixmap(size.width(), size.height()))

    def setStyleSheet(self, style: str):  # noqa: N802
        # Proxy stylesheet to inner button
        self.button.setStyleSheet(style)

    # Utility -----------------------------------------------------------------
    def _lighten(self, color_str: str, factor: float) -> str:
        try:
            c = QColor(color_str)
            if not c.isValid():
                # Fallback for invalid color strings (e.g., "red-light")
                c = QColor("#2e7d32")
        except (TypeError, AttributeError):
            # Fallback for catastrophic failures
            c = QColor("#2e7d32")

        h, s, v, a = c.getHsvF()
        v = max(0, min(v * factor, 1))
        c.setHsvF(h, s, v, a)
        return c.name()

    def get_stylesheet(self, color):
        color_light = self._lighten(color, 1.15)
        color_dark = self._lighten(color, 0.85)
        return f"""
            PrimaryPushButton {{
                background-color: {color};
                color: white;
                border-radius: 4px;
                padding-left: 12px;
                padding-right: 24px;
            }}
            PrimaryPushButton:hover {{
                background-color: {color_light};
            }}
            PrimaryPushButton:pressed {{
                background-color: {color_dark};
            }}
            PrimaryPushButton:disabled {{
                background-color: #3d3d3d;
                color: #777;
            }}
        """

# ------------------------------------------------------------------
# Custom QScrollArea class with auto-scrolling functionality
class AutoScrollArea(ScrollArea):
    _active_scroller = None
    _MIN_SCALE = 0.2
    _MAX_SCALE = 5.0
    _SCROLL_INTERVAL_MS = 50
    _SCROLL_SPEED_FACTOR = 0.1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_margin = 50
        self.setMouseTracking(True)
        self.setWidgetResizable(True)
        # Ensure the scroll area and its content do not introduce bright
        # backgrounds when placed inside a dark CardWidget
        try:
            self.enableTransparentBackground()
        except AttributeError:
            # Older versions may not have this helper; fall back to stylesheet
            self.setStyleSheet("QScrollArea{border:none;background:transparent}")
        self._current_scale = 1.0
        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._perform_auto_scroll)
        self._mouse_pos = QPoint()
        self.viewport().installEventFilter(self)
        self.installEventFilter(self)

    # ------------------------------------------------------------------
    # Re-implement setWidget to re-apply the transparency to any newly
    # assigned widget, guaranteeing white backgrounds do not re-appear.
    # ------------------------------------------------------------------
    def setWidget(self, widget):  # type: ignore[override]
        super().setWidget(widget)
        # Ensure the viewport child is also transparent
        if widget is not None:
            widget.setStyleSheet("background: transparent")

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove:
            if self.window().isActiveWindow():
                if self._is_mouse_in_margin(QCursor.pos()):
                    if AutoScrollArea._active_scroller is None:
                        AutoScrollArea._active_scroller = self
                    if AutoScrollArea._active_scroller == self and not self._scroll_timer.isActive():
                        self._scroll_timer.start(self._SCROLL_INTERVAL_MS)
                elif AutoScrollArea._active_scroller == self:
                    AutoScrollArea._active_scroller = None
        elif event.type() == QEvent.Leave:
            if AutoScrollArea._active_scroller == self:
                AutoScrollArea._active_scroller = None
            self._scroll_timer.stop()
        
        return super().eventFilter(obj, event)

    def _is_mouse_in_margin(self, global_pos):
        local_pos = self.mapFromGlobal(global_pos)
        rect = self.rect()
        return (local_pos.y() < self.scroll_margin or
                local_pos.y() > rect.height() - self.scroll_margin or
                local_pos.x() < self.scroll_margin or
                local_pos.x() > rect.width() - self.scroll_margin)

    def _perform_auto_scroll(self):
        if AutoScrollArea._active_scroller != self:
            self._scroll_timer.stop()
            return

        if not self.widget() or not self.isVisible() or not self.window().isActiveWindow():
            self._scroll_timer.stop()
            if AutoScrollArea._active_scroller == self:
                AutoScrollArea._active_scroller = None
            return

        global_pos = QCursor.pos()
        if not self._is_mouse_in_margin(global_pos):
            self._scroll_timer.stop()
            if AutoScrollArea._active_scroller == self:
                AutoScrollArea._active_scroller = None
            return

        local_pos = self.mapFromGlobal(global_pos)
        rect = self.rect()
        v_bar = self.verticalScrollBar()
        h_bar = self.horizontalScrollBar()

        # Vertical scrolling
        if local_pos.y() < self.scroll_margin:
            delta = max(1, int((self.scroll_margin - local_pos.y()) * self._SCROLL_SPEED_FACTOR))
            v_bar.setValue(v_bar.value() - delta)
        elif local_pos.y() > rect.height() - self.scroll_margin:
            delta = max(1, int((local_pos.y() - (rect.height() - self.scroll_margin)) * self._SCROLL_SPEED_FACTOR))
            v_bar.setValue(v_bar.value() + delta)

        # Horizontal scrolling
        if local_pos.x() < self.scroll_margin:
            delta = max(1, int((self.scroll_margin - local_pos.x()) * self._SCROLL_SPEED_FACTOR))
            h_bar.setValue(h_bar.value() - delta)
        elif local_pos.x() > rect.width() - self.scroll_margin:
            delta = max(1, int((local_pos.x() - (rect.width() - self.scroll_margin)) * self._SCROLL_SPEED_FACTOR))
            h_bar.setValue(h_bar.value() + delta)


    def wheelEvent(self, event):
        # Handle wheel events for zooming when Ctrl is pressed
        if event.modifiers() & Qt.ControlModifier:
            # Check if the Ctrl key is being held down
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            # Set zoom factor to 1.1 for zoom in (scroll up) or 0.9 for zoom out (scroll down)
            self.zoom(zoom_factor)
            # Call the zoom method with the calculated zoom factor
            event.accept()
            # Accept the event to prevent it from being passed to the parent
        else:
            # If Ctrl is not pressed, handle normal scrolling
            super().wheelEvent(event)
            # Call the parent class's wheelEvent method for default scrolling behavior

    def zoom(self, factor):
        # Zoom the content of the scroll area
        if self.widget():
            previous_scale = getattr(self, "_previous_scale", 1.0)
            self._current_scale = getattr(self, "_current_scale", 1.0) * factor
            self._current_scale = max(self._MIN_SCALE, min(self._MAX_SCALE, self._current_scale))
            
            # Calculate the relative factor to apply to the current size
            relative_factor = self._current_scale / previous_scale
            self._previous_scale = self._current_scale # Update previous_scale for the next iteration

            current_size = self.widget().size()
            new_width = int(current_size.width() * relative_factor)
            new_height = int(current_size.height() * relative_factor)
            self.widget().resize(new_width, new_height)

            # Adjust scroll position to keep the center point fixed
            # Calculate the center point of the viewport
            center = QPoint(self.viewport().width() // 2, self.viewport().height() // 2)
            # Convert the center point to global coordinates
            global_center = self.mapToGlobal(center)
            # Convert the global center point to widget coordinates
            target_global = self.widget().mapFromGlobal(global_center)
            # Convert the widget coordinates back to scroll area coordinates
            target_local = self.widget().mapTo(self, target_global)

            # Ensure the target point is visible in the scroll area
            self.ensureVisible(target_local.x(), target_local.y(),
            self.viewport().width() // 2, self.viewport().height() // 2)

class CustomNavButton(PushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next_widget_on_enter = None # Renamed from custom_next_widget

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            # Allow the button's primary action (click) to occur first.
            super().keyPressEvent(event) # This should trigger the click.
            
            # After the click action, if a next_widget_on_enter is defined, navigate to it.
            if self.next_widget_on_enter:
                self.next_widget_on_enter.setFocus()
            # event.accept() # Focus change should be sufficient.
            return # Explicitly return after handling Enter/Return
        elif key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right):
            # For arrow keys, accept the event to prevent default Qt spatial navigation
            # if we don't want the button to lose focus to other UI elements.
            # This makes arrow keys do nothing on the button for custom navigation.
            event.accept()
            return

        # For other keys (like Tab), let the default QPushButton behavior occur.
        super().keyPressEvent(event)

# ------------------------------------------------------------------
# Shared helper functions for QFluentWidgets TableWidget styling
# ------------------------------------------------------------------
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView
from qfluentwidgets import setCustomStyleSheet

__all__ = [
    "apply_center_alignment",
    "set_intelligent_column_widths",
    "style_fluent_table",
]

def apply_center_alignment(table) -> None:
    """Center-align all existing items in *table*."""
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item is not None:
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

def set_intelligent_column_widths(table) -> None:
    """SIMPLIFIED - Force all columns to stretch equally"""
    try:
        if not table or table.columnCount() == 0:
            return
            
        header = table.horizontalHeader()
        
        # SIMPLE: All columns stretch to fill space equally
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        
        _log_resize_debug(f"Set all columns to stretch for {type(table).__name__}")
        
    except Exception as e:
        _log_resize_error(f"Failed to set stretch columns for {type(table).__name__}", e)

def _validate_table_for_resize(table, operation_name: str) -> bool:
    """Validate table state before resize operations"""
    try:
        if table is None:
            _log_resize_error(f"Table is None in {operation_name}", None)
            return False
            
        if not hasattr(table, 'columnCount'):
            _log_resize_error(f"Table does not have columnCount method in {operation_name}", None)
            return False
            
        if not hasattr(table, 'isVisible'):
            _log_resize_error(f"Table does not have isVisible method in {operation_name}", None)
            return False
            
        # Check if table is properly initialized
        try:
            table.columnCount()
            table.isVisible()
        except Exception as e:
            _log_resize_error(f"Table methods are not accessible in {operation_name}", e)
            return False
            
        return True
        
    except Exception as e:
        _log_resize_error(f"Validation failed for table in {operation_name}", e)
        return False

def _log_resize_debug(message: str):
    """Log debug information for resize operations"""
    try:
        print(f"[CUSTOM_WIDGETS RESIZE DEBUG] {message}")
    except Exception:
        pass  # Silently ignore logging errors

def _log_resize_error(message: str, exception: Exception):
    """Log error information for resize operations with meaningful messages"""
    try:
        if exception:
            print(f"[CUSTOM_WIDGETS RESIZE ERROR] {message}: {str(exception)}")
            # Only print traceback for unexpected errors, not validation failures
            if not isinstance(exception, (AttributeError, TypeError)):
                import traceback
                print(f"[CUSTOM_WIDGETS RESIZE ERROR] Traceback: {traceback.format_exc()}")
        else:
            print(f"[CUSTOM_WIDGETS RESIZE ERROR] {message}")
    except Exception:
        pass  # Silently ignore logging errors

def _fallback_table_resize(table) -> bool:
    """Provide graceful fallback when intelligent resize fails"""
    try:
        if not _validate_table_for_resize(table, "_fallback_table_resize"):
            return False
            
        if table.columnCount() == 0:
            return False
            
        # Simple fallback: set all columns to equal width
        header = table.horizontalHeader()
        if not header:
            return False
            
        # Get available width safely
        try:
            viewport_width = table.viewport().width() if table.viewport() else table.width()
            if viewport_width <= 0:
                viewport_width = 800  # Default fallback width
                
            available_width = max(viewport_width - 50, 300)  # Ensure minimum width
            column_count = table.columnCount()
            
            if column_count > 0:
                equal_width = max(available_width // column_count, 90)  # Minimum 90px per column for readability
                
                for col in range(column_count):
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    table.setColumnWidth(col, equal_width)
                
                header.setMinimumSectionSize(90)
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                
                _log_resize_debug(f"Applied fallback resize to {type(table).__name__}: {column_count} columns at {equal_width}px each")
                return True
                
        except Exception as e:
            _log_resize_error(f"Fallback resize calculation failed for {type(table).__name__}", e)
            return False
            
    except Exception as e:
        _log_resize_error(f"Fallback table resize failed for {type(table).__name__}", e)
        return False

def style_fluent_table(table) -> None:
    """Apply modern Fluent-compatible styling, alternate rows, header tweaks, etc."""
    # Basic properties
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setHighlightSections(False)
    table.setBorderVisible(True)
    table.setBorderRadius(8)
    table.verticalHeader().setDefaultSectionSize(45)

    header = table.horizontalHeader()
    if hasattr(header, "setTextElideMode"):
        header.setTextElideMode(Qt.ElideNone)

    # Theme-aware CSS lifted from HistoryTab
    light_qss = """
        QTableWidget {
            background-color: #ffffff;
            color: #212121;
            gridline-color: #e0e0e0;
            selection-background-color: #1976d2;
            alternate-background-color: #f8f9fa;
            border: 2px solid #d0d7de;
            border-radius: 12px;
            font-weight: 500;
        }
        QHeaderView::section {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f6f8fa, stop:1 #e1e4e8);
            color: #24292f;
            font-weight: 700;
            font-size: 14px;
            border: none;
            border-bottom: 3px solid #d0d7de;
            border-right: 1px solid #d0d7de;
            padding: 14px 18px;
            text-align: center;
        }
        QTableWidget::item {
            padding: 1px 2px;
            border: none;
            border-right: 1px solid #f0f0f0;
            text-align: center;
        }
    """
    dark_qss = """
        QTableWidget {
            background-color: #21262d;
            color: #f0f6fc;
            gridline-color: #30363d;
            selection-background-color: #0969da;
            alternate-background-color: #161b22;
            border: 2px solid #30363d;
            border-radius: 12px;
            font-weight: 500;
        }
        QHeaderView::section {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #30363d, stop:1 #21262d);
            color: #f0f6fc;
            font-weight: 700;
            font-size: 14px;
            border: none;
            border-bottom: 3px solid #30363d;
            border-right: 1px solid #30363d;
            padding: 14px 18px;
            text-align: center;
        }
        QTableWidget::item {
            padding: 1px 2px;
            border: none;
            border-right: 1px solid #30363d;
            text-align: center;
        }
    """
    setCustomStyleSheet(table, light_qss, dark_qss)

    # Apply alignment & responsive widths
    apply_center_alignment(table)
    set_intelligent_column_widths(table)

# ===================== Fluent-Widgets Progress Dialog =====================
try:
    from qfluentwidgets import IndeterminateProgressBar  # type: ignore
except ImportError:  # Graceful degradation if library missing
    IndeterminateProgressBar = None  # type: ignore


class FluentProgressDialog(QDialog):
    """A minimal frameless dialog with an indeterminate Fluent progress bar.

    It replicates the role of :class:`QProgressDialog` but with Fluent design
    aesthetics and without any buttons to press. Use it as a context manager
    or manage its lifecycle manually. Example::

        dlg = FluentProgressDialog("Uploading…", parent=self)
        dlg.show()
        # … do work …
        dlg.close()
    """

    def __init__(self, message: str = "Please wait…", parent=None):  # noqa: D401
        super().__init__(parent)
        # Frameless & translucent to feel lighter
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        # Keep window opaque so our custom background colour is visible
        # self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        # Semi-transparent dark background so the dialog stands out

        # Apply dark styling so the dialog matches global dark theme
        self.setStyleSheet(
            """
            QDialog {
                background-color: #2b2b2b;
                border: 1px solid #444444;
            }
            QLabel {
                color: #ffffff;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignCenter)

        if IndeterminateProgressBar is not None:
            self._bar = IndeterminateProgressBar(parent=self)
            self._bar.setFixedWidth(180)
            # ensure bar starts animating
            self._bar.start()
            layout.addWidget(self._bar, 0, Qt.AlignCenter)
        else:
            # Fallback: a simple Qt busy bar
            fallback = QProgressBar(self)
            fallback.setRange(0, 0)
            fallback.setFixedWidth(180)
            layout.addWidget(fallback, 0, Qt.AlignCenter)

        label = QLabel(message, self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

    # Allow ``with FluentProgressDialog(...) as dlg:`` usage
    def __enter__(self):  # noqa: D401
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # noqa: D401
        self.close()
        return False


# ===================== QFluentWidgets Smooth Scrolling Implementation =====================

from qfluentwidgets import SmoothMode

class SmoothTableWidget(TableWidget):
    """TableWidget with enhanced smooth scrolling using qfluentwidgets built-in capabilities"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure smooth scrolling using qfluentwidgets built-in functionality
        QTimer.singleShot(50, self._configure_smooth_scrolling)
        
        # Set up keyboard shortcuts for enhanced navigation
        QTimer.singleShot(100, self._setup_keyboard_shortcuts)
    
    def _configure_smooth_scrolling(self):
        """Configure smooth scrolling using qfluentwidgets built-in scroll delegate"""
        try:
            # Configure scroll sensitivity and smoothness
            if hasattr(self, 'scrollDelagate') and hasattr(self.scrollDelagate, 'verticalSmoothScroll'):
                # Don't disable smooth scrolling - keep it enabled but make it more responsive
                # self.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)
                
                # Set balanced animation parameters
                if hasattr(self.scrollDelagate.verticalSmoothScroll, 'setScrollAnimation'):
                    # Balanced animation with smooth easing
                    self.scrollDelagate.verticalSmoothScroll.setScrollAnimation(
                        duration=200,  # Balanced animation speed
                        easing=QEasingCurve.OutQuad  # Smooth easing
                    )
                
                # Configure horizontal smooth scrolling if available
                if hasattr(self.scrollDelagate, 'horizontalSmoothScroll'):
                    if hasattr(self.scrollDelagate.horizontalSmoothScroll, 'setScrollAnimation'):
                        self.scrollDelagate.horizontalSmoothScroll.setScrollAnimation(
                            duration=150,
                            easing=QEasingCurve.OutCubic
                        )
            
            # Configure scroll bar step sizes for better sensitivity
            self._configure_scroll_sensitivity()
            
            # Apply modern scroll bar styling
            self._apply_scroll_bar_styling()
            
        except Exception as e:
            print(f"Warning: Could not configure smooth scrolling: {e}")
            # Fallback to basic smooth scrolling if advanced features aren't available
            self._enable_basic_smooth_scrolling()
    
    def _configure_scroll_sensitivity(self):
        """Configure scroll bar sensitivity for balanced scrolling"""
        try:
            # Set balanced scroll steps
            v_bar = self.verticalScrollBar()
            h_bar = self.horizontalScrollBar()
            
            # Moderate single step for balanced wheel scrolling
            v_bar.setSingleStep(25)  # Balanced step size
            h_bar.setSingleStep(25)
            
            # Set reasonable page step
            v_bar.setPageStep(120)  # Moderate page steps
            h_bar.setPageStep(120)
            
        except Exception as e:
            print(f"Warning: Could not configure scroll sensitivity: {e}")
    
    def _apply_scroll_bar_styling(self):
        """Apply modern styling to scroll bars"""
        scroll_bar_style = """
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.05);
                width: 12px;
                border-radius: 6px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 120, 212, 0.7);
                border-radius: 6px;
                min-height: 20px;
                margin: 1px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 120, 212, 0.9);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(0, 120, 212, 1.0);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            
            QScrollBar:horizontal {
                background: rgba(0, 0, 0, 0.05);
                height: 12px;
                border-radius: 6px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: rgba(0, 120, 212, 0.7);
                border-radius: 6px;
                min-width: 20px;
                margin: 1px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(0, 120, 212, 0.9);
            }
            QScrollBar::handle:horizontal:pressed {
                background: rgba(0, 120, 212, 1.0);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """
        
        # Apply the styling to the table's scroll bars
        current_style = self.styleSheet()
        self.setStyleSheet(current_style + scroll_bar_style)
    
    def _enable_basic_smooth_scrolling(self):
        """Fallback smooth scrolling implementation with balanced sensitivity"""
        # Set balanced single step for good scrolling
        if hasattr(self, 'verticalScrollBar'):
            v_bar = self.verticalScrollBar()
            v_bar.setSingleStep(20)  # Balanced steps
            v_bar.setPageStep(100)   # Moderate page scrolling
        
        if hasattr(self, 'horizontalScrollBar'):
            h_bar = self.horizontalScrollBar()
            h_bar.setSingleStep(20)  # Balanced steps
            h_bar.setPageStep(100)   # Moderate page scrolling
    
    def _setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for enhanced navigation"""
        # Home/End for smooth scrolling to top/bottom
        home_shortcut = QShortcut(QKeySequence.MoveToStartOfDocument, self)
        home_shortcut.activated.connect(self.smooth_scroll_to_top)
        
        end_shortcut = QShortcut(QKeySequence.MoveToEndOfDocument, self)
        end_shortcut.activated.connect(self.smooth_scroll_to_bottom)
        
        # Page Up/Down for smooth page scrolling
        page_up_shortcut = QShortcut(QKeySequence.MoveToPreviousPage, self)
        page_up_shortcut.activated.connect(self._smooth_page_up)
        
        page_down_shortcut = QShortcut(QKeySequence.MoveToNextPage, self)
        page_down_shortcut.activated.connect(self._smooth_page_down)
    
    def smooth_scroll_to_top(self):
        """Quickly scroll to the top of the content"""
        try:
            if hasattr(self, 'scrollDelagate') and hasattr(self.scrollDelagate, 'verticalSmoothScroll'):
                # Use qfluentwidgets smooth scrolling
                self.scrollDelagate.verticalSmoothScroll.scrollTo(0)
            else:
                # Fallback to regular scrolling
                self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())
        except Exception:
            self.verticalScrollBar().setValue(self.verticalScrollBar().minimum())
    
    def smooth_scroll_to_bottom(self):
        """Quickly scroll to the bottom of the content"""
        try:
            if hasattr(self, 'scrollDelagate') and hasattr(self.scrollDelagate, 'verticalSmoothScroll'):
                # Use qfluentwidgets smooth scrolling
                max_value = self.verticalScrollBar().maximum()
                self.scrollDelagate.verticalSmoothScroll.scrollTo(max_value)
            else:
                # Fallback to regular scrolling
                self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        except Exception:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
    
    def _smooth_page_up(self):
        """Quickly scroll up by one page"""
        try:
            v_bar = self.verticalScrollBar()
            page_step = v_bar.pageStep()
            target = max(v_bar.minimum(), v_bar.value() - page_step)
            
            if hasattr(self, 'scrollDelagate') and hasattr(self.scrollDelagate, 'verticalSmoothScroll'):
                self.scrollDelagate.verticalSmoothScroll.scrollTo(target)
            else:
                v_bar.setValue(target)
        except Exception:
            v_bar = self.verticalScrollBar()
            page_step = v_bar.pageStep()
            target = max(v_bar.minimum(), v_bar.value() - page_step)
            v_bar.setValue(target)
    
    def _smooth_page_down(self):
        """Quickly scroll down by one page"""
        try:
            v_bar = self.verticalScrollBar()
            page_step = v_bar.pageStep()
            target = min(v_bar.maximum(), v_bar.value() + page_step)
            
            if hasattr(self, 'scrollDelagate') and hasattr(self.scrollDelagate, 'verticalSmoothScroll'):
                self.scrollDelagate.verticalSmoothScroll.scrollTo(target)
            else:
                v_bar.setValue(target)
        except Exception:
            v_bar = self.verticalScrollBar()
            page_step = v_bar.pageStep()
            target = min(v_bar.maximum(), v_bar.value() + page_step)
            v_bar.setValue(target)
    
    def wheelEvent(self, event):
        """Enhanced wheel event handling for balanced responsive scrolling"""
        # Get the scroll delta
        delta = event.angleDelta().y()
        
        # Calculate balanced scroll amount - not too fast, not too slow
        scroll_multiplier = 1.2  # Balanced sensitivity
        scroll_amount = int(abs(delta) / 120 * 45 * scroll_multiplier)  # Moderate responsiveness
        
        # Get the vertical scroll bar
        v_bar = self.verticalScrollBar()
        current_value = v_bar.value()
        
        # Calculate target value
        if delta > 0:
            # Scroll up
            target_value = max(v_bar.minimum(), current_value - scroll_amount)
        else:
            # Scroll down
            target_value = min(v_bar.maximum(), current_value + scroll_amount)
        
        # Try to use smooth scrolling if available
        try:
            if hasattr(self, 'scrollDelagate') and hasattr(self.scrollDelagate, 'verticalSmoothScroll'):
                # Use qfluentwidgets smooth scrolling with our target
                self.scrollDelagate.verticalSmoothScroll.scrollTo(target_value)
            else:
                # Fallback to direct scroll bar control
                v_bar.setValue(target_value)
        except Exception:
            # Final fallback
            v_bar.setValue(target_value)
        
        event.accept()
