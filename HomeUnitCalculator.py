import sys
from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame, QShortcut
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
    get_room_group_style, get_month_info_style, get_table_style, get_label_style
)

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

    def focusInEvent(self, event):
        # Call the parent class focus in event
        super().focusInEvent(event)
        # Ensure this widget is visible when it receives focus
        self.ensureWidgetVisible()

    def ensureWidgetVisible(self):
        # Find the parent QScrollArea
        parent = self.parent()
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parent()
        # If a QScrollArea is found, ensure this widget is visible within it
        if parent:
            parent.ensureWidgetVisible(self)

    def keyPressEvent(self, event):
        # Handle navigation keys
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down, Qt.Key_Right):
            # Move focus forward
            self.moveFocus(forward=True)
        elif event.key() in (Qt.Key_Up, Qt.Key_Left):
            # Move focus backward
            self.moveFocus(forward=False)
        elif event.key() == Qt.Key_Tab:
            # Handle Tab key normally
            super().keyPressEvent(event)
        else:
            # Handle other keys normally
            super().keyPressEvent(event)
        
        # Ensure the widget is visible after any key press
        self.ensureWidgetVisible()

    def moveFocus(self, forward=True):
        current = self.focusWidget()
        if current:
            next_widget = self.findNextWidget(forward)
            if next_widget:
                next_widget.setFocus()
            else:
                print("No valid next widget found")

    def findNextWidget(self, forward=True):
        # Find all CustomLineEdit widgets in the parent
        widgets = self.parent().findChildren(CustomLineEdit)
        current_index = widgets.index(self)
        # Calculate the next index, wrapping around if necessary
        next_index = (current_index + (1 if forward else -1)) % len(widgets)
        return widgets[next_index]

# Custom QScrollArea class with auto-scrolling functionality
class AutoScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_speed = 1
        self.scroll_margin = 50
        self.setMouseTracking(True)
        self.verticalScrollBar().installEventFilter(self)
        self.horizontalScrollBar().installEventFilter(self)
        self.setWidgetResizable(True)

    def eventFilter(self, obj, event):
        # Filter events for auto-scrolling
        if obj in (self.verticalScrollBar(), self.horizontalScrollBar()) and event.type() == QEvent.MouseMove:
            # Check if the event has a valid position before calling handleMouseMove
            if hasattr(event, 'globalPos'):
                self.handleMouseMove(event.globalPos())
            elif hasattr(event, 'globalPosition'):
                self.handleMouseMove(event.globalPosition().toPoint())
            else:
                # If neither globalPos nor globalPosition is available, log an error or handle accordingly
                print("Error: Unable to get mouse position from event")
        return super().eventFilter(obj, event)

    def handleMouseMove(self, global_pos):
        # Handle mouse movement for auto-scrolling
        local_pos = self.mapFromGlobal(global_pos)
        rect = self.rect()
        v_bar = self.verticalScrollBar()
        h_bar = self.horizontalScrollBar()

        # Vertical scrolling
        if local_pos.y() < self.scroll_margin:
            v_bar.setValue(v_bar.value() - self.scroll_speed)
        elif local_pos.y() > rect.height() - self.scroll_margin:
            v_bar.setValue(v_bar.value() + self.scroll_speed)

        # Horizontal scrolling
        if local_pos.x() < self.scroll_margin:
            h_bar.setValue(h_bar.value() - self.scroll_speed)
        elif local_pos.x() > rect.width() - self.scroll_margin:
            h_bar.setValue(h_bar.value() + self.scroll_speed)

    def mouseMoveEvent(self, event):
        # Handle mouse movement events
        if hasattr(event, 'globalPos'):
            self.handleMouseMove(event.globalPos())
        elif hasattr(event, 'globalPosition'):
            self.handleMouseMove(event.globalPosition().toPoint())
        else:
            print("Error: Unable to get mouse position from event")
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        # Handle wheel events for zooming when Ctrl is pressed
        if event.modifiers() & Qt.ControlModifier:
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.zoom(zoom_factor)
            event.accept()  # Prevent the event from being passed to the parent
        else:
            # Use the parent's wheelEvent to handle scrolling
            super().wheelEvent(event)

    def zoom(self, factor):
        # Zoom the content of the scroll area
        if self.widget():
            current_size = self.widget().size()
            new_size = current_size * factor
            self.widget().resize(new_size)

            # Adjust scroll position to keep the center point fixed
            center = QPoint(self.viewport().width() // 2, self.viewport().height() // 2)
            global_center = self.mapToGlobal(center)
            target_global = self.widget().mapFromGlobal(global_center)
            target_local = self.widget().mapTo(self, target_global)

            self.ensureVisible(target_local.x(), target_local.y(), 
            self.viewport().width() // 2, self.viewport().height() // 2)

# Main application class
class MeterCalculationApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Meter Calculation Application")
        self.setGeometry(400, 100, 1000, 800)
        
        self.setWindowIcon(QIcon("icon.png"))
        self.setStyleSheet(get_stylesheet())

        self.init_ui()
        self.setup_navigation()

    def init_ui(self):
        # Initialize the main user interface
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Add header
        header = QLabel("Meter Calculation Application")
        header.setStyleSheet(get_header_style())
        main_layout.addWidget(header)

        # Create and add tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_main_tab(), "Main Calculation")
        self.tab_widget.addTab(self.create_rooms_tab(), "Room Calculations")
        self.tab_widget.addTab(self.create_history_tab(), "History")
        main_layout.addWidget(self.tab_widget)

        # Add Save to PDF button
        save_pdf_button = QPushButton("Save to PDF")
        save_pdf_button.setIcon(QIcon("save_icon.png"))
        save_pdf_button.clicked.connect(self.save_to_pdf)
        main_layout.addWidget(save_pdf_button)

    def create_main_tab(self):
        # Create the main calculation tab
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Add Date Selection group
        filter_group = QGroupBox("Date Selection")
        filter_group.setStyleSheet(get_group_box_style())
        filter_layout = QHBoxLayout()
        filter_group.setLayout(filter_layout)

        # Add Month selection
        month_label = QLabel("Month:")
        month_label.setStyleSheet(get_label_style())
        self.month_combo = QComboBox()
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())

        # Add Year selection
        year_label = QLabel("Year:")
        year_label.setStyleSheet(get_label_style())
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self.year_spinbox.setStyleSheet(get_month_info_style())

        # Add widgets to filter layout
        filter_layout.addWidget(month_label)
        filter_layout.addWidget(self.month_combo)
        filter_layout.addSpacing(20)
        filter_layout.addWidget(year_label)
        filter_layout.addWidget(self.year_spinbox)
        filter_layout.addStretch(1)

        main_layout.addWidget(filter_group)

        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #A7F3D0;")
        main_layout.addWidget(separator)

        # Add Meter and Difference Readings
        readings_layout = QHBoxLayout()
        readings_layout.setSpacing(20)

        meter_group = self.create_meter_group()
        readings_layout.addWidget(meter_group)

        diff_group = self.create_diff_group()
        readings_layout.addWidget(diff_group)

        main_layout.addLayout(readings_layout)

        # Add Calculate button
        calculate_button = QPushButton("Calculate")
        calculate_button.setIcon(QIcon("calculate_icon.png"))
        calculate_button.clicked.connect(self.calculate_main)
        calculate_button.setStyleSheet(get_button_style())
        calculate_button.setFixedHeight(50)
        main_layout.addWidget(calculate_button)

        # Add Results section
        results_group = self.create_results_group()
        main_layout.addWidget(results_group)

        # Add stretch to push everything to the top
        main_layout.addStretch(1)

        return main_tab

    def create_month_info_section(self):
        # Create the month and year selection section
        month_info_layout = QHBoxLayout()
        month_info_layout.setSpacing(10)

        month_label = QLabel("Month:")
        month_label.setStyleSheet("font-weight: bold;")
        self.month_combo = QComboBox()
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())

        year_label = QLabel("Year:")
        year_label.setStyleSheet("font-weight: bold;")
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self.year_spinbox.setStyleSheet(get_month_info_style())

        month_info_layout.addWidget(month_label)
        month_info_layout.addWidget(self.month_combo, 1)
        month_info_layout.addWidget(year_label)
        month_info_layout.addWidget(self.year_spinbox, 1)
        month_info_layout.addStretch(2)

        return month_info_layout

    def create_meter_group(self):
        # Create the Meter Readings group
        meter_group = QGroupBox("Meter Readings")
        meter_group.setStyleSheet(get_group_box_style())
        meter_layout = QFormLayout()
        meter_layout.setSpacing(10)
        self.meter_entries = []
        for i in range(3):
            meter_entry = CustomLineEdit()
            meter_entry.setPlaceholderText(f"Enter meter {i+1} reading")
            meter_layout.addRow(f"Meter {i+1} Reading:", meter_entry)
            self.meter_entries.append(meter_entry)
        meter_group.setLayout(meter_layout)
        return meter_group
    
    def create_diff_group(self):
        # Create the Difference Readings group
        diff_group = QGroupBox("Difference Readings")
        diff_group.setStyleSheet(get_group_box_style())
        diff_layout = QFormLayout()
        diff_layout.setSpacing(10)
        self.diff_entries = []
        for i in range(3):
            diff_entry = CustomLineEdit()
            diff_entry.setPlaceholderText(f"Enter difference {i+1}")
            diff_layout.addRow(f"Difference {i+1}:", diff_entry)
            self.diff_entries.append(diff_entry)
        diff_group.setLayout(diff_layout)
        return diff_group

    def create_results_group(self):
        # Create the Results group
        results_group = QGroupBox("Results")
        results_layout = QHBoxLayout()
        results_layout.setSpacing(50)
        
        # Create labels for titles and values
        total_unit_title = QLabel("Total Unit")
        self.total_unit_label = QLabel("N/A")
        total_diff_title = QLabel("Total Difference")
        self.total_diff_label = QLabel("N/A")
        per_unit_cost_title = QLabel("Per Unit Cost")
        self.per_unit_cost_label = QLabel("N/A")

        # Create vertical layouts for each result
        for title, value in [
            (total_unit_title, self.total_unit_label),
            (total_diff_title, self.total_diff_label),
            (per_unit_cost_title, self.per_unit_cost_label)
        ]:
            item_layout = QVBoxLayout()
            item_layout.addWidget(title)
            item_layout.addWidget(value)
            results_layout.addLayout(item_layout)

        # Set the layout for the group box
        results_group.setLayout(results_layout)
        results_group.setStyleSheet(get_results_group_style())

        # Apply styles to all labels
        for label in [total_unit_title, self.total_unit_label, 
                    total_diff_title, self.total_diff_label, 
                    per_unit_cost_title, self.per_unit_cost_label]:
            label.setStyleSheet("border: none; background-color: transparent; padding: 0;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        return results_group

    def create_rooms_tab(self):
        # Create the Room Calculations tab
        rooms_tab = QWidget()
        layout = QVBoxLayout()
        rooms_tab.setLayout(layout)

        # Add Number of Rooms selection
        num_rooms_layout = QHBoxLayout()
        num_rooms_label = QLabel("Number of Rooms:")
        self.num_rooms_spinbox = QSpinBox()
        self.num_rooms_spinbox.setRange(1, 20)
        self.num_rooms_spinbox.setValue(11)
        self.num_rooms_spinbox.valueChanged.connect(self.update_room_inputs)
        self.num_rooms_spinbox.setStyleSheet(get_line_edit_style())
        num_rooms_layout.addWidget(num_rooms_label)
        num_rooms_layout.addWidget(self.num_rooms_spinbox)
        layout.addLayout(num_rooms_layout)

        # Add scrollable area for room inputs
        self.rooms_scroll_area = AutoScrollArea()
        self.rooms_scroll_area.setWidgetResizable(True)
        self.rooms_scroll_widget = QWidget()
        self.rooms_scroll_layout = QGridLayout(self.rooms_scroll_widget)
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget)
        layout.addWidget(self.rooms_scroll_area)

        self.room_entries = []
        self.room_results = []

        self.update_room_inputs()

        # Add Calculate Room Bills button
        calculate_rooms_button = QPushButton("Calculate Room Bills")
        calculate_rooms_button.setIcon(QIcon("calculate_icon.png"))
        calculate_rooms_button.clicked.connect(self.calculate_rooms)
        calculate_rooms_button.setStyleSheet(get_button_style())
        layout.addWidget(calculate_rooms_button)

        return rooms_tab

    def update_room_inputs(self):
        # Update the room inputs based on the number of rooms selected
        # Clear existing widgets
        for i in reversed(range(self.rooms_scroll_layout.count())):
            self.rooms_scroll_layout.itemAt(i).widget().setParent(None)

        num_rooms = self.num_rooms_spinbox.value()
        self.room_entries = []
        self.room_results = []

        for i in range(num_rooms):
            room_group = QGroupBox(f"Room {i+1}")
            room_layout = QFormLayout()
            room_group.setLayout(room_layout)
            room_group.setStyleSheet(get_room_group_style())

            present_entry = CustomLineEdit()
            previous_entry = CustomLineEdit()
            real_unit_label = QLabel()
            unit_bill_label = QLabel()

            # Apply styles to the input fields
            present_entry.setStyleSheet(get_line_edit_style())
            previous_entry.setStyleSheet(get_line_edit_style())

            room_layout.addRow("Present Unit:", present_entry)
            room_layout.addRow("Previous Unit:", previous_entry)
            room_layout.addRow("Real Unit:", real_unit_label)
            room_layout.addRow("Unit Bill:", unit_bill_label)

            self.room_entries.append((present_entry, previous_entry))
            self.room_results.append((real_unit_label, unit_bill_label))

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
            total_unit = sum(int(entry.text()) for entry in self.meter_entries if entry.text())
            total_diff = sum(int(entry.text()) for entry in self.diff_entries if entry.text())
            if total_diff == 0:
                raise ZeroDivisionError
            per_unit_cost = total_unit / total_diff

            self.total_unit_label.setText(f"{total_unit} TK")
            self.total_diff_label.setText(f"{total_diff}")
            self.per_unit_cost_label.setText(f"{per_unit_cost:.2f} TK")

            # Don't save here, as room calculations haven't been performed yet
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid integer values for all fields.")
        except ZeroDivisionError:
            QMessageBox.warning(self, "Division by Zero", "Total Diff cannot be zero.")

    def calculate_rooms(self):
        # Calculate the room bills
        try:
            per_unit_cost_text = self.per_unit_cost_label.text().replace("TK", "")
            if not per_unit_cost_text:
                raise ValueError("Per unit cost not calculated")

            per_unit_cost = float(per_unit_cost_text)
            for (present_entry, previous_entry), (real_unit_label, unit_bill_label) in zip(self.room_entries, self.room_results):
                present_text = present_entry.text()
                previous_text = previous_entry.text()
                if present_text and previous_text:
                    present_unit = int(present_text)
                    previous_unit = int(previous_text)
                    real_unit = present_unit - previous_unit
                    unit_bill = real_unit * per_unit_cost
                    unit_bill = int(round(unit_bill))

                    real_unit_label.setText(f"{real_unit}")
                    unit_bill_label.setText(f"{unit_bill} TK")
                else:
                    real_unit_label.setText("Incomplete")
                    unit_bill_label.setText("Incomplete")

            # Save calculations after both main and room calculations are complete
            self.save_calculation_to_csv()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def save_calculation_to_csv(self):
        # Save the calculation results to a CSV file
        month_name = f"{self.month_combo.currentText()} {self.year_spinbox.value()}"
        filename = "meter_calculation_history.csv"
        
        try:
            file_exists = os.path.isfile(filename)
            
            with open(filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow([
                        "Month", "Meter-1", "Meter-2", "Meter-3", 
                        "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
                        "Total Diff", "Per Unit Cost", "Room", 
                        "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"
                    ])

                # Write main calculation data
                main_data = [
                    month_name,
                    *[entry.text() for entry in self.meter_entries],
                    *[entry.text() for entry in self.diff_entries],
                    self.total_unit_label.text().replace("TK", "").strip(),
                    self.total_diff_label.text().strip(),
                    self.per_unit_cost_label.text().replace("TK", "").strip(),
                    "", "", "", "", ""  # Empty fields for room-specific data
                ]
                writer.writerow(main_data)

                # Write room calculation data
                for i, (present_entry, previous_entry) in enumerate(self.room_entries):
                    real_unit_label, unit_bill_label = self.room_results[i]
                    room_data = [
                        month_name,
                        *[""] * 9,  # Empty fields for main calculation data
                        f"Room {i+1}",
                        present_entry.text(),
                        previous_entry.text(),
                        real_unit_label.text(),
                        unit_bill_label.text().replace("TK", "").strip()
                    ]
                    writer.writerow(room_data)

            QMessageBox.information(self, "Save Successful", "Calculation data has been saved to CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")

    def create_history_tab(self):
        # Create the History tab
        history_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        history_tab.setLayout(layout)

        # Add month and year selection for filtering
        filter_group = QGroupBox("Filter Options")
        filter_group.setStyleSheet(get_group_box_style())
        filter_layout = QHBoxLayout()
        filter_group.setLayout(filter_layout)
        
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
        self.history_year_spinbox.setSpecialValueText("All")  # Display "All" when value is minimum
        self.history_year_spinbox.setStyleSheet(get_month_info_style())
        
        filter_layout.addWidget(month_label)
        filter_layout.addWidget(self.history_month_combo)
        filter_layout.addSpacing(20)
        filter_layout.addWidget(year_label)
        filter_layout.addWidget(self.history_year_spinbox)
        filter_layout.addStretch(1)  # This will push everything to the left
        
        layout.addWidget(filter_group)

        # Add Main Calculation Info Section
        main_calc_group = QGroupBox("Main Calculation Info")
        main_calc_group.setStyleSheet(get_group_box_style())
        main_calc_layout = QVBoxLayout()
        main_calc_group.setLayout(main_calc_layout)

        self.main_history_table = QTableWidget()
        self.main_history_table.setColumnCount(10)
        self.main_history_table.setHorizontalHeaderLabels([
            "Month", "Meter-1", "Meter-2", "Meter-3", 
            "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
            "Total Diff", "Per Unit Cost"
        ])
        self.main_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.main_history_table.setAlternatingRowColors(True)
        self.main_history_table.setStyleSheet(get_table_style())
        main_calc_layout.addWidget(self.main_history_table)

        layout.addWidget(main_calc_group)

        # Add Room Calculation Info Section
        room_calc_group = QGroupBox("Room Calculation Info")
        room_calc_group.setStyleSheet(get_group_box_style())
        room_calc_layout = QVBoxLayout()
        room_calc_group.setLayout(room_calc_layout)

        self.room_history_table = QTableWidget()
        self.room_history_table.setColumnCount(6)
        self.room_history_table.setHorizontalHeaderLabels([
            "Month", "Room", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"
        ])
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.room_history_table.setAlternatingRowColors(True)
        self.room_history_table.setStyleSheet(get_table_style())
        room_calc_layout.addWidget(self.room_history_table)

        layout.addWidget(room_calc_group)

        # Add Load History Button
        load_history_button = QPushButton("Load History")
        load_history_button.clicked.connect(self.load_history)
        load_history_button.setStyleSheet(get_button_style())
        load_history_button.setFixedHeight(40)
        layout.addWidget(load_history_button)

        return history_tab

    def load_history(self):
        # Load and display historical data
        filename = "meter_calculation_history.csv"
        if not os.path.isfile(filename):
            QMessageBox.information(self, "No History", "No history available")
            return

        try:
            selected_month = self.history_month_combo.currentText()
            selected_year = self.history_year_spinbox.value()
            selected_year_str = str(selected_year) if selected_year != self.history_year_spinbox.minimum() else ""

            with open(filename, mode='r') as file:
                reader = csv.reader(file)
                header = next(reader)  # Skip header row
                history = list(reader)

            filtered_history = []
            for row in history:
                month_year = row[0].split()
                if len(month_year) == 2:
                    month, year = month_year
                    if (selected_month == "All" or month == selected_month) and \
                    (not selected_year_str or year == selected_year_str):
                        filtered_history.append(row)

            # Separate main calculation and room calculation data
            main_history = []
            room_history = []
            for row in filtered_history:
                if row[10]:  # If there's a room number, it's a room calculation row
                    room_history.append(row)
                else:
                    main_history.append(row)

            # Load main calculation info
            self.main_history_table.setRowCount(len(main_history))
            for row_index, row in enumerate(main_history):
                for column_index, item in enumerate(row[:10]):  # Only first 10 columns for main data
                    self.main_history_table.setItem(row_index, column_index, QTableWidgetItem(item))

            # Load room calculation info
            self.room_history_table.setRowCount(len(room_history))
            for row_index, row in enumerate(room_history):
                room_data = [row[0]] + row[10:]  # Month + room-specific data
                for column_index, item in enumerate(room_data):
                    self.room_history_table.setItem(row_index, column_index, QTableWidgetItem(item))

            QMessageBox.information(self, "History Loaded", f"Loaded {len(main_history)} main records and {len(room_history)} room records from history.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")

    def save_to_pdf(self):
        # Open a file dialog to save the PDF
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.generate_pdf(file_path)

    def generate_pdf(self, file_path):
        # Generate a PDF report of the calculations
        # Reduce margins to fit more content
        doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=0.3*inch, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
        elements = []

        # Adjust styles to have slightly larger font sizes
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=10,
            alignment=TA_CENTER
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=5,
            alignment=TA_CENTER
        )
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=2
        )
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=1
        )

        def create_cell(content, bgcolor=colors.lightsteelblue, textcolor=colors.black, style=normal_style, height=0.2*inch):
            if isinstance(content, str):
                content = Paragraph(content, style)
            return Table(
                [[content]],
                colWidths=[7.5*inch],
                rowHeights=[height],
                style=TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), bgcolor),
                    ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
                    ('TEXTCOLOR', (0,0), (-1,-1), textcolor),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ])
            )

        # Title
        elements.append(Paragraph("Meter Calculation Report", title_style))
        elements.append(Spacer(1, 0.1*inch))

        # Month
        month_year = f"{self.month_combo.currentText()} {self.year_spinbox.value()}"
        month_paragraph = Paragraph(f"Month: <font color='red'>{month_year}</font>", header_style)
        elements.append(create_cell(month_paragraph, bgcolor=colors.lightsteelblue, height=0.3*inch))
        elements.append(Spacer(1, 0.05*inch))

        # Main Meter Info Headline
        elements.append(Spacer(1, 0.1*inch))
        elements.append(create_cell("Main Meter Info", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))

        # Main Meter Info Content
        meter_info_left = [
            [Paragraph("Meter-1 Unit:", normal_style), Paragraph(f"{self.meter_entries[0].text() or 'N/A'}", normal_style)],
            [Paragraph("Meter-2 Unit:", normal_style), Paragraph(f"{self.meter_entries[1].text() or 'N/A'}", normal_style)],
            [Paragraph("Meter-3 Unit:", normal_style), Paragraph(f"{self.meter_entries[2].text() or 'N/A'}", normal_style)],
        ]

        meter_info_right = [
            [Paragraph("Total Diff:", normal_style), Paragraph(f"{self.total_diff_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Per Unit Cost:", normal_style), Paragraph(f"{self.per_unit_cost_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Total Unit Cost:", normal_style), Paragraph(f"{self.total_unit_label.text() or 'N/A'}", normal_style)],
        ]

        main_meter_table = Table(
            [meter_info_left[i] + meter_info_right[i] for i in range(3)],
            colWidths=[2.5*inch, 1.25*inch, 2.5*inch, 1.25*inch],
            rowHeights=[0.2*inch] * 3
        )

        main_meter_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),
            ('LINEABOVE', (0, 1), (-1, -1), 1, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        elements.append(main_meter_table)
        elements.append(Spacer(1, 0.1*inch))

        # Room Info Headline
        elements.append(Spacer(1, 0.1*inch))
        elements.append(create_cell("Room Information", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))

        # Room Info
        room_data = []
        for i in range(0, len(self.room_entries), 2):
            row = []
            for j in range(2):
                if i + j < len(self.room_entries):
                    present_entry, previous_entry = self.room_entries[i + j]
                    real_unit_label, unit_bill_label = self.room_results[i + j]

                    room_info = [
                        [Paragraph(f"<b>Room {i + j + 1}</b>", normal_style)],
                        [Paragraph("Month:", label_style), Paragraph(month_year, normal_style)],
                        [Paragraph("Per-Unit Cost:", label_style), Paragraph(self.per_unit_cost_label.text() or 'N/A', normal_style)],
                        [Paragraph("Unit:", label_style), Paragraph(real_unit_label.text() or 'N/A', normal_style)],
                        [Paragraph("Unit Bill:", label_style), Paragraph(unit_bill_label.text() or 'N/A', normal_style)]
                    ]

                    room_table = Table(room_info, colWidths=[1.5*inch, 2.15*inch])
                    room_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightsteelblue),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('BOX', (0, 0), (-1, -1), 1, colors.darkblue),
                        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
                        ('LINEABOVE', (0, 1), (-1, -1), 1, colors.lightgrey),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 2),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ]))
                    row.append(room_table)
                else:
                    row.append("")
            room_data.append(row)

        room_table = Table(room_data, colWidths=[3.85*inch, 3.85*inch], spaceBefore=0.05*inch)
        room_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(room_table)

        # Build the PDF document
        doc.build(elements)

    def setup_navigation(self):
        # Interleave meter and difference entries
        all_entries = []
        for meter_entry, diff_entry in zip(self.meter_entries, self.diff_entries):
            all_entries.extend([meter_entry, diff_entry])
        
        # Add room entries
        all_entries.extend([entry for room in self.room_entries for entry in room])

        # Link each entry to the next and previous entries in the list
        for i, entry in enumerate(all_entries):
            entry.previous_widget = all_entries[i - 1] if i > 0 else None
            entry.next_widget = all_entries[i + 1] if i < len(all_entries) - 1 else None

        # Ensure tab order is set correctly
        for i in range(len(all_entries) - 1):
            QWidget.setTabOrder(all_entries[i], all_entries[i + 1])

        # Set focus to the first entry when the tab is opened
        if all_entries:
            self.tab_widget.currentChanged.connect(lambda index: all_entries[0].setFocus() if index == 0 else None)

        # Add error handling for empty lists
        if not self.meter_entries or not self.diff_entries or not self.room_entries:
            print("Warning: One or more entry lists are empty.")
            # Consider raising an exception or handling this case more robustly

        # Improve performance for large lists
        if len(all_entries) > 1000:
            print("Warning: Large number of entries may impact performance.")
            # Consider implementing pagination or lazy loading for better performance

        # Add accessibility features
        for entry in all_entries:
            entry.setAccessibleName(f"Entry {all_entries.index(entry) + 1}")
            entry.setAccessibleDescription("Input field for meter or difference value")

        # Add keyboard shortcut for quick navigation
        self.shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut.activated.connect(lambda: self.focus_next_entry(all_entries))

    def focus_next_entry(self, entries):
        current = QApplication.focusWidget()
        if current in entries:
            index = entries.index(current)
            next_index = (index + 1) % len(entries)
            entries[next_index].setFocus()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeterCalculationApp()
    window.show()
    sys.exit(app.exec_())