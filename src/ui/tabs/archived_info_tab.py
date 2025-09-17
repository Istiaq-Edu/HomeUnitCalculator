# -*- coding: utf-8 -*-
import sys
import traceback
import os
import time
from datetime import datetime
import logging
from typing import Dict, Any, List

from PyQt5.QtCore import Qt, QRegExp, QTimer
from PyQt5.QtGui import QColor, QBrush, QFont, QFontMetrics
from PyQt5.QtGui import QIcon, QRegExpValidator, QPixmap
from src.core.utils import resource_path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGridLayout, QFormLayout, QMessageBox, QSizePolicy, QDialog,
    QFileDialog, QTableWidgetItem, QHeaderView, QAbstractItemView, QProgressDialog, QFrame,
    QTableWidget
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
from src.ui.components.table_optimization import (
    DebounceResizeManager,
    TableCacheManager,
    BatchUpdateManager,
    ResizeDebugManager
)
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

        # Debug configuration flags for production control
        self._resize_debug_enabled = False  # Can be enabled via configuration

        self.archived_records_table = None
        # >>> ADD
        self._inline_progress_bar = None  # For inline cloud-fetch indicator
        # <<< ADD

        self.init_ui()
        
        # Initialize optimization components after UI setup
        self._setup_optimization_components()
        
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
        
        # Configure table properties matching history tab strategy
        self.archived_records_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.archived_records_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.archived_records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.archived_records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.archived_records_table.clicked.connect(self.show_record_details_dialog)
        
        # Add table with stretch factor like history tab
        table_layout.addWidget(self.archived_records_table, 1)
        
        main_layout.addWidget(table_group)
        self.setLayout(main_layout)

    def load_archived_records(self):
        # Reset table first
        self.archived_records_table.clearContents()
        self.archived_records_table.setRowCount(0)
        
        # Invalidate cache when table content is cleared
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                self._cache_manager.invalidate_cache_for_table('archive_table')
        except Exception as e:
            print(f"Cache invalidation on table clear failed: {e}")

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

        # Invalidate cache when table content changes
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                self._cache_manager.invalidate_cache_for_table('archive_table')
        except Exception as e:
            print(f"Cache invalidation failed: {e}")

        # Use batch update manager for flicker-free table population
        batch_manager_used = False
        if hasattr(self, '_batch_manager') and self._batch_manager:
            try:
                self._batch_manager.begin_batch_update()
                batch_manager_used = True
            except Exception as e:
                print(f"Failed to start batch update: {e}")

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
        
        # Clean up batch update
        try:
            if batch_manager_used:
                self._batch_manager.end_batch_update()
        except Exception as e:
            print(f"Failed to complete batch update cleanup: {e}")
        
        # Apply intelligent column widths after populating data with delay to ensure table is fully rendered
        QTimer.singleShot(200, lambda: self._set_intelligent_column_widths(self.archived_records_table))
        
        # Also recalculate when tab becomes visible to fix initial sizing issues
        QTimer.singleShot(500, lambda: self._set_intelligent_column_widths(self.archived_records_table))

    def _set_intelligent_column_widths(self, table: SmoothTableWidget):
        """Set responsive column widths based on content and window size with advanced caching optimization"""
        if table.columnCount() == 0:
            return
        
        # Check if table is properly initialized
        available_width = table.viewport().width()
        if available_width <= 50:  # Minimum reasonable width
            # Table not ready yet, retry after a short delay
            QTimer.singleShot(100, lambda: self._set_intelligent_column_widths(table))
            return
        
        # Also check if table is visible and has reasonable size
        if not table.isVisible() or table.width() <= 50:
            # Table not properly shown yet, retry after delay
            QTimer.singleShot(100, lambda: self._set_intelligent_column_widths(table))
            return
        
        # Start timing for performance monitoring
        start_time = time.time() * 1000  # Convert to milliseconds
        
        try:
            # DISABLED: Cache can interfere with column distribution
            # Check for cached widths first using advanced cache manager
            if False and hasattr(self, '_cache_manager') and self._cache_manager:
                cache_key = self._cache_manager.generate_table_content_hash(table)
                cached_data = self._cache_manager.get_cached_content_width(cache_key)
                
                if cached_data and len(cached_data['column_widths']) == table.columnCount():
                    # Use cached widths if available and valid
                    self._apply_cached_column_widths(table, cached_data['column_widths'])
                    
                    if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                        self._debug_manager.log_cache_operation('content_width', 'get_cached_widths', True, 
                                                              {'cache_key': cache_key[:8], 'column_count': table.columnCount()})
                    return
                
                if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                    self._debug_manager.log_cache_operation('content_width', 'get_cached_widths', False,
                                                          {'cache_key': cache_key[:8], 'reason': 'cache_miss'})
        
        except Exception as e:
            print(f"Advanced cache lookup failed: {e}")
        
        header = table.horizontalHeader()
        
        # Ensure Qt isn't stretching the last section implicitly (from history tab)
        if header:
            header.setStretchLastSection(False)
        
        # Force geometry update first to get accurate measurements (from history tab)
        table.updateGeometry()
        
        # Calculate available width more accurately (from history tab)
        viewport_width = table.viewport().width()
        table_width = table.width()
        
        # Use the most reliable width measurement (from history tab)
        if viewport_width > 50:
            available_width = viewport_width
        elif table_width > 50:
            available_width = table_width - 50  # Account for potential scrollbars
        else:
            # Last resort - use parent width
            available_width = table.parent().width() - 50 if table.parent() else 500
        
        column_count = table.columnCount()
        
        # Debug: Print viewport width for troubleshooting
        self._log_resize_debug("Column width calculation started", {
            'viewport_width': viewport_width,
            'table_width': table_width,
            'available_width': available_width,
            'column_count': column_count
        })
        
        # Calculate content-based widths for each column with cached font metrics
        content_widths = {}
        total_min_width = 0
        
        for col in range(column_count):
            # Start with header text width
            header_item = table.horizontalHeaderItem(col)
            header_text = header_item.text() if header_item else ""
            
            # Use cached font metrics for performance
            font_metrics = self._get_cached_font_metrics_for_column(table, col, header_text)
            header_width = font_metrics.boundingRect(header_text).width() + 8  # Minimal padding
            
            # Check content width for sample rows (for performance)
            max_content_width = header_width
            sample_size = min(table.rowCount(), 100)  # Increased sample size but still limited
            for row in range(sample_size):
                item = table.item(row, col)
                if item:
                    content_text = item.text()
                    content_width = font_metrics.boundingRect(content_text).width() + 8  # Minimal padding
                    max_content_width = max(max_content_width, content_width)
            
            # Apply intelligent bounds based on column type (optimized to fit in viewport)
            header_lower = header_text.lower()
            if any(keyword in header_lower for keyword in ["tenant", "name"]):
                # Tenant name: allow more space for full names, min 200px
                content_widths[col] = max(max_content_width, 200)
            elif any(keyword in header_lower for keyword in ["room", "number"]):
                # Room number: compact, min 80px, max 100px
                content_widths[col] = max(80, min(max_content_width, 100))
            elif any(keyword in header_lower for keyword in ["advanced", "paid", "total", "cost", "bill", "amount"]):
                # Financial columns: moderate, min 100px, max 130px
                content_widths[col] = max(100, min(max_content_width, 130))
            elif any(keyword in header_lower for keyword in ["created", "updated"]):
                # Date columns: reasonable, min 110px, max 130px
                content_widths[col] = max(110, min(max_content_width, 130))
            else:
                # Default columns: standard bounds
                content_widths[col] = max(80, min(max_content_width, 150))
            
            total_min_width += content_widths[col]
        
        # Cache the calculated widths using advanced cache manager (before proportional distribution)
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                cache_key = self._cache_manager.generate_table_content_hash(table)
                column_widths_list = [content_widths[col] for col in range(column_count)]
                
                self._cache_manager.cache_content_width(
                    cache_key, 
                    column_widths_list, 
                    total_min_width, 
                    sample_size
                )
                
                # Update table content hash tracking
                self._cache_manager.update_table_content_hash('archive_table', table)
                
        except Exception as e:
            print(f"Failed to cache column widths: {e}")
        
        # HYBRID APPROACH: Stretch when content fits, scroll when it doesn't (like history tab)
        print(f"[ARCHIVED DEBUG] Available: {available_width}px")
        print(f"[ARCHIVED DEBUG] Content widths: {[content_widths[col] for col in range(column_count)]}")
        print(f"[ARCHIVED DEBUG] Total min width: {total_min_width}px")
        
        header = table.horizontalHeader()
        
        # Determine if content fits in available space
        content_fits = total_min_width <= (available_width - 30)  # 30px buffer for scrollbars
        print(f"[ARCHIVED DEBUG] Content fits: {content_fits} ({total_min_width} <= {available_width - 30})")
        
        if content_fits and available_width > 200:
            # Content fits - use STRETCH mode for equal distribution
            for col in range(column_count):
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            print(f"[ARCHIVED DEBUG] Applied STRETCH mode - content fits in {available_width}px")
        else:
            # Content doesn't fit - use FIXED mode with horizontal scrolling to prevent truncation
            for col in range(column_count):
                header.setSectionResizeMode(col, QHeaderView.Fixed)
                table.setColumnWidth(col, content_widths[col])
            
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            # Ensure horizontal scrollbar is visible when needed
            if hasattr(table, 'horizontalScrollBar') and table.horizontalScrollBar():
                table.horizontalScrollBar().setVisible(True)
            
            print(f"[ARCHIVED DEBUG] Applied FIXED mode with scrolling - total width {total_min_width}px")
        
        # Verify mode was applied
        for col in range(column_count):
            mode = header.sectionResizeMode(col)
            mode_name = {0: "Interactive", 1: "Fixed", 2: "Stretch", 3: "ResizeToContents"}.get(mode, f"Unknown({mode})")
            width = table.columnWidth(col) if mode == 1 else "auto"
            print(f"[ARCHIVED DEBUG] Column {col} ({table.horizontalHeaderItem(col).text() if table.horizontalHeaderItem(col) else 'N/A'}): {mode_name}, width: {width}")
        
        # Ensure table takes full width of its parent
        table.setMinimumWidth(0)
        table.setMaximumWidth(16777215)
        policy = table.sizePolicy()
        policy.setHorizontalPolicy(policy.Expanding)
        policy.setVerticalPolicy(policy.Expanding)
        table.setSizePolicy(policy)
        
        # Configure header settings
        if header:
            header.setStretchLastSection(False)  # Disable for consistent behavior
            header.setMinimumSectionSize(80)  # Minimum column width
        
        print(f"[ARCHIVED DEBUG] Table size policy and header configured")
        
        # Apply special styling to tenant name column
        self._apply_tenant_name_column_styling(table)
    
    def _ensure_stretch_mode(self, table):
        """Ensure all columns are in stretch mode - called with delay to override any conflicting settings"""
        try:
            header = table.horizontalHeader()
            if header and table.columnCount() > 0:
                print(f"[ARCHIVED DEBUG] Ensuring stretch mode for {table.columnCount()} columns")
                
                # Force all columns to stretch mode
                for col in range(table.columnCount()):
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                
                # Ensure stretch last section is enabled
                header.setStretchLastSection(True)
                
                # Disable horizontal scrolling
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                
                # Debug: Check what modes were actually set
                for col in range(table.columnCount()):
                    mode = header.sectionResizeMode(col)
                    mode_name = {0: "Interactive", 1: "Fixed", 2: "Stretch", 3: "ResizeToContents"}.get(mode, f"Unknown({mode})")
                    print(f"[ARCHIVED DEBUG] Column {col} mode after force: {mode_name}")
                    
        except Exception as e:
            print(f"[ARCHIVED DEBUG] Failed to ensure stretch mode: {e}")
    
    def _force_proportional_distribution(self, table):
        """Force proportional column distribution - called after data is loaded"""
        try:
            header = table.horizontalHeader()
            if not header or table.columnCount() == 0:
                return
                
            available_width = table.viewport().width()
            if available_width <= 200:
                return
                
            print(f"[ARCHIVED DEBUG] Forcing proportional distribution with viewport width: {available_width}px")
            
            # Define column weights
            column_weights = {}
            for col in range(table.columnCount()):
                header_item = table.horizontalHeaderItem(col)
                header_text = header_item.text() if header_item else ""
                header_lower = header_text.lower()
                
                if any(keyword in header_lower for keyword in ["tenant", "name"]):
                    column_weights[col] = 0.30
                elif any(keyword in header_lower for keyword in ["room", "number"]):
                    column_weights[col] = 0.15
                elif any(keyword in header_lower for keyword in ["advanced", "paid", "total", "cost", "bill", "amount"]):
                    column_weights[col] = 0.15
                elif any(keyword in header_lower for keyword in ["created", "updated"]):
                    column_weights[col] = 0.20
                else:
                    column_weights[col] = 0.20
            
            # Normalize weights
            total_weight = sum(column_weights.values())
            if total_weight > 0:
                for col in column_weights:
                    column_weights[col] = column_weights[col] / total_weight
            
            # First, ensure all columns are in Interactive mode
            for col in range(table.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.Interactive)
            
            # Disable stretch last section temporarily to allow manual sizing
            header.setStretchLastSection(False)
            
            # Apply proportional widths with more aggressive approach
            print(f"[ARCHIVED DEBUG] Applying proportional widths:")
            for col in range(table.columnCount()):
                weight = column_weights.get(col, 1.0 / table.columnCount())
                proportional_width = int(available_width * weight)
                min_width = max(60, proportional_width)
                
                # Get current width for comparison
                current_width = table.columnWidth(col)
                
                # Try multiple methods to set the width
                header.resizeSection(col, min_width)
                table.setColumnWidth(col, min_width)
                
                # Verify the width was set
                new_width = table.columnWidth(col)
                header_item = table.horizontalHeaderItem(col)
                header_text = header_item.text() if header_item else f"Col {col}"
                
                print(f"[ARCHIVED DEBUG]   {header_text}: {current_width}px -> {new_width}px (target: {min_width}px, weight: {weight:.2f})")
            
            # Re-enable stretch last section for edge alignment
            header.setStretchLastSection(True)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            print(f"[ARCHIVED DEBUG] Forced proportional distribution with weights: {column_weights}")
            
        except Exception as e:
            print(f"[ARCHIVED DEBUG] Failed to force proportional distribution: {e}")
    
    def _apply_tenant_name_column_styling(self, table: SmoothTableWidget):
        """Apply special styling to the tenant name column for better visual distinction (matching month column style)"""
        if table.columnCount() == 0:
            return
        
        # Find the tenant name column
        tenant_col = -1
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            if header_item and any(keyword in header_item.text().lower() for keyword in ["tenant", "name"]):
                tenant_col = col
                break
        
        if tenant_col == -1:
            return  # No tenant name column found
        
        from PyQt5.QtGui import QColor, QBrush, QFont
        from qfluentwidgets import isDarkTheme
        
        # Style the header to match month column
        header_item = table.horizontalHeaderItem(tenant_col)
        if header_item:
            font = header_item.font()
            font.setBold(True)
            font.setPointSize(13)  # Slightly larger for tenant name header
            header_item.setFont(font)
        
        # Style all tenant name column cells with distinct background (matching month column exactly)
        for row in range(table.rowCount()):
            item = table.item(row, tenant_col)
            if item:
                # Apply distinct styling matching month column
                font = item.font()
                font.setBold(True)
                font.setPointSize(11)
                item.setFont(font)
                
                # Apply theme-aware background color matching month column exactly
                if isDarkTheme():
                    item.setBackground(QBrush(QColor(45, 55, 75)))  # Darker blue background (same as month)
                    item.setForeground(QBrush(QColor(220, 230, 255)))  # Light blue text (same as month)
                else:
                    item.setBackground(QBrush(QColor(230, 240, 255)))  # Light blue background (same as month)
                    item.setForeground(QBrush(QColor(25, 50, 100)))  # Dark blue text (same as month)

    def _get_cached_font_metrics_for_column(self, table: SmoothTableWidget, col: int, header_text: str):
        """Get cached font metrics for a specific column with priority-aware font configuration"""
        try:
            # Determine if this is a priority column
            is_priority = self._is_priority_column('archive_table', header_text)
            
            # Get font configuration based on priority
            if is_priority:
                font_size = self.FONT_SIZES['priority_columns']
                font_weight = self.FONT_WEIGHTS['priority_columns']
            else:
                font_size = self.FONT_SIZES['regular_columns']
                font_weight = self.FONT_WEIGHTS['regular_columns']
            
            # Generate font cache key
            font_key = f"archive_font_{font_size}_{font_weight}"
            
            # Try to get cached font metrics
            if hasattr(self, '_cache_manager') and self._cache_manager:
                cached_metrics = self._cache_manager.get_cached_font_metrics(font_key)
                if cached_metrics:
                    if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                        self._debug_manager.log_cache_operation('font_metrics', 'get_cached_metrics', True,
                                                              {'font_key': font_key, 'column': col})
                    return cached_metrics['metrics']
            
            # Cache miss - create new font and metrics
            from PyQt5.QtGui import QFont, QFontMetrics
            font = QFont()
            font.setPointSize(font_size)
            font.setWeight(font_weight)
            metrics = QFontMetrics(font)
            
            # Cache the new font metrics
            if hasattr(self, '_cache_manager') and self._cache_manager:
                self._cache_manager.cache_font_metrics(font_key, font, metrics)
                
                if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                    self._debug_manager.log_cache_operation('font_metrics', 'cache_new_metrics', False,
                                                          {'font_key': font_key, 'column': col})
            
            return metrics
            
        except Exception as e:
            print(f"Font metrics caching failed: {e}")
            # Fallback to basic font metrics
            header_item = table.horizontalHeaderItem(col)
            if header_item:
                return QFontMetrics(header_item.font())
            else:
                return QFontMetrics(table.font())
    
    def _is_priority_column(self, table_type: str, column_name: str) -> bool:
        """Check if a column is priority based on table type and column name"""
        priority_columns = self.PRIORITY_COLUMNS.get(table_type, [])
        return column_name.upper() in [col.upper() for col in priority_columns]
    
    def _invalidate_table_cache_on_data_change(self):
        """Invalidate table cache when data changes - call this after data updates"""
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager and hasattr(self, 'archived_records_table'):
                self._cache_manager.invalidate_cache_for_table('archive_table')
                
                if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                    self._debug_manager.log_cache_operation('cache_invalidation', 'data_change', True,
                                                          {'table': 'archive_table', 'reason': 'data_update'})
        except Exception as e:
            print(f"Cache invalidation failed: {e}")
    
    def _log_resize_debug(self, operation: str, details: Dict[str, Any] = None, duration: float = None):
        """
        Log resize debug information with configurable output.
        
        Args:
            operation: Name/description of the resize operation
            details: Optional dictionary of operation details
            duration: Optional operation duration in milliseconds
        """
        # Check if debug logging is enabled
        if not self._resize_debug_enabled:
            return
            
        try:
            # Log to debug manager if available
            if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                if duration is not None:
                    self._debug_manager.log_resize_operation(operation, duration, details)
                else:
                    # Log as general debug info
                    print(f"[ARCHIVED DEBUG] {operation}")
                    if details:
                        for key, value in details.items():
                            print(f"  {key}: {value}")
            
            # Always log to console if debug enabled (for immediate feedback)
            elif self._resize_debug_enabled:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                if duration is not None:
                    status = "SLOW" if duration > 100 else "OK"
                    print(f"[{timestamp}] ARCHIVED RESIZE: {operation} - {duration:.2f}ms [{status}]")
                else:
                    print(f"[{timestamp}] ARCHIVED DEBUG: {operation}")
                
                if details:
                    for key, value in details.items():
                        print(f"  {key}: {value}")
                        
        except Exception as e:
            # Don't let debug logging break the application
            print(f"Debug logging error: {e}")

    def _get_cache_performance_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics for monitoring"""
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                stats = self._cache_manager.get_cache_statistics()
                
                # Add table-specific information
                stats['table_info'] = {
                    'table_type': 'archive_table',
                    'current_row_count': self.archived_records_table.rowCount() if hasattr(self, 'archived_records_table') and self.archived_records_table else 0,
                    'current_column_count': self.archived_records_table.columnCount() if hasattr(self, 'archived_records_table') and self.archived_records_table else 0
                }
                
                return stats
            else:
                return {'error': 'Cache manager not initialized'}
        except Exception as e:
            return {'error': f'Failed to get cache statistics: {e}'}
    
    def print_cache_performance_report(self):
        """Print a detailed cache performance report for debugging"""
        try:
            stats = self._get_cache_performance_statistics()
            
            if 'error' in stats:
                print(f"Cache Statistics Error: {stats['error']}")
                return
            
            print("\n=== ARCHIVED TAB CACHE PERFORMANCE REPORT ===")
            print(f"Table: {stats.get('table_info', {}).get('table_type', 'unknown')}")
            print(f"Rows: {stats.get('table_info', {}).get('current_row_count', 0)}")
            print(f"Columns: {stats.get('table_info', {}).get('current_column_count', 0)}")
            
            # Font metrics cache stats
            font_stats = stats.get('font_metrics', {})
            print(f"\nFont Metrics Cache:")
            print(f"  Hit Ratio: {font_stats.get('hit_ratio', 0):.2%}")
            print(f"  Hits: {font_stats.get('hits', 0)}")
            print(f"  Misses: {font_stats.get('misses', 0)}")
            
            # Content width cache stats
            content_stats = stats.get('content_width', {})
            print(f"\nContent Width Cache:")
            print(f"  Hit Ratio: {content_stats.get('hit_ratio', 0):.2%}")
            print(f"  Hits: {content_stats.get('hits', 0)}")
            print(f"  Misses: {content_stats.get('misses', 0)}")
            
            # Cache sizes
            cache_sizes = stats.get('cache_sizes', {})
            print(f"\nCache Sizes:")
            print(f"  Font Metrics: {cache_sizes.get('font_metrics', 0)} entries")
            print(f"  Content Width: {cache_sizes.get('content_width', 0)} entries")
            print(f"  Table Hashes: {cache_sizes.get('table_hashes', 0)} entries")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"Failed to print cache performance report: {e}")
    
    def debug_column_width_distribution(self):
        """Debug method to check current column width distribution"""
        try:
            if not hasattr(self, 'archived_records_table') or not self.archived_records_table:
                print("No archived records table available for debugging")
                return
            
            table = self.archived_records_table
            print("\n=== ARCHIVED TAB COLUMN WIDTH DEBUG ===")
            
            # Get current table info
            viewport_width = table.viewport().width()
            column_count = table.columnCount()
            
            print(f"Viewport width: {viewport_width}px")
            print(f"Column count: {column_count}")
            
            # Get current column widths
            current_widths = [table.columnWidth(col) for col in range(column_count)]
            current_total = sum(current_widths)
            
            print(f"Current column widths: {current_widths}")
            print(f"Current total width: {current_total}px")
            print(f"Viewport fill ratio: {current_total/viewport_width*100:.1f}%")
            
            # Get header resize modes
            header = table.horizontalHeader()
            resize_modes = []
            for col in range(column_count):
                mode = header.sectionResizeMode(col)
                mode_name = {
                    0: "Interactive",
                    1: "Fixed", 
                    2: "Stretch",
                    3: "ResizeToContents"
                }.get(mode, f"Unknown({mode})")
                resize_modes.append(mode_name)
            
            print(f"Resize modes: {resize_modes}")
            
            # Check scrollbar policy
            h_policy = table.horizontalScrollBarPolicy()
            policy_name = {
                0: "AsNeeded",
                1: "AlwaysOff", 
                2: "AlwaysOn"
            }.get(h_policy, f"Unknown({h_policy})")
            
            print(f"Horizontal scrollbar policy: {policy_name}")
            
            # Recommendations
            if current_total < viewport_width * 0.95:
                print("⚠️  Columns don't fill viewport - consider using stretch mode for last column")
            else:
                print("✅ Columns properly fill the viewport")
            
            print("=" * 50)
            
        except Exception as e:
            print(f"Failed to debug column width distribution: {e}")
    
    def _apply_cached_column_widths(self, table: SmoothTableWidget, column_widths: List[int]):
        """Apply cached column widths to table with improved proportional distribution"""
        try:
            header = table.horizontalHeader()
            available_width = table.viewport().width()
            column_count = len(column_widths)
            
            print(f"[ARCHIVED DEBUG] Applying cached widths with hybrid approach")
            
            # Use HYBRID approach consistent with main method
            total_cached_width = sum(column_widths)
            content_fits = total_cached_width <= (available_width - 30)  # 30px buffer for safety
            
            if content_fits and available_width > 200:
                # Content fits: Use STRETCH mode for all columns
                for col in range(column_count):
                    if col < table.columnCount():
                        header.setSectionResizeMode(col, QHeaderView.Stretch)
                
                # Disable horizontal scrollbar since content fits
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                
            else:
                # Content doesn't fit: Use FIXED mode with scrolling
                for col, width in enumerate(column_widths):
                    if col < table.columnCount():
                        header.setSectionResizeMode(col, QHeaderView.Fixed)
                        table.setColumnWidth(col, width)
                
                # Enable horizontal scrolling when needed
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # Ensure table takes full width of its parent
            table.setMinimumWidth(0)
            table.setMaximumWidth(16777215)
            policy = table.sizePolicy()
            policy.setHorizontalPolicy(policy.Expanding)
            policy.setVerticalPolicy(policy.Expanding)
            table.setSizePolicy(policy)
            
            # Configure stretch last section based on mode
            if content_fits:
                header.setStretchLastSection(True)   # Enable for stretch mode
            else:
                header.setStretchLastSection(False)  # Disable for fixed mode
            
            # Apply special styling to tenant name column
            self._apply_tenant_name_column_styling(table)
            
        except Exception as e:
            print(f"Failed to apply cached column widths: {e}")
            # Fallback to recalculation
            self._set_intelligent_column_widths(table)

    def _on_table_resize(self, table: SmoothTableWidget):
        """Handle table resize events"""
        QTimer.singleShot(150, lambda: self._set_intelligent_column_widths(table))



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
                padding: 0px 1px;
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
                padding: 0px 1px;
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
                padding: 0px 1px;
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
                padding: 0px 1px;
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
        
        # Configure header alignment and stretching for proper window edge alignment
        header = table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setStretchLastSection(True)  # Fix: Enable stretch last section for proper edge alignment
        
        # Enable sorting
        table.setSortingEnabled(True)
        
        # Set minimum section size
        header.setMinimumSectionSize(80)

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
        """Handle widget resize events - directly recalculate column widths"""
        super().resizeEvent(event)
        # Since table optimization is disabled, directly call our column width method
        if hasattr(self, 'archived_records_table') and self.archived_records_table:
            QTimer.singleShot(200, lambda: self._set_intelligent_column_widths(self.archived_records_table))
    
    def showEvent(self, event):
        """Handle tab becoming visible - directly recalculate column widths"""
        try:
            super().showEvent(event)
            
            # Since table optimization is disabled, directly call our column width method
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                QTimer.singleShot(100, lambda: self._set_intelligent_column_widths(self.archived_records_table))
                # Additional recalculation to ensure proper sizing
                QTimer.singleShot(300, lambda: self._set_intelligent_column_widths(self.archived_records_table))
        except Exception as e:
            logging.warning(f"Error in showEvent: {e}")

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
        """Recalculate column widths for all tables using batched updates and caching"""
        try:
            # Use batch update manager for flicker-free recalculation
            if hasattr(self, '_batch_manager') and self._batch_manager and hasattr(self, 'archived_records_table') and self.archived_records_table:
                try:
                    self._batch_manager.begin_batch_update()
                    self._set_intelligent_column_widths(self.archived_records_table)
                    return True
                except Exception as e:
                    logging.warning(f"Batched table width recalculation failed: {e}")
                    return False
                finally:
                    self._batch_manager.end_batch_update()
            else:
                # Fallback to direct method if batch manager not available
                if hasattr(self, 'archived_records_table') and self.archived_records_table:
                    self._set_intelligent_column_widths(self.archived_records_table)
                    return True
        except Exception as e:
            logging.warning(f"Could not recalculate table widths: {e}")
            return False

    # ===== OPTIMIZATION METHODS =====
    
    def _setup_optimization_components(self):
        """Initialize optimization components with comprehensive error handling and fallback mechanisms"""
        try:
            # Import the new optimization component manager
            from src.ui.components.table_optimization import OptimizationComponentManager
            
            # Initialize the comprehensive optimization manager
            self._optimization_manager = OptimizationComponentManager(self)
            
            # Setup table optimization for archived records table
            QTimer.singleShot(100, self._setup_table_optimizations)
            
            # Store references for backward compatibility
            self._debounce_manager = self._optimization_manager.debounce_manager
            self._cache_manager = self._optimization_manager.cache_manager
            self._debug_manager = self._optimization_manager.debug_manager
            
            # Connect debounce signal
            if self._debounce_manager:
                self._debounce_manager.resize_requested.connect(self._perform_debounced_resize)
            
        except Exception as e:
            print(f"Warning: Could not initialize optimization components: {e}")
            # Initialize fallback components
            self._setup_fallback_optimization()

    def _setup_fallback_optimization(self):
        """Setup basic fallback optimization when advanced components fail"""
        try:
            from src.ui.components.table_optimization import (
                OptimizationConfig, OptimizationErrorHandler, FallbackResizeManager
            )
            
            # Create basic configuration and error handler
            self._config = OptimizationConfig()
            self._config.disable_all_optimizations()  # Use fallback mode
            self._error_handler = OptimizationErrorHandler(self._config)
            
            # Create fallback manager
            self._fallback_manager = FallbackResizeManager(self)
            
            # Set components to None to indicate fallback mode
            self._optimization_manager = None
            self._debounce_manager = None
            self._cache_manager = None
            self._debug_manager = None
            
        except Exception as e:
            print(f"Critical: Could not initialize fallback optimization: {e}")
            # Absolute fallback - no optimization components
            self._optimization_manager = None
            self._debounce_manager = None
            self._cache_manager = None
            self._debug_manager = None
            self._fallback_manager = None

    def _setup_table_optimizations(self):
        """Setup optimization for specific tables with error handling"""
        try:
            # DISABLED: Table optimization interferes with our column width management
            # The optimization system forces ResizeToContents mode which overrides our
            # carefully set STRETCH/FIXED modes for proper column distribution
            print("Table optimization disabled to prevent column width interference")
            return
            
            if not self._optimization_manager:
                return
            
            # Setup optimization for archived records table
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                self._optimization_manager.setup_table_optimization(
                    self.archived_records_table, 
                    'archive_table'
                )
            
            # Setup resize debouncing
            self._setup_resize_debouncing()
            
        except Exception as e:
            print(f"Warning: Could not setup table optimizations: {e}")
            # Try fallback setup
            self._setup_fallback_table_optimization()

    def _setup_resize_debouncing(self):
        """Initialize debounced resize system and consolidate resize handlers with error handling"""
        try:
            if not self._optimization_manager or not self._debounce_manager:
                # Use fallback resize setup
                self._setup_fallback_resize_handling()
                return
                
            # Consolidate all resize event sources
            self._consolidate_resize_handlers()
            
            # Batch managers are now handled by the optimization manager
            # Store reference for backward compatibility
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                batch_managers = self._optimization_manager.batch_managers
                self._archived_batch_manager = batch_managers.get('archive_table')
            
        except Exception as e:
            print(f"Warning: Could not setup resize debouncing: {e}")
            # Try fallback resize handling
            self._setup_fallback_resize_handling()

    def _setup_fallback_resize_handling(self):
        """Setup basic resize handling when optimization components fail"""
        try:
            if hasattr(self, '_fallback_manager') and self._fallback_manager:
                # Setup basic table properties
                if hasattr(self, 'archived_records_table') and self.archived_records_table:
                    self._fallback_manager.perform_basic_table_setup(self.archived_records_table)
            
        except Exception as e:
            print(f"Warning: Fallback resize setup failed: {e}")

    def _setup_fallback_table_optimization(self):
        """Setup fallback table optimization when main optimization fails"""
        try:
            if hasattr(self, '_fallback_manager') and self._fallback_manager:
                if hasattr(self, 'archived_records_table') and self.archived_records_table:
                    self._fallback_manager.perform_basic_table_setup(self.archived_records_table)
                    
        except Exception as e:
            print(f"Warning: Fallback table optimization failed: {e}")

    def _perform_debounced_resize(self):
        """Execute the actual resize operation with comprehensive error handling and fallback mechanisms"""
        try:
            start_time = time.time() * 1000 if hasattr(self, '_debug_manager') and self._debug_manager else None
            
            # Check if optimization manager is available
            if self._optimization_manager and not self._optimization_manager.error_handler.is_fallback_active():
                # Use optimized resize path
                self._perform_optimized_resize()
            else:
                # Use fallback resize path
                self._perform_fallback_resize()
                
            # Log performance if debug enabled
            if start_time and hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                duration = (time.time() * 1000) - start_time
                self._debug_manager.log_resize_operation("debounced_resize", duration)
                
        except Exception as e:
            print(f"Error during debounced resize: {e}")
            # Last resort fallback
            self._emergency_resize_fallback()

    def _perform_optimized_resize(self):
        """Perform optimized resize using the optimization manager"""
        try:
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                self._optimization_manager.safe_resize_table(
                    self.archived_records_table, 
                    'archive_table'
                )
            
        except Exception as e:
            # Let optimization manager handle the error
            if self._optimization_manager:
                should_retry = self._optimization_manager.error_handler.handle_error(
                    'perform_optimized_resize', e, {'table': 'archive_table'}
                )
                if not should_retry:
                    self._perform_fallback_resize()
            else:
                raise e

    def _perform_fallback_resize(self):
        """Perform fallback resize using basic mechanisms"""
        try:
            if hasattr(self, '_fallback_manager') and self._fallback_manager:
                if hasattr(self, 'archived_records_table') and self.archived_records_table:
                    self._fallback_manager.perform_basic_resize(self.archived_records_table)
            else:
                # Direct fallback to original method
                self._recalculate_all_table_widths()
                
        except Exception as e:
            print(f"Fallback resize failed: {e}")
            # Try emergency fallback
            self._emergency_resize_fallback()

    def _emergency_resize_fallback(self):
        """Emergency resize fallback when all other methods fail"""
        try:
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                # Use stretch mode for consistent behavior even in emergency fallback
                header = self.archived_records_table.horizontalHeader()
                for col in range(self.archived_records_table.columnCount()):
                    try:
                        header.setSectionResizeMode(col, QHeaderView.Stretch)
                    except Exception:
                        pass  # Continue with other columns
                
                # Ensure stretch last section is enabled
                try:
                    header.setStretchLastSection(True)
                    self.archived_records_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                except Exception:
                    pass
                        
        except Exception as e:
            print(f"Emergency resize fallback failed: {e}")
            # At this point, we've exhausted all options

    # ===== ERROR HANDLING AND CONFIGURATION METHODS =====
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive status of optimization components for monitoring and debugging"""
        try:
            if self._optimization_manager:
                return self._optimization_manager.get_optimization_status()
            else:
                return {
                    'status': 'fallback_mode',
                    'optimization_manager': False,
                    'fallback_manager': hasattr(self, '_fallback_manager') and self._fallback_manager is not None,
                    'error': 'Optimization manager not initialized'
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def enable_optimization_safe_mode(self):
        """Enable safe mode with minimal optimizations for troubleshooting"""
        try:
            if self._optimization_manager:
                self._optimization_manager.enable_safe_mode()
                print("[ARCHIVED TAB] Optimization safe mode enabled")
            else:
                print("[ARCHIVED TAB] Cannot enable safe mode - optimization manager not available")
        except Exception as e:
            print(f"[ARCHIVED TAB] Failed to enable safe mode: {e}")
    
    def disable_all_optimizations(self):
        """Disable all optimizations and use fallback mode"""
        try:
            if self._optimization_manager:
                self._optimization_manager.disable_all_optimizations()
                print("[ARCHIVED TAB] All optimizations disabled")
            else:
                print("[ARCHIVED TAB] Optimizations already disabled")
        except Exception as e:
            print(f"[ARCHIVED TAB] Failed to disable optimizations: {e}")
    
    def reset_optimization_state(self):
        """Reset optimization state and clear errors for recovery"""
        try:
            if self._optimization_manager:
                self._optimization_manager.reset_optimization_state()
                print("[ARCHIVED TAB] Optimization state reset")
            else:
                # Try to reinitialize optimization components
                self._setup_optimization_components()
                print("[ARCHIVED TAB] Attempted to reinitialize optimization components")
        except Exception as e:
            print(f"[ARCHIVED TAB] Failed to reset optimization state: {e}")
    
    def print_optimization_report(self):
        """Print detailed optimization performance and error report for debugging"""
        try:
            status = self.get_optimization_status()
            
            print("\n=== ARCHIVED TAB OPTIMIZATION REPORT ===")
            print(f"Status: {status.get('status', 'unknown')}")
            
            if 'config' in status:
                config = status['config']
                print(f"Debounced Resize: {'Enabled' if config.get('enable_debounced_resize') else 'Disabled'}")
                print(f"Caching: {'Enabled' if config.get('enable_caching') else 'Disabled'}")
                print(f"Batch Updates: {'Enabled' if config.get('enable_batch_updates') else 'Disabled'}")
                print(f"Debug Logging: {'Enabled' if config.get('enable_debug_logging') else 'Disabled'}")
            
            if 'error_summary' in status:
                error_summary = status['error_summary']
                print(f"Total Errors: {error_summary.get('total_errors', 0)}")
                print(f"Fallback Active: {error_summary.get('fallback_active', False)}")
                
                if error_summary.get('recent_errors'):
                    print("Recent Errors:")
                    for error in error_summary['recent_errors'][-3:]:  # Last 3 errors
                        print(f"  - {error.get('operation', 'unknown')}: {error.get('error_message', 'unknown')}")
            
            print("=" * 47)
            
        except Exception as e:
            print(f"Failed to print optimization report: {e}")
    
    def force_column_width_refresh(self):
        """Force refresh of column widths to ensure they stick to the window"""
        try:
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                # Clear any cached widths to force recalculation
                if hasattr(self, '_cache_manager') and self._cache_manager:
                    self._cache_manager.invalidate_cache_for_table('archive_table')
                
                # Force immediate recalculation with multiple attempts
                def attempt_resize(attempt=1):
                    try:
                        viewport_width = self.archived_records_table.viewport().width()
                        print(f"[ARCHIVED FORCE REFRESH] Attempt {attempt}: Viewport width = {viewport_width}px")
                        
                        if viewport_width > 50:
                            self._set_intelligent_column_widths(self.archived_records_table)
                            print(f"[ARCHIVED FORCE REFRESH] Success on attempt {attempt}")
                        elif attempt < 5:
                            # Retry with increasing delay
                            QTimer.singleShot(attempt * 100, lambda: attempt_resize(attempt + 1))
                        else:
                            print(f"[ARCHIVED FORCE REFRESH] Failed after {attempt} attempts")
                    except Exception as e:
                        print(f"[ARCHIVED FORCE REFRESH] Error on attempt {attempt}: {e}")
                
                attempt_resize()
                
        except Exception as e:
            print(f"Failed to force column width refresh: {e}")
            try:
                self._recalculate_all_table_widths()
            except Exception as fallback_error:
                print(f"Fallback resize also failed: {fallback_error}")

    def _consolidate_resize_handlers(self):
        """Unify all resize event sources to route through debounced system"""
        try:
            # Override any existing resize handlers to use debounced system
            # This ensures all resize events (resizeEvent, showEvent, etc.) use the same path
            
            # Store original showEvent if it exists
            if hasattr(self, 'showEvent'):
                self._original_showEvent = self.showEvent
            
            # Replace showEvent to trigger debounced resize
            def optimized_showEvent(event):
                if hasattr(self, '_original_showEvent'):
                    self._original_showEvent(event)
                else:
                    super(ArchivedInfoTab, self).showEvent(event)
                    
                # Trigger optimized initial table sizing
                if hasattr(self, '_debounce_manager') and self._debounce_manager:
                    QTimer.singleShot(100, self._debounce_manager.trigger_debounced_resize)
                    
            self.showEvent = optimized_showEvent
            
            # Ensure table resize handlers also use debounced system
            if hasattr(self, 'archived_records_table') and self.archived_records_table:
                # Override any existing table resize handlers
                def optimized_table_resize():
                    if hasattr(self, '_debounce_manager') and self._debounce_manager:
                        self._debounce_manager.trigger_debounced_resize()
                        
                # Replace any existing table resize connections
                try:
                    # Disconnect existing connections if any
                    self.archived_records_table.horizontalHeader().sectionResized.disconnect()
                except:
                    pass
                    
                # Connect to debounced system
                self.archived_records_table.horizontalHeader().sectionResized.connect(
                    lambda: QTimer.singleShot(50, optimized_table_resize)
                )
                
        except Exception as e:
            print(f"Warning: Could not consolidate resize handlers: {e}")

    def _generate_table_cache_key(self, table: QTableWidget) -> str:
        """Generate a cache key based on table content for width caching"""
        try:
            # Create a hash based on table structure and sample content
            content_parts = []
            
            # Add column headers
            for col in range(table.columnCount()):
                header_item = table.horizontalHeaderItem(col)
                if header_item:
                    content_parts.append(header_item.text())
            
            # Add sample content from first few rows
            sample_rows = min(5, table.rowCount())
            for row in range(sample_rows):
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item:
                        content_parts.append(item.text())
            
            # Create hash
            import hashlib
            content_str = "|".join(content_parts)
            return hashlib.md5(content_str.encode()).hexdigest()
            
        except Exception as e:
            print(f"Warning: Could not generate cache key: {e}")
            return f"fallback_{table.rowCount()}_{table.columnCount()}"

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
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report for optimization analysis.
        
        Returns:
            Dictionary containing performance metrics, cache statistics, and recommendations
        """
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'tab_name': 'archived_info_tab',
                'debug_enabled': self._resize_debug_enabled,
                'optimization_status': {},
                'cache_performance': {},
                'debug_statistics': {},
                'recommendations': []
            }
            
            # Get optimization manager status
            if hasattr(self, '_optimization_manager') and self._optimization_manager:
                report['optimization_status'] = self._optimization_manager.get_optimization_status()
            
            # Get cache performance statistics
            report['cache_performance'] = self._get_cache_performance_statistics()
            
            # Get debug manager statistics
            if hasattr(self, '_debug_manager') and self._debug_manager:
                report['debug_statistics'] = self._debug_manager.get_performance_report()
            
            # Add table-specific metrics
            if self.archived_records_table:
                report['table_metrics'] = {
                    'row_count': self.archived_records_table.rowCount(),
                    'column_count': self.archived_records_table.columnCount(),
                    'viewport_width': self.archived_records_table.viewport().width(),
                    'table_width': self.archived_records_table.width(),
                    'is_visible': self.archived_records_table.isVisible()
                }
            
            # Generate recommendations based on performance data
            self._add_performance_recommendations(report)
            
            return report
            
        except Exception as e:
            return {
                'error': f'Failed to generate performance report: {e}',
                'timestamp': datetime.now().isoformat(),
                'tab_name': 'archived_info_tab'
            }
    
    def _add_performance_recommendations(self, report: Dict[str, Any]):
        """
        Add performance recommendations based on collected metrics.
        
        Args:
            report: Performance report dictionary to add recommendations to
        """
        try:
            recommendations = []
            
            # Check cache performance
            cache_perf = report.get('cache_performance', {})
            for cache_type, stats in cache_perf.items():
                if isinstance(stats, dict) and 'hit_ratio' in stats:
                    if stats['hit_ratio'] < 0.3:
                        recommendations.append(f"Low {cache_type} cache hit ratio ({stats['hit_ratio']:.1%}). Consider reviewing cache strategy.")
                    elif stats['hit_ratio'] > 0.9:
                        recommendations.append(f"Excellent {cache_type} cache performance ({stats['hit_ratio']:.1%}).")
            
            # Check debug statistics
            debug_stats = report.get('debug_statistics', {})
            timing_analysis = debug_stats.get('timing_analysis', {})
            if timing_analysis:
                avg_duration = timing_analysis.get('average_duration_ms', 0)
                slow_percentage = timing_analysis.get('slow_operations_percentage', 0)
                
                if avg_duration > 50:
                    recommendations.append(f"Average resize duration is high ({avg_duration:.1f}ms). Consider optimization.")
                
                if slow_percentage > 25:
                    recommendations.append(f"High percentage of slow operations ({slow_percentage:.1f}%). Review resize logic.")
            
            # Check optimization status
            opt_status = report.get('optimization_status', {})
            if opt_status.get('fallback_active', False):
                recommendations.append("Optimization fallback is active. Check for errors in optimization components.")
            
            # Check table metrics
            table_metrics = report.get('table_metrics', {})
            if table_metrics:
                row_count = table_metrics.get('row_count', 0)
                if row_count > 1000:
                    recommendations.append(f"Large table ({row_count} rows). Consider pagination or virtualization.")
                
                viewport_width = table_metrics.get('viewport_width', 0)
                if viewport_width < 300:
                    recommendations.append("Very narrow viewport. Table may not display optimally.")
            
            report['recommendations'] = recommendations
            
        except Exception as e:
            report['recommendations'] = [f"Error generating recommendations: {e}"]
    
    def enable_debug_logging(self, enabled: bool = True):
        """
        Enable or disable debug logging for this tab.
        
        Args:
            enabled: Whether to enable debug logging
        """
        self._resize_debug_enabled = enabled
        
        # Also enable debug manager if available
        if hasattr(self, '_debug_manager') and self._debug_manager:
            self._debug_manager.set_enabled(enabled)
        
        self._log_resize_debug("Debug logging state changed", {'enabled': enabled})
    
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is currently enabled."""
        return self._resize_debug_enabled
    
    def print_performance_report(self):
        """Print a comprehensive performance report for debugging and analysis."""
        try:
            report = self.get_performance_report()
            
            print("\n" + "="*60)
            print("ARCHIVED TAB PERFORMANCE REPORT")
            print("="*60)
            print(f"Generated: {report.get('timestamp', 'Unknown')}")
            print(f"Debug Enabled: {report.get('debug_enabled', False)}")
            
            # Optimization Status
            opt_status = report.get('optimization_status', {})
            if opt_status:
                print(f"\nOptimization Status:")
                print(f"  Fallback Active: {opt_status.get('fallback_active', 'Unknown')}")
                components = opt_status.get('components_initialized', {})
                if components:
                    print(f"  Components Initialized:")
                    for comp, status in components.items():
                        print(f"    {comp}: {status}")
            
            # Cache Performance
            cache_perf = report.get('cache_performance', {})
            if cache_perf and 'error' not in cache_perf:
                print(f"\nCache Performance:")
                for cache_type, stats in cache_perf.items():
                    if isinstance(stats, dict) and 'hit_ratio' in stats:
                        print(f"  {cache_type}:")
                        print(f"    Hit Ratio: {stats['hit_ratio']:.1%}")
                        print(f"    Hits: {stats.get('hits', 0)}")
                        print(f"    Misses: {stats.get('misses', 0)}")
            
            # Debug Statistics
            debug_stats = report.get('debug_statistics', {})
            if debug_stats:
                print(f"\nDebug Statistics:")
                summary = debug_stats.get('summary', {})
                if summary:
                    print(f"  Total Resize Operations: {summary.get('total_resize_operations', 0)}")
                    print(f"  Cache Hit Ratio: {summary.get('cache_hit_ratio', 0):.1%}")
                
                timing = debug_stats.get('timing_analysis', {})
                if timing:
                    print(f"  Timing Analysis:")
                    print(f"    Average Duration: {timing.get('average_duration_ms', 0):.1f}ms")
                    print(f"    Slow Operations: {timing.get('slow_operations_percentage', 0):.1f}%")
            
            # Table Metrics
            table_metrics = report.get('table_metrics', {})
            if table_metrics:
                print(f"\nTable Metrics:")
                print(f"  Rows: {table_metrics.get('row_count', 0)}")
                print(f"  Columns: {table_metrics.get('column_count', 0)}")
                print(f"  Viewport Width: {table_metrics.get('viewport_width', 0)}px")
                print(f"  Table Width: {table_metrics.get('table_width', 0)}px")
            
            # Recommendations
            recommendations = report.get('recommendations', [])
            if recommendations:
                print(f"\nRecommendations:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")
            
            print("="*60)
            
        except Exception as e:
            print(f"Failed to print performance report: {e}")