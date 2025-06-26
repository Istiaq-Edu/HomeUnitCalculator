import sys
import traceback
import os
import io # Import the io module for in-memory binary streams
from datetime import datetime
from pathlib import Path # Import Path from pathlib
import shutil # Import shutil for file operations
import uuid # Import uuid for generating unique filenames
import urllib.parse
import re

# Suppress SSL certificate warnings when verify=False is used in requests
try:
    import urllib3
except ModuleNotFoundError:
    import requests.packages.urllib3 as urllib3  # type: ignore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from PyQt5.QtCore import Qt, QRegExp, QEvent
from PyQt5.QtGui import QIcon, QRegExpValidator, QPixmap # Keep QPixmap for _validate_image_file
from reportlab.lib.utils import ImageReader # Added ImageReader
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QGroupBox, QFormLayout, QMessageBox, QSizePolicy, QDialog,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QCheckBox, QProgressDialog
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image, PageBreak, NextPageTemplate, BaseDocTemplate, PageTemplate, Frame, FrameBreak # Re-import FrameBreak
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

from src.ui.styles import (
    get_room_selection_style, get_room_group_style, get_line_edit_style,
    get_button_style, get_table_style, get_label_style, get_source_combo_style,
    get_checkbox_style
)
from src.core.utils import resource_path, _clear_layout
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomNavButton, FluentProgressDialog
from src.ui.dialogs import RentalRecordDialog
from src.ui.background_workers import FetchSupabaseRentalRecordsWorker
# >>> ADD
# Fluent-widgets progress bar
try:
    from qfluentwidgets import IndeterminateProgressBar  # type: ignore
except ImportError:
    IndeterminateProgressBar = None  # type: ignore
# <<< ADD


class RentalInfoTab(QWidget):
    # Define safe and forbidden directories at the class level
    SAFE_DIRS = [Path.cwd()] + [Path.home() / d for d in ("Documents", "Desktop", "Downloads")]
    FORBIDDEN = [
        Path(p) for p in (
            "/etc", "/sys", "/proc", "/bin", "/usr",
            "C:/Windows", "C:/Windows/System32"
        )
    ]
    # Define the directory where images will be stored within the application's data folder
    IMAGE_STORAGE_DIR = Path.cwd() / "data" / "images"

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = self.main_window.db_manager
        # >>> ADD
        # Ensure the image storage directory exists right at start-up so that
        # subsequent save operations don't fail due to a missing folder.
        try:
            self.IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as dir_e:
            print(f"Warning: could not create image storage dir: {dir_e}")
        # Inline progress bar reference (for cloud fetch)
        self._inline_progress_bar = None
        # <<< ADD

        self.tenant_name_input = None
        self.room_number_input = None
        self.advanced_paid_input = None
        self.photo_path_label = None
        self.nid_front_path_label = None
        self.nid_back_path_label = None
        self.police_form_path_label = None
        self.rental_records_table = None

        self.current_rental_id = None  # Local DB primary key (if editing an existing record)
        self.current_supabase_id = None  # Supabase record UUID (if editing an existing record)
        self.current_is_archived = False  # Preserve archive status when editing

        self.init_ui()
        self.setup_db_table()
        self.load_rental_records() # Initial load will be from default source

    def init_ui(self):
        main_horizontal_layout = QHBoxLayout(self)
        main_horizontal_layout.setContentsMargins(10, 10, 10, 10)
        main_horizontal_layout.setSpacing(15)

        # Left Column Layout (Input Form + Image Uploads + Save/Clear)
        left_column_layout = QVBoxLayout()
        left_column_layout.setSpacing(15)

        # Input Form Group
        input_group = QGroupBox("Rental Details")
        input_group.setStyleSheet(get_room_selection_style())
        input_form_layout = QFormLayout(input_group)
        input_form_layout.setContentsMargins(20, 20, 20, 20)
        input_form_layout.setSpacing(10)

        self.tenant_name_input = CustomLineEdit()
        self.tenant_name_input.setPlaceholderText("Enter tenant's full name")
        self.tenant_name_input.setStyleSheet(get_line_edit_style())
        # No validator for tenant name, as it can contain any characters
        input_form_layout.addRow("Tenant Name:", self.tenant_name_input)

        self.room_number_input = CustomLineEdit()
        self.room_number_input.setPlaceholderText("e.g., A-101, Room 5")
        self.room_number_input.setStyleSheet(get_line_edit_style())
        # No validator for room number, as it can be free-form text
        input_form_layout.addRow("Room Number:", self.room_number_input)

        self.advanced_paid_input = CustomLineEdit()
        self.advanced_paid_input.setPlaceholderText("Enter advanced payment amount")
        self.advanced_paid_input.setStyleSheet(get_line_edit_style())
        numeric_validator = QRegExpValidator(QRegExp(r'^\d*\.?\d*$')) # Allow float
        self.advanced_paid_input.setValidator(numeric_validator)
        input_form_layout.addRow("Advanced Paid (TK):", self.advanced_paid_input)

        left_column_layout.addWidget(input_group)

        # Store input fields for keyboard navigation
        self.input_fields = [
            self.tenant_name_input,
            self.room_number_input,
            self.advanced_paid_input
        ]

        # ─── Configure CustomLineEdit navigation (Enter / Up / Down) ───
        for idx, fld in enumerate(self.input_fields):
            next_fld = self.input_fields[(idx + 1) % len(self.input_fields)]
            prev_fld = self.input_fields[(idx - 1) % len(self.input_fields)]

            fld.next_widget_on_enter = next_fld   # Enter → next
            fld.down_widget = next_fld            # ↓ → next
            fld.up_widget = prev_fld              # ↑ → previous

        # Give initial focus to the first field when the tab opens
        self.tenant_name_input.setFocus()

        # Image Uploads Group
        image_upload_group = QGroupBox("Document Upload")
        image_upload_group.setStyleSheet(get_room_selection_style())
        image_upload_layout = QGridLayout(image_upload_group)
        image_upload_layout.setContentsMargins(20, 20, 20, 20)
        image_upload_layout.setSpacing(10)

        # Photo
        self.photo_path_label = QLineEdit("No file selected")
        self.photo_path_label.setReadOnly(True)
        self.photo_path_label.setStyleSheet(get_label_style())
        upload_photo_btn = QPushButton("Photo")
        upload_photo_btn.setStyleSheet(get_button_style())
        upload_photo_btn.clicked.connect(lambda: self.upload_image("photo"))
        image_upload_layout.addWidget(self.photo_path_label, 0, 0)
        image_upload_layout.addWidget(upload_photo_btn, 0, 1)

        # NID Front
        self.nid_front_path_label = QLineEdit("No file selected")
        self.nid_front_path_label.setReadOnly(True)
        self.nid_front_path_label.setStyleSheet(get_label_style())
        upload_nid_front_btn = QPushButton("NID Front")
        upload_nid_front_btn.setStyleSheet(get_button_style())
        upload_nid_front_btn.clicked.connect(lambda: self.upload_image("nid_front"))
        image_upload_layout.addWidget(self.nid_front_path_label, 1, 0)
        image_upload_layout.addWidget(upload_nid_front_btn, 1, 1)

        # NID Back
        self.nid_back_path_label = QLineEdit("No file selected")
        self.nid_back_path_label.setReadOnly(True)
        self.nid_back_path_label.setStyleSheet(get_label_style())
        upload_nid_back_btn = QPushButton("NID Back")
        upload_nid_back_btn.setStyleSheet(get_button_style())
        upload_nid_back_btn.clicked.connect(lambda: self.upload_image("nid_back"))
        image_upload_layout.addWidget(self.nid_back_path_label, 2, 0)
        image_upload_layout.addWidget(upload_nid_back_btn, 2, 1)

        # Police Form
        self.police_form_path_label = QLineEdit("No file selected")
        self.police_form_path_label.setReadOnly(True)
        self.police_form_path_label.setStyleSheet(get_label_style())
        upload_police_form_btn = QPushButton("Police Form")
        upload_police_form_btn.setStyleSheet(get_button_style())
        upload_police_form_btn.clicked.connect(lambda: self.upload_image("police_form"))
        image_upload_layout.addWidget(self.police_form_path_label, 3, 0)
        image_upload_layout.addWidget(upload_police_form_btn, 3, 1)

        left_column_layout.addWidget(image_upload_group)

        # Save Options Group
        save_options_group = QGroupBox("Save Options")
        save_options_group.setStyleSheet(get_room_selection_style())
        save_options_layout = QHBoxLayout(save_options_group)
        save_options_layout.setContentsMargins(10, 10, 10, 10)
        save_options_layout.setSpacing(20)
        save_options_layout.setAlignment(Qt.AlignCenter)

        self.save_to_pc_checkbox = QCheckBox("Save to PC")
        self.save_to_pc_checkbox.setChecked(True)
        self.save_to_pc_checkbox.setStyleSheet(get_checkbox_style())
        self.save_to_pc_checkbox.setIcon(QIcon(resource_path("icons/database_icon.png")))
        self.save_to_pc_checkbox.setIconSize(self.save_to_pc_checkbox.sizeHint() / 2)
        save_options_layout.addWidget(self.save_to_pc_checkbox)

        self.save_to_cloud_checkbox = QCheckBox("Save to Cloud")
        self.save_to_cloud_checkbox.setChecked(True)
        self.save_to_cloud_checkbox.setStyleSheet(get_checkbox_style())
        self.save_to_cloud_checkbox.setIcon(QIcon(resource_path("icons/calculate_icon.png")))
        self.save_to_cloud_checkbox.setIconSize(self.save_to_cloud_checkbox.sizeHint() / 2)
        save_options_layout.addWidget(self.save_to_cloud_checkbox)

        left_column_layout.addWidget(save_options_group)

        # Action Buttons Layout
        action_buttons_layout = QHBoxLayout()
        
        # Save Record Button
        self.save_record_btn = CustomNavButton("Save Record")
        self.save_record_btn.setStyleSheet(get_button_style())
        self.save_record_btn.clicked.connect(self.save_rental_record)
        action_buttons_layout.addWidget(self.save_record_btn)

        # Clear Form Button
        self.clear_form_btn = QPushButton("Clear Form")
        clear_button_style = get_button_style().replace("#059669", "#6c757d").replace("#047857", "#5a6268") # Gray color
        self.clear_form_btn.setStyleSheet(clear_button_style)
        self.clear_form_btn.clicked.connect(self.clear_form)
        action_buttons_layout.addWidget(self.clear_form_btn)
        
        left_column_layout.addLayout(action_buttons_layout)
        
        main_horizontal_layout.addLayout(left_column_layout)

        # Right Column Layout (Rental Records Table)
        right_column_layout = QVBoxLayout()
        right_column_layout.setSpacing(15)

        table_group = QGroupBox("Existing Rental Records")
        table_group.setStyleSheet(get_room_selection_style())
        table_layout = QVBoxLayout(table_group)
        # >>> ADD
        # Expose the layout so we can insert/remove the progress bar later
        self.table_layout = table_layout
        # <<< ADD

        # Add Load Source Combo Box
        self.load_source_combo = QComboBox()
        self.load_source_combo.addItems(["Local DB", "Cloud (Supabase)"])
        self.load_source_combo.setStyleSheet(get_source_combo_style()) # Re-using button style for now
        self.load_source_combo.currentIndexChanged.connect(self.load_rental_records)
        table_layout.addWidget(self.load_source_combo)

        self.rental_records_table = QTableWidget()
        self.rental_records_table.setColumnCount(6) # ID, Name, Room, Advanced, Created, Updated
        self.rental_records_table.setHorizontalHeaderLabels(["ID", "Tenant Name", "Room Number", "Advanced Paid", "Created At", "Updated At"])
        self.rental_records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.rental_records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rental_records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rental_records_table.setStyleSheet(get_table_style())
        self.rental_records_table.clicked.connect(self.show_record_details_dialog)
        table_layout.addWidget(self.rental_records_table)
        
        right_column_layout.addWidget(table_group)
        main_horizontal_layout.addLayout(right_column_layout)

        self.setLayout(main_horizontal_layout)

    def setup_db_table(self):
        try:
            self.db_manager.bootstrap_rentals_table()
        except Exception as e:
            print(f"Database Error: Failed to create rentals table: {e}\n{traceback.format_exc()}")
            # QMessageBox.critical(self, "Database Error", f"Failed to create rentals table: {e}")
            # traceback.print_exc()

    def upload_image(self, image_type):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, f"Select {image_type.replace('_', ' ').title()} Image", "",
                                                   "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*)", options=options)
        if file_path:
            # Check that the chosen path is allowed and that the file is an image
            if not self._is_safe_path(file_path):
                QMessageBox.warning(self, "Forbidden Path", "The selected location is not permitted.")
                return
            if not self._validate_image_file(file_path):
                QMessageBox.warning(self, "Invalid File", "The selected file is not a valid image.")
                return

            # Ensure the image storage directory exists
            self.IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

            try:
                # Generate a unique filename to avoid collisions
                original_filename = Path(file_path).name
                file_extension = Path(file_path).suffix
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                destination_path = self.IMAGE_STORAGE_DIR / unique_filename

                # Copy the file to the application's image storage directory
                shutil.copy2(file_path, destination_path)
                
                # Update the label with the new internal path
                if image_type == "photo":
                    self.photo_path_label.setText(str(destination_path))
                elif image_type == "nid_front":
                    self.nid_front_path_label.setText(str(destination_path))
                elif image_type == "nid_back":
                    self.nid_back_path_label.setText(str(destination_path))
                elif image_type == "police_form":
                    self.police_form_path_label.setText(str(destination_path))
                
                QMessageBox.information(self, "Image Uploaded", f"Image copied to application data: {destination_path.name}")

            except Exception as e:
                QMessageBox.critical(self, "File Copy Error", f"Failed to copy image: {e}\n{traceback.format_exc()}")
                # Reset label if copy fails
                if image_type == "photo":
                    self.photo_path_label.setText("No file selected")
                elif image_type == "nid_front":
                    self.nid_front_path_label.setText("No file selected")
                elif image_type == "nid_back":
                    self.nid_back_path_label.setText("No file selected")
                elif image_type == "police_form":
                    self.police_form_path_label.setText("No file selected")

    def save_rental_record(self):
        tenant_name = self.tenant_name_input.text().strip()
        room_number = self.room_number_input.text().strip()
        advanced_paid_str = self.advanced_paid_input.text().strip()
        
        photo_path = self.photo_path_label.text()
        nid_front_path = self.nid_front_path_label.text()
        nid_back_path = self.nid_back_path_label.text()
        police_form_path = self.police_form_path_label.text()

        save_to_pc = self.save_to_pc_checkbox.isChecked()
        save_to_cloud = self.save_to_cloud_checkbox.isChecked()

        if not tenant_name or not room_number:
            QMessageBox.warning(self, "Input Error", "Tenant Name and Room Number cannot be empty.")
            return

        if not save_to_pc and not save_to_cloud:
            QMessageBox.warning(self, "Save Option Error", "Please select at least one destination to save the record (PC or Cloud).")
            return
            
        advanced_paid = float(advanced_paid_str) if advanced_paid_str else 0.0
        
        record_data = {
            "id": self.current_rental_id,
            "supabase_id": self.current_supabase_id,
            "tenant_name": tenant_name,
            "room_number": room_number,
            "advanced_paid": advanced_paid,
            "photo_path": photo_path if photo_path != "No file selected" else None,
            "nid_front_path": nid_front_path if nid_front_path != "No file selected" else None,
            "nid_back_path": nid_back_path if nid_back_path != "No file selected" else None,
            "police_form_path": police_form_path if police_form_path != "No file selected" else None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_archived": 1 if self.current_is_archived else 0
        }
        
        local_save_success = True
        cloud_save_success = True
        
        if save_to_pc:
            try:
                if self.current_rental_id:
                    # Use execute_query for the update
                    update_query = """
                        UPDATE rentals SET
                            tenant_name = :tenant_name, room_number = :room_number,
                            advanced_paid = :advanced_paid, photo_path = :photo_path,
                            nid_front_path = :nid_front_path, nid_back_path = :nid_back_path,
                            police_form_path = :police_form_path, updated_at = :updated_at,
                            is_archived = :is_archived
                        WHERE id = :id
                    """
                    self.db_manager.execute_query(update_query, record_data)

                    # If the update did not affect any row (e.g. the record was loaded from
                    # Supabase and doesn't yet exist locally), fall back to an insert.
                    if self.db_manager.cursor.rowcount == 0:
                        try:
                            new_id = self.db_manager.insert_rental_record(record_data)
                            self.current_rental_id = new_id
                        except Exception as ins_e:
                            print(f"Local insert fallback failed: {ins_e}")
                            local_save_success = False
                else:
                    self.db_manager.insert_rental_record(record_data)
                print("Record saved to local DB successfully.")
            except Exception as e:
                local_save_success = False
                QMessageBox.critical(self, "Local DB Error", f"Failed to save record to local DB: {e}\n{traceback.format_exc()}")
        
        if save_to_cloud:
            if self.main_window.supabase_manager.is_client_initialized():
                try:
                    image_paths = {
                        "photo": record_data.get("photo_path"),
                        "nid_front": record_data.get("nid_front_path"),
                        "nid_back": record_data.get("nid_back_path"),
                        "police_form": record_data.get("police_form_path"),
                    }
                    # SupabaseManager's save_rental_record handles both insert and update
                    result = self.main_window.supabase_manager.save_rental_record(record_data, image_paths)
                    
                    # Ensure result is a string before checking its content
                    if isinstance(result, str) and "Successfully" in result:
                        print("Record saved to Supabase successfully.")
                    else:
                        cloud_save_success = False
                        QMessageBox.critical(self, "Supabase Error", f"Failed to save record to Supabase: {result}")

                except Exception as e:
                    cloud_save_success = False
                    QMessageBox.critical(self, "Supabase Error", f"Failed to save record to Supabase: {e}\n{traceback.format_exc()}")
            else:
                cloud_save_success = False
                QMessageBox.warning(self, "Supabase Error", "Supabase client not initialized. Cannot save to cloud.")
        
        if local_save_success and cloud_save_success:
            QMessageBox.information(self, "Success", "Rental record saved successfully.")
            self.clear_form()

            # If user chose to save only locally, ensure we refresh from Local DB to prevent an unnecessary
            # cloud fetch that might hang if network connectivity is poor.
            if save_to_pc and not save_to_cloud:
                # Temporarily block signals to avoid double invocation of load_rental_records()
                self.load_source_combo.blockSignals(True)
                self.load_source_combo.setCurrentText("Local DB")
                self.load_source_combo.blockSignals(False)

            self.load_rental_records()  # Refresh the table with the currently selected source
            self.main_window.refresh_all_rental_tabs()
        else:
            QMessageBox.warning(self, "Partial Success", "Record may not have been saved to all selected locations.")

    def load_rental_records(self):
        # Clear current table contents first
        self.rental_records_table.clearContents()
        self.rental_records_table.setRowCount(0)

        selected_source = self.load_source_combo.currentText()

        if selected_source == "Local DB":
            # --- synchronous path (unchanged) ---
            try:
                records = self.db_manager.execute_query(
                    "SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived, supabase_id "
                    "FROM rentals WHERE is_archived = 0 ORDER BY created_at DESC"
                )
                print(f"Loaded {len(records)} records from Local DB.")
                self._populate_rental_table(selected_source, records)
            except Exception as e:
                QMessageBox.critical(self, "Local DB Error", f"Failed to load rental records from local DB: {e}")
                traceback.print_exc()
            return

        # ---------- Cloud (Supabase) using background thread ----------
        if not self.main_window.supabase_manager.is_client_initialized():
            QMessageBox.warning(
                self, "Supabase Not Configured", "Supabase client is not initialized. Cannot load from cloud."
            )
            return

        # ---------- Inline Fluent progress bar ----------
        # >>> ADD BLOCK
        if IndeterminateProgressBar is not None and self._inline_progress_bar is None:
            self._inline_progress_bar = IndeterminateProgressBar(parent=self)
            self._inline_progress_bar.setFixedHeight(4)
            self._inline_progress_bar.start()
            # Insert just below the source combo (index 1)
            self.table_layout.insertWidget(1, self._inline_progress_bar)
        # <<< ADD BLOCK

        # Disable source combo to prevent re-entrancy
        self.load_source_combo.setEnabled(False)

        # Start the background worker
        self._fetch_worker = FetchSupabaseRentalRecordsWorker(
            self.main_window.supabase_manager, is_archived=False, parent=self
        )
        self._fetch_worker.records_fetched.connect(
            lambda recs: self._on_cloud_records_ready(recs, selected_source)
        )
        self._fetch_worker.error_occurred.connect(self._on_cloud_records_error)
        self._fetch_worker.finished.connect(self._on_cloud_records_finished)
        self._fetch_worker.start()

    # ------------------------------------------------------------------
    # Background-worker callbacks
    # ------------------------------------------------------------------

    def _on_cloud_records_ready(self, records, source):
        """Handle successful retrieval of records."""
        if not records:
            # Message already displayed by caller (load_rental_records or worker callback)
            return
        self._populate_rental_table(source, records)

    def _on_cloud_records_error(self, message: str):
        QMessageBox.critical(self, "Cloud DB Error", f"Failed to load rental records from Supabase: {message}")
        # >>> ADD
        # Ensure we tidy up the progress bar even on error
        if self._inline_progress_bar is not None:
            self._inline_progress_bar.stop()
            self.table_layout.removeWidget(self._inline_progress_bar)
            self._inline_progress_bar.deleteLater()
            self._inline_progress_bar = None
        # <<< ADD

    def _on_cloud_records_finished(self):
        """Always called when worker thread ends—success or fail."""
        self.load_source_combo.setEnabled(True)
        # >>> MODIFY
        if self._inline_progress_bar is not None:
            self._inline_progress_bar.stop()
            self.table_layout.removeWidget(self._inline_progress_bar)
            self._inline_progress_bar.deleteLater()
            self._inline_progress_bar = None
        # <<< MODIFY

    # ------------------------------------------------------------------
    # Helper to populate table (shared between local & cloud paths)  
    # ------------------------------------------------------------------

    def _populate_rental_table(self, source_label: str, records: list):
        """Fill the QTableWidget with rental records."""
        if not records:
            # Message already displayed by caller (load_rental_records or worker callback)
            return

        self.rental_records_table.setRowCount(len(records))

        for row_idx, record in enumerate(records):
            if source_label == "Local DB":
                # SQLite tuple; keep same unpacking as before
                display_id, tenant_name, room_number, advanced_paid, created_at, updated_at = (
                    record[0], record[1], record[2], record[3], record[4], record[5]
                )
                full_record_data = record  # full tuple
            else:  # Cloud (Supabase) -> dict
                display_id = record.get("id")
                tenant_name = record.get("tenant_name")
                room_number = record.get("room_number")
                advanced_paid = record.get("advanced_paid")
                created_at = record.get("created_at")
                updated_at = record.get("updated_at")
                full_record_data = record

            self.rental_records_table.setItem(row_idx, 0, QTableWidgetItem(str(display_id)))
            self.rental_records_table.setItem(row_idx, 1, QTableWidgetItem(str(tenant_name)))
            self.rental_records_table.setItem(row_idx, 2, QTableWidgetItem(str(room_number)))
            self.rental_records_table.setItem(row_idx, 3, QTableWidgetItem(str(advanced_paid)))
            self.rental_records_table.setItem(row_idx, 4, QTableWidgetItem(str(created_at)))
            self.rental_records_table.setItem(row_idx, 5, QTableWidgetItem(str(updated_at)))

            # Attach raw data for later dialog
            self.rental_records_table.item(row_idx, 0).setData(Qt.UserRole, full_record_data)

    def show_record_details_dialog(self, index):
        if not index.isValid():
            return
            
        selected_row = index.row()
        if selected_row < 0 or selected_row >= self.rental_records_table.rowCount():
            return
            
        item = self.rental_records_table.item(selected_row, 0)
        if not item:
            print(f"No item found at row {selected_row}")
            return
            
        record_data = item.data(Qt.UserRole)
        if not record_data:
            print(f"No record data found for row {selected_row}")
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
                current_source=selected_source, # Pass the current source to the dialog
                supabase_id=record_dict.get("supabase_id") # Pass supabase_id
            )
            dialog.exec_() # Show as modal dialog
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open record details: {e}")
            print(f"Error opening rental record dialog: {e}\n{traceback.format_exc()}")

    def load_record_into_form_for_edit(self, record_data: dict):
        # This method is called from the dialog to load data for editing
        # record_data is expected to be a dictionary (either from local DB or Supabase, flattened)
        self.current_rental_id = record_data.get("id") # Local DB ID
        self.current_supabase_id = record_data.get("supabase_id") # Supabase ID
        # Store archive status so we can retain it during save
        self.current_is_archived = bool(record_data.get("is_archived", False))

        self.tenant_name_input.setText(record_data.get("tenant_name", ""))
        self.room_number_input.setText(record_data.get("room_number", ""))
        self.advanced_paid_input.setText(str(record_data.get("advanced_paid", 0.0)))

        # For image paths, prioritize local paths if available, otherwise use Supabase URLs
        self.photo_path_label.setText(record_data.get("photo_path") or record_data.get("photo_url") or "No file selected")
        self.nid_front_path_label.setText(record_data.get("nid_front_path") or record_data.get("nid_front_url") or "No file selected")
        self.nid_back_path_label.setText(record_data.get("nid_back_path") or record_data.get("nid_back_url") or "No file selected")
        self.police_form_path_label.setText(record_data.get("police_form_path") or record_data.get("police_form_url") or "No file selected")
        
        self.save_record_btn.setText("Update Record")
        self.tenant_name_input.setFocus() # Set focus back to the form

    def clear_form(self):
        self.tenant_name_input.clear()
        self.room_number_input.clear()
        self.advanced_paid_input.clear()
        self.photo_path_label.setText("No file selected")
        self.nid_front_path_label.setText("No file selected")
        self.nid_back_path_label.setText("No file selected")
        self.police_form_path_label.setText("No file selected")
        self.current_rental_id = None
        self.current_supabase_id = None
        self.current_is_archived = False
        self.save_record_btn.setText("Save Record")

    def _handle_enter_pressed(self, current_index):
        """Handles Enter key press for sequential focus movement."""
        last_idx = len(self.input_fields) - 1
        # Cycle only within the three input fields
        target = self.input_fields[(current_index + 1) % (last_idx + 1)]
        target.setFocus()
        if isinstance(target, QLineEdit):
            target.selectAll()
        return True  # Event handled – stop further processing

    def eventFilter(self, obj, event):
        """Filters events to handle Up/Down arrow key navigation."""
        if event.type() == QEvent.KeyPress and obj in self.input_fields:
            current_index = self.input_fields.index(obj)
            if event.key() == Qt.Key_Down:
                target = self.input_fields[(current_index + 1) % len(self.input_fields)]
                target.setFocus()
                if isinstance(target, QLineEdit):
                    target.selectAll()
                return True  # Event handled
            elif event.key() == Qt.Key_Up:
                target = self.input_fields[(current_index - 1) % len(self.input_fields)]
                target.setFocus()
                if isinstance(target, QLineEdit):
                    target.selectAll()
                return True  # Event handled
        return super().eventFilter(obj, event)

    def _rel_to(self, p: Path, root: Path) -> bool:
        """Helper to safely check if a path is relative to a root, guarding against ValueError."""
        try:
            return p.is_relative_to(root)
        except ValueError:
            return False

    def _is_safe_path(self, p: str) -> bool:
        """
        Validate that the file path is safe to access, considering symlinks and preventing
        directory traversal attacks.

        This function performs several security checks:
        1. Ensures the path is not empty.
        2. Handles potential OSError during path normalization.
        3. Checks the original (user-supplied) path against a list of forbidden directories.
        4. Prevents directory traversal attempts by checking for ".." segments in the original path.
        5. Resolves the path to its true location, handling symlinks.
        6. Checks the resolved path against forbidden directories (defense-in-depth).
        7. Checks the resolved path against a list of allowed safe directories.
        """
        if not p:
            return False

        try:
            # Convert the input string to a Path object for easier manipulation
            original_path = Path(p)
            # Normalize original path for case-insensitive comparison on Windows
            original_path_norm = Path(os.path.normcase(str(original_path)))
        except OSError: # Catches invalid path strings (e.g. containing null bytes)
            # If path conversion fails, it's not a safe path
            return False

        # 1. Check original path against forbidden directories (before resolving symlinks)
        # This prevents access to sensitive system directories even if symlinked from a safe location.
        if any(self._rel_to(original_path_norm, Path(os.path.normcase(str(fd)))) for fd in self.FORBIDDEN):
            return False

        # 2. Reject any traversal attempt visible in the user-supplied path
        # Path.resolve() eliminates ".." segments, so this check must be done before resolution.
        if any(part == ".." for part in original_path.parts):
            return False

        # 3. Resolve the path to check its true location
        # This handles symlinks and gets the canonical path.
        try:
            resolved_path = original_path.resolve(strict=False)
            resolved_path_norm = Path(os.path.normcase(str(resolved_path)))
        except OSError:
            # If resolution fails (e.g., path does not exist or permissions issue), it's not a safe path
            return False

        # 4. Explicitly check for directory traversal segments in the resolved path (defense-in-depth)
        # While resolve() typically removes '..', this acts as an additional safeguard.
        if any(part == ".." for part in resolved_path.parts):
            return False

        # 5. Check resolved path against forbidden directories (in case a safe path symlinks to a forbidden one)
        if any(self._rel_to(resolved_path_norm, Path(os.path.normcase(str(fd)))) for fd in self.FORBIDDEN):
            return False

        # 6. Check resolved path against safe directories
        return any(self._rel_to(resolved_path_norm, Path(os.path.normcase(str(sd)))) for sd in self.SAFE_DIRS)

    def _validate_image_file(self, file_path):
        """Validate that the file is actually an image"""
        try:
            pixmap = QPixmap(file_path)
            return not pixmap.isNull()
        except Exception:
            return False

    def _scale_image(self, image_path, max_width_points, max_height_points):
        # If the path is a URL, download to temp file first
        if image_path and str(image_path).startswith("http"):
            try:
                import requests, tempfile, urllib.parse, os as _os

                # Parse the URL to safely extract the file extension (ignore query params)
                parsed = urllib.parse.urlparse(image_path)
                url_path = parsed.path  # e.g. "/storage/v1/object/public/..../image.jpg"
                _root, ext = _os.path.splitext(url_path)
                # Fallback to .jpg if extension missing or contains illegal chars (e.g. '.jpg?')
                if not ext or any(c in ext for c in "?&#%"):
                    ext = ".jpg"

                # Disable TLS certificate verification to avoid failures in bundled executables
                r = requests.get(image_path, timeout=10, verify=False)
                if r.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    tmp.write(r.content)
                    tmp.close()
                    image_path = tmp.name
                    # temp files are considered safe
                    safe_bypass = True
                else:
                    return None, 0, 0
            except Exception as url_exc:
                print(f"Error downloading image {image_path}: {url_exc}")
                return None, 0, 0

        if not image_path or ('safe_bypass' not in locals() and not self._is_safe_path(image_path)) or not os.path.exists(image_path):
            return None, 0, 0
        try:
            # Use ReportLab's ImageReader to get original dimensions in points
            img_reader = ImageReader(image_path)
            original_width_points, original_height_points = img_reader.getSize()

            # Calculate scaling factors
            width_scale = max_width_points / original_width_points
            height_scale = max_height_points / original_height_points
            scale_factor = min(width_scale, height_scale)

            # If the image is already smaller than the max dimensions, don't upscale
            if scale_factor >= 1.0:
                return image_path, original_width_points, original_height_points

            new_width_points = original_width_points * scale_factor
            new_height_points = original_height_points * scale_factor

            # Return the original path and new dimensions in points
            return image_path, new_width_points, new_height_points
        except Exception as e:
            print(f"Error scaling image {image_path}: {e}")
            traceback.print_exc()
            return None, 0, 0

    def generate_rental_pdf_from_data(self, record_data):
        tenant_name = record_data[1]
        room_number = record_data[2]
        advanced_paid = record_data[3]
        created_at = record_data[4]
        updated_at = record_data[5]
        photo_path = record_data[6]
        nid_front_path = record_data[7]
        nid_back_path = record_data[8]
        police_form_path = record_data[9]

        # Define PDF file name
        def _sanitize(s):
            # Replace invalid filename characters with underscore
            return re.sub(r'[\\/*?:"<>|]', '_', str(s)).replace(' ', '_')

        pdf_filename = f"Rental_Record_{_sanitize(tenant_name)}_{_sanitize(room_number)}.pdf"
        pdf_path = os.path.join(os.path.expanduser("~/Documents"), pdf_filename)

        try:
            doc = BaseDocTemplate(pdf_path, pagesize=letter,
                                  leftMargin=0.1 * inch, rightMargin=0.1 * inch,
                                  topMargin=0.1 * inch, bottomMargin=0.1 * inch)
            styles = getSampleStyleSheet()

            # Custom style for centered bold text
            centered_bold_style = ParagraphStyle(
                'CenteredBold',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=3
            )

            # Custom style for "Associated Documents:" to control spacing
            associated_docs_style = ParagraphStyle(
                'AssociatedDocs',
                parent=styles['h3'], # Inherit font/size from h3, but override spacing
                spaceBefore=0,
                spaceAfter=0
            )

            # Define Frames for Page 1 (Rental Details)
            frame1_height = letter[1] - (2 * 0.1 * inch) # Page height - top/bottom margins
            frame1 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, frame1_height,
                           leftPadding=0, bottomPadding=0,
                           rightPadding=0, topPadding=0,
                           showBoundary=1) # Set showBoundary=1 for debugging frames

            # Define Frames for Page 2 (Tenant Photo, NID Front/Back)
            # Page width and height for calculations
            page_width, page_height = letter

            # Margins for Page 2 frames
            p2_left_margin = 0.1 * inch
            p2_right_margin = 0.1 * inch
            p2_top_margin = 0.1 * inch
            p2_bottom_margin = 0.1 * inch

            # Calculate usable width and height for frames
            usable_width = page_width - p2_left_margin - p2_right_margin
            usable_height = page_height - p2_top_margin - p2_bottom_margin

            # Define a single full-page frame for Page 2
            frame2_full = Frame(p2_left_margin, p2_bottom_margin, usable_width, usable_height,
                                leftPadding=0, bottomPadding=0,
                                rightPadding=0, topPadding=0,
                                showBoundary=1)

            # Define Frames for Page 3 (Police Form)
            frame3_height = letter[1] - (2 * 0.1 * inch)
            frame3 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, frame3_height,
                           leftPadding=0, bottomPadding=0,
                           rightPadding=0, topPadding=0,
                           showBoundary=1)

            # Define Page Templates
            page_template_1 = PageTemplate(id='Page1', frames=[frame1])
            page_template_2 = PageTemplate(id='Page2', frames=[frame2_full]) # Use single frame
            page_template_3 = PageTemplate(id='Page3', frames=[frame3])

            doc.addPageTemplates([page_template_1, page_template_2, page_template_3])

            all_elements = []
            
            # --- Page 1: Rental Information Data ---
            all_elements.append(Paragraph("Rental Information Record", centered_bold_style))
            all_elements.append(Spacer(1, 0.02 * inch))

            # Tenant Details Table
            data = [
                ["Field", "Details"],
                ["Tenant Name:", tenant_name],
                ["Room Number:", room_number],
                ["Advanced Paid:", f"TK {advanced_paid:,.2f}"],
                ["Record Created:", created_at],
                ["Last Updated:", updated_at]
            ]
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ])
            table = Table(data, colWidths=[2 * inch, 4 * inch])
            table.setStyle(table_style)
            all_elements.append(table)
            all_elements.append(Spacer(1, 0.02 * inch))
            all_elements.append(NextPageTemplate('Page2')) # Set template for the next page
            all_elements.append(PageBreak()) # Force a page break

            # --- Page 2: Tenant Photo, NID Front/Back ---
            # Define a common max height for images on Page 2 to ensure they fit
            # Set a fixed maximum height for each image to ensure all three fit on the page.
            max_image_height_p2 = 3.0 * inch # Each image will be scaled to fit within 3 inches height

            all_elements.append(Paragraph("<b>Associated Documents:</b>", associated_docs_style))
            all_elements.append(Spacer(1, 0.05 * inch)) # Use a fixed spacer height

            # Tenant Photo
            if photo_path and (photo_path.startswith("http") or (os.path.exists(photo_path) and self._is_safe_path(photo_path))):
                all_elements.append(Paragraph("<b>Tenant Photo:</b>", ParagraphStyle('ImageTitle', parent=styles['Normal'], spaceAfter=0, leading=0)))
                scaled_image_path, img_width_points, img_height_points = self._scale_image(photo_path, usable_width, max_image_height_p2)
                if scaled_image_path:
                    img = Image(scaled_image_path, width=img_width_points, height=img_height_points, kind='proportional')
                    img.hAlign = 'CENTER' # Center the image horizontally
                    all_elements.append(img)
                else:
                    all_elements.append(Paragraph(f"<i>Could not load image from {photo_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>Tenant Photo: Not provided or file not found/safe.</i>", styles['Normal']))
            all_elements.append(Spacer(1, 0.05 * inch))

            # NID Front Side
            if nid_front_path and (nid_front_path.startswith("http") or (os.path.exists(nid_front_path) and self._is_safe_path(nid_front_path))):
                all_elements.append(Paragraph("<b>NID Front Side:</b>", ParagraphStyle('ImageTitle', parent=styles['Normal'], spaceAfter=0, leading=0)))
                scaled_image_path, img_width_points, img_height_points = self._scale_image(nid_front_path, usable_width, max_image_height_p2)
                if scaled_image_path:
                    img = Image(scaled_image_path, width=img_width_points, height=img_height_points, kind='proportional')
                    img.hAlign = 'CENTER' # Center the image horizontally
                    all_elements.append(img)
                else:
                    all_elements.append(Paragraph(f"<i>Could not load image from {nid_front_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>NID Front Side: Not provided or file not found/safe.</i>", styles['Normal']))
            all_elements.append(Spacer(1, 0.05 * inch)) # Small space between NID images

            # NID Back Side
            if nid_back_path and (nid_back_path.startswith("http") or (os.path.exists(nid_back_path) and self._is_safe_path(nid_back_path))):
                all_elements.append(Paragraph("<b>NID Back Side:</b>", ParagraphStyle('ImageTitle', parent=styles['Normal'], spaceAfter=0, leading=0)))
                scaled_image_path, img_width_points, img_height_points = self._scale_image(nid_back_path, usable_width, max_image_height_p2)
                if scaled_image_path:
                    img = Image(scaled_image_path, width=img_width_points, height=img_height_points, kind='proportional')
                    img.hAlign = 'CENTER' # Center the image horizontally
                    all_elements.append(img)
                else:
                    all_elements.append(Paragraph(f"<i>Could not load image from {nid_back_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>NID Back Side: Not provided or file not found/safe.</i>", styles['Normal']))
            all_elements.append(NextPageTemplate('Page3')) # Set template for the next page
            all_elements.append(PageBreak()) # Force a page break

            # --- Page 3: Police Verification Form ---
            all_elements.append(Paragraph("<b>Police Verification Form:</b>", styles['Normal']))
            all_elements.append(Spacer(1, 0.02 * inch))

            if police_form_path and (police_form_path.startswith("http") or (os.path.exists(police_form_path) and self._is_safe_path(police_form_path))):
                # Calculate max_width and max_height for the police form to fit frame3
                police_form_max_width = frame3.width # Use full frame width
                police_form_max_height = frame3_height - (1.0 * inch) # Account for some internal padding/spacing and title/spacer

                # Use _scale_image for police form as well
                scaled_image_path, img_width_points, img_height_points = self._scale_image(police_form_path, police_form_max_width, police_form_max_height)
                
                if scaled_image_path:
                    try:
                        img = Image(scaled_image_path, width=img_width_points, height=img_height_points) # No need for kind='proportional' if already scaled
                        img.hAlign = 'CENTER'
                        all_elements.append(img)
                    except Exception as img_e:
                        all_elements.append(Paragraph(f"<i>Error creating image object for police form: {img_e}</i>", styles['Normal']))
                else:
                    all_elements.append(Paragraph(f"<i>Could not load or scale police form image from {police_form_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>Police Verification Form: Not provided or file not found/safe.</i>", styles['Normal']))

            doc.build(all_elements)
            QMessageBox.information(self, "PDF Generated", f"Rental record PDF saved to:\n{pdf_path}")
            return pdf_path
        except Exception as e:
            QMessageBox.critical(self, "PDF Generation Error", f"Failed to generate PDF: {e}\n{traceback.format_exc()}")
            return None
