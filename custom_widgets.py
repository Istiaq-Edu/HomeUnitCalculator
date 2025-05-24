from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QPainter, QPixmap # QFont was not used by these specific widgets but good to have
from PyQt5.QtWidgets import (
    QLineEdit, QSizePolicy, QScrollArea, QSpinBox, QAbstractSpinBox, 
    QStyleOptionSpinBox, QStyle, QPushButton
)
# Assuming styles.py and utils.py will be in the same directory or Python path
# If they are in subdirectories, the import paths might need adjustment, e.g., from .styles import ...
from styles import get_line_edit_style, get_custom_spinbox_style 
from utils import resource_path

# Custom QLineEdit class for improved input handling and navigation
class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        # Call the parent class constructor
        super().__init__(*args, **kwargs)
        # Set validator to only allow integer input
        self.setValidator(QRegExpValidator(QRegExp(r'^\d*$')))
        # Set placeholder text for the input field
        self.setPlaceholderText("Enter a number")
        # Set tooltip for the input field
        self.setToolTip("Input only integer values")
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
            target_widget = self.up_widget
        elif key == Qt.Key_Down:
            target_widget = self.down_widget
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            target_widget = self.next_widget_on_enter
        
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
        # Find all CustomLineEdit widgets in the parent
        widgets = self.parent().findChildren(CustomLineEdit)
        # Get the index of the current widget in the list of CustomLineEdit widgets
        current_index = widgets.index(self)
        # Calculate the next index, wrapping around if necessary
        # If forward is True, add 1; if False, subtract 1
        # Use modulo to wrap around to the beginning or end of the list
        next_index = (current_index + (1 if forward else -1)) % len(widgets)
        # Return the widget at the calculated next index
        return widgets[next_index]

# Custom QScrollArea class with auto-scrolling functionality
class AutoScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)  # Initialize the parent QScrollArea
        self.scroll_speed = 1  # Set the default scroll speed
        self.scroll_margin = 50  # Set the margin for triggering auto-scroll
        self.setMouseTracking(True)  # Enable mouse tracking for the widget
        self.verticalScrollBar().installEventFilter(self)  # Install event filter for vertical scrollbar
        self.horizontalScrollBar().installEventFilter(self)  # Install event filter for horizontal scrollbar
        self.setWidgetResizable(True)  # Allow the scroll area to resize its widget

    def eventFilter(self, obj, event):
        # Define the event filter method to handle events for auto-scrolling
        if obj in (self.verticalScrollBar(), self.horizontalScrollBar()) and event.type() == QEvent.MouseMove:
            # Check if the event is a mouse move event on the scrollbars
            if hasattr(event, 'globalPos'):
                # If the event has a 'globalPos' attribute, use it for mouse position
                self.handleMouseMove(event.globalPos())
            elif hasattr(event, 'globalPosition'):
                # If the event has a 'globalPosition' attribute, convert it to a point and use it
                self.handleMouseMove(event.globalPosition().toPoint())
            else:
                # If neither attribute is available, print an error message
                print("Error: Unable to get mouse position from event")
        # Call the parent class's eventFilter method and return its result
        return super().eventFilter(obj, event)

    def handleMouseMove(self, global_pos):
        # Handle mouse movement for auto-scrolling
        local_pos = self.mapFromGlobal(global_pos)  # Convert global mouse position to local coordinates
        rect = self.rect()  # Get the rectangle of the widget
        v_bar = self.verticalScrollBar()  # Get the vertical scrollbar
        h_bar = self.horizontalScrollBar()  # Get the horizontal scrollbar

        # Vertical scrolling
        if local_pos.y() < self.scroll_margin:  # If mouse is near the top edge
            v_bar.setValue(v_bar.value() - self.scroll_speed)  # Scroll up
        elif local_pos.y() > rect.height() - self.scroll_margin:  # If mouse is near the bottom edge
            v_bar.setValue(v_bar.value() + self.scroll_speed)  # Scroll down

        # Horizontal scrolling
        if local_pos.x() < self.scroll_margin:  # If mouse is near the left edge
            h_bar.setValue(h_bar.value() - self.scroll_speed)  # Scroll left
        elif local_pos.x() > rect.width() - self.scroll_margin:  # If mouse is near the right edge
            h_bar.setValue(h_bar.value() + self.scroll_speed)  # Scroll right

    def mouseMoveEvent(self, event):
        # Handle mouse movement events
        if hasattr(event, 'globalPos'):
            # If the event has a 'globalPos' attribute, use it directly
            self.handleMouseMove(event.globalPos())
        elif hasattr(event, 'globalPosition'):
            # If the event has a 'globalPosition' attribute, convert it to a point
            self.handleMouseMove(event.globalPosition().toPoint())
        else:
            # If neither attribute is available, print an error message
            print("Error: Unable to get mouse position from event")
        # Call the parent class's mouseMoveEvent method
        super().mouseMoveEvent(event)

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
            # Get the current size of the widget
            current_size = self.widget().size()
            # QSize cannot be multiplied directly; build a new instance instead
            new_size = QSize(
                int(current_size.width() * factor),
                int(current_size.height() * factor),
            )
            # Resize the widget to the new size
            self.widget().resize(new_size)

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
        icon_size = 14
        padding = 2
        
        up_arrow = QIcon(resource_path("icons/up_arrow.png")).pixmap(icon_size, icon_size)
        down_arrow = QIcon(resource_path("icons/down_arrow.png")).pixmap(icon_size, icon_size)
        
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
