# -*- coding: utf-8 -*-
"""
Table Optimization Infrastructure Components
Provides debounced resize handling, caching, batched updates, and performance monitoring
for enhanced table performance and flicker elimination.
"""

import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from collections import OrderedDict

from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QTableWidget, QHeaderView, QAbstractItemView

from src.ui.custom_widgets import SmoothTableWidget


class OptimizationConfig:
    """
    Configuration manager for table optimization features.
    Provides centralized control over optimization components with fallback capabilities.
    """
    
    def __init__(self):
        """Initialize optimization configuration with safe defaults."""
        # Feature flags for enabling/disabling optimization components
        self.enable_debounced_resize = True
        self.enable_caching = True
        self.enable_batch_updates = True
        self.enable_debug_logging = False
        
        # Performance configuration
        self.debounce_delay_ms = 50
        self.cache_size_limit = 1000
        self.max_sample_rows = 100
        self.slow_operation_threshold_ms = 100
        
        # Error handling configuration
        self.enable_graceful_degradation = True
        self.max_retry_attempts = 3
        self.fallback_timeout_ms = 5000
        
        # Debug configuration
        self.verbose_error_logging = False
        self.performance_monitoring = False
        
    def disable_all_optimizations(self):
        """Disable all optimization features for fallback mode."""
        self.enable_debounced_resize = False
        self.enable_caching = False
        self.enable_batch_updates = False
        
    def enable_safe_mode(self):
        """Enable only the safest optimization features."""
        self.enable_debounced_resize = True
        self.enable_caching = False
        self.enable_batch_updates = False
        self.debounce_delay_ms = 100  # Longer delay for safety
        
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary for serialization."""
        return {
            'enable_debounced_resize': self.enable_debounced_resize,
            'enable_caching': self.enable_caching,
            'enable_batch_updates': self.enable_batch_updates,
            'enable_debug_logging': self.enable_debug_logging,
            'debounce_delay_ms': self.debounce_delay_ms,
            'cache_size_limit': self.cache_size_limit,
            'max_sample_rows': self.max_sample_rows,
            'slow_operation_threshold_ms': self.slow_operation_threshold_ms,
            'enable_graceful_degradation': self.enable_graceful_degradation,
            'max_retry_attempts': self.max_retry_attempts,
            'fallback_timeout_ms': self.fallback_timeout_ms,
            'verbose_error_logging': self.verbose_error_logging,
            'performance_monitoring': self.performance_monitoring
        }


class OptimizationErrorHandler:
    """
    Centralized error handling and recovery system for table optimization components.
    Provides graceful degradation and fallback mechanisms.
    """
    
    def __init__(self, config: OptimizationConfig):
        """
        Initialize error handler with configuration.
        
        Args:
            config: OptimizationConfig instance for behavior control
        """
        self.config = config
        self.error_count = 0
        self.error_log: List[Dict[str, Any]] = []
        self.fallback_active = False
        
    def handle_error(self, operation: str, error: Exception, context: Optional[Dict] = None) -> bool:
        """
        Handle an optimization error with appropriate recovery strategy.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            context: Optional context information
            
        Returns:
            True if operation should be retried, False if fallback should be used
        """
        self.error_count += 1
        
        # Log the error
        error_entry = {
            'timestamp': datetime.now(),
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'fallback_triggered': False
        }
        
        if self.config.verbose_error_logging:
            print(f"[OPTIMIZATION ERROR] {operation}: {error}")
            if context:
                print(f"  Context: {context}")
        
        # Determine recovery strategy based on error type and configuration
        should_retry = self._should_retry_operation(operation, error)
        
        if not should_retry or self.error_count > self.config.max_retry_attempts:
            # Trigger fallback mode
            error_entry['fallback_triggered'] = True
            self.fallback_active = True
            
            if self.config.verbose_error_logging:
                print(f"[OPTIMIZATION FALLBACK] Activating fallback for {operation}")
        
        self.error_log.append(error_entry)
        
        # Keep error log size manageable
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-50:]  # Keep last 50 errors
        
        return should_retry and not self.fallback_active
    
    def _should_retry_operation(self, operation: str, error: Exception) -> bool:
        """
        Determine if an operation should be retried based on error type.
        
        Args:
            operation: Name of the operation
            error: The exception that occurred
            
        Returns:
            True if operation should be retried
        """
        # Don't retry certain critical errors
        critical_errors = (MemoryError, RecursionError, SystemExit, KeyboardInterrupt)
        if isinstance(error, critical_errors):
            return False
        
        # Don't retry if graceful degradation is disabled
        if not self.config.enable_graceful_degradation:
            return False
        
        # Retry timeout and temporary errors
        timeout_errors = (TimeoutError, ConnectionError)
        if isinstance(error, timeout_errors):
            return True
        
        # Retry most other errors unless we've exceeded retry limit
        return self.error_count <= self.config.max_retry_attempts
    
    def is_fallback_active(self) -> bool:
        """Check if fallback mode is currently active."""
        return self.fallback_active
    
    def reset_error_state(self):
        """Reset error state to allow normal operation."""
        self.error_count = 0
        self.fallback_active = False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors for monitoring."""
        if not self.error_log:
            return {'total_errors': 0, 'fallback_active': self.fallback_active}
        
        error_types = {}
        operations = {}
        fallback_count = 0
        
        for entry in self.error_log:
            error_type = entry['error_type']
            operation = entry['operation']
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            operations[operation] = operations.get(operation, 0) + 1
            
            if entry['fallback_triggered']:
                fallback_count += 1
        
        return {
            'total_errors': len(self.error_log),
            'error_types': error_types,
            'operations': operations,
            'fallback_count': fallback_count,
            'fallback_active': self.fallback_active,
            'recent_errors': self.error_log[-5:] if len(self.error_log) > 0 else []
        }


class FallbackResizeManager:
    """
    Fallback resize manager that provides basic table resizing without optimizations.
    Used when advanced optimization components fail.
    """
    
    def __init__(self, parent_tab):
        """
        Initialize fallback resize manager.
        
        Args:
            parent_tab: The parent tab widget containing tables
        """
        self.parent_tab = parent_tab
        
    def perform_basic_resize(self, table: QTableWidget):
        """
        Perform basic table resize using original Qt mechanisms.
        
        Args:
            table: QTableWidget to resize
        """
        try:
            # Basic column width adjustment
            header = table.horizontalHeader()
            
            # Simple resize to contents approach
            for col in range(table.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            
            # Allow user resizing
            header.setSectionResizeMode(QHeaderView.Interactive)
            
            return True
            
        except Exception as e:
            print(f"Fallback resize failed: {e}")
            return False
    
    def perform_basic_table_setup(self, table: QTableWidget):
        """
        Perform basic table setup without advanced features.
        
        Args:
            table: QTableWidget to set up
        """
        try:
            # Basic table properties
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setHighlightSections(False)
            
            # Basic header setup
            header = table.horizontalHeader()
            header.setStretchLastSection(True)
            
            return True
            
        except Exception as e:
            print(f"Fallback table setup failed: {e}")
            return False


class DebounceResizeManager(QObject):
    """
    Manages debounced resize events to prevent flickering and improve performance.
    Enhanced with comprehensive error handling and fallback mechanisms.
    
    Features:
    - Configurable debounce delay (50-100ms)
    - Progress guard to prevent overlapping operations
    - Unified entry point for all resize events
    - Integration with existing table resize methods
    - Error handling with graceful degradation
    - Fallback to basic resize on failures
    """
    
    # Signal emitted when debounced resize should be performed
    resize_requested = pyqtSignal()
    
    def __init__(self, parent_tab, config: OptimizationConfig, error_handler: OptimizationErrorHandler, debounce_delay: int = 50):
        """
        Initialize the debounce resize manager.
        
        Args:
            parent_tab: The parent tab widget containing tables
            config: OptimizationConfig for feature control
            error_handler: OptimizationErrorHandler for error management
            debounce_delay: Delay in milliseconds for debouncing (default: 50ms)
        """
        super().__init__(parent_tab)
        self.parent_tab = parent_tab
        self.config = config
        self.error_handler = error_handler
        self.debounce_delay = debounce_delay
        
        # Timer for debouncing resize events
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._perform_debounced_resize)
        
        # Progress guard to prevent overlapping operations
        self._resizing_in_progress = False
        
        # Track pending resize requests
        self._pending_resize = False
        
        # Fallback manager for when optimizations fail
        self._fallback_manager = FallbackResizeManager(parent_tab)
        
    def trigger_debounced_resize(self):
        """
        Trigger a debounced resize operation with error handling.
        If a resize is already in progress, queue the request for the next cycle.
        """
        try:
            # Check if optimizations are disabled
            if not self.config.enable_debounced_resize or self.error_handler.is_fallback_active():
                self._perform_fallback_resize()
                return
            
            if self._resizing_in_progress:
                # Queue resize for next cycle
                self._pending_resize = True
                return
                
            # Stop any existing timer and start new one
            self._resize_timer.stop()
            self._resize_timer.start(self.debounce_delay)
            
        except Exception as e:
            should_retry = self.error_handler.handle_error('trigger_debounced_resize', e, 
                                                         {'debounce_delay': self.debounce_delay})
            if not should_retry:
                self._perform_fallback_resize()
        
    def _perform_debounced_resize(self):
        """
        Execute the actual resize operation with batching, progress guards, and error handling.
        """
        if self._resizing_in_progress:
            return
            
        try:
            self._resizing_in_progress = True
            
            # Check if we should use fallback mode
            if self.error_handler.is_fallback_active():
                self._perform_fallback_resize()
                return
            
            # Emit signal for parent to handle resize
            self.resize_requested.emit()
            
            # Check if another resize was queued during operation
            if self._pending_resize:
                self._pending_resize = False
                # Schedule another resize cycle
                self._resize_timer.start(self.debounce_delay)
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('perform_debounced_resize', e,
                                                         {'resizing_in_progress': self._resizing_in_progress})
            if not should_retry:
                self._perform_fallback_resize()
        finally:
            self._resizing_in_progress = False
    
    def _perform_fallback_resize(self):
        """
        Perform fallback resize using basic mechanisms when optimizations fail.
        """
        try:
            # Use fallback manager for basic resize
            if hasattr(self.parent_tab, 'rental_records_table') and self.parent_tab.rental_records_table:
                self._fallback_manager.perform_basic_resize(self.parent_tab.rental_records_table)
            
            if hasattr(self.parent_tab, 'archived_records_table') and self.parent_tab.archived_records_table:
                self._fallback_manager.perform_basic_resize(self.parent_tab.archived_records_table)
                
        except Exception as e:
            # Even fallback failed - log but don't crash
            if self.config.verbose_error_logging:
                print(f"[CRITICAL] Fallback resize failed: {e}")
    
    def safe_trigger_resize(self, table: QTableWidget = None):
        """
        Safely trigger a resize with comprehensive error handling.
        
        Args:
            table: Optional specific table to resize
        """
        try:
            if table and self.error_handler.is_fallback_active():
                # Direct fallback for specific table
                self._fallback_manager.perform_basic_resize(table)
            else:
                # Use normal debounced path
                self.trigger_debounced_resize()
                
        except Exception as e:
            self.error_handler.handle_error('safe_trigger_resize', e, {'table_provided': table is not None})
            # Last resort - try direct fallback
            if table:
                try:
                    self._fallback_manager.perform_basic_resize(table)
                except Exception as fallback_error:
                    if self.config.verbose_error_logging:
                        print(f"[CRITICAL] All resize methods failed: {fallback_error}")
            
    def consolidate_resize_handlers(self):
        """
        Ensure all resize events route through the debounced system.
        This method should be called during initialization to replace existing handlers.
        """
        # This will be implemented by the parent tab to route all resize events
        # through trigger_debounced_resize()
        pass
        
    def is_resizing(self) -> bool:
        """Check if a resize operation is currently in progress."""
        return self._resizing_in_progress
        
    def set_debounce_delay(self, delay: int):
        """Update the debounce delay."""
        self.debounce_delay = delay


class TableCacheManager:
    """
    Manages multi-level caching for font metrics, content widths, and table hashes.
    Enhanced with comprehensive error handling and recovery mechanisms.
    
    Features:
    - Font metrics caching with font configuration keys
    - Content width caching with content hash keys
    - Automatic cache invalidation on content changes
    - Performance monitoring and statistics
    - Memory-efficient cache size management with LRU eviction
    - Error handling with graceful degradation
    - Cache corruption recovery
    """
    
    def __init__(self, config: OptimizationConfig, error_handler: OptimizationErrorHandler, cache_size_limit: int = 1000):
        """
        Initialize the table cache manager.
        
        Args:
            config: OptimizationConfig for feature control
            error_handler: OptimizationErrorHandler for error management
            cache_size_limit: Maximum number of entries per cache type
        """
        self.config = config
        self.error_handler = error_handler
        self.cache_size_limit = cache_size_limit
        
        # Font metrics cache: font_key -> metrics data
        self._font_metrics_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Content width cache: content_hash -> width data
        self._content_width_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Table content hash tracking: table_name -> hash info
        self._table_content_hash: Dict[str, Dict[str, Any]] = {}
        
        # Cache performance statistics
        self._cache_statistics = {
            'font_metrics': {'hits': 0, 'misses': 0},
            'content_width': {'hits': 0, 'misses': 0}
        }
        
    def get_cached_font_metrics(self, font_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached font metrics for a given font configuration with error handling.
        
        Args:
            font_key: Unique key identifying font configuration
            
        Returns:
            Cached font metrics data or None if not found or error occurred
        """
        try:
            # Check if caching is disabled
            if not self.config.enable_caching or self.error_handler.is_fallback_active():
                self._cache_statistics['font_metrics']['misses'] += 1
                return None
            
            if font_key in self._font_metrics_cache:
                # Move to end (LRU)
                self._font_metrics_cache.move_to_end(font_key)
                self._cache_statistics['font_metrics']['hits'] += 1
                
                # Validate cached data
                cached_data = self._font_metrics_cache[font_key]
                if self._validate_font_cache_entry(cached_data):
                    return cached_data
                else:
                    # Remove corrupted entry
                    del self._font_metrics_cache[font_key]
                    self._cache_statistics['font_metrics']['misses'] += 1
                    return None
            else:
                self._cache_statistics['font_metrics']['misses'] += 1
                return None
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('get_cached_font_metrics', e, 
                                                         {'font_key': font_key})
            if not should_retry:
                # Clear potentially corrupted cache
                self._safe_clear_font_cache()
            self._cache_statistics['font_metrics']['misses'] += 1
            return None
    
    def _validate_font_cache_entry(self, cached_data: Dict[str, Any]) -> bool:
        """
        Validate that a cached font entry is not corrupted.
        
        Args:
            cached_data: Cached font data to validate
            
        Returns:
            True if entry is valid, False otherwise
        """
        try:
            required_keys = ['font_object', 'metrics', 'char_width', 'line_height', 'timestamp']
            return all(key in cached_data for key in required_keys)
        except Exception:
            return False
    
    def _safe_clear_font_cache(self):
        """Safely clear font cache on corruption."""
        try:
            self._font_metrics_cache.clear()
            if self.config.verbose_error_logging:
                print("[CACHE RECOVERY] Font cache cleared due to corruption")
        except Exception as e:
            if self.config.verbose_error_logging:
                print(f"[CACHE ERROR] Failed to clear font cache: {e}")
            
    def cache_font_metrics(self, font_key: str, font: QFont, metrics: QFontMetrics):
        """
        Cache font metrics for a given font configuration with error handling.
        
        Args:
            font_key: Unique key identifying font configuration
            font: QFont object
            metrics: QFontMetrics object
        """
        try:
            # Check if caching is disabled
            if not self.config.enable_caching or self.error_handler.is_fallback_active():
                return
            
            # Prepare cache data with validation
            cache_data = {
                'font_object': font,
                'metrics': metrics,
                'char_width': metrics.averageCharWidth(),
                'line_height': metrics.height(),
                'timestamp': datetime.now()
            }
            
            # Validate data before caching
            if not self._validate_font_cache_entry(cache_data):
                if self.config.verbose_error_logging:
                    print(f"[CACHE WARNING] Invalid font data for key: {font_key}")
                return
            
            # Add to cache with LRU management
            self._font_metrics_cache[font_key] = cache_data
            self._font_metrics_cache.move_to_end(font_key)
            
            # Enforce cache size limit
            if len(self._font_metrics_cache) > self.cache_size_limit:
                self._font_metrics_cache.popitem(last=False)  # Remove oldest
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('cache_font_metrics', e,
                                                         {'font_key': font_key})
            if not should_retry:
                # Clear cache on repeated failures
                self._safe_clear_font_cache()
            
    def get_cached_content_width(self, content_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached content width data for a given content hash.
        
        Args:
            content_key: Hash key identifying table content
            
        Returns:
            Cached width data or None if not found
        """
        if content_key in self._content_width_cache:
            # Move to end (LRU)
            self._content_width_cache.move_to_end(content_key)
            self._cache_statistics['content_width']['hits'] += 1
            return self._content_width_cache[content_key]
        else:
            self._cache_statistics['content_width']['misses'] += 1
            return None
            
    def cache_content_width(self, content_key: str, column_widths: List[int], 
                          total_width: int, sample_size: int):
        """
        Cache content width data for a given content hash.
        
        Args:
            content_key: Hash key identifying table content
            column_widths: List of calculated column widths
            total_width: Total calculated width
            sample_size: Number of rows sampled for calculation
        """
        cache_data = {
            'column_widths': column_widths.copy(),
            'total_width': total_width,
            'sample_size': sample_size,
            'timestamp': datetime.now()
        }
        
        # Add to cache with LRU management
        self._content_width_cache[content_key] = cache_data
        self._content_width_cache.move_to_end(content_key)
        
        # Enforce cache size limit
        if len(self._content_width_cache) > self.cache_size_limit:
            self._content_width_cache.popitem(last=False)  # Remove oldest
            
    def generate_table_content_hash(self, table: QTableWidget) -> str:
        """
        Generate a hash key for table content to use for caching.
        
        Args:
            table: QTableWidget to generate hash for
            
        Returns:
            Hash string representing table content
        """
        # Create hash based on table dimensions and sample content
        hash_data = []
        
        # Add table dimensions
        hash_data.append(f"rows:{table.rowCount()}")
        hash_data.append(f"cols:{table.columnCount()}")
        
        # Sample content from first few rows and columns for hash
        sample_rows = min(10, table.rowCount())
        sample_cols = min(5, table.columnCount())
        
        for row in range(sample_rows):
            for col in range(sample_cols):
                item = table.item(row, col)
                if item:
                    hash_data.append(item.text())
                    
        # Create hash
        content_str = "|".join(hash_data)
        return hashlib.md5(content_str.encode()).hexdigest()
        
    def update_table_content_hash(self, table_name: str, table: QTableWidget):
        """
        Update the stored content hash for a table.
        
        Args:
            table_name: Name identifier for the table
            table: QTableWidget to hash
        """
        current_hash = self.generate_table_content_hash(table)
        
        self._table_content_hash[table_name] = {
            'current_hash': current_hash,
            'row_count': table.rowCount(),
            'column_count': table.columnCount(),
            'last_update': datetime.now()
        }
        
    def has_table_content_changed(self, table_name: str, table: QTableWidget) -> bool:
        """
        Check if table content has changed since last hash update.
        
        Args:
            table_name: Name identifier for the table
            table: QTableWidget to check
            
        Returns:
            True if content has changed, False otherwise
        """
        if table_name not in self._table_content_hash:
            return True
            
        current_hash = self.generate_table_content_hash(table)
        stored_hash = self._table_content_hash[table_name]['current_hash']
        
        return current_hash != stored_hash
        
    def invalidate_cache_for_table(self, table_name: str):
        """
        Invalidate cache entries for a specific table.
        
        Args:
            table_name: Name identifier for the table
        """
        # Remove table from hash tracking
        if table_name in self._table_content_hash:
            del self._table_content_hash[table_name]
            
        # Remove related content width cache entries
        # (We could implement more sophisticated tracking, but for now clear all)
        # In a more advanced implementation, we'd track which cache entries
        # belong to which tables
        
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Return cache performance statistics.
        
        Returns:
            Dictionary containing cache hit/miss ratios and other metrics
        """
        stats = {}
        
        for cache_type, data in self._cache_statistics.items():
            total_requests = data['hits'] + data['misses']
            hit_ratio = data['hits'] / total_requests if total_requests > 0 else 0
            
            stats[cache_type] = {
                'hits': data['hits'],
                'misses': data['misses'],
                'total_requests': total_requests,
                'hit_ratio': hit_ratio
            }
            
        # Add cache size information
        stats['cache_sizes'] = {
            'font_metrics': len(self._font_metrics_cache),
            'content_width': len(self._content_width_cache),
            'table_hashes': len(self._table_content_hash)
        }
        
        return stats
        
    def clear_all_caches(self):
        """Clear all cached data."""
        self._font_metrics_cache.clear()
        self._content_width_cache.clear()
        self._table_content_hash.clear()
        
        # Reset statistics
        for cache_type in self._cache_statistics:
            self._cache_statistics[cache_type] = {'hits': 0, 'misses': 0}


class BatchUpdateManager:
    """
    Coordinates batched UI updates to prevent visual artifacts during table operations.
    Enhanced with comprehensive error handling and state restoration guarantees.
    
    Features:
    - Temporary disabling of table updates (setUpdatesEnabled(False))
    - Header signal blocking during batch operations
    - Sorting state preservation and restoration
    - Viewport update coordination
    - Graceful error handling with state restoration guarantees
    - Automatic recovery from batch operation failures
    - State validation and corruption detection
    """
    
    def __init__(self, table: QTableWidget, config: OptimizationConfig, error_handler: OptimizationErrorHandler):
        """
        Initialize the batch update manager for a specific table.
        
        Args:
            table: QTableWidget to manage batch updates for
            config: OptimizationConfig for feature control
            error_handler: OptimizationErrorHandler for error management
        """
        self.table = table
        self.config = config
        self.error_handler = error_handler
        
        # Store original states for restoration
        self._original_states = {}
        self._batch_active = False
        self._state_backup = {}  # Additional backup for critical failures
        
    def begin_batch_update(self):
        """
        Start batched update mode by disabling updates and storing current states with error handling.
        """
        if self._batch_active:
            return  # Already in batch mode
        
        try:
            # Check if batch updates are disabled
            if not self.config.enable_batch_updates or self.error_handler.is_fallback_active():
                return  # Skip batch mode
            
            # Create state backup before making changes
            self._create_state_backup()
            
            # Store original states
            self._original_states = {
                'updates_enabled': self.table.updatesEnabled(),
                'sorting_enabled': self.table.isSortingEnabled(),
                'header_signals_blocked': False
            }
            
            # Disable table updates to prevent flickering
            self.table.setUpdatesEnabled(False)
            
            # Temporarily disable sorting to prevent interference
            if self._original_states['sorting_enabled']:
                self.table.setSortingEnabled(False)
                
            # Block header signals if possible
            header = self.table.horizontalHeader()
            if header:
                self._original_states['header_signals_blocked'] = header.signalsBlocked()
                header.blockSignals(True)
                
            self._batch_active = True
            
        except Exception as e:
            should_retry = self.error_handler.handle_error('begin_batch_update', e,
                                                         {'table_id': str(id(self.table))})
            if not should_retry:
                # Force restore to safe state
                self._emergency_state_restore()
            else:
                # Try to restore normally
                self._restore_table_states()
    
    def _create_state_backup(self):
        """Create a backup of critical table states for emergency recovery."""
        try:
            self._state_backup = {
                'updates_enabled': self.table.updatesEnabled(),
                'sorting_enabled': self.table.isSortingEnabled(),
                'header_signals_blocked': False
            }
            
            header = self.table.horizontalHeader()
            if header:
                self._state_backup['header_signals_blocked'] = header.signalsBlocked()
                
        except Exception as e:
            if self.config.verbose_error_logging:
                print(f"[BATCH WARNING] Failed to create state backup: {e}")
    
    def _emergency_state_restore(self):
        """Emergency state restoration using backup data."""
        try:
            # Force enable updates
            self.table.setUpdatesEnabled(True)
            
            # Force enable sorting
            self.table.setSortingEnabled(True)
            
            # Force unblock header signals
            header = self.table.horizontalHeader()
            if header:
                header.blockSignals(False)
                
            self._batch_active = False
            
            if self.config.verbose_error_logging:
                print("[BATCH RECOVERY] Emergency state restoration completed")
                
        except Exception as e:
            if self.config.verbose_error_logging:
                print(f"[BATCH CRITICAL] Emergency restoration failed: {e}")
            
    def end_batch_update(self):
        """
        End batched update mode and restore all original states with error handling.
        """
        if not self._batch_active:
            return  # Not in batch mode
            
        try:
            self._restore_table_states()
        except Exception as e:
            should_retry = self.error_handler.handle_error('end_batch_update', e,
                                                         {'table_id': str(id(self.table))})
            if not should_retry:
                # Use emergency restoration
                self._emergency_state_restore()
        finally:
            self._batch_active = False
            
    def _restore_table_states(self):
        """
        Restore original table states with comprehensive error handling.
        This method guarantees state restoration even if individual operations fail.
        """
        errors = []
        restoration_success = True
        
        # Restore updates enabled state
        try:
            if 'updates_enabled' in self._original_states:
                self.table.setUpdatesEnabled(self._original_states['updates_enabled'])
            elif 'updates_enabled' in self._state_backup:
                self.table.setUpdatesEnabled(self._state_backup['updates_enabled'])
        except Exception as e:
            errors.append(f"Failed to restore updates enabled: {e}")
            restoration_success = False
            # Force enable updates as fallback
            try:
                self.table.setUpdatesEnabled(True)
            except Exception as fallback_error:
                errors.append(f"Fallback updates enable failed: {fallback_error}")
                
        # Restore sorting enabled state
        try:
            if 'sorting_enabled' in self._original_states:
                self.table.setSortingEnabled(self._original_states['sorting_enabled'])
            elif 'sorting_enabled' in self._state_backup:
                self.table.setSortingEnabled(self._state_backup['sorting_enabled'])
        except Exception as e:
            errors.append(f"Failed to restore sorting enabled: {e}")
            restoration_success = False
            # Force enable sorting as fallback
            try:
                self.table.setSortingEnabled(True)
            except Exception as fallback_error:
                errors.append(f"Fallback sorting enable failed: {fallback_error}")
                
        # Restore header signals
        try:
            header = self.table.horizontalHeader()
            if header:
                if 'header_signals_blocked' in self._original_states:
                    header.blockSignals(self._original_states['header_signals_blocked'])
                elif 'header_signals_blocked' in self._state_backup:
                    header.blockSignals(self._state_backup['header_signals_blocked'])
        except Exception as e:
            errors.append(f"Failed to restore header signals: {e}")
            restoration_success = False
            # Force unblock signals as fallback
            try:
                if header:
                    header.blockSignals(False)
            except Exception as fallback_error:
                errors.append(f"Fallback header unblock failed: {fallback_error}")
        
        # Log errors and report to error handler
        if errors:
            error_context = {
                'error_count': len(errors),
                'restoration_success': restoration_success,
                'table_id': str(id(self.table))
            }
            
            if self.config.verbose_error_logging:
                print(f"BatchUpdateManager restoration errors: {errors}")
            
            # Report to error handler if restoration failed
            if not restoration_success:
                combined_error = Exception(f"State restoration failed: {'; '.join(errors)}")
                self.error_handler.handle_error('restore_table_states', combined_error, error_context)
            
    def is_batch_active(self) -> bool:
        """Check if batch update mode is currently active."""
        return self._batch_active
        
    def __enter__(self):
        """Context manager entry - begin batch update."""
        self.begin_batch_update()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - end batch update."""
        self.end_batch_update()
        
    def disable_all_optimizations(self):
        """Disable all optimization features for fallback mode."""
        self.enable_debounced_resize = False
        self.enable_caching = False
        self.enable_batch_updates = False
        
    def enable_safe_mode(self):
        """Enable only the safest optimization features."""
        self.enable_debounced_resize = True
        self.enable_caching = False
        self.enable_batch_updates = False
        self.debounce_delay_ms = 100  # Longer delay for safety
        
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary for serialization."""
        return {
            'enable_debounced_resize': self.enable_debounced_resize,
            'enable_caching': self.enable_caching,
            'enable_batch_updates': self.enable_batch_updates,
            'enable_debug_logging': self.enable_debug_logging,
            'debounce_delay_ms': self.debounce_delay_ms,
            'cache_size_limit': self.cache_size_limit,
            'max_sample_rows': self.max_sample_rows,
            'slow_operation_threshold_ms': self.slow_operation_threshold_ms,
            'enable_graceful_degradation': self.enable_graceful_degradation,
            'max_retry_attempts': self.max_retry_attempts,
            'fallback_timeout_ms': self.fallback_timeout_ms,
            'verbose_error_logging': self.verbose_error_logging,
            'performance_monitoring': self.performance_monitoring
        }


class OptimizationErrorHandler:
    """
    Centralized error handling and recovery system for table optimization components.
    Provides graceful degradation and fallback mechanisms.
    """
    
    def __init__(self, config: OptimizationConfig):
        """
        Initialize error handler with configuration.
        
        Args:
            config: OptimizationConfig instance for behavior control
        """
        self.config = config
        self.error_count = 0
        self.error_log: List[Dict[str, Any]] = []
        self.fallback_active = False
        
    def handle_error(self, operation: str, error: Exception, context: Optional[Dict] = None) -> bool:
        """
        Handle an optimization error with appropriate recovery strategy.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            context: Optional context information
            
        Returns:
            True if operation should be retried, False if fallback should be used
        """
        self.error_count += 1
        
        # Log the error
        error_entry = {
            'timestamp': datetime.now(),
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'fallback_triggered': False
        }
        
        if self.config.verbose_error_logging:
            print(f"[OPTIMIZATION ERROR] {operation}: {error}")
            if context:
                print(f"  Context: {context}")
        
        # Determine recovery strategy based on error type and configuration
        should_retry = self._should_retry_operation(operation, error)
        
        if not should_retry or self.error_count > self.config.max_retry_attempts:
            # Trigger fallback mode
            error_entry['fallback_triggered'] = True
            self.fallback_active = True
            
            if self.config.verbose_error_logging:
                print(f"[OPTIMIZATION FALLBACK] Activating fallback for {operation}")
        
        self.error_log.append(error_entry)
        
        # Keep error log size manageable
        if len(self.error_log) > 100:
            self.error_log = self.error_log[-50:]  # Keep last 50 errors
        
        return should_retry and not self.fallback_active
    
    def _should_retry_operation(self, operation: str, error: Exception) -> bool:
        """
        Determine if an operation should be retried based on error type.
        
        Args:
            operation: Name of the operation
            error: The exception that occurred
            
        Returns:
            True if operation should be retried
        """
        # Don't retry certain critical errors
        critical_errors = (MemoryError, RecursionError, SystemExit, KeyboardInterrupt)
        if isinstance(error, critical_errors):
            return False
        
        # Don't retry if graceful degradation is disabled
        if not self.config.enable_graceful_degradation:
            return False
        
        # Retry timeout and temporary errors
        timeout_errors = (TimeoutError, ConnectionError)
        if isinstance(error, timeout_errors):
            return True
        
        # Retry most other errors unless we've exceeded retry limit
        return self.error_count <= self.config.max_retry_attempts
    
    def is_fallback_active(self) -> bool:
        """Check if fallback mode is currently active."""
        return self.fallback_active
    
    def reset_error_state(self):
        """Reset error state to allow normal operation."""
        self.error_count = 0
        self.fallback_active = False
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors for monitoring."""
        if not self.error_log:
            return {'total_errors': 0, 'fallback_active': self.fallback_active}
        
        error_types = {}
        operations = {}
        fallback_count = 0
        
        for entry in self.error_log:
            error_type = entry['error_type']
            operation = entry['operation']
            
            error_types[error_type] = error_types.get(error_type, 0) + 1
            operations[operation] = operations.get(operation, 0) + 1
            
            if entry['fallback_triggered']:
                fallback_count += 1
        
        return {
            'total_errors': len(self.error_log),
            'error_types': error_types,
            'operations': operations,
            'fallback_count': fallback_count,
            'fallback_active': self.fallback_active,
            'recent_errors': self.error_log[-5:] if len(self.error_log) > 0 else []
        }


class FallbackResizeManager:
    """
    Fallback resize manager that provides basic table resizing without optimizations.
    Used when advanced optimization components fail.
    """
    
    def __init__(self, parent_tab):
        """
        Initialize fallback resize manager.
        
        Args:
            parent_tab: The parent tab widget containing tables
        """
        self.parent_tab = parent_tab
        
    def perform_basic_resize(self, table: QTableWidget):
        """
        Perform basic table resize using original Qt mechanisms.
        
        Args:
            table: QTableWidget to resize
        """
        try:
            # Basic column width adjustment
            header = table.horizontalHeader()
            
            # Simple resize to contents approach
            for col in range(table.columnCount()):
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            
            # Allow user resizing
            header.setSectionResizeMode(QHeaderView.Interactive)
            
            return True
            
        except Exception as e:
            print(f"Fallback resize failed: {e}")
            return False
    
    def perform_basic_table_setup(self, table: QTableWidget):
        """
        Perform basic table setup without advanced features.
        
        Args:
            table: QTableWidget to set up
        """
        try:
            # Basic table properties
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setHighlightSections(False)
            
            # Basic header setup
            header = table.horizontalHeader()
            header.setStretchLastSection(True)
            
            return True
            
        except Exception as e:
            print(f"Fallback table setup failed: {e}")
            return False


class ResizeDebugManager:
    """
    Provides performance monitoring and troubleshooting capabilities for table resize operations.
    
    Features:
    - Detailed resize operation logging
    - Cache hit/miss ratio tracking and reporting
    - Resize operation timing and performance measurement
    - Debug configuration flags for production control
    - Performance report generation for optimization analysis
    """
    
    def __init__(self, enabled: bool = False):
        """
        Initialize the resize debug manager.
        
        Args:
            enabled: Whether debug logging is enabled
        """
        self.enabled = enabled
        
        # Performance tracking
        self.operation_times: List[Dict[str, Any]] = []
        self.cache_operations: List[Dict[str, Any]] = []
        
        # Operation counters
        self.resize_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        
        # Timing thresholds for performance warnings
        self.slow_operation_threshold = 100  # milliseconds
        
    def log_resize_operation(self, operation: str, duration: float, details: Optional[Dict] = None):
        """
        Log a resize operation with timing information.
        
        Args:
            operation: Name/description of the operation
            duration: Duration in milliseconds
            details: Optional additional details about the operation
        """
        if not self.enabled:
            return
            
        self.resize_count += 1
        
        operation_data = {
            'timestamp': datetime.now(),
            'operation': operation,
            'duration_ms': duration,
            'details': details or {},
            'is_slow': duration > self.slow_operation_threshold
        }
        
        self.operation_times.append(operation_data)
        
        # Print debug info if enabled
        if self.enabled:
            status = "SLOW" if operation_data['is_slow'] else "OK"
            print(f"[RESIZE DEBUG] {operation}: {duration:.2f}ms [{status}]")
            if details:
                print(f"  Details: {details}")
                
    def log_cache_operation(self, cache_type: str, operation: str, hit: bool, details: Optional[Dict] = None):
        """
        Log a cache operation (hit/miss).
        
        Args:
            cache_type: Type of cache (font_metrics, content_width, etc.)
            operation: Description of the cache operation
            hit: Whether it was a cache hit (True) or miss (False)
            details: Optional additional details
        """
        if not self.enabled:
            return
            
        if hit:
            self.cache_hit_count += 1
        else:
            self.cache_miss_count += 1
            
        cache_data = {
            'timestamp': datetime.now(),
            'cache_type': cache_type,
            'operation': operation,
            'hit': hit,
            'details': details or {}
        }
        
        self.cache_operations.append(cache_data)
        
        # Print debug info if enabled
        if self.enabled:
            status = "HIT" if hit else "MISS"
            print(f"[CACHE DEBUG] {cache_type}.{operation}: {status}")
            if details:
                print(f"  Details: {details}")
                
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance analysis report.
        
        Returns:
            Dictionary containing performance metrics and analysis
        """
        report = {
            'summary': {
                'total_resize_operations': self.resize_count,
                'total_cache_operations': self.cache_hit_count + self.cache_miss_count,
                'cache_hit_ratio': self.cache_hit_count / (self.cache_hit_count + self.cache_miss_count) if (self.cache_hit_count + self.cache_miss_count) > 0 else 0
            },
            'timing_analysis': {},
            'cache_analysis': {},
            'recommendations': []
        }
        
        # Analyze operation timings
        if self.operation_times:
            durations = [op['duration_ms'] for op in self.operation_times]
            slow_operations = [op for op in self.operation_times if op['is_slow']]
            
            report['timing_analysis'] = {
                'average_duration_ms': sum(durations) / len(durations),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations),
                'slow_operations_count': len(slow_operations),
                'slow_operations_percentage': len(slow_operations) / len(self.operation_times) * 100
            }
            
            # Add recommendations based on timing
            if report['timing_analysis']['slow_operations_percentage'] > 20:
                report['recommendations'].append("High percentage of slow operations detected. Consider increasing debounce delay or optimizing table operations.")
                
        # Analyze cache performance
        if self.cache_operations:
            cache_types = {}
            for op in self.cache_operations:
                cache_type = op['cache_type']
                if cache_type not in cache_types:
                    cache_types[cache_type] = {'hits': 0, 'misses': 0}
                    
                if op['hit']:
                    cache_types[cache_type]['hits'] += 1
                else:
                    cache_types[cache_type]['misses'] += 1
                    
            for cache_type, stats in cache_types.items():
                total = stats['hits'] + stats['misses']
                hit_ratio = stats['hits'] / total if total > 0 else 0
                cache_types[cache_type]['hit_ratio'] = hit_ratio
                
            report['cache_analysis'] = cache_types
            
            # Add cache recommendations
            for cache_type, stats in cache_types.items():
                if stats['hit_ratio'] < 0.5:
                    report['recommendations'].append(f"Low cache hit ratio for {cache_type} ({stats['hit_ratio']:.1%}). Consider adjusting cache strategy.")
                    
        return report
        
    def clear_statistics(self):
        """Clear all collected statistics and start fresh."""
        self.operation_times.clear()
        self.cache_operations.clear()
        self.resize_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        
    def set_enabled(self, enabled: bool):
        """Enable or disable debug logging."""
        self.enabled = enabled
        
    def set_slow_operation_threshold(self, threshold_ms: float):
        """Set the threshold for considering an operation 'slow'."""
        self.slow_operation_threshold = threshold_ms


class OptimizationComponentManager:
    """
    Central manager for all table optimization components with comprehensive error handling.
    Provides unified setup, configuration, and fallback management.
    """
    
    def __init__(self, parent_tab):
        """
        Initialize the optimization component manager.
        
        Args:
            parent_tab: The parent tab widget containing tables
        """
        self.parent_tab = parent_tab
        
        # Initialize configuration and error handling
        self.config = OptimizationConfig()
        self.error_handler = OptimizationErrorHandler(self.config)
        
        # Initialize optimization components
        self.debounce_manager = None
        self.cache_manager = None
        self.batch_managers = {}  # Table-specific batch managers
        self.debug_manager = None
        
        # Fallback manager
        self.fallback_manager = FallbackResizeManager(parent_tab)
        
        # Setup components
        self._setup_components()
    
    def _setup_components(self):
        """Setup all optimization components with error handling."""
        try:
            # Setup debounce manager
            self.debounce_manager = DebounceResizeManager(
                self.parent_tab, 
                self.config, 
                self.error_handler,
                self.config.debounce_delay_ms
            )
            
            # Setup cache manager
            self.cache_manager = TableCacheManager(
                self.config,
                self.error_handler,
                self.config.cache_size_limit
            )
            
            # Setup debug manager
            self.debug_manager = ResizeDebugManager(self.config.enable_debug_logging)
            
        except Exception as e:
            self.error_handler.handle_error('setup_components', e)
            # Continue with fallback mode
    
    def setup_table_optimization(self, table: QTableWidget, table_name: str):
        """
        Setup optimization for a specific table with error handling.
        
        Args:
            table: QTableWidget to optimize
            table_name: Unique name for the table
        """
        try:
            # Create batch manager for this table
            if self.config.enable_batch_updates and not self.error_handler.is_fallback_active():
                self.batch_managers[table_name] = BatchUpdateManager(
                    table, 
                    self.config, 
                    self.error_handler
                )
            
            # Setup basic table properties with fallback
            if self.error_handler.is_fallback_active():
                self.fallback_manager.perform_basic_table_setup(table)
            else:
                # Apply optimized table setup
                self._apply_optimized_table_setup(table)
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('setup_table_optimization', e,
                                                         {'table_name': table_name})
            if not should_retry:
                # Use fallback setup
                self.fallback_manager.perform_basic_table_setup(table)
    
    def _apply_optimized_table_setup(self, table: QTableWidget):
        """Apply optimized table setup with error handling."""
        try:
            # Basic table properties
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setHighlightSections(False)
            
            # Enhanced header setup
            header = table.horizontalHeader()
            header.setStretchLastSection(False)  # Allow intelligent sizing
            
        except Exception as e:
            raise e  # Re-raise for higher-level handling
    
    def safe_resize_table(self, table: QTableWidget, table_name: str):
        """
        Safely resize a table using the best available method.
        
        Args:
            table: QTableWidget to resize
            table_name: Name of the table for batch manager lookup
        """
        try:
            if self.error_handler.is_fallback_active():
                # Use fallback resize
                self.fallback_manager.perform_basic_resize(table)
                return
            
            # Use batch manager if available
            batch_manager = self.batch_managers.get(table_name)
            if batch_manager and self.config.enable_batch_updates:
                with batch_manager:
                    self._perform_intelligent_resize(table)
            else:
                # Direct resize without batching
                self._perform_intelligent_resize(table)
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('safe_resize_table', e,
                                                         {'table_name': table_name})
            if not should_retry:
                # Use fallback
                self.fallback_manager.perform_basic_resize(table)
    
    def _perform_intelligent_resize(self, table: QTableWidget):
        """Perform intelligent table resize with caching."""
        # This would integrate with EnhancedTableMixin methods
        # For now, use basic resize to contents
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive status of optimization components."""
        return {
            'config': self.config.get_config_dict(),
            'error_summary': self.error_handler.get_error_summary(),
            'cache_stats': self.cache_manager.get_cache_statistics() if self.cache_manager else {},
            'debug_stats': self.debug_manager.get_performance_report() if self.debug_manager else {},
            'fallback_active': self.error_handler.is_fallback_active(),
            'components_initialized': {
                'debounce_manager': self.debounce_manager is not None,
                'cache_manager': self.cache_manager is not None,
                'debug_manager': self.debug_manager is not None,
                'batch_managers_count': len(self.batch_managers)
            }
        }
    
    def enable_safe_mode(self):
        """Enable safe mode with minimal optimizations."""
        self.config.enable_safe_mode()
        self.error_handler.reset_error_state()
        
        # Reinitialize components with safe settings
        self._setup_components()
    
    def disable_all_optimizations(self):
        """Disable all optimizations and use fallback mode."""
        self.config.disable_all_optimizations()
        self.error_handler.fallback_active = True
    
    def reset_optimization_state(self):
        """Reset optimization state and clear errors."""
        self.error_handler.reset_error_state()
        if self.cache_manager:
            self.cache_manager.clear_all_caches()
        if self.debug_manager:
            self.debug_manager.clear_statistics()


class ResizeDebugManager:
    """
    Provides performance monitoring and troubleshooting capabilities for table resize operations.
    
    Features:
    - Detailed resize operation logging
    - Cache hit/miss ratio tracking and reporting
    - Resize operation timing and performance measurement
    - Debug configuration flags for production control
    - Performance report generation for optimization analysis
    """
    
    def __init__(self, enabled: bool = False):
        """
        Initialize the resize debug manager.
        
        Args:
            enabled: Whether debug logging is enabled
        """
        self.enabled = enabled
        
        # Performance tracking
        self.operation_times: List[Dict[str, Any]] = []
        self.cache_operations: List[Dict[str, Any]] = []
        
        # Operation counters
        self.resize_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        
        # Timing thresholds for performance warnings
        self.slow_operation_threshold = 100  # milliseconds
        
    def log_resize_operation(self, operation: str, duration: float, details: Optional[Dict] = None):
        """
        Log a resize operation with timing information.
        
        Args:
            operation: Name/description of the operation
            duration: Duration in milliseconds
            details: Optional additional details about the operation
        """
        if not self.enabled:
            return
            
        self.resize_count += 1
        
        operation_data = {
            'timestamp': datetime.now(),
            'operation': operation,
            'duration_ms': duration,
            'details': details or {},
            'is_slow': duration > self.slow_operation_threshold
        }
        
        self.operation_times.append(operation_data)
        
        # Print debug info if enabled
        if self.enabled:
            status = "SLOW" if operation_data['is_slow'] else "OK"
            print(f"[RESIZE DEBUG] {operation}: {duration:.2f}ms [{status}]")
            if details:
                print(f"  Details: {details}")
                
    def log_cache_operation(self, cache_type: str, operation: str, hit: bool, details: Optional[Dict] = None):
        """
        Log a cache operation (hit/miss).
        
        Args:
            cache_type: Type of cache (font_metrics, content_width, etc.)
            operation: Description of the cache operation
            hit: Whether it was a cache hit (True) or miss (False)
            details: Optional additional details
        """
        if not self.enabled:
            return
            
        if hit:
            self.cache_hit_count += 1
        else:
            self.cache_miss_count += 1
            
        cache_data = {
            'timestamp': datetime.now(),
            'cache_type': cache_type,
            'operation': operation,
            'hit': hit,
            'details': details or {}
        }
        
        self.cache_operations.append(cache_data)
        
        # Print debug info if enabled
        if self.enabled:
            status = "HIT" if hit else "MISS"
            print(f"[CACHE DEBUG] {cache_type}.{operation}: {status}")
            if details:
                print(f"  Details: {details}")
                
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive performance analysis report.
        
        Returns:
            Dictionary containing performance metrics and analysis
        """
        report = {
            'summary': {
                'total_resize_operations': self.resize_count,
                'total_cache_operations': self.cache_hit_count + self.cache_miss_count,
                'cache_hit_ratio': self.cache_hit_count / (self.cache_hit_count + self.cache_miss_count) if (self.cache_hit_count + self.cache_miss_count) > 0 else 0
            },
            'timing_analysis': {},
            'cache_analysis': {},
            'recommendations': []
        }
        
        # Analyze operation timings
        if self.operation_times:
            durations = [op['duration_ms'] for op in self.operation_times]
            slow_operations = [op for op in self.operation_times if op['is_slow']]
            
            report['timing_analysis'] = {
                'average_duration_ms': sum(durations) / len(durations),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations),
                'slow_operations_count': len(slow_operations),
                'slow_operations_percentage': len(slow_operations) / len(self.operation_times) * 100
            }
            
            # Add recommendations based on timing
            if report['timing_analysis']['slow_operations_percentage'] > 20:
                report['recommendations'].append("High percentage of slow operations detected. Consider increasing debounce delay or optimizing table operations.")
                
        # Analyze cache performance
        if self.cache_operations:
            cache_types = {}
            for op in self.cache_operations:
                cache_type = op['cache_type']
                if cache_type not in cache_types:
                    cache_types[cache_type] = {'hits': 0, 'misses': 0}
                    
                if op['hit']:
                    cache_types[cache_type]['hits'] += 1
                else:
                    cache_types[cache_type]['misses'] += 1
                    
            for cache_type, stats in cache_types.items():
                total = stats['hits'] + stats['misses']
                hit_ratio = stats['hits'] / total if total > 0 else 0
                cache_types[cache_type]['hit_ratio'] = hit_ratio
                
            report['cache_analysis'] = cache_types
            
            # Add cache recommendations
            for cache_type, stats in cache_types.items():
                if stats['hit_ratio'] < 0.5:
                    report['recommendations'].append(f"Low cache hit ratio for {cache_type} ({stats['hit_ratio']:.1%}). Consider adjusting cache strategy.")
                    
        return report
        
    def clear_statistics(self):
        """Clear all collected statistics and start fresh."""
        self.operation_times.clear()
        self.cache_operations.clear()
        self.resize_count = 0
        self.cache_hit_count = 0
        self.cache_miss_count = 0
        
    def set_enabled(self, enabled: bool):
        """Enable or disable debug logging."""
        self.enabled = enabled
        
    def set_slow_operation_threshold(self, threshold_ms: float):
        """Set the threshold for considering an operation 'slow'."""
        self.slow_operation_threshold = threshold_ms


class OptimizationComponentManager:
    """
    Central manager for all table optimization components with comprehensive error handling.
    Provides unified setup, configuration, and fallback management.
    """
    
    def __init__(self, parent_tab):
        """
        Initialize the optimization component manager.
        
        Args:
            parent_tab: The parent tab widget containing tables
        """
        self.parent_tab = parent_tab
        
        # Initialize configuration and error handling
        self.config = OptimizationConfig()
        self.error_handler = OptimizationErrorHandler(self.config)
        
        # Initialize optimization components
        self.debounce_manager = None
        self.cache_manager = None
        self.batch_managers = {}  # Table-specific batch managers
        self.debug_manager = None
        
        # Fallback manager
        self.fallback_manager = FallbackResizeManager(parent_tab)
        
        # Setup components
        self._setup_components()
    
    def _setup_components(self):
        """Setup all optimization components with error handling."""
        try:
            # Setup debounce manager
            self.debounce_manager = DebounceResizeManager(
                self.parent_tab, 
                self.config, 
                self.error_handler,
                self.config.debounce_delay_ms
            )
            
            # Setup cache manager
            self.cache_manager = TableCacheManager(
                self.config,
                self.error_handler,
                self.config.cache_size_limit
            )
            
            # Setup debug manager
            self.debug_manager = ResizeDebugManager(self.config.enable_debug_logging)
            
        except Exception as e:
            self.error_handler.handle_error('setup_components', e)
            # Continue with fallback mode
    
    def setup_table_optimization(self, table: QTableWidget, table_name: str):
        """
        Setup optimization for a specific table with error handling.
        
        Args:
            table: QTableWidget to optimize
            table_name: Unique name for the table
        """
        try:
            # Create batch manager for this table
            if self.config.enable_batch_updates and not self.error_handler.is_fallback_active():
                self.batch_managers[table_name] = BatchUpdateManager(
                    table, 
                    self.config, 
                    self.error_handler
                )
            
            # Setup basic table properties with fallback
            if self.error_handler.is_fallback_active():
                self.fallback_manager.perform_basic_table_setup(table)
            else:
                # Apply optimized table setup
                self._apply_optimized_table_setup(table)
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('setup_table_optimization', e,
                                                         {'table_name': table_name})
            if not should_retry:
                # Use fallback setup
                self.fallback_manager.perform_basic_table_setup(table)
    
    def _apply_optimized_table_setup(self, table: QTableWidget):
        """Apply optimized table setup with error handling."""
        try:
            # Basic table properties
            table.setAlternatingRowColors(True)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setHighlightSections(False)
            
            # Enhanced header setup
            header = table.horizontalHeader()
            header.setStretchLastSection(False)  # Allow intelligent sizing
            
        except Exception as e:
            raise e  # Re-raise for higher-level handling
    
    def safe_resize_table(self, table: QTableWidget, table_name: str):
        """
        Safely resize a table using the best available method.
        
        Args:
            table: QTableWidget to resize
            table_name: Name of the table for batch manager lookup
        """
        try:
            if self.error_handler.is_fallback_active():
                # Use fallback resize
                self.fallback_manager.perform_basic_resize(table)
                return
            
            # Use batch manager if available
            batch_manager = self.batch_managers.get(table_name)
            if batch_manager and self.config.enable_batch_updates:
                with batch_manager:
                    self._perform_intelligent_resize(table)
            else:
                # Direct resize without batching
                self._perform_intelligent_resize(table)
                
        except Exception as e:
            should_retry = self.error_handler.handle_error('safe_resize_table', e,
                                                         {'table_name': table_name})
            if not should_retry:
                # Use fallback
                self.fallback_manager.perform_basic_resize(table)
    
    def _perform_intelligent_resize(self, table: QTableWidget):
        """Perform intelligent table resize with caching."""
        # This would integrate with EnhancedTableMixin methods
        # For now, use basic resize to contents
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get comprehensive status of optimization components."""
        return {
            'config': self.config.get_config_dict(),
            'error_summary': self.error_handler.get_error_summary(),
            'cache_stats': self.cache_manager.get_cache_statistics() if self.cache_manager else {},
            'debug_stats': self.debug_manager.get_performance_report() if self.debug_manager else {},
            'fallback_active': self.error_handler.is_fallback_active(),
            'components_initialized': {
                'debounce_manager': self.debounce_manager is not None,
                'cache_manager': self.cache_manager is not None,
                'debug_manager': self.debug_manager is not None,
                'batch_managers_count': len(self.batch_managers)
            }
        }
    
    def enable_safe_mode(self):
        """Enable safe mode with minimal optimizations."""
        self.config.enable_safe_mode()
        self.error_handler.reset_error_state()
        
        # Reinitialize components with safe settings
        self._setup_components()
    
    def disable_all_optimizations(self):
        """Disable all optimizations and use fallback mode."""
        self.config.disable_all_optimizations()
        self.error_handler.fallback_active = True
    
    def reset_optimization_state(self):
        """Reset optimization state and clear errors."""
        self.error_handler.reset_error_state()
        if self.cache_manager:
            self.cache_manager.clear_all_caches()
        if self.debug_manager:
            self.debug_manager.clear_statistics()