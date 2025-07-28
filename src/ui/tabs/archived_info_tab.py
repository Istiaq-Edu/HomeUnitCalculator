# -*- coding: utf-8 -*-
import sys
import traceback
import os
from datetime import datetime
import logging

from PyQt5.QtCore import Qt, QRegExp, QTimer
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtGui import QIcon, QRegExpValidator, QPixmap
from src.core.utils import resource_path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QFormLayout, QMessageBox, QSizePolicy, QDialog,
    QFileDialog, QTableWidgetItem, QHeaderView, QAbstractItemView, QProgressDialog, QFrame
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, BaseDocTemplate, PageTemplate, Frame, NextPageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from qfluentwidgets import (
    CardWidget, ComboBox, TableWidget, TitleLabel, FluentIcon, setCustomStyleSheet
)

from src.ui.dialogs import RentalRecordDialog # Move to shared dialogs module
from src.ui.background_workers import FetchSupabaseRentalRecordsWorker
from src.ui.custom_widgets import FluentProgressDialog, SmoothTableWidget  # Avoid top-level import to keep optional
from src.ui.components import EnhancedTableMixin
# >>> ADD
# Optional Fluent-widgets progress bar (inline)
try:
    from qfluentwidgets import IndeterminateProgressBar  # type: ignore
except ImportError:
    IndeterminateProgressBar = None  # type: ignore
# <<< ADD

class ArchivedInfoTab(QWidget, EnhancedTableMixin):
    # Define priority columns for archive table
    PRIORITY_COLUMNS = {
        'archive_table': ['TENANT NAME', 'ROOM NUMBER', 'ADVANCED PAID']
    }
    
    # Define specific column icons for archive table
    COLUMN_ICONS = {
        'ID': FluentIcon.TAG,
        'TENANT_NAME': FluentIcon.PEOPLE,
        'TENANT NAME': FluentIcon.PEOPLE,
        'ROOM_NUMBER': FluentIcon.HOME,
        'ROOM NUMBER': FluentIcon.HOME,
        'ADVANCED_PAID': FluentIcon.ACCEPT_MEDIUM,
        'ADVANCED PAID': FluentIcon.ACCEPT_MEDIUM,
        'CREATED_AT': FluentIcon.CALENDAR,
        'CREATED AT': FluentIcon.CALENDAR,
        'UPDATED_AT': FluentIcon.CALENDAR,
        'UPDATED AT': FluentIcon.CALENDAR
    }
    
    # Font configuration matching History tab exactly
    FONT_SIZES = {
        'priority_columns': 12,
        'regular_columns': 10,
        'headers': 11
    }
    
    FONT_WEIGHTS = {
        'priority_columns': 600,
        'regular_columns': 500,
        'headers': 700
    }
    
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = self.main_window.db_manager

        self.archived_records_table = None
        # >>> ADD
        self._inline_progress_bar = None  # For inline cloud-fetch indicator
        # <<< ADD

        self.init_ui()
        self.load_archived_records()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        table_group = CardWidget()
        outer_table_layout = QVBoxLayout(table_group)
        outer_table_layout.setSpacing(8)
        outer_table_layout.setContentsMargins(12, 12, 12, 12)
        
        # Create title with FluentIcon to match history tab styling
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setPixmap(FluentIcon.DOCUMENT.icon().pixmap(20, 20))
        title_text = TitleLabel("Archived Rental Records")
        title_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_text.setWordWrap(True)
        title_text.setStyleSheet("font-weight: 600; font-size: 16px; color: #0969da; margin-bottom: 8px;")
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_text)
        title_layout.addStretch()
        outer_table_layout.addLayout(title_layout)
        
        # Add subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("QFrame { border: 1px solid #e1e4e8; margin: 8px 0; }")
        outer_table_layout.addWidget(divider)
        
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

        self.archived_records_table = SmoothTableWidget()
        
        # Use simple table header creation without icons
        archive_headers = ["Tenant Name", "Room Number", "Advanced Paid", "Created At", "Updated At"]
        self.archived_records_table.setColumnCount(len(archive_headers))
        self.archived_records_table.setHorizontalHeaderLabels(archive_headers)
        # self._set_table_headers_with_icons(self.archived_records_table, archive_headers, 'archive_table')  # Disabled - no icons
        
        # Apply History tab's exact table styling
        self._style_table(self.archived_records_table)
        
        self.archived_records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archived_records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.archived_records_table.clicked.connect(self.show_record_details_dialog)
        table_layout.addWidget(self.archived_records_table)
        
        main_layout.addWidget(table_group)
        self.setLayout(main_layout)

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

            # Create items using sophisticated History tab methods for enhanced visual hierarchy
            tenant_item = self._create_identifier_item(str(tenant_name), "tenant")
            room_item = self._create_identifier_item(str(room_number), "room")
            advanced_item = self._create_special_item(str(advanced_paid), "advanced_paid", is_priority=True)
            created_item = self._create_identifier_item(str(created_at), "date")
            updated_item = self._create_identifier_item(str(updated_at), "date")
            
            self.archived_records_table.setItem(row_idx, 0, tenant_item)
            self.archived_records_table.setItem(row_idx, 1, room_item)
            self.archived_records_table.setItem(row_idx, 2, advanced_item)
            self.archived_records_table.setItem(row_idx, 3, created_item)
            self.archived_records_table.setItem(row_idx, 4, updated_item)

            # Store full record data in the first column
            self.archived_records_table.item(row_idx, 0).setData(Qt.UserRole, full_record_data)
        
        # Apply intelligent column widths after populating data
        self._set_intelligent_column_widths(self.archived_records_table)

    def _set_intelligent_column_widths(self, table: SmoothTableWidget):
        """Set responsive column widths that adapt to window size while preventing truncation"""
        if table.columnCount() == 0:
            return
            
        # Set minimum column widths to prevent truncation
        min_widths = {}
        
        for col in range(table.columnCount()):
            header = table.horizontalHeaderItem(col)
            if not header:
                continue
                
            header_text = header.text().strip().lower()
            
            # Set minimum widths based on content type
            if "id" in header_text:
                min_widths[col] = 60   # ID column
            elif any(keyword in header_text for keyword in ["tenant", "name"]):
                min_widths[col] = 150  # Tenant names need more space
            elif any(keyword in header_text for keyword in ["room", "number"]):
                min_widths[col] = 100  # Room numbers
            elif any(keyword in header_text for keyword in ["advanced", "paid"]):
                min_widths[col] = 120  # Money values
            elif any(keyword in header_text for keyword in ["created", "updated"]):
                min_widths[col] = 130  # Dates
            else:
                min_widths[col] = 110  # Default
        
        # Calculate total minimum width needed
        total_min_width = sum(min_widths.values())
        available_width = table.viewport().width()
        
        # If total minimum width exceeds available space, use fixed widths with scrollbar
        if total_min_width > available_width:
            for col in range(table.columnCount()):
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                table.setColumnWidth(col, min_widths.get(col, 110))
        else:
            # Use stretch mode with minimum section sizes for responsiveness
            for col in range(table.columnCount()):
                header_text = table.horizontalHeaderItem(col).text().strip().lower() if table.horizontalHeaderItem(col) else ""
                
                # Tenant name column gets stretch behavior for responsiveness
                if any(keyword in header_text for keyword in ["tenant", "name"]):
                    table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
                else:
                    table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
                
                table.horizontalHeader().setMinimumSectionSize(min_widths.get(col, 110))
        
        # Always allow horizontal scrollbar when needed
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _on_table_resize(self, table: SmoothTableWidget):
        """Handle table resize events"""
        QTimer.singleShot(150, lambda: self._set_intelligent_column_widths(table))

    def _recalculate_all_table_widths(self):
        """Recalculate column widths for all tables"""
        try:
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                self._set_intelligent_column_widths(self.archived_records_table)
        except Exception as e:
            print(f"Could not recalculate table widths: {e}")

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
                self.main_window,  # Use main window as parent for proper centering
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

    def _style_table(self, table: SmoothTableWidget):
        """Apply History tab's exact table styling to match the UI design"""
        # Basic table properties matching History tab
        table.setBorderVisible(True)
        table.setBorderRadius(8)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setHighlightSections(False)
        table.verticalHeader().setDefaultSectionSize(35)  # Row height from History tab
        
        # Configure scroll behavior and selection with smooth scrolling
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Apply History tab's EXACT dark styling for consistent appearance
        light_qss = """
            QTableWidget {
                background-color: #ffffff;
                color: #212121;
                gridline-color: #e0e0e0;
                selection-background-color: #1976d2;
                alternate-background-color: #f8f9fa;
                border: 2px solid #d0d7de;
                border-radius: 12px;
                font-weight: 500;
                font-size: 11px;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f6f8fa, stop:1 #e1e4e8);
                color: #24292f;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-bottom: 3px solid #d0d7de;
                border-right: 1px solid #d0d7de;
                padding: 1px 0px;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            QHeaderView::section:first {
                border-left: none;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border: none;
                border-right: 1px solid #f0f0f0;
                text-align: center;
                /* DO NOT set font-weight here - let individual items control their own font weight */
            }
            QTableWidget::item:selected {
                background-color: #0969da;
                color: white;
                font-weight: 600;
                border-radius: 4px;
            }
            QTableWidget::item:hover {
                background-color: #e3f2fd;
                font-weight: 600;
            }
        """
        
        dark_qss = """
            QTableWidget {
                background-color: #21262d;
                color: #f0f6fc;
                gridline-color: #30363d;
                selection-background-color: #0969da;
                alternate-background-color: #161b22;
                border: 2px solid #30363d;
                border-radius: 12px;
                font-weight: 500;
                font-size: 11px;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #30363d, stop:1 #21262d);
                color: #f0f6fc;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-bottom: 3px solid #30363d;
                border-right: 1px solid #30363d;
                padding: 1px 0px;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 0.3px;
            }
            QHeaderView::section:first {
                border-left: none;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget::item {
                padding: 8px 12px;
                border: none;
                border-right: 1px solid #30363d;
                text-align: center;
                /* DO NOT set font-weight here - let individual items control their own font weight */
            }
            QTableWidget::item:selected {
                background-color: #0969da;
                color: white;
                font-weight: 600;
                border-radius: 4px;
            }
            QTableWidget::item:hover {
                background-color: #1c2128;
                font-weight: 600;
            }
        """
        
        setCustomStyleSheet(table, light_qss, dark_qss)
        
        # Configure header alignment
        table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        # Enable sorting
        table.setSortingEnabled(True)
        
        # Set minimum section size
        table.horizontalHeader().setMinimumSectionSize(80)

    def _apply_center_alignment(self, table: SmoothTableWidget):
        """Apply center alignment to all table cells"""
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item:
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)





    def _on_table_resize(self, table: SmoothTableWidget):
        """Handle table resize events"""
        QTimer.singleShot(150, lambda: self._set_intelligent_column_widths(table))

    def resizeEvent(self, event):
        """Handle widget resize events"""
        super().resizeEvent(event)
        QTimer.singleShot(200, lambda: self._set_intelligent_column_widths(self.archived_records_table))

    def _create_centered_item(self, text: str, column_name: str = "", is_priority: bool = False) -> QTableWidgetItem:
        """Create a table widget item with center alignment, number formatting, and priority-aware styling"""
        from PyQt5.QtGui import QColor, QBrush, QFont
        
        # Format numbers with thousand separators
        formatted_text = self._format_number(str(text)) if self._is_numeric_text(str(text)) else str(text)
        
        item = QTableWidgetItem(formatted_text)
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Apply priority-aware font sizing using class constants
        font = item.font()
        if is_priority:
            font.setPointSize(self.FONT_SIZES['priority_columns'])
            font.setWeight(self.FONT_WEIGHTS['priority_columns'])
        else:
            font.setPointSize(self.FONT_SIZES['regular_columns'])
            font.setWeight(self.FONT_WEIGHTS['regular_columns'])
        
        # Enhanced styling for numeric content
        if self._is_numeric_text(str(text)):
            if is_priority:
                font.setWeight(QFont.Bold)  # Bold for priority numbers
            else:
                font.setWeight(QFont.DemiBold)  # Semi-bold for regular numbers
        
        item.setFont(font)
        return item

    def _create_special_item(self, text: str, column_type: str, column_name: str = "", is_priority: bool = False) -> QTableWidgetItem:
        """Create a styled item for special columns with priority-aware formatting and enhanced Material Design colors"""
        from PyQt5.QtGui import QColor, QBrush, QFont
        from qfluentwidgets import isDarkTheme
        
        # Format numbers with thousand separators and add currency symbol for money columns
        formatted_text = str(text)
        if self._is_numeric_text(str(text)):
            formatted_text = self._format_number(str(text))
            # Add currency symbol for money-related columns
            if column_type in ["advanced_paid", "total_amount"] and formatted_text not in ["0.0", "0", ""]:
                formatted_text = f"৳{formatted_text}"
        
        # Enhanced color mapping with theme awareness
        if isDarkTheme():
            color_map = {
                "advanced_paid": "#66BB6A",     # Light Green for dark theme
                "total_amount": "#FF7043",      # Light Deep Orange 
                "tenant_name": "#4FC3F7",       # Light Cyan
                "room_number": "#FFA726",       # Light Orange
            }
        else:
            color_map = {
                "advanced_paid": "#2E7D32",     # Dark Green for light theme
                "total_amount": "#D84315",      # Dark Deep Orange 
                "tenant_name": "#1976D2",       # Material Blue
                "room_number": "#EF6C00",       # Dark Orange
            }
        
        item = QTableWidgetItem(formatted_text)
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Apply enhanced styling for special columns
        color = color_map.get(column_type, "#1976D2")  # Default Material Blue
        item.setForeground(QBrush(QColor(color)))
        
        # Priority-aware font sizing and styling
        font = item.font()
        font.setBold(True)
        font.setWeight(QFont.Bold)
        
        if is_priority:
            font.setPointSize(12)  # Priority columns: larger font
        else:
            font.setPointSize(10)  # Regular columns: smaller font
        
        item.setFont(font)
        return item
    
    def _create_identifier_item(self, text: str, identifier_type: str) -> QTableWidgetItem:
        """Create a styled item for identifier columns (Tenant Name, Dates) with modern styling"""
        from PyQt5.QtGui import QColor, QBrush, QFont
        from qfluentwidgets import isDarkTheme
        
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Enhanced styling for identifier columns
        if isDarkTheme():
            if identifier_type == "tenant":
                # Sophisticated blue for tenant names in dark theme
                item.setForeground(QBrush(QColor("#64B5F6")))  # Light blue
            elif identifier_type == "date":
                # Elegant gray for dates in dark theme
                item.setForeground(QBrush(QColor("#BDBDBD")))  # Light gray
            elif identifier_type == "room":
                # Elegant cyan for room identifiers in dark theme
                item.setForeground(QBrush(QColor("#4FC3F7")))  # Light cyan
        else:
            if identifier_type == "tenant":
                # Professional blue for tenant names in light theme
                item.setForeground(QBrush(QColor("#1976D2")))  # Material blue
            elif identifier_type == "date":
                # Subtle gray for dates in light theme
                item.setForeground(QBrush(QColor("#757575")))  # Medium gray
            elif identifier_type == "room":
                # Sophisticated teal for room identifiers in light theme
                item.setForeground(QBrush(QColor("#00796B")))  # Teal
        
        # Modern typography - semi-bold with elegant sizing
        font = item.font()
        font.setWeight(QFont.DemiBold)
        font.setPointSizeF(font.pointSizeF() + 1)  # Slightly larger for prominence
        item.setFont(font)
        
        return item

    def _format_number(self, text: str) -> str:
        """Format numbers with thousand separators and proper decimals"""
        if not text or text.lower() in ['n/a', '', 'unknown', '0', '0.0']:
            return text
        
        try:
            cleaned = str(text).replace(',', '').replace('TK', '').replace('৳', '').strip()
            if not cleaned:
                return text
            
            num = float(cleaned)
            
            if num == 0:
                return "0.0"
            elif num == int(num):
                return f"{int(num):,}.0"
            else:
                return f"{num:,.2f}"
                
        except (ValueError, TypeError):
            return text

    def _is_numeric_text(self, text: str) -> bool:
        """Check if text represents a numeric value"""
        if not text or text.lower() in ['n/a', '', 'unknown']:
            return False
        try:
            cleaned = text.replace(',', '').replace('TK', '').replace('৳', '').strip()
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False

    def _apply_accent_colors(self, table: TableWidget):
        """Apply additional styling"""
        pass

    def _recalculate_all_table_widths(self):
        """Recalculate column widths for all tables"""
        try:
            if hasattr(self, 'archived_records_table'):
                self._set_intelligent_column_widths(self.archived_records_table)
        except Exception as e:
            logging.warning(f"Could not recalculate table widths: {e}")

    def _enhance_headers_with_icons(self, table: TableWidget):
        """Add icons to table headers for better visual identification - DISABLED"""
        # Icons disabled per user request
        pass
        # from qfluentwidgets import FluentIcon
        # 
        # header_icons = {
        #     "id": FluentIcon.TAG,
        #     "tenant name": FluentIcon.PEOPLE,
        #     "room number": FluentIcon.HOME,
        #     "advanced paid": FluentIcon.MORE,
        #     "created at": FluentIcon.CALENDAR,
        #     "updated at": FluentIcon.CALENDAR
        # }
        #
        # for col in range(table.columnCount()):
        #     header = table.horizontalHeaderItem(col)
        #     if not header:
        #         continue
        #     
        #     header_text = header.text().strip().lower()
        #     
        #     # Find the corresponding icon
        #     icon = header_icons.get(header_text)
        #     
        #     if icon:
        #         header.setIcon(icon.icon())

    def _is_numeric_column(self, header_text: str) -> bool:
        """Check if a column header indicates numeric content"""
        numeric_indicators = [
            "advanced paid"
        ]
        header_lower = header_text.lower()
        return any(indicator in header_lower for indicator in numeric_indicators)

    def _format_number(self, text: str) -> str:
        """Format numbers with thousand separators and proper decimals"""
        if not text or text.lower() in ['n/a', '', 'unknown', '0', '0.0']:
            return text
        
        try:
            cleaned = str(text).replace(',', '').replace('TK', '').replace('\u09f3', '').strip()
            if not cleaned:
                return text
            
            num = float(cleaned)
            
            if num == 0:
                return "0.0"
            elif num == int(num):
                return f"{int(num):,}.0"
            else:
                return f"{num:,.2f}"
                
        except (ValueError, TypeError):
            return text

    def _is_numeric_text(self, text: str) -> bool:
        """Check if text represents a numeric value"""
        if not text or text.lower() in ['n/a', '', 'unknown']:
            return False
        try:
            cleaned = text.replace(',', '').replace('TK', '').replace('\u09f3', '').strip()
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False

    def resize_table_to_content(self, table):
        """Resize table height to fit all rows without scrolling"""
        if table.rowCount() == 0:
            # Set a reasonable minimum height instead of fixed height
            table.setMinimumHeight(table.horizontalHeader().height() + 10)
            table.setMaximumHeight(16777215)  # Remove height constraint
            return
        
        header_height = table.horizontalHeader().height()
        row_height = 0
        
        for row in range(table.rowCount()):
            row_height += table.rowHeight(row)
        
        total_height = header_height + row_height + 10
        
        # Set minimum height but allow expansion
        table.setMinimumHeight(total_height)
        table.setMaximumHeight(16777215)  # Remove height constraint
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)