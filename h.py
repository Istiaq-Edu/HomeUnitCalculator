import sys
from PyQt5.QtCore import Qt, QRegExp, QEvent
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame
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
    get_room_group_style, get_month_info_style
)

class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QRegExpValidator(QRegExp(r'^\d*$')))
        self.setPlaceholderText("Enter a number")
        self.setToolTip("Input only integer values")
        self.next_widget = None
        self.previous_widget = None
        self.setStyleSheet(get_line_edit_style())

    def focusInEvent(self, event):
        super().focusInEvent(event)
        # Ensure the widget scrolls into view when it gains focus
        self.ensureWidgetVisible()

    def ensureWidgetVisible(self):
        # Scroll the parent scroll area to make this widget visible
        parent = self.parent()
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parent()
        if parent:
            parent.ensureWidgetVisible(self)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.next_widget:
                self.next_widget.setFocus()
        elif event.key() in (Qt.Key_Down, Qt.Key_Right):
            if self.next_widget:
                self.next_widget.setFocus()
        elif event.key() in (Qt.Key_Up, Qt.Key_Left):
            if self.previous_widget:
                self.previous_widget.setFocus()
        else:
            super().keyPressEvent(event)

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
        if obj in (self.verticalScrollBar(), self.horizontalScrollBar()) and event.type() == QEvent.MouseMove:
            self.handleMouseMove(event.globalPos())
        return super().eventFilter(obj, event)

    def handleMouseMove(self, global_pos):
        local_pos = self.mapFromGlobal(global_pos)
        rect = self.rect()
        v_bar = self.verticalScrollBar()
        h_bar = self.horizontalScrollBar()

        if local_pos.y() < self.scroll_margin:
            v_bar.setValue(v_bar.value() - self.scroll_speed)
        elif local_pos.y() > rect.height() - self.scroll_margin:
            v_bar.setValue(v_bar.value() + self.scroll_speed)

        if local_pos.x() < self.scroll_margin:
            h_bar.setValue(h_bar.value() - self.scroll_speed)
        elif local_pos.x() > rect.width() - self.scroll_margin:
            h_bar.setValue(h_bar.value() + self.scroll_speed)

    def mouseMoveEvent(self, event):
        self.handleMouseMove(event.globalPos())
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            # Zoom in/out with Ctrl + Wheel
            if event.angleDelta().y() > 0:
                self.zoom(1.1)
            else:
                self.zoom(0.9)
        else:
            super().wheelEvent(event)

    def zoom(self, factor):
        if self.widget():
            current_size = self.widget().size()
            new_size = current_size * factor
            self.widget().resize(new_size)

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
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("Meter Calculation Application")
        header.setStyleSheet(get_header_style())
        main_layout.addWidget(header)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_main_tab(), "Main Calculation")
        self.tab_widget.addTab(self.create_rooms_tab(), "Room Calculations")
        self.tab_widget.addTab(self.create_history_tab(), "History")
        main_layout.addWidget(self.tab_widget)

        # Save to PDF button
        save_pdf_button = QPushButton("Save to PDF")
        save_pdf_button.setIcon(QIcon("save_icon.png"))
        save_pdf_button.clicked.connect(self.save_to_pdf)
        main_layout.addWidget(save_pdf_button)

    def create_main_tab(self):
        main_tab = QWidget()
        layout = QVBoxLayout()

        # Month Information
        month_info_layout = self.create_month_info_section()
        layout.addLayout(month_info_layout)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Meter and Difference Readings
        readings_layout = self.create_meter_diff_section()
        layout.addLayout(readings_layout)

        # Calculate button
        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self.calculate_main)
        calculate_button.setStyleSheet(get_button_style())
        layout.addWidget(calculate_button)

        # Results section
        self.create_results_section(layout)

        main_tab.setLayout(layout)
        return main_tab

    def create_month_info_section(self):
        month_info_layout = QHBoxLayout()
        
        month_label = QLabel("Month:")
        self.month_combo = QComboBox()
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())

        year_label = QLabel("Year:")
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self.year_spinbox.setStyleSheet(get_month_info_style())

        month_info_layout.addWidget(month_label)
        month_info_layout.addWidget(self.month_combo)
        month_info_layout.addWidget(year_label)
        month_info_layout.addWidget(self.year_spinbox)
        month_info_layout.addStretch(1)  # Add stretch to push widgets to the left

        return month_info_layout

    def create_meter_diff_section(self):
        readings_layout = QHBoxLayout()
        
        meter_group = QGroupBox("Meter Readings")
        meter_group.setStyleSheet(get_group_box_style())
        meter_layout = QFormLayout()
        self.meter_entries = []
        for i in range(3):
            meter_entry = CustomLineEdit()
            meter_entry.setPlaceholderText(f"Enter meter {i+1} reading")
            meter_layout.addRow(f"Meter {i+1} Reading:", meter_entry)
            self.meter_entries.append(meter_entry)
        meter_group.setLayout(meter_layout)
        readings_layout.addWidget(meter_group)

        diff_group = QGroupBox("Difference Readings")
        diff_group.setStyleSheet(get_group_box_style())
        diff_layout = QFormLayout()
        self.diff_entries = []
        for i in range(3):
            diff_entry = CustomLineEdit()
            diff_entry.setPlaceholderText(f"Enter difference {i+1}")
            diff_layout.addRow(f"Difference {i+1}:", diff_entry)
            self.diff_entries.append(diff_entry)
        diff_group.setLayout(diff_layout)
        readings_layout.addWidget(diff_group)

        return readings_layout

    def create_results_section(self, layout):
        results_group = QGroupBox("Results")
        results_layout = QHBoxLayout()
        
        # Create labels for titles and values
        total_unit_title = QLabel("Total Unit")
        self.total_unit_label = QLabel("N/A")
        total_diff_title = QLabel("Total Difference")
        self.total_diff_label = QLabel("N/A")
        per_unit_cost_title = QLabel("Per Unit Cost")
        self.per_unit_cost_label = QLabel("N/A")

        # Create vertical layouts for each result
        total_unit_layout = QVBoxLayout()
        total_unit_layout.addWidget(total_unit_title)
        total_unit_layout.addWidget(self.total_unit_label)

        total_diff_layout = QVBoxLayout()
        total_diff_layout.addWidget(total_diff_title)
        total_diff_layout.addWidget(self.total_diff_label)

        per_unit_cost_layout = QVBoxLayout()
        per_unit_cost_layout.addWidget(per_unit_cost_title)
        per_unit_cost_layout.addWidget(self.per_unit_cost_label)

        # Add vertical layouts to the main horizontal layout
        results_layout.addLayout(total_unit_layout)
        results_layout.addLayout(total_diff_layout)
        results_layout.addLayout(per_unit_cost_layout)

        # Set the layout for the group box
        results_group.setLayout(results_layout)
        results_group.setStyleSheet(get_results_group_style())
        layout.addWidget(results_group)

        # Apply styles to all labels
        for label in [total_unit_title, self.total_unit_label, 
                    total_diff_title, self.total_diff_label, 
                    per_unit_cost_title, self.per_unit_cost_label]:
            label.setStyleSheet("border: none; background-color: transparent; padding: 0;")


    def create_rooms_tab(self):
        rooms_tab = QWidget()
        layout = QVBoxLayout()
        rooms_tab.setLayout(layout)

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

        # Use the new AutoScrollArea
        self.rooms_scroll_area = AutoScrollArea()
        self.rooms_scroll_area.setWidgetResizable(True)
        self.rooms_scroll_widget = QWidget()
        self.rooms_scroll_layout = QGridLayout(self.rooms_scroll_widget)
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget)
        layout.addWidget(self.rooms_scroll_area)

        self.room_entries = []
        self.room_results = []

        self.update_room_inputs()

        calculate_rooms_button = QPushButton("Calculate Room Bills")
        calculate_rooms_button.clicked.connect(self.calculate_rooms)
        calculate_rooms_button.setStyleSheet(get_button_style())
        layout.addWidget(calculate_rooms_button)

        return rooms_tab

    def update_room_inputs(self):
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
        try:
            total_unit = sum(int(entry.text()) for entry in self.meter_entries if entry.text())
            total_diff = sum(int(entry.text()) for entry in self.diff_entries if entry.text())
            if total_diff == 0:
                raise ZeroDivisionError
            per_unit_cost = total_unit / total_diff

            self.total_unit_label.setText(f"{total_unit} TK")
            self.total_diff_label.setText(f"{total_diff}")
            self.per_unit_cost_label.setText(f"{per_unit_cost:.2f} TK")

            self.save_calculation_to_csv()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid integer values for all fields.")
        except ZeroDivisionError:
            QMessageBox.warning(self, "Division by Zero", "Total Diff cannot be zero.")

    def calculate_rooms(self):
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
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def save_calculation_to_csv(self):
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
                    self.total_unit_label.text().replace("TK", ""),
                    self.total_diff_label.text(),
                    self.per_unit_cost_label.text().replace("TK", "")
                ]
                writer.writerow(main_data)

                # Write room calculation data
                for i, (present_entry, previous_entry) in enumerate(self.room_entries):
                    real_unit_label, unit_bill_label = self.room_results[i]
                    room_data = [
                        month_name,
                        f"Room {i+1}",
                        present_entry.text(),
                        previous_entry.text(),
                        real_unit_label.text(),
                        unit_bill_label.text().replace("TK", "")
                    ]
                    writer.writerow([""] * 10 + room_data)

            QMessageBox.information(self, "Save Successful", "Calculation data has been saved to CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")


    def create_history_tab(self):
        history_tab = QWidget()
        layout = QVBoxLayout()
        history_tab.setLayout(layout)

        # Add month and year selection
        filter_layout = QHBoxLayout()
        
        month_label = QLabel("Month:")
        self.history_month_combo = QComboBox()
        self.history_month_combo.addItems([
            "All", "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        
        year_label = QLabel("Year:")
        self.history_year_input = QLineEdit()
        self.history_year_input.setPlaceholderText("Enter year or leave blank for all")
        
        filter_layout.addWidget(month_label)
        filter_layout.addWidget(self.history_month_combo)
        filter_layout.addWidget(year_label)
        filter_layout.addWidget(self.history_year_input)
        
        layout.addLayout(filter_layout)

        # Main Calculation Info Section
        main_calc_label = QLabel("Main Calculation Info")
        main_calc_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #065F46;")
        layout.addWidget(main_calc_label)

        self.main_history_table = QTableWidget()
        self.main_history_table.setColumnCount(10)
        self.main_history_table.setHorizontalHeaderLabels([
            "Month", "Meter-1", "Meter-2", "Meter-3", 
            "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
            "Total Diff", "Per Unit Cost"
        ])
        self.main_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.main_history_table)

        # Room Calculation Info Section
        room_calc_label = QLabel("Room Calculation Info")
        room_calc_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #065F46;")
        layout.addWidget(room_calc_label)

        self.room_history_table = QTableWidget()
        self.room_history_table.setColumnCount(6)
        self.room_history_table.setHorizontalHeaderLabels([
            "Month", "Room", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"
        ])
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.room_history_table)

        load_history_button = QPushButton("Load History")
        load_history_button.clicked.connect(self.load_history)
        layout.addWidget(load_history_button)

        return history_tab

    def load_history(self):
        filename = "meter_calculation_history.csv"
        if not os.path.isfile(filename):
            QMessageBox.information(self, "No History", "No history available")
            return

        try:
            selected_month = self.history_month_combo.currentText()
            selected_year = self.history_year_input.text().strip()

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
                    (not selected_year or year == selected_year):
                        filtered_history.append(row)

            # Load main calculation info
            main_history = [row[:10] for row in filtered_history]
            self.main_history_table.setRowCount(len(main_history))
            for row_index, row in enumerate(main_history):
                for column_index, item in enumerate(row):
                    self.main_history_table.setItem(row_index, column_index, QTableWidgetItem(item))

            # Load room calculation info
            room_history = [row[10:] for row in filtered_history]
            self.room_history_table.setRowCount(len(room_history))
            for row_index, row in enumerate(room_history):
                for column_index, item in enumerate(row):
                    self.room_history_table.setItem(row_index, column_index, QTableWidgetItem(item))

            QMessageBox.information(self, "History Loaded", f"Loaded {len(filtered_history)} records from history.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load history: {str(e)}")

    def save_to_pdf(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.generate_pdf(file_path)

    def generate_pdf(self, file_path):
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
        for i in range(len(all_entries)):
            if i > 0:
                all_entries[i].previous_widget = all_entries[i - 1]
            if i < len(all_entries) - 1:
                all_entries[i].next_widget = all_entries[i + 1]

        # Ensure the first and last entries' navigation is correctly terminated
        if all_entries:
            all_entries[0].previous_widget = None
            all_entries[-1].next_widget = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeterCalculationApp()
    window.show()
    sys.exit(app.exec_())