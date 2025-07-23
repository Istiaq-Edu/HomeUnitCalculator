"""
Responsive image components for dynamic scaling and preview functionality.

This module provides image widgets that automatically scale with their containers
while maintaining aspect ratio and providing efficient caching.
"""

from typing import Optional, Dict
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QResizeEvent
from PyQt5.QtWidgets import QLabel, QSizePolicy
import os


class ResponsiveImageLabel(QLabel):
    """
    A QLabel that automatically scales its image content to fit the container
    while maintaining aspect ratio and providing efficient caching.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap: Optional[QPixmap] = None
        self._cached_pixmaps: Dict[tuple, QPixmap] = {}
        self._max_cache_size = 10  # Limit cache to prevent memory issues
        
        # Set up responsive behavior
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(50, 50)  # Reasonable minimum size
        self.setScaledContents(False)  # We'll handle scaling manually for better quality
        
        # Default styling
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #cccccc;
                border-radius: 8px;
                background-color: #f8f9fa;
                color: #6c757d;
            }
            QLabel:hover {
                border-color: #007bff;
                background-color: #e3f2fd;
            }
        """)
    
    def setPixmap(self, pixmap: QPixmap):
        """Set the pixmap and store original for scaling."""
        if pixmap and not pixmap.isNull():
            self._original_pixmap = pixmap
            self._cached_pixmaps.clear()  # Clear cache when new image is set
            self._update_scaled_pixmap()
        else:
            self._original_pixmap = None
            self._cached_pixmaps.clear()
            super().setPixmap(QPixmap())  # Clear the display
    
    def setImagePath(self, path: str, placeholder_text: str = "No Image"):
        """Load image from file path with error handling."""
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.setPixmap(pixmap)
                self.setText("")  # Clear any placeholder text
                return True
            else:
                self._show_placeholder(f"Invalid Image: {placeholder_text}")
                return False
        else:
            self._show_placeholder(placeholder_text)
            return False
    
    def setImageData(self, data: bytes, placeholder_text: str = "No Image"):
        """Load image from binary data (e.g., from network request)."""
        if data:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.setPixmap(pixmap)
                self.setText("")  # Clear any placeholder text
                return True
            else:
                self._show_placeholder(f"Invalid Image Data: {placeholder_text}")
                return False
        else:
            self._show_placeholder(placeholder_text)
            return False
    
    def _show_placeholder(self, text: str):
        """Show placeholder text when no valid image is available."""
        self._original_pixmap = None
        self._cached_pixmaps.clear()
        super().setPixmap(QPixmap())  # Clear any existing pixmap
        self.setText(text)
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize events to update image scaling."""
        super().resizeEvent(event)
        if self._original_pixmap:
            self._update_scaled_pixmap()
    
    def _update_scaled_pixmap(self):
        """Update the displayed pixmap to fit current size."""
        if not self._original_pixmap:
            return
        
        # Get current size minus some padding for borders
        current_size = self.size()
        target_size = QSize(
            max(current_size.width() - 10, 10),  # Account for border/padding
            max(current_size.height() - 10, 10)
        )
        
        # Convert QSize to tuple for use as dictionary key
        size_key = (target_size.width(), target_size.height())
        
        # Check cache first
        if size_key in self._cached_pixmaps:
            super().setPixmap(self._cached_pixmaps[size_key])
            return
        
        # Scale the image maintaining aspect ratio
        scaled_pixmap = self._original_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Cache the scaled pixmap (with size limit)
        if len(self._cached_pixmaps) >= self._max_cache_size:
            # Remove oldest cached item (simple FIFO)
            oldest_key = next(iter(self._cached_pixmaps))
            del self._cached_pixmaps[oldest_key]
        
        self._cached_pixmaps[size_key] = scaled_pixmap
        super().setPixmap(scaled_pixmap)
    
    def clearImage(self):
        """Clear the current image and show placeholder."""
        self._show_placeholder("No Image")
    
    def hasImage(self) -> bool:
        """Check if a valid image is currently loaded."""
        return self._original_pixmap is not None and not self._original_pixmap.isNull()
    
    def getOriginalSize(self) -> Optional[QSize]:
        """Get the original size of the loaded image."""
        if self._original_pixmap:
            return self._original_pixmap.size()
        return None


class ResponsiveImagePreviewGrid(QLabel):
    """
    A specialized responsive image label for grid layouts that maintains
    consistent sizing within a grid while still being responsive.
    """
    
    def __init__(self, parent=None, aspect_ratio: float = 1.0):
        super().__init__(parent)
        self._aspect_ratio = aspect_ratio  # width/height ratio to maintain
        self._original_pixmap: Optional[QPixmap] = None
        self._cached_pixmaps: Dict[tuple, QPixmap] = {}
        
        # Set up responsive behavior for grid context
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(80, 80)  # Smaller minimum for grid context
        self.setScaledContents(False)
        
        # Grid-appropriate styling
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                background-color: #ffffff;
                color: #6c757d;
                font-size: 12px;
            }
            QLabel:hover {
                border-color: #007bff;
                background-color: #f8f9fa;
            }
        """)
    
    def sizeHint(self) -> QSize:
        """Provide size hint based on aspect ratio."""
        base_size = super().sizeHint()
        if self._aspect_ratio > 1.0:
            # Wider than tall
            return QSize(int(base_size.height() * self._aspect_ratio), base_size.height())
        else:
            # Taller than wide
            return QSize(base_size.width(), int(base_size.width() / self._aspect_ratio))
    
    def setPixmap(self, pixmap: QPixmap):
        """Set pixmap with grid-appropriate scaling."""
        if pixmap and not pixmap.isNull():
            self._original_pixmap = pixmap
            self._cached_pixmaps.clear()
            self._update_scaled_pixmap()
        else:
            self._original_pixmap = None
            self._cached_pixmaps.clear()
            super().setPixmap(QPixmap())
    
    def setImagePath(self, path: str, placeholder_text: str = "No Preview"):
        """Load image from file path with grid-appropriate placeholder."""
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.setPixmap(pixmap)
                self.setText("")
                return True
        
        self._show_placeholder(placeholder_text)
        return False
    
    def setImageData(self, data: bytes, placeholder_text: str = "No Preview"):
        """Load image from binary data (e.g., from network request)."""
        if data:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.setPixmap(pixmap)
                self.setText("")
                return True
            else:
                self._show_placeholder(f"Invalid Image Data: {placeholder_text}")
                return False
        else:
            self._show_placeholder(placeholder_text)
            return False
    
    def _show_placeholder(self, text: str):
        """Show compact placeholder text for grid context."""
        self._original_pixmap = None
        self._cached_pixmaps.clear()
        super().setPixmap(QPixmap())
        self.setText(text)
    
    def resizeEvent(self, event: QResizeEvent):
        """Handle resize with aspect ratio consideration."""
        super().resizeEvent(event)
        if self._original_pixmap:
            self._update_scaled_pixmap()
    
    def _update_scaled_pixmap(self):
        """Update scaled pixmap for grid context."""
        if not self._original_pixmap:
            return
        
        # Calculate target size maintaining aspect ratio
        current_size = self.size()
        target_width = current_size.width() - 6  # Account for border
        target_height = current_size.height() - 6
        
        # Maintain aspect ratio
        if self._aspect_ratio > 1.0:
            target_height = min(target_height, int(target_width / self._aspect_ratio))
        else:
            target_width = min(target_width, int(target_height * self._aspect_ratio))
        
        target_size = QSize(max(target_width, 10), max(target_height, 10))
        
        # Convert QSize to tuple for use as dictionary key
        size_key = (target_size.width(), target_size.height())
        
        # Use caching similar to ResponsiveImageLabel
        if size_key in self._cached_pixmaps:
            super().setPixmap(self._cached_pixmaps[size_key])
            return
        
        scaled_pixmap = self._original_pixmap.scaled(
            target_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Simple cache management
        if len(self._cached_pixmaps) >= 5:  # Smaller cache for grid items
            oldest_key = next(iter(self._cached_pixmaps))
            del self._cached_pixmaps[oldest_key]
        
        self._cached_pixmaps[size_key] = scaled_pixmap
        super().setPixmap(scaled_pixmap)