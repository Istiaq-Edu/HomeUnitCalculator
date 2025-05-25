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
from rental_info_tab import RentalRecordDialog # Re-use the dialog

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
        # This will ensure the 'rentals' table exists and has 'is_archived' column
        # The actual table creation/alteration logic is in RentalInfoTab's setup_db_table
        # We just need to call it to make sure it's set up.
        try:
            # This is a bit of a hack, but ensures the table is set up if this tab is loaded first
            # A better approach might be a central DB setup function in DBManager or main app
            self.db_manager.create_table("""
                CREATE TABLE IF NOT EXISTS rentals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_name TEXT NOT NULL,
                    room_number TEXT NOT NULL,
                    advanced_paid REAL,
                    photo_path TEXT,
                    nid_front_path TEXT,
                    nid_back_path TEXT,
                    police_form_path TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    is_archived INTEGER DEFAULT 0
                )
            """)
            # Add is_archived column if it doesn't exist (for backward compatibility)
            self.db_manager.execute_query("""
                PRAGMA table_info(rentals);
            """)
            columns = self.db_manager.cursor.fetchall()
            column_names = [col[1] for col in columns]
            if 'is_archived' not in column_names:
                self.db_manager.execute_query("""
                    ALTER TABLE rentals ADD COLUMN is_archived INTEGER DEFAULT 0;
                """)
                print("Added 'is_archived' column to rentals table from ArchivedInfoTab.")
            print("Rentals table ensured from ArchivedInfoTab.")
        except Exception as e:
            print(f"Database Error: Failed to ensure rentals table from ArchivedInfoTab: {e}\n{traceback.format_exc()}")
            # QMessageBox.critical(self, "Database Error", f"Failed to ensure rentals table from ArchivedInfoTab: {e}")
            # traceback.print_exc()

    def load_archived_records(self):
        try:
            # Select only records where is_archived is 1
            records = self.db_manager.execute_query("SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived FROM rentals WHERE is_archived = 1 ORDER BY updated_at DESC", fetch_all=True)
            self.archived_records_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                for col_idx, data in enumerate(record[:6]): # Display first 6 columns in table
                    item = QTableWidgetItem(str(data))
                    self.archived_records_table.setItem(row_idx, col_idx, item)
                # Store full paths in item data for later retrieval
                self.archived_records_table.item(row_idx, 0).setData(Qt.UserRole, record) # Store full record in ID item
        except Exception as e:
            print(f"Database Error: Failed to load archived rental records: {e}\n{traceback.format_exc()}")
            # QMessageBox.critical(self, "Database Error", f"Failed to load archived rental records: {e}")
            # traceback.print_exc()

    def show_record_details_dialog(self, index):
        selected_row = index.row()
        record = self.archived_records_table.item(selected_row, 0).data(Qt.UserRole)
        
        if record:
            # Pass is_archived status to the dialog
            is_archived = record[10] if len(record) > 10 else False
            # Pass the main_window_ref to the dialog so it can access generate_rental_pdf_from_data
            dialog = RentalRecordDialog(self, record_data=record, db_manager=self.db_manager, is_archived_record=bool(is_archived), main_window_ref=self.main_window)
            dialog.exec_() # Show as modal dialog