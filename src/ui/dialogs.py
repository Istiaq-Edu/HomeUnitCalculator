import sys
import traceback
import os
from datetime import datetime
from collections import namedtuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout, QMessageBox, QDialog,
    QGridLayout
)

from src.ui.styles import (
    get_room_selection_style, get_button_style
)
from src.ui.custom_widgets import CustomNavButton

# Suppress SSL certificate warnings when verify=False is used in requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define a namedtuple for rental records for clearer access
RentalRecord = namedtuple('RentalRecord', [
    'id', 'tenant_name', 'room_number', 'advanced_paid', 'created_at',
    'updated_at', 'photo_path', 'nid_front_path', 'nid_back_path',
    'police_form_path', 'is_archived', 'supabase_id', # Added supabase_id
    'photo_url', 'nid_front_url', 'nid_back_url', 'police_form_url' # Added Supabase URLs
])

class RentalRecordDialog(QDialog):
    def __init__(self, parent=None, record_data=None, db_manager=None, supabase_manager=None, is_archived_record=False, main_window_ref=None, current_source="Local DB", supabase_id=None):
        super().__init__(parent)
        self.setWindowTitle("Rental Record Details")
        self.setMinimumSize(500, 600)
        if db_manager is None:
            raise ValueError("db_manager is required for dialog operations")
        if record_data is None:
            raise ValueError("record_data is required to display record details")
        
        self.db_manager = db_manager
        self.supabase_manager = supabase_manager # New: SupabaseManager instance
        # record_data is now expected to be a dictionary for consistency
        # Convert dictionary to namedtuple, providing defaults for new fields
        self.record_data = RentalRecord(
            id=record_data.get('id'),
            tenant_name=record_data.get('tenant_name'),
            room_number=record_data.get('room_number'),
            advanced_paid=record_data.get('advanced_paid'),
            created_at=record_data.get('created_at'),
            updated_at=record_data.get('updated_at'),
            photo_path=record_data.get('photo_path'),
            nid_front_path=record_data.get('nid_front_path'),
            nid_back_path=record_data.get('nid_back_path'),
            police_form_path=record_data.get('police_form_path'),
            is_archived=record_data.get('is_archived'),
            supabase_id=record_data.get('supabase_id'), # New
            photo_url=record_data.get('photo_url'), # New
            nid_front_url=record_data.get('nid_front_url'), # New
            nid_back_url=record_data.get('nid_back_url'), # New
            police_form_url=record_data.get('police_form_url') # New
        )
        self.is_archived_record = is_archived_record
        self.main_window = main_window_ref # Store reference to main window
        self.current_source = current_source # New: To know if record came from Local DB or Supabase
        self.supabase_id = supabase_id or record_data.get("supabase_id")

        self.init_ui()
        if self.record_data:
            self.display_record_details()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Display Area for Details
        details_group = QGroupBox("Record Information")
        details_group.setStyleSheet(get_room_selection_style())
        details_layout = QFormLayout(details_group)
        
        self.tenant_name_label = QLabel()
        self.room_number_label = QLabel()
        self.advanced_paid_label = QLabel()
        self.created_at_label = QLabel()
        self.updated_at_label = QLabel()

        details_layout.addRow("Tenant Name:", self.tenant_name_label)
        details_layout.addRow("Room Number:", self.room_number_label)
        details_layout.addRow("Advanced Paid:", self.advanced_paid_label)
        details_layout.addRow("Created At:", self.created_at_label)
        details_layout.addRow("Updated At:", self.updated_at_label)
        
        main_layout.addWidget(details_group)

        # Image Previews
        image_preview_group = QGroupBox("Document Previews")
        image_preview_group.setStyleSheet(get_room_selection_style())
        image_preview_layout = QGridLayout(image_preview_group)
        image_preview_layout.setContentsMargins(20, 20, 20, 20)
        image_preview_layout.setSpacing(10)

        self.photo_preview_label = QLabel("No Photo")
        self.photo_preview_label.setAlignment(Qt.AlignCenter)
        self.photo_preview_label.setFixedSize(120, 120)
        self.photo_preview_label.setStyleSheet("border: 1px solid #ccc;")
        image_preview_layout.addWidget(self.photo_preview_label, 0, 0)

        self.nid_front_preview_label = QLabel("No NID Front")
        self.nid_front_preview_label.setAlignment(Qt.AlignCenter)
        self.nid_front_preview_label.setFixedSize(120, 120)
        self.nid_front_preview_label.setStyleSheet("border: 1px solid #ccc;")
        image_preview_layout.addWidget(self.nid_front_preview_label, 0, 1)

        self.nid_back_preview_label = QLabel("No NID Back")
        self.nid_back_preview_label.setAlignment(Qt.AlignCenter)
        self.nid_back_preview_label.setFixedSize(120, 120)
        self.nid_back_preview_label.setStyleSheet("border: 1px solid #ccc;")
        image_preview_layout.addWidget(self.nid_back_preview_label, 1, 0)

        self.police_form_preview_label = QLabel("No Police Form")
        self.police_form_preview_label.setAlignment(Qt.AlignCenter)
        self.police_form_preview_label.setFixedSize(120, 120)
        self.police_form_preview_label.setStyleSheet("border: 1px solid #ccc;")
        image_preview_layout.addWidget(self.police_form_preview_label, 1, 1)
        
        main_layout.addWidget(image_preview_group)

        # PDF Link Display
        pdf_link_group = QGroupBox("Generated PDF")
        pdf_link_group.setStyleSheet(get_room_selection_style())
        pdf_link_layout = QVBoxLayout(pdf_link_group)
        
        self.pdf_path_label = QLabel("No PDF generated yet.")
        self.pdf_path_label.setOpenExternalLinks(True) # Make link clickable
        self.pdf_path_label.setStyleSheet("color: blue; text-decoration: underline;")
        pdf_link_layout.addWidget(self.pdf_path_label)
 
        main_layout.addWidget(pdf_link_group)

        # Action Buttons for the dialog
        dialog_buttons_layout = QHBoxLayout()
        
        self.dialog_save_pdf_btn = CustomNavButton("Save PDF")
        self.dialog_save_pdf_btn.setStyleSheet(get_button_style())
        self.dialog_save_pdf_btn.clicked.connect(self.generate_pdf_from_dialog)
        dialog_buttons_layout.addWidget(self.dialog_save_pdf_btn)

        self.dialog_edit_btn = CustomNavButton("Edit")
        self.dialog_edit_btn.setStyleSheet(get_button_style())
        self.dialog_edit_btn.clicked.connect(self.edit_record)
        dialog_buttons_layout.addWidget(self.dialog_edit_btn)

        self.dialog_archive_btn = CustomNavButton("Archive")
        self.dialog_archive_btn.setStyleSheet(get_button_style())
        self.dialog_archive_btn.clicked.connect(self.toggle_archive_status)
        dialog_buttons_layout.addWidget(self.dialog_archive_btn)

        self.dialog_delete_btn = CustomNavButton("Delete")
        self.dialog_delete_btn.setStyleSheet(get_button_style())
        self.dialog_delete_btn.clicked.connect(self.delete_record)
        dialog_buttons_layout.addWidget(self.dialog_delete_btn)

        main_layout.addLayout(dialog_buttons_layout)

    def display_record_details(self):
        # Access record data using named attributes
        self.tenant_name_label.setText(self.record_data.tenant_name)
        self.room_number_label.setText(self.record_data.room_number)
        raw_adv = self.record_data.advanced_paid
        try:
            adv_val = float(raw_adv) if raw_adv is not None else None
        except (TypeError, ValueError):
            adv_val = None
        self.advanced_paid_label.setText(f"{adv_val:.2f} TK" if adv_val is not None else "N/A")
        self.created_at_label.setText(self.record_data.created_at)
        self.updated_at_label.setText(self.record_data.updated_at)

        # Adjust archive button text and visibility
        if self.is_archived_record:
            self.dialog_archive_btn.setText("Unarchive")
            self.dialog_edit_btn.hide() # Typically, archived records are not edited directly
        else:
            self.dialog_archive_btn.setText("Archive")
            self.dialog_edit_btn.show()
        self.dialog_archive_btn.setEnabled(True) # Enable the button

        # Display image previews
        image_labels = {
            "photo": self.photo_preview_label,
            "nid_front": self.nid_front_preview_label,
            "nid_back": self.nid_back_preview_label,
            "police_form": self.police_form_preview_label
        }
        image_paths = {}
        if self.current_source == "Local DB":
            image_paths = {
                "photo": self.record_data.photo_path,
                "nid_front": self.record_data.nid_front_path,
                "nid_back": self.record_data.nid_back_path,
                "police_form": self.record_data.police_form_path
            }
        else: # Cloud (Supabase)
            image_paths = {
                "photo": self.record_data.photo_url,
                "nid_front": self.record_data.nid_front_url,
                "nid_back": self.record_data.nid_back_url,
                "police_form": self.record_data.police_form_url
            }

        for img_type, label in image_labels.items():
            path = image_paths[img_type]
            if path and path.startswith("http"):
                try:
                    import requests
                    # Disable TLS certificate verification to avoid failures in bundled executables
                    resp = requests.get(path, timeout=5, verify=False)
                    if resp.status_code == 200:
                        pixmap = QPixmap()
                        pixmap.loadFromData(resp.content)
                        label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        label.setText("")
                    else:
                        label.setText(f"No {img_type.replace('_', ' ').title()}")
                except Exception as e:
                    label.setText(f"No {img_type.replace('_', ' ').title()}")
            elif path and self._is_safe_path(path) and os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    label.setText("")
                else:
                    label.setText(f"Invalid {img_type.replace('_', ' ').title()}")
            else:
                label.setText(f"No {img_type.replace('_', ' ').title()}")

        # Set PDF link (assuming PDF is generated and path is stored somewhere, or will be generated on demand)
        # For now, we'll set it to a placeholder or clear it if no PDF is associated
        # The actual PDF path will be set after generation via generate_pdf_from_dialog
        self.pdf_path_label.setText("No PDF generated yet for this record.")
        self.pdf_path_label.setToolTip("Click 'Save PDF' to generate and and view.")

    def _is_safe_path(self, file_path):
        """Validate that the file path is safe to access"""
        if not file_path:
            return False
        
        try:
            # Convert to absolute path and resolve any symbolic links
            abs_path = os.path.abspath(os.path.realpath(file_path))
            
            # Get the application's working directory as the safe base
            app_dir = os.path.abspath(os.getcwd())
            
            # Security checks:
            # 1. Must be within app directory or common safe directories
            safe_dirs = [
                app_dir,
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Downloads")
            ]
            
            # Check if path is within any safe directory
            # Normalize paths for comparison, especially for Windows case-insensitivity
            abs_path_lower = abs_path.lower() if os.name == 'nt' else abs_path
            safe_dirs_abs_lower = [os.path.abspath(safe_dir).lower() if os.name == 'nt' else os.path.abspath(safe_dir) for safe_dir in safe_dirs]

            # Check if path is within any safe directory using os.path.commonpath
            is_in_safe_dir = any(
                os.path.commonpath([abs_path_lower, safe_dir_abs_lower]) == safe_dir_abs_lower
                for safe_dir_abs_lower in safe_dirs_abs_lower
            )
            
            # 2. Prevent directory traversal attacks
            # `abs_path` is already canonicalised via realpath; check it instead
            has_traversal_chars = ".." in abs_path
            
            # 3. Prevent access to system directories (case-insensitive for Windows)
            forbidden_dirs = ["/etc", "/sys", "/proc", "c:\\windows", "c:\\system32"]
            in_forbidden_dir = any(abs_path_lower.startswith(forbidden.lower()) for forbidden in forbidden_dirs)
            
            return is_in_safe_dir and not in_forbidden_dir and not has_traversal_chars
            
        except (OSError, ValueError):
            return False

    def generate_pdf_from_dialog(self):
        # Re-use the PDF generation logic from RentalInfoTab
        # Pass the record_data to the main tab's PDF generation method
        # Pass the record_data to the main window's rental_info_tab for PDF generation
        if self.main_window and hasattr(self.main_window, 'rental_info_tab_instance') and hasattr(self.main_window.rental_info_tab_instance, 'generate_rental_pdf_from_data'):
            # Pass the namedtuple directly
            pdf_path = self.main_window.rental_info_tab_instance.generate_rental_pdf_from_data(self.record_data)
            if isinstance(pdf_path, str) and pdf_path: # Ensure it's a string and not empty
                self.pdf_path_label.setText(f"<a href='file:///{pdf_path}'>{os.path.basename(pdf_path)}</a>")
                self.pdf_path_label.setToolTip(f"Click to open: {pdf_path}")
            else:
                self.pdf_path_label.setText("PDF generation cancelled or failed.")
                self.pdf_path_label.setToolTip("No PDF generated.")
        else:
            QMessageBox.critical(self, "Error", "PDF generation function not accessible.")

    def edit_record(self):
        # Load data back into the main form for editing
        if self.parent() and hasattr(self.parent(), 'load_record_into_form_for_edit'):
            # Pass the record_data (which is already a dictionary from RentalInfoTab)
            # The RentalInfoTab's load_record_into_form_for_edit expects a dictionary
            # and handles the conversion to its internal QLineEdit values.
            self.parent().load_record_into_form_for_edit(self.record_data._asdict()) # Convert namedtuple back to dict
            self.accept() # Close the dialog
        else:
            QMessageBox.critical(self, "Error", "Edit function not accessible.")

    def delete_record(self):
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete the record for '{self.record_data.tenant_name}' (Room: {self.record_data.room_number}) from {self.current_source}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if self.current_source == "Local DB":
                    # Get file paths before deleting the record from DB
                    photo_path = self.record_data.photo_path
                    nid_front_path = self.record_data.nid_front_path
                    nid_back_path = self.record_data.nid_back_path
                    police_form_path = self.record_data.police_form_path

                    # Delete the record from the local database
                    self.db_manager.execute_query("DELETE FROM rentals WHERE id = ?", (self.record_data.id,))
                    QMessageBox.information(self, "Success", "Record deleted from local database.")

                    # Attempt to delete associated local files after successful database deletion
                    files_to_delete = [photo_path, nid_front_path, nid_back_path, police_form_path]
                    for f_path in files_to_delete:
                        if f_path and os.path.exists(f_path) and self._is_safe_path(f_path):
                            try:
                                os.remove(f_path)
                                print(f"Deleted associated local file: {f_path}")
                            except Exception as file_e:
                                print(f"Warning: Failed to delete associated local file {f_path}: {file_e}")
                elif self.current_source == "Cloud (Supabase)":
                    if self.supabase_manager and self.record_data.supabase_id:
                        success = self.supabase_manager.delete_rental_record(self.record_data.supabase_id)
                        if success:
                            QMessageBox.information(self, "Success", "Record deleted from Supabase.")
                            # Optionally, delete the corresponding local record if it exists
                            if self.record_data.id:
                                self.db_manager.execute_query("DELETE FROM rentals WHERE id = ?", (self.record_data.id,))
                                print(f"Also deleted corresponding local record ID: {self.record_data.id}")
                        else:
                            QMessageBox.critical(self, "Cloud Error", "Failed to delete record from Supabase.")
                            return # Do not proceed to refresh if Supabase deletion failed
                    else:
                        QMessageBox.warning(self, "Supabase Error", "Supabase manager not available or record has no Supabase ID.")
                        return # Do not proceed to refresh if Supabase deletion cannot be attempted
                
                # Refresh all rental tabs via the main window
                if self.main_window and hasattr(self.main_window, 'refresh_all_rental_tabs'):
                    self.main_window.refresh_all_rental_tabs()
                self.accept() # Close the dialog
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete record: {e}")
                traceback.print_exc()

                # Delete the record from the database
                self.db_manager.execute_query("DELETE FROM rentals WHERE id = ?", (self.record_data.id,))
                QMessageBox.information(self, "Success", "Record deleted successfully.")

                # Attempt to delete associated files after successful database deletion
                files_to_delete = [photo_path, nid_front_path, nid_back_path, police_form_path]
                for f_path in files_to_delete:
                    if f_path and os.path.exists(f_path) and self._is_safe_path(f_path):
                        try:
                            os.remove(f_path)
                            print(f"Deleted associated file: {f_path}")
                        except Exception as file_e:
                            print(f"Warning: Failed to delete associated file {f_path}: {file_e}")
                            # Log the error but do not re-raise, as the database record is already deleted.
                            # This ensures the main operation completes even if file cleanup has issues.

                # Refresh all rental tabs via the main window
                if self.main_window and hasattr(self.main_window, 'refresh_all_rental_tabs'):
                    self.main_window.refresh_all_rental_tabs()
                self.accept() # Close the dialog
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete record: {e}")
                traceback.print_exc()


    def toggle_archive_status(self):
        print(f"Toggling archive status for Supabase record ID: {self.supabase_id}")
        if self.supabase_manager.is_client_initialized():
            success = self.supabase_manager.update_rental_record_archive_status(self.supabase_id, not self.is_archived_record)
            if success:
                QMessageBox.information(self, "Success", f"Record has been {'archived' if not self.is_archived_record else 'unarchived'} in the cloud.")
                self.is_archived_record = not self.is_archived_record
                
                # Refresh the main window's tabs
                if self.main_window:
                    self.main_window.refresh_all_rental_tabs()
                
                self.accept() # Close the dialog
            else:
                QMessageBox.critical(self, "Supabase Error", "Failed to update record in Supabase.")
        else:
            QMessageBox.warning(self, "Supabase Error", "Supabase client not configured.")