import sys
import traceback
import os
from datetime import datetime
import logging

from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QFormLayout, QMessageBox, QSizePolicy, QDialog,
    QFileDialog, QTableWidgetItem, QHeaderView, QAbstractItemView, QProgressDialog
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, BaseDocTemplate, PageTemplate, Frame, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from qfluentwidgets import (
    CardWidget, ComboBox, TableWidget, TitleLabel
)

from src.ui.dialogs import RentalRecordDialog # Move to shared dialogs module
from src.ui.background_workers import FetchSupabaseRentalRecordsWorker
from src.ui.custom_widgets import FluentProgressDialog  # Avoid top-level import to keep optional
# >>> ADD
# Optional Fluent-widgets progress bar (inline)
try:
    from qfluentwidgets import IndeterminateProgressBar  # type: ignore
except ImportError:
    IndeterminateProgressBar = None  # type: ignore
# <<< ADD

class ArchivedInfoTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = self.main_window.db_manager

        self.archived_records_table = None
        # >>> ADD
        self._inline_progress_bar = None  # For inline cloud-fetch indicator
        # <<< ADD

        self.init_ui()
        self.setup_db_table() # Ensure rentals table exists and has is_archived column
        self.load_archived_records()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        table_group = CardWidget()
        outer_table_layout = QVBoxLayout(table_group)
        outer_table_layout.setSpacing(8)
        outer_table_layout.setContentsMargins(12, 12, 12, 12)
        outer_table_layout.addWidget(TitleLabel("Archived Rental Records"))
        table_layout = QVBoxLayout()
        outer_table_layout.addLayout(table_layout)
        # >>> ADD
        self.table_layout = table_layout  # expose to insert/remove progress bar
        # <<< ADD

        # Add Load Source Combo Box
        self.load_source_combo = ComboBox()
        self.load_source_combo.addItems(["Local DB", "Cloud (Supabase)"])
        self.load_source_combo.currentIndexChanged.connect(self.load_archived_records)
        table_layout.addWidget(self.load_source_combo)

        self.archived_records_table = TableWidget()
        self.archived_records_table.setColumnCount(6) # ID, Name, Room, Advanced, Created, Updated
        self.archived_records_table.setHorizontalHeaderLabels(["ID", "Tenant Name", "Room Number", "Advanced Paid", "Created At", "Updated At"])
        self.archived_records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.archived_records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archived_records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
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
        # Reset table first
        self.archived_records_table.clearContents()
        self.archived_records_table.setRowCount(0)

        selected_source = self.load_source_combo.currentText()

        if selected_source == "Local DB":
            # --- synchronous local path ---
            try:
                query = (
                    "SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at, "
                    "photo_path, nid_front_path, nid_back_path, police_form_path, is_archived, supabase_id "
                    "FROM rentals WHERE is_archived = ? ORDER BY updated_at DESC"
                )
                records = self.db_manager.execute_query(query, (1,))
                logging.info(f"Loaded {len(records)} archived records from Local DB.")
                self._populate_archived_table(selected_source, records)
            except Exception as e:
                logging.error(
                    f"Database Error: Failed to load archived rental records from local DB: {e}", exc_info=True
                )
                QMessageBox.critical(self, "Local DB Error", f"Failed to load archived rental records from local DB: {e}")
            return

        # ---------- Cloud (Supabase) path using background worker ----------
        if not self.main_window.supabase_manager.is_client_initialized():
            QMessageBox.warning(
                self, "Supabase Not Configured", "Supabase client is not initialized. Cannot load from cloud."
            )
            return

        # ---------- Inline Fluent progress bar ----------
        if IndeterminateProgressBar is not None and self._inline_progress_bar is None:
            self._inline_progress_bar = IndeterminateProgressBar(parent=self)
            self._inline_progress_bar.setFixedHeight(4)
            self._inline_progress_bar.start()
            # Insert just below the source combo (index 1)
            self.table_layout.insertWidget(1, self._inline_progress_bar)

        self.load_source_combo.setEnabled(False)

        self._fetch_worker = FetchSupabaseRentalRecordsWorker(
            self.main_window.supabase_manager, is_archived=True, parent=self
        )
        self._fetch_worker.records_fetched.connect(
            lambda recs: self._on_archived_cloud_ready(recs, selected_source)
        )
        self._fetch_worker.error_occurred.connect(self._on_archived_cloud_error)
        self._fetch_worker.finished.connect(self._on_archived_cloud_finished)
        self._fetch_worker.start()

    # ---------------- Worker callbacks and helpers ----------------

    def _on_archived_cloud_ready(self, records, source):
        if not records:
            # Message already displayed by caller (load_archived_records or worker callback)
            return
        self._populate_archived_table(source, records)

    def _on_archived_cloud_error(self, message: str):
        QMessageBox.critical(self, "Cloud DB Error", f"Failed to load archived rental records from Supabase: {message}")
        # >>> ADD
        # Clean up the progress bar on error
        if self._inline_progress_bar is not None:
            self._inline_progress_bar.stop()
            self.table_layout.removeWidget(self._inline_progress_bar)
            self._inline_progress_bar.deleteLater()
            self._inline_progress_bar = None
        # <<< ADD

    def _on_archived_cloud_finished(self):
        self.load_source_combo.setEnabled(True)
        # >>> MODIFY
        if self._inline_progress_bar is not None:
            self._inline_progress_bar.stop()
            self.table_layout.removeWidget(self._inline_progress_bar)
            self._inline_progress_bar.deleteLater()
            self._inline_progress_bar = None
        # <<< MODIFY

    def _populate_archived_table(self, source_label: str, records: list):
        if not records:
            # Message already displayed by caller (load_archived_records or worker callback)
            return

        self.archived_records_table.setRowCount(len(records))

        for row_idx, record in enumerate(records):
            if source_label == "Local DB":
                display_id, tenant_name, room_number, advanced_paid, created_at, updated_at = (
                    record[0], record[1], record[2], record[3], record[4], record[5]
                )
                full_record_data = record
            else:
                display_id = record.get("id")
                tenant_name = record.get("tenant_name")
                room_number = record.get("room_number")
                advanced_paid = record.get("advanced_paid")
                created_at = record.get("created_at")
                updated_at = record.get("updated_at")
                full_record_data = record

            self.archived_records_table.setItem(row_idx, 0, QTableWidgetItem(str(display_id)))
            self.archived_records_table.setItem(row_idx, 1, QTableWidgetItem(str(tenant_name)))
            self.archived_records_table.setItem(row_idx, 2, QTableWidgetItem(str(room_number)))
            self.archived_records_table.setItem(row_idx, 3, QTableWidgetItem(str(advanced_paid)))
            self.archived_records_table.setItem(row_idx, 4, QTableWidgetItem(str(created_at)))
            self.archived_records_table.setItem(row_idx, 5, QTableWidgetItem(str(updated_at)))

            self.archived_records_table.item(row_idx, 0).setData(Qt.UserRole, full_record_data)

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
            
        record_data = item.data(Qt.UserRole)
        if not record_data:
            logging.warning(f"No record data found for row {selected_row}")
            return
        
        selected_source = self.load_source_combo.currentText()

        # Adapt record_data to a consistent format for the dialog
        if selected_source == "Local DB":
            # SQLite record: (id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived, supabase_id)
            # Convert to dict for consistency with Supabase records in dialog
            record_dict = {
                "id": record_data[0],
                "tenant_name": record_data[1],
                "room_number": record_data[2],
                "advanced_paid": record_data[3],
                "created_at": record_data[4],
                "updated_at": record_data[5],
                "photo_path": record_data[6],
                "nid_front_path": record_data[7],
                "nid_back_path": record_data[8],
                "police_form_path": record_data[9],
                "is_archived": bool(record_data[10]),
                "supabase_id": record_data[11]
            }
        else: # Cloud (Supabase) - already a flattened dict
            record_dict = record_data
            # Ensure local paths are empty strings if not present, as dialog expects paths
            record_dict["photo_path"] = record_dict.get("photo_url", "")
            record_dict["nid_front_path"] = record_dict.get("nid_front_url", "")
            record_dict["nid_back_path"] = record_dict.get("nid_back_url", "")
            record_dict["police_form_path"] = record_dict.get("police_form_url", "")

        try:
            dialog = RentalRecordDialog(
                self,
                record_data=record_dict, # Pass the consistent dictionary
                db_manager=self.db_manager, # Local DB manager
                supabase_manager=self.main_window.supabase_manager, # Supabase manager
                is_archived_record=record_dict.get("is_archived", False),
                main_window_ref=self.main_window,
                current_source=selected_source # Pass the current source to the dialog
            )
            dialog.exec_() # Show as modal dialog
        except Exception as e:
            logging.error(f"Failed to open record details dialog: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", "Unable to open record details. Please try again.")