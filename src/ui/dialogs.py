import sys
import traceback
import os
from datetime import datetime
from collections import namedtuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QMessageBox, QDialog, QWidget,
    QGridLayout
)
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, TitleLabel
)
from .responsive_components import ResponsiveDialog
from .responsive_image import ResponsiveImagePreviewGrid

# Suppress SSL certificate warnings when verify=False is used in requests
try:
    import urllib3
except ModuleNotFoundError:
    # Fallback: urllib3 may be vendored inside requests in some environments / PyInstaller builds
    import requests.packages.urllib3 as urllib3  # type: ignore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define a namedtuple for rental records for clearer access
RentalRecord = namedtuple('RentalRecord', [
    'id', 'tenant_name', 'room_number', 'advanced_paid', 'created_at',
    'updated_at', 'photo_path', 'nid_front_path', 'nid_back_path',
    'police_form_path', 'is_archived', 'supabase_id', # Added supabase_id
    'photo_url', 'nid_front_url', 'nid_back_url', 'police_form_url' # Added Supabase URLs
])

class RentalRecordDialog(ResponsiveDialog):
    def __init__(self, parent=None, record_data=None, db_manager=None, supabase_manager=None, is_archived_record=False, main_window_ref=None, current_source="Local DB", supabase_id=None):
        super().__init__(parent)
        self.setWindowTitle("Rental Record Details")
        # self.setMinimumSize(500, 600) # Removed for responsiveness
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
        details_group = CardWidget()
        details_layout = QVBoxLayout(details_group)
        details_layout.addWidget(TitleLabel("Record Information"))
        
        details_form_widget = QWidget()
        details_form_layout = QFormLayout(details_form_widget)
        
        self.tenant_name_label = QLabel()
        self.room_number_label = QLabel()
        self.advanced_paid_label = QLabel()
        self.created_at_label = QLabel()
        self.updated_at_label = QLabel()

        details_form_layout.addRow("Tenant Name:", self.tenant_name_label)
        details_form_layout.addRow("Room Number:", self.room_number_label)
        details_form_layout.addRow("Advanced Paid:", self.advanced_paid_label)
        details_form_layout.addRow("Created At:", self.created_at_label)
        details_form_layout.addRow("Updated At:", self.updated_at_label)
        details_layout.addWidget(details_form_widget)
        
        main_layout.addWidget(details_group)

        # Image Previews
        image_preview_group = CardWidget()
        image_preview_main_layout = QVBoxLayout(image_preview_group)
        image_preview_main_layout.addWidget(TitleLabel("Document Previews"))
        image_preview_widget = QWidget()
        image_preview_layout = QGridLayout(image_preview_widget)
        image_preview_main_layout.addWidget(image_preview_widget)
        image_preview_layout.setContentsMargins(20, 20, 20, 20)
        image_preview_layout.setSpacing(10)

        self.photo_preview_label = ResponsiveImagePreviewGrid()
        image_preview_layout.addWidget(self.photo_preview_label, 0, 0)

        self.nid_front_preview_label = ResponsiveImagePreviewGrid()
        image_preview_layout.addWidget(self.nid_front_preview_label, 0, 1)

        self.nid_back_preview_label = ResponsiveImagePreviewGrid()
        image_preview_layout.addWidget(self.nid_back_preview_label, 1, 0)

        self.police_form_preview_label = ResponsiveImagePreviewGrid()
        image_preview_layout.addWidget(self.police_form_preview_label, 1, 1)
        
        main_layout.addWidget(image_preview_group)

        # PDF Link Display
        pdf_link_group = CardWidget()
        pdf_link_layout = QVBoxLayout(pdf_link_group)
        pdf_link_layout.addWidget(TitleLabel("Generated PDF"))
        
        self.pdf_path_label = QLabel("No PDF generated yet.")
        self.pdf_path_label.setOpenExternalLinks(True) # Make link clickable
        pdf_link_layout.addWidget(self.pdf_path_label)
 
        main_layout.addWidget(pdf_link_group)

        # Action Buttons for the dialog
        dialog_buttons_layout = QHBoxLayout()
        
        self.dialog_save_pdf_btn = PrimaryPushButton("Save PDF")
        self.dialog_save_pdf_btn.clicked.connect(self.generate_pdf_from_dialog)
        dialog_buttons_layout.addWidget(self.dialog_save_pdf_btn)

        self.dialog_edit_btn = PushButton("Edit")
        self.dialog_edit_btn.clicked.connect(self.edit_record)
        dialog_buttons_layout.addWidget(self.dialog_edit_btn)

        self.dialog_archive_btn = PushButton("Archive")
        self.dialog_archive_btn.clicked.connect(self.toggle_archive_status)
        dialog_buttons_layout.addWidget(self.dialog_archive_btn)

        self.dialog_delete_btn = PushButton("Delete")
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
            placeholder_text = f"No {img_type.replace('_', ' ').title()}"
            
            print(f"DEBUG: Processing {img_type} with path: {path}")
            
            if path and path != "No file selected" and path.startswith("http"):
                try:
                    import requests
                    # Disable TLS certificate verification to avoid failures in bundled executables
                    resp = requests.get(path, timeout=5, verify=False)
                    if resp.status_code == 200:
                        label.setImageData(resp.content, placeholder_text)
                        print(f"DEBUG: Successfully loaded {img_type} from URL")
                    else:
                        label._show_placeholder(placeholder_text)
                        print(f"DEBUG: Failed to load {img_type} from URL, status: {resp.status_code}")
                except Exception as e:
                    label._show_placeholder(placeholder_text)
                    print(f"DEBUG: Exception loading {img_type} from URL: {e}")
            elif path and path != "No file selected" and os.path.exists(path):
                # Simplified check - just verify file exists
                try:
                    success = label.setImagePath(path, placeholder_text)
                    if success:
                        print(f"DEBUG: Successfully loaded {img_type} from file: {path}")
                    else:
                        print(f"DEBUG: Failed to load {img_type} from file: {path}")
                        label._show_placeholder(placeholder_text)
                except Exception as e:
                    print(f"DEBUG: Exception loading {img_type} from file: {e}")
                    label._show_placeholder(placeholder_text)
            else:
                label._show_placeholder(placeholder_text)
                print(f"DEBUG: Showing placeholder for {img_type} - path: {path}, exists: {os.path.exists(path) if path else False}")

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
        # Since parent is now main window, we need to access the rental tab through main_window_ref
        try:
            # Use the correct attribute name from the main window
            if self.main_window and hasattr(self.main_window, 'rental_info_tab_instance'):
                # Access the rental tab through the main window
                rental_tab = self.main_window.rental_info_tab_instance
                if hasattr(rental_tab, 'load_record_into_form_for_edit'):
                    # Convert namedtuple to dict for the rental tab
                    record_dict = self.record_data._asdict()
                    rental_tab.load_record_into_form_for_edit(record_dict)
                    self.accept()  # Close the dialog
                    return
            
            # Fallback: try the old attribute name
            if self.main_window and hasattr(self.main_window, 'rental_info_tab'):
                rental_tab = self.main_window.rental_info_tab
                if hasattr(rental_tab, 'load_record_into_form_for_edit'):
                    record_dict = self.record_data._asdict()
                    rental_tab.load_record_into_form_for_edit(record_dict)
                    self.accept()  # Close the dialog
                    return
            
            # Second fallback: try to find rental tab in navigation interface
            if self.main_window and hasattr(self.main_window, 'stackedWidget'):
                for i in range(self.main_window.stackedWidget.count()):
                    tab = self.main_window.stackedWidget.widget(i)
                    if hasattr(tab, 'load_record_into_form_for_edit'):
                        record_dict = self.record_data._asdict()
                        tab.load_record_into_form_for_edit(record_dict)
                        self.accept()  # Close the dialog
                        return
            
            QMessageBox.critical(self, "Error", "Edit function not accessible. Could not find rental tab.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit record: {e}")

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
        try:
            new_archive_status = not self.is_archived_record
            action_text = "archived" if new_archive_status else "unarchived"
            
            # Handle both local and cloud records
            if self.current_source == "Local DB":
                # Update local database
                update_query = "UPDATE rentals SET is_archived = ? WHERE id = ?"
                self.db_manager.execute_query(update_query, (1 if new_archive_status else 0, self.record_data.id))
                QMessageBox.information(self, "Success", f"Record has been {action_text} in local database.")
                
            elif self.current_source == "Cloud (Supabase)":
                # Update cloud database
                if self.supabase_manager and self.supabase_manager.is_client_initialized():
                    success = self.supabase_manager.update_rental_record_archive_status(
                        self.supabase_id or self.record_data.supabase_id, 
                        new_archive_status
                    )
                    if success:
                        QMessageBox.information(self, "Success", f"Record has been {action_text} in the cloud.")
                    else:
                        QMessageBox.critical(self, "Supabase Error", "Failed to update record in Supabase.")
                        return
                else:
                    QMessageBox.warning(self, "Supabase Error", "Supabase client not configured.")
                    return
            
            # Update local state
            self.is_archived_record = new_archive_status
            
            # Refresh the rental tabs
            try:
                if self.main_window:
                    # Try different methods to refresh the tabs
                    if hasattr(self.main_window, 'refresh_all_rental_tabs'):
                        self.main_window.refresh_all_rental_tabs()
                    elif hasattr(self.main_window, 'rental_info_tab'):
                        # Refresh the rental info tab directly
                        self.main_window.rental_info_tab.load_rental_records()
                    elif hasattr(self.main_window, 'tab_widget'):
                        # Find and refresh rental tabs in the tab widget
                        for i in range(self.main_window.tab_widget.count()):
                            tab = self.main_window.tab_widget.widget(i)
                            if hasattr(tab, 'load_rental_records'):
                                tab.load_rental_records()
            except Exception as refresh_error:
                print(f"Warning: Could not refresh tabs: {refresh_error}")
            
            self.accept()  # Close the dialog
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle archive status: {e}")
            print(f"Archive toggle error: {traceback.format_exc()}")