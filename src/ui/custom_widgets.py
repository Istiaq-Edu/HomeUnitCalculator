from PyQt5.QtCore import Qt, QEvent, QPoint, QTimer
from PyQt5.QtGui import QIcon, QPainter # QFont was not used by these specific widgets but good to have
from PyQt5.QtWidgets import (
    QLineEdit, QSizePolicy, QScrollArea, QSpinBox, QAbstractSpinBox, 
    QStyleOptionSpinBox, QStyle, QPushButton, QDialog, QVBoxLayout, QLabel, QProgressBar
)
# Assuming styles.py and utils.py will be in the same directory or Python path
# If they are in subdirectories, the import paths might need adjustment, e.g., from .styles import ...
from src.ui.styles import get_line_edit_style, get_custom_spinbox_style
from src.core.utils import resource_path

# Custom QLineEdit class for improved input handling and navigation
class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        # Call the parent class constructor
        super().__init__(*args, **kwargs)
        # Remove default validator to allow any input by default
        # Validators should be set explicitly where needed (e.g., for numeric inputs)
        # self.setValidator(QRegExpValidator(QRegExp(r'^\d*$'))) # Removed
        # Set placeholder text for the input field
        # self.setPlaceholderText("Enter a number") # Removed default placeholder
        # Set tooltip for the input field
        # self.setToolTip("Input only integer values") # Removed default tooltip
        # Set size policy to expanding horizontally
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # Initialize next and previous widget references
        self.next_widget_on_enter = None # For Enter/Return key
        self.up_widget = None
        self.down_widget = None
        # self.left_widget and self.right_widget are removed as per new plan
        # Apply custom style sheet
        self.setStyleSheet(get_line_edit_style())

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
        # print(f"CustomLineEdit FocusIn: {self.objectName()} (text: '{self.text()}')") # Removed debug print
        super().focusInEvent(event)
        self.ensureWidgetVisible()

    def ensureWidgetVisible(self):
        # Ensure that this widget is visible within its parent QScrollArea
        parent = self.parent()  # Get the immediate parent of this widget
        while parent and not isinstance(parent, QScrollArea):
            # Loop until we find a QScrollArea parent or reach the top-level parent
            parent = parent.parent()  # Move up to the next parent in the hierarchy
        if parent:
            # If a QScrollArea parent is found
            parent.ensureWidgetVisible(self)  # Ensure this widget is visible within the QScrollArea


    def moveFocus(self, forward=True):
        # Define a method to move focus to the next or previous widget
        current = self.focusWidget()  # Get the currently focused widget
        if current:  # If there is a currently focused widget
            next_widget = self.findNextWidget(forward)  # Find the next widget based on the 'forward' parameter
            if next_widget:  # If a next widget is found
                next_widget.setFocus()  # Set focus to the next widget
            else:  # If no next widget is found
                print("No valid next widget found")  # Print a message indicating no valid next widget was found

    def findNextWidget(self, forward=True):
        parent_widget = self.parentWidget()
        if parent_widget is None:
            return None
        # Respect the visual / tab-order using QWidget::nextInFocusChain
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
        
        if not widgets: # Handle case where no CustomLineEdit widgets are found
            return None

        if forward:
            next_index = (current_index + 1) % len(widgets)
        else:
            next_index = (current_index - 1 + len(widgets)) % len(widgets)
        
        return widgets[next_index]

# Custom QScrollArea class with auto-scrolling functionality
class AutoScrollArea(QScrollArea):
    _MIN_SCALE = 0.2
    _MAX_SCALE = 5.0
    _SCROLL_INTERVAL_MS = 50  # Milliseconds between scroll updates
    _SCROLL_SPEED_FACTOR = 0.1 # Adjust this for faster/slower scrolling based on distance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_margin = 50
        self.setMouseTracking(True)
        self.setWidgetResizable(True)
        self._current_scale = 1.0
        self._scroll_timer = QTimer(self)
        self._scroll_timer.timeout.connect(self._perform_auto_scroll)
        self._mouse_pos = QPoint() # Store last known mouse position
        # Ensure the scroll area and its viewport receive mouse-move / leave events
        self.viewport().installEventFilter(self)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove:
            if hasattr(event, 'globalPos'):
                self._mouse_pos = event.globalPos()
            elif hasattr(event, 'globalPosition'):
                self._mouse_pos = event.globalPosition().toPoint()
            
            # Start timer if mouse is in margin and not already running
            if self._is_mouse_in_margin(self._mouse_pos) and not self._scroll_timer.isActive():
                self._scroll_timer.start(self._SCROLL_INTERVAL_MS)
            # Stop timer if mouse is outside margin and running
            elif not self._is_mouse_in_margin(self._mouse_pos) and self._scroll_timer.isActive():
                self._scroll_timer.stop()
        elif event.type() == QEvent.Leave:
            # Stop timer if mouse leaves the widget
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
        if not self.widget():
            # No widget to scroll
            return

        local_pos = self.mapFromGlobal(self._mouse_pos)
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

    def mouseMoveEvent(self, event):
        # Update stored mouse position and trigger event filter logic
        if hasattr(event, 'globalPos'):
            self._mouse_pos = event.globalPos()
        elif hasattr(event, 'globalPosition'):
            self._mouse_pos = event.globalPosition().toPoint()
        
        # Manually call eventFilter to process mouse move for auto-scrolling
        self.eventFilter(self, event)
        super().mouseMoveEvent(event)

    def closeEvent(self, event):
        """Ensures the scroll timer is stopped and deleted when the widget is closed."""
        if self._scroll_timer.isActive():
            self._scroll_timer.stop()
        self._scroll_timer.deleteLater() # Schedule for deletion
        super().closeEvent(event)

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

class CustomSpinBox(QSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.setStyleSheet(get_custom_spinbox_style())
        # Initialize pixmaps here, after QApplication is guaranteed to be available
        self._UP_ARROW_PM = QIcon(resource_path("icons/up_arrow.png")).pixmap(14, 14)
        self._DOWN_ARROW_PM = QIcon(resource_path("icons/down_arrow.png")).pixmap(14, 14)

    def stepBy(self, steps):
        super().stepBy(steps)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        option = QStyleOptionSpinBox()
        self.initStyleOption(option)
        
        # Draw the base widget
        self.style().drawComplexControl(QStyle.CC_SpinBox, option, painter, self)
        
        # Draw custom up/down arrows
        rect = self.rect()
        icon_size = 14 # This can remain as it's used for positioning
        padding = 2
        
        up_arrow = self._UP_ARROW_PM
        down_arrow = self._DOWN_ARROW_PM
        
        painter.drawPixmap(rect.right() - icon_size - padding, rect.top() + padding, up_arrow)
        painter.drawPixmap(rect.right() - icon_size - padding, rect.bottom() - icon_size - padding, down_arrow)

    def mousePressEvent(self, event):
        rect = self.rect()
        if event.x() > rect.right() - 20:
            if event.y() < rect.height() / 2:
                self.stepUp()
            else:
                self.stepDown()
            event.accept()
            return
        else:
            super().mousePressEvent(event)

class CustomNavButton(QPushButton):
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
        self.setStyleSheet(
            "background-color: rgba(0, 0, 0, 160); color: white; border-radius: 8px;"
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
