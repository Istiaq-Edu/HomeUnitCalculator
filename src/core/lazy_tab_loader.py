"""
Lazy Tab Loader for Home Unit Calculator
Defers tab initialization until first access to improve startup time
"""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QTimer


class LazyTabLoader:
    """
    Manages lazy loading of application tabs.
    Tabs are created only when first accessed by the user.
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self._tab_cache = {}
        self._tab_factories = {}
        self._loading_placeholders = {}
    
    def register_tab(self, tab_name, factory_func, eager_load=False):
        """
        Register a tab with its factory function.
        
        Args:
            tab_name: Unique identifier for the tab
            factory_func: Callable that creates and returns the tab widget
            eager_load: If True, load immediately; if False, load on first access
        """
        self._tab_factories[tab_name] = factory_func
        
        if eager_load:
            # Load immediately
            self._tab_cache[tab_name] = factory_func()
        else:
            # Create placeholder
            self._loading_placeholders[tab_name] = self._create_placeholder(tab_name)
    
    def get_tab(self, tab_name):
        """
        Get a tab instance, creating it if necessary.
        
        Args:
            tab_name: Unique identifier for the tab
            
        Returns:
            The tab widget instance
        """
        # Return cached instance if available
        if tab_name in self._tab_cache:
            return self._tab_cache[tab_name]
        
        # Check if factory exists
        if tab_name not in self._tab_factories:
            raise ValueError(f"Tab '{tab_name}' not registered")
        
        # Create tab instance
        print(f"[LazyTabLoader] Loading tab: {tab_name}")
        tab_instance = self._tab_factories[tab_name]()
        self._tab_cache[tab_name] = tab_instance
        
        # Remove placeholder if it exists
        if tab_name in self._loading_placeholders:
            del self._loading_placeholders[tab_name]
        
        return tab_instance
    
    def get_placeholder(self, tab_name):
        """Get the loading placeholder for a tab"""
        return self._loading_placeholders.get(tab_name)
    
    def is_loaded(self, tab_name):
        """Check if a tab has been loaded"""
        return tab_name in self._tab_cache
    
    def preload_tab(self, tab_name):
        """Preload a tab in the background"""
        if not self.is_loaded(tab_name):
            # Use QTimer to load asynchronously
            QTimer.singleShot(0, lambda: self.get_tab(tab_name))
    
    def _create_placeholder(self, tab_name):
        """Create a simple placeholder widget"""
        from PyQt5.QtWidgets import QVBoxLayout, QLabel
        from PyQt5.QtCore import Qt
        
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel(f"Loading {tab_name}...")
        label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return placeholder
    
    def get_all_loaded_tabs(self):
        """Get list of all loaded tab names"""
        return list(self._tab_cache.keys())
    
    def clear_cache(self):
        """Clear all cached tabs (useful for testing)"""
        self._tab_cache.clear()


class DeferredImporter:
    """
    Manages deferred imports to reduce startup time.
    Heavy modules are imported only when needed.
    """
    
    _imports = {}
    
    @classmethod
    def get_reportlab(cls):
        """Get reportlab modules (for PDF generation)"""
        if 'reportlab' not in cls._imports:
            print("[DeferredImporter] Loading reportlab...")
            from reportlab.lib.units import inch
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            
            cls._imports['reportlab'] = {
                'inch': inch,
                'letter': letter,
                'SimpleDocTemplate': SimpleDocTemplate,
                'Table': Table,
                'TableStyle': TableStyle,
                'Paragraph': Paragraph,
                'Spacer': Spacer,
                'getSampleStyleSheet': getSampleStyleSheet,
                'ParagraphStyle': ParagraphStyle,
                'colors': colors,
                'TA_CENTER': TA_CENTER,
            }
        
        return cls._imports['reportlab']
    
    @classmethod
    def get_pil(cls):
        """Get PIL modules (for image processing)"""
        if 'pil' not in cls._imports:
            print("[DeferredImporter] Loading PIL...")
            from PIL import Image
            cls._imports['pil'] = {'Image': Image}
        
        return cls._imports['pil']
    
    @classmethod
    def clear_cache(cls):
        """Clear import cache (useful for testing)"""
        cls._imports.clear()


# Example usage in HomeUnitCalculator.py:
"""
# In __init__:
self.tab_loader = LazyTabLoader(self)

# Register tabs
self.tab_loader.register_tab('main', lambda: MainTab(self), eager_load=True)
self.tab_loader.register_tab('rooms', lambda: RoomsTab(self.main_tab_instance, self))
self.tab_loader.register_tab('history', lambda: HistoryTab(self))
self.tab_loader.register_tab('rental', lambda: RentalInfoTab(self))
self.tab_loader.register_tab('archived', lambda: ArchivedInfoTab(self))
self.tab_loader.register_tab('config', lambda: SupabaseConfigTab(self))

# Access tabs
@property
def main_tab_instance(self):
    return self.tab_loader.get_tab('main')

@property
def rooms_tab_instance(self):
    return self.tab_loader.get_tab('rooms')

# In navigation setup:
def on_tab_changed(self, tab_name):
    tab = self.tab_loader.get_tab(tab_name)
    # Switch to tab
"""
