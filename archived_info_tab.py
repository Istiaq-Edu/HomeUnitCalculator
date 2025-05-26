import sys
import traceback
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QGroupBox, QFormLayout, QMessageBox, QSizePolicy, QDialog,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, BaseDocTemplate, PageTemplate, Frame, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from styles import (
    get_room_selection_style, get_room_group_style, get_line_edit_style,
    get_button_style, get_table_style, get_label_style
)
from utils import resource_path, _clear_layout
from custom_widgets import CustomLineEdit, AutoScrollArea, CustomNavButton
from dialogs import RentalRecordDialog # Move to shared dialogs module

class ArchivedInfoTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = self.main_window.db_manager

        self.archived_records_table = None

        self.init_ui()
        self.setup_db_table() # Ensure rentals table exists and has is_archived column
        self.load_archived_records()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        table_group = QGroupBox("Archived Rental Records")
        table_group.setStyleSheet(get_room_selection_style())
        table_layout = QVBoxLayout(table_group)

        self.archived_records_table = QTableWidget()
        self.archived_records_table.setColumnCount(6) # ID, Name, Room, Advanced, Created, Updated
        self.archived_records_table.setHorizontalHeaderLabels(["ID", "Tenant Name", "Room Number", "Advanced Paid", "Created At", "Updated At"])
        self.archived_records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archived_records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archived_records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.archived_records_table.setStyleSheet(get_table_style())
        self.archived_records_table.clicked.connect(self.show_record_details_dialog)
        table_layout.addWidget(self.archived_records_table)
        
        main_layout.addWidget(table_group)
        self.setLayout(main_layout)

    def setup_db_table(self):
        # Ensure the 'rentals' table exists and has all necessary columns
        try:
            self.db_manager.bootstrap_rentals_table()
        except Exception as e:
            print(f"Database Error: Failed to ensure rentals table from ArchivedInfoTab: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Database Warning", "Unable to initialize database table. Some features may not work correctly.")

    def load_archived_records(self):
        try:
            # Reset table to pristine state
            self.archived_records_table.clearContents()
            self.archived_records_table.setRowCount(0)
            # Select only records where is_archived is 1
            records = self.db_manager.execute_query("SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived FROM rentals WHERE is_archived = ? ORDER BY updated_at DESC", (1,), fetch_all=True)
            if not records:
                return          # nothing to show or DB error already warned

            self.archived_records_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                for col_idx, data in enumerate(record[:6]): # Display first 6 columns in table
                    item = QTableWidgetItem(str(data))
                    self.archived_records_table.setItem(row_idx, col_idx, item)
                # Store full paths in item data for later retrieval
                self.archived_records_table.item(row_idx, 0).setData(Qt.UserRole, record) # Store full record in ID item
        except Exception as e:
            print(f"Database Error: Failed to load archived rental records: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Load Error", "Unable to load archived records. Please check the database connection.")

    def show_record_details_dialog(self, index):
        selected_row = index.row()
        item = self.archived_records_table.item(selected_row, 0)
        if not item:
            return  # click on an empty area
        record = item.data(Qt.UserRole)
        if not record:
            return
        
        if record:
            # Pass is_archived status to the dialog
            is_archived = record[10] if len(record) > 10 else False
            # Pass the main_window_ref to the dialog so it can access generate_rental_pdf_from_data
            dialog = RentalRecordDialog(self, record_data=record, db_manager=self.db_manager, is_archived_record=bool(is_archived), main_window_ref=self.main_window)
            dialog.exec_() # Show as modal dialog