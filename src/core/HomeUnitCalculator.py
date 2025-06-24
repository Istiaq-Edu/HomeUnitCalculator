import sys
import os
# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
from datetime import datetime as dt_class

import functools
import logging
from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor, QKeySequence, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame, QShortcut,
    QAbstractSpinBox, QStyleOptionSpinBox, QStyle, QDesktopWidget, QSizePolicy, QDialog, QAbstractItemView
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import csv
import os
import traceback
from postgrest.exceptions import APIError
from datetime import datetime
from src.core.db_manager import DBManager
from src.core.encryption_utils import EncryptionUtil
from src.core.key_manager import get_or_create_key
from src.core.supabase_manager import SupabaseManager # New import
from src.ui.styles import (
    get_stylesheet, get_header_style, get_group_box_style,
    get_line_edit_style, get_button_style, get_results_group_style,
    get_room_group_style, get_month_info_style, get_table_style, get_label_style, get_custom_spinbox_style,
    get_room_selection_style, get_result_title_style, get_result_value_style
)
from src.core.utils import resource_path
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomSpinBox, CustomNavButton
from src.ui.tabs.main_tab import MainTab
from src.ui.tabs.rooms_tab import RoomsTab
from src.ui.tabs.history_tab import HistoryTab, EditRecordDialog # EditRecordDialog is imported from history_tab
from src.ui.tabs.supabase_config_tab import SupabaseConfigTab
from src.ui.tabs.rental_info_tab import RentalInfoTab
from src.ui.tabs.archived_info_tab import ArchivedInfoTab

# Fluent design toast-like information bars (non-blocking replacements for QMessageBox.information)
try:
    from qfluentwidgets import InfoBar, InfoBarPosition  # type: ignore

    def _non_blocking_information(parent, title, text, *_, **__):  # noqa: D401, ANN001
        """Patched replacement for QMessageBox.information that shows a transient Fluent InfoBar.

        Returns immediately with QMessageBox.Ok so that existing calling code keeps working
        without modifications.
        """
        # Use success style for positive feedback; feel free to tweak orientation/position here
        InfoBar.success(
            title=title,
            content=text,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,  # auto-dismiss after 3 s; negative value means stay until closed
            parent=parent,
        )
        return QMessageBox.Ok

    # Monkey-patch only if it hasn't been patched yet (to avoid double-patching in tests)
    if not getattr(QMessageBox.information, "__fluent_patched__", False):
        _non_blocking_information.__fluent_patched__ = True  # type: ignore[attr-defined]
        QMessageBox.information = _non_blocking_information  # type: ignore[assignment]
except ImportError:
    # If PyQt-Fluent-Widgets isn't installed, fall back silently to the default behaviour.
    pass
# ----------------------------------------------------------------------------------------------

class MeterCalculationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Home Unit Calculator")
        self.setGeometry(100, 100, 1300, 860)
        self.setStyleSheet(get_stylesheet())
        self.setWindowIcon(QIcon(resource_path("icons/icon.png")))

        # Ensure the data/images directory exists
        self.image_storage_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'images')
        os.makedirs(self.image_storage_dir, exist_ok=True)
        
        self.db_manager = DBManager()
        self.encryption_util = EncryptionUtil()
        self.supabase_manager = SupabaseManager() # Initialize SupabaseManager
        
        self.load_info_source_combo = QComboBox()
        self.load_info_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_info_source_combo.setStyleSheet(get_month_info_style())
        
        self.load_history_source_combo = QComboBox()
        self.load_history_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_history_source_combo.setStyleSheet(get_month_info_style())

        self.main_tab_instance = MainTab(self)
        self.rooms_tab_instance = RoomsTab(self.main_tab_instance, self)
        self.history_tab_instance = HistoryTab(self)
        self.supabase_config_tab_instance = SupabaseConfigTab(self)
        self.rental_info_tab_instance = RentalInfoTab(self)
        self.archived_info_tab_instance = ArchivedInfoTab(self)

        self._initialize_supabase_client()
        self.init_ui()
        self.setup_navigation()
        self.center_window()

    def check_internet_connectivity(self):
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            return True
        except OSError:
            return False

    def _initialize_supabase_client(self):
        # Re-create the SupabaseManager so that it (re)initializes its client
        # internally. This avoids calling its protected methods directly and
        # keeps the encapsulation boundary intact.

        self.supabase_manager = SupabaseManager()
        
        if self.supabase_manager.is_client_initialized():
            # Set default load source to Cloud if Supabase is configured
            self.load_history_source_combo.setCurrentText("Load from Cloud")
        else:
            print("Supabase client not initialized. Cloud features disabled.")
            # If Supabase fails to initialize, ensure source is PC (CSV)
            self.load_history_source_combo.setCurrentText("Load from PC (CSV)")

    def init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QLabel("Meter Calculation Application")
        header.setStyleSheet(get_header_style())
        main_layout.addWidget(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("QTabWidget::pane { border: 0; }")

        self.tab_widget.addTab(self.main_tab_instance, "Main Calculation")
        self.tab_widget.addTab(self.rooms_tab_instance, "Room Calculations")
        self.tab_widget.addTab(self.history_tab_instance, "Calculation History")
        self.tab_widget.addTab(self.supabase_config_tab_instance, "Supabase Config")
        self.tab_widget.addTab(self.rental_info_tab_instance, "Rental Info")
        self.tab_widget.addTab(self.archived_info_tab_instance, "Archived Info")
        
        # Connection is done in setup_navigation() with guard
        main_layout.addWidget(self.tab_widget)

        # Create buttons but don't add them to the main layout yet
        self.save_pdf_button = QPushButton("Save as PDF")
        self.save_pdf_button.setObjectName("savePdfButton")
        self.save_pdf_button.setIcon(QIcon(resource_path("icons/save_icon.png")))
        self.save_pdf_button.clicked.connect(self.save_to_pdf)

        self.save_csv_button = QPushButton("Save as CSV")
        self.save_csv_button.setObjectName("saveCsvButton")
        self.save_csv_button.setIcon(QIcon(resource_path("icons/save_icon.png")))
        self.save_csv_button.clicked.connect(self.save_calculation_to_csv)

        self.save_cloud_button = QPushButton("Save to Cloud")
        self.save_cloud_button.setObjectName("saveCloudButton")
        self.save_cloud_button.setIcon(QIcon(resource_path("icons/database_icon.png")))
        self.save_cloud_button.clicked.connect(self.save_calculation_to_supabase)

        # Create a layout for these buttons
        self.save_buttons_layout = QHBoxLayout()
        self.save_buttons_layout.addWidget(self.save_pdf_button)
        self.save_buttons_layout.addWidget(self.save_csv_button)
        self.save_buttons_layout.addWidget(self.save_cloud_button)
        
        # Add the button layout to the main layout
        main_layout.addLayout(self.save_buttons_layout)

        # Connect tab change signal to update button visibility
        self.tab_widget.currentChanged.connect(self.update_save_buttons_visibility)
        self.update_save_buttons_visibility(self.tab_widget.currentIndex()) # Set initial visibility

    def update_save_buttons_visibility(self, index):
        # Get the name of the current tab
        current_tab_name = self.tab_widget.tabText(index)
        
        # Define which tabs should show the buttons
        if current_tab_name in ["Main Calculation", "Room Calculations"]:
            self.save_pdf_button.show()
            self.save_csv_button.show()
            self.save_cloud_button.show()
        else:
            self.save_pdf_button.hide()
            self.save_csv_button.hide()
            self.save_cloud_button.hide()

    def save_to_pdf(self):
        month_name = self.main_tab_instance.month_combo.currentText()
        year_value = self.main_tab_instance.year_spinbox.value()
        default_filename = f"MeterCalculation_{month_name}_{year_value}.pdf"
        
        def try_save_pdf(path):
            try:
                self.generate_pdf(path)
                QMessageBox.information(self, "PDF Saved", f"Report saved to {path}")
                return True
            except PermissionError:
                QMessageBox.warning(self, "Permission Denied",
                                  f"Cannot save to {path}\n\nThe file may be open in another program or you don't have write permission to this location. Please close any programs using this file and try again or select a different location.")
                return False
            except Exception as e:
                QMessageBox.critical(self, "PDF Save Error", f"Failed to save PDF: {e}\n{traceback.format_exc()}")
                return False
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", default_filename, "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            try_save_pdf(file_path)

    def generate_pdf(self, file_path):
        doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=0.3*inch, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.darkblue, spaceAfter=10, alignment=TA_CENTER)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.darkblue, spaceAfter=5, alignment=TA_CENTER)
        normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=10, textColor=colors.black, spaceAfter=2)
        label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=9, textColor=colors.grey, spaceAfter=1)
        bold_number_style = ParagraphStyle('BoldNumberStyle', parent=styles['Normal'], fontSize=12, textColor=colors.black, spaceAfter=2, fontName='Helvetica-Bold')

        def create_cell(content, bgcolor=colors.lightsteelblue, textcolor=colors.black, style=normal_style, height=0.2*inch):
            if isinstance(content, str): content = Paragraph(content, style)
            return Table([[content]], colWidths=[7.5*inch], rowHeights=[height], style=TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bgcolor), ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,-1), textcolor), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))

        elements.append(Paragraph("Meter Calculation Report", title_style))
        elements.append(Spacer(1, 0.1*inch))
        month_year = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
        elements.append(create_cell(Paragraph(f"Month: <font color='red'>{month_year}</font>", header_style), bgcolor=colors.lightsteelblue, height=0.3*inch))
        elements.append(Spacer(1, 0.05*inch))
        elements.append(create_cell("Main Meter Info", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
        
        meter_info_left_data = []
        for i in range(len(self.main_tab_instance.meter_entries)):
            meter_info_left_data.append(
                [Paragraph(f"Meter-{i+1} Unit:", normal_style), Paragraph(self.main_tab_instance.meter_entries[i].text() or '0', normal_style)]
            )
        meter_info_left_data.append(
            [Paragraph("Total Difference:", normal_style), Paragraph(f"{self.main_tab_instance.total_diff_value_label.text() or 'N/A'}", normal_style)]
        )
        
        meter_info_right_data = [
            [Paragraph("Per Unit Cost:", normal_style), Paragraph(f"{self.main_tab_instance.per_unit_cost_value_label.text() or 'N/A'}", bold_number_style)],
            [Paragraph("Total Unit Cost:", normal_style), Paragraph(f"{self.main_tab_instance.total_unit_value_label.text() or 'N/A'} TK", bold_number_style)],
            [Paragraph("Added Amount:", normal_style), Paragraph(f"{self.main_tab_instance.additional_amount_value_label.text() or 'N/A'}", normal_style)],
            [Paragraph("In Total Amount:", normal_style), Paragraph(f"{self.main_tab_instance.in_total_value_label.text() or 'N/A'}", bold_number_style)],
        ]

        max_rows = max(len(meter_info_left_data), len(meter_info_right_data))
        while len(meter_info_left_data) < max_rows: meter_info_left_data.append([Paragraph("", normal_style), Paragraph("", normal_style)])
        while len(meter_info_right_data) < max_rows: meter_info_right_data.append([Paragraph("", normal_style), Paragraph("", normal_style)])
        
        main_meter_table_data = [meter_info_left_data[i] + meter_info_right_data[i] for i in range(max_rows)]
        main_meter_table = Table(main_meter_table_data, colWidths=[2.5*inch, 1.25*inch, 2.5*inch, 1.25*inch], rowHeights=[0.2*inch] * max_rows)
        main_meter_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white), ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.lightgrey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(main_meter_table)
        elements.append(Spacer(1, 0.1*inch))

        elements.append(create_cell("Room Information", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
        
        room_pdf_data = []
        if self.rooms_tab_instance.room_entries:
            for i in range(0, len(self.rooms_tab_instance.room_entries), 2):
                row = []
                for j in range(2):
                    if i + j < len(self.rooms_tab_instance.room_entries):
                        room_data = self.rooms_tab_instance.room_entries[i+j]
                        
                        real_unit_label = room_data['real_unit_label']
                        unit_bill_label = room_data['unit_bill_label']
                        gas_bill_entry = room_data['gas_bill_entry']
                        water_bill_entry = room_data['water_bill_entry']
                        house_rent_entry = room_data['house_rent_entry']
                        grand_total_label = room_data['grand_total_label']

                        room_group_widget = self.rooms_tab_instance.rooms_scroll_layout.itemAtPosition((i+j)//3, (i+j)%3).widget()
                        room_name = room_group_widget.title() if isinstance(room_group_widget, QGroupBox) else f"Room {i+j+1}"
                        month_idx = self.main_tab_instance.month_combo.currentIndex()
                        next_month_name = self.main_tab_instance.month_combo.itemText((month_idx + 1) % 12)
                        
                        room_header_style_pdf = ParagraphStyle('RoomHeaderStylePdf', parent=styles['Normal'], fontSize=10, textColor=colors.darkblue, spaceAfter=2, fontName='Helvetica-Bold')
                        bold_unit_bill_style_pdf = ParagraphStyle('BoldUnitBillStylePdf', parent=styles['Normal'], fontSize=11, textColor=colors.black, spaceAfter=2, fontName='Helvetica-Bold')
                        header_style_left_pdf = ParagraphStyle('HeaderStyleLeftPdf', parent=room_header_style_pdf, alignment=0)
                        header_style_right_gray_pdf = ParagraphStyle('HeaderStyleRightGrayPdf', parent=room_header_style_pdf, alignment=2, textColor=colors.gray)
 
                        header_row_pdf = [Paragraph(f"{room_name}", header_style_left_pdf), Paragraph(f"Created: {next_month_name}", header_style_right_gray_pdf)]

                        room_info_data = [ header_row_pdf,
                            [Paragraph("Month:", label_style), Paragraph(month_year, normal_style)],
                            [Paragraph("Per-Unit Cost:", label_style), Paragraph(self.main_tab_instance.per_unit_cost_value_label.text() or 'N/A', normal_style)],
                            [Paragraph("Unit:", label_style), Paragraph(real_unit_label.text() or 'N/A', normal_style)],
                            [Paragraph("Unit Bill:", label_style), Paragraph(unit_bill_label.text() or 'N/A', bold_unit_bill_style_pdf)],
                            [Paragraph("Gas Bill:", label_style), Paragraph(gas_bill_entry.text() or '0.00', normal_style)],
                            [Paragraph("Water Bill:", label_style), Paragraph(water_bill_entry.text() or '0.00', normal_style)],
                            [Paragraph("House Rent:", label_style), Paragraph(house_rent_entry.text() or '0.00', normal_style)],
                            [Paragraph("Grand Total:", label_style), Paragraph(grand_total_label.text() or 'N/A', bold_unit_bill_style_pdf)]]
                        room_table_pdf = Table(room_info_data, colWidths=[1.5*inch, 2.15*inch], rowHeights=[0.3*inch] + [0.2*inch]*8)
                        room_table_pdf.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.lightsteelblue), ('BACKGROUND', (0,1), (-1,-1), colors.white),
                            ('BOX', (0,0), (-1,-1), 1, colors.darkblue), ('LINEBELOW', (0,0), (-1,0), 1, colors.darkblue),
                            ('LINEBELOW', (0,4), (-1,4), 2, colors.darkblue), # Thick line below Unit Bill (row 4, 0-indexed)
                            ('LINEABOVE', (0,1), (-1,-1), 1, colors.lightgrey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
                            ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
                        row.append(room_table_pdf)
                    else: row.append("")
                room_pdf_data.append(row)
        if room_pdf_data:
            room_table_main = Table(room_pdf_data, colWidths=[3.85*inch, 3.85*inch], spaceBefore=0.05*inch)
            room_table_main.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            elements.append(room_table_main)
        
        # Add summary section for all room bills
        if self.rooms_tab_instance.room_entries:
            room_bill_totals = self.rooms_tab_instance.get_all_room_bill_totals()
            
            elements.append(Spacer(1, 0.1*inch))
            elements.append(create_cell("Total Room Bills Summary", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
            
            summary_data = [
                [Paragraph("Total House Rent:", normal_style), Paragraph(f"{room_bill_totals['total_house_rent']:.2f} TK", normal_style)],
                [Paragraph("Total Water Bill:", normal_style), Paragraph(f"{room_bill_totals['total_water_bill']:.2f} TK", normal_style)],
                [Paragraph("Total Gas Bill:", normal_style), Paragraph(f"{room_bill_totals['total_gas_bill']:.2f} TK", normal_style)],
                [Paragraph("Total Room Unit Bill:", normal_style), Paragraph(f"{room_bill_totals['total_room_unit_bill']:.2f} TK", normal_style)],
            ]
            summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch], rowHeights=[0.2*inch]*4)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.white), ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
                ('LINEABOVE', (0,0), (-1,-1), 1, colors.lightgrey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            elements.append(summary_table)

        doc.build(elements)

    def save_calculation_to_csv(self):
        month_name = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
        filename = "meter_calculation_history.csv"
        meter_texts = [me.text() for me in self.main_tab_instance.meter_entries]
        diff_texts = [de.text() for de in self.main_tab_instance.diff_entries]
        if all(not text for text in meter_texts) and all(not text for text in diff_texts):
             QMessageBox.warning(self, "Empty Data", "Cannot save empty calculation data.")
             return
        try:
            file_exists = os.path.isfile(filename)
            with open(filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists or os.path.getsize(filename) == 0:
                    header = ["Month"] + [f"Meter-{i+1}" for i in range(10)] + \
                                [f"Diff-{i+1}" for i in range(10)] + \
                                ["Total Unit", "Total Diff", "Per Unit Cost", "Added Amount", "In Total"] + \
                                ["Room Name", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill",
                                 "Gas Bill", "Water Bill", "House Rent", "Grand Total",
                                 "Total House Rent", "Total Water Bill", "Total Gas Bill", "Total Room Unit Bill"]
                    writer.writerow(header)
                main_data_row = [month_name]
                for i in range(10): main_data_row.append(self.main_tab_instance.meter_entries[i].text() if i < len(self.main_tab_instance.meter_entries) and self.main_tab_instance.meter_entries[i].text() else "0")
                for i in range(10): main_data_row.append(self.main_tab_instance.diff_entries[i].text() if i < len(self.main_tab_instance.diff_entries) and self.main_tab_instance.diff_entries[i].text() else "0")
                main_data_row.extend([
                    (self.main_tab_instance.total_unit_value_label.text().split(':')[-1].replace("TK", "").strip() or "0"),
                    (self.main_tab_instance.total_diff_value_label.text().split(':')[-1].replace("TK", "").strip() or "0"),
                    (self.main_tab_instance.per_unit_cost_value_label.text().split(':')[-1].replace("TK", "").strip() or "0.00"),
                    str(self.main_tab_instance.get_additional_amount()),
                    (self.main_tab_instance.in_total_value_label.text().split(':')[-1].replace("TK", "").strip() or "0.00")
                ])
                if self.rooms_tab_instance.room_entries:
                    for i, room_data in enumerate(self.rooms_tab_instance.room_entries):
                        room_group_widget = self.rooms_tab_instance.rooms_scroll_layout.itemAtPosition(i // 3, i % 3).widget()
                        room_name = room_group_widget.title() if isinstance(room_group_widget, QGroupBox) else f"Room {i+1}"
                        
                        present_text = room_data['present_entry'].text() or "0"
                        previous_text = room_data['previous_entry'].text() or "0"
                        real_unit = room_data['real_unit_label'].text() if room_data['real_unit_label'].text() != "Incomplete" else "N/A"
                        unit_bill = room_data['unit_bill_label'].text().replace(" TK", "") if room_data['unit_bill_label'].text() != "Incomplete" else "N/A"
                        gas_bill = room_data['gas_bill_entry'].text() or "0.00"
                        water_bill = room_data['water_bill_entry'].text() or "0.00"
                        house_rent = room_data['house_rent_entry'].text() or "0.00"
                        grand_total = room_data['grand_total_label'].text().replace(" TK", "") if room_data['grand_total_label'].text() != "Incomplete" else "N/A"

                        room_csv_data_parts = [
                            room_name, present_text, previous_text, real_unit, unit_bill,
                            gas_bill, water_bill, house_rent, grand_total
                        ]
                        if i == 0:
                            # For the first room, append room data and then the summary totals
                            room_bill_totals = self.rooms_tab_instance.get_all_room_bill_totals()
                            summary_csv_parts = [
                                f"{room_bill_totals['total_house_rent']:.2f}",
                                f"{room_bill_totals['total_water_bill']:.2f}",
                                f"{room_bill_totals['total_gas_bill']:.2f}",
                                f"{room_bill_totals['total_room_unit_bill']:.2f}"
                            ]
                            writer.writerow(main_data_row + room_csv_data_parts + summary_csv_parts)
                        else:
                             writer.writerow([""] * len(main_data_row) + room_csv_data_parts + [""] * 4) # Empty cells for totals in subsequent room rows
                else:
                    writer.writerow(main_data_row + ["N/A"] * 9 + ["N/A"] * 4) # 9 new fields for rooms + 4 for totals
            QMessageBox.information(self, "Save Successful", f"Data saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save data to CSV: {e}\n{traceback.format_exc()}")

    def save_calculation_to_supabase(self):
        if not self.supabase_manager.is_client_initialized() or not self.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return
        try:
            month = self.main_tab_instance.month_combo.currentText()
            year = self.main_tab_instance.year_spinbox.value()

            def _s_float(v, default=0.0):
                try: return float(v) if v and v.strip() else default
                except ValueError: return default

            meter_values = [_s_float(me.text()) for me in self.main_tab_instance.meter_entries]
            diff_values = [_s_float(de.text()) for de in self.main_tab_instance.diff_entries]

            # Build dictionary with both indexed keys (meter_1, diff_1, ...) and array versions for backward compatibility
            main_calc_data = {
                "month": month,
                "year": year,
                "meter_readings": meter_values,
                "diff_readings": diff_values,
            }

            # Add individual meter_i and diff_i keys expected by HistoryTab
            for idx, val in enumerate(meter_values):
                main_calc_data[f"meter_{idx+1}"] = val
            for idx, val in enumerate(diff_values):
                main_calc_data[f"diff_{idx+1}"] = val

            # Additional summary fields using names expected by HistoryTab
            main_calc_data.update({
                "total_unit_cost": _s_float(self.main_tab_instance.total_unit_value_label.text().replace("TK", "").strip()),
                "total_diff_units": _s_float(self.main_tab_instance.total_diff_value_label.text().replace("TK", "").strip()),
                "per_unit_cost": _s_float(self.main_tab_instance.per_unit_cost_value_label.text().replace("TK", "").strip()),
                "added_amount": _s_float(self.main_tab_instance.additional_amount_input.text()),
                "grand_total": _s_float(self.main_tab_instance.in_total_value_label.text().replace("TK", "").strip()),
            })

            # Check for incomplete room calculations before saving
            incomplete_rooms = []
            room_data_for_supabase = []
            if self.rooms_tab_instance.room_entries:
                for i, room_data in enumerate(self.rooms_tab_instance.room_entries):
                    real_unit_label = room_data['real_unit_label']
                    unit_bill_label = room_data['unit_bill_label']
                    grand_total_label = room_data['grand_total_label']
                    room_group_widget = self.rooms_tab_instance.rooms_scroll_layout.itemAtPosition(i // 3, i % 3).widget()
                    room_name = room_group_widget.title() if isinstance(room_group_widget, QGroupBox) else f"Room {i+1}"
                    
                    if real_unit_label.text() == "Incomplete" or unit_bill_label.text() == "Incomplete" or grand_total_label.text() == "Incomplete":
                        incomplete_rooms.append(room_name)
                    else:
                        # Prepare room data for SupabaseManager, including local image paths
                        room_entry_data = {
                            "room_name": room_name,
                            "present_unit": _s_float(room_data['present_entry'].text()),
                            "previous_unit": _s_float(room_data['previous_entry'].text()),
                            "real_unit": _s_float(real_unit_label.text()),
                            "unit_bill": _s_float(unit_bill_label.text().replace(" TK", "").strip()),
                            "gas_bill": _s_float(room_data['gas_bill_entry'].text()),
                            "water_bill": _s_float(room_data['water_bill_entry'].text()),
                            "house_rent": _s_float(room_data['house_rent_entry'].text()),
                            "grand_total": _s_float(grand_total_label.text().replace(" TK", "").strip()),
                            # Include local image paths for SupabaseManager to handle upload
                            "photo_path": room_data.get('photo_path'), # Assuming these keys exist in room_data
                            "nid_front_path": room_data.get('nid_front_path'),
                            "nid_back_path": room_data.get('nid_back_path'),
                            "police_form_path": room_data.get('police_form_path')
                        }
                        room_data_for_supabase.append(room_entry_data)
                
                if incomplete_rooms:
                    reply = QMessageBox.question(self, "Incomplete Data",
                                               f"Some rooms have incomplete calculations: {', '.join(incomplete_rooms)}\n\n"
                                               f"Do you want to save anyway? (Incomplete rooms will be skipped)",
                                               QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.No:
                        return

            # Save main calculation using SupabaseManager
            main_calc_id = self.supabase_manager.save_main_calculation(main_calc_data)

            if main_calc_id:
                # Save room calculations using SupabaseManager
                if room_data_for_supabase:
                    rooms_saved = self.supabase_manager.save_room_calculations(main_calc_id, room_data_for_supabase)
                    if rooms_saved:
                        QMessageBox.information(self, "Success", "Calculation data and room info saved to Supabase successfully!")
                    else:
                        QMessageBox.critical(self, "Supabase Error", "Failed to save room calculation data to Supabase.")
                else:
                    QMessageBox.information(self, "Success", "Main calculation data saved to Supabase successfully (no room data).")
            else:
                QMessageBox.critical(self, "Supabase Error", "Failed to save main calculation data to Supabase.")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred while saving to Supabase: {e}\n{traceback.format_exc()}")
        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Supabase API Error: {e.message}\nDetails: {e.details}\nHint: {e.hint}")
            print(f"Supabase API Error: {e.message}\nDetails: {e.details}\nHint: {e.hint}\n{traceback.format_exc()}")
        except Exception as e:
            QMessageBox.critical(self, "Supabase Save Error", f"Failed to save data to Supabase: {e}\n{traceback.format_exc()}")

    def setup_navigation(self):
        # Connect tab change signal to a handler that sets focus
        self.tab_widget.currentChanged.connect(self.set_focus_on_tab_change)

        # Set initial focus based on the currently active tab
        self.set_focus_on_tab_change(self.tab_widget.currentIndex())

    def set_focus_on_tab_change(self, index):
        current_tab = self.tab_widget.widget(index)
        if isinstance(current_tab, MainTab):
            self.main_tab_instance.meter_entries[0].setFocus()
        elif isinstance(current_tab, RoomsTab):
            if self.rooms_tab_instance.room_entries:
                self.rooms_tab_instance.room_entries[0]['present_entry'].setFocus()
        elif isinstance(current_tab, HistoryTab):
            self.history_tab_instance.main_history_table.setFocus()
        elif isinstance(current_tab, SupabaseConfigTab):
            self.supabase_config_tab_instance.supabase_url_input.setFocus()
        elif isinstance(current_tab, RentalInfoTab):
            self.rental_info_tab_instance.rental_records_table.setFocus()
        elif isinstance(current_tab, ArchivedInfoTab):
            self.archived_info_tab_instance.archived_records_table.setFocus()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def refresh_all_rental_tabs(self):
        # This method will be called when rental info is updated
        # It should trigger a refresh in all tabs that display rental info
        # For now, it only refreshes the HistoryTab
        try:
            self.rental_info_tab_instance.load_rental_records()
            self.archived_info_tab_instance.load_archived_records()
        except Exception as e:
            logging.error(f"Error refreshing rental tabs: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Set application style for better aesthetics
    app.setStyle("Fusion") 
    ex = MeterCalculationApp()
    ex.show()
    sys.exit(app.exec_())
