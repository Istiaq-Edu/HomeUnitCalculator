"""
Refactored Rental Record Dialog with modern purple theme and side-by-side layout.
Matches the design of EditRecordDialog for consistency.
"""
import sys
import traceback
import os
from datetime import datetime
from collections import namedtuple

from PyQt5.QtCore import Qt, QUrl, QSize, QStandardPaths
from PyQt5.QtGui import QPixmap, QColor, QCursor
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QMessageBox, QWidget,
    QGridLayout, QPushButton, QFrame
)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QNetworkDiskCache
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, TitleLabel, FluentIcon, BodyLabel
)

from .responsive_components import ResponsiveDialog
from .responsive_image import ResponsiveImagePreviewGrid
from .background_workers import FetchImageWorker, FetchMultipleImagesWorker
from .custom_widgets import AutoScrollArea

# Suppress SSL certificate warnings
try:
    import urllib3
except ModuleNotFoundError:
    import requests.packages.urllib3 as urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define a namedtuple for rental records
RentalRecord = namedtuple('RentalRecord', [
    'id', 'tenant_name', 'room_number', 'advanced_paid', 'created_at',
    'updated_at', 'photo_path', 'nid_front_path', 'nid_back_path',
    'police_form_path', 'is_archived', 'supabase_id',
    'photo_url', 'nid_front_url', 'nid_back_url', 'police_form_url'
])

# Custom CardWidget without hover effects
class StaticCardWidget(CardWidget):
    """CardWidget that disables hover effects."""
    def enterEvent(self, event):
        return
    def leaveEvent(self, event):
        return


class ConfirmDialog(ResponsiveDialog):
    """Custom confirmation dialog with purple theme."""
    
    def __init__(self, parent=None, title="Confirm", message="Are you sure?", icon_type="question"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.result_value = False
        
        # Main container
        container = QWidget()
        container.setObjectName("confirmContainer")
        container.setStyleSheet("""
            QWidget#confirmContainer {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title bar
        self._create_title_bar(container_layout, title)
        
        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #2b2b2b; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.addWidget(content_widget)
        
        # Message with icon
        message_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel()
        if icon_type == "question":
            icon_label.setPixmap(FluentIcon.INFO.icon(color=QColor(108, 92, 231)).pixmap(48, 48))
        elif icon_type == "warning":
            icon_label.setPixmap(FluentIcon.DELETE.icon(color=QColor(198, 40, 40)).pixmap(48, 48))
        message_layout.addWidget(icon_label)
        
        # Message text
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #ffffff; font-size: 14px; padding-left: 10px;")
        message_layout.addWidget(message_label, 1)
        
        content_layout.addLayout(message_layout)
        content_layout.addSpacing(20)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # No button (Gray)
        no_btn = PrimaryPushButton("No")
        no_btn.setFixedHeight(36)
        no_btn.setFixedWidth(100)
        no_btn.clicked.connect(self.reject)
        no_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #757575;
                border: 1px solid #757575;
                border-radius: 6px;
                font-weight: bold;
            }
            PrimaryPushButton:hover {
                background-color: #9e9e9e;
            }
            PrimaryPushButton:pressed {
                background-color: #616161;
            }
        """)
        button_layout.addWidget(no_btn)
        
        # Yes button (Red for delete)
        yes_btn = PrimaryPushButton("Yes")
        yes_btn.setFixedHeight(36)
        yes_btn.setFixedWidth(100)
        yes_btn.clicked.connect(self._on_yes)
        yes_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #c62828;
                border: 1px solid #c62828;
                border-radius: 6px;
                font-weight: bold;
            }
            PrimaryPushButton:hover {
                background-color: #d84315;
            }
            PrimaryPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        button_layout.addWidget(yes_btn)
        
        content_layout.addLayout(button_layout)
    
    def _create_title_bar(self, layout, title):
        """Create custom title bar."""
        title_bar = QWidget()
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1f1f1f;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 8, 8, 8)
        
        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(FluentIcon.INFO.icon(color=QColor(108, 92, 231)).pixmap(18, 18))
        title_bar_layout.addWidget(icon_label)
        
        # Title
        title_text = QLabel(title)
        title_text.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; background: transparent;")
        title_bar_layout.addWidget(title_text)
        title_bar_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #c42b1c;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
                padding-bottom: 2px;
                margin: 0px;
                line-height: 32px;
            }
            QPushButton:hover {
                background-color: #d84315;
            }
            QPushButton:pressed {
                background-color: #a02315;
            }
        """)
        title_bar_layout.addWidget(close_btn)
        
        # Draggable
        title_bar.mousePressEvent = lambda e: setattr(self, '_drag_pos', e.globalPos() - self.frameGeometry().topLeft()) if e.button() == Qt.LeftButton else None
        title_bar.mouseMoveEvent = lambda e: self.move(e.globalPos() - self._drag_pos) if e.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos') else None
        
        layout.addWidget(title_bar)
    
    def _on_yes(self):
        """Handle Yes button click."""
        self.result_value = True
        self.accept()
    
    @staticmethod
    def ask(parent, title, message, icon_type="question"):
        """Show confirmation dialog and return True if Yes clicked."""
        dialog = ConfirmDialog(parent, title, message, icon_type)
        dialog.exec_()
        return dialog.result_value


class RentalRecordDialog(ResponsiveDialog):
    """Refactored rental record dialog with modern purple theme and side-by-side layout."""
    
    def __init__(self, parent=None, record_data=None, db_manager=None, supabase_manager=None, 
                 is_archived_record=False, main_window_ref=None, current_source="Local DB", supabase_id=None):
        super().__init__(parent)
        
        if db_manager is None:
            raise ValueError("db_manager is required for dialog operations")
        if record_data is None:
            raise ValueError("record_data is required to display record details")
        
        self.db_manager = db_manager
        self.supabase_manager = supabase_manager
        self.main_window = main_window_ref
        self.current_source = current_source
        self.supabase_id = supabase_id or record_data.get("supabase_id")
        self.is_archived_record = is_archived_record
        
        # Convert dictionary to namedtuple
        self.record_data = RentalRecord(
            id=record_data.get('id'),
            tenant_name=record_data.get('tenant_name'),
            room_number=record_data.get('room_number'),
            advanced_paid=record_data.get('advanced_paid'),
            created_at=record_data.get('created_at'),
            updated_at=record_data.get('updated_at'),
            photo_path=record_data.get('photo_path'),
            nid_front_path=record_data.get('nid_front_path'),
            nid_back_path=record_data.get('nid_back_path'),
            police_form_path=record_data.get('police_form_path'),
            is_archived=record_data.get('is_archived'),
            supabase_id=record_data.get('supabase_id'),
            photo_url=record_data.get('photo_url'),
            nid_front_url=record_data.get('nid_front_url'),
            nid_back_url=record_data.get('nid_back_url'),
            police_form_url=record_data.get('police_form_url')
        )
        
        # Async image loading state
        self._image_cache = {}
        self._image_workers = {}
        self._current_image_urls = {}
        self._parallel_fetch_worker = None  # For parallel image fetching
        
        # Network manager for image loading
        self._qnam = QNetworkAccessManager(self)
        cache = QNetworkDiskCache(self)
        cache_dir = QStandardPaths.writableLocation(QStandardPaths.CacheLocation)
        if cache_dir:
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except Exception:
                pass
            cache.setCacheDirectory(cache_dir)
            cache.setMaximumCacheSize(50 * 1024 * 1024)
            self._qnam.setCache(cache)
        
        self.init_ui()
        self.display_record_details()

    
    def init_ui(self):
        """Initialize the UI with modern purple theme and side-by-side layout."""
        self.setWindowTitle("Rental Record Details")
        
        # Set minimum dialog size to prevent horizontal scrollbar in info section
        self.setMinimumWidth(1200)
        self.setMinimumHeight(700)
        
        # Enable translucent background for rounded corners
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main container with rounded corners
        container = QWidget()
        container.setObjectName("dialogContainer")
        container.setStyleSheet("""
            QWidget#dialogContainer {
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            StaticCardWidget {
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                background-color: rgba(61, 61, 61, 0.3);
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Custom title bar
        self._create_title_bar(container_layout)
        
        # Content container
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.addWidget(content_widget)
        
        # Main header
        self._create_main_header(content_layout)
        
        # Horizontal sections (Informations | Document Preview)
        self._create_horizontal_sections(content_layout)
        
        # Generated PDF section
        self._create_pdf_section(content_layout)
        
        # Action buttons
        self._create_action_buttons(content_layout)

    
    def _create_title_bar(self, layout):
        """Create custom dark title bar with app icon and close button."""
        title_bar = QWidget()
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1f1f1f;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(10, 8, 8, 8)
        title_bar_layout.setSpacing(8)
        
        # App icon
        app_icon_label = QLabel()
        try:
            from src.core.utils import resource_path
            icon_path = resource_path("icons/icon.png")
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    app_icon_label.setPixmap(pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    app_icon_label.setPixmap(FluentIcon.DOCUMENT.icon(color=QColor(108, 92, 231)).pixmap(18, 18))
            else:
                app_icon_label.setPixmap(FluentIcon.DOCUMENT.icon(color=QColor(108, 92, 231)).pixmap(18, 18))
        except:
            app_icon_label.setPixmap(FluentIcon.DOCUMENT.icon(color=QColor(108, 92, 231)).pixmap(18, 18))
        title_bar_layout.addWidget(app_icon_label)
        
        # Title text
        title_text = QLabel("Rental Record Details")
        title_text.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; background: transparent;")
        title_bar_layout.addWidget(title_text)
        title_bar_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #c42b1c;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                padding: 0px;
                padding-bottom: 2px;
                line-height: 32px;
            }
            QPushButton:hover {
                background-color: #d84315;
            }
            QPushButton:pressed {
                background-color: #a02315;
            }
        """)
        title_bar_layout.addWidget(close_btn)
        
        # Make title bar draggable
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move
        self._drag_pos = None
        
        layout.addWidget(title_bar)

    
    def title_bar_mouse_press(self, event):
        """Handle mouse press on title bar for dragging."""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def title_bar_mouse_move(self, event):
        """Handle mouse move on title bar for dragging."""
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
    
    def _create_main_header(self, layout):
        """Create main header with tenant name."""
        tenant_name = self.record_data.tenant_name or "Unknown Tenant"
        header_label = TitleLabel(f"Record for: {tenant_name}")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("""
            color: #6C5CE7;
            font-weight: bold;
            font-size: 28px;
            padding-bottom: 3px;
        """)
        layout.addWidget(header_label)
        
        # Purple divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #6C5CE7; min-height: 3px; max-height: 3px;")
        layout.addWidget(divider)
        layout.addSpacing(5)

    
    def _create_horizontal_sections(self, layout):
        """Create side-by-side sections for Informations and Document Preview."""
        sections_layout = QHBoxLayout()
        
        # LEFT: Informations section (30%)
        info_section = StaticCardWidget()
        info_section.setMaximumWidth(500)
        info_section.setMinimumWidth(450)
        info_layout = QVBoxLayout(info_section)
        
        # Section header
        info_header = TitleLabel("Informations")
        info_header.setAlignment(Qt.AlignCenter)
        info_header.setStyleSheet("""
            color: #6C5CE7;
            font-weight: bold;
            font-size: 20px;
            padding-bottom: 2px;
        """)
        info_layout.addWidget(info_header)
        
        # Purple divider
        info_divider = QFrame()
        info_divider.setFrameShape(QFrame.HLine)
        info_divider.setStyleSheet("background-color: #6C5CE7; min-height: 2px; max-height: 2px;")
        info_layout.addWidget(info_divider)
        info_layout.addSpacing(3)
        
        # Scroll area for information
        info_scroll = AutoScrollArea()
        info_scroll.setWidgetResizable(True)
        info_widget = QWidget()
        info_vbox = QVBoxLayout(info_widget)
        info_vbox.setContentsMargins(10, 10, 10, 10)
        info_vbox.setSpacing(8)
        info_scroll.setWidget(info_widget)
        info_layout.addWidget(info_scroll)
        
        # Information labels (initialize first)
        self.tenant_name_label = QLabel()
        self.room_number_label = QLabel()
        self.advanced_paid_label = QLabel()
        self.created_at_label = QLabel()
        self.updated_at_label = QLabel()
        
        # Tenant Name with frosted container (horizontal layout) - White
        tenant_name_container = QWidget()
        tenant_name_container.setAttribute(Qt.WA_StyledBackground, True)
        tenant_name_container.setAutoFillBackground(True)
        tenant_name_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
        tenant_name_container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.14);
                border: 1px solid rgba(255, 255, 255, 0.45);
                border-radius: 6px;
            }
        """)
        tenant_name_layout = QHBoxLayout(tenant_name_container)
        tenant_name_layout.setContentsMargins(12, 6, 12, 6)
        tenant_name_layout.setSpacing(8)
        tenant_name_title = BodyLabel("Tenant Name:")
        tenant_name_title.setStyleSheet("color:#FFFFFF; font-weight:bold; background:transparent; border:none;")
        tenant_name_layout.addWidget(tenant_name_title)
        self.tenant_name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tenant_name_label.setStyleSheet("color:#FFFFFF; font-weight:bold; background:transparent; border:none; font-size:14px;")
        tenant_name_layout.addWidget(self.tenant_name_label)
        tenant_name_layout.addStretch()
        info_vbox.addWidget(tenant_name_container)
        
        # Room Number with frosted container (horizontal layout) - Blue/Cyan
        room_number_container = QWidget()
        room_number_container.setAttribute(Qt.WA_StyledBackground, True)
        room_number_container.setAutoFillBackground(True)
        room_number_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
        room_number_container.setStyleSheet("""
            QWidget {
                background-color: rgba(79, 195, 247, 0.14);
                border: 1px solid rgba(79, 195, 247, 0.45);
                border-radius: 6px;
            }
        """)
        room_number_layout = QHBoxLayout(room_number_container)
        room_number_layout.setContentsMargins(12, 6, 12, 6)
        room_number_layout.setSpacing(8)
        room_number_title = BodyLabel("Room Number:")
        room_number_title.setStyleSheet("color:#4FC3F7; font-weight:bold; background:transparent; border:none;")
        room_number_layout.addWidget(room_number_title)
        self.room_number_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.room_number_label.setStyleSheet("color:#4FC3F7; font-weight:bold; background:transparent; border:none; font-size:14px;")
        room_number_layout.addWidget(self.room_number_label)
        room_number_layout.addStretch()
        info_vbox.addWidget(room_number_container)
        
        # Advanced Paid with frosted container (horizontal layout) - Green
        advanced_paid_container = QWidget()
        advanced_paid_container.setAttribute(Qt.WA_StyledBackground, True)
        advanced_paid_container.setAutoFillBackground(True)
        advanced_paid_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
        advanced_paid_container.setStyleSheet("""
            QWidget {
                background-color: rgba(129, 199, 132, 0.14);
                border: 1px solid rgba(129, 199, 132, 0.45);
                border-radius: 6px;
            }
        """)
        advanced_paid_layout = QHBoxLayout(advanced_paid_container)
        advanced_paid_layout.setContentsMargins(12, 6, 12, 6)
        advanced_paid_layout.setSpacing(8)
        advanced_paid_title = BodyLabel("Advanced Paid:")
        advanced_paid_title.setStyleSheet("color:#81C784; font-weight:bold; background:transparent; border:none;")
        advanced_paid_layout.addWidget(advanced_paid_title)
        self.advanced_paid_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.advanced_paid_label.setStyleSheet("color:#81C784; font-weight:bold; background:transparent; border:none; font-size:14px;")
        advanced_paid_layout.addWidget(self.advanced_paid_label)
        advanced_paid_layout.addStretch()
        info_vbox.addWidget(advanced_paid_container)
        
        # Created At with frosted container (horizontal layout) - Orange
        created_at_container = QWidget()
        created_at_container.setAttribute(Qt.WA_StyledBackground, True)
        created_at_container.setAutoFillBackground(True)
        created_at_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
        created_at_container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 183, 77, 0.14);
                border: 1px solid rgba(255, 183, 77, 0.45);
                border-radius: 6px;
            }
        """)
        created_at_layout = QHBoxLayout(created_at_container)
        created_at_layout.setContentsMargins(12, 6, 12, 6)
        created_at_layout.setSpacing(8)
        created_at_title = BodyLabel("Created At:")
        created_at_title.setStyleSheet("color:#FFB74D; font-weight:bold; background:transparent; border:none;")
        created_at_layout.addWidget(created_at_title)
        self.created_at_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.created_at_label.setStyleSheet("color:#FFB74D; font-weight:bold; background:transparent; border:none; font-size:14px;")
        created_at_layout.addWidget(self.created_at_label)
        created_at_layout.addStretch()
        info_vbox.addWidget(created_at_container)
        
        # Updated At with frosted container (horizontal layout) - Pink/Rose
        updated_at_container = QWidget()
        updated_at_container.setAttribute(Qt.WA_StyledBackground, True)
        updated_at_container.setAutoFillBackground(True)
        updated_at_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
        updated_at_container.setStyleSheet("""
            QWidget {
                background-color: rgba(236, 64, 122, 0.14);
                border: 1px solid rgba(236, 64, 122, 0.45);
                border-radius: 6px;
            }
        """)
        updated_at_layout = QHBoxLayout(updated_at_container)
        updated_at_layout.setContentsMargins(12, 6, 12, 6)
        updated_at_layout.setSpacing(8)
        updated_at_title = BodyLabel("Updated At:")
        updated_at_title.setStyleSheet("color:#EC407A; font-weight:bold; background:transparent; border:none;")
        updated_at_layout.addWidget(updated_at_title)
        self.updated_at_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.updated_at_label.setStyleSheet("color:#EC407A; font-weight:bold; background:transparent; border:none; font-size:14px;")
        updated_at_layout.addWidget(self.updated_at_label)
        updated_at_layout.addStretch()
        info_vbox.addWidget(updated_at_container)
        
        sections_layout.addWidget(info_section)
        
        # RIGHT: Document Preview section (70%)
        doc_section = StaticCardWidget()
        doc_layout = QVBoxLayout(doc_section)
        
        # Section header
        doc_header = TitleLabel("Document Preview")
        doc_header.setAlignment(Qt.AlignCenter)
        doc_header.setStyleSheet("""
            color: #6C5CE7;
            font-weight: bold;
            font-size: 20px;
            padding-bottom: 2px;
        """)
        doc_layout.addWidget(doc_header)
        
        # Purple divider
        doc_divider = QFrame()
        doc_divider.setFrameShape(QFrame.HLine)
        doc_divider.setStyleSheet("background-color: #6C5CE7; min-height: 2px; max-height: 2px;")
        doc_layout.addWidget(doc_divider)
        doc_layout.addSpacing(3)
        
        # Scroll area for documents
        doc_scroll = AutoScrollArea()
        doc_scroll.setWidgetResizable(True)
        doc_widget = QWidget()
        doc_grid = QGridLayout(doc_widget)
        doc_grid.setContentsMargins(10, 10, 10, 10)
        doc_grid.setSpacing(10)
        doc_scroll.setWidget(doc_widget)
        doc_layout.addWidget(doc_scroll)
        
        # 2x2 image preview grid with minimum sizes
        self.photo_preview_label = ResponsiveImagePreviewGrid()
        self.photo_preview_label.setMinimumSize(200, 250)
        doc_grid.addWidget(self.photo_preview_label, 0, 0)
        
        self.nid_front_preview_label = ResponsiveImagePreviewGrid()
        self.nid_front_preview_label.setMinimumSize(200, 250)
        doc_grid.addWidget(self.nid_front_preview_label, 0, 1)
        
        self.nid_back_preview_label = ResponsiveImagePreviewGrid()
        self.nid_back_preview_label.setMinimumSize(200, 250)
        doc_grid.addWidget(self.nid_back_preview_label, 1, 0)
        
        self.police_form_preview_label = ResponsiveImagePreviewGrid()
        self.police_form_preview_label.setMinimumSize(200, 250)
        doc_grid.addWidget(self.police_form_preview_label, 1, 1)
        
        # Set column stretch to make images expand
        doc_grid.setColumnStretch(0, 1)
        doc_grid.setColumnStretch(1, 1)
        doc_grid.setRowStretch(0, 1)
        doc_grid.setRowStretch(1, 1)
        
        sections_layout.addWidget(doc_section)
        layout.addLayout(sections_layout)
    


    
    def _create_pdf_section(self, layout):
        """Create Generated PDF section."""
        pdf_section = StaticCardWidget()
        pdf_layout = QVBoxLayout(pdf_section)
        
        # Section header
        pdf_header = TitleLabel("Generated PDF")
        pdf_header.setAlignment(Qt.AlignCenter)
        pdf_header.setStyleSheet("""
            color: #6C5CE7;
            font-weight: bold;
            font-size: 20px;
            padding-bottom: 2px;
        """)
        pdf_layout.addWidget(pdf_header)
        
        # Purple divider
        pdf_divider = QFrame()
        pdf_divider.setFrameShape(QFrame.HLine)
        pdf_divider.setStyleSheet("background-color: #6C5CE7; min-height: 2px; max-height: 2px;")
        pdf_layout.addWidget(pdf_divider)
        pdf_layout.addSpacing(3)
        
        # Container for PDF status/button
        pdf_content_layout = QHBoxLayout()
        pdf_content_layout.setContentsMargins(10, 10, 10, 10)
        
        # PDF status label (shown when no PDF)
        self.pdf_status_label = QLabel("No PDF generated yet.")
        self.pdf_status_label.setStyleSheet("color: #ffffff; font-size: 13px;")
        pdf_content_layout.addWidget(self.pdf_status_label)
        
        # PDF button (hidden initially, shown when PDF is generated)
        self.pdf_open_button = PrimaryPushButton("Open PDF")
        self.pdf_open_button.setIcon(FluentIcon.DOCUMENT.icon(color=QColor(255, 255, 255)))
        self.pdf_open_button.setIconSize(QSize(20, 20))
        self.pdf_open_button.setFixedHeight(36)
        self.pdf_open_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px 8px 40px;
            }
            PrimaryPushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            PrimaryPushButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
        """)
        self.pdf_open_button.hide()  # Hidden initially
        self.pdf_open_button.clicked.connect(self._open_pdf)
        pdf_content_layout.addWidget(self.pdf_open_button)
        
        pdf_content_layout.addStretch()
        pdf_layout.addLayout(pdf_content_layout)
        
        # Store PDF path
        self._pdf_path = None
        
        layout.addWidget(pdf_section)

    
    def _create_action_buttons(self, layout):
        """Create action buttons with proper colors."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Save PDF button (Blue)
        self.dialog_save_pdf_btn = PrimaryPushButton("Save PDF")
        self.dialog_save_pdf_btn.setIcon(FluentIcon.DOCUMENT.icon(color=QColor(255, 255, 255)))
        self.dialog_save_pdf_btn.setIconSize(QSize(20, 20))
        self.dialog_save_pdf_btn.setFixedHeight(36)
        self.dialog_save_pdf_btn.clicked.connect(self.generate_pdf_from_dialog)
        self.dialog_save_pdf_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px 8px 40px;
            }
            PrimaryPushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            PrimaryPushButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
        """)
        button_layout.addWidget(self.dialog_save_pdf_btn)
        
        # Edit button (Green)
        self.dialog_edit_btn = PrimaryPushButton("Edit")
        self.dialog_edit_btn.setIcon(FluentIcon.EDIT.icon(color=QColor(255, 255, 255)))
        self.dialog_edit_btn.setIconSize(QSize(20, 20))
        self.dialog_edit_btn.setFixedHeight(36)
        self.dialog_edit_btn.clicked.connect(self.edit_record)
        self.dialog_edit_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #2e7d32;
                border: 1px solid #2e7d32;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px 8px 40px;
            }
            PrimaryPushButton:hover {
                background-color: #43a047;
                border-color: #43a047;
            }
            PrimaryPushButton:pressed {
                background-color: #1b5e20;
                border-color: #1b5e20;
            }
        """)
        button_layout.addWidget(self.dialog_edit_btn)
        
        # Archive/Unarchive button (Gray)
        self.dialog_archive_btn = PrimaryPushButton("Archive")
        self.dialog_archive_btn.setIcon(FluentIcon.FOLDER.icon(color=QColor(255, 255, 255)))
        self.dialog_archive_btn.setIconSize(QSize(20, 20))
        self.dialog_archive_btn.setFixedHeight(36)
        self.dialog_archive_btn.clicked.connect(self.toggle_archive_status)
        self.dialog_archive_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #757575;
                border: 1px solid #757575;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px 8px 40px;
            }
            PrimaryPushButton:hover {
                background-color: #9e9e9e;
                border-color: #9e9e9e;
            }
            PrimaryPushButton:pressed {
                background-color: #616161;
                border-color: #616161;
            }
        """)
        button_layout.addWidget(self.dialog_archive_btn)
        
        # Delete button (Red)
        self.dialog_delete_btn = PrimaryPushButton("Delete")
        self.dialog_delete_btn.setIcon(FluentIcon.DELETE.icon(color=QColor(255, 255, 255)))
        self.dialog_delete_btn.setIconSize(QSize(20, 20))
        self.dialog_delete_btn.setFixedHeight(36)
        self.dialog_delete_btn.clicked.connect(self.delete_record)
        self.dialog_delete_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #c62828;
                border: 1px solid #c62828;
                border-radius: 6px;
                font-weight: bold;
                padding: 8px 16px 8px 40px;
            }
            PrimaryPushButton:hover {
                background-color: #d84315;
                border-color: #d84315;
            }
            PrimaryPushButton:pressed {
                background-color: #b71c1c;
                border-color: #b71c1c;
            }
        """)
        button_layout.addWidget(self.dialog_delete_btn)
        
        layout.addLayout(button_layout)

    
    def display_record_details(self):
        """Display record information and load images."""
        # Display text information
        self.tenant_name_label.setText(self.record_data.tenant_name or "N/A")
        self.room_number_label.setText(self.record_data.room_number or "N/A")
        
        # Format advanced paid
        raw_adv = self.record_data.advanced_paid
        try:
            adv_val = float(raw_adv) if raw_adv is not None else None
        except (TypeError, ValueError):
            adv_val = None
        self.advanced_paid_label.setText(f"{adv_val:.2f} TK" if adv_val is not None else "N/A")
        
        self.created_at_label.setText(self.record_data.created_at or "N/A")
        self.updated_at_label.setText(self.record_data.updated_at or "N/A")
        
        # Adjust archive button
        if self.is_archived_record:
            self.dialog_archive_btn.setText("Unarchive")
            self.dialog_edit_btn.hide()
        else:
            self.dialog_archive_btn.setText("Archive")
            self.dialog_edit_btn.show()
        
        # Load images
        self._load_images()
    
    def _load_images(self):
        """
        Load document preview images with optimized parallel loading.
        
        This method now uses parallel image fetching for network URLs,
        which is 3-4x faster than sequential loading.
        """
        image_labels = {
            "photo": self.photo_preview_label,
            "nid_front": self.nid_front_preview_label,
            "nid_back": self.nid_back_preview_label,
            "police_form": self.police_form_preview_label
        }
        
        image_paths = {}
        if self.current_source == "Local DB":
            image_paths = {
                "photo": self.record_data.photo_path,
                "nid_front": self.record_data.nid_front_path,
                "nid_back": self.record_data.nid_back_path,
                "police_form": self.record_data.police_form_path
            }
        else:
            image_paths = {
                "photo": self.record_data.photo_url,
                "nid_front": self.record_data.nid_front_url,
                "nid_back": self.record_data.nid_back_url,
                "police_form": self.record_data.police_form_url
            }
        
        # Separate network URLs from local paths
        network_urls = {}
        local_paths = {}
        
        for img_type, path in image_paths.items():
            placeholder_text = f"No {img_type.replace('_', ' ').title()}"
            label = image_labels[img_type]
            
            if path and path != "No file selected":
                if isinstance(path, str) and path.startswith("http"):
                    network_urls[img_type] = (path, label, placeholder_text)
                elif os.path.exists(path):
                    local_paths[img_type] = (path, label, placeholder_text)
                else:
                    label._show_placeholder(placeholder_text)
            else:
                label._show_placeholder(placeholder_text)
        
        # Load local images immediately (fast)
        for img_type, (path, label, placeholder_text) in local_paths.items():
            try:
                label.setImagePath(path, placeholder_text)
            except Exception:
                label._show_placeholder(placeholder_text)
        
        # Load network images in parallel (optimized!)
        if network_urls:
            self._load_network_images_parallel(network_urls)

    
    def _load_network_images_parallel(self, network_urls):
        """
        Load multiple network images in parallel for maximum performance.
        
        This is the key optimization: instead of loading images one at a time
        (sequential), we load them all at once (parallel), which is 3-4x faster.
        
        Example:
            Sequential (old): 4 images × 2s each = 8s total
            Parallel (new):   4 images × 2s = 2s total (4x faster!)
        
        Args:
            network_urls: Dict mapping img_type to (url, label, placeholder_text)
        """
        import logging
        
        # Show simple loading placeholders (no spinners for dialog view)
        for img_type, (url, label, placeholder_text) in network_urls.items():
            self._current_image_urls[img_type] = url
            try:
                label._show_placeholder(f"Loading...")
            except Exception:
                label.setText(f"Loading...")
        
        # Collect URLs to fetch
        urls_to_fetch = []
        url_to_type = {}
        
        for img_type, (url, label, placeholder_text) in network_urls.items():
            # Check cache first
            cached = self._image_cache.get(url)
            if cached:
                label.setImageData(cached, placeholder_text)
                logging.info(f"✓ Using cached image for {img_type}")
            else:
                urls_to_fetch.append(url)
                url_to_type[url] = (img_type, label, placeholder_text)
        
        # If all images were cached, we're done!
        if not urls_to_fetch:
            logging.info("✓ All images loaded from cache (instant!)")
            return
        
        # Start parallel fetch worker with thumbnail mode for display
        logging.info(f"⚡ Starting parallel fetch of {len(urls_to_fetch)} thumbnails...")
        
        worker = FetchMultipleImagesWorker(urls_to_fetch, for_display=True, parent=self)
        
        def on_images_fetched(results):
            """Handle fetched images"""
            for url, data in results.items():
                if url in url_to_type:
                    img_type, label, placeholder_text = url_to_type[url]
                    
                    # Verify this is still the current URL for this image type
                    if self._current_image_urls.get(img_type) != url:
                        continue
                    
                    if data:
                        # Cache the image
                        if len(self._image_cache) > 64:
                            self._image_cache.pop(next(iter(self._image_cache)))
                        self._image_cache[url] = data
                        
                        # Display the image (thumbnail)
                        label.setImageData(data, placeholder_text)
                        logging.info(f"✓ Loaded {img_type} thumbnail")
                    else:
                        label._show_placeholder(placeholder_text)
                        logging.warning(f"✗ Failed to load {img_type}")
        
        def on_error(error_msg):
            """Handle fetch errors"""
            logging.error(f"✗ Parallel image fetch error: {error_msg}")
            # Show placeholders for failed images
            for url, (img_type, label, placeholder_text) in url_to_type.items():
                if self._current_image_urls.get(img_type) == url:
                    label._show_placeholder(placeholder_text)
        
        worker.images_fetched.connect(on_images_fetched)
        worker.error_occurred.connect(on_error)
        
        # Store worker reference to prevent garbage collection
        self._parallel_fetch_worker = worker
        worker.start()
    
    def _load_network_image(self, url, img_type, label, placeholder_text):
        """
        Load image from network URL (DEPRECATED - kept for backward compatibility).
        
        This method is now deprecated in favor of _load_network_images_parallel
        which loads multiple images concurrently for better performance.
        """
        self._current_image_urls[img_type] = url
        
        # Check cache
        cached = self._image_cache.get(url)
        if cached:
            label.setImageData(cached, placeholder_text)
            return
        
        try:
            label._show_placeholder(f"Loading {img_type.replace('_', ' ').title()}...")
        except Exception:
            label.setText(f"Loading {img_type.replace('_', ' ').title()}...")
        
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.CacheLoadControlAttribute, QNetworkRequest.PreferCache)
        reply = self._qnam.get(req)
        
        def handle_finished(rep=reply, it=img_type, u=url, lbl=label):
            try:
                if self._current_image_urls.get(it) != u:
                    rep.deleteLater()
                    return
                if rep.error() == QNetworkReply.NoError:
                    data = bytes(rep.readAll())
                    if data:
                        if len(self._image_cache) > 64:
                            self._image_cache.pop(next(iter(self._image_cache)))
                        self._image_cache[u] = data
                        lbl.setImageData(data, placeholder_text)
                    else:
                        lbl._show_placeholder(placeholder_text)
                else:
                    self._start_worker_image_fetch(u, it, lbl, placeholder_text)
            finally:
                rep.deleteLater()
        
        reply.finished.connect(handle_finished)
    
    def _start_worker_image_fetch(self, url, img_type, label, placeholder_text):
        """Fallback image fetch using worker thread."""
        try:
            if img_type in self._image_workers:
                self._image_workers.pop(img_type, None)
            worker = FetchImageWorker(url, timeout=8, verify_tls=False, parent=self)
            
            def on_downloaded(data, it=img_type, u=url, lbl=label):
                if self._current_image_urls.get(it) == u and data:
                    if len(self._image_cache) > 64:
                        self._image_cache.pop(next(iter(self._image_cache)))
                    self._image_cache[u] = data
                    lbl.setImageData(data, placeholder_text)
            
            def on_error(err, it=img_type, u=url, lbl=label):
                if self._current_image_urls.get(it) == u:
                    lbl._show_placeholder(placeholder_text)
            
            worker.image_downloaded.connect(on_downloaded)
            worker.error_occurred.connect(on_error)
            self._image_workers[img_type] = worker
            worker.start()
        except Exception:
            pass

    
    def generate_pdf_from_dialog(self):
        """Generate PDF for this rental record."""
        if self.main_window and hasattr(self.main_window, 'rental_info_tab_instance'):
            if hasattr(self.main_window.rental_info_tab_instance, 'generate_rental_pdf_from_data'):
                pdf_path = self.main_window.rental_info_tab_instance.generate_rental_pdf_from_data(self.record_data)
                if isinstance(pdf_path, str) and pdf_path:
                    # Store PDF path and show button
                    self._pdf_path = pdf_path
                    self.pdf_status_label.setText(f"PDF: {os.path.basename(pdf_path)}")
                    self.pdf_open_button.show()
                else:
                    self.pdf_status_label.setText("PDF generation cancelled or failed.")
                    self.pdf_open_button.hide()
            else:
                QMessageBox.critical(self, "Error", "PDF generation function not accessible.")
        else:
            QMessageBox.critical(self, "Error", "PDF generation function not accessible.")
    
    def _open_pdf(self):
        """Open the generated PDF file."""
        if self._pdf_path and os.path.exists(self._pdf_path):
            try:
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(self._pdf_path)
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', self._pdf_path])
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not open PDF: {e}")
    
    def edit_record(self):
        """Load record into rental tab for editing."""
        try:
            if self.main_window and hasattr(self.main_window, 'rental_info_tab_instance'):
                rental_tab = self.main_window.rental_info_tab_instance
                if hasattr(rental_tab, 'load_record_into_form_for_edit'):
                    record_dict = self.record_data._asdict()
                    rental_tab.load_record_into_form_for_edit(record_dict)
                    self.accept()
                    return
            
            if self.main_window and hasattr(self.main_window, 'rental_info_tab'):
                rental_tab = self.main_window.rental_info_tab
                if hasattr(rental_tab, 'load_record_into_form_for_edit'):
                    record_dict = self.record_data._asdict()
                    rental_tab.load_record_into_form_for_edit(record_dict)
                    self.accept()
                    return
            
            QMessageBox.critical(self, "Error", "Edit function not accessible.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit record: {e}")

    
    def toggle_archive_status(self):
        """Toggle archive status of the record."""
        try:
            new_archive_status = not self.is_archived_record
            action_text = "archived" if new_archive_status else "unarchived"
            
            if self.current_source == "Local DB":
                update_query = "UPDATE rentals SET is_archived = ? WHERE id = ?"
                self.db_manager.execute_query(update_query, (1 if new_archive_status else 0, self.record_data.id))
                QMessageBox.information(self, "Success", f"Record has been {action_text} in local database.")
            elif self.current_source == "Cloud (Supabase)":
                if self.supabase_manager and self.supabase_manager.is_client_initialized():
                    success = self.supabase_manager.update_rental_record_archive_status(
                        self.supabase_id or self.record_data.supabase_id,
                        new_archive_status
                    )
                    if success:
                        QMessageBox.information(self, "Success", f"Record has been {action_text} in the cloud.")
                    else:
                        QMessageBox.critical(self, "Supabase Error", "Failed to update record in Supabase.")
                        return
                else:
                    QMessageBox.warning(self, "Supabase Error", "Supabase client not configured.")
                    return
            
            self.is_archived_record = new_archive_status
            
            # Refresh the tabs to show updated records
            if self.main_window and hasattr(self.main_window, 'refresh_all_rental_tabs'):
                try:
                    self.main_window.refresh_all_rental_tabs()
                except Exception as e:
                    print(f"Warning: Failed to refresh tabs: {e}")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle archive status: {e}")

    
    def delete_record(self):
        """Delete the rental record."""
        # Use custom confirmation dialog
        confirmed = ConfirmDialog.ask(
            self, 
            "Confirm Delete",
            f"Are you sure you want to delete the record for '{self.record_data.tenant_name}' (Room: {self.record_data.room_number}) from {self.current_source}?",
            "warning"
        )
        if confirmed:
            try:
                if self.current_source == "Local DB":
                    photo_path = self.record_data.photo_path
                    nid_front_path = self.record_data.nid_front_path
                    nid_back_path = self.record_data.nid_back_path
                    police_form_path = self.record_data.police_form_path
                    
                    self.db_manager.execute_query("DELETE FROM rentals WHERE id = ?", (self.record_data.id,))
                    QMessageBox.information(self, "Success", "Record deleted from local database.")
                    
                    files_to_delete = [photo_path, nid_front_path, nid_back_path, police_form_path]
                    for f_path in files_to_delete:
                        if f_path and os.path.exists(f_path) and self._is_safe_path(f_path):
                            try:
                                os.remove(f_path)
                            except Exception:
                                pass
                
                elif self.current_source == "Cloud (Supabase)":
                    if self.supabase_manager and self.record_data.supabase_id:
                        success = self.supabase_manager.delete_rental_record(self.record_data.supabase_id)
                        if success:
                            QMessageBox.information(self, "Success", "Record deleted from Supabase.")
                            if self.record_data.id:
                                self.db_manager.execute_query("DELETE FROM rentals WHERE id = ?", (self.record_data.id,))
                        else:
                            QMessageBox.critical(self, "Cloud Error", "Failed to delete record from Supabase.")
                            return
                    else:
                        QMessageBox.warning(self, "Supabase Error", "Supabase manager not available.")
                        return
                
                # Refresh the tabs to show updated records
                if self.main_window and hasattr(self.main_window, 'refresh_all_rental_tabs'):
                    try:
                        self.main_window.refresh_all_rental_tabs()
                    except Exception as e:
                        print(f"Warning: Failed to refresh tabs: {e}")
                
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete record: {e}")
                traceback.print_exc()
    
    def _is_safe_path(self, file_path):
        """Validate that the file path is safe to access."""
        if not file_path:
            return False
        try:
            from src.core.utils import get_user_data_dir
            abs_path = os.path.abspath(os.path.realpath(file_path))
            app_dir = os.path.abspath(os.getcwd())
            safe_dirs = [
                app_dir,
                str(get_user_data_dir()),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Desktop"),
                os.path.expanduser("~/Downloads")
            ]
            abs_path_lower = abs_path.lower() if os.name == 'nt' else abs_path
            safe_dirs_abs_lower = [os.path.abspath(d).lower() if os.name == 'nt' else os.path.abspath(d) for d in safe_dirs]
            is_in_safe_dir = any(
                os.path.commonpath([abs_path_lower, safe_dir]) == safe_dir
                for safe_dir in safe_dirs_abs_lower
            )
            has_traversal = ".." in abs_path
            forbidden_dirs = ["/etc", "/sys", "/proc", "c:\\windows", "c:\\system32"]
            in_forbidden = any(abs_path_lower.startswith(f.lower()) for f in forbidden_dirs)
            return is_in_safe_dir and not in_forbidden and not has_traversal
        except (OSError, ValueError):
            return False
    
    def closeEvent(self, event):
        """Clean up resources when dialog closes."""
        try:
            try:
                self._qnam.setParent(None)
                self._qnam.deleteLater()
            except Exception:
                pass
            
            # Clean up parallel fetch worker
            if self._parallel_fetch_worker:
                try:
                    self._parallel_fetch_worker.requestInterruption()
                    self._parallel_fetch_worker.quit()
                    self._parallel_fetch_worker.wait(100)
                except Exception:
                    pass
                self._parallel_fetch_worker = None
            
            # Clean up individual workers
            for worker in list(self._image_workers.values()):
                try:
                    worker.requestInterruption()
                    worker.quit()
                    worker.wait(100)
                except Exception:
                    pass
            self._image_workers.clear()
            self._current_image_urls.clear()
        except Exception:
            pass
        super().closeEvent(event)
