# -*- coding: utf-8 -*-
"""
Enhanced Table Mixin - Reusable table enhancement functionality
Provides font hierarchy, icon integration, and intelligent column sizing
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush, QFontMetrics
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from qfluentwidgets import FluentIcon, TableWidget, isDarkTheme
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any


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
    
    # Cache configuration
    CACHE_CONFIG = {
        'max_font_cache_size': 50,
        'max_content_cache_size': 1000,
        'cache_ttl_seconds': 300,  # 5 minutes
        'max_sample_rows': 100
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
    
    def _ensure_caching_initialized(self):
        """Lazy initialization of caching system to avoid inheritance conflicts"""
        if not hasattr(self, '_font_metrics_cache'):
            # Font metrics cache: {font_key: {'metrics': QFontMetrics, 'font': QFont, 'timestamp': float}}
            self._font_metrics_cache: Dict[str, Dict[str, Any]] = {}
            
            # Content width cache: {content_hash: {'widths': List[int], 'timestamp': float, 'sample_size': int}}
            self._content_width_cache: Dict[str, Dict[str, Any]] = {}
            
            # Table content hash tracking: {table_id: {'hash': str, 'row_count': int, 'col_count': int, 'timestamp': float}}
            self._table_content_hash: Dict[str, Dict[str, Any]] = {}
            
            # Cache statistics for monitoring
            self._cache_stats = {
                'font_hits': 0,
                'font_misses': 0,
                'content_hits': 0,
                'content_misses': 0,
                'invalidations': 0
            }
    
    def _get_font_cache_key(self, font_size: int, font_weight: int) -> str:
        """Generate cache key for font metrics"""
        return f"font_{font_size}_{font_weight}"
    
    def _get_cached_font_metrics(self, font_size: int, font_weight: int) -> Optional[Tuple[QFontMetrics, QFont]]:
        """Retrieve cached font metrics or create new ones"""
        self._ensure_caching_initialized()
        cache_key = self._get_font_cache_key(font_size, font_weight)
        current_time = time.time()
        
        # Check if cached entry exists and is still valid
        if cache_key in self._font_metrics_cache:
            cached_entry = self._font_metrics_cache[cache_key]
            if current_time - cached_entry['timestamp'] < self.CACHE_CONFIG['cache_ttl_seconds']:
                self._cache_stats['font_hits'] += 1
                return cached_entry['metrics'], cached_entry['font']
            else:
                # Remove expired entry
                del self._font_metrics_cache[cache_key]
        
        # Create new font and metrics
        font = QFont()
        font.setPointSize(font_size)
        font.setWeight(font_weight)
        metrics = QFontMetrics(font)
        
        # Cache the new entry (with size limit)
        if len(self._font_metrics_cache) >= self.CACHE_CONFIG['max_font_cache_size']:
            self._evict_oldest_font_cache()
        
        self._font_metrics_cache[cache_key] = {
            'metrics': metrics,
            'font': font,
            'timestamp': current_time
        }
        
        self._cache_stats['font_misses'] += 1
        return metrics, font
    
    def _get_table_content_hash(self, table: TableWidget) -> str:
        """Generate hash of table content for cache invalidation"""
        content_parts = []
        
        # Include table dimensions
        content_parts.append(f"rows:{table.rowCount()}")
        content_parts.append(f"cols:{table.columnCount()}")
        
        # Sample content from table (limited for performance)
        max_sample_rows = min(self.CACHE_CONFIG['max_sample_rows'], table.rowCount())
        for row in range(0, max_sample_rows, max(1, max_sample_rows // 20)):  # Sample every nth row
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    content_parts.append(f"{row}:{col}:{item.text()}")
        
        # Include headers
        for col in range(table.columnCount()):
            header_item = table.horizontalHeaderItem(col)
            if header_item:
                content_parts.append(f"header:{col}:{header_item.text()}")
        
        content_string = "|".join(content_parts)
        return hashlib.md5(content_string.encode()).hexdigest()
    
    def _get_cached_content_widths(self, table: TableWidget, table_type: str) -> Optional[List[int]]:
        """Retrieve cached content widths if table content hasn't changed"""
        self._ensure_caching_initialized()
        table_id = str(id(table))
        current_hash = self._get_table_content_hash(table)
        current_time = time.time()
        
        # Check if we have a cached hash for this table
        if table_id in self._table_content_hash:
            cached_info = self._table_content_hash[table_id]
            
            # Check if content hasn't changed and cache is still valid
            if (cached_info['hash'] == current_hash and 
                current_time - cached_info['timestamp'] < self.CACHE_CONFIG['cache_ttl_seconds']):
                
                # Look for cached widths
                cache_key = f"{table_type}_{current_hash}"
                if cache_key in self._content_width_cache:
                    cached_widths = self._content_width_cache[cache_key]
                    if current_time - cached_widths['timestamp'] < self.CACHE_CONFIG['cache_ttl_seconds']:
                        self._cache_stats['content_hits'] += 1
                        return cached_widths['widths']
        
        # Update table hash tracking
        self._table_content_hash[table_id] = {
            'hash': current_hash,
            'row_count': table.rowCount(),
            'col_count': table.columnCount(),
            'timestamp': current_time
        }
        
        self._cache_stats['content_misses'] += 1
        return None
    
    def _cache_content_widths(self, table: TableWidget, table_type: str, widths: List[int]):
        """Cache calculated content widths"""
        self._ensure_caching_initialized()
        table_id = str(id(table))
        current_hash = self._get_table_content_hash(table)
        cache_key = f"{table_type}_{current_hash}"
        
        # Implement cache size limit with LRU eviction
        if len(self._content_width_cache) >= self.CACHE_CONFIG['max_content_cache_size']:
            self._evict_oldest_content_cache()
        
        self._content_width_cache[cache_key] = {
            'widths': widths.copy(),
            'timestamp': time.time(),
            'sample_size': min(self.CACHE_CONFIG['max_sample_rows'], table.rowCount())
        }
    
    def _evict_oldest_font_cache(self):
        """Remove oldest font cache entry"""
        if not self._font_metrics_cache:
            return
        
        oldest_key = min(self._font_metrics_cache.keys(), 
                        key=lambda k: self._font_metrics_cache[k]['timestamp'])
        del self._font_metrics_cache[oldest_key]
    
    def _evict_oldest_content_cache(self):
        """Remove oldest content cache entry"""
        if not self._content_width_cache:
            return
        
        oldest_key = min(self._content_width_cache.keys(),
                        key=lambda k: self._content_width_cache[k]['timestamp'])
        del self._content_width_cache[oldest_key]
    
    def _invalidate_table_cache(self, table: TableWidget):
        """Invalidate cache entries for a specific table"""
        self._ensure_caching_initialized()
        table_id = str(id(table))
        
        # Remove table hash tracking
        if table_id in self._table_content_hash:
            del self._table_content_hash[table_id]
        
        # Remove related content width cache entries
        table_type = self._get_table_type(table)
        keys_to_remove = [key for key in self._content_width_cache.keys() 
                         if key.startswith(f"{table_type}_")]
        
        for key in keys_to_remove:
            del self._content_width_cache[key]
        
        self._cache_stats['invalidations'] += 1
    
    def _get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        self._ensure_caching_initialized()
        total_font_requests = self._cache_stats['font_hits'] + self._cache_stats['font_misses']
        total_content_requests = self._cache_stats['content_hits'] + self._cache_stats['content_misses']
        
        return {
            'font_cache_size': len(self._font_metrics_cache),
            'content_cache_size': len(self._content_width_cache),
            'font_hit_ratio': self._cache_stats['font_hits'] / max(1, total_font_requests),
            'content_hit_ratio': self._cache_stats['content_hits'] / max(1, total_content_requests),
            'total_invalidations': self._cache_stats['invalidations'],
            'cache_stats': self._cache_stats.copy()
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
        Optimized implementation with advanced caching and content sampling.
        """
        try:
            # Determine table type for priority column lookup and caching
            table_type = self._get_table_type(table)
            
            # Check for cached widths first
            cached_widths = self._get_cached_content_widths(table, table_type)
            if cached_widths and len(cached_widths) == table.columnCount():
                # Apply cached widths
                for col, width in enumerate(cached_widths):
                    table.setColumnWidth(col, width)
                return True

            # Get font configuration
            font_sizes = getattr(self, 'FONT_SIZES', {'priority_columns': 12, 'regular_columns': 10, 'headers': 13})
            font_weights = getattr(self, 'FONT_WEIGHTS', {'priority_columns': 600, 'regular_columns': 500, 'headers': 700})

            # Calculate maximum width for each column
            calculated_widths = []

            for col in range(table.columnCount()):
                max_width = 0

                # Get header text and calculate header width
                header_text = ""
                header_item = table.horizontalHeaderItem(col)
                if header_item:
                    header_text = header_item.text()

                # Determine if this is a priority column
                is_priority = self._is_priority_column(table_type, header_text)

                # Get appropriate font configuration and cached metrics
                font_size = font_sizes['priority_columns'] if is_priority else font_sizes['regular_columns']
                font_weight = font_weights['priority_columns'] if is_priority else font_weights['regular_columns']
                
                font_metrics, font = self._get_cached_font_metrics(font_size, font_weight)

                # Calculate header width
                if header_text:
                    header_width = font_metrics.width(header_text) + 40  # Extra padding for icon
                    max_width = max(max_width, header_width)

                # Calculate content widths with intelligent sampling
                max_rows_to_check = min(self.CACHE_CONFIG['max_sample_rows'], table.rowCount())
                
                # Use intelligent sampling for large tables
                if table.rowCount() > 50:
                    # Sample rows: first 20, last 20, and evenly distributed middle rows
                    sample_rows = list(range(min(20, table.rowCount())))  # First 20
                    if table.rowCount() > 40:
                        sample_rows.extend(range(max(20, table.rowCount() - 20), table.rowCount()))  # Last 20
                    
                    # Add middle samples
                    if table.rowCount() > 100:
                        middle_start = 20
                        middle_end = table.rowCount() - 20
                        step = max(1, (middle_end - middle_start) // 30)  # Up to 30 middle samples
                        sample_rows.extend(range(middle_start, middle_end, step))
                    
                    sample_rows = sorted(set(sample_rows))[:max_rows_to_check]
                else:
                    sample_rows = range(table.rowCount())

                for row in sample_rows:
                    item = table.item(row, col)
                    if item:
                        text = item.text()
                        if text:
                            width = font_metrics.width(text) + 20  # Padding for content
                            max_width = max(max_width, width)

                # Ensure minimum width for usability
                max_width = max(max_width, 80)  # Minimum column width
                calculated_widths.append(max_width)

            # Cache the calculated widths
            self._cache_content_widths(table, table_type, calculated_widths)

            # Apply calculated widths to columns
            for col, width in enumerate(calculated_widths):
                table.setColumnWidth(col, width)

            return True

        except Exception as e:
            # Log error but don't break functionality
            print(f"Error in _calculate_intelligent_column_widths: {e}")
            return False

    def _get_table_type(self, table):
        """
        Determine table type based on object name, parent class, or other criteria.
        Enhanced to support rental and archive table detection.
        """
        # Get table name from objectName method
        table_name = ''
        if hasattr(table, 'objectName') and callable(table.objectName):
            table_name = table.objectName().lower()
        elif hasattr(table, 'objectName'):
            table_name = str(table.objectName).lower()
        
        # Check parent class type for more accurate detection
        parent_class_name = self.__class__.__name__.lower()
        
        # Rental table detection
        if 'rental' in parent_class_name or 'rental' in table_name:
            return 'rental_table'
        
        # Archive table detection  
        elif 'archive' in parent_class_name or 'archive' in table_name:
            return 'archive_table'
        
        # History table detection (existing)
        elif 'history' in parent_class_name or 'history' in table_name:
            if 'main' in table_name:
                return 'main_table'
            elif 'room' in table_name:
                return 'room_table'
            elif 'totals' in table_name:
                return 'totals_table'
            else:
                return 'history_table'
        
        # Fallback detection based on table name patterns
        elif 'main' in table_name:
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
    
    # Cache management methods for external use
    
    def invalidate_table_cache(self, table: TableWidget):
        """
        Public method to invalidate cache for a specific table.
        Call this when table content changes.
        """
        self._invalidate_table_cache(table)
    
    def clear_all_caches(self):
        """Clear all caches - useful for memory management or debugging"""
        self._ensure_caching_initialized()
        self._font_metrics_cache.clear()
        self._content_width_cache.clear()
        self._table_content_hash.clear()
        
        # Reset statistics
        self._cache_stats = {
            'font_hits': 0,
            'font_misses': 0,
            'content_hits': 0,
            'content_misses': 0,
            'invalidations': 0
        }
    
    def get_cache_performance_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics for monitoring and debugging.
        Returns cache hit ratios, sizes, and other performance metrics.
        """
        return self._get_cache_statistics()
    
    def set_intelligent_column_widths(self, table: TableWidget, force_recalculate: bool = False):
        """
        Public method to set intelligent column widths with caching.
        
        Args:
            table: The table widget to resize
            force_recalculate: If True, bypass cache and recalculate widths
        """
        if force_recalculate:
            self._invalidate_table_cache(table)
        
        return self._calculate_intelligent_column_widths(table)
    
    def on_table_content_changed(self, table: TableWidget):
        """
        Call this method when table content changes to invalidate relevant caches.
        This ensures cache consistency and prevents stale width calculations.
        """
        self._invalidate_table_cache(table)
    
    def on_table_structure_changed(self, table: TableWidget):
        """
        Call this method when table structure changes (columns added/removed).
        This performs a more aggressive cache invalidation.
        """
        # Invalidate all caches related to this table
        self._invalidate_table_cache(table)
        
        # Also clear font cache if table structure changed significantly
        # as column types might have changed
        table_type = self._get_table_type(table)
        if hasattr(self, '_last_table_structure'):
            if self._last_table_structure.get(str(id(table))) != table.columnCount():
                # Structure changed, clear font cache too
                self._font_metrics_cache.clear()
        
        # Track table structure
        if not hasattr(self, '_last_table_structure'):
            self._last_table_structure = {}
        self._last_table_structure[str(id(table))] = table.columnCount()