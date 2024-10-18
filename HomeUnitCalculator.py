import sys
from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor, QKeySequence, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame, QShortcut,
    QAbstractSpinBox, QStyleOptionSpinBox, QStyle
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import csv
import os
from datetime import datetime
from styles import (
    get_stylesheet, get_header_style, get_group_box_style,
    get_line_edit_style, get_button_style, get_results_group_style,
    get_room_group_style, get_month_info_style, get_table_style, get_label_style, get_custom_spinbox_style,
    get_room_selection_style
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
        # Initialize next and previous widget references
        self.next_widget = None
        self.previous_widget = None
        # Apply custom style sheet
        self.setStyleSheet(get_line_edit_style())

    def keyPressEvent(self, event):
        # Handle key press events for the custom line edit
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down, Qt.Key_Right):
            # If the pressed key is Enter, Return, Down arrow, or Right arrow
            if self.next_widget:
                # If there's a next widget defined
                self.next_widget.setFocus()  # Set focus to the next widget
                return  # Exit the method
        elif event.key() in (Qt.Key_Up, Qt.Key_Left):
            # If the pressed key is Up arrow or Left arrow
            if self.previous_widget:
                # If there's a previous widget defined
                self.previous_widget.setFocus()  # Set focus to the previous widget
                return  # Exit the method
        super().keyPressEvent(event)  # Call the parent class's keyPressEvent method for other keys

    def focusInEvent(self, event):
        # Handle focus in events for the custom line edit
        super().focusInEvent(event)  # Call the parent class's focusInEvent method
        self.ensureWidgetVisible()  # Ensure this widget is visible when it receives focus

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

# Main application class
class MeterCalculationApp(QMainWindow):
    def __init__(self):
        # Call the parent class constructor
        super().__init__()

        # Set the window title
        self.setWindowTitle("Meter Calculation Application")
        # Set the window size and position (x, y, width, height)
        self.setGeometry(300, 100, 1300, 800)
        
        # Set the window icon using the resource_path function to locate the icon file
        self.setWindowIcon(QIcon(resource_path("icons/icon.png")))
        # Apply the stylesheet to the entire application
        self.setStyleSheet(get_stylesheet())

        # Initialize the user interface
        self.init_ui()
        # Set up the navigation for the application
        self.setup_navigation()

    def init_ui(self):
        # Initialize the main user interface
        central_widget = QWidget(self)  # Create a central widget for the main window
        self.setCentralWidget(central_widget)  # Set the central widget for the main window
        main_layout = QVBoxLayout(central_widget)  # Create a vertical layout for the central widget

        # Add header
        header = QLabel("Meter Calculation Application")  # Create a label for the header
        header.setStyleSheet(get_header_style())  # Apply custom style to the header
        main_layout.addWidget(header)  # Add the header to the main layout

        # Create and add tab widget
        self.tab_widget = QTabWidget()  # Create a tab widget to hold different sections
        self.tab_widget.addTab(self.create_main_tab(), "Main Calculation")  # Add the main calculation tab
        self.tab_widget.addTab(self.create_rooms_tab(), "Room Calculations")  # Add the room calculations tab
        self.tab_widget.addTab(self.create_history_tab(), "History")  # Add the history tab
        main_layout.addWidget(self.tab_widget)  # Add the tab widget to the main layout

        # Add Save to PDF button
        save_pdf_button = QPushButton("Save to PDF")  # Create a button for saving to PDF
        save_pdf_button.setIcon(QIcon(resource_path("icons/save_icon.png")))  # Set an icon for the save button
        save_pdf_button.clicked.connect(self.save_to_pdf)  # Connect the button click to the save_to_pdf method
        main_layout.addWidget(save_pdf_button)  # Add the save button to the main layout

    def create_main_tab(self):
        # Create the main calculation tab
        main_tab = QWidget()  # Create a new QWidget for the main tab
        main_layout = QVBoxLayout(main_tab)  # Create a vertical layout for the main tab
        main_layout.setSpacing(20)  # Set spacing between layout items to 20 pixels
        main_layout.setContentsMargins(20, 20, 20, 20)  # Set margins for the layout

         # Create a horizontal layout for the top section
        top_layout = QHBoxLayout()  

        # Add Date Selection group
        filter_group = QGroupBox("Date Selection")  # Create a group box for date selection
        filter_group.setStyleSheet(get_group_box_style())  # Apply custom style to the group box
        filter_layout = QHBoxLayout()  # Create a horizontal layout for the filter group
        filter_group.setLayout(filter_layout)  # Set the horizontal layout for the filter group

        # Add Month selection
        month_label = QLabel("Month:")  # Create a label for month selection
        month_label.setStyleSheet(get_label_style())  # Apply custom style to the month label
        self.month_combo = QComboBox()  # Create a combo box for month selection
        self.month_combo.addItems([  # Add month names to the combo box
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())  # Apply custom style to the month combo box

        # Add Year selection
        year_label = QLabel("Year:")  # Create a label for year selection
        year_label.setStyleSheet(get_label_style())  # Apply custom style to the year label
        self.year_spinbox = QSpinBox()  # Create a spin box for year selection
        self.year_spinbox.setRange(2000, 2100)  # Set the range of years from 2000 to 2100
        self.year_spinbox.setValue(datetime.now().year)  # Set the current year as default value
        self.year_spinbox.setStyleSheet(get_month_info_style())  # Apply custom style to the year spin box

        # Add widgets to filter layout
        filter_layout.addWidget(month_label)  # Add month label to the filter layout
        filter_layout.addWidget(self.month_combo)  # Add month combo box to the filter layout
        filter_layout.addSpacing(20)  # Add 20 pixels of spacing
        filter_layout.addWidget(year_label)  # Add year label to the filter layout
        filter_layout.addWidget(self.year_spinbox)  # Add year spin box to the filter layout
        filter_layout.addStretch(1)  # Add stretchable space at the end

        top_layout.addWidget(filter_group)  # Add the filter group to the main layout

        # Additional Amount group
        amount_group = self.create_additional_amount_group()
        top_layout.addWidget(amount_group)  # Add the additional amount group to the top layout

        # Add the top layout to the main layout
        main_layout.addLayout(top_layout)

        # Add Meter and Difference Readings
        readings_layout = QHBoxLayout()  # Create a horizontal layout for readings
        readings_layout.setSpacing(20)  # Set spacing between items in the readings layout

        meter_group = self.create_meter_group()  # Create the meter readings group
        readings_layout.addWidget(meter_group)  # Add meter group to the readings layout

        diff_group = self.create_diff_group()  # Create the difference readings group
        readings_layout.addWidget(diff_group)  # Add difference group to the readings layout

        main_layout.addLayout(readings_layout)  # Add the readings layout to the main layout

        # Add Calculate button
        calculate_button = QPushButton("Calculate")  # Create a calculate button
        calculate_button.setIcon(QIcon(resource_path("icons/calculate_icon.png")))  # Set icon for the calculate button
        calculate_button.clicked.connect(self.calculate_main)  # Connect button click to calculate_main method
        calculate_button.setStyleSheet(get_button_style())  # Apply custom style to the button
        calculate_button.setFixedHeight(50)  # Set fixed height for the button
        main_layout.addWidget(calculate_button)  # Add the calculate button to the main layout

        # Add Results section
        results_group = self.create_results_group()  # Create the results group
        main_layout.addWidget(results_group)  # Add the results group to the main layout

        # Add stretch to push everything to the top
        main_layout.addStretch(1)  # Add stretchable space at the bottom

        return main_tab  # Return the created main tab
    

    def create_additional_amount_group(self):
        amount_group = QGroupBox("Additional Amount")
        amount_group.setStyleSheet(get_group_box_style())
        amount_layout = QHBoxLayout()
        amount_group.setLayout(amount_layout)

        amount_label = QLabel("Additional Amount:")
        amount_label.setStyleSheet(get_label_style())
        self.additional_amount_input = CustomLineEdit()
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
            return int(self.additional_amount_input.text()) if self.additional_amount_input.text() else 0
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric value for the additional amount.")
            return 0

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

    def create_meter_group(self):
        # Create the Meter Readings group
        meter_group = QGroupBox("Meter Readings")  # Create a QGroupBox for meter readings
        meter_group.setStyleSheet(get_group_box_style())  # Apply custom style to the group box
        meter_layout = QFormLayout()  # Create a form layout for organizing the meter entries
        meter_layout.setSpacing(10)  # Set spacing between form layout items
        self.meter_entries = []  # Initialize an empty list to store meter entry widgets
        for i in range(3):  # Loop 3 times to create 3 meter entry fields
            meter_entry = CustomLineEdit()  # Create a custom line edit widget for each meter entry
            meter_entry.setPlaceholderText(f"Enter meter {i+1} reading")  # Set placeholder text for the entry
            meter_layout.addRow(f"Meter {i+1} Reading:", meter_entry)  # Add a labeled row to the form layout
            self.meter_entries.append(meter_entry)  # Add the entry widget to the list of meter entries
        meter_group.setLayout(meter_layout)  # Set the form layout as the layout for the group box
        return meter_group  # Return the created and configured group box
    
    def create_diff_group(self):
        # Create the Difference Readings group
        diff_group = QGroupBox("Difference Readings")  # Create a QGroupBox for difference readings
        diff_group.setStyleSheet(get_group_box_style())  # Apply custom style to the group box
        diff_layout = QFormLayout()  # Create a form layout for organizing the difference entries
        diff_layout.setSpacing(10)  # Set spacing between form layout items
        self.diff_entries = []  # Initialize an empty list to store difference entry widgets
        for i in range(3):  # Loop 3 times to create 3 difference entry fields
            diff_entry = CustomLineEdit()  # Create a custom line edit widget for each difference entry
            diff_entry.setPlaceholderText(f"Enter difference {i+1}")  # Set placeholder text for the entry
            diff_layout.addRow(f"Difference {i+1}:", diff_entry)  # Add a labeled row to the form layout
            self.diff_entries.append(diff_entry)  # Add the entry widget to the list of difference entries
        diff_group.setLayout(diff_layout)  # Set the form layout as the layout for the group box
        return diff_group  # Return the created and configured group box

    def create_results_group(self):
        # Create the Results group
        results_group = QGroupBox("Results")  # Create a QGroupBox for the results
        results_layout = QHBoxLayout()  # Create a horizontal layout for the results
        results_layout.setSpacing(50)  # Set spacing between items in the layout
        
        # Create labels for titles and values
        total_unit_title = QLabel("Total Unit Cost")  # Create a label for total unit cost title
        self.total_unit_label = QLabel("N/A")  # Create a label to display total unit cost value
        total_diff_title = QLabel("Total Difference")  # Create a label for total difference title
        self.total_diff_label = QLabel("N/A")  # Create a label to display total difference value
        per_unit_cost_title = QLabel("Per Unit Cost")  # Create a label for per unit cost title
        self.per_unit_cost_label = QLabel("N/A")  # Create a label to display per unit cost value
        added_amount_title = QLabel("Added Amount")
        self.added_amount_label = QLabel("N/A")
        in_total_title = QLabel("In Total")
        self.in_total_label = QLabel("N/A")

        # Create vertical layouts for each result
        for title, value in [
            (total_unit_title, self.total_unit_label),
            (total_diff_title, self.total_diff_label),
            (per_unit_cost_title, self.per_unit_cost_label),
            (added_amount_title, self.added_amount_label),
            (in_total_title, self.in_total_label)
        ]:
            item_layout = QVBoxLayout()  # Create a vertical layout for each result pair
            item_layout.addWidget(title)  # Add the title label to the layout
            item_layout.addWidget(value)  # Add the value label to the layout
            results_layout.addLayout(item_layout)  # Add the vertical layout to the main horizontal layout

        # Set the layout for the group box
        results_group.setLayout(results_layout)  # Set the main layout for the results group
        results_group.setStyleSheet(get_results_group_style())  # Apply custom style to the results group

        # Apply styles to all labels
        for label in [total_unit_title, self.total_unit_label, 
                    total_diff_title, self.total_diff_label, 
                    per_unit_cost_title, self.per_unit_cost_label,
                    added_amount_title, self.added_amount_label,
                    in_total_title, self.in_total_label]:
            label.setStyleSheet("border: none; background-color: transparent; padding: 0;")  # Set style for each label
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center-align the text in each label

        return results_group  # Return the created results group

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

        self.update_room_inputs()

        # Add Calculate Room Bills button
        calculate_rooms_button = QPushButton("Calculate Room Bills")  # Create a button for calculating room bills
        calculate_rooms_button.setIcon(QIcon(resource_path("icons/calculate_icon.png")))  # Set an icon for the button
        calculate_rooms_button.clicked.connect(self.calculate_rooms)  # Connect button click to calculation method
        calculate_rooms_button.setStyleSheet(get_button_style())  # Apply style to the button
        layout.addWidget(calculate_rooms_button)  # Add the button to the main layout

        return rooms_tab  # Return the created rooms tab

    def update_room_inputs(self):
        # Update the room inputs based on the number of rooms selected
        # Clear existing widgets from the scroll layout
        for i in reversed(range(self.rooms_scroll_layout.count())):
            # Remove each widget from the layout and set its parent to None
            self.rooms_scroll_layout.itemAt(i).widget().setParent(None)

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
            # Set the layout for the room group
            room_group.setLayout(room_layout)
            # Apply the room group style
            room_group.setStyleSheet(get_room_group_style())

            # Create input fields and labels for the room
            present_entry = CustomLineEdit()
            previous_entry = CustomLineEdit()
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

        # Apply styles to all CustomLineEdit widgets in the room entries
        for present_entry, previous_entry in self.room_entries:
            present_entry.setStyleSheet(get_line_edit_style())
            previous_entry.setStyleSheet(get_line_edit_style())

        # Ensure the scroll area updates its content
        self.rooms_scroll_widget.setLayout(self.rooms_scroll_layout)
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget)

    def calculate_main(self):
        # Calculate the main meter readings
        try:
            # Sum up the total unit from meter entries, converting each to int if not empty
            total_unit = sum(int(entry.text()) for entry in self.meter_entries if entry.text())
            # Sum up the total difference from diff entries, converting each to int if not empty
            total_diff = sum(int(entry.text()) for entry in self.diff_entries if entry.text())

            # Get the additional amount
            additional_amount = self.get_additional_amount()

            # Calculate the in total amount
            in_total = total_unit + additional_amount


            # Check if total_diff is zero to avoid division by zero
            if total_diff == 0:
                raise ZeroDivisionError
            # Calculate the per unit cost by dividing total unit by total difference
            per_unit_cost = total_unit / total_diff

            # Set the total unit label text with the calculated value
            self.total_unit_label.setText(f"{total_unit} TK")
            # Set the total difference label text with the calculated value
            self.total_diff_label.setText(f"{total_diff}")
            # Set the per unit cost label text with the calculated value, formatted to 2 decimal places
            self.per_unit_cost_label.setText(f"{per_unit_cost:.2f} TK")
            # Set the added amount label text
            self.added_amount_label.setText(f"{additional_amount} TK")
            # Set the in total label text
            self.in_total_label.setText(f"{in_total} TK")

            # Don't save here, as room calculations haven't been performed yet

        except ValueError:
            # Show a warning message if invalid input is detected
            QMessageBox.warning(self, "Invalid Input", "Please enter valid integer values for all fields.")
        except ZeroDivisionError:
            # Show a warning message if total difference is zero
            QMessageBox.warning(self, "Division by Zero", "Total Diff cannot be zero.")

    def calculate_rooms(self):
        # Calculate the room bills
        try:
            # Get the per unit cost text from the label and remove 'TK'
            per_unit_cost_text = self.per_unit_cost_label.text().replace("TK", "")
            # If per unit cost is not calculated, raise an error
            if not per_unit_cost_text:
                raise ValueError("Per unit cost not calculated")

            # Convert per unit cost to float
            per_unit_cost = float(per_unit_cost_text)
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
            self.save_calculation_to_csv()
        except ValueError as e:
            # Show warning if there's a value error
            QMessageBox.warning(self, "Error", str(e))

    def save_calculation_to_csv(self):
        # Save the calculation results to a CSV file
        month_name = f"{self.month_combo.currentText()} {self.year_spinbox.value()}"  # Create a string with month and year
        filename = "meter_calculation_history.csv"  # Set the filename for the CSV file
        
        try:
            file_exists = os.path.isfile(filename)  # Check if the file already exists
            
            with open(filename, mode='a', newline='') as file:  # Open the file in append mode
                writer = csv.writer(file)  # Create a CSV writer object
                if not file_exists:  # If the file doesn't exist, write the header row
                    writer.writerow([
                        "Month", "Meter-1", "Meter-2", "Meter-3", 
                        "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
                        "Total Diff", "Per Unit Cost", "Added Amount", "In Total", "Room", 
                        "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"
                    ])

                # Write main calculation data
                main_data = [
                    month_name,  # Add month and year
                    *[entry.text() for entry in self.meter_entries],  # Add meter readings
                    *[entry.text() for entry in self.diff_entries],  # Add difference readings
                    self.total_unit_label.text().replace("TK", "").strip(),  # Add total unit cost
                    self.total_diff_label.text().strip(),  # Add total difference
                    self.per_unit_cost_label.text().replace("TK", "").strip(),  # Add per unit cost
                    self.added_amount_label.text().replace("TK", "").strip(),  # Add added amount
                    self.in_total_label.text().replace("TK", "").strip(),  # Add in total amount
                    "", "", "", "", ""  # Empty fields for room-specific data
                ]
                writer.writerow(main_data)  # Write the main data row

                # Write room calculation data
                for i, (present_entry, previous_entry) in enumerate(self.room_entries):  # Iterate through room entries
                    real_unit_label, unit_bill_label = self.room_results[i]  # Get corresponding room results
                    room_data = [
                        month_name,  # Add month and year
                        *[""] * 11,  # Empty fields for main calculation data
                        f"Room {i+1}",  # Add room number
                        present_entry.text(),  # Add present unit reading
                        previous_entry.text(),  # Add previous unit reading
                        real_unit_label.text(),  # Add real unit value
                        unit_bill_label.text().replace("TK", "").strip()  # Add unit bill value
                    ]
                    writer.writerow(room_data)  # Write the room data row

            QMessageBox.information(self, "Save Successful", "Calculation data has been saved to CSV.")  # Show success message
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")  # Show error message if saving fails

    def create_history_tab(self):
        # Create the History tab
        history_tab = QWidget()  # Create a new QWidget for the history tab
        layout = QVBoxLayout()  # Create a vertical box layout for the tab
        layout.setSpacing(20)  # Set the spacing between widgets to 20 pixels
        layout.setContentsMargins(20, 20, 20, 20)  # Set the margins of the layout
        history_tab.setLayout(layout)  # Set the layout for the history tab

        # Add month and year selection for filtering
        filter_group = QGroupBox("Filter Options")  # Create a group box for filter options
        filter_group.setStyleSheet(get_group_box_style())  # Apply custom style to the group box
        filter_layout = QHBoxLayout()  # Create a horizontal box layout for the filter options
        filter_group.setLayout(filter_layout)  # Set the layout for the filter group
        
        month_label = QLabel("Month:")  # Create a label for month selection
        month_label.setStyleSheet(get_label_style())  # Apply custom style to the month label
        self.history_month_combo = QComboBox()  # Create a combo box for month selection
        self.history_month_combo.addItems([  # Add items to the month combo box
            "All", "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.history_month_combo.setStyleSheet(get_month_info_style())  # Apply custom style to the month combo box
        
        year_label = QLabel("Year:")  # Create a label for year selection
        year_label.setStyleSheet(get_label_style())  # Apply custom style to the year label
        self.history_year_spinbox = QSpinBox()  # Create a spin box for year selection
        self.history_year_spinbox.setRange(2000, 2100)  # Set the range of years from 2000 to 2100
        self.history_year_spinbox.setValue(datetime.now().year)  # Set the current year as default value
        self.history_year_spinbox.setSpecialValueText("All")  # Display "All" when value is minimum
        self.history_year_spinbox.setStyleSheet(get_month_info_style())  # Apply custom style to the year spin box
        
        filter_layout.addWidget(month_label)  # Add month label to the filter layout
        filter_layout.addWidget(self.history_month_combo)  # Add month combo box to the filter layout
        filter_layout.addSpacing(20)  # Add 20 pixels of spacing
        filter_layout.addWidget(year_label)  # Add year label to the filter layout
        filter_layout.addWidget(self.history_year_spinbox)  # Add year spin box to the filter layout
        filter_layout.addStretch(1)  # Add stretchable space to push everything to the left
        
        layout.addWidget(filter_group)  # Add the filter group to the main layout

        # Add Main Calculation Info Section
        main_calc_group = QGroupBox("Main Calculation Info")  # Create a group box for main calculation info
        main_calc_group.setStyleSheet(get_group_box_style())  # Apply custom style to the group box
        main_calc_layout = QVBoxLayout()  # Create a vertical box layout for main calculation info
        main_calc_group.setLayout(main_calc_layout)  # Set the layout for the main calculation group

        self.main_history_table = QTableWidget()  # Create a table widget for main calculation history
        self.main_history_table.setColumnCount(12)  # Set the number of columns to 10
        self.main_history_table.setHorizontalHeaderLabels([  # Set the horizontal header labels
            "Month", "Meter-1", "Meter-2", "Meter-3", 
            "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
            "Total Diff", "Per Unit Cost", "Added Amount", "In Total"
        ])
        self.main_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Make columns stretch to fit
        self.main_history_table.setAlternatingRowColors(True)  # Set alternating row colors
        self.main_history_table.setStyleSheet(get_table_style())  # Apply custom style to the table
        main_calc_layout.addWidget(self.main_history_table)  # Add the table to the main calculation layout

        layout.addWidget(main_calc_group)  # Add the main calculation group to the main layout

        # Add Room Calculation Info Section
        room_calc_group = QGroupBox("Room Calculation Info")  # Create a group box for room calculation info
        room_calc_group.setStyleSheet(get_group_box_style())  # Apply custom style to the group box
        room_calc_layout = QVBoxLayout()  # Create a vertical box layout for room calculation info
        room_calc_group.setLayout(room_calc_layout)  # Set the layout for the room calculation group

        self.room_history_table = QTableWidget()  # Create a table widget for room calculation history
        self.room_history_table.setColumnCount(6)  # Set the number of columns to 6
        self.room_history_table.setHorizontalHeaderLabels([  # Set the horizontal header labels
            "Month", "Room", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"
        ])
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # Make columns stretch to fit
        self.room_history_table.setAlternatingRowColors(True)  # Set alternating row colors
        self.room_history_table.setStyleSheet(get_table_style())  # Apply custom style to the table
        room_calc_layout.addWidget(self.room_history_table)  # Add the table to the room calculation layout

        layout.addWidget(room_calc_group)  # Add the room calculation group to the main layout

        # Add Load History Button
        load_history_button = QPushButton("Load History")  # Create a button to load history
        load_history_button.clicked.connect(self.load_history)  # Connect button click to load_history method
        load_history_button.setStyleSheet(get_button_style())  # Apply custom style to the button
        load_history_button.setFixedHeight(40)  # Set fixed height for the button
        layout.addWidget(load_history_button)  # Add the load history button to the main layout

        return history_tab  # Return the created history tab

    def load_history(self):
        # Load and display historical data
        filename = "meter_calculation_history.csv"  # Define the filename for the history CSV file
        if not os.path.isfile(filename):  # Check if the file exists
            QMessageBox.information(self, "No History", "No history available")  # Show a message if no history file is found
            return  # Exit the function if no file is found

        try:  # Start a try-except block to handle potential errors
            selected_month = self.history_month_combo.currentText()  # Get the selected month from the combo box
            selected_year = self.history_year_spinbox.value()  # Get the selected year from the spin box
            selected_year_str = str(selected_year) if selected_year != self.history_year_spinbox.minimum() else ""  # Convert year to string, or empty if minimum

            with open(filename, mode='r', newline='') as file:  # Open the CSV file in read mode
                reader = csv.reader(file)  # Create a CSV reader object
                header = next(reader, None)  # Skip the header row
                if not header:  # Check if the header is None
                    raise ValueError("No header found in CSV file")  # Raise an error if no header is found
                
                history = list(reader)  # Read all rows into a list

            filtered_history = []  # Initialize an empty list for filtered history
            for row in history:  # Iterate through each row in the history
                if not row:  # Check if the row is empty
                    continue  # Skip empty rows
                month_year = row[0].split() if row[0] else []  # Split the first column into month and year
                if len(month_year) == 2:  # Check if the split resulted in two parts
                    month, year = month_year  # Unpack month and year
                    if (selected_month == "All" or month == selected_month) and \
                    (not selected_year_str or year == selected_year_str):  # Filter based on selected month and year
                        filtered_history.append(row)  # Add matching rows to filtered history

            # Separate main calculation and room calculation data
            main_history = []  # Initialize list for main calculation history
            room_history = []  # Initialize list for room calculation history
            for row in filtered_history:  # Iterate through filtered history
                if len (row)> 12 and row[12].strip():  # Check if there's a room number (11th column)
                    room_history.append(row)  # Add to room history if room number exists
                else:
                    main_history.append(row)  # Add to main history if no room number

            # Load main calculation info
            self.main_history_table.setRowCount(len(main_history))  # Set the number of rows in main history table
            for row_index, row in enumerate(main_history):  # Iterate through main history rows
                for column_index, item in enumerate(row[:12]):  # Iterate through first 10 columns
                    self.main_history_table.setItem(row_index, column_index, QTableWidgetItem(str(item)))  # Set table item

            # Load room calculation info
            self.room_history_table.setRowCount(len(room_history))  # Set the number of rows in room history table
            for row_index, row in enumerate(room_history):  # Iterate through room history rows
                room_data = [row[0]] + row[12:18]  # Combine month with room-specific data
                for column_index, item in enumerate(room_data):  # Iterate through room data
                    self.room_history_table.setItem(row_index, column_index, QTableWidgetItem(str(item)))  # Set table item

            QMessageBox.information(self, "History Loaded", f"Loaded {len(main_history)} main records and {len(room_history)} room records from history.")  # Show success message
        except Exception as e:  # Catch any exceptions that occur
            QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")  # Show error message
            print(f"Detailed error: {str(e)}")  # Print detailed error message

    def save_to_pdf(self):
        # Open a file dialog to save the PDF
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")  # Open save file dialog
        if file_path:  # If a file path is selected
            self.generate_pdf(file_path)  # Call the generate_pdf method with the selected file path

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
        )
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

        # Main Meter Info Content
        meter_info_left = [  # Create a list for the left side of the main meter info
            [Paragraph("Meter-1 Unit:", normal_style), Paragraph(f"{self.meter_entries[0].text() or 'N/A'}", normal_style)],
            [Paragraph("Meter-2 Unit:", normal_style), Paragraph(f"{self.meter_entries[1].text() or 'N/A'}", normal_style)],
            [Paragraph("Meter-3 Unit:", normal_style), Paragraph(f"{self.meter_entries[2].text() or 'N/A'}", normal_style)],
            [Paragraph("Total Difference:", normal_style), Paragraph(f"{self.total_diff_label.text() or 'N/A'}", normal_style)],
        ]

        meter_info_right = [  # Create a list for the right side of the main meter info
            [Paragraph("Per Unit Cost:", normal_style), Paragraph(f"{self.per_unit_cost_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Total Unit Cost:", normal_style), Paragraph(f"{self.total_unit_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Added Amount:", normal_style), Paragraph(f"{self.added_amount_label.text() or 'N/A'}", normal_style)],
            [Paragraph("In Total Amount:", normal_style), Paragraph(f"{self.in_total_label.text() or 'N/A'}", normal_style)],
        ]

        main_meter_table = Table(  # Create a table for the main meter info
            [meter_info_left[i] + meter_info_right[i] for i in range(4)],  # Combine left and right info
            colWidths=[2.5*inch, 1.25*inch, 2.5*inch, 1.25*inch],  # Set column widths
            rowHeights=[0.2*inch] * 4  # Set row heights
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

                    room_info = [  # Create a list of room information
                        [Paragraph(f"<b>Room {i + j + 1}</b>", normal_style)],  # Room number
                        [Paragraph("Month:", label_style), Paragraph(month_year, normal_style)],  # Month and year
                        [Paragraph("Per-Unit Cost:", label_style), Paragraph(self.per_unit_cost_label.text() or 'N/A', normal_style)],  # Per-unit cost
                        [Paragraph("Unit:", label_style), Paragraph(real_unit_label.text() or 'N/A', normal_style)],  # Unit
                        [Paragraph("Unit Bill:", label_style), Paragraph(unit_bill_label.text() or 'N/A', normal_style)]  # Unit bill
                    ]

                    room_table = Table(room_info, colWidths=[1.5*inch, 2.15*inch])  # Create a table for each room
                    room_table.setStyle(TableStyle([  # Set the style for the room table
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightsteelblue),  # Set background color for the header
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),  # Set background color for the content
                        ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),  # Add a box around the table
                        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),  # Add a line below the header
                        ('LINEABOVE', (0, 1), (-1, -1), 1, colors.lightgrey),  # Add lines above each row
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

    def setup_navigation(self):
        # Setup navigation for main calculation tab
        for i in range(3):  # Loop through 3 pairs of meter and diff entries
            meter_entry = self.meter_entries[i]  # Get the current meter entry
            diff_entry = self.diff_entries[i]  # Get the current diff entry
            
            # Set navigation from meter to diff
            meter_entry.next_widget = diff_entry  # Set the next widget for meter entry to be the diff entry
            diff_entry.previous_widget = meter_entry  # Set the previous widget for diff entry to be the meter entry
            
            # Set navigation from diff to next meter (or back to first meter if it's the last pair)
            if i < 2:  # If it's not the last pair
                diff_entry.next_widget = self.meter_entries[i+1]  # Set next widget of diff to be the next meter entry
                self.meter_entries[i+1].previous_widget = diff_entry  # Set previous widget of next meter to be current diff
            else:  # If it's the last pair
                diff_entry.next_widget = self.meter_entries[0]  # Set next widget of last diff to be the first meter entry
                self.meter_entries[0].previous_widget = diff_entry  # Set previous widget of first meter to be the last diff

        # Setup navigation for room calculation tab
        num_rooms = len(self.room_entries)  # Get the total number of rooms
        for i, (present_entry, previous_entry) in enumerate(self.room_entries):  # Loop through room entries
            # Set navigation within the room
            present_entry.next_widget = previous_entry  # Set next widget of present entry to be previous entry
            previous_entry.previous_widget = present_entry  # Set previous widget of previous entry to be present entry
            
            # Set navigation to the next room (or back to the first room if it's the last room)
            next_room_index = (i + 1) % num_rooms  # Calculate the index of the next room (wrapping around if necessary)
            previous_entry.next_widget = self.room_entries[next_room_index][0]  # Set next widget of previous entry to be present entry of next room
            present_entry.previous_widget = self.room_entries[i - 1][1]  # Set previous widget of present entry to be previous entry of previous room

        # Set focus to the first entry when the tab is opened
        self.tab_widget.currentChanged.connect(self.set_focus_on_tab_change)  # Connect tab change event to focus setting function

        # Add accessibility features
        self.add_accessibility_features(self.meter_entries + self.diff_entries)  # Add accessibility features to meter and diff entries
        for room_entries in self.room_entries:  # Loop through room entries
            self.add_accessibility_features(room_entries)  # Add accessibility features to each room's entries

        # Add keyboard shortcut for quick navigation
        self.shortcut = QShortcut(QKeySequence("Ctrl+N"), self)  # Create a keyboard shortcut
        self.shortcut.activated.connect(self.focus_next_entry)  # Connect the shortcut to the focus_next_entry function

    def set_focus_on_tab_change(self, index):
        if index == 0 and self.meter_entries:  # If switching to main calculation tab and meter entries exist
            self.meter_entries[0].setFocus()  # Set focus to the first meter entry
        elif index == 1 and self.room_entries:  # If switching to room calculation tab and room entries exist
            self.room_entries[0][0].setFocus()  # Set focus to the first entry of the first room

    def add_accessibility_features(self, entries):
        for i, entry in enumerate(entries):  # Loop through the entries
            entry.setAccessibleName(f"Entry {i + 1}")  # Set an accessible name for each entry
            entry.setAccessibleDescription("Input field for meter or difference value")  # Set an accessible description for each entry

    def focus_next_entry(self):
        current = QApplication.focusWidget()  # Get the currently focused widget
        if isinstance(current, CustomLineEdit) and current.next_widget:  # If the current widget is a CustomLineEdit and has a next widget
            current.next_widget.setFocus()  # Set focus to the next widget

if __name__ == "__main__":
    app = QApplication(sys.argv)  # Create a QApplication instance
    window = MeterCalculationApp()  # Create an instance of the MeterCalculationApp
    window.show()  # Show the main window
    sys.exit(app.exec_())  # Start the event loop and exit when it's done