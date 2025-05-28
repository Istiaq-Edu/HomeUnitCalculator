import sys
import traceback
import os
from datetime import datetime
import logging

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

from src.ui.styles import (
    get_room_selection_style, get_table_style
)
from src.ui.dialogs import RentalRecordDialog # Move to shared dialogs module

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
            logging.error(f"Database Error: Failed to ensure rentals table from ArchivedInfoTab: {e}", exc_info=True)
            QMessageBox.warning(self, "Database Warning", "Unable to initialize database table. Some features may not work correctly.")

    def load_archived_records(self):
        try:
            # Reset table to pristine state
            self.archived_records_table.clearContents()
            self.archived_records_table.setRowCount(0)
            # Select only records where is_archived is 1
            query = """
                SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at,
                       photo_path, nid_front_path, nid_back_path, police_form_path, is_archived
                FROM rentals
                WHERE is_archived = ?
                ORDER BY updated_at DESC
            """
            records = self.db_manager.execute_query(query, (1,), fetch_all=True)
            
            if not records:
                logging.info("No archived records found")
                return          # nothing to show or DB error already warned

            self.archived_records_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                for col_idx, data in enumerate(record[:6]): # Display first 6 columns in table
                    # Handle None values appropriately
                    display_data = str(data) if data is not None else ""
                    item = QTableWidgetItem(display_data)
                    self.archived_records_table.setItem(row_idx, col_idx, item)
                # Store full paths in item data for later retrieval
                self.archived_records_table.item(row_idx, 0).setData(Qt.UserRole, record) # Store full record in ID item
        except Exception as e:
            logging.error(f"Database Error: Failed to load archived rental records: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Error", "Unable to load archived records. Please check the database connection.")

    def show_record_details_dialog(self, index):
        if not index.isValid():
            return
            
        selected_row = index.row()
        if selected_row < 0 or selected_row >= self.archived_records_table.rowCount():
            return
            
        item = self.archived_records_table.item(selected_row, 0)
        if not item:
            logging.warning(f"No item found at row {selected_row}")
            return
            
        record = item.data(Qt.UserRole)
        if not record:
            logging.warning(f"No record data found for row {selected_row}")
            return
        
        try:
            # Pass is_archived status to the dialog (is_archived is at index 10)
            # Cast explicitly to int so that "0" and 0 are both handled correctly
            is_archived = bool(int(record[10])) if len(record) > 10 else False
            
            # Pass the main_window_ref to the dialog so it can access generate_rental_pdf_from_data
            dialog = RentalRecordDialog(
                self,
                record_data=record,
                db_manager=self.db_manager,
                is_archived_record=is_archived,
                main_window_ref=self.main_window
            )
            dialog.exec_() # Show as modal dialog
        except Exception as e:
            logging.error(f"Failed to open record details dialog: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Unable to open record details. Please try again.")