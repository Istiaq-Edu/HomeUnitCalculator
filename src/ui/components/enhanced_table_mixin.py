# -*- coding: utf-8 -*-
"""
Enhanced Table Mixin - Reusable table enhancement functionality
Provides font hierarchy, icon integration, and intelligent column sizing
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from qfluentwidgets import FluentIcon, TableWidget, isDarkTheme


class EnhancedTableMixin:
    """Mixin class providing enhanced table functionality with font hierarchy and icons"""

    # Font size configuration for different column types
    FONT_SIZES = {
        'priority_columns': 12,
        'regular_columns': 10,
        'headers': 13
    }

    FONT_WEIGHTS = {
        'priority_columns': 600,
        'regular_columns': 500,
        'headers': 700
    }
    
    # Base column icons - can be overridden by subclasses
    BASE_COLUMN_ICONS = {
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
        'UPDATED AT': FluentIcon.CALENDAR,
        'MONTH': FluentIcon.CALENDAR,
        'TOTAL': FluentIcon.ACCEPT_MEDIUM,
        'GRAND_TOTAL': FluentIcon.ACCEPT_MEDIUM,
        'GRAND TOTAL': FluentIcon.ACCEPT_MEDIUM
    }
    
    def _is_priority_column(self, table_type: str, column_name: str) -> bool:
        """Check if a column is priority based on table type and column name"""
        # Get priority columns for this table type, default to empty list
        priority_columns = getattr(self, 'PRIORITY_COLUMNS', {}).get(table_type, [])
        return column_name.upper() in [col.upper() for col in priority_columns]
    
    def _get_column_icon(self, column_name: str) -> FluentIcon:
        """Get icon for column, checking both class-specific and base icons"""
        # First check class-specific icons
        class_icons = getattr(self, 'COLUMN_ICONS', {})
        icon_key = column_name.upper().replace(' ', '_')
        
        if icon_key in class_icons:
            return class_icons[icon_key]
        elif icon_key in self.BASE_COLUMN_ICONS:
            return self.BASE_COLUMN_ICONS[icon_key]
        else:
            # Default icon for unknown columns
            return FluentIcon.SETTING
    
    def _set_table_headers_with_icons(self, table: TableWidget, headers: list, table_type: str):
        """Set table headers with icons and priority-aware styling"""
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # Apply header styling with icons
        header = table.horizontalHeader()
        for i, header_text in enumerate(headers):
            header_item = table.horizontalHeaderItem(i)
            if header_item:
                # Set header font
                font = QFont()
                font.setPointSize(self.FONT_SIZES['headers'])
                font.setWeight(self.FONT_WEIGHTS['headers'])
                header_item.setFont(font)
                
                # Add icon if available
                icon = self._get_column_icon(header_text)
                header_item.setIcon(icon.icon())
                
                # Check if this is a priority column for special styling
                is_priority = self._is_priority_column(table_type, header_text)
                if is_priority:
                    # Priority headers get slightly different styling
                    font.setWeight(self.FONT_WEIGHTS['headers'] + 100)  # Extra bold
                    header_item.setFont(font)
    
    def _calculate_intelligent_column_widths(self, table: TableWidget):
        """
        Calculate intelligent column widths based on content and font hierarchy.
        Optimized implementation with efficient QFontMetrics usage and caching.
        """
        try:
            from PyQt5.QtGui import QFontMetrics

            # Initialize caching variables if not already done (lazy initialization)
            if not hasattr(self, '_font_metrics_cache'):
                self._font_metrics_cache = {}
            if not hasattr(self, '_content_width_cache'):
                self._content_width_cache = {}

            # Get font configuration from HistoryTab
            font_sizes = getattr(self, 'FONT_SIZES', {'priority_columns': 12, 'regular_columns': 10, 'headers': 13})
            font_weights = getattr(self, 'FONT_WEIGHTS', {'priority_columns': 600, 'regular_columns': 500, 'headers': 700})
            priority_columns = getattr(self, 'PRIORITY_COLUMNS', {})

            # Determine table type for priority column lookup
            table_type = self._get_table_type(table)
            table_id = id(table)  # Unique identifier for this table instance

            # Calculate maximum width for each column
            max_widths = {}

            for col in range(table.columnCount()):
                max_width = 0

                # Get header text and calculate header width
                header_text = ""
                if table.horizontalHeaderItem(col):
                    header_text = table.horizontalHeaderItem(col).text() if table.horizontalHeaderItem(col) else ""

                # Determine if this is a priority column
                is_priority = self._is_priority_column(table_type, header_text)

                # Get appropriate font configuration
                font_size = font_sizes['priority_columns'] if is_priority else font_sizes['regular_columns']
                font_weight = font_weights['priority_columns'] if is_priority else font_weights['regular_columns']
                font_key = f"{font_size}_{font_weight}"

                # Use cached font metrics or create new one
                if font_key not in self._font_metrics_cache:
                    font = QFont()
                    font.setPointSize(font_size)
                    font.setWeight(font_weight)
                    self._font_metrics_cache[font_key] = QFontMetrics(font)

                font_metrics = self._font_metrics_cache[font_key]

                # Calculate header width with caching for content width
                content_key = f"header_{table_id}_{col}"
                if content_key not in self._content_width_cache:
                    if header_text:
                        self._content_width_cache[content_key] = font_metrics.width(header_text)
                    else:
                        self._content_width_cache[content_key] = 0

                header_width = self._content_width_cache[content_key] + 40  # Extra padding for icon
                max_width = max(max_width, header_width)

                # Calculate content widths for first few rows (performance optimization)
                max_rows_to_check = min(100, table.rowCount())  # Check up to 100 rows for performance
                for row in range(max_rows_to_check):
                    item = table.item(row, col)
                    if item:
                        text = item.text()
                        if text:
                            # Use caching for content width calculation
                            content_cache_key = f"content_{table_id}_{col}_{row}"
                            if content_cache_key not in self._content_width_cache:
                                self._content_width_cache[content_cache_key] = font_metrics.width(text)

                            width = self._content_width_cache[content_cache_key] + 20  # Padding for content
                            max_width = max(max_width, width)

                max_widths[col] = max_width

            # Apply calculated widths to columns
            for col, width in max_widths.items():
                table.setColumnWidth(col, width)

            return True

        except Exception as e:
            # Log error but don't break functionality
            print(f"Error in _calculate_intelligent_column_widths: {e}")
            return False

    def _get_table_type(self, table):
        """
        Determine table type based on object name or other criteria.
        Override in subclasses for more specific detection.
        """
        table_name = getattr(table, 'objectName', '').lower()

        if 'main' in table_name:
            return 'main_table'
        elif 'room' in table_name:
            return 'room_table'
        elif 'totals' in table_name:
            return 'totals_table'
        else:
            return 'unknown_table'
    
    def _create_centered_item(self, text: str, column_name: str = "", is_priority: bool = False) -> QTableWidgetItem:
        """Create a table widget item with center alignment, number formatting, and priority-aware styling"""
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
        
        # Apply modern styling to numeric content
        if self._is_numeric_text(str(text)):
            if is_priority:
                font.setWeight(QFont.Bold)  # Bold for priority numbers
            else:
                font.setWeight(QFont.DemiBold)  # Semi-bold for regular numbers
            
            # Theme-aware subtle color enhancement for numbers
            if isDarkTheme():
                item.setForeground(QBrush(QColor("#B3E5FC")))  # Light blue for dark theme
            else:
                item.setForeground(QBrush(QColor("#1565C0")))  # Dark blue for light theme
        
        item.setFont(font)
        return item
    
    def _create_special_item(self, text: str, column_type: str, column_name: str = "", is_priority: bool = False) -> QTableWidgetItem:
        """Create a styled item for special columns with priority-aware formatting"""
        # Format the text based on column type
        formatted_text = str(text)
        if self._is_numeric_text(str(text)):
            formatted_text = self._format_number(str(text))
            if column_type in ["advanced_paid", "total", "grand_total"]:
                formatted_text = f"৳{formatted_text}"  # Add Taka symbol
        
        item = QTableWidgetItem(formatted_text)
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Apply priority-aware font styling
        font = item.font()
        if is_priority:
            font.setPointSize(self.FONT_SIZES['priority_columns'])
            font.setWeight(self.FONT_WEIGHTS['priority_columns'])
        else:
            font.setPointSize(self.FONT_SIZES['regular_columns'])
            font.setWeight(self.FONT_WEIGHTS['regular_columns'])
        
        # Apply special styling based on column type
        if column_type in ["advanced_paid", "total", "grand_total"]:
            font.setWeight(QFont.Bold)
            if isDarkTheme():
                item.setForeground(QBrush(QColor("#66BB6A")))  # Light green for dark theme
            else:
                item.setForeground(QBrush(QColor("#2E7D32")))  # Dark green for light theme
        
        item.setFont(font)
        return item
    
    def _create_identifier_item(self, text: str, identifier_type: str, is_priority: bool = False) -> QTableWidgetItem:
        """Create a styled item for identifier columns"""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Apply priority-aware font styling
        font = item.font()
        if is_priority:
            font.setPointSize(self.FONT_SIZES['priority_columns'])
            font.setWeight(self.FONT_WEIGHTS['priority_columns'])
        else:
            font.setPointSize(self.FONT_SIZES['regular_columns'])
            font.setWeight(self.FONT_WEIGHTS['regular_columns'])
        
        # Apply identifier-specific styling
        if identifier_type == "room":
            if isDarkTheme():
                item.setForeground(QBrush(QColor("#4FC3F7")))  # Light cyan for dark theme
            else:
                item.setForeground(QBrush(QColor("#00796B")))  # Dark teal for light theme
        elif identifier_type == "id":
            font.setWeight(QFont.DemiBold)
        
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