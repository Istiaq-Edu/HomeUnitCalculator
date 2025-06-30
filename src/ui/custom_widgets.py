from PyQt5.QtCore import Qt, QEvent, QPoint, QTimer, QSize
from PyQt5.QtGui import QIcon, QPainter, QCursor, QColor
from PyQt5.QtWidgets import (
    QSizePolicy, QDialog, QVBoxLayout, QLabel, QProgressBar
)
from qfluentwidgets import LineEdit, ScrollArea, SpinBox, PushButton

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
        self.button.setMinimumHeight(40)
        self.button.setIconSize(QSize(1, 1))  # effectively hide default icon
        self.button.setStyleSheet(
            f"PrimaryPushButton{{background-color:{color};color:white;border-radius:4px;padding-left:12px;padding-right:24px;}}"
            f"PrimaryPushButton:hover{{background-color:{self._lighten(color, 1.15)}}}"
            f"PrimaryPushButton:pressed{{background-color:{self._lighten(color, 0.85)}}}"
            f"PrimaryPushButton:disabled{{background-color:#3d3d3d;color:#777;}}"
        )

        self._icon_label = BodyLabel()
        # FluentIcon returns QIcon via .icon() method
        self._icon_label.setPixmap(self._icon.icon().pixmap(20, 20))
        self._icon_label.setFixedSize(26, 26)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setStyleSheet(f"background-color:{color};border-top-left-radius:4px;border-bottom-left-radius:4px;")

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
        c = QColor(color_str)
        h, s, v, a = c.getHsvF()
        v = max(0, min(v * factor, 1))
        c.setHsvF(h, s, v, a)
        return c.name()

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
