import sys
import json
from datetime import datetime as dt_class # Changed import for clarity
import functools # Added import 
from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor, QKeySequence, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame, QShortcut,
    QAbstractSpinBox, QStyleOptionSpinBox, QStyle, QDesktopWidget, QSizePolicy, QDialog, QAbstractItemView # Added QDialog and QAbstractItemView
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import csv
import os
import traceback # Added for detailed error logging
from supabase import create_client, Client
from postgrest.exceptions import APIError
from datetime import datetime
from db_manager import DBManager # Import DBManager
from encryption_utils import EncryptionUtil # Import EncryptionUtil
from key_manager import get_or_create_key # Import get_or_create_key
from styles import (
    get_stylesheet, get_header_style, get_group_box_style,
    get_line_edit_style, get_button_style, get_results_group_style,
    get_room_group_style, get_month_info_style, get_table_style, get_label_style, get_custom_spinbox_style,
    get_room_selection_style, get_result_title_style, get_result_value_style # Added new style imports
)
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
            # Calculate the new size by multiplying the current size with the zoom factor
            new_size = current_size * factor
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

# Dialog for Editing Records
class EditRecordDialog(QDialog):
    def __init__(self, record_id, main_data, room_data_list, parent=None):
        super().__init__(parent)
        self.record_id = record_id # Store the ID of the record being edited
        self.supabase = parent.supabase # Get supabase client from parent
        self.room_edit_widgets = [] # To store references to room input widgets
        self.meter_diff_edit_widgets = [] # To store references to meter/diff input widgets
        
        self.setWindowTitle("Edit Calculation Record")
        self.setMinimumWidth(600) 
        self.setMinimumHeight(500) # Give more vertical space
        self.setStyleSheet(get_stylesheet()) 

        # Layouts
        main_layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()

        # Display Month/Year (non-editable)
        self.month_year_label = QLabel(f"Record for: {main_data.get('month', '')} {main_data.get('year', '')}")
        main_layout.addWidget(self.month_year_label)

        # --- Main Calculation Fields ---
        main_group = QGroupBox("Main Calculation Data")
        main_scroll_area = AutoScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_widget = QWidget()
        main_group_layout = QFormLayout(main_scroll_widget)
        main_group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow) # Allow fields to expand
        main_scroll_area.setWidget(main_scroll_widget)
        main_group_vbox = QVBoxLayout(main_group)
        main_group_vbox.addWidget(main_scroll_area)
        
        # Create the default meter/diff entries first (for backward compatibility)
        self.meter1_edit = CustomLineEdit(); self.meter1_edit.setObjectName("dialog_meter1_edit")
        self.meter2_edit = CustomLineEdit(); self.meter2_edit.setObjectName("dialog_meter2_edit")
        self.meter3_edit = CustomLineEdit(); self.meter3_edit.setObjectName("dialog_meter3_edit")
        self.diff1_edit = CustomLineEdit(); self.diff1_edit.setObjectName("dialog_diff1_edit")
        self.diff2_edit = CustomLineEdit(); self.diff2_edit.setObjectName("dialog_diff2_edit")
        self.diff3_edit = CustomLineEdit(); self.diff3_edit.setObjectName("dialog_diff3_edit")
        
        # Determine the number of meter/diff pairs needed
        # First check for the default pairs (meter1, meter2, meter3, diff1, diff2, diff3)
        meter_values = [
            main_data.get("meter1_reading", "") or "",
            main_data.get("meter2_reading", "") or "",
            main_data.get("meter3_reading", "") or ""
        ]
        diff_values = [
            main_data.get("diff1", "") or "",
            main_data.get("diff2", "") or "",
            main_data.get("diff3", "") or ""
        ]
        
        # Check for extra meter/diff readings in JSON format
        extra_meter_readings = main_data.get("extra_meter_readings", None)
        extra_diff_readings = main_data.get("extra_diff_readings", None)
        
        # Parse extra values if they exist
        if extra_meter_readings:
            try:
                extra_meters = json.loads(extra_meter_readings)
                if isinstance(extra_meters, list):
                    meter_values.extend(extra_meters)
            except Exception as e:
                print(f"Error parsing extra meter readings in dialog: {e}")
        
        if extra_diff_readings:
            try:
                extra_diffs = json.loads(extra_diff_readings)
                if isinstance(extra_diffs, list):
                    diff_values.extend(extra_diffs)
            except Exception as e:
                print(f"Error parsing extra diff readings in dialog: {e}")
        
        # Determine total number of pairs needed
        num_pairs = max(len(meter_values), len(diff_values))
        
        # Create meter/diff entries for each pair
        for i in range(num_pairs):
            # For the first three pairs, use the pre-defined widgets for backward compatibility
            if i < 3:
                meter_edit = [self.meter1_edit, self.meter2_edit, self.meter3_edit][i]
                diff_edit = [self.diff1_edit, self.diff2_edit, self.diff3_edit][i]
            else:
                # Create new custom widgets for additional pairs
                meter_edit = CustomLineEdit()
                meter_edit.setObjectName(f"dialog_meter{i+1}_edit")
                diff_edit = CustomLineEdit()
                diff_edit.setObjectName(f"dialog_diff{i+1}_edit")
            
            # Add the row to the form layout
            main_group_layout.addRow(f"Meter {i+1} Reading:", meter_edit)
            main_group_layout.addRow(f"Difference {i+1}:", diff_edit)
            
            # Store in the widgets list
            self.meter_diff_edit_widgets.append({
                'meter_edit': meter_edit,
                'diff_edit': diff_edit,
                'index': i
            })
        
        # Add additional amount at the end
        self.additional_amount_edit = CustomLineEdit()
        self.additional_amount_edit.setObjectName("dialog_additional_amount_edit")
        self.additional_amount_edit.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$'))) # Allow decimals
        main_group_layout.addRow("Additional Amount:", self.additional_amount_edit)
        
        main_layout.addWidget(main_group)

        # --- Room Calculation Fields ---
        self.rooms_group = QGroupBox("Room Data") 
        rooms_main_layout = QVBoxLayout(self.rooms_group) # Main layout for the group

        # Scroll Area for room inputs
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        self.rooms_edit_layout = QVBoxLayout(scroll_content_widget) # Layout inside scroll area
        scroll_area.setWidget(scroll_content_widget)
        rooms_main_layout.addWidget(scroll_area) # Add scroll area to group box

        # Dynamically create room edit sections
        for i, room_data in enumerate(room_data_list):
            room_name = room_data.get('room_name', 'Unknown Room')
            room_edit_group = QGroupBox(room_name)
            room_edit_group.setStyleSheet(get_room_group_style()) # Reuse style
            room_edit_form_layout = QFormLayout(room_edit_group)
            room_edit_form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

            present_edit = CustomLineEdit()
            present_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_present")
            previous_edit = CustomLineEdit()
            previous_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_previous")
            
            # Store original room ID if needed for updates (assuming 'id' exists in room_data)
            room_id = room_data.get('id') 

            room_edit_form_layout.addRow("Present Reading:", present_edit)
            room_edit_form_layout.addRow("Previous Reading:", previous_edit)

            self.rooms_edit_layout.addWidget(room_edit_group)
            self.room_edit_widgets.append({
                "room_id": room_id, # Store original room ID
                "name": room_name, # Store name for saving
                "present_edit": present_edit,
                "previous_edit": previous_edit
            })
            
        if not room_data_list:
             no_rooms_label = QLabel("No room data associated with this record.")
             self.rooms_edit_layout.addWidget(no_rooms_label)

        main_layout.addWidget(self.rooms_group)


        # --- Buttons ---
        self.save_button = CustomNavButton("Save Changes")
        self.cancel_button = QPushButton("Cancel") # Cancel button does not need custom navigation
        self.save_button.setStyleSheet(get_button_style())
        self.cancel_button.setStyleSheet("background-color: #6c757d; color: white; border: none; border-radius: 4px; padding: 10px; font-weight: bold; font-size: 14px;") 

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

        # --- Populate Fields ---
        self.populate_data(main_data, room_data_list)

        # --- Connections ---
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.reject) # Close dialog without saving

        # --- Setup Navigation ---
        self._setup_navigation_edit_dialog()
        
    # This method sets up keyboard navigation for the edit dialog fields 
    # It defines the tab order and arrow key navigation between all input fields
    # The implementation at line ~487 is the active version

    def _setup_navigation_edit_dialog(self):
        """Set up keyboard navigation for edit dialog fields.
        
        This method configures the tab order and arrow key navigation between
        all input fields in the edit dialog. It creates a navigation sequence that includes:
        1. All meter/diff input fields first
        2. The additional amount field
        3. All room input fields (present/previous pairs)
        
        Navigation links both Enter/Return key progression and Up/Down arrow keys.
        """
        # Get all meter/diff fields
        meter_diff_edits = []
        for pair in self.meter_diff_edit_widgets:
            meter_edit = pair.get('meter_edit')
            diff_edit = pair.get('diff_edit')
            if meter_edit and diff_edit:
                meter_diff_edits.append(meter_edit)
                meter_diff_edits.append(diff_edit)
        
        # Additional amount edit and save button
        aa = self.additional_amount_edit
        save_btn = self.save_button

        # --- Clear all existing navigation links first ---
        all_line_edits_in_dialog = meter_diff_edits + [aa]
        for room_set in self.room_edit_widgets:
            all_line_edits_in_dialog.append(room_set["present_edit"])
            all_line_edits_in_dialog.append(room_set["previous_edit"])

        for widget in all_line_edits_in_dialog:
            if widget: # Ensure widget exists
                widget.next_widget_on_enter = None
                widget.up_widget = None
                widget.down_widget = None
                widget.left_widget = None
                widget.right_widget = None
        
        if isinstance(save_btn, CustomNavButton):
            save_btn.next_widget_on_enter = None

        # --- Define Enter/Return Key Sequence ---
        # This will be a flat list for simplicity of Enter key progression
        enter_sequence = meter_diff_edits + [aa]
        
        # Add room fields to enter_sequence
        for room_set in self.room_edit_widgets:
            enter_sequence.append(room_set["present_edit"])
            enter_sequence.append(room_set["previous_edit"])
        
        # Link Enter sequence
        for i, widget in enumerate(enter_sequence):
            if i < len(enter_sequence) - 1:
                widget.next_widget_on_enter = enter_sequence[i+1]
            else: # Last widget in enter_sequence (could be a room's previous_edit or additional_amount_edit)
                widget.next_widget_on_enter = save_btn
        
        if isinstance(save_btn, CustomNavButton) and enter_sequence:
            save_btn.next_widget_on_enter = enter_sequence[0] # Loop back to first field

        # --- Define Arrow Key Navigation (Up/Down Fields Only, in a single sequence) ---
        
        # Sequence for main fields: meter1 <-> diff1 <-> meter2 <-> diff2 <-> ... <-> aa
        main_up_down_sequence = meter_diff_edits + [aa]
        
        # Sequence for room fields: room1_present <-> room1_previous <-> room2_present <-> ...
        room_up_down_sequence = []
        for room_set in self.room_edit_widgets:
            room_up_down_sequence.append(room_set["present_edit"])
            room_up_down_sequence.append(room_set["previous_edit"])

        # Combine sequences if rooms exist, otherwise just use main_fields
        if room_up_down_sequence:
            # Link aa down to first room field, and first room field up to aa
            aa.down_widget = room_up_down_sequence[0]
            room_up_down_sequence[0].up_widget = aa
            
            # Link last room field down to first main field (m1), and m1 up to last room field
            room_up_down_sequence[-1].down_widget = main_up_down_sequence[0] # last room field down to m1
            main_up_down_sequence[0].up_widget = room_up_down_sequence[-1]   # m1 up to last room field

            # Link main_up_down_sequence internally (excluding ends that connect to rooms)
            for i, widget in enumerate(main_up_down_sequence):
                if widget == main_up_down_sequence[0]: # m1
                    if i + 1 < len(main_up_down_sequence): widget.down_widget = main_up_down_sequence[i+1]
                    # m1.up_widget is set above (to last room field)
                elif widget == main_up_down_sequence[-1]: # aa
                    if i - 1 >= 0: widget.up_widget = main_up_down_sequence[i-1]
                    # aa.down_widget is set above (to first room field)
                else: # Middle elements of main_up_down_sequence
                    if i + 1 < len(main_up_down_sequence): widget.down_widget = main_up_down_sequence[i+1]
                    if i - 1 >= 0: widget.up_widget = main_up_down_sequence[i-1]

            # Link room_up_down_sequence internally
            for i, widget in enumerate(room_up_down_sequence):
                if widget == room_up_down_sequence[0]: # first room field
                    if i + 1 < len(room_up_down_sequence): widget.down_widget = room_up_down_sequence[i+1]
                    # first_room_field.up_widget is set above (to aa)
                elif widget == room_up_down_sequence[-1]: # last room field
                    if i - 1 >= 0: widget.up_widget = room_up_down_sequence[i-1]
                    # last_room_field.down_widget is set above (to m1)
                else: # Middle elements of room_up_down_sequence
                     if i + 1 < len(room_up_down_sequence): widget.down_widget = room_up_down_sequence[i+1]
                     if i - 1 >= 0: widget.up_widget = room_up_down_sequence[i-1]

        else: # No rooms, main_up_down_sequence loops on itself
            for i, widget in enumerate(main_up_down_sequence):
                widget.down_widget = main_up_down_sequence[(i + 1) % len(main_up_down_sequence)]
                widget.up_widget = main_up_down_sequence[(i - 1 + len(main_up_down_sequence)) % len(main_up_down_sequence)]

        # Ensure Left/Right are None for all CustomLineEdits in this dialog
        for widget_to_clear in all_line_edits_in_dialog: # all_line_edits_in_dialog defined earlier
            if widget_to_clear: # Check if widget is not None
                widget_to_clear.left_widget = None
                widget_to_clear.right_widget = None
        
        # Set initial focus
        if enter_sequence:
            enter_sequence[0].setFocus()
    def populate_data(self, main_data, room_data_list):
        # Get the default and additional meter/difference values
        meter_values = [
            main_data.get("meter1_reading", "") or "",
            main_data.get("meter2_reading", "") or "",
            main_data.get("meter3_reading", "") or ""
        ]
        diff_values = [
            main_data.get("diff1", "") or "",
            main_data.get("diff2", "") or "",
            main_data.get("diff3", "") or ""
        ]
        
        # Check for extra meter readings and diff readings (added in JSON format)
        extra_meter_readings = main_data.get("extra_meter_readings", None)
        extra_diff_readings = main_data.get("extra_diff_readings", None)
        
        # Parse extra values if they exist
        if extra_meter_readings:
            try:
                extra_meters = json.loads(extra_meter_readings)
                if isinstance(extra_meters, list):
                    meter_values.extend(extra_meters)
            except Exception as e:
                print(f"Error parsing extra meter readings: {e}")
        
        if extra_diff_readings:
            try:
                extra_diffs = json.loads(extra_diff_readings)
                if isinstance(extra_diffs, list):
                    diff_values.extend(extra_diffs)
            except Exception as e:
                print(f"Error parsing extra diff readings: {e}")
        
        # Set the values for each meter/diff pair
        for i, pair in enumerate(self.meter_diff_edit_widgets):
            meter_edit = pair.get('meter_edit')
            diff_edit = pair.get('diff_edit')
            
            if meter_edit and i < len(meter_values):
                meter_edit.setText(str(meter_values[i]))
                
            if diff_edit and i < len(diff_values):
                diff_edit.setText(str(diff_values[i]))
                
        # Set additional amount
        self.additional_amount_edit.setText(str(main_data.get("additional_amount", "") or ""))
        
        # Populate room fields
        for i, room_widget_set in enumerate(self.room_edit_widgets):
            if i < len(room_data_list):
                room_data = room_data_list[i]
                room_widget_set["present_edit"].setText(str(room_data.get("present_reading_room", "") or ""))
                room_widget_set["previous_edit"].setText(str(room_data.get("previous_reading_room", "") or ""))


    def save_changes(self):
        # Helper functions for safe parsing
        def _safe_parse_int(value_str, default=0):
            try: return int(value_str) if value_str else default
            except (ValueError, TypeError): return default
            
        def _safe_parse_float(value_str, default=0.0):
            try: return float(value_str) if value_str else default
            except (ValueError, TypeError): return default

        try:
            # TODO: Add more robust validation if needed
            
            # Collect all meter/diff values
            meter_values = []
            diff_values = []
            
            for pair in self.meter_diff_edit_widgets:
                meter_edit = pair.get('meter_edit')
                diff_edit = pair.get('diff_edit')
                
                if meter_edit:
                    meter_values.append(_safe_parse_int(meter_edit.text(), 0))
                else:
                    meter_values.append(0)
                    
                if diff_edit:
                    diff_values.append(_safe_parse_int(diff_edit.text(), 0))
                else:
                    diff_values.append(0)
            
            # Ensure we have at least 3 values for the fixed fields
            while len(meter_values) < 3:
                meter_values.append(0)
            while len(diff_values) < 3:
                diff_values.append(0)
                
            # Get the first three pairs for backward compatibility
            meter1 = meter_values[0]
            meter2 = meter_values[1]
            meter3 = meter_values[2]
            diff1 = diff_values[0]
            diff2 = diff_values[1]
            diff3 = diff_values[2]
            
            # Handle extra pairs beyond the first three
            extra_meter_readings = meter_values[3:] if len(meter_values) > 3 else []
            extra_diff_readings = diff_values[3:] if len(diff_values) > 3 else []
            
            # Convert to JSON strings for storage
            extra_meter_json = json.dumps(extra_meter_readings) if extra_meter_readings else None
            extra_diff_json = json.dumps(extra_diff_readings) if extra_diff_readings else None
            
            additional_amount = _safe_parse_float(self.additional_amount_edit.text())

            # Recalculate main derived fields
            total_unit_cost = sum(meter_values) # Use DB name
            total_diff_units = sum(diff_values) # Use DB name
            per_unit_cost_calculated = (total_unit_cost / total_diff_units) if total_diff_units != 0 else 0.0 # Use DB name
            grand_total_bill = total_unit_cost + additional_amount # Use DB name

            # Prepare updated main data dictionary using DB column names
            updated_main_data = {
                "meter1_reading": meter1,
                "meter2_reading": meter2,
                "meter3_reading": meter3,
                "diff1": diff1,
                "diff2": diff2,
                "diff3": diff3,
                "additional_amount": additional_amount,
                "total_unit_cost": total_unit_cost, 
                "total_diff_units": total_diff_units, 
                "per_unit_cost_calculated": per_unit_cost_calculated, 
                "grand_total_bill": grand_total_bill,
                "extra_meter_readings": extra_meter_json,
                "extra_diff_readings": extra_diff_json
            }

            # Prepare updated room data
            updated_room_data_list = []
            for room_widget_set in self.room_edit_widgets:
                present_reading = _safe_parse_int(room_widget_set["present_edit"].text())
                previous_reading = _safe_parse_int(room_widget_set["previous_edit"].text())
                units_consumed = present_reading - previous_reading
                cost = units_consumed * per_unit_cost_calculated # Use recalculated cost

                room_data = {
                    "main_calculation_id": self.record_id, # Link to the main record
                    "room_name": room_widget_set["name"], # Use stored name
                    "present_reading_room": present_reading,
                    "previous_reading_room": previous_reading,
                    "units_consumed_room": units_consumed,
                    "cost_room": cost
                    # Removed user_id as it expects UUID and allows NULL
                }
                updated_room_data_list.append(room_data)


            # --- Execute Supabase Update ---
            print(f"Updating main_calculations record ID: {self.record_id}")
            # Update main record
            self.supabase.table("main_calculations").update(updated_main_data).eq("id", self.record_id).execute()
            
            # Delete old room records for this main_calc_id
            print(f"Deleting old room_calculations for main_calculation_id: {self.record_id}")
            self.supabase.table("room_calculations").delete().eq("main_calculation_id", self.record_id).execute()

            # Insert new room records 
            if updated_room_data_list:
                print(f"Inserting new room_calculations for main_calculation_id: {self.record_id}")
                self.supabase.table("room_calculations").insert(updated_room_data_list).execute()

            QMessageBox.information(self, "Success", "Record updated successfully.")
            self.accept() # Close dialog with success signal

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to update record: {e.message}\nDetails: {e.details}")
            print(f"Supabase API Error on update: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"An unexpected error occurred during update: {e}\n{traceback.format_exc()}")
            print(f"Unexpected Update Error: {e}\n{traceback.format_exc()}")


# Main application class
class MeterCalculationApp(QMainWindow):
    def __init__(self):
        # Call the parent class constructor
        super().__init__()

        self.setWindowTitle("Home Unit Calculator")
        self.setGeometry(100, 100, 1300, 860) # Increased width for better layout
        self.setStyleSheet(get_stylesheet())
        self.setWindowIcon(QIcon(resource_path("icons/icon.png")))
        
        self.db_manager = DBManager()
        self.encryption_util = EncryptionUtil()
        self.supabase = None
        self.supabase_url = None
        self.supabase_key = None
        
        # Initialize combo box for loading data source (used in Main and History tabs)
        self.load_info_source_combo = QComboBox()
        self.load_info_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_info_source_combo.setStyleSheet(get_month_info_style())
        
        # Initialize combo box for loading history source (used in History tab)
        self.load_history_source_combo = QComboBox()
        self.load_history_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_history_source_combo.setStyleSheet(get_month_info_style())

        self._initialize_supabase_client()
        self.init_ui() # Initialize the user interface
        self.setup_navigation() # Set up the navigation for the application
        self.center_window() # Center the window on the screen

    def check_internet_connectivity(self):
        """Helper method for checking internet connectivity."""
        import socket
        try:
            # Try to establish a connection to Google's DNS server
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            return False

    def _initialize_supabase_client(self):
        """Initializes the Supabase client using stored or newly entered credentials."""
        config = self.db_manager.get_config()
        self.supabase_url = config.get("SUPABASE_URL")
        self.supabase_key = config.get("SUPABASE_KEY")

        if not (self.supabase_url and self.supabase_key):
            self.supabase = None
            QMessageBox.information(
                self, "Supabase Configuration",
                "Supabase URL and Key not found. Please configure Supabase to enable cloud features."
            )
            return

        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            print("Supabase client initialized successfully from stored config.")
        except Exception as e:
            self.supabase = None
            QMessageBox.critical(
                self, "Supabase Error",
                f"Failed to initialize Supabase client with stored credentials: {e}\nPlease re-enter your Supabase configuration."
            )

    def init_ui(self):
        # Initialize the main user interface
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Add header
        header = QLabel("Meter Calculation Application")  # Create a label for the header
        header.setStyleSheet(get_header_style())  # Apply custom style to the header
        main_layout.addWidget(header)  # Add the header to the main layout

        # Create and add tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabWidget::pane { border: 0; }") # Remove border around tabs

        # Create tabs
        main_tab = self.create_main_tab()
        rooms_tab = self.create_rooms_tab()
        history_tab = self.create_history_tab()
        supabase_config_tab = self.create_supabase_config_tab() # New Supabase config tab

        # Add tabs to the tab widget
        self.tab_widget.addTab(main_tab, "Main Calculation")
        self.tab_widget.addTab(rooms_tab, "Room Calculations")
        self.tab_widget.addTab(history_tab, "Calculation History")
        self.tab_widget.addTab(supabase_config_tab, "Supabase Config") # Add new tab
        
        # Connect tab change signal to a slot for focus management
        self.tab_widget.currentChanged.connect(self.set_focus_on_tab_change)

        main_layout.addWidget(self.tab_widget)

        # Create a horizontal layout for the save buttons
        save_buttons_layout = QHBoxLayout()

        # Add Save as PDF button
        save_pdf_button = QPushButton("Save as PDF")
        save_pdf_button.setObjectName("savePdfButton") # For specific styling
        save_pdf_button.setIcon(QIcon(resource_path("icons/save_icon.png")))
        save_pdf_button.clicked.connect(self.save_to_pdf)
        save_buttons_layout.addWidget(save_pdf_button)

        # Add Save as CSV button
        save_csv_button = QPushButton("Save as CSV")
        save_csv_button.setObjectName("saveCsvButton") # For specific styling
        # You might want a different icon for CSV, e.g., a document icon
        save_csv_button.setIcon(QIcon(resource_path("icons/save_icon.png"))) # Placeholder icon
        save_csv_button.clicked.connect(self.save_calculation_to_csv)
        save_buttons_layout.addWidget(save_csv_button)

        # Add Save to Cloud button (formerly Save to Supabase)
        save_cloud_button = QPushButton("Save to Cloud")
        save_cloud_button.setObjectName("saveCloudButton") # For specific styling
        save_cloud_button.setIcon(QIcon(resource_path("icons/database_icon.png"))) # Assuming a database_icon.png exists
        save_cloud_button.clicked.connect(self.save_calculation_to_supabase)
        save_buttons_layout.addWidget(save_cloud_button)
        
        main_layout.addLayout(save_buttons_layout) # Add the horizontal layout of buttons to the main layout

    def create_main_tab(self):
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- NEW TOP ROW ---
        new_top_row_layout = QHBoxLayout()
        new_top_row_layout.setSpacing(20) 

        # Date Selection Group (Left side of Top Row)
        # This group contains the month/year for the CURRENT calculation
        date_selection_group = QGroupBox("Date Selection") 
        date_selection_group.setStyleSheet(get_group_box_style())
        date_selection_filter_layout = QHBoxLayout() 
        date_selection_group.setLayout(date_selection_filter_layout)

        month_label = QLabel("Month:")
        month_label.setStyleSheet(get_label_style())
        self.month_combo = QComboBox() 
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())

        year_label = QLabel("Year:")
        year_label.setStyleSheet(get_label_style())
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self.year_spinbox.setStyleSheet(get_month_info_style())

        date_selection_filter_layout.addWidget(month_label)
        date_selection_filter_layout.addWidget(self.month_combo)
        date_selection_filter_layout.addSpacing(20)
        date_selection_filter_layout.addWidget(year_label)
        date_selection_filter_layout.addWidget(self.year_spinbox)
        date_selection_filter_layout.addStretch(1)
        
        new_top_row_layout.addWidget(date_selection_group, 1) 

        # Moved Load Data Options Group (Right side of Top Row)
        # This group is for LOADING data from history/cloud into the current input fields
        moved_load_options_group = QGroupBox("Load Data Options")
        moved_load_options_group.setStyleSheet(get_group_box_style())

        moved_load_options_internal_layout = QVBoxLayout()
        moved_load_options_group.setLayout(moved_load_options_internal_layout)

        # create_load_info_group contains its own month/year (self.load_month_combo, self.load_year_spinbox) and Load button
        load_info_group = self.create_load_info_group() 
        moved_load_options_internal_layout.addWidget(load_info_group)

        # Source for 'Load' Button
        source_info_layout = QHBoxLayout()
        source_info_label = QLabel("Source for 'Load' Button:")
        source_info_label.setStyleSheet(get_label_style())
        source_info_layout.addWidget(source_info_label)
        source_info_layout.addWidget(self.load_info_source_combo) # Initialized in __init__
        source_info_layout.addStretch(1) 
        moved_load_options_internal_layout.addLayout(source_info_layout)
        
        new_top_row_layout.addWidget(moved_load_options_group, 1) 

        main_layout.addLayout(new_top_row_layout)

        # --- MIDDLE ROW (METER, DIFF, RIGHT COLUMN) ---
        middle_row_layout = QHBoxLayout()
        
        # Create Meter group with scrollable area
        meter_group = QGroupBox("Meter Readings")
        meter_group.setStyleSheet(get_group_box_style())
        meter_scroll = AutoScrollArea()
        meter_scroll.setWidgetResizable(True)
        meter_container = QWidget()
        self.meter_layout = QFormLayout(meter_container)
        self.meter_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        meter_scroll.setWidget(meter_container)
        meter_group_layout = QVBoxLayout(meter_group)
        meter_group_layout.addWidget(meter_scroll)
        middle_row_layout.addWidget(meter_group, 1)
        
        # Create Difference group with scrollable area
        diff_group = QGroupBox("Difference Readings")
        diff_group.setStyleSheet(get_group_box_style())
        diff_scroll = AutoScrollArea()
        diff_scroll.setWidgetResizable(True)
        diff_container = QWidget()
        self.diff_layout = QFormLayout(diff_container)
        self.diff_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        diff_scroll.setWidget(diff_container)
        diff_group_layout = QVBoxLayout(diff_group)
        diff_group_layout.addWidget(diff_scroll)
        middle_row_layout.addWidget(diff_group, 1)
        
        # Store references to dynamically created widgets
        self.meter_entries = []
        self.diff_entries = []
        
        # Right column (Spinboxes and Additional Amount)
        right_column_layout = QVBoxLayout()
        
        # Create a horizontal layout for meter and diff spinboxes
        spinboxes_layout = QHBoxLayout()
        
        # Number of Meters group
        meter_count_group = QGroupBox("Number of Meters:")
        meter_count_group.setStyleSheet(get_group_box_style())
        meter_count_layout = QHBoxLayout(meter_count_group)
        meter_count_layout.setContentsMargins(5, 5, 5, 5)  # Reduce padding (left, top, right, bottom)
        meter_count_layout.setSpacing(2)  # Reduce spacing between elements
        self.meter_count_spinbox = CustomSpinBox()
        self.meter_count_spinbox.setRange(1, 10)
        self.meter_count_spinbox.setValue(3)  # Default to 3 meters
        self.meter_count_spinbox.valueChanged.connect(self.update_meter_inputs)
        meter_count_layout.addWidget(self.meter_count_spinbox)
        spinboxes_layout.addWidget(meter_count_group)
        
        # Number of Diffs group
        diff_count_group = QGroupBox("Number of Diffs:")
        diff_count_group.setStyleSheet(get_group_box_style())
        diff_count_layout = QHBoxLayout(diff_count_group)
        diff_count_layout.setContentsMargins(5, 5, 5, 5)  # Reduce padding (left, top, right, bottom)
        diff_count_layout.setSpacing(2)  # Reduce spacing between elements
        self.diff_count_spinbox = CustomSpinBox()
        self.diff_count_spinbox.setRange(1, 10)
        self.diff_count_spinbox.setValue(3)  # Default to 3 diffs
        self.diff_count_spinbox.valueChanged.connect(self.update_diff_inputs)
        diff_count_layout.addWidget(self.diff_count_spinbox)
        spinboxes_layout.addWidget(diff_count_group)
        
        # Set smaller spacing for the spinboxes_layout
        spinboxes_layout.setSpacing(5)  # Reduce spacing between spinbox groups
        
        # Add the horizontal spinboxes layout to the right column
        right_column_layout.addLayout(spinboxes_layout)
        
        # Additional Amount group
        amount_group = self.create_additional_amount_group()
        right_column_layout.addWidget(amount_group)
        
        middle_row_layout.addLayout(right_column_layout, 1)
        
        main_layout.addLayout(middle_row_layout)

        # --- RESULTS SECTION --- (Moved before Calculate button)
        results_group = self.create_results_group()
        main_layout.addWidget(results_group)

        # --- CALCULATE BUTTON ---
        self.main_calculate_button = CustomNavButton("Calculate")
        self.main_calculate_button.setIcon(QIcon(resource_path("icons/calculate_icon.png")))
        self.main_calculate_button.clicked.connect(self.calculate_main)
        self.main_calculate_button.setStyleSheet(get_button_style())
        self.main_calculate_button.setFixedHeight(50)
        main_layout.addWidget(self.main_calculate_button)
        
        # Initialize the dynamic meter/diff inputs
        self.update_meter_inputs(3)
        self.update_diff_inputs(3)

        # Removed final stretch to allow vertical expansion
        return main_tab
    

    def create_additional_amount_group(self):
        amount_group = QGroupBox("Additional Amount")
        amount_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Allow horizontal expansion
        amount_group.setStyleSheet(get_group_box_style())
        amount_layout = QHBoxLayout()
        amount_group.setLayout(amount_layout)

        amount_label = QLabel("Additional Amount:")
        amount_label.setStyleSheet(get_label_style())
        self.additional_amount_input = CustomLineEdit()
        self.additional_amount_input.setObjectName("main_additional_amount_input")
        self.additional_amount_input.setPlaceholderText("Enter additional amount")
        self.additional_amount_input.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))
        self.additional_amount_input.setStyleSheet(get_line_edit_style())
        
        # Add a QLabel to display the currency
        currency_label = QLabel("TK")
        currency_label.setStyleSheet(get_label_style())

        # Create a QHBoxLayout for the input and currency label
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.additional_amount_input, 1)  # Add stretch factor
        input_layout.addWidget(currency_label)
        input_layout.setSpacing(5)  # Set spacing between input and currency label

        amount_layout.addWidget(amount_label)
        amount_layout.addLayout(input_layout, 1)  # Add stretch factor
        
        # Remove the stretch at the end to allow proper resizing
        # amount_layout.addStretch(1)

        # Add a tooltip to explain the purpose of this field
        amount_group.setToolTip("Enter any additional amount to be added to the total bill")

        return amount_group

    def get_additional_amount(self):
        try:
            return float(self.additional_amount_input.text()) if self.additional_amount_input.text() else 0.0
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric value for the additional amount.")
            return 0.0

    def create_month_info_section(self):
        # Create the month and year selection section
        month_info_layout = QHBoxLayout()  # Create a horizontal box layout for the month and year selection
        month_info_layout.setSpacing(10)  # Set the spacing between widgets to 10 pixels

        month_label = QLabel("Month:")  # Create a label for the month selection
        month_label.setStyleSheet("font-weight: bold;")  # Set the label's font to bold
        self.month_combo = QComboBox()  # Create a combo box for selecting the month
        self.month_combo.addItems([  # Add month names to the combo box
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())  # Apply custom style to the month combo box

        year_label = QLabel("Year:")  # Create a label for the year selection
        year_label.setStyleSheet("font-weight: bold;")  # Set the label's font to bold
        self.year_spinbox = QSpinBox()  # Create a spin box for selecting the year
        self.year_spinbox.setRange(2000, 2100)  # Set the range of selectable years from 2000 to 2100
        self.year_spinbox.setValue(datetime.now().year)  # Set the initial value to the current year
        self.year_spinbox.setStyleSheet(get_month_info_style())  # Apply custom style to the year spin box

        month_info_layout.addWidget(month_label)  # Add the month label to the layout
        month_info_layout.addWidget(self.month_combo, 1)  # Add the month combo box to the layout with a stretch factor of 1
        month_info_layout.addWidget(year_label)  # Add the year label to the layout
        month_info_layout.addWidget(self.year_spinbox, 1)  # Add the year spin box to the layout with a stretch factor of 1
        month_info_layout.addStretch(2)  # Add a stretchable space at the end with a stretch factor of 2

        return month_info_layout  # Return the completed layout

    def update_meter_inputs(self, value=None):
        # Get the requested number of meter entries (or use the current spinbox value if not provided)
        num_meters = value if value is not None else self.meter_count_spinbox.value()
        
        # Store current values from existing widgets if any
        current_values = {}
        for i, meter_edit in enumerate(self.meter_entries):
            if i < len(self.meter_entries):
                current_values[i] = meter_edit.text()
        
        # Clear existing widgets from the layout
        self._clear_layout(self.meter_layout)
        self.meter_entries = []
        
        # Create the requested number of meter inputs
        for i in range(num_meters):
            # Create a meter input
            meter_edit = CustomLineEdit()
            meter_edit.setObjectName(f"meter_edit_{i}")
            meter_edit.setPlaceholderText(f"Enter meter {i+1} reading")
            self.meter_layout.addRow(f"Meter {i+1} Reading:", meter_edit)
            
            # Restore previous value if available
            if i in current_values:
                meter_edit.setText(current_values[i])
            
            # Store reference for later use
            self.meter_entries.append(meter_edit)
        
        # Update navigation
        self.setup_navigation()
    
    def update_diff_inputs(self, value=None):
        # Get the requested number of diff entries (or use the current spinbox value if not provided)
        num_diffs = value if value is not None else self.diff_count_spinbox.value()
        
        # Store current values from existing widgets if any
        current_values = {}
        for i, diff_edit in enumerate(self.diff_entries):
            if i < len(self.diff_entries):
                current_values[i] = diff_edit.text()
        
        # Clear existing widgets from the layout
        self._clear_layout(self.diff_layout)
        self.diff_entries = []
        
        # Create the requested number of diff inputs
        for i in range(num_diffs):
            # Create a diff input
            diff_edit = CustomLineEdit()
            diff_edit.setObjectName(f"diff_edit_{i}")
            diff_edit.setPlaceholderText(f"Enter difference {i+1} reading")
            self.diff_layout.addRow(f"Difference {i+1} Reading:", diff_edit)
            
            # Restore previous value if available
            if i in current_values:
                diff_edit.setText(current_values[i])
            
            # Store reference for later use
            self.diff_entries.append(diff_edit)
        
        # Update navigation
        self.setup_navigation()
    
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    # Properly dispose the widget to release memory & native handles
                    widget.setParent(None)
                    widget.deleteLater()
                elif item.layout() is not None:
                    self._clear_layout(item.layout())
                    # do **not** return – continue the while-loop so subsequent siblings are processed
    
    # Keep these methods for backward compatibility but modify them to be empty or use the new system
    def create_meter_group(self):
        # This method is no longer used, but kept for backward compatibility
        # The functionality is now part of update_meter_diff_inputs
        group = QGroupBox("Meter Readings")
        group.setLayout(QVBoxLayout())
        return group
    
    def create_diff_group(self):
        # This method is no longer used, but kept for backward compatibility
        # The functionality is now part of update_meter_diff_inputs
        group = QGroupBox("Difference Readings")
        group.setLayout(QVBoxLayout())
        return group

    def create_results_group(self):
        # Create the Results section with new layout
        results_group = QGroupBox("Results")
        # Apply general group box style, specific label styles will override QLabel part
        results_group.setStyleSheet(get_group_box_style())
        results_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        results_layout = QHBoxLayout(results_group) # Main horizontal layout
        results_layout.setSpacing(20) # Spacing between each vertical metric group
        results_layout.setContentsMargins(15, 25, 15, 15) # top margin increased for title space

        # --- Create Vertical Layouts for Each Metric ---
        
        # Metric 1: Total Units
        total_unit_layout = QVBoxLayout()
        total_unit_layout.setSpacing(2) # Minimal spacing between title and value
        total_unit_title_label = QLabel("Total Units")
        total_unit_title_label.setStyleSheet(get_result_title_style())
        self.total_unit_value_label = QLabel("0") # Instance variable for value
        self.total_unit_value_label.setStyleSheet(get_result_value_style())
        total_unit_layout.addWidget(total_unit_title_label)
        total_unit_layout.addWidget(self.total_unit_value_label)
        total_unit_layout.addStretch(1) # Push to top if needed
        results_layout.addLayout(total_unit_layout, 1) # Add to main layout with stretch

        # Metric 2: Total Difference
        total_diff_layout = QVBoxLayout()
        total_diff_layout.setSpacing(2)
        total_diff_title_label = QLabel("Total Difference")
        total_diff_title_label.setStyleSheet(get_result_title_style())
        self.total_diff_value_label = QLabel("0")
        self.total_diff_value_label.setStyleSheet(get_result_value_style())
        total_diff_layout.addWidget(total_diff_title_label)
        total_diff_layout.addWidget(self.total_diff_value_label)
        total_diff_layout.addStretch(1)
        results_layout.addLayout(total_diff_layout, 1)

        # Metric 3: Per Unit Cost
        per_unit_cost_layout = QVBoxLayout()
        per_unit_cost_layout.setSpacing(2)
        per_unit_cost_title_label = QLabel("Per Unit Cost")
        per_unit_cost_title_label.setStyleSheet(get_result_title_style())
        self.per_unit_cost_value_label = QLabel("0.00")
        self.per_unit_cost_value_label.setStyleSheet(get_result_value_style())
        per_unit_cost_layout.addWidget(per_unit_cost_title_label)
        per_unit_cost_layout.addWidget(self.per_unit_cost_value_label)
        per_unit_cost_layout.addStretch(1)
        results_layout.addLayout(per_unit_cost_layout, 1)

        # Metric 4: Added Amount
        added_amount_layout = QVBoxLayout()
        added_amount_layout.setSpacing(2)
        added_amount_title_label = QLabel("Added Amount")
        added_amount_title_label.setStyleSheet(get_result_title_style())
        self.additional_amount_value_label = QLabel("0") # Renamed instance variable
        self.additional_amount_value_label.setStyleSheet(get_result_value_style())
        added_amount_layout.addWidget(added_amount_title_label)
        added_amount_layout.addWidget(self.additional_amount_value_label)
        added_amount_layout.addStretch(1)
        results_layout.addLayout(added_amount_layout, 1)

        # Metric 5: In Total
        in_total_layout = QVBoxLayout()
        in_total_layout.setSpacing(2)
        in_total_title_label = QLabel("In Total")
        in_total_title_label.setStyleSheet(get_result_title_style())
        self.in_total_value_label = QLabel("0.00") # Renamed instance variable
        self.in_total_value_label.setStyleSheet(get_result_value_style())
        in_total_layout.addWidget(in_total_title_label)
        in_total_layout.addWidget(self.in_total_value_label)
        in_total_layout.addStretch(1)
        results_layout.addLayout(in_total_layout, 1)

        # Adjust minimum height if necessary based on new font sizes
        results_group.setMinimumHeight(100) # Increased minimum height guess

        return results_group

    def create_rooms_tab(self):
        # Create the Room Calculations tab
        rooms_tab = QWidget()  # Create a new QWidget for the rooms tab
        layout = QVBoxLayout()  # Create a vertical layout for the tab
        rooms_tab.setLayout(layout)  # Set the layout for the rooms tab

        # Create a group box for room selection
        room_selection_group = QGroupBox("Room Selection")
        room_selection_group.setStyleSheet(get_room_selection_style())
        room_selection_layout = QFormLayout()
        room_selection_group.setLayout(room_selection_layout)

        # Add Number of Rooms selection
        num_rooms_label = QLabel("Number of Rooms:")
        self.num_rooms_spinbox = CustomSpinBox()
        self.num_rooms_spinbox.setRange(1, 20)
        self.num_rooms_spinbox.setValue(11)
        self.num_rooms_spinbox.valueChanged.connect(self.update_room_inputs)
        
        # Add the label and spinbox to the form layout
        room_selection_layout.addRow(num_rooms_label, self.num_rooms_spinbox)

        # Add room selection group to the main layout
        layout.addWidget(room_selection_group)

        # Create a wrapper widget for the scroll area
        scroll_wrapper = QWidget()
        scroll_wrapper_layout = QVBoxLayout(scroll_wrapper)
        scroll_wrapper_layout.setContentsMargins(0, 0, 0, 0)

        # Add scrollable area for room inputs
        self.rooms_scroll_area = AutoScrollArea()
        self.rooms_scroll_area.setWidgetResizable(True)
        self.rooms_scroll_widget = QWidget()
        self.rooms_scroll_layout = QGridLayout(self.rooms_scroll_widget)
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget)
        scroll_wrapper_layout.addWidget(self.rooms_scroll_area)

        # Add the wrapper to the main layout
        layout.addWidget(scroll_wrapper)

        self.room_entries = []
        self.room_results = []

        # Add Calculate Room Bills button FIRST, so it exists when update_room_inputs is called
        self.calculate_rooms_button = CustomNavButton("Calculate Room Bills")
        self.calculate_rooms_button.setIcon(QIcon(resource_path("icons/calculate_icon.png")))
        self.calculate_rooms_button.clicked.connect(self.calculate_rooms)
        self.calculate_rooms_button.setStyleSheet(get_button_style())
        layout.addWidget(self.calculate_rooms_button)

        # Now call update_room_inputs, which also sets up navigation
        self.update_room_inputs()

        return rooms_tab  # Return the created rooms tab

    def update_room_inputs(self):
        # Update the room inputs based on the number of rooms selected
        # Clear existing widgets from the scroll layout
        for i in reversed(range(self.rooms_scroll_layout.count())):
            # Remove each widget from the layout and set its parent to None
            widget = self.rooms_scroll_layout.itemAt(i).widget()
            if widget: # Check if it's a widget before calling setParent
                widget.setParent(None)

        # Get the number of rooms from the spinbox
        num_rooms = self.num_rooms_spinbox.value()
        # Initialize empty lists for room entries and results
        self.room_entries = []
        self.room_results = []

        # Create input fields and labels for each room
        for i in range(num_rooms):
            # Create a group box for each room
            room_group = QGroupBox(f"Room {i+1}")
            # Create a form layout for the room's inputs
            room_layout = QFormLayout()
            room_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow) # Make fields expand horizontally
            # Set the layout for the room group
            room_group.setLayout(room_layout)
            # Apply the room group style
            room_group.setStyleSheet(get_room_group_style())
            room_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Allow horizontal expansion

            # Create input fields and labels for the room
            present_entry = CustomLineEdit()
            present_entry.setObjectName(f"room_{i}_present")
            previous_entry = CustomLineEdit()
            previous_entry.setObjectName(f"room_{i}_previous")
            real_unit_label = QLabel()
            unit_bill_label = QLabel()

            # Apply styles to the input fields
            present_entry.setStyleSheet(get_line_edit_style())
            previous_entry.setStyleSheet(get_line_edit_style())

            # Add rows to the room layout
            room_layout.addRow("Present Unit:", present_entry)
            room_layout.addRow("Previous Unit:", previous_entry)
            room_layout.addRow("Real Unit:", real_unit_label)
            room_layout.addRow("Unit Bill:", unit_bill_label)

            # Store the entries and results for later use
            self.room_entries.append((present_entry, previous_entry))
            self.room_results.append((real_unit_label, unit_bill_label))

            # Add the room group to the scroll layout
            self.rooms_scroll_layout.addWidget(room_group, i // 3, i % 3)

        # Set column stretch factors for the grid layout to distribute space
        if self.rooms_scroll_layout.columnCount() > 0: # Check if there are columns
            for col in range(self.rooms_scroll_layout.columnCount()):
                 self.rooms_scroll_layout.setColumnStretch(col, 1)

        # Apply styles to all CustomLineEdit widgets in the room entries
        for present_entry, previous_entry in self.room_entries:
            present_entry.setStyleSheet(get_line_edit_style())
            previous_entry.setStyleSheet(get_line_edit_style())

        # Ensure the scroll area updates its content
        self.rooms_scroll_widget.setLayout(self.rooms_scroll_layout) # Re-set layout after adding widgets
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget) # Re-set widget after modifying layout

        # --- Setup Navigation for Room Entries ---
        if hasattr(self, 'calculate_rooms_button') and self.room_entries:
            all_room_line_edits = []
            for present_entry_widget, previous_entry_widget in self.room_entries:
                all_room_line_edits.append(present_entry_widget)
                all_room_line_edits.append(previous_entry_widget)

            if all_room_line_edits and isinstance(self.calculate_rooms_button, CustomNavButton):
                # First, clear all potential old links
                for pe_widget, prev_e_widget in self.room_entries:
                    pe_widget.next_widget_on_enter = None; pe_widget.up_widget = None; pe_widget.down_widget = None; pe_widget.left_widget = None; pe_widget.right_widget = None
                    prev_e_widget.next_widget_on_enter = None; prev_e_widget.up_widget = None; prev_e_widget.down_widget = None; prev_e_widget.left_widget = None; prev_e_widget.right_widget = None
                if isinstance(self.calculate_rooms_button, CustomNavButton):
                    self.calculate_rooms_button.next_widget_on_enter = None

                # Link Enter sequence (Field1 -> Field2 -> ... -> Button -> Field1)
                enter_sequence_rooms = []
                for pe, prev_e in self.room_entries:
                    enter_sequence_rooms.append(pe)
                    enter_sequence_rooms.append(prev_e)
                
                if enter_sequence_rooms: # Only proceed if there are room entries
                    for idx, widget in enumerate(enter_sequence_rooms):
                        if idx < len(enter_sequence_rooms) - 1:
                            widget.next_widget_on_enter = enter_sequence_rooms[idx+1]
                        else: # Last room field
                            widget.next_widget_on_enter = self.calculate_rooms_button
                    if isinstance(self.calculate_rooms_button, CustomNavButton):
                        self.calculate_rooms_button.next_widget_on_enter = enter_sequence_rooms[0]

                # Link Arrow Key Navigation (Up/Down Fields Only, in a single sequence for rooms)
                # Sequence: room1_present <-> room1_previous <-> room2_present <-> ... <-> last_room_previous
                
                # all_room_line_edits was already created for the Enter sequence. We can reuse it.
                if all_room_line_edits: # Check if there are any room line edits
                    for i, widget in enumerate(all_room_line_edits):
                        # Down navigation
                        if i < len(all_room_line_edits) - 1:
                            widget.down_widget = all_room_line_edits[i+1]
                        else: # Last widget in room sequence, loops to first
                            widget.down_widget = all_room_line_edits[0]
                        
                        # Up navigation
                        if i > 0:
                            widget.up_widget = all_room_line_edits[i-1]
                        else: # First widget in room sequence, loops to last
                            widget.up_widget = all_room_line_edits[-1]
                        
                        # Ensure Left/Right are None for text cursor movement
                        widget.left_widget = None
                        widget.right_widget = None
            
            # Optionally, set initial focus
            # if self.room_entries and self.tab_widget.currentWidget() == self.rooms_scroll_area.parentWidget().parentWidget().parentWidget():
            #     self.room_entries[0][0].setFocus()

    def calculate_main(self):
        # Calculate main meter readings and update result labels
        try:
            # Get values from the meter and diff entries
            meter_readings = []
            diff_readings = []
            
            # Get meter readings
            for meter_edit in self.meter_entries:
                if meter_edit and meter_edit.text():
                    meter_readings.append(int(meter_edit.text()))
                else:
                    meter_readings.append(0)
            
            # Get difference readings
            for diff_edit in self.diff_entries:
                if diff_edit and diff_edit.text():
                    diff_readings.append(int(diff_edit.text()))
                else:
                    diff_readings.append(0)
            
            additional_amount = self.get_additional_amount() # Get additional amount

            total_unit = sum(meter_readings)  # Calculate total units
            total_diff = sum(diff_readings)  # Calculate total differences

            if total_diff == 0: # Avoid division by zero
                per_unit_cost = 0
            else:
                per_unit_cost = total_unit / total_diff  # Calculate per unit cost
            
            in_total = total_unit + additional_amount # Calculate in total including additional amount

            # Update result value labels with calculated values
            self.total_unit_value_label.setText(f"{total_unit}")
            self.total_diff_value_label.setText(f"{total_diff}")
            self.per_unit_cost_value_label.setText(f"{per_unit_cost:.2f} TK")
            self.additional_amount_value_label.setText(f"{additional_amount:.2f} TK")
            self.in_total_value_label.setText(f"{in_total:.2f} TK")

        except ValueError:
            # Show warning message for invalid input
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for all readings.")
        except Exception as e:
            # Show error message for other exceptions
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}\n{traceback.format_exc()}")

    def calculate_rooms(self):
        # Calculate the room bills
        try:
            # Get the per unit cost text from the label and remove 'TK'
            label_content = self.per_unit_cost_value_label.text().strip()
            value_to_process = ""

            if ':' in label_content:
                parts = label_content.split(':', 1)
                if len(parts) > 1:
                    value_to_process = parts[1].strip()
                else: # Colon present, but nothing after it (e.g., "Label:")
                    raise ValueError(f"Per unit cost value is missing after colon in '{label_content}'.")
            else: # No colon, assume the whole content is the value
                value_to_process = label_content

            if not value_to_process: # Handles empty label or label that became empty after stripping
                raise ValueError(f"Per unit cost value is empty or missing. Original label content: '{label_content}'.")

            # Clean for "tk" and try to convert
            cleaned_value_text = value_to_process.lower().replace("tk", "").strip()

            if not cleaned_value_text:
                raise ValueError(f"Per unit cost value is non-numeric (e.g., only 'TK' or whitespace) after cleaning. Original value part: '{value_to_process}', from label: '{label_content}'.")

            try:
                per_unit_cost = float(cleaned_value_text)
            except ValueError as e:
                raise ValueError(f"Cannot convert per unit cost value '{cleaned_value_text}' to a number. Original label content: '{label_content}'. Error: {e}")
            # Iterate through room entries and results
            for (present_entry, previous_entry), (real_unit_label, unit_bill_label) in zip(self.room_entries, self.room_results):
                # Get present and previous unit values
                present_text = present_entry.text()
                previous_text = previous_entry.text()
                # If both present and previous values are provided
                if present_text and previous_text:
                    # Convert to integers
                    present_unit = int(present_text)
                    previous_unit = int(previous_text)
                    # Calculate real unit
                    real_unit = present_unit - previous_unit
                    # Calculate unit bill
                    unit_bill = real_unit * per_unit_cost
                    # Round and convert to integer
                    unit_bill = int(round(unit_bill))

                    # Set the calculated values to labels
                    real_unit_label.setText(f"{real_unit}")
                    unit_bill_label.setText(f"{unit_bill} TK")
                else:
                    # If data is incomplete, set labels accordingly
                    real_unit_label.setText("Incomplete")
                    unit_bill_label.setText("Incomplete")

            # Save calculations after both main and room calculations are complete
            # self.save_calculation_to_csv() # Removed automatic save from here
        except ValueError as e:
            # Show warning if there's a value error
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e: # Catch broader exceptions
             QMessageBox.critical(self, "Error", f"An unexpected error occurred during room calculation: {e}\n{traceback.format_exc()}")

    def save_calculation_to_csv(self):
        # Save the main calculation and room bills to a CSV file
        month_name = f"{self.month_combo.currentText()} {self.year_spinbox.value()}"  # Create a string with month and year
        filename = "meter_calculation_history.csv"  # Define the filename for the CSV

        # Check if essential fields are empty
        meter_texts = []
        diff_texts = []
        
        # Gather all meter and diff inputs
        for meter_edit in self.meter_entries:
            meter_texts.append(meter_edit.text())
        for diff_edit in self.diff_entries:
            diff_texts.append(diff_edit.text())
                
        if all(not text for text in meter_texts) and all(not text for text in diff_texts):
             QMessageBox.warning(self, "Empty Data", "Cannot save empty calculation data.")
             return

        try:
            file_exists = os.path.isfile(filename)  # Check if the file already exists
            
            with open(filename, mode='a', newline='') as file:  # Open the file in append mode
                writer = csv.writer(file)  # Create a CSV writer object
                
                # Determine how many meter/diff entries we have
                num_pairs = max(len(self.meter_entries), len(self.diff_entries))
                
                # Write header row if the file is new or empty
                if not file_exists or os.path.getsize(filename) == 0:
                    # Create header dynamically based on number of pairs
                    header = ["Month"]
                    
                    # Add headers for each meter/diff pair (always reserve 10 columns)
                    for i in range(1, 11):
                        header.append(f"Meter-{i}")
                    for i in range(1, 11):
                        header.append(f"Diff-{i}")
                        
                    # Add the rest of the headers
                    header.extend([
                        "Total Unit", "Total Diff", "Per Unit Cost", 
                        "Added Amount", "In Total", 
                        "Room Name", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"
                    ])
                    
                    writer.writerow(header)

                # Prepare main calculation data
                main_data = [month_name]
                
                # Add all meter readings (always pad to 10 columns)
                for i in range(10):
                    if i < len(self.meter_entries):
                        main_data.append(self.meter_entries[i].text() if self.meter_entries[i] and self.meter_entries[i].text() else "0")
                    else:
                        main_data.append("0")  # Pad with zeros for missing entries
                
                # Add all diff readings (always pad to 10 columns)
                for i in range(10):
                    if i < len(self.diff_entries):
                        main_data.append(self.diff_entries[i].text() if self.diff_entries[i] and self.diff_entries[i].text() else "0")
                    else:
                        main_data.append("0")  # Pad with zeros for missing entries
                
                # Add the calculated values
                main_data.extend([
                    (lambda _t: (lambda _v: _v if _v else '0')((_t.split(':',1)[1] if ':' in _t else _t).strip().lower().replace('tk','').strip()))(self.total_unit_value_label.text().strip()),
                    (lambda _t: (lambda _v: _v if _v else '0')((_t.split(':',1)[1] if ':' in _t else _t).strip().lower().replace('tk','').strip()))(self.total_diff_value_label.text().strip()),
                    (lambda _t: (lambda _v: _v if _v else '0.00')((_t.split(':',1)[1] if ':' in _t else _t).strip().lower().replace('tk','').strip()))(self.per_unit_cost_value_label.text().strip()),
                    str(self.get_additional_amount()), # Save additional amount
                    (lambda _t: (lambda _v: _v if _v else '0.00')((_t.split(':',1)[1] if ':' in _t else _t).strip().lower().replace('tk','').strip()))(self.in_total_value_label.text().strip())
                ])

                # Check if room calculations have been performed and data exists
                if self.room_entries and hasattr(self, 'room_results') and self.room_results: # Check if room_results exists and is populated
                    for i, room in enumerate(self.room_entries):
                        room_name = f"Room {i+1}" # Default name
                        # Find the QGroupBox for this room to get the name if set
                        room_group_widget = self.rooms_scroll_layout.itemAtPosition(i // 3, i % 3).widget()
                        if isinstance(room_group_widget, QGroupBox):
                            room_name = room_group_widget.title()

                        present_unit = room[0].text() or "0" # present_entry
                        previous_unit = room[1].text() or "0" # previous_entry
                        
                        real_unit = "N/A"
                        unit_bill = "N/A"
                        if i < len(self.room_results):
                            real_unit_label, unit_bill_label = self.room_results[i]
                            real_unit = real_unit_label.text() if real_unit_label.text() != "Incomplete" else "N/A"
                            unit_bill = unit_bill_label.text().replace(" TK", "") if unit_bill_label.text() != "Incomplete" else "N/A"
                        
                        # For the first room, write main data alongside room data
                        if i == 0:
                            writer.writerow(main_data + [room_name, present_unit, previous_unit, real_unit, unit_bill])
                        else:
                            # For subsequent rooms, write month_name, then pad other main data fields with empty strings, then room data
                            writer.writerow([month_name] + [""] * (len(main_data) - 1) + [room_name, present_unit, previous_unit, real_unit, unit_bill])
                else:
                    # If no room data, just write the main calculation data
                    writer.writerow(main_data + ["N/A"] * 5) # Add placeholders for room columns

            QMessageBox.information(self, "Save Successful", f"Data saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save data to CSV: {e}\n{traceback.format_exc()}")

    def save_calculation_to_supabase(self):
        # Save the main calculation and room bills to Supabase
        if not self.supabase:
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized. Cannot save data.")
            return
        
        # Check if we're online before attempting Supabase operations
        if not self.check_internet_connectivity():
            QMessageBox.warning(self, "Network Error", 
                             "No internet connection detected. Please check your network connection and try again.\n\n"
                             "Tip: You can still use local CSV files for saving data when offline.")
            return

        try:
            month = self.month_combo.currentText()
            year = self.year_spinbox.value()
            
            # Helper to safely parse string to int or float
            def _safe_parse_int(value_str, default=None):
                try: return int(value_str) if value_str else default
                except (ValueError, TypeError): return default
            
            def _safe_parse_float(value_str, default=None):
                try: return float(value_str) if value_str else default
                except (ValueError, TypeError): return default

            # Get values from meter and diff entries
            meter_readings = []
            diff_readings = []
            
            # Process all meter entries (up to max 10)
            for i, meter_edit in enumerate(self.meter_entries):
                if i < 10:  # Limit to 10 maximum
                    meter_readings.append(_safe_parse_int(meter_edit.text(), 0))
            
            # Process all diff entries (up to max 10)
            for i, diff_edit in enumerate(self.diff_entries):
                if i < 10:  # Limit to 10 maximum
                    diff_readings.append(_safe_parse_int(diff_edit.text(), 0))
            
            # Ensure we have at least 3 values for backward compatibility
            while len(meter_readings) < 3:
                meter_readings.append(0)
            while len(diff_readings) < 3:
                diff_readings.append(0)
            
            # Get first three values for backward compatibility (meter1, meter2, meter3)
            meter1 = meter_readings[0]
            meter2 = meter_readings[1]
            meter3 = meter_readings[2]
            diff1 = diff_readings[0]
            diff2 = diff_readings[1]
            diff3 = diff_readings[2]
            # Preserve decimals entered by the user
            additional_amount = _safe_parse_float(self.additional_amount_input.text(), 0.0)

            # Recalculate totals
            total_unit_cost = sum(meter_readings) # Use DB name
            total_diff_units = sum(diff_readings) # Use DB name
            per_unit_cost_calculated = (total_unit_cost / total_diff_units) if total_diff_units != 0 else 0.0 # Use DB name
            grand_total_bill = total_unit_cost + additional_amount # Use DB name

            # Prepare meter and diff data as JSON strings for all pairs beyond the first 3
            extra_meter_readings = meter_readings[3:] if len(meter_readings) > 3 else []
            extra_diff_readings = diff_readings[3:] if len(diff_readings) > 3 else []
            
            # Serialize extra meter/diff readings to JSON strings for storage
            extra_meter_json = json.dumps(extra_meter_readings) if extra_meter_readings else None
            extra_diff_json = json.dumps(extra_diff_readings) if extra_diff_readings else None

            # Main calculation data using DB column names
            main_calc_data = {
                "month": month,
                "year": year,
                "meter1_reading": meter1, # DB name
                "meter2_reading": meter2, # DB name
                "meter3_reading": meter3, # DB name
                "diff1": diff1,
                "diff2": diff2,
                "diff3": diff3,
                "additional_amount": additional_amount,
                "total_unit_cost": total_unit_cost, # DB name
                "total_diff_units": total_diff_units, # DB name
                "per_unit_cost_calculated": per_unit_cost_calculated, # DB name
                "grand_total_bill": grand_total_bill, # DB name
                "extra_meter_readings": extra_meter_json, # New field for additional meter readings
                "extra_diff_readings": extra_diff_json  # New field for additional diff readings
                # Removed user_id as it doesn't exist in the schema
            }

            # Upsert main calculation data
            response = self.supabase.table("main_calculations").select("id").eq("month", month).eq("year", year).execute()
            
            main_calc_id = None
            if response.data: # Record exists, update it
                main_calc_id = response.data[0]['id']
                self.supabase.table("main_calculations").update(main_calc_data).eq("id", main_calc_id).execute()
                print(f"Main calculation data updated for {month} {year}")
            else: # Record doesn't exist, insert it
                insert_response = self.supabase.table("main_calculations").insert(main_calc_data).execute()
                if insert_response.data:
                    main_calc_id = insert_response.data[0]['id']
                    print(f"Main calculation data inserted for {month} {year} with ID: {main_calc_id}")
                else:
                    QMessageBox.critical(self, "Supabase Error", f"Failed to insert main calculation data.")
                    return


            # Room calculation data (if main_calc_id is available)
            if main_calc_id and self.room_entries and hasattr(self, 'room_results') and self.room_results:
                # First, delete existing room calculations for this main_calc_id to avoid duplicates on update
                self.supabase.table("room_calculations").delete().eq("main_calculation_id", main_calc_id).execute()
                print(f"Deleted existing room calculations for main_calc_id: {main_calc_id}")

                room_data_list = []
                for i, room_entry_set in enumerate(self.room_entries):
                    present_entry, previous_entry = room_entry_set
                    real_unit_label, unit_bill_label = self.room_results[i]
                    
                    # Get room name from group box title
                    room_group_widget = self.rooms_scroll_layout.itemAtPosition(i // 3, i % 3).widget()
                    room_name = room_group_widget.title() if isinstance(room_group_widget, QGroupBox) else f"Room {i+1}"
                    
                    # Get calculated room values
                    present_reading = _safe_parse_int(present_entry.text())
                    previous_reading = _safe_parse_int(previous_entry.text())
                    units_consumed = _safe_parse_int(real_unit_label.text())
                    cost = _safe_parse_float(unit_bill_label.text().replace(" TK", ""))

                    room_data = {
                        "main_calculation_id": main_calc_id,
                        "room_name": room_name,
                        "present_reading_room": present_reading, # DB name
                        "previous_reading_room": previous_reading, # DB name
                        "units_consumed_room": units_consumed, # DB name
                        "cost_room": cost # DB name
                        # Removed user_id as it likely doesn't exist in the schema
                    }
                    room_data_list.append(room_data)
                
                if room_data_list:
                    self.supabase.table("room_calculations").insert(room_data_list).execute()
                    print(f"Room calculation data inserted/updated for main_calc_id: {main_calc_id}")

            QMessageBox.information(self, "Save Successful", "Data saved to Cloud successfully.")

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to save data to Supabase: {e.message}\nDetails: {e.details}")
            print(f"Supabase API Error: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred while saving to Supabase: {e}\n{traceback.format_exc()}")
            print(f"Unexpected Supabase Save Error: {e}\n{traceback.format_exc()}")
            
    def create_load_info_group(self):
        # Create Load Information box (used in Main tab now)
        load_info_group = QGroupBox("Load Information")
        load_info_group.setStyleSheet(get_group_box_style())
        load_info_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred) 
        load_info_layout = QHBoxLayout()
        load_info_group.setLayout(load_info_layout)

        load_month_label = QLabel("Month:")
        load_month_label.setStyleSheet(get_label_style())
        self.load_month_combo = QComboBox() # For selecting which month's data to load
        self.load_month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.load_month_combo.setStyleSheet(get_month_info_style())

        load_year_label = QLabel("Year:")
        load_year_label.setStyleSheet(get_label_style())
        self.load_year_spinbox = QSpinBox() # For selecting which year's data to load
        self.load_year_spinbox.setRange(2000, 2100)
        self.load_year_spinbox.setValue(datetime.now().year)
        self.load_year_spinbox.setStyleSheet(get_month_info_style())

        load_button = QPushButton("Load") # Button to trigger loading into input fields
        load_button.setStyleSheet(get_button_style())
        load_button.clicked.connect(self.load_info_to_inputs) # Connects to a method that loads data

        load_info_layout.addWidget(load_month_label)
        load_info_layout.addWidget(self.load_month_combo)
        load_info_layout.addSpacing(20)
        load_info_layout.addWidget(load_year_label)
        load_info_layout.addWidget(self.load_year_spinbox)
        load_info_layout.addSpacing(20)
        load_info_layout.addWidget(load_button)
        load_info_layout.addStretch(1) # Push elements to the left

        return load_info_group

    def create_history_tab(self):
        history_tab = QWidget()
        layout = QVBoxLayout(history_tab)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- TOP ROW: Filter Options and Load History Options ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(15) # Adjusted spacing

        # Filter Options Group
        filter_group = QGroupBox("Filter Options")
        filter_group.setStyleSheet(get_group_box_style())
        filter_layout = QHBoxLayout(filter_group)

        month_label = QLabel("Month:")
        month_label.setStyleSheet(get_label_style())
        self.history_month_combo = QComboBox()
        self.history_month_combo.addItems([
            "All", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])
        self.history_month_combo.setStyleSheet(get_month_info_style())
        
        year_label = QLabel("Year:")
        year_label.setStyleSheet(get_label_style())
        self.history_year_spinbox = QSpinBox()
        self.history_year_spinbox.setRange(2000, 2100)
        self.history_year_spinbox.setValue(datetime.now().year)
        self.history_year_spinbox.setSpecialValueText("All")
        self.history_year_spinbox.setStyleSheet(get_month_info_style())
        
        filter_layout.addWidget(month_label)
        filter_layout.addWidget(self.history_month_combo)
        filter_layout.addSpacing(15)
        filter_layout.addWidget(year_label)
        filter_layout.addWidget(self.history_year_spinbox)
        filter_layout.addStretch(1)
        
        top_layout.addWidget(filter_group, 2) # Stretch factor 2

        # Load History Options Group
        load_history_options_group = QGroupBox("Load History Options")
        load_history_options_group.setStyleSheet(get_group_box_style())
        load_history_options_layout = QHBoxLayout(load_history_options_group)
        load_history_options_layout.setSpacing(10)
        
        history_source_label = QLabel("Source:")
        history_source_label.setStyleSheet(get_label_style())
        load_history_options_layout.addWidget(history_source_label)
        load_history_options_layout.addWidget(self.load_history_source_combo)
        
        load_history_button = QPushButton("Load History Table")
        load_history_button.clicked.connect(self.load_history)
        load_history_button.setStyleSheet(get_button_style())
        load_history_button.setFixedHeight(35)
        load_history_options_layout.addWidget(load_history_button)
        load_history_options_layout.addStretch(1)

        top_layout.addWidget(load_history_options_group, 2) # Stretch factor 2

        # Record Actions Group (New)
        record_actions_group = QGroupBox("Record Actions")
        record_actions_group.setStyleSheet(get_group_box_style())
        record_actions_layout = QHBoxLayout(record_actions_group)
        record_actions_layout.setSpacing(10)

        self.edit_selected_record_button = QPushButton("Edit Record")
        self.edit_selected_record_button.setStyleSheet(get_button_style())
        self.edit_selected_record_button.setFixedHeight(35)
        self.edit_selected_record_button.clicked.connect(self.handle_edit_selected_record)

        self.delete_selected_record_button = QPushButton("Delete Record")
        # Consider a different style for delete, e.g., red background
        delete_button_style = "background-color: #dc3545; color: white; border: none; border-radius: 4px; padding: 8px; font-weight: bold; font-size: 13px;"
        self.delete_selected_record_button.setStyleSheet(delete_button_style)
        self.delete_selected_record_button.setFixedHeight(35)
        self.delete_selected_record_button.clicked.connect(self.handle_delete_selected_record)
        
        record_actions_layout.addWidget(self.edit_selected_record_button)
        record_actions_layout.addWidget(self.delete_selected_record_button)
        record_actions_layout.addStretch(1)

        top_layout.addWidget(record_actions_group, 1) # Stretch factor 1

        layout.addLayout(top_layout)

        # --- Main Calculation Info Section ---
        main_calc_group = QGroupBox("Main Calculation Info")
        main_calc_group.setStyleSheet(get_group_box_style())
        main_calc_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) # Strict fixed vertical policy
        main_calc_layout = QVBoxLayout(main_calc_group)

        self.main_history_table = QTableWidget()
        self.main_history_table.setColumnCount(12) # Reduced column count
        self.main_history_table.setHorizontalHeaderLabels([
            "Month", "Meter-1", "Meter-2", "Meter-3",
            "Diff-1", "Diff-2", "Diff-3", "Total Unit Cost",
            "Total Diff Units", "Per Unit Cost", "Added Amount", "Grand Total" # Removed "Actions"
        ])
        header = self.main_history_table.horizontalHeader()
        for i in range(self.main_history_table.columnCount()): # Stretch all columns
             header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        self.main_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.main_history_table.setAlternatingRowColors(True)
        self.main_history_table.setStyleSheet(get_table_style())
        
        # Set fixed height for main_history_table to show header + 2 data rows
        table_header_height = self.main_history_table.horizontalHeader().height()
        # Estimate row height or use a fixed value if defaultSectionSize is unreliable before items are added
        # A common default row height is around 25-30px. Let's use 28 for calculation.
        estimated_row_height = 30 # Increased
        num_data_rows_main_table = 2
        
        # Calculate height for the table itself
        table_content_height = (num_data_rows_main_table * estimated_row_height)
        # Add a small buffer for table borders/internal padding if any
        table_total_height = table_header_height + table_content_height + 10 # Increased buffer slightly
        self.main_history_table.setFixedHeight(table_total_height)

        main_calc_layout.addWidget(self.main_history_table)
        
        # Calculate fixed height for the main_calc_group
        group_box_margins = main_calc_group.layout().contentsMargins()
        # Approximate title bar height + top/bottom margins/padding of the group box itself
        group_box_chrome_and_internal_padding = 40 # Increased estimate

        # Add a small overall buffer for the group box
        overall_buffer = 5
        
        fixed_group_height = table_total_height + group_box_margins.top() + group_box_margins.bottom() + group_box_chrome_and_internal_padding + overall_buffer
        main_calc_group.setFixedHeight(fixed_group_height)

        layout.addWidget(main_calc_group, 0) # Stretch factor 0 for main_calc_group

        # --- Room Calculation Info Section ---
        room_calc_group = QGroupBox("Room Calculation Info")
        room_calc_group.setStyleSheet(get_group_box_style())
        room_calc_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # This should take remaining space
        room_calc_layout = QVBoxLayout(room_calc_group)

        self.room_history_table = QTableWidget()
        self.room_history_table.setColumnCount(6)
        self.room_history_table.setHorizontalHeaderLabels([
            "Month", "Room", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill" # Use CSV/Display Names
        ])
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
        self.room_history_table.setAlternatingRowColors(True)
        self.room_history_table.setStyleSheet(get_table_style())
        room_calc_layout.addWidget(self.room_history_table)
        layout.addWidget(room_calc_group)
        
        # Removed final stretch to allow vertical expansion

        return history_tab

    def create_supabase_config_tab(self):
        config_tab = QWidget()
        layout = QVBoxLayout(config_tab)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        header_label = QLabel("Supabase Configuration")
        header_label.setStyleSheet(get_header_style())
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        config_group = QGroupBox("Supabase Credentials")
        config_group.setStyleSheet(get_group_box_style())
        config_layout = QFormLayout(config_group)
        config_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Supabase URL Input
        url_input_layout = QHBoxLayout()
        self.supabase_url_input = QLineEdit()
        self.supabase_url_input.setPlaceholderText("Enter your Supabase Project URL")
        self.supabase_url_input.setStyleSheet(get_line_edit_style())
        self.supabase_url_input.setToolTip("e.g., https://your-project-ref.supabase.co")
        self.supabase_url_input.setEchoMode(QLineEdit.Password) # Mask input
        url_input_layout.addWidget(self.supabase_url_input)

        self.toggle_url_visibility_button = QPushButton("Show")
        self.toggle_url_visibility_button.setCheckable(True)
        self.toggle_url_visibility_button.setFixedWidth(60)
        self.toggle_url_visibility_button.setStyleSheet("QPushButton { background-color: #555; color: white; border: none; border-radius: 4px; padding: 5px; } QPushButton:checked { background-color: #007bff; }")
        self.toggle_url_visibility_button.clicked.connect(lambda: self._toggle_password_visibility(self.supabase_url_input, self.toggle_url_visibility_button))
        url_input_layout.addWidget(self.toggle_url_visibility_button)
        config_layout.addRow("Supabase URL:", url_input_layout)

        # Supabase Key Input
        key_input_layout = QHBoxLayout()
        self.supabase_key_input = QLineEdit()
        self.supabase_key_input.setPlaceholderText("Enter your Supabase Anon Key")
        self.supabase_key_input.setStyleSheet(get_line_edit_style())
        self.supabase_key_input.setToolTip("e.g., eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        self.supabase_key_input.setEchoMode(QLineEdit.Password) # Mask input
        key_input_layout.addWidget(self.supabase_key_input)

        self.toggle_key_visibility_button = QPushButton("Show")
        self.toggle_key_visibility_button.setCheckable(True)
        self.toggle_key_visibility_button.setFixedWidth(60)
        self.toggle_key_visibility_button.setStyleSheet("QPushButton { background-color: #555; color: white; border: none; border-radius: 4px; padding: 5px; } QPushButton:checked { background-color: #007bff; }")
        self.toggle_key_visibility_button.clicked.connect(lambda: self._toggle_password_visibility(self.supabase_key_input, self.toggle_key_visibility_button))
        key_input_layout.addWidget(self.toggle_key_visibility_button)
        config_layout.addRow("Supabase Anon Key:", key_input_layout)

        layout.addWidget(config_group)

        self.save_supabase_config_button = QPushButton("Save Supabase Configuration")
        self.save_supabase_config_button.setStyleSheet(get_button_style())
        self.save_supabase_config_button.setFixedHeight(40)
        self.save_supabase_config_button.clicked.connect(self.save_supabase_config)
        layout.addWidget(self.save_supabase_config_button)

        layout.addStretch(1) # Push content to the top

        self._load_supabase_config_to_ui() # Load existing config on tab creation

        return config_tab

    def _toggle_password_visibility(self, line_edit, button):
        """Toggles the echo mode of a QLineEdit between Normal and Password."""
        if button.isChecked():
            line_edit.setEchoMode(QLineEdit.Normal)
            button.setText("Hide")
        else:
            line_edit.setEchoMode(QLineEdit.Password)
            button.setText("Show")

    def _load_supabase_config_to_ui(self):
        """Loads existing Supabase config from DB and populates UI fields."""
        config = self.db_manager.get_config()
        if config:
            self.supabase_url_input.setText(config.get("SUPABASE_URL", ""))
            self.supabase_key_input.setText(config.get("SUPABASE_KEY", ""))
            print("Loaded Supabase config into UI.")
        else:
            self.supabase_url_input.clear()
            self.supabase_key_input.clear()
            print("No Supabase config found in DB to load into UI.")

    def save_supabase_config(self):
        """Saves the Supabase URL and Key to the database."""
        url = self.supabase_url_input.text().strip()
        key = self.supabase_key_input.text().strip()

        if not url or not key:
            QMessageBox.warning(self, "Input Error", "Supabase URL and Key cannot be empty.")
            return

        try:
            self.db_manager.save_config(url, key)
            QMessageBox.information(self, "Success", "Supabase configuration saved and encrypted successfully!")
            self._initialize_supabase_client() # Re-initialize client with new config
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save Supabase configuration: {e}")
            print(f"Error saving Supabase config: {e}")

    def load_info_to_inputs(self):
        # Determine source (CSV or Supabase)
        source = self.load_info_source_combo.currentText()
        selected_month = self.load_month_combo.currentText()
        selected_year = self.load_year_spinbox.value()

        if source == "Load from PC (CSV)":
            self.load_info_to_inputs_from_csv(selected_month, selected_year)
        elif source == "Load from Cloud":
            if self.supabase:
                self.load_info_to_inputs_from_supabase(selected_month, selected_year)
            else:
                QMessageBox.warning(self, "Supabase Not Configured", "Supabase is not configured. Please go to the 'Supabase Config' tab to set up your credentials.")
        else:
            QMessageBox.warning(self, "Unknown Source", "Please select a valid source to load data from.")

    def load_info_to_inputs_from_csv(self, selected_month, selected_year):
        filename = "meter_calculation_history.csv"
        selected_month_year = f"{selected_month} {selected_year}" # This variable is not used in the current comparison logic
        selected_month = selected_month.strip() # Ensure no leading/trailing spaces from UI
        
        if not os.path.exists(filename):
            QMessageBox.warning(self, "File Not Found", f"{filename} does not exist.")
            return

        try:
            with open(filename, mode='r', newline='', encoding='utf-8') as file: # Added encoding='utf-8'
                reader = csv.DictReader(file)
                found_main = False
                room_data_for_month = []

                # Helper function for robust, case-insensitive CSV value retrieval
                def get_csv_value(row_dict, key_name, default_if_missing_or_empty):
                    for k_original, v_original in row_dict.items():
                        if k_original.lower() == key_name.lower():
                            # Key found, process its value
                            stripped_v = v_original.strip() if isinstance(v_original, str) else ""
                            return stripped_v if stripped_v else default_if_missing_or_empty
                    # Key not found, or initial value was not a string (e.g. None)
                    return default_if_missing_or_empty

                for row in reader:
                    csv_month_year_str = get_csv_value(row, "Month", "")
                    if not csv_month_year_str:
                        continue # Skip row if month string is empty

                    parsed_csv_month_full = None
                    parsed_csv_year_full = None

                    try:
                        # Attempt 1: Parse "Month YYYY" format (e.g., "January 2025")
                        parts = csv_month_year_str.split(' ', 1)
                        if len(parts) == 2 and len(parts[1]) == 4 and parts[1].isdigit():
                            month_str, year_str = parts
                            parsed_csv_month_full = dt_class.strptime(month_str, '%B').strftime('%B') # Validate full month name
                            parsed_csv_year_full = year_str
                        else:
                            # If not "Month YYYY", raise error to try "Mon-YY"
                            raise ValueError("Not Month YYYY format")
                            
                    except ValueError:
                        try:
                            # Attempt 2: Parse "Mon-YY" format (e.g., "Jan-25")
                            csv_month_abbr, csv_year_short = csv_month_year_str.split('-', 1)
                            if not (len(csv_year_short) == 2 and csv_year_short.isdigit()):
                                continue # Invalid "Mon-YY" year format

                            parsed_csv_month_full = dt_class.strptime(csv_month_abbr, '%b').strftime('%B')
                            parsed_csv_year_full = "20" + csv_year_short
                        except ValueError:
                            # Both parsing attempts failed
                            continue # Skip this row

                    if parsed_csv_month_full and parsed_csv_year_full:
                        # Compare with UI selected month (full name) and year (as string)
                        if parsed_csv_month_full.lower() == selected_month.lower() and \
                           parsed_csv_year_full == str(selected_year):
                            if not found_main: # Load main data only once
                                # Populate main calculation inputs
                                self.month_combo.setCurrentText(selected_month) # Set main tab's month
                                self.year_spinbox.setValue(selected_year)     # Set main tab's year
                                
                                # Read all meter/diff values that exist in the CSV file
                                meter_values = []
                                diff_values = []
                                
                                # Check for meter-X values until we don't find any more
                                i = 1
                                while True:
                                    meter_value = get_csv_value(row, f"Meter-{i}", None)
                                    if meter_value is None:
                                        break
                                    meter_values.append(meter_value)
                                    i += 1
                                    
                                # Check for diff-X values until we don't find any more    
                                i = 1
                                while True:
                                    diff_value = get_csv_value(row, f"Diff-{i}", None)
                                    if diff_value is None:
                                        break
                                    diff_values.append(diff_value)
                                    i += 1
                                
                                # Fall back to the minimum of 3 pairs if none found
                                if not meter_values:
                                    meter_values = ["0", "0", "0"]
                                if not diff_values:
                                    diff_values = ["0", "0", "0"]
                                
                                # Set the spinbox values to match the number of meter/diff entries
                                # Ensure we don't exceed spinbox maximum values
                                num_meters = min(len(meter_values), self.meter_count_spinbox.maximum())
                                num_diffs = min(len(diff_values), self.diff_count_spinbox.maximum())
                                
                                # Update meter spinbox without triggering value change handler
                                self.meter_count_spinbox.blockSignals(True)
                                self.meter_count_spinbox.setValue(num_meters)
                                self.meter_count_spinbox.blockSignals(False)
                                
                                # Update diff spinbox without triggering value change handler
                                self.diff_count_spinbox.blockSignals(True)
                                self.diff_count_spinbox.setValue(num_diffs)
                                self.diff_count_spinbox.blockSignals(False)
                                
                                # Manually update the meter and diff inputs
                                self.update_meter_inputs(num_meters)
                                self.update_diff_inputs(num_diffs)
                                
                                # Set the values for each meter entry
                                for i, meter_edit in enumerate(self.meter_entries):
                                    if i < len(meter_values):
                                        meter_edit.setText(meter_values[i])
                                
                                # Set the values for each diff entry
                                for i, diff_edit in enumerate(self.diff_entries):
                                    if i < len(diff_values):
                                        diff_edit.setText(diff_values[i])
                                            
                                # Set additional amount
                                self.additional_amount_input.setText(get_csv_value(row, "Added Amount", "0"))
                                found_main = True

                            # Collect room data if present (only if month/year matched)
                            room_name_csv = get_csv_value(row, "Room Name", "")
                            # Case-insensitive check for "N/A"
                            if room_name_csv and room_name_csv.upper() != "N/A":
                                 # Check if room_entries is initialized and has enough space
                                if hasattr(self, 'room_entries'):
                                    # Check for duplicates before adding
                                    is_duplicate = False
                                    for existing_room in room_data_for_month:
                                        if (existing_room["name"] == room_name_csv and
                                            existing_room["present"] == get_csv_value(row, "Present Unit", "") and
                                            existing_room["previous"] == get_csv_value(row, "Previous Unit", "")):
                                            is_duplicate = True
                                            break
                                    
                                    # Only add if not a duplicate
                                    if not is_duplicate:
                                        room_data_for_month.append({
                                            "name": room_name_csv, # Already processed by get_csv_value
                                            "present": get_csv_value(row, "Present Unit", ""),
                                            "previous": get_csv_value(row, "Previous Unit", "")
                                        })
                
                if not found_main:
                    QMessageBox.information(self, "Data Not Found", f"No data found for {selected_month_year} in {filename}.")
                    return

                # Populate room inputs if data was found
                if room_data_for_month and hasattr(self, 'room_entries'):
                    # Remove duplicate room entries by creating a set of unique rooms
                    unique_room_data = []
                    room_keys_seen = set()
                    
                    for room in room_data_for_month:
                        # Create a key that uniquely identifies this room's data
                        room_key = (room["name"], room["present"], room["previous"])
                        if room_key not in room_keys_seen:
                            room_keys_seen.add(room_key)
                            unique_room_data.append(room)
                    
                    # Use only the unique room data
                    room_data_for_month = unique_room_data
                    num_rooms_to_load = len(room_data_for_month)
                    # Check if num_rooms_spinbox exists before setting value
                    if hasattr(self, 'num_rooms_spinbox'):
                        # Block signals to prevent update_room_inputs from being called twice
                        self.num_rooms_spinbox.blockSignals(True)
                        self.num_rooms_spinbox.setValue(num_rooms_to_load)
                        self.num_rooms_spinbox.blockSignals(False)
                        
                        # Manually update room inputs to create the correct number of widgets
                        self.update_room_inputs()
                        
                        # Now populate the room data
                        for i, room_csv_data in enumerate(room_data_for_month):
                            if i < len(self.room_entries): # Check bounds
                                present_entry, previous_entry = self.room_entries[i]
                                # Find the corresponding group box to set the title (room name)
                                room_group_widget = self.rooms_scroll_layout.itemAtPosition(i // 3, i % 3).widget()
                                if isinstance(room_group_widget, QGroupBox):
                                    room_group_widget.setTitle(room_csv_data["name"]) # name is already stripped
                                present_entry.setText(room_csv_data["present"]) # present is already stripped
                                previous_entry.setText(room_csv_data["previous"]) # previous is already stripped
                    else:
                        print("Warning: num_rooms_spinbox not found during CSV load.")

                elif hasattr(self, 'num_rooms_spinbox'): # If no room data found, reset to 1 room
                    # Block signals to prevent update_room_inputs from being called twice
                    self.num_rooms_spinbox.blockSignals(True)
                    self.num_rooms_spinbox.setValue(1)
                    self.num_rooms_spinbox.blockSignals(False)
                    
                    # Manually update room inputs to create the correct number of widgets
                    self.update_room_inputs()
                    
                    # No need to clear entries as update_room_inputs already created fresh ones


                QMessageBox.information(self, "Load Successful", f"Data for {selected_month_year} loaded into input fields.")

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load data from CSV: {e}\n{traceback.format_exc()}")

    def load_info_to_inputs_from_supabase(self, selected_month, selected_year):
        if not self.supabase:
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized. Cannot load data.")
            return
            
        # Check if we're online before attempting Supabase operations
        if not self.check_internet_connectivity():
            QMessageBox.warning(self, "Network Error", 
                             "No internet connection detected. Please check your network connection and try again.\n\n"
                             "Tip: You can still use local CSV files for saving and loading data when offline.")
            return

        try:
            # Fetch main calculation data
            print(f"Fetching main data for {selected_month} {selected_year} from Supabase...")
            response_main = self.supabase.table("main_calculations") \
                                .select("*") \
                                .eq("month", selected_month) \
                                .eq("year", selected_year) \
                                .limit(1) \
                                .execute()

            if not response_main.data:
                QMessageBox.information(self, "Data Not Found", f"No data found for {selected_month} {selected_year} in Cloud.")
                return

            main_data = response_main.data[0]
            main_calc_id = main_data.get('id')
            print(f"Found main data with ID: {main_calc_id}")

            # Populate main calculation inputs using DB column names
            self.month_combo.setCurrentText(main_data.get("month", selected_month))
            self.year_spinbox.setValue(main_data.get("year", selected_year))
            
            # Get the default and additional meter/difference values
            meter_values = [
                main_data.get("meter1_reading", "") or "",
                main_data.get("meter2_reading", "") or "",
                main_data.get("meter3_reading", "") or ""
            ]
            diff_values = [
                main_data.get("diff1", "") or "",
                main_data.get("diff2", "") or "",
                main_data.get("diff3", "") or ""
            ]
            
            # Check for extra meter readings and diff readings (added in JSON format)
            extra_meter_readings = main_data.get("extra_meter_readings", None)
            extra_diff_readings = main_data.get("extra_diff_readings", None)
            
            # Parse extra values if they exist
            if extra_meter_readings:
                try:
                    extra_meters = json.loads(extra_meter_readings)
                    if isinstance(extra_meters, list):
                        meter_values.extend(extra_meters)
                except Exception as e:
                    print(f"Error parsing extra meter readings: {e}")
            
            if extra_diff_readings:
                try:
                    extra_diffs = json.loads(extra_diff_readings)
                    if isinstance(extra_diffs, list):
                        diff_values.extend(extra_diffs)
                except Exception as e:
                    print(f"Error parsing extra diff readings: {e}")
            
            # Set the spinbox values to match the number of meter/diff entries
            # Ensure we don't exceed spinbox maximum values
            num_meters = min(len(meter_values), self.meter_count_spinbox.maximum())
            num_diffs = min(len(diff_values), self.diff_count_spinbox.maximum())
            
            # Update meter spinbox without triggering value change handler
            self.meter_count_spinbox.blockSignals(True)
            self.meter_count_spinbox.setValue(num_meters)
            self.meter_count_spinbox.blockSignals(False)
            
            # Update diff spinbox without triggering value change handler
            self.diff_count_spinbox.blockSignals(True)
            self.diff_count_spinbox.setValue(num_diffs)
            self.diff_count_spinbox.blockSignals(False)
            
            # Manually update the meter and diff inputs
            self.update_meter_inputs(num_meters)
            self.update_diff_inputs(num_diffs)
            
            # Set the values for each meter entry
            for i, meter_edit in enumerate(self.meter_entries):
                if i < len(meter_values):
                    meter_edit.setText(str(meter_values[i]))
            
            # Set the values for each diff entry
            for i, diff_edit in enumerate(self.diff_entries):
                if i < len(diff_values):
                    diff_edit.setText(str(diff_values[i]))
            
            # Set the additional amount
            self.additional_amount_input.setText(str(main_data.get("additional_amount", "") or ""))

            # Fetch related room calculation data
            room_data_list = []
            if main_calc_id:
                print(f"Fetching room data for main_calc_id: {main_calc_id}...")
                response_rooms = self.supabase.table("room_calculations") \
                                     .select("*") \
                                     .eq("main_calculation_id", main_calc_id) \
                                     .order("id") \
                                     .execute()
                if response_rooms.data:
                    room_data_list = response_rooms.data
                    print(f"Found {len(room_data_list)} room records.")
                else:
                    print("No room records found for this main calculation.")

            # Populate room inputs using DB column names
            if room_data_list and hasattr(self, 'room_entries') and hasattr(self, 'num_rooms_spinbox'):
                # Remove duplicate room entries by creating a set of unique rooms
                unique_room_data = []
                room_keys_seen = set()
                
                for room in room_data_list:
                    # Create a key that uniquely identifies this room's data
                    room_key = (room.get("room_name", ""), 
                               str(room.get("present_reading_room", "")), 
                               str(room.get("previous_reading_room", "")))
                    if room_key not in room_keys_seen:
                        room_keys_seen.add(room_key)
                        unique_room_data.append(room)
                
                # Use only the unique room data
                room_data_list = unique_room_data
                num_rooms_to_load = len(room_data_list)
                
                # Block signals to prevent update_room_inputs from being called twice
                self.num_rooms_spinbox.blockSignals(True)
                self.num_rooms_spinbox.setValue(num_rooms_to_load)
                self.num_rooms_spinbox.blockSignals(False)
                
                # Manually update room inputs to create the correct number of widgets
                self.update_room_inputs()
                
                # Now populate the room data
                for i, room_db_data in enumerate(room_data_list):
                    if i < len(self.room_entries):
                        present_entry, previous_entry = self.room_entries[i]
                        room_group_widget = self.rooms_scroll_layout.itemAtPosition(i // 3, i % 3).widget()
                        
                        if isinstance(room_group_widget, QGroupBox):
                            room_group_widget.setTitle(room_db_data.get("room_name", f"Room {i+1}"))
                        present_entry.setText(str(room_db_data.get("present_reading_room", "") or "")) # Use DB name
                        previous_entry.setText(str(room_db_data.get("previous_reading_room", "") or "")) # Use DB name
            
            elif hasattr(self, 'num_rooms_spinbox'): # If no room data found, reset to 1 room
                # Block signals to prevent update_room_inputs from being called twice
                self.num_rooms_spinbox.blockSignals(True)
                self.num_rooms_spinbox.setValue(1)
                self.num_rooms_spinbox.blockSignals(False)
                
                # Manually update room inputs to create the correct number of widgets
                self.update_room_inputs()
                
                # No need to clear entries as update_room_inputs already created fresh ones

            QMessageBox.information(self, "Load Successful", f"Data for {selected_month} {selected_year} loaded from Cloud.")

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to load data from Supabase: {e.message}\nDetails: {e.details}")
            print(f"Supabase API Error: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"An unexpected error occurred while loading from Supabase: {e}\n{traceback.format_exc()}")
            print(f"Unexpected Supabase Load Error: {e}\n{traceback.format_exc()}")


    def load_history(self):
        try:
            selected_month = self.history_month_combo.currentText()
            selected_year_val = self.history_year_spinbox.value()
            source = self.load_history_source_combo.currentText()

            if source == "Load from PC (CSV)":
                self.load_history_tables_from_csv(selected_month, selected_year_val)
            elif source == "Load from Cloud":
                if self.supabase:
                    self.load_history_tables_from_supabase(selected_month, selected_year_val)
                else:
                    QMessageBox.warning(self, "Supabase Not Configured", "Supabase is not configured. Please go to the 'Supabase Config' tab to set up your credentials.")
            else:
                QMessageBox.warning(self, "Unknown Source", "Please select a valid source to load history from.")
        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"An error occurred while loading history: {e}\n{traceback.format_exc()}")


    def load_history_tables_from_csv(self, selected_month, selected_year_val):
        # Reverted logic based on previous working version from previus/HomeUnitCalculator.py
        filename = "meter_calculation_history.csv"
        if not os.path.isfile(filename):
            QMessageBox.information(self, "No History", "No history file found.")
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)
            return

        try:
            is_all_months = (selected_month == "All")
            # Check if "All" is selected for year. The specialValueText is "All" when value is minimum.
            is_all_years = (selected_year_val == self.history_year_spinbox.minimum() and 
                            self.history_year_spinbox.text() == self.history_year_spinbox.specialValueText())
            selected_year_str = str(selected_year_val) if not is_all_years else ""

            with open(filename, mode='r', newline='') as file:
                reader = csv.reader(file)
                header = next(reader, None) # Read/skip header
                if not header:
                    raise ValueError("CSV file is empty or missing header.")
                
                history = list(reader) # Read all data rows

            filtered_history = []
            for row in history:
                if not row or not row[0]: # Skip empty rows or rows without a month/year
                    continue
                month_year = row[0].split()
                if len(month_year) == 2:
                    month, year_str = month_year
                    match_month = is_all_months or (month == selected_month)
                    match_year = is_all_years or (year_str == selected_year_str)
                    if match_month and match_year:
                        filtered_history.append(row)

            # Logic to load all rooms associated with a main entry
            main_history_dict = {}
            room_history_for_display = [] # This will store all rooms
            last_main_month_year_key = None

            for row_index, row in enumerate(filtered_history):
                if not row or len(row) < 1:
                    print(f"Skipping empty or invalid row at index {row_index}: {row}")
                    continue

                current_row_month_year_key = row[0].strip() if row[0] and row[0].strip() else None

                # If current_row_month_year_key is present, it's a potential main entry row
                if current_row_month_year_key:
                    if current_row_month_year_key not in main_history_dict:
                        # Determine where the room columns actually start
                        ROOM_NAME_IDX = header.index("Room Name") if "Room Name" in header else 12
                        
                        # Slice main row up to, but not including, the room columns
                        main_data_for_table = row[:ROOM_NAME_IDX]
                        while len(main_data_for_table) < ROOM_NAME_IDX:
                            main_data_for_table.append("")
                        main_history_dict[current_row_month_year_key] = main_data_for_table[:ROOM_NAME_IDX]
                    last_main_month_year_key = current_row_month_year_key # Update last seen main key

                # Check for room data in this row
                # Get the Room Name column index
                ROOM_NAME_IDX = header.index("Room Name") if "Room Name" in header else 12
                
                # Get room name value if it exists
                room_name_csv = row[ROOM_NAME_IDX] if len(row) > ROOM_NAME_IDX else ""
                
                # Check if this row contains room data
                is_room_row_candidate = (
                    len(row) > ROOM_NAME_IDX
                    and room_name_csv
                    and room_name_csv.strip() 
                    and room_name_csv.strip().lower() != "n/a"
                )

                if is_room_row_candidate:
                    # Determine the effective month_year_key for this room
                    # If row[0] is populated, use that. Otherwise, use the last_main_month_year_key.
                    effective_month_year_for_room = current_row_month_year_key if current_row_month_year_key else last_main_month_year_key

                    if effective_month_year_for_room:
                        # Room table expects: Month-Year, Room Name, Present, Previous, Units, Cost
                        room_data_to_add = [effective_month_year_for_room]
                        # Room details start from Room Name index
                        ROOM_END_IDX = ROOM_NAME_IDX + 5  # Room Name + Present + Previous + Units + Cost = 5 columns
                        room_details_from_csv = row[ROOM_NAME_IDX:ROOM_END_IDX] if len(row) >= ROOM_END_IDX else row[ROOM_NAME_IDX:]
                        room_data_to_add.extend(room_details_from_csv)
                        
                        # Ensure room_data_to_add has exactly 6 columns for the table
                        while len(room_data_to_add) < 6:
                            room_data_to_add.append("")
                        
                        room_history_for_display.append(room_data_to_add[:6])
                    else:
                        print(f"Warning: Room data found but no effective month-year key to associate it with: {row}")
                
                elif not current_row_month_year_key and not is_room_row_candidate:
                     print(f"Skipping row with no month_year_key and no identifiable room data: {row}")


            # Convert main_history_dict.values() to a list for populating the table
            main_history_list = list(main_history_dict.values())
            
            # Populate Main History Table
            self.main_history_table.setRowCount(0) # Clear table
            self.main_history_table.setRowCount(len(main_history_list))
            for r_idx, r_data in enumerate(main_history_list):
                for c_idx, item in enumerate(r_data):
                    self.main_history_table.setItem(r_idx, c_idx, QTableWidgetItem(str(item or "")))

            # Populate Room History Table
            self.room_history_table.setRowCount(0) # Clear table
            self.room_history_table.setRowCount(len(room_history_for_display))
            for r_idx, r_data in enumerate(room_history_for_display):
                for c_idx, item in enumerate(r_data):
                    self.room_history_table.setItem(r_idx, c_idx, QTableWidgetItem(str(item or "")))

            if not main_history_list and not room_history_for_display:
                 QMessageBox.information(self, "No Data", "No matching history data found for the selected criteria.")
            # Removed the success message as it might be redundant if data is shown
            # else:
            #      QMessageBox.information(self, "History Loaded", f"Loaded {len(main_history_list)} main records and {len(room_history_for_display)} room records from CSV.")

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load history from CSV: {e}\n{traceback.format_exc()}")
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)


    def load_history_tables_from_supabase(self, selected_month, selected_year_val):
        if not self.supabase:
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized. Cannot load history.")
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)
            return
        
        # Check if we're online before attempting Supabase operations
        if not self.check_internet_connectivity():
            QMessageBox.warning(self, "Network Error", 
                             "No internet connection detected. Please check your network connection and try again.\n\n"
                             "Tip: You can still use local CSV files for viewing history when offline.")
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)
            return

        try: 
            is_all_months = (selected_month == "All")
            is_all_years = (selected_year_val == self.history_year_spinbox.minimum() and 
                            self.history_year_spinbox.text() == self.history_year_spinbox.specialValueText())

            # Ensure 'id' is selected
            query = self.supabase.table("main_calculations").select("id, *, room_calculations(*)") 

            if not is_all_months:
                query = query.eq("month", selected_month)
            if not is_all_years:
                query = query.eq("year", selected_year_val)
            
            query = query.order("year", desc=True).order("month", desc=True) # Order by date

            response = query.execute()

            main_data_for_table = [] # List to hold dicts {id: ..., display_data: [...]}
            room_data_to_display = []
            
            # Prepare data for display first
            if response.data:
                for main_row in response.data:
                     # Format main data for table display using DB column names
                    main_data_for_table.append({
                        "id": main_row.get('id'), # Store ID for button connection
                        "display_data": [
                            f"{main_row.get('month','')} {main_row.get('year','')}",
                            str(main_row.get('meter1_reading', '') or ''), # DB name
                            str(main_row.get('meter2_reading', '') or ''), # DB name
                            str(main_row.get('meter3_reading', '') or ''), # DB name
                            str(main_row.get('diff1', '') or ''), 
                            str(main_row.get('diff2', '') or ''), 
                            str(main_row.get('diff3', '') or ''),
                            str(main_row.get('total_unit_cost', '') or ''), # DB name
                            str(main_row.get('total_diff_units', '') or ''), # DB name
                            f"{main_row.get('per_unit_cost_calculated', 0.0):.2f}" if main_row.get('per_unit_cost_calculated') is not None else '', # DB name
                            str(main_row.get('additional_amount', '') or ''),
                            f"{main_row.get('grand_total_bill', 0.0):.2f}" if main_row.get('grand_total_bill') is not None else '' # DB name
                        ]
                    })
                    
                    # Format room data for table display using DB column names
                    if main_row.get('room_calculations'):
                        for room_row in main_row['room_calculations']:
                             room_data_to_display.append([
                                f"{main_row.get('month','')} {main_row.get('year','')}", # Month Year context
                                room_row.get('room_name', ''),
                                str(room_row.get('present_reading_room', '') or ''), # DB name
                                str(room_row.get('previous_reading_room', '') or ''), # DB name
                                str(room_row.get('units_consumed_room', '') or ''), # DB name
                                f"{room_row.get('cost_room', 0.0):.2f}" if room_row.get('cost_room') is not None else '' # DB name
                            ])


            # Populate Main History Table
            self.main_history_table.setRowCount(0) # Clear existing rows
            for item in main_data_for_table:
                row_position = self.main_history_table.rowCount()
                self.main_history_table.insertRow(row_position)
                
                # Populate data cells (now 12 columns)
                record_id = item.get('id') # Get record_id for storing
                for col_num, data_value in enumerate(item["display_data"]): # item["display_data"] should have 12 items
                    if col_num < 12: # Ensure we don't try to write more than 12 columns
                        table_item = QTableWidgetItem(str(data_value or '')) # Use data_value here
                        if col_num == 0 and record_id: # Store record_id with the first item of the row
                            table_item.setData(Qt.UserRole, record_id)
                        self.main_history_table.setItem(row_position, col_num, table_item)
            
            # Populate Room History Table
            self.room_history_table.setRowCount(0) # Clear existing rows
            # self.room_history_table.setRowCount(len(room_data_to_display)) # Not needed if inserting rows one by one
            for row_data_item in room_data_to_display: # Iterate through room_data_to_display
                row_pos_room = self.room_history_table.rowCount()
                self.room_history_table.insertRow(row_pos_room)
                for col_idx, cell_data in enumerate(row_data_item): # Iterate through items in row_data_item
                    self.room_history_table.setItem(row_pos_room, col_idx, QTableWidgetItem(str(cell_data or '')))

            if not main_data_for_table and not room_data_to_display:
                 QMessageBox.information(self, "No Data", "No matching history data found in Cloud for the selected criteria.")

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to load history from Supabase: {e.message}\nDetails: {e.details}") # Corrected variable name
            print(f"Supabase API Error: {e}")
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"An unexpected error occurred while loading history from Supabase: {e}\n{traceback.format_exc()}")
            print(f"Unexpected Supabase History Load Error: {e}\n{traceback.format_exc()}")
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)


    def save_to_pdf(self):
        month_name = self.month_combo.currentText()
        year_value = self.year_spinbox.value()
        default_filename = f"MeterCalculation_{month_name}_{year_value}.pdf"
        
        def try_save_pdf(path):
            try:
                self.generate_pdf(path)
                QMessageBox.information(self, "PDF Saved", f"Report saved to {path}")
                return True
            except PermissionError as pe:
                # Special handling for permission errors
                QMessageBox.warning(self, "Permission Denied", 
                                  f"Cannot save to {path}\n\nThe file may be open in another program or you don't have write permission to this location. Please close any programs using this file and try again or select a different location.")
                return False
            except Exception as e:
                QMessageBox.critical(self, "PDF Save Error", f"Failed to save PDF: {e}\n{traceback.format_exc()}")
                return False
        
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog  # Using native dialog may help with permissions
        
        # Try until successful or user cancels
        while True:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save PDF", 
                default_filename, 
                "PDF Files (*.pdf);;All Files (*)", 
                options=options
            )
            
            if not file_path:  # User canceled
                break
                
            # Try saving with the chosen path
            if try_save_pdf(file_path):
                break  # Success, exit the loop

    def generate_pdf(self, file_path):
        # Generate a PDF report of the calculations
        # Reduce margins to fit more content
        doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=0.3*inch, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)  # Create a PDF document with reduced margins
        elements = []  # Initialize an empty list to store PDF elements

        # Adjust styles to have slightly larger font sizes
        styles = getSampleStyleSheet()  # Get the default stylesheet
        title_style = ParagraphStyle(  # Create a custom style for the title
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=10,
            alignment=TA_CENTER
        )
        header_style = ParagraphStyle(  # Create a custom style for headers
            'HeaderStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=5,
            alignment=TA_CENTER
        )
        normal_style = ParagraphStyle(  # Create a custom style for normal text
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=2
        ) # Added missing closing parenthesis
        label_style = ParagraphStyle(  # Create a custom style for labels
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=1
        )

        def create_cell(content, bgcolor=colors.lightsteelblue, textcolor=colors.black, style=normal_style, height=0.2*inch):
            # Convert string content to Paragraph object if necessary
            if isinstance(content, str):
                content = Paragraph(content, style)  # Convert string to Paragraph if it's not already
            
            # Create and return a Table object with specified properties
            return Table(
                [[content]],  # Content wrapped in a nested list for single-cell table
                colWidths=[7.5*inch],  # Set column width to 7.5 inches
                rowHeights=[height],  # Set row height to the specified height (default 0.2 inches)
                style=TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), bgcolor),  # Set background color
                    ('BOX', (0,0), (-1,-1), 1, colors.darkblue),  # Add a box around the cell
                    ('TEXTCOLOR', (0,0), (-1,-1), textcolor),  # Set text color
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),  # Vertically align content to middle
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),  # Horizontally align content to left
                    ('LEFTPADDING', (0,0), (-1,-1), 6),  # Set left padding
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),  # Set right padding
                    ('TOPPADDING', (0,0), (-1,-1), 2),  # Set top padding
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),  # Set bottom padding
                ])
            )

        # Title
        elements.append(Paragraph("Meter Calculation Report", title_style))  # Add the title to the PDF
        elements.append(Spacer(1, 0.1*inch))  # Add some space after the title

        # Month
        month_year = f"{self.month_combo.currentText()} {self.year_spinbox.value()}"  # Get the selected month and year
        month_paragraph = Paragraph(f"Month: <font color='red'>{month_year}</font>", header_style)  # Create a paragraph for the month and year
        elements.append(create_cell(month_paragraph, bgcolor=colors.lightsteelblue, height=0.3*inch))  # Add the month and year to the PDF
        elements.append(Spacer(1, 0.05*inch))  # Add some space after the month and year

        # Main Meter Info Headline
        elements.append(Spacer(1, 0.1*inch))  # Add some space before the main meter info
        elements.append(create_cell("Main Meter Info", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))  # Add the main meter info headline

        # Main Meter Info Content - Handle dynamic number of meter entries
        meter_info_left = [
            # One row per existing meter entry (no hard cap)
            *[
                [Paragraph(f"Meter-{i+1} Unit:", normal_style),
                 Paragraph(self.meter_entries[i].text() or '0', normal_style)]
                for i in range(len(self.meter_entries))
            ],
            [Paragraph("Total Difference:", normal_style), Paragraph(f"{self.total_diff_value_label.text() or 'N/A'}", normal_style)],
        ]

        meter_info_right = [  # Create a list for the right side of the main meter info
            [Paragraph("Per Unit Cost:", normal_style), Paragraph(f"{self.per_unit_cost_value_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Total Unit Cost:", normal_style), Paragraph(f"{self.total_unit_value_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Added Amount:", normal_style), Paragraph(f"{self.additional_amount_value_label.text() or 'N/A'}", normal_style)], # Corrected label reference
            [Paragraph("In Total Amount:", normal_style), Paragraph(f"{self.in_total_value_label.text() or 'N/A'}", normal_style)],
        ]

        # Ensure left and right tables have the same number of rows
        max_rows = max(len(meter_info_left), len(meter_info_right))
        while len(meter_info_left) < max_rows:
            meter_info_left.append([Paragraph("", normal_style), Paragraph("", normal_style)])
        while len(meter_info_right) < max_rows:
            meter_info_right.append([Paragraph("", normal_style), Paragraph("", normal_style)])
        
        # Use the actual number of rows based on the number of meter entries
        num_rows = len(meter_info_left)
        main_meter_table = Table(  # Create a table for the main meter info
            [meter_info_left[i] + meter_info_right[i] for i in range(num_rows)],  # Combine left and right info
            colWidths=[2.5*inch, 1.25*inch, 2.5*inch, 1.25*inch],  # Set column widths
            rowHeights=[0.2*inch] * num_rows  # Set row heights
        )

        main_meter_table.setStyle(TableStyle([  # Set the style for the main meter table
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Set background color
            ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),  # Add a box around the table
            ('LINEABOVE', (0, 1), (-1, -1), 1, colors.lightgrey),  # Add lines above each row
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content to middle
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Horizontally align content to left
            ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Set left padding
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Set right padding
            ('TOPPADDING', (0, 0), (-1, -1), 2),  # Set top padding
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),  # Set bottom padding
        ]))

        elements.append(main_meter_table)  # Add the main meter table to the PDF
        elements.append(Spacer(1, 0.1*inch))  # Add some space after the main meter table

        # Room Info Headline
        elements.append(Spacer(1, 0.1*inch))  # Add some space before the room info
        elements.append(create_cell("Room Information", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))  # Add the room info headline

        # Room Info
        room_data = []  # Initialize an empty list to store room data
        for i in range(0, len(self.room_entries), 2):  # Iterate through room entries two at a time
            row = []  # Initialize an empty list for each row (pair of rooms)
            for j in range(2):  # Process two rooms at a time
                if i + j < len(self.room_entries):  # Check if there's a room to process
                    present_entry, previous_entry = self.room_entries[i + j]  # Get the present and previous entries for the room
                    real_unit_label, unit_bill_label = self.room_results[i + j]  # Get the real unit and unit bill labels for the room
                    
                    # Get room name from group box title
                    room_group_widget = self.rooms_scroll_layout.itemAtPosition((i+j) // 3, (i+j) % 3).widget()
                    room_name = room_group_widget.title() if isinstance(room_group_widget, QGroupBox) else f"Room {i+j+1}"


                    # Get the next month name for display
                    month_idx = self.month_combo.currentIndex()
                    next_month_idx = (month_idx + 1) % 12  # Wrap around to January if December
                    next_month_name = self.month_combo.itemText(next_month_idx)
                    
                    # Create header style for room header with dark navy text
                    room_header_style = ParagraphStyle(
                        'RoomHeaderStyle',
                        parent=styles['Normal'],
                        fontSize=10,  # Standard font size
                        textColor=colors.darkblue,  # Dark navy text for header
                        spaceAfter=2,
                        fontName='Helvetica-Bold'
                    )
                    
                    # Create bold style for unit bill - slightly larger but not too big
                    bold_unit_bill_style = ParagraphStyle(
                        'BoldUnitBillStyle',
                        parent=styles['Normal'],
                        fontSize=11,  # Slightly larger font size for the unit bill
                        textColor=colors.black,
                        spaceAfter=2,
                        fontName='Helvetica-Bold'
                    )
                    
                    # Set up first row with Room X and Created: on the same line
                    header_style_left = ParagraphStyle(
                        'HeaderStyleLeft',
                        parent=room_header_style,
                        alignment=0  # 0 = left alignment
                    )
                    
                    header_style_right = ParagraphStyle(
                        'HeaderStyleRight',
                        parent=room_header_style,
                        alignment=2  # 2 = right alignment
                    )
                    
                    # Create style for Created: text (light gray)
                    header_style_right_gray = ParagraphStyle(
                        'HeaderStyleRightGray',
                        parent=room_header_style,
                        alignment=2,  # 2 = right alignment
                        textColor=colors.gray  # Lighter gray color for less prominence
                    )
                    
                    # Create a single row header with Room, Created: and month name all in one line
                    header_row = [
                        Paragraph(f"{room_name}", header_style_left),
                        Paragraph(f"Created: {next_month_name}", header_style_right_gray)
                    ]
                    
                    room_info = [  # Create a list of room information
                        header_row,      # Single row header with all information
                        [Paragraph("Month:", label_style), Paragraph(month_year, normal_style)],  # Month and year
                        [Paragraph("Per-Unit Cost:", label_style), Paragraph(self.per_unit_cost_value_label.text() or 'N/A', normal_style)], # Get cost from main results
                        [Paragraph("Unit:", label_style), Paragraph(real_unit_label.text() or 'N/A', normal_style)],  # Unit
                        [Paragraph("Unit Bill:", label_style), Paragraph(unit_bill_label.text() or 'N/A', bold_unit_bill_style)]  # Unit bill with bold style
                    ]

                    # Define row heights for the single header row plus content rows
                    room_row_heights = [0.3*inch] + [0.2*inch] * 4  # Single header row + content rows
                    
                    room_table = Table(room_info, colWidths=[1.5*inch, 2.15*inch], rowHeights=room_row_heights)  # Create a table for each room with custom row heights
                    room_table.setStyle(TableStyle([  # Set the style for the room table
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightsteelblue),  # Set background color for the header row
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Set background color for the content
                        ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),  # Add a box around the table
                        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),  # Add a line below the header row
                        ('LINEABOVE', (0, 1), (-1, -1), 1, colors.lightgrey),  # Add lines above each content row
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertically align content to middle
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Horizontally align content to left
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),  # Set left padding
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),  # Set right padding
                        ('TOPPADDING', (0, 0), (-1, -1), 2),  # Set top padding
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),  # Set bottom padding
                    ]))
                    row.append(room_table)  # Add the room table to the row
                else:
                    row.append("")  # Add an empty string if there's no room to process
            room_data.append(row)  # Add the row to the room data

        room_table = Table(room_data, colWidths=[3.85*inch, 3.85*inch], spaceBefore=0.05*inch)  # Create a table for all rooms
        room_table.setStyle(TableStyle([  # Set the style for the room table
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Vertically align content to top
        ]))
        elements.append(room_table)  # Add the room table to the PDF

        # Build the PDF document
        doc.build(elements)  # Build the PDF with all the elements

    def handle_edit_record(self, record_id):
        print(f"Attempting to edit record ID: {record_id}")
        if not self.supabase:
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized.")
            return
            
        # Check internet connectivity
        if not self.check_internet_connectivity():
            QMessageBox.warning(self, "Network Error", 
                              "No internet connection detected. Cannot edit records while offline.")
            return

        try:
            # Fetch the specific record including related room data
            response = self.supabase.table("main_calculations") \
                           .select("*, room_calculations(*)") \
                           .eq("id", record_id) \
                           .maybe_single() \
                           .execute()

            if response.data:
                main_data = response.data
                room_data_list = main_data.get("room_calculations", [])
                
                # Create and show the dialog
                dialog = EditRecordDialog(record_id, main_data, room_data_list, parent=self) # Uncommented
                if dialog.exec_() == QDialog.Accepted: # Uncommented
                    print(f"Edit dialog accepted for record {record_id}. Refreshing history.") # Uncommented
                    # Refresh the history view if changes were saved
                    self.load_history() # Uncommented
                else: # Uncommented
                    print(f"Edit dialog cancelled for record {record_id}.") # Uncommented
                # Removed placeholder QMessageBox
                # print("Fetched data for edit:", main_data) # Optional: Keep for debugging if needed

            else:
                QMessageBox.warning(self, "Not Found", f"Record with ID {record_id} not found in the database.")

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to fetch record for editing: {e.message}\nDetails: {e.details}")
            print(f"Supabase API Error on fetch for edit: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred while preparing to edit: {e}\n{traceback.format_exc()}")
            print(f"Unexpected error in handle_edit_record: {e}\n{traceback.format_exc()}")

    def handle_delete_record(self, record_id):
        print(f"Attempting to delete record ID: {record_id}")
        if not self.supabase:
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized.")
            return
            
        # Check internet connectivity
        if not self.check_internet_connectivity():
            QMessageBox.warning(self, "Network Error", 
                              "No internet connection detected. Cannot delete records while offline.")
            return

        # Confirmation Dialog
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                     f"Are you sure you want to permanently delete record ID {record_id} and all its associated room data from the Cloud?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                print(f"Confirmed deletion for record ID: {record_id}")
                # 1. Delete associated room calculations first (CASCADE should handle this, but explicit delete is safer)
                print(f"Deleting room_calculations for main_calculation_id: {record_id}")
                delete_rooms_response = self.supabase.table("room_calculations").delete().eq("main_calculation_id", record_id).execute()
                print(f"Room deletion response: {delete_rooms_response}") # Log response

                # 2. Delete the main calculation record
                print(f"Deleting main_calculations record ID: {record_id}")
                delete_main_response = self.supabase.table("main_calculations").delete().eq("id", record_id).execute()
                print(f"Main deletion response: {delete_main_response}") # Log response
                
                # Basic check (Supabase delete often returns empty data on success)
                # A more robust check might involve checking status codes if the client library provides them easily
                # For now, assume success if no exception is raised.
                
                QMessageBox.information(self, "Delete Successful", f"Record ID {record_id} deleted successfully from the Cloud.")
                
                # Refresh the history view
                self.load_history()
                # else:
                #     QMessageBox.warning(self, "Delete Failed", f"Failed to delete record ID {record_id}. It might have already been deleted.")


            except APIError as e:
                QMessageBox.critical(self, "Supabase API Error", f"Failed to delete record: {e.message}\nDetails: {e.details}")
                print(f"Supabase API Error on delete: {e}")
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"An unexpected error occurred during deletion: {e}\n{traceback.format_exc()}")
                print(f"Unexpected error in handle_delete_record: {e}\n{traceback.format_exc()}")
        else:
            print(f"Deletion cancelled for record ID: {record_id}")

    def handle_edit_selected_record(self):
        selected_items = self.main_history_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a record from the Main Calculation Info table to edit.")
            return

        # Assuming the record_id is stored in the UserRole of the first item in the selected row
        selected_row = selected_items[0].row()
        first_item_in_row = self.main_history_table.item(selected_row, 0)
        if not first_item_in_row:
            QMessageBox.warning(self, "Error", "Could not retrieve data for the selected row.")
            return
            
        record_id = first_item_in_row.data(Qt.UserRole)

        if record_id:
            # Check if the source is Supabase, as CSV editing is not directly supported by EditRecordDialog
            source = self.load_history_source_combo.currentText()
            if source == "Load from Cloud":
                self.handle_edit_record(record_id) # Call existing Supabase edit logic
            else:
                QMessageBox.information(self, "Not Supported", "Editing records loaded from CSV is not currently supported via this button. Please edit the CSV file directly or load from cloud.")
        else:
            QMessageBox.warning(self, "No Record ID", "Could not find a Record ID for the selected row. Editing may not be supported for this item (e.g., if loaded from CSV without a unique ID).")

    def handle_delete_selected_record(self):
        selected_items = self.main_history_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a record from the Main Calculation Info table to delete.")
            return

        selected_row = selected_items[0].row()
        first_item_in_row = self.main_history_table.item(selected_row, 0)
        if not first_item_in_row:
            QMessageBox.warning(self, "Error", "Could not retrieve data for the selected row.")
            return

        record_id = first_item_in_row.data(Qt.UserRole)

        if record_id:
            # Check if the source is Supabase
            source = self.load_history_source_combo.currentText()
            if source == "Load from Cloud":
                self.handle_delete_record(record_id) # Call existing Supabase delete logic
            else:
                QMessageBox.information(self, "Not Supported", "Deleting records loaded from CSV is not currently supported via this button. Please manage the CSV file directly or load from cloud.")
        else:
            # For CSV, we might not have a stored record_id.
            # We could offer to remove the row from the view, but not from the file.
            # Or, identify by month/year if that's unique enough for CSV context.
            # For now, indicate it's not supported for items without a clear ID.
            QMessageBox.warning(self, "No Record ID", "Could not find a Record ID for the selected row. Deletion may not be supported for this item (e.g., if loaded from CSV without a unique ID).")


    def setup_navigation(self):
        # --- Main Calculation Tab Navigation ---
        # Ensure all widgets are created before calling this
        if hasattr(self, 'meter_entries') and hasattr(self, 'diff_entries') and \
           hasattr(self, 'additional_amount_input') and hasattr(self, 'main_calculate_button'):

            # Build a flat sequence of all input fields for navigation
            main_tab_fields_in_order = []
            
            # First add all meter inputs
            for meter_edit in self.meter_entries:
                main_tab_fields_in_order.append(meter_edit)
                
            # Then add all diff inputs
            for diff_edit in self.diff_entries:
                main_tab_fields_in_order.append(diff_edit)
            
            # Then add the additional amount input
            main_tab_fields_in_order.append(self.additional_amount_input)

            if main_tab_fields_in_order and isinstance(self.main_calculate_button, CustomNavButton):
                calc_btn = self.main_calculate_button

                # Clear existing links for all fields involved
                all_main_tab_line_edits = main_tab_fields_in_order.copy()
                for widget in all_main_tab_line_edits:
                    widget.next_widget_on_enter = None
                    widget.up_widget = None
                    widget.down_widget = None
                    widget.left_widget = None
                    widget.right_widget = None
                calc_btn.next_widget_on_enter = None

                # Enter/Return Key Sequence (Field1 -> Field2 -> ... -> LastField -> Button -> Field1)
                # Connect each field to the next one in sequence
                for i, widget in enumerate(main_tab_fields_in_order):
                    if i < len(main_tab_fields_in_order) - 1:
                        widget.next_widget_on_enter = main_tab_fields_in_order[i+1]
                    else:
                        # Last widget connects to the calculate button
                        widget.next_widget_on_enter = calc_btn
                
                # Calculate button loops back to the first input field
                if main_tab_fields_in_order:
                    calc_btn.next_widget_on_enter = main_tab_fields_in_order[0]

                # Arrow Key Navigation (Up/Down Fields Only, in a single sequence)
                # Connect each field to the one above and below it
                for i, widget in enumerate(main_tab_fields_in_order):
                    # Down navigation (to next widget)
                    if i < len(main_tab_fields_in_order) - 1:
                        widget.down_widget = main_tab_fields_in_order[i+1]
                    else: # Last widget, loops to first
                        widget.down_widget = main_tab_fields_in_order[0]
                    
                    # Up navigation (to previous widget)
                    if i > 0:
                        widget.up_widget = main_tab_fields_in_order[i-1]
                    else: # First widget, loops to last
                        widget.up_widget = main_tab_fields_in_order[-1]

                # Ensure Left/Right are None for all these fields so CustomLineEdit uses super() for them
                for widget_in_main_tab in all_main_tab_line_edits: # all_main_tab_line_edits defined earlier
                    widget_in_main_tab.left_widget = None
                    widget_in_main_tab.right_widget = None

        # Call to connect tab change signal for initial focus
        if not hasattr(self, '_tab_change_connected'): # Connect only once
            self.tab_widget.currentChanged.connect(self.set_focus_on_tab_change)
            self._tab_change_connected = True
        
        # Set initial focus on the first tab's first input field
        self.set_focus_on_tab_change(0)


    def set_focus_on_tab_change(self, index):
        current_tab = self.tab_widget.widget(index)
        if current_tab:
            first_input = current_tab.findChild(CustomLineEdit)
            if not first_input:
                first_input = current_tab.findChild(QSpinBox)
            
            if first_input:
                first_input.setFocus()
                if isinstance(first_input, QLineEdit):
                    first_input.selectAll()


    def add_accessibility_features(self, entries):
        for i, entry in enumerate(entries):
            if i + 1 < len(entries):
                entry.next_widget = entries[i+1]
            if i - 1 >= 0:
                entry.previous_widget = entries[i-1]

    def focus_next_entry(self):
        current = self.focusWidget()
        if isinstance(current, CustomLineEdit) and current.next_widget:
            current.next_widget.setFocus()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MeterCalculationApp()
    window.show() # Display the main window
    sys.exit(app.exec_()) # Start the application's event loop
