import sys
import traceback
import os
import io # Import the io module for in-memory binary streams
from datetime import datetime
from pathlib import Path # Import Path from pathlib

from PyQt5.QtCore import Qt, QRegExp, QEvent
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
    get_room_selection_style, get_room_group_style, get_line_edit_style,
    get_button_style, get_table_style, get_label_style
)
from src.core.utils import resource_path, _clear_layout
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomNavButton
from src.ui.dialogs import RentalRecordDialog


class RentalInfoTab(QWidget):
    # Define safe and forbidden directories at the class level
    SAFE_DIRS = [Path.cwd()] + [Path.home() / d for d in ("Documents", "Desktop", "Downloads")]
    FORBIDDEN = [
        Path(p) for p in (
            "/etc", "/sys", "/proc", "/bin", "/usr",
            "C:/Windows", "C:/Windows/System32"
        )
    ]

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = self.main_window.db_manager

        self.tenant_name_input = None
        self.room_number_input = None
        self.advanced_paid_input = None
        self.photo_path_label = None
        self.nid_front_path_label = None
        self.nid_back_path_label = None
        self.police_form_path_label = None
        self.rental_records_table = None

        self.current_rental_id = None # To track if we are editing an existing record

        self.init_ui()
        self.setup_db_table()
        self.load_rental_records()

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

        # Set up keyboard navigation for input fields
        for i, field in enumerate(self.input_fields):
            field.returnPressed.connect(lambda i=i: self._handle_enter_pressed(i))
            field.installEventFilter(self) # Install event filter for arrow keys

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

        # Save Record Button
        self.save_record_btn = CustomNavButton("Save Record")
        self.save_record_btn.setStyleSheet(get_button_style())
        self.save_record_btn.clicked.connect(self.save_rental_record)
        left_column_layout.addWidget(self.save_record_btn)

        main_horizontal_layout.addLayout(left_column_layout)

        # Right Column Layout (Rental Records Table)
        right_column_layout = QVBoxLayout()
        right_column_layout.setSpacing(15)

        table_group = QGroupBox("Existing Rental Records")
        table_group.setStyleSheet(get_room_selection_style())
        table_layout = QVBoxLayout(table_group)

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
                
            if image_type == "photo":
                self.photo_path_label.setText(file_path)
            elif image_type == "nid_front":
                self.nid_front_path_label.setText(file_path)
            elif image_type == "nid_back":
                self.nid_back_path_label.setText(file_path)
            elif image_type == "police_form":
                self.police_form_path_label.setText(file_path)

    def save_rental_record(self):
        tenant_name = self.tenant_name_input.text().strip()
        room_number = self.room_number_input.text().strip()
        advanced_paid_text = self.advanced_paid_input.text().strip()
        
        if not tenant_name or not room_number:
            QMessageBox.warning(self, "Input Error", "Tenant Name and Room Number cannot be empty.")
            return

        try:
            advanced_paid = float(advanced_paid_text) if advanced_paid_text else 0.0
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Advanced Paid must be a valid number.")
            return

        photo_path = self.photo_path_label.text() if self.photo_path_label.text() != "No file selected" else ""
        nid_front_path = self.nid_front_path_label.text() if self.nid_front_path_label.text() != "No file selected" else ""
        nid_back_path = self.nid_back_path_label.text() if self.nid_back_path_label.text() != "No file selected" else ""
        police_form_path = self.police_form_path_label.text() if self.police_form_path_label.text() != "No file selected" else ""

        current_time = datetime.now().isoformat()

        try:
            if self.current_rental_id is not None:
                # Update existing record
                self.db_manager.execute_query(
                    """
                    UPDATE rentals SET
                        tenant_name = ?, room_number = ?, advanced_paid = ?,
                        photo_path = ?, nid_front_path = ?, nid_back_path = ?,
                        police_form_path = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (tenant_name, room_number, advanced_paid,
                     photo_path, nid_front_path, nid_back_path,
                     police_form_path, current_time, self.current_rental_id)
                )
                QMessageBox.information(self, "Success", "Rental record updated successfully!")
            else:
                # Insert new record
                self.db_manager.execute_query(
                    """
                    INSERT INTO rentals (tenant_name, room_number, advanced_paid, photo_path, nid_front_path, nid_back_path, police_form_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_name, room_number, advanced_paid, photo_path, nid_front_path, nid_back_path, police_form_path, current_time, current_time)
                )
                QMessageBox.information(self, "Success", "Rental record saved successfully!")
            
            self.load_rental_records()
            self.clear_form()
            # Removed automatic PDF generation after saving/updating the record, as per user feedback.
            # PDF generation will now be triggered by a dedicated button in the record details dialog.

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save rental record: {e}")
            traceback.print_exc()

    def load_rental_records(self):
        try:
            records = self.db_manager.execute_query("SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived FROM rentals WHERE is_archived = 0 ORDER BY created_at DESC", fetch_all=True)
            self.rental_records_table.clearContents() # Clear existing items and their data
            self.rental_records_table.setRowCount(len(records))
            for row_idx, record in enumerate(records):
                for col_idx, data in enumerate(record[:6]): # Display first 6 columns in table
                    item = QTableWidgetItem(str(data))
                    self.rental_records_table.setItem(row_idx, col_idx, item)
                # Store full paths in item data for later retrieval
                self.rental_records_table.item(row_idx, 0).setData(Qt.UserRole, record) # Store full record in ID item
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load rental records: {e}")
            traceback.print_exc()

    def show_record_details_dialog(self, index):
        selected_row = index.row()
        record = self.rental_records_table.item(selected_row, 0).data(Qt.UserRole)
        
        if record:
            # Pass is_archived status to the dialog
            is_archived = record[10] if len(record) > 10 else False
            dialog = RentalRecordDialog(self, record_data=record, db_manager=self.db_manager, is_archived_record=bool(is_archived), main_window_ref=self.main_window)
            dialog.exec_() # Show as modal dialog

    def load_record_into_form_for_edit(self, record_data):
        # This method is called from the dialog to load data for editing
        self.current_rental_id = record_data[0] # ID
        self.tenant_name_input.setText(record_data[1]) # Tenant Name
        self.room_number_input.setText(record_data[2]) # Room Number
        self.advanced_paid_input.setText(str(record_data[3])) # Advanced Paid

        self.photo_path_label.setText(record_data[6] if record_data[6] else "No file selected")
        self.nid_front_path_label.setText(record_data[7] if record_data[7] else "No file selected")
        self.nid_back_path_label.setText(record_data[8] if record_data[8] else "No file selected")
        self.police_form_path_label.setText(record_data[9] if record_data[9] else "No file selected")
        
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
        self.save_record_btn.setText("Save Record")

    def _handle_enter_pressed(self, current_index):
        """Handles Enter key press for sequential focus movement."""
        if current_index < len(self.input_fields) - 1:
            self.input_fields[current_index + 1].setFocus()
            if isinstance(self.input_fields[current_index + 1], QLineEdit):
                self.input_fields[current_index + 1].selectAll()
        else:
            # If it's the last input field, move focus to the Save Record button
            self.save_record_btn.setFocus()

    def eventFilter(self, obj, event):
        """Filters events to handle Up/Down arrow key navigation."""
        if event.type() == QEvent.KeyPress and obj in self.input_fields:
            current_index = self.input_fields.index(obj)
            if event.key() == Qt.Key_Down:
                if current_index < len(self.input_fields) - 1:
                    self.input_fields[current_index + 1].setFocus()
                    if isinstance(self.input_fields[current_index + 1], QLineEdit):
                        self.input_fields[current_index + 1].selectAll()
                    return True # Event handled
            elif event.key() == Qt.Key_Up:
                if current_index > 0:
                    self.input_fields[current_index - 1].setFocus()
                    if isinstance(self.input_fields[current_index - 1], QLineEdit):
                        self.input_fields[current_index - 1].selectAll()
                    return True # Event handled
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

    def _scale_image(self, image_path, max_width, max_height):
        if not image_path or not self._is_safe_path(image_path) or not os.path.exists(image_path):
            return None
        try:
            # Create a temporary Image object to get original dimensions
            temp_pixmap = QPixmap(image_path)
            if temp_pixmap.isNull():
                return None

            # Calculate scaling factor
            width = temp_pixmap.width()
            height = temp_pixmap.height()

            if width > max_width or height > max_height:
                aspect_ratio = width / height
                if width > height:
                    new_width = max_width
                    new_height = int(new_width / aspect_ratio)
                else:
                    new_height = max_height
                    new_width = int(new_height * aspect_ratio)
                return temp_pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return temp_pixmap
        except Exception as e:
            print(f"Error scaling image {image_path}: {e}")
            traceback.print_exc()
            return None

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
        pdf_filename = f"Rental_Record_{tenant_name.replace(' ', '_')}_{room_number.replace(' ', '_')}.pdf"
        pdf_path = os.path.join(os.path.expanduser("~/Documents"), pdf_filename)

        try:
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Custom style for centered bold text
            centered_bold_style = ParagraphStyle(
                'CenteredBold',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=12
            )

            elements = []

            # Title
            elements.append(Paragraph("Rental Information Record", centered_bold_style))
            elements.append(Spacer(1, 0.2 * inch))

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
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ])
            table = Table(data, colWidths=[2 * inch, 4 * inch])
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))

            # Document Images
            elements.append(Paragraph("<b>Associated Documents:</b>", styles['h3']))
            elements.append(Spacer(1, 0.1 * inch))

            image_paths = {
                "Tenant Photo": photo_path,
                "NID Front Side": nid_front_path,
                "NID Back Side": nid_back_path,
                "Police Verification Form": police_form_path
            }

            for title, path in image_paths.items():
                if path and os.path.exists(path) and self._is_safe_path(path):
                    elements.append(Paragraph(f"<b>{title}:</b>", styles['Normal']))
                    scaled_image = self._scale_image(path, 500, 500) # Max width/height for images
                    if scaled_image:
                        # Convert QPixmap to ReportLab Image
                        img_data = scaled_image.toImage().bits().asstring(scaled_image.toImage().byteCount())
                        img = Image(io.BytesIO(img_data), scaled_image.width(), scaled_image.height())
                        elements.append(img)
                        elements.append(Spacer(1, 0.1 * inch))
                    else:
                        elements.append(Paragraph(f"<i>Could not load image from {path}</i>", styles['Normal']))
                else:
                    elements.append(Paragraph(f"<i>{title}: Not provided or file not found/safe.</i>", styles['Normal']))
                elements.append(Spacer(1, 0.2 * inch))

            doc.build(elements)
            QMessageBox.information(self, "PDF Generated", f"Rental record PDF saved to:\n{pdf_path}")
            return True
        except Exception as e:
            QMessageBox.critical(self, "PDF Generation Error", f"Failed to generate PDF: {e}\n{traceback.format_exc()}")
            return False