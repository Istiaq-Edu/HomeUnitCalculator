import sys
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea
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

class CustomLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down, Qt.Key_Right):
            self.focusNextChild()
        elif event.key() in (Qt.Key_Up, Qt.Key_Left):
            self.focusPreviousChild()
        else:
            super().keyPressEvent(event)

class MeterCalculationApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.meter1_value = QLineEdit()
        self.meter2_value = QLineEdit()
        self.meter3_value = QLineEdit()


        self.setWindowTitle("Meter Calculation Application")
        self.setGeometry(100, 100, 1000, 700)

        self.is_dark_theme = False
        self.apply_stylesheet()

        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.main_tab = QWidget()
        self.rooms_tab = QWidget()
        self.history_tab = QWidget()

        self.tabs.addTab(self.main_tab, "Main Calculation")
        self.tabs.addTab(self.rooms_tab, "Room Calculations")
        self.tabs.addTab(self.history_tab, "History")

        self.month_name_entry = None
        self.num_rooms_spinbox = None

        self.init_main_tab()
        self.init_rooms_tab()
        self.init_history_tab()

        self.theme_toggle_button = QPushButton("Toggle Theme")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        self.tabs.setCornerWidget(self.theme_toggle_button, Qt.TopRightCorner)

    def init_main_tab(self):
        layout = QVBoxLayout()
        self.main_tab.setLayout(layout)

        header_font = QFont('Segoe UI', 16, QFont.Bold)

        month_layout = QHBoxLayout()
        month_label = QLabel("Month Name:")
        self.month_name_entry = QLineEdit()
        month_layout.addWidget(month_label)
        month_layout.addWidget(self.month_name_entry)
        layout.addLayout(month_layout)

        self.create_meter_section(layout, header_font)
        self.create_diff_section(layout, header_font)

        calculate_button = QPushButton("Calculate")
        calculate_button.clicked.connect(self.calculate_main)
        layout.addWidget(calculate_button)

        self.create_results_section(layout)

        save_pdf_button = QPushButton("Save to PDF")
        save_pdf_button.clicked.connect(self.save_to_pdf)
        layout.addWidget(save_pdf_button)

    def create_meter_section(self, layout, header_font):
        meter_label = QLabel("Meter Readings")
        meter_label.setFont(header_font)
        layout.addWidget(meter_label)

        meter_layout = QGridLayout()
        self.meter_entries = []
        for i in range(3):
            meter_lbl = QLabel(f"Meter-{i+1}:")
            meter_entry = CustomLineEdit()
            self.meter_entries.append(meter_entry)
            meter_layout.addWidget(meter_lbl, i, 0)
            meter_layout.addWidget(meter_entry, i, 1)

        layout.addLayout(meter_layout)

    def create_diff_section(self, layout, header_font):
        diff_label = QLabel("Diff Readings")
        diff_label.setFont(header_font)
        layout.addWidget(diff_label)

        diff_layout = QGridLayout()
        self.diff_entries = []
        for i in range(3):
            diff_lbl = QLabel(f"Diff-{i+1}:")
            diff_entry = CustomLineEdit()
            self.diff_entries.append(diff_entry)
            diff_layout.addWidget(diff_lbl, i, 0)
            diff_layout.addWidget(diff_entry, i, 1)

        layout.addLayout(diff_layout)

    def create_results_section(self, layout):
        results_group = QGroupBox("Results")
        results_layout = QFormLayout()
        self.total_unit_label = QLabel()
        self.total_diff_label = QLabel()
        self.per_unit_cost_label = QLabel()

        results_layout.addRow("Total Unit:", self.total_unit_label)
        results_layout.addRow("Total Diff:", self.total_diff_label)
        results_layout.addRow("Per Unit Cost:", self.per_unit_cost_label)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

    def init_rooms_tab(self):
        layout = QVBoxLayout()
        self.rooms_tab.setLayout(layout)

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
        layout.addWidget(calculate_rooms_button)

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

    def init_history_tab(self):
        layout = QVBoxLayout()
        self.history_tab.setLayout(layout)

        self.history_text = QLabel("No history available")
        layout.addWidget(self.history_text)

        load_history_button = QPushButton("Load History")
        load_history_button.clicked.connect(self.load_history)
        layout.addWidget(load_history_button)

    def calculate_main(self):
        try:
            total_unit = sum(float(entry.text()) for entry in self.meter_entries if entry.text())
            total_diff = sum(float(entry.text()) for entry in self.diff_entries if entry.text())
            if total_diff == 0:
                raise ZeroDivisionError
            per_unit_cost = total_unit / total_diff

            self.total_unit_label.setText(f"{total_unit:.2f}")
            self.total_diff_label.setText(f"{total_diff:.2f}")
            self.per_unit_cost_label.setText(f"{per_unit_cost:.2f}")

            self.save_calculation_to_csv()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for all fields.")
        except ZeroDivisionError:
            QMessageBox.warning(self, "Division by Zero", "Total Diff cannot be zero.")

    def calculate_rooms(self):
        try:
            per_unit_cost_text = self.per_unit_cost_label.text()
            if not per_unit_cost_text:
                raise ValueError("Per unit cost not calculated")

            per_unit_cost = float(per_unit_cost_text)
            for (present_entry, previous_entry), (real_unit_label, unit_bill_label) in zip(self.room_entries, self.room_results):
                present_text = present_entry.text()
                previous_text = previous_entry.text()
                if present_text and previous_text:
                    present_unit = float(present_text)
                    previous_unit = float(previous_text)
                    real_unit = present_unit - previous_unit
                    unit_bill = real_unit * per_unit_cost

                    real_unit_label.setText(f"{real_unit:.2f}")
                    unit_bill_label.setText(f"{unit_bill:.2f}")
                else:
                    real_unit_label.setText("Incomplete")
                    unit_bill_label.setText("Incomplete")
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def save_calculation_to_csv(self):
        month_name = self.month_name_entry.text() or datetime.now().strftime("%B %Y")
        filename = "meter_calculation_history.csv"
        
        file_exists = os.path.isfile(filename)
        
        with open(filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Month", "Total Unit", "Total Diff", "Per Unit Cost"])
            writer.writerow([
                month_name,
                self.total_unit_label.text(),
                self.total_diff_label.text(),
                self.per_unit_cost_label.text()
            ])

    def load_history(self):
        filename = "meter_calculation_history.csv"
        if not os.path.isfile(filename):
            self.history_text.setText("No history available")
            return

        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            history = list(reader)

        if not history:
            self.history_text.setText("No history available")
            return

        history_text = "Calculation History:\n\n"
        for row in history[-5:]:  # Show last 5 entries
            history_text += f"Month: {row[0]}\n"
            history_text += f"Total Unit: {row[1]}\n"
            history_text += f"Total Diff: {row[2]}\n"
            history_text += f"Per Unit Cost: {row[3]}\n\n"

        self.history_text.setText(history_text)

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
            fontSize=16,  # Increased font size
            textColor=colors.darkblue,
            spaceAfter=10,
            alignment=TA_CENTER  # Center align
        )
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading2'],
            fontSize=14,  # Increased font size
            textColor=colors.darkblue,
            spaceAfter=5,
            alignment=TA_CENTER  # Center align
        )
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10,  # Increased font size
            textColor=colors.black,
            spaceAfter=2
        )
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=9,  # Increased font size
            textColor=colors.grey,
            spaceAfter=1
        )

        # Define the create_cell function
        def create_cell(text, bgcolor=colors.lightsteelblue, textcolor=colors.black, style=normal_style, height=0.2*inch):
            return Table(
                [[Paragraph(text, style)]],
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
        elements.append(Spacer(1, 0.1*inch))  # Adjusted spacer

        # Month
        elements.append(create_cell(f"Month: {self.month_name_entry.text() or 'Not specified'}", bgcolor=colors.lightsteelblue, textcolor=colors.red, style=header_style, height=0.3*inch))
        elements.append(Spacer(1, 0.1*inch))  # Adjusted spacer

        # Main Meter Info Headline
        elements.append(Spacer(1, 0.1*inch))  # Add some space before the header
        elements.append(create_cell("Main Meter Info", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
        #elements.append(Spacer(1, 0.05*inch))  # Add space after the header

        # Main Meter Info Content (Add after the headline)
        meter_info_left = [
            [Paragraph("Meter-1:", normal_style), Paragraph(f"{self.meter1_value.text() or 'N/A'}", normal_style)],
            [Paragraph("Meter-2:", normal_style), Paragraph(f"{self.meter2_value.text() or 'N/A'}", normal_style)],
            [Paragraph("Meter-3:", normal_style), Paragraph(f"{self.meter3_value.text() or 'N/A'}", normal_style)],
        ]

        meter_info_right = [
            [Paragraph("Total Unit Cost:", normal_style), Paragraph(f"{self.total_unit_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Total Diff:", normal_style), Paragraph(f"{self.total_diff_label.text() or 'N/A'}", normal_style)],
            [Paragraph("Per Unit Cost:", normal_style), Paragraph(f"{self.per_unit_cost_label.text() or 'N/A'}", normal_style)],
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
        elements.append(Spacer(1, 0.1*inch))  # Add space after the content


        # Room Info Headline
        elements.append(Spacer(1, 0.1*inch))  # Add some space before the header
        elements.append(create_cell("Room Information", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
        #elements.append(Spacer(1, 0.05*inch))  # Adjusted spacer

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
                        [Paragraph("Present Unit:", label_style), Paragraph(present_entry.text() or 'N/A', normal_style)],
                        [Paragraph("Previous Unit:", label_style), Paragraph(previous_entry.text() or 'N/A', normal_style)],
                        [Paragraph("Real Unit:", label_style), Paragraph(real_unit_label.text() or 'N/A', normal_style)],
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








    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_stylesheet()

    def apply_stylesheet(self):
        if self.is_dark_theme:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #121212;
                    color: #FFFFFF;
                }
                QLabel {
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    color: #FFFFFF;
                }
                QLineEdit, QSpinBox {
                    padding: 8px;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                }
                QPushButton {
                    padding: 10px;
                    background-color: #3A3A3A;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 5px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QGroupBox {
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                    color: #FFFFFF;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    margin-top: 10px;
                    background-color: #1E1E1E;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 10px;
                    background-color: transparent;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #1E1E1E;
                }
                QTabBar::tab {
                    background: #2C2C2C;
                    color: #FFFFFF;
                    padding: 10px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }
                QTabBar::tab:selected {
                    background: #3A3A3A;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QLabel {
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    color: #333333;
                }
                QLineEdit, QSpinBox {
                    padding: 8px;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    background-color: #FFFFFF;
                    color: #333333;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                }
                QPushButton {
                    padding: 10px;
                    background-color: #4CAF50;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 5px;
                    font-family: 'Segoe UI';
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QGroupBox {
                    font-family: 'Segoe UI';
                    font-size: 14px;
                    font-weight: bold;
                    color: #4CAF50;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 10px;
                    background-color: #FFFFFF;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 10px;
                    background-color: transparent;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background-color: #FFFFFF;
                }
                QTabBar::tab {
                    background: #e0e0e0;
                    color: #333333;
                    padding: 10px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }
                QTabBar::tab:selected {
                    background: #4CAF50;
                    color: #FFFFFF;
                }
            """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MeterCalculationApp()
    window.show()
    sys.exit(app.exec_())