from PyQt5.QtCore import Qt, QPoint, QRect, QSize
from PyQt5.QtWidgets import QLayout, QSizePolicy


class FlowLayout(QLayout):
    """
    Custom layout that wraps widgets to new lines when space is limited.
    
    Enhanced version with improved geometry calculation, optimization,
    and configuration options for responsive behavior.
    """
    
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)

        self.itemList = []
        
        # Enhanced configuration options
        self._horizontal_spacing = spacing
        self._vertical_spacing = spacing
        self._alignment = Qt.AlignLeft | Qt.AlignTop
        self._wrap_policy = True  # Allow wrapping to new lines
        self._uniform_item_sizes = False  # Whether to make all items the same size
        
        # Performance optimization caches
        self._cached_size_hint = None
        self._cached_minimum_size = None
        self._cache_valid = False

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)
        self._invalidate_cache()

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]

        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            self._invalidate_cache()
            return self.itemList.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())

        margin, _, _, _ = self.getContentsMargins()

        size += QSize(2 * margin, 2 * margin)
        return size

    def _do_layout(self, rect, test_only):
        if not self.itemList:
            return 0
            
        x = rect.x()
        y = rect.y()
        line_height = 0
        
        # Calculate uniform item size if enabled
        uniform_size = None
        if self._uniform_item_sizes and self.itemList:
            max_width = max(item.sizeHint().width() for item in self.itemList)
            max_height = max(item.sizeHint().height() for item in self.itemList)
            uniform_size = QSize(max_width, max_height)

        for item in self.itemList:
            wid = item.widget()
            if not wid:
                continue
                
            # Use configured spacing or calculate from style
            h_spacing = self.horizontalSpacing()
            v_spacing = self.verticalSpacing()
            
            if h_spacing < 0:
                h_spacing = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            if v_spacing < 0:
                v_spacing = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            
            # Determine item size
            item_size = uniform_size if uniform_size else item.sizeHint()
            
            # Check if we need to wrap to next line
            next_x = x + item_size.width() + h_spacing
            if self._wrap_policy and next_x - h_spacing > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + v_spacing
                next_x = x + item_size.width() + h_spacing
                line_height = 0

            if not test_only:
                # Apply alignment within the item's allocated space
                item_rect = QRect(QPoint(x, y), item_size)
                
                # Handle alignment
                if self._alignment & Qt.AlignRight:
                    item_rect.moveRight(x + item_size.width())
                elif self._alignment & Qt.AlignHCenter:
                    item_rect.moveLeft(x + (item_size.width() - item.sizeHint().width()) // 2)
                
                if self._alignment & Qt.AlignBottom:
                    item_rect.moveBottom(y + item_size.height())
                elif self._alignment & Qt.AlignVCenter:
                    item_rect.moveTop(y + (item_size.height() - item.sizeHint().height()) // 2)
                
                item.setGeometry(item_rect)

            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y()
    
    def _invalidate_cache(self):
        """Invalidate cached size calculations."""
        self._cache_valid = False
        self._cached_size_hint = None
        self._cached_minimum_size = None
    
    def setHorizontalSpacing(self, spacing):
        """Set horizontal spacing between items."""
        self._horizontal_spacing = spacing
        self._invalidate_cache()
        self.update()
    
    def setVerticalSpacing(self, spacing):
        """Set vertical spacing between items."""
        self._vertical_spacing = spacing
        self._invalidate_cache()
        self.update()
    
    def horizontalSpacing(self):
        """Get horizontal spacing between items."""
        return self._horizontal_spacing if self._horizontal_spacing >= 0 else self.spacing()
    
    def verticalSpacing(self):
        """Get vertical spacing between items."""
        return self._vertical_spacing if self._vertical_spacing >= 0 else self.spacing()
    
    def setAlignment(self, alignment):
        """Set alignment for items within the layout."""
        self._alignment = alignment
        self.update()
    
    def alignment(self):
        """Get current alignment setting."""
        return self._alignment
    
    def setWrapPolicy(self, wrap):
        """Set whether items should wrap to new lines."""
        self._wrap_policy = wrap
        self._invalidate_cache()
        self.update()
    
    def wrapPolicy(self):
        """Get current wrap policy."""
        return self._wrap_policy
    
    def setUniformItemSizes(self, uniform):
        """Set whether all items should have uniform sizes."""
        self._uniform_item_sizes = uniform
        self._invalidate_cache()
        self.update()
    
    def uniformItemSizes(self):
        """Get whether items have uniform sizes."""
        return self._uniform_item_sizes