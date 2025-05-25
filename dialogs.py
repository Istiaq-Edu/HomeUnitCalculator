import sys
import traceback
import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QFormLayout, QMessageBox, QDialog,
    QGridLayout
)

from styles import (
    get_room_selection_style, get_button_style
)
from custom_widgets import CustomNavButton


class RentalRecordDialog(QDialog):
    def __init__(self, parent=None, record_data=None, db_manager=None, is_archived_record=False, main_window_ref=None):
        super().__init__(parent)
        self.setWindowTitle("Rental Record Details")
        self.setGeometry(200, 200, 800, 600)
        self.db_manager = db_manager
        self.record_data = record_data # Full record data including paths
        self.is_archived_record = is_archived_record
        self.main_window = main_window_ref # Store reference to main window

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
        # record_data: id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived
        self.tenant_name_label.setText(self.record_data[1])
        self.room_number_label.setText(self.record_data[2])
        raw_adv = self.record_data[3]
        try:
            adv_val = float(raw_adv) if raw_adv is not None else None
        except (TypeError, ValueError):
            adv_val = None
        self.advanced_paid_label.setText(f"{adv_val:.2f} TK" if adv_val is not None else "N/A")
        self.created_at_label.setText(self.record_data[4])
        self.updated_at_label.setText(self.record_data[5])

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
        image_paths = {
            "photo": self.record_data[6],
            "nid_front": self.record_data[7],
            "nid_back": self.record_data[8],
            "police_form": self.record_data[9]
        }

        for img_type, label in image_labels.items():
            path = image_paths[img_type]
            if path and self._is_safe_path(path) and os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    label.setText("") # Clear "No Photo" text
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
            is_in_safe_dir = any(abs_path.startswith(os.path.abspath(safe_dir)) for safe_dir in safe_dirs)
            
            # 2. Prevent directory traversal attacks
            has_traversal = ".." in file_path or abs_path != os.path.normpath(abs_path)
            
            # 3. Prevent access to system directories
            forbidden_dirs = ["/etc", "/sys", "/proc", "C:\\Windows", "C:\\System32"]
            in_forbidden_dir = any(abs_path.startswith(forbidden) for forbidden in forbidden_dirs)
            
            return is_in_safe_dir and not has_traversal and not in_forbidden_dir
            
        except (OSError, ValueError):
            return False

    def generate_pdf_from_dialog(self):
        # Re-use the PDF generation logic from RentalInfoTab
        # Pass the record_data to the main tab's PDF generation method
        # Pass the record_data to the main window's rental_info_tab for PDF generation
        if self.main_window and hasattr(self.main_window, 'rental_info_tab_instance') and hasattr(self.main_window.rental_info_tab_instance, 'generate_rental_pdf_from_data'):
            pdf_path = self.main_window.rental_info_tab_instance.generate_rental_pdf_from_data(self.record_data)
            if pdf_path:
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
            self.parent().load_record_into_form_for_edit(self.record_data)
            self.accept() # Close the dialog
        else:
            QMessageBox.critical(self, "Error", "Edit function not accessible.")

    def delete_record(self):
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to delete the record for '{self.record_data[1]}' (Room: {self.record_data[2]})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_query("DELETE FROM rentals WHERE id = ?", (self.record_data[0],))
                QMessageBox.information(self, "Success", "Record deleted successfully.")
                # Refresh all rental tabs via the main window
                if self.main_window and hasattr(self.main_window, 'refresh_all_rental_tabs'):
                    self.main_window.refresh_all_rental_tabs()
                self.accept() # Close the dialog
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to delete record: {e}")
                traceback.print_exc()


    def toggle_archive_status(self):
        record_id = self.record_data[0]
        current_status = self.record_data[10] # is_archived column is at index 10
        
        new_status = 1 if current_status == 0 else 0
        action_text = "archive" if new_status == 1 else "unarchive"
        
        reply = QMessageBox.question(self, f"Confirm {action_text.capitalize()}",
                                     f"Are you sure you want to {action_text} the record for '{self.record_data[1]}' (Room: {self.record_data[2]})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.db_manager.execute_query("UPDATE rentals SET is_archived = ?, updated_at = ? WHERE id = ?",
                                             (new_status, datetime.now().isoformat(), record_id))
                QMessageBox.information(self, "Success", f"Record {action_text}d successfully.")
                
                # Refresh all rental tabs via the main window
                if self.main_window and hasattr(self.main_window, 'refresh_all_rental_tabs'):
                    self.main_window.refresh_all_rental_tabs()
                self.accept() # Close the dialog
            except Exception as e:
                QMessageBox.critical(self, "Database Error", f"Failed to {action_text} record: {e}")
                traceback.print_exc()