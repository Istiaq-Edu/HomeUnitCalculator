import sys
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView
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
    get_room_group_style
    # get_main_label_style, get_sub_header_style
)

class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QRegExpValidator(QRegExp(r'^\d*$')))
        self.setPlaceholderText("Enter a number")
        self.setToolTip("Input only integer values")
        self.next_widget = None
        self.previous_widget = None

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
        month_group = QGroupBox("Month Information")
        month_group.setStyleSheet(get_group_box_style())
        month_layout = QFormLayout()
        self.month_name_entry = QLineEdit()
        self.month_name_entry.setPlaceholderText("E.g., January 2024")
        self.month_name_entry.setStyleSheet(get_line_edit_style())
        month_layout.addRow("Month Name:", self.month_name_entry)
        month_group.setLayout(month_layout)
        layout.addWidget(month_group)

        # Meter and Difference Readings
        readings_layout = QHBoxLayout()
        
        meter_group = QGroupBox("Meter Readings")
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
        diff_layout = QFormLayout()
        self.diff_entries = []
        for i in range(3):
            diff_entry = CustomLineEdit()
            diff_entry.setPlaceholderText(f"Enter difference {i+1}")
            diff_layout.addRow(f"Difference {i+1}:", diff_entry)
            self.diff_entries.append(diff_entry)
        diff_group.setLayout(diff_layout)
        readings_layout.addWidget(diff_group)

        layout.addLayout(readings_layout)

        # Calculate button
        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self.calculate_main)
        calculate_button.setStyleSheet(get_button_style())
        layout.addWidget(calculate_button)

        # Results section
        self.create_results_section(layout)

        # Save to PDF button
        save_pdf_button = QPushButton("Save to PDF")
        save_pdf_button.clicked.connect(self.save_to_pdf)
        save_pdf_button.setStyleSheet(get_button_style())
        layout.addWidget(save_pdf_button)

        main_tab.setLayout(layout)
        return main_tab

    def create_meter_and_diff_section(self, layout):
        meter_diff_label = QLabel("Meter and Diff Readings")
        meter_diff_label.setFont(QFont('Segoe UI', 18, QFont.Bold))
        layout.addWidget(meter_diff_label)

        meter_diff_layout = QGridLayout()
        self.meter_entries = []
        self.diff_entries = []
        for i in range(3):
            meter_lbl = QLabel(f"Meter-{i+1}:")
            meter_entry = CustomLineEdit()
            self.meter_entries.append(meter_entry)
            meter_diff_layout.addWidget(meter_lbl, i, 0)
            meter_diff_layout.addWidget(meter_entry, i, 1)

            diff_lbl = QLabel(f"Diff-{i+1}:")
            diff_entry = CustomLineEdit()
            self.diff_entries.append(diff_entry)
            meter_diff_layout.addWidget(diff_lbl, i, 2)
            meter_diff_layout.addWidget(diff_entry, i, 3)

        layout.addLayout(meter_diff_layout)

    def create_results_section(self, layout):
        results_group = QGroupBox("Results")
        results_layout = QFormLayout()
        self.total_unit_label = QLabel("N/A")
        self.total_diff_label = QLabel("N/A")
        self.per_unit_cost_label = QLabel("N/A")

        results_layout.addRow("Total Unit:", self.total_unit_label)
        results_layout.addRow("Total Diff:", self.total_diff_label)
        results_layout.addRow("Per Unit Cost:", self.per_unit_cost_label)

        results_group.setLayout(results_layout)
        results_group.setStyleSheet(get_results_group_style())
        layout.addWidget(results_group)

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
        num_rooms_layout.addWidget(num_rooms_label)
        num_rooms_layout.addWidget(self.num_rooms_spinbox)
        layout.addLayout(num_rooms_layout)

        self.rooms_scroll_area = QScrollArea()
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

            room_layout.addRow("Present Unit:", present_entry)
            room_layout.addRow("Previous Unit:", previous_entry)
            room_layout.addRow("Real Unit:", real_unit_label)
            room_layout.addRow("Unit Bill:", unit_bill_label)

            self.room_entries.append((present_entry, previous_entry))
            self.room_results.append((real_unit_label, unit_bill_label))

            self.rooms_scroll_layout.addWidget(room_group, i // 3, i % 3)

    def create_history_tab(self):
        history_tab = QWidget()
        layout = QVBoxLayout()
        history_tab.setLayout(layout)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(10)
        self.history_table.setHorizontalHeaderLabels([
            "Month", "Meter-1", "Meter-2", "Meter-3", 
            "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
            "Total Diff", "Per Unit Cost"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)

        load_history_button = QPushButton("Load History")
        load_history_button.clicked.connect(self.load_history)
        layout.addWidget(load_history_button)

        return history_tab

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
        month_name = self.month_name_entry.text() or datetime.now().strftime("%B %Y")
        filename = "meter_calculation_history.csv"
        
        try:
            file_exists = os.path.isfile(filename)
            
            with open(filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow([
                        "Month", "Meter-1", "Meter-2", "Meter-3", 
                        "Diff-1", "Diff-2", "Diff-3", "Total Unit", 
                        "Total Diff", "Per Unit Cost"
                    ])

                writer.writerow([
                    month_name,
                    *[entry.text() for entry in self.meter_entries],
                    *[entry.text() for entry in self.diff_entries],
                    self.total_unit_label.text().replace("TK", ""),
                    self.total_diff_label.text(),
                    self.per_unit_cost_label.text().replace("TK", "")
                ])

            QMessageBox.information(self, "Save Successful", "Calculation data has been saved to CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save data: {str(e)}")

    def load_history(self):
        filename = "meter_calculation_history.csv"
        if not os.path.isfile(filename):
            QMessageBox.information(self, "No History", "No history available")
            return

        try:
            with open(filename, mode='r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip header row
                history = list(reader)

            self.history_table.setRowCount(len(history))
            for row_index, row in enumerate(history):
                for column_index, item in enumerate(row):
                    self.history_table.setItem(row_index, column_index, QTableWidgetItem(item))
            
            QMessageBox.information(self, "History Loaded", f"Loaded {len(history)} records from history.")
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
        month_paragraph = Paragraph(f"Month: <font color='red'>{self.month_name_entry.text() or 'Not specified'}</font>", header_style)
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
                        [Paragraph("Month:", label_style), Paragraph(self.month_name_entry.text() or 'N/A', normal_style)],
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
        # Link CustomLineEdits for navigation
        all_entries = []
        for i in range(3):
            all_entries.append(self.meter_entries[i])
            all_entries.append(self.diff_entries[i])
        all_entries.extend([entry for pair in self.room_entries for entry in pair])

        for i in range(len(all_entries) - 1):
            all_entries[i].next_widget = all_entries[i + 1]
            all_entries[i + 1].previous_widget = all_entries[i]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeterCalculationApp()
    window.show()
    sys.exit(app.exec_())