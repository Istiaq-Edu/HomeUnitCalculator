from PyQt5.QtCore import (
    Qt,
    QEvent,
    QPoint,
    QTimer,
    QSize,
    QPropertyAnimation,
    QEasingCurve,
    pyqtSignal,
)
from PyQt5.QtGui import QIcon, QPainter, QCursor, QColor, QKeySequence, QPen, QLinearGradient, QFontMetrics
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import (
    QSizePolicy,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollBar,
    QAbstractScrollArea,
    QShortcut,
    QApplication,
    QWidget,
    QDesktopWidget,
    QToolTip,
)
from qfluentwidgets import (
    LineEdit,
    ScrollArea,
    SpinBox,
    PushButton,
    TableWidget,
    SmoothMode,
    BodyLabel,
    CaptionLabel,
    IconWidget,
    FluentIcon,
    PrimaryPushButton,
)

from src.core.utils import resource_path


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    s = str(hex_color or "").strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    if len(s) != 6:
        return 0, 120, 212
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except Exception:
        return 0, 120, 212


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
        self.next_widget_on_enter = None  # For Enter/Return key
        self.up_widget = None
        self.down_widget = None

    def keyPressEvent(self, event):
        key = event.key()

        if key == Qt.Key_Left or key == Qt.Key_Right:
            super().keyPressEvent(
                event
            )  # Default QLineEdit behavior for Left/Right arrows
            return

        target_widget = None
        if key == Qt.Key_Up:
            target_widget = self.up_widget or self.findNextWidget(forward=False)
        elif key == Qt.Key_Down:
            target_widget = self.down_widget or self.findNextWidget(forward=True)
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            target_widget = self.next_widget_on_enter or self.findNextWidget(
                forward=True
            )

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

    def __init__(
        self, icon: FluentIcon, text: str, color: str = "#2e7d32", parent=None
    ):
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
        self._icon_label.setStyleSheet(
            f"background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {{{self._lighten(color, 1.1)}}}, stop:1 {{{self._lighten(color, 0.9)}}}); border-top-left-radius:4px;border-bottom-left-radius:4px;"
        )

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
        self._icon_label.setPixmap(
            self._icon.icon().pixmap(size.width(), size.height())
        )

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
                    if (
                        AutoScrollArea._active_scroller == self
                        and not self._scroll_timer.isActive()
                    ):
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
        return (
            local_pos.y() < self.scroll_margin
            or local_pos.y() > rect.height() - self.scroll_margin
            or local_pos.x() < self.scroll_margin
            or local_pos.x() > rect.width() - self.scroll_margin
        )

    def _perform_auto_scroll(self):
        if AutoScrollArea._active_scroller != self:
            self._scroll_timer.stop()
            return

        if (
            not self.widget()
            or not self.isVisible()
            or not self.window().isActiveWindow()
        ):
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
            delta = max(
                1, int((self.scroll_margin - local_pos.y()) * self._SCROLL_SPEED_FACTOR)
            )
            v_bar.setValue(v_bar.value() - delta)
        elif local_pos.y() > rect.height() - self.scroll_margin:
            delta = max(
                1,
                int(
                    (local_pos.y() - (rect.height() - self.scroll_margin))
                    * self._SCROLL_SPEED_FACTOR
                ),
            )
            v_bar.setValue(v_bar.value() + delta)

        # Horizontal scrolling
        if local_pos.x() < self.scroll_margin:
            delta = max(
                1, int((self.scroll_margin - local_pos.x()) * self._SCROLL_SPEED_FACTOR)
            )
            h_bar.setValue(h_bar.value() - delta)
        elif local_pos.x() > rect.width() - self.scroll_margin:
            delta = max(
                1,
                int(
                    (local_pos.x() - (rect.width() - self.scroll_margin))
                    * self._SCROLL_SPEED_FACTOR
                ),
            )
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
            self._current_scale = max(
                self._MIN_SCALE, min(self._MAX_SCALE, self._current_scale)
            )

            # Calculate the relative factor to apply to the current size
            relative_factor = self._current_scale / previous_scale
            self._previous_scale = (
                self._current_scale
            )  # Update previous_scale for the next iteration

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
            self.ensureVisible(
                target_local.x(),
                target_local.y(),
                self.viewport().width() // 2,
                self.viewport().height() // 2,
            )


class CustomNavButton(PushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next_widget_on_enter = None  # Renamed from custom_next_widget

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key_Return, Qt.Key_Enter):
            # Allow the button's primary action (click) to occur first.
            super().keyPressEvent(event)  # This should trigger the click.

            # After the click action, if a next_widget_on_enter is defined, navigate to it.
            if self.next_widget_on_enter:
                self.next_widget_on_enter.setFocus()
            # event.accept() # Focus change should be sufficient.
            return  # Explicitly return after handling Enter/Return
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
        _log_resize_error(
            f"Failed to set stretch columns for {type(table).__name__}", e
        )


def _validate_table_for_resize(table, operation_name: str) -> bool:
    """Validate table state before resize operations"""
    try:
        if table is None:
            _log_resize_error(f"Table is None in {operation_name}", None)
            return False

        if not hasattr(table, "columnCount"):
            _log_resize_error(
                f"Table does not have columnCount method in {operation_name}", None
            )
            return False

        if not hasattr(table, "isVisible"):
            _log_resize_error(
                f"Table does not have isVisible method in {operation_name}", None
            )
            return False

        # Check if table is properly initialized
        try:
            table.columnCount()
            table.isVisible()
        except Exception as e:
            _log_resize_error(
                f"Table methods are not accessible in {operation_name}", e
            )
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

                print(
                    f"[CUSTOM_WIDGETS RESIZE ERROR] Traceback: {traceback.format_exc()}"
                )
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
            viewport_width = (
                table.viewport().width() if table.viewport() else table.width()
            )
            if viewport_width <= 0:
                viewport_width = 800  # Default fallback width

            available_width = max(viewport_width - 50, 300)  # Ensure minimum width
            column_count = table.columnCount()

            if column_count > 0:
                equal_width = max(
                    available_width // column_count, 90
                )  # Minimum 90px per column for readability

                for col in range(column_count):
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    table.setColumnWidth(col, equal_width)

                header.setMinimumSectionSize(90)
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

                _log_resize_debug(
                    f"Applied fallback resize to {type(table).__name__}: {column_count} columns at {equal_width}px each"
                )
                return True

        except Exception as e:
            _log_resize_error(
                f"Fallback resize calculation failed for {type(table).__name__}", e
            )
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


class FluentProgressDialog(QDialog):
    """A simple progress dialog with Fluent Design aesthetics.

    Features:
    - Vertical layout with text and progress bar
    - Modern purple accent color
    - Rounded corners
    - Centered on screen

    Example::

        dlg = FluentProgressDialog("Uploading…", parent=self)
        dlg.show()
        # … do work …
        dlg.close()
    """

    def __init__(self, message: str = "Please wait…", parent=None):  # noqa: D401
        super().__init__(parent)

        # Frameless with translucent background for modern look
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)

        # Main container with rounded corners
        container = QWidget(self)
        container.setObjectName("progressContainer")
        container.setStyleSheet("""
            QWidget#progressContainer {
                background-color: #2b2b2b;
                border: 2px solid #6C5CE7;
                border-radius: 8px;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        # Container layout - VERTICAL with centered content
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignCenter)

        # Message label with modern styling - centered (TEXT ON TOP)
        label = QLabel(message, self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        layout.addWidget(label)

        # Progress bar
        self._bar = QProgressBar(container)
        self._bar.setRange(0, 0)  # Indeterminate mode
        self._bar.setFixedSize(280, 6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #3d3d3d;
            }
            QProgressBar::chunk {
                background-color: #6C5CE7;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._bar, 0, Qt.AlignCenter)

        # Set minimum width for the container
        container.setMinimumWidth(350)

        # Adjust size to content
        container.adjustSize()
        self.adjustSize()

    def showEvent(self, event):
        """Center the dialog when shown."""
        super().showEvent(event)
        # Center on screen
        screen = QApplication.desktop().screenGeometry()
        dialog_rect = self.geometry()
        x = (screen.width() - dialog_rect.width()) // 2
        y = (screen.height() - dialog_rect.height()) // 2
        self.move(x, y)

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
            if hasattr(self, "scrollDelagate") and hasattr(
                self.scrollDelagate, "verticalSmoothScroll"
            ):
                # Don't disable smooth scrolling - keep it enabled but make it more responsive
                # self.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)

                # Set balanced animation parameters
                if hasattr(
                    self.scrollDelagate.verticalSmoothScroll, "setScrollAnimation"
                ):
                    # Balanced animation with smooth easing
                    self.scrollDelagate.verticalSmoothScroll.setScrollAnimation(
                        duration=200,  # Balanced animation speed
                        easing=QEasingCurve.OutQuad,  # Smooth easing
                    )

                # Configure horizontal smooth scrolling if available
                if hasattr(self.scrollDelagate, "horizontalSmoothScroll"):
                    if hasattr(
                        self.scrollDelagate.horizontalSmoothScroll, "setScrollAnimation"
                    ):
                        self.scrollDelagate.horizontalSmoothScroll.setScrollAnimation(
                            duration=150, easing=QEasingCurve.OutCubic
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
        if hasattr(self, "verticalScrollBar"):
            v_bar = self.verticalScrollBar()
            v_bar.setSingleStep(20)  # Balanced steps
            v_bar.setPageStep(100)  # Moderate page scrolling

        if hasattr(self, "horizontalScrollBar"):
            h_bar = self.horizontalScrollBar()
            h_bar.setSingleStep(20)  # Balanced steps
            h_bar.setPageStep(100)  # Moderate page scrolling

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
            if hasattr(self, "scrollDelagate") and hasattr(
                self.scrollDelagate, "verticalSmoothScroll"
            ):
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
            if hasattr(self, "scrollDelagate") and hasattr(
                self.scrollDelagate, "verticalSmoothScroll"
            ):
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

            if hasattr(self, "scrollDelagate") and hasattr(
                self.scrollDelagate, "verticalSmoothScroll"
            ):
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

            if hasattr(self, "scrollDelagate") and hasattr(
                self.scrollDelagate, "verticalSmoothScroll"
            ):
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
        if getattr(self, "_disable_smooth_wheel", False):
            return super().wheelEvent(event)

        # Get the scroll delta
        delta = event.angleDelta().y()

        # Calculate balanced scroll amount - not too fast, not too slow
        scroll_multiplier = 1.2  # Balanced sensitivity
        scroll_amount = int(
            abs(delta) / 120 * 45 * scroll_multiplier
        )  # Moderate responsiveness

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
            if hasattr(self, "scrollDelagate") and hasattr(
                self.scrollDelagate, "verticalSmoothScroll"
            ):
                # Use qfluentwidgets smooth scrolling with our target
                self.scrollDelagate.verticalSmoothScroll.scrollTo(target_value)
            else:
                # Fallback to direct scroll bar control
                v_bar.setValue(target_value)
        except Exception:
            # Final fallback
            v_bar.setValue(target_value)

        event.accept()


class SummaryKpiCard(QWidget):
    """Modern KPI card with gradient background, icon, title, and value."""

    def __init__(self, title: str, icon, accent_color: str, parent=None):
        super().__init__(parent)
        self._accent_color = accent_color
        self._icon = icon

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedHeight(100)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        r, g, b = _hex_to_rgb(accent_color)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Top row: icon + title
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Icon with gradient background
        icon_container = QWidget()
        icon_container.setFixedSize(28, 28)
        icon_container.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba({r}, {g}, {b}, 40),
                stop:1 rgba({r}, {g}, {b}, 20));
            border-radius: 6px;
            border: 1px solid rgba({r}, {g}, {b}, 30);
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(2, 2, 2, 2)
        icon_label = IconWidget(icon, icon_container)
        icon_label.setFixedSize(20, 20)
        icon_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        top_row.addWidget(icon_container)

        # Title
        self._kpi_title_label = CaptionLabel(title)
        self._kpi_title_label.setTextColor(QColor(160, 160, 160))
        title_font = self._kpi_title_label.font()
        title_font.setPointSize(10)
        title_font.setWeight(50)
        self._kpi_title_label.setFont(title_font)
        top_row.addWidget(self._kpi_title_label, 1)

        layout.addLayout(top_row)

        # Value
        self._kpi_value_label = BodyLabel("---")
        self._kpi_value_label.setTextColor(QColor(255, 255, 255))
        value_font = self._kpi_value_label.font()
        value_font.setPointSize(18)
        value_font.setBold(True)
        self._kpi_value_label.setFont(value_font)
        layout.addWidget(self._kpi_value_label, 1)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background with gradient
        r, g, b = _hex_to_rgb(self._accent_color)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(r, g, b, 15))
        gradient.setColorAt(1, QColor(r, g, b, 5))

        painter.setPen(QPen(QColor(r, g, b, 30), 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

        painter.end()


class AnimatedNumberLabel(BodyLabel):
    """Label that smoothly animates between numeric values."""

    def __init__(self, fmt_fn=None, parent=None):
        super().__init__(parent)
        self._fmt_fn = fmt_fn or (lambda v: f"{v:,.0f}")
        self._current_value = 0.0
        self._animation = None

    def animate_to(self, target: float, duration_ms: int = 600):
        from PyQt5.QtCore import QVariantAnimation, QEasingCurve

        if self._animation and self._animation.state() == QVariantAnimation.Running:
            self._animation.stop()

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(self._current_value)
        self._animation.setEndValue(target)
        self._animation.setDuration(duration_ms)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._on_value_changed)
        self._animation.finished.connect(lambda: self._on_finished(target))
        self._animation.start()

    def _on_value_changed(self, value):
        self._current_value = value
        self.setText(self._fmt_fn(value))

    def _on_finished(self, target):
        self._current_value = target
        self.setText(self._fmt_fn(target))


class ShimmerPlaceholder(QWidget):
    """Skeleton loader with pulsing shimmer animation."""

    def __init__(self, min_height: int = 72, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(min_height)
        self._shimmer_offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_shimmer)

    def set_active(self, active: bool):
        if active:
            self._shimmer_offset = 0.0
            self._timer.start(33)
            self.show()
        else:
            self._timer.stop()
            self.hide()

    def _advance_shimmer(self):
        self._shimmer_offset += 0.02
        if self._shimmer_offset > 1.0:
            self._shimmer_offset = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(43, 43, 43))
        painter.drawRoundedRect(self.rect(), 12, 12)

        # Shimmer band
        w = self.width()
        band_width = int(w * 0.3)
        band_x = int(self._shimmer_offset * (w + band_width)) - band_width

        gradient = QLinearGradient(band_x, 0, band_x + band_width, 0)
        gradient.setColorAt(0.0, QColor(43, 43, 43))
        gradient.setColorAt(0.5, QColor(58, 58, 58))
        gradient.setColorAt(1.0, QColor(43, 43, 43))

        painter.setBrush(gradient)
        painter.drawRoundedRect(self.rect(), 12, 12)
        painter.end()


class EmptyStateWidget(QWidget):
    """Centered placeholder for no-data scenarios."""

    def __init__(self, icon, message: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon_widget = IconWidget(icon, self)
        icon_widget.setFixedSize(48, 48)
        layout.addWidget(icon_widget, 0, Qt.AlignCenter)

        msg_label = BodyLabel(message)
        msg_label.setTextColor(QColor(255, 255, 255))
        msg_font = msg_label.font()
        msg_font.setPointSize(16)
        msg_font.setBold(True)
        msg_label.setFont(msg_font)
        layout.addWidget(msg_label, 0, Qt.AlignCenter)

        if subtitle:
            sub_label = CaptionLabel(subtitle)
            sub_label.setTextColor(QColor(160, 160, 160))
            layout.addWidget(sub_label, 0, Qt.AlignCenter)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 13), 1))
        painter.setBrush(QColor(43, 43, 43, 200))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)
        painter.end()


class SimpleBarChartWidget(QWidget):
    """Custom-painted bar chart fallback when PyQt5.QtChart is unavailable."""

    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels = self.MONTHS[:]
        self._values = [0.0] * 12
        self._tooltips = [""] * 12
        self._bar_color = QColor(0, 120, 212)
        self._hover_index = None
        self._bar_rects = []
        self._grouped_data = None
        self._grouped_colors = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)
        self.setMouseTracking(True)

    def set_data(self, labels, values, tooltips=None, bar_color=None):
        self._labels = list(labels)[:12]
        self._values = [float(v or 0.0) for v in values][:12]
        self._tooltips = (list(tooltips) if tooltips else [""] * len(self._values))[:12]
        if bar_color:
            self._bar_color = QColor(bar_color)
        self._grouped_data = None
        self._grouped_colors = None
        self.update()

    def set_grouped_data(self, labels, grouped_dict, tooltips=None, color_list=None):
        self._labels = list(labels)[:12]
        self._grouped_data = grouped_dict
        self._grouped_colors = color_list or [
            QColor(73, 198, 255), QColor(185, 122, 255),
            QColor(159, 226, 157), QColor(255, 184, 107),
            QColor(255, 107, 107), QColor(0, 120, 212),
        ]
        self._tooltips = (list(tooltips) if tooltips else [""] * 12)[:12]
        self._values = [0.0] * 12
        self.update()

    def _hit_test(self, pos):
        for i, rect in enumerate(self._bar_rects):
            if rect.contains(pos):
                return i
        return None

    def mouseMoveEvent(self, event):
        idx = self._hit_test(event.pos())
        if idx != self._hover_index:
            self._hover_index = idx
            if idx is not None and idx < len(self._tooltips) and self._tooltips[idx]:
                QToolTip.showText(QCursor.pos(), self._tooltips[idx], self)
            else:
                QToolTip.hideText()
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        from qfluentwidgets import isDarkTheme

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(14, 12, -12, -12)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        dark = isDarkTheme()
        bg = QColor(39, 39, 39) if dark else QColor(250, 250, 250)
        grid = QColor(80, 80, 80) if dark else QColor(210, 210, 210)
        text = QColor(230, 230, 230) if dark else QColor(30, 30, 30)

        painter.fillRect(rect, bg)

        left_pad = 88
        bottom_pad = 36
        top_pad = 4
        plot = rect.adjusted(left_pad, top_pad, -8, -bottom_pad)

        if plot.width() <= 0 or plot.height() <= 0:
            return

        # Grid lines
        painter.setPen(QPen(grid, 1))
        for i in range(5):
            y = plot.top() + int(i * plot.height() / 4)
            painter.drawLine(plot.left(), y, plot.right(), y)

        n = len(self._labels)
        if n <= 0:
            painter.setPen(text)
            painter.drawText(plot, Qt.AlignCenter, "No data")
            return

        # Compute max value
        all_values = list(self._values)
        if self._grouped_data:
            for vals in self._grouped_data.values():
                all_values.extend([float(v or 0.0) for v in vals])
        max_v = max(all_values) if all_values else 1.0
        if max_v <= 0:
            max_v = 1.0

        # Bar layout
        bar_spacing = max(4, plot.width() // (n * 3))
        total_bar_width = plot.width() - bar_spacing * (n + 1)
        bar_width = max(8, total_bar_width // max(1, n))

        self._bar_rects = []

        if self._grouped_data:
            # Grouped bars
            groups = list(self._grouped_data.values())
            num_groups = len(groups)
            if num_groups > 0:
                single_bar_width = max(4, bar_width // num_groups)
                for i in range(n):
                    x_base = plot.left() + bar_spacing + i * (bar_width + bar_spacing)
                    for g_idx, group_values in enumerate(groups):
                        val = float(group_values[i] or 0.0) if i < len(group_values) else 0.0
                        bar_h = int((val / max_v) * plot.height())
                        x = x_base + g_idx * single_bar_width
                        y = plot.bottom() - bar_h
                        bar_rect = QRect(x, y, single_bar_width - 2, bar_h)
                        self._bar_rects.append(bar_rect)
                        color = self._grouped_colors[g_idx % len(self._grouped_colors)]
                        if self._hover_index == i:
                            color = color.lighter(120)
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(color)
                        painter.drawRoundedRect(bar_rect, 2, 2)
        else:
            # Single bars
            for i in range(n):
                val = float(self._values[i] or 0.0)
                bar_h = int((val / max_v) * plot.height())
                x = plot.left() + bar_spacing + i * (bar_width + bar_spacing)
                y = plot.bottom() - bar_h
                bar_rect = QRect(x, y, bar_width, bar_h)
                self._bar_rects.append(bar_rect)

                color = self._bar_color
                if self._hover_index == i:
                    color = color.lighter(120)
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(bar_rect, 3, 3)

        # X-axis labels
        painter.setPen(QPen(text, 1))
        fm = QFontMetrics(painter.font())
        for i, label in enumerate(self._labels[:n]):
            short = label[:3]
            x = plot.left() + bar_spacing + i * (bar_width + bar_spacing) + bar_width // 2
            w = fm.horizontalAdvance(short)
            painter.drawText(x - w // 2, plot.bottom() + fm.ascent() + 10, short)

        # Y-axis labels
        for i in range(5):
            frac = 1.0 - (i / 4.0)
            val = frac * max_v
            y = plot.top() + int(i * plot.height() / 4)
            s = f"TK {val:,.0f}"
            w = fm.horizontalAdvance(s)
            painter.drawText(plot.left() - w - 8, y + int(fm.ascent() / 2), s)

        painter.end()


# ==================================================================
# CollapsibleSection — expandable container with frosted glass header
# ==================================================================
class CollapsibleSection(QWidget):
    """A collapsible section with a clickable header and toggleable content area.

    Uses frosted glass styling on the header. Content widget is shown/hidden
    on header click. Starts expanded by default.
    """

    def __init__(self, title: str, content_widget: QWidget, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._expanded = expanded
        self._content_widget = content_widget

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        self._header = QWidget()
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.setFixedHeight(44)
        self._header.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
            }
            QWidget:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)

        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(8)

        self._title_label = BodyLabel(title)
        self._title_label.setStyleSheet(
            "font-size: 15px; font-weight: 600; color: #ffffff; background: transparent; border: none;"
        )

        self._chevron = IconWidget(FluentIcon.CHEVRON_DOWN_MED if expanded else FluentIcon.CHEVRON_RIGHT)
        self._chevron.setFixedSize(16, 16)
        self._chevron.setStyleSheet("background: transparent; border: none;")

        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._chevron)

        self._header.mousePressEvent = lambda _: self._toggle()

        root.addWidget(self._header)

        # ── Content ──
        self._content_widget.setVisible(expanded)
        root.addWidget(self._content_widget)

    def _toggle(self):
        self._expanded = not self._expanded
        self._content_widget.setVisible(self._expanded)
        self._chevron.setIcon(FluentIcon.CHEVRON_DOWN_MED if self._expanded else FluentIcon.CHEVRON_RIGHT)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._content_widget.setVisible(expanded)
        self._chevron.setIcon(FluentIcon.CHEVRON_DOWN_MED if expanded else FluentIcon.CHEVRON_RIGHT)

    def is_expanded(self) -> bool:
        return self._expanded


# ==================================================================
# KpiChipBar — horizontal row of color-coded KPI chips
# ==================================================================
class KpiChipBar(QWidget):
    """A horizontal bar of KPI chips with frosted glass styling.

    Each chip has an emoji icon, label, and value. The container uses
    glass-morphism with a subtle shadow.

    Usage:
        bar = KpiChipBar()
        bar.set_kpis([
            {"emoji": "🔢", "label": "Total Units", "value": "N/A", "color": "#4FC3F7"},
            ...
        ])
        bar.update_kpi(0, "450")
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chips: list = []
        self._value_labels: list = []

        self._root = QHBoxLayout(self)
        self._root.setContentsMargins(12, 10, 12, 10)
        self._root.setSpacing(8)

        self.setStyleSheet("""
            KpiChipBar {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
        """)

        # Shadow
        try:
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 60))
            self.setGraphicsEffect(shadow)
        except Exception:
            pass

    def set_kpis(self, kpis: list):
        """Set KPI definitions. Each dict: {emoji, label, value, color}."""
        # Clear existing
        while self._root.count():
            item = self._root.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._chips.clear()
        self._value_labels.clear()

        for kpi in kpis:
            chip = self._create_chip(kpi["emoji"], kpi["label"], kpi.get("value", "N/A"), kpi["color"])
            self._chips.append(chip)
            self._root.addWidget(chip)

    def _create_chip(self, emoji: str, label: str, value: str, color: str) -> QWidget:
        chip = QWidget()
        r, g, b = _hex_to_rgb(color)
        chip.setStyleSheet(f"""
            QWidget {{
                background-color: rgba({r}, {g}, {b}, 0.14);
                border: 1px solid rgba({r}, {g}, {b}, 0.35);
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(chip)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        emoji_label = BodyLabel(emoji)
        emoji_label.setStyleSheet("font-size: 16px; background: transparent; border: none;")

        name_label = CaptionLabel(label)
        name_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.7); "
            f"background: transparent; border: none;"
        )

        value_label = BodyLabel(value)
        value_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {color}; "
            f"background: transparent; border: none;"
        )

        layout.addWidget(emoji_label)
        layout.addWidget(name_label)
        layout.addWidget(value_label)

        self._value_labels.append(value_label)
        return chip

    def update_kpi(self, index: int, value: str):
        """Update the value of a KPI chip by index."""
        if 0 <= index < len(self._value_labels):
            self._value_labels[index].setText(value)
