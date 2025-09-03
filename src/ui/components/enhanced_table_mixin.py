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
        DISABLED - Let the main table handle its own column widths
        """
        # Do nothing - let the main table's _set_intelligent_column_widths handle everything
        return
    
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