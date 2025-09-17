import sys
import traceback
import os
import io # Import the io module for in-memory binary streams
import time
import hashlib
from datetime import datetime
from pathlib import Path # Import Path from pathlib
from typing import List, Dict, Any
import shutil # Import shutil for file operations
import uuid # Import uuid for generating unique filenames
import urllib.parse
import re
import requests  # Used for downloading remote images

# Suppress SSL certificate warnings when verify=False is used in requests
try:
    import urllib3
except ModuleNotFoundError:
    import requests.packages.urllib3 as urllib3  # type: ignore

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from PyQt5.QtCore import Qt, QRegExp, QEvent, QTimer
from PyQt5.QtGui import QIcon, QRegExpValidator, QPixmap, QPainter, QColor, QFont, QFontMetrics # Keep QPixmap for _validate_image_file
from reportlab.lib.utils import ImageReader # Added ImageReader
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QAbstractItemView, QSizePolicy, QLineEdit
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer, Image, PageBreak, NextPageTemplate, BaseDocTemplate, PageTemplate, Frame, FrameBreak # Re-import FrameBreak
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from qfluentwidgets import (
    CardWidget, ComboBox, CheckBox, PrimaryPushButton, PushButton,
    LineEdit, TableWidget, FluentIcon, TitleLabel, GroupHeaderCardWidget,
    HeaderCardWidget, BodyLabel, CaptionLabel, SwitchButton, IndicatorPosition,
    SearchLineEdit, ToolButton, TransparentToolButton, Action, RoundMenu,
    HyperlinkButton, IconWidget, InfoBarIcon, setCustomStyleSheet
)

from src.core.utils import resource_path, _clear_layout
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, FluentProgressDialog, SmoothTableWidget
from src.ui.dialogs import RentalRecordDialog
from src.ui.background_workers import FetchSupabaseRentalRecordsWorker
from src.ui.components import EnhancedTableMixin
from src.ui.components.table_optimization import (
    DebounceResizeManager,
    TableCacheManager,
    BatchUpdateManager,
    ResizeDebugManager
)

# >>> ADD
# Fluent-widgets progress bar
try:
    from qfluentwidgets import IndeterminateProgressBar  # type: ignore
except ImportError:
    IndeterminateProgressBar = None  # type: ignore
# <<< ADD


class NumericTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other):
        # Prefer comparing numeric sort keys stored in UserRole
        try:
            a = self.data(Qt.UserRole)
            b = other.data(Qt.UserRole)
            if a is not None and b is not None:
                return float(a) < float(b)
        except Exception:
            pass
        # Fallback: try parsing text
        try:
            return float(self.text()) < float(other.text())
        except Exception:
            return super().__lt__(other)


class RentalInfoTab(QWidget, EnhancedTableMixin):
    # Define priority columns for rental table
    PRIORITY_COLUMNS = {
        'rental_table': ['TENANT NAME', 'ROOM NUMBER', 'ADVANCED PAID']
    }
    
    # Define specific column icons for rental table
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
    
    # Define safe and forbidden directories at the class level
    SAFE_DIRS = [Path.cwd()] + [Path.home() / d for d in ("Documents", "Desktop", "Downloads")]
    FORBIDDEN = [
        Path(p) for p in (
            "/etc", "/sys", "/proc", "/bin", "/usr",
            "C:/Windows", "C:/Windows/System32"
        )
    ]
    # Define the directory where images will be stored within the application's data folder
    IMAGE_STORAGE_DIR = Path.cwd() / "data" / "images"

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = self.main_window.db_manager
        
        # Debug configuration flags for production control
        self._resize_debug_enabled = False  # Can be enabled via configuration
        
        # >>> ADD
        # Ensure the image storage directory exists right at start-up so that
        # subsequent save operations don't fail due to a missing folder.
        try:
            self.IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as dir_e:
            print(f"Warning: could not create image storage dir: {dir_e}")
        # Inline progress bar reference (for cloud fetch)
        self._inline_progress_bar = None
        # <<< ADD

        self.tenant_name_input = None
        self.room_number_input = None
        self.advanced_paid_input = None
        # Initialize legacy labels properly to avoid None errors
        self.photo_path_label = LineEdit()
        self.photo_path_label.setText("No file selected")
        self.nid_front_path_label = LineEdit()
        self.nid_front_path_label.setText("No file selected")
        self.nid_back_path_label = LineEdit()
        self.nid_back_path_label.setText("No file selected")
        self.police_form_path_label = LineEdit()
        self.police_form_path_label.setText("No file selected")
        self.rental_records_table = None

        self.current_rental_id = None  # Local DB primary key (if editing an existing record)
        self.current_supabase_id = None  # Supabase record UUID (if editing an existing record)
        self.current_is_archived = False  # Preserve archive status when editing

        # Cloud pagination state
        self._cloud_page_size = 25
        self._cloud_offset = 0
        self._cloud_has_more = True
        self._cloud_records_cache = []
        self._is_fetching = False
        self._cloud_append = False

        # Local cache to persist table data between source switches
        self._local_records_cache = None

        # Initialize optimization components
        self._setup_optimization_components()

        self.init_ui()
        self.load_rental_records() # Initial load will be from default source

    def init_ui(self):
        # Use a direct layout approach without scroll area for better theming
        # Set the main layout for the tab
        tab_layout = QVBoxLayout(self)
        tab_layout.setContentsMargins(12, 12, 12, 12)  # Reduced margins for more compact layout
        tab_layout.setSpacing(12)  # Reduced spacing from 20 to 12
        
        # Create the main horizontal layout directly on the tab
        main_horizontal_layout = QHBoxLayout()
        main_horizontal_layout.setSpacing(20)
        tab_layout.addLayout(main_horizontal_layout)

        # Left Column Layout (Input Form + Image Uploads + Save/Clear)
        left_column_layout = QVBoxLayout()
        left_column_layout.setSpacing(4)  # Aggressively reduced to give action buttons maximum space

        # Rental Details Card using HeaderCardWidget
        self.rental_details_card = HeaderCardWidget(self)
        self.rental_details_card.setTitle("Rental Details")
        self.rental_details_card.setBorderRadius(8)
        self.rental_details_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Remove maximum width for responsive behavior

        # Create simple vertical layout for input fields
        rental_details_layout = QVBoxLayout()
        rental_details_layout.setSpacing(4)  # Reduced to give action buttons more space
        rental_details_layout.setContentsMargins(0, 0, 0, 0)

        # Create input fields with modern styling and labels
        # Tenant Name field
        tenant_name_label = BodyLabel("Tenant Name")
        self.tenant_name_input = LineEdit()
        self.tenant_name_input.setClearButtonEnabled(True)
        
        # Room Number field
        room_number_label = BodyLabel("Room Number")
        self.room_number_input = LineEdit()
        self.room_number_input.setClearButtonEnabled(True)

        # Advanced Paid field
        advanced_paid_label = BodyLabel("Advanced Paid (TK)")
        self.advanced_paid_input = LineEdit()
        self.advanced_paid_input.setClearButtonEnabled(True)
        numeric_validator = QRegExpValidator(QRegExp(r'^\d*\.?\d*$'))
        self.advanced_paid_input.setValidator(numeric_validator)

        # Add labels and input fields to the layout
        rental_details_layout.addWidget(tenant_name_label)
        rental_details_layout.addWidget(self.tenant_name_input)
        rental_details_layout.addWidget(room_number_label)
        rental_details_layout.addWidget(self.room_number_input)
        rental_details_layout.addWidget(advanced_paid_label)
        rental_details_layout.addWidget(self.advanced_paid_input)

        # Add the layout to the card
        self.rental_details_card.viewLayout.addLayout(rental_details_layout)

        left_column_layout.addWidget(self.rental_details_card)

        # Store input fields for keyboard navigation
        self.input_fields = [
            self.tenant_name_input,
            self.room_number_input,
            self.advanced_paid_input
        ]

        # ─── Configure CustomLineEdit navigation (Enter / Up / Down) ───
        for idx, fld in enumerate(self.input_fields):
            next_fld = self.input_fields[(idx + 1) % len(self.input_fields)]
            prev_fld = self.input_fields[(idx - 1) % len(self.input_fields)]

            fld.next_widget_on_enter = next_fld   # Enter → next
            fld.down_widget = next_fld            # ↓ → next
            fld.up_widget = prev_fld              # ↑ → previous

        # Give initial focus to the first field when the tab opens
        self.tenant_name_input.setFocus()

        # Document Upload Card using HeaderCardWidget
        self.document_upload_card = HeaderCardWidget(self)
        self.document_upload_card.setTitle("Document Upload")
        self.document_upload_card.setBorderRadius(8)
        self.document_upload_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Remove maximum width for responsive behavior

        # Create modern file upload widgets with vertical layout (row by row)
        upload_layout = QVBoxLayout()
        upload_layout.setSpacing(4)  # Reduced spacing to give action buttons more room
        upload_layout.setContentsMargins(0, 0, 0, 0)

        # Photo Upload
        self.photo_widget = self._create_file_upload_widget(
            FluentIcon.CAMERA, "Photo", "Upload tenant photo", "photo"
        )
        self.photo_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        upload_layout.addWidget(self.photo_widget)

        # NID Front Upload
        self.nid_front_widget = self._create_file_upload_widget(
            FluentIcon.PEOPLE, "NID Front", "Upload front side of National ID", "nid_front"
        )
        self.nid_front_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        upload_layout.addWidget(self.nid_front_widget)

        # NID Back Upload
        self.nid_back_widget = self._create_file_upload_widget(
            FluentIcon.PEOPLE, "NID Back", "Upload back side of National ID", "nid_back"
        )
        self.nid_back_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        upload_layout.addWidget(self.nid_back_widget)

        # Police Form Upload
        self.police_form_widget = self._create_file_upload_widget(
            FluentIcon.DOCUMENT, "Police Form", "Upload police verification form", "police_form"
        )
        self.police_form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        upload_layout.addWidget(self.police_form_widget)

        self.document_upload_card.viewLayout.addLayout(upload_layout)
        left_column_layout.addWidget(self.document_upload_card)

        # Save Options Card using HeaderCardWidget
        self.save_options_card = HeaderCardWidget(self)
        self.save_options_card.setTitle("Save Options")
        self.save_options_card.setBorderRadius(8)
        self.save_options_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Remove maximum width for responsive behavior

        # Create save options layout with horizontal arrangement for compactness
        save_options_layout = QHBoxLayout()
        save_options_layout.setSpacing(12)  # Space between PC and Cloud options
        save_options_layout.setContentsMargins(4, 4, 4, 4)  # Reduced margins to give action buttons more space

        # Save to PC option - more compact
        pc_save_layout = QHBoxLayout()
        pc_save_layout.setSpacing(6)
        
        pc_icon = IconWidget(FluentIcon.SAVE)
        pc_icon.setFixedSize(16, 16)  # Smaller icon
        pc_label = CaptionLabel("PC")  # Shorter label
        self.save_to_pc_switch = SwitchButton("Off", indicatorPos=IndicatorPosition.RIGHT)
        self.save_to_pc_switch.setOnText("On")
        self.save_to_pc_switch.setChecked(True)
        
        pc_save_layout.addWidget(pc_icon)
        pc_save_layout.addWidget(pc_label)
        pc_save_layout.addWidget(self.save_to_pc_switch)
        
        # Save to Cloud option - more compact
        cloud_save_layout = QHBoxLayout()
        cloud_save_layout.setSpacing(6)
        
        cloud_icon = IconWidget(FluentIcon.CLOUD)
        cloud_icon.setFixedSize(16, 16)  # Smaller icon
        cloud_label = CaptionLabel("Cloud")  # Shorter label
        self.save_to_cloud_switch = SwitchButton("Off", indicatorPos=IndicatorPosition.RIGHT)
        self.save_to_cloud_switch.setOnText("On")
        self.save_to_cloud_switch.setChecked(True)
        
        cloud_save_layout.addWidget(cloud_icon)
        cloud_save_layout.addWidget(cloud_label)
        cloud_save_layout.addWidget(self.save_to_cloud_switch)

        save_options_layout.addLayout(pc_save_layout)
        save_options_layout.addStretch(1)  # Add stretch between options
        save_options_layout.addLayout(cloud_save_layout)

        self.save_options_card.viewLayout.addLayout(save_options_layout)
        left_column_layout.addWidget(self.save_options_card)

        # Action Buttons Layout
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.setSpacing(10)
        
        # Save Record Button
        self.save_record_btn = PrimaryPushButton(FluentIcon.SAVE, "Save Record")
        self.save_record_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.save_record_btn.setMinimumWidth(120)  # Removed for responsiveness
        self.save_record_btn.clicked.connect(self.save_rental_record)
        # Set button text color to white with proper icon positioning and white icon color
        self.save_record_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 4px;
                font-weight: 600;
                padding: 8px 24px 8px 48px;
                text-align: center;
                qproperty-iconSize: 16px 16px;
            }
            PrimaryPushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            PrimaryPushButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
            PrimaryPushButton::icon {
                color: white;
            }
        """)
        # Create a white version of the save icon
        original_icon = FluentIcon.SAVE.icon()
        white_pixmap = original_icon.pixmap(16, 16)
        # Create a white version by applying a color overlay
        white_icon_pixmap = QPixmap(16, 16)
        white_icon_pixmap.fill(QColor(255, 255, 255, 0))  # Transparent background
        painter = QPainter(white_icon_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.drawPixmap(0, 0, white_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(white_icon_pixmap.rect(), QColor(255, 255, 255))  # White color
        painter.end()
        white_save_icon = QIcon(white_icon_pixmap)
        self.save_record_btn.setIcon(white_save_icon)
        action_buttons_layout.addWidget(self.save_record_btn)

        # Clear Form Button
        self.clear_form_btn = PushButton(FluentIcon.CANCEL, "Clear Form")
        self.clear_form_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # self.clear_form_btn.setMinimumWidth(120)  # Removed for responsiveness
        self.clear_form_btn.clicked.connect(self.clear_form)
        # Set button text color to white with proper icon positioning and white icon color
        self.clear_form_btn.setStyleSheet("""
            PushButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 4px;
                font-weight: 600;
                padding: 8px 24px 8px 48px;
                text-align: center;
                qproperty-iconSize: 16px 16px;
            }
            PushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            PushButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
        """)
        action_buttons_layout.addWidget(self.clear_form_btn)
        
        left_column_layout.addLayout(action_buttons_layout)
        
        # Add the left column layout directly to the main layout
        # Reduce stretch factor to give records section even more space
        main_horizontal_layout.addLayout(left_column_layout, 0)

        # Right Column Layout (Rental Records Table)
        right_column_layout = QVBoxLayout()
        right_column_layout.setSpacing(16)

        # Records Table Card using CardWidget to match History tab
        self.records_table_card = CardWidget()
        self.records_table_card.setBorderRadius(8)
        self.records_table_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        records_card_layout = QVBoxLayout(self.records_table_card)
        records_card_layout.setSpacing(8)
        records_card_layout.setContentsMargins(12, 12, 12, 12)
        
        # Create title with FluentIcon to match history tab styling
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setPixmap(FluentIcon.PEOPLE.icon().pixmap(20, 20))
        title_text = TitleLabel("Existing Rental Records")
        title_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_text.setWordWrap(True)
        title_text.setStyleSheet("font-weight: 600; font-size: 16px; color: #0969da; margin-bottom: 8px;")
        title_layout.addWidget(title_icon)
        title_layout.addWidget(title_text)
        title_layout.addStretch()
        records_card_layout.addLayout(title_layout)
        
        # Add subtle divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("QFrame { border: 1px solid #e1e4e8; margin: 8px 0; }")
        records_card_layout.addWidget(divider)

        # Create table controls layout
        table_controls_layout = QHBoxLayout()
        table_controls_layout.setSpacing(12)
        table_controls_layout.setContentsMargins(0, 0, 0, 8)

        # Load Source Combo with modern styling
        source_label = BodyLabel("Data Source:")
        self.load_source_combo = ComboBox()
        self.load_source_combo.addItems(["Local DB", "Cloud (Supabase)"])
        self.load_source_combo.currentIndexChanged.connect(self.load_rental_records)
        # self.load_source_combo.setFixedWidth(180) # Removed for responsiveness

        # Add refresh button
        self.refresh_button = ToolButton(FluentIcon.UPDATE)
        self.refresh_button.setToolTip("Refresh records")
        # Force refresh clears caches and reloads
        self.refresh_button.clicked.connect(lambda: self.load_rental_records(force_refresh=True))
        # Set button text color to white
        self.refresh_button.setStyleSheet("""
            ToolButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 4px;
                padding: 4px;
                qproperty-iconSize: 16px 16px;
            }
            ToolButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            ToolButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
        """)

        table_controls_layout.addWidget(source_label)
        table_controls_layout.addWidget(self.load_source_combo)
        table_controls_layout.addWidget(self.refresh_button)
        table_controls_layout.addStretch(1)

        # Create main table layout
        table_layout = QVBoxLayout()
        table_layout.setSpacing(8)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Expose the layout so we can insert/remove the progress bar later
        self.table_layout = table_layout
        
        table_layout.addLayout(table_controls_layout)

        # Create modern table with History tab styling and smooth scrolling
        self.rental_records_table = SmoothTableWidget()
        self.rental_records_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Use simple table header creation without icons
        rental_headers = ["Tenant Name", "Room Number", "Advanced Paid", "Created At", "Updated At"]
        self.rental_records_table.setColumnCount(len(rental_headers))
        self.rental_records_table.setHorizontalHeaderLabels(rental_headers)
        # self._set_table_headers_with_icons(self.rental_records_table, rental_headers, 'rental_table')  # Disabled - no icons
        
        # Apply History tab's exact table styling
        self._style_table(self.rental_records_table)
        
        # Configure table properties matching history tab strategy
        self.rental_records_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.rental_records_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.rental_records_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rental_records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rental_records_table.clicked.connect(self.show_record_details_dialog)

        # Infinite scroll: auto-load next page on near-bottom
        try:
            self.rental_records_table.verticalScrollBar().valueChanged.connect(self._on_table_scroll)
        except Exception:
            pass

        # Add table with stretch factor like history tab
        table_layout.addWidget(self.rental_records_table, 1)

        records_card_layout.addLayout(table_layout)
        right_column_layout.addWidget(self.records_table_card)
        
        # Add the right column layout directly to the main layout
        # Set a stretch factor of 2 to give it more space
        main_horizontal_layout.addLayout(right_column_layout, 2)


    def _create_file_upload_widget(self, icon, title, description, file_type):
        """Create a modern file upload widget with visual feedback"""
        widget = QWidget()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        widget.setMinimumHeight(50)  # Ensure minimum height for proper button display
        widget.setMaximumHeight(60)  # Reasonable maximum height

        # Main horizontal layout
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)  # Good margins for proper spacing
        layout.setSpacing(12)

        # Icon
        icon_widget = IconWidget(icon, widget)
        icon_widget.setFixedSize(20, 20)  # Slightly larger icon for better visibility
        layout.addWidget(icon_widget)

        # Title and description
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        title_label = BodyLabel(title)  # Use BodyLabel for better visibility
        description_label = CaptionLabel(description)
        description_label.setTextColor("#666666", "#9f9f9f")
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(description_label)
        layout.addLayout(text_layout)
        layout.setStretchFactor(text_layout, 1)  # Allow text to expand

        # Status and buttons section
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        
        # Status label
        status_label = CaptionLabel("No file selected")
        status_label.setTextColor("#999999", "#7f7f7f")
        right_layout.addWidget(status_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)
        
        # Upload button - make it more prominent
        upload_btn = PrimaryPushButton("Upload")  # Use PrimaryPushButton for better visibility
        upload_btn.setFixedSize(70, 28)  # Good size for visibility
        upload_btn.setToolTip(f"Upload {title}")
        upload_btn.clicked.connect(lambda: self._handle_file_upload(file_type, status_label))
        # Set button text color to white
        upload_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #0078D4;
                border: 1px solid #0078D4;
                border-radius: 4px;
                font-weight: 600;
                padding: 4px 8px;
                text-align: center;
            }
            PrimaryPushButton:hover {
                background-color: #106ebe;
                border-color: #106ebe;
            }
            PrimaryPushButton:pressed {
                background-color: #005a9e;
                border-color: #005a9e;
            }
            PrimaryPushButton::icon {
                color: white;
            }
        """)
        button_layout.addWidget(upload_btn)
        
        # Clear button
        clear_btn = TransparentToolButton(FluentIcon.DELETE)
        clear_btn.setFixedSize(28, 28)  # Proper size
        clear_btn.setToolTip("Remove file")
        clear_btn.clicked.connect(lambda: self._clear_file_upload(file_type, status_label))
        # Set button text color to white
        clear_btn.setStyleSheet("""
            TransparentToolButton {
                color: white;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
            }
            TransparentToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
            TransparentToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.3);
            }
            TransparentToolButton::icon {
                color: white;
            }
        """)
        button_layout.addWidget(clear_btn)
        
        right_layout.addLayout(button_layout)
        layout.addLayout(right_layout)

        # Store references for later access
        widget.status_label = status_label
        widget.file_type = file_type
        widget.file_path = None
        widget.upload_btn = upload_btn
        
        return widget

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
        
        # Apply intelligent column widths for responsiveness
        self._set_intelligent_column_widths(table)

    def _set_intelligent_column_widths(self, table: TableWidget):
        """Set responsive column widths based on content and window size with advanced caching optimization"""
        print(f"[RENTAL DEBUG] _set_intelligent_column_widths called for table with {table.columnCount()} columns")
        
        if table.columnCount() == 0:
            print(f"[RENTAL DEBUG] No columns, returning early")
            return
        
        # Check if table is properly initialized
        available_width = table.viewport().width()
        print(f"[RENTAL DEBUG] Available width: {available_width}px")
        
        if available_width <= 50:  # Minimum reasonable width
            print(f"[RENTAL DEBUG] Available width too small ({available_width}px), retrying...")
            # Table not ready yet, retry after a short delay
            QTimer.singleShot(100, lambda: self._set_intelligent_column_widths(table))
            return
        
        # Check if table has reasonable size (remove visibility check for headless testing)
        table_width = table.width()
        print(f"[RENTAL DEBUG] Table width: {table_width}px")
        
        if table_width <= 50:
            print(f"[RENTAL DEBUG] Table width too small ({table_width}px), retrying...")
            # Table not properly sized yet, retry after delay
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
                    self._log_resize_debug("Cache hit for content widths", {'cache_key': cache_key[:8]})
                    return
                
                if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                    self._debug_manager.log_cache_operation('content_width', 'get_cached_widths', False,
                                                          {'cache_key': cache_key[:8], 'reason': 'cache_miss'})
                self._log_resize_debug("Cache miss for content widths", {'cache_key': cache_key[:8]})
        
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
            
            # Set minimum widths based on column type (inspired by history tab)
            header_lower = header_text.lower()
            if any(keyword in header_lower for keyword in ["tenant", "name"]):
                # Tenant name column needs more space for full names (like month column in history)
                # Use a more generous minimum width to prevent truncation
                content_widths[col] = max(max_content_width, 200)
            elif any(keyword in header_lower for keyword in ["room", "number"]):
                # Room columns moderate space
                content_widths[col] = max(max_content_width, 100)
            elif any(keyword in header_lower for keyword in ["advanced", "paid", "total", "cost", "bill", "amount", "grand"]):
                # Financial columns need space for numbers
                content_widths[col] = max(max_content_width, 120)
            elif any(keyword in header_lower for keyword in ["created", "updated"]):
                # Date columns need space for timestamps
                content_widths[col] = max(max_content_width, 140)
            elif "id" in header_lower:
                # ID columns can be compact
                content_widths[col] = max(max_content_width, 80)
            else:
                # Default column width
                content_widths[col] = max(max_content_width, 100)
            
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
                self._cache_manager.update_table_content_hash('rental_table', table)
                
        except Exception as e:
            print(f"Failed to cache column widths: {e}")
        
        # HYBRID APPROACH: Stretch when content fits, scroll when it doesn't (like history tab)
        print(f"[RENTAL DEBUG] Available: {available_width}px")
        print(f"[RENTAL DEBUG] Content widths: {[content_widths[col] for col in range(column_count)]}")
        print(f"[RENTAL DEBUG] Total min width: {total_min_width}px")
        
        header = table.horizontalHeader()
        
        # Determine if content fits in available space
        content_fits = total_min_width <= (available_width - 30)  # 30px buffer for scrollbars
        print(f"[RENTAL DEBUG] Content fits: {content_fits} ({total_min_width} <= {available_width - 30})")
        
        if content_fits and available_width > 200:
            # Content fits - use STRETCH mode for equal distribution
            for col in range(column_count):
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            print(f"[RENTAL DEBUG] Applied STRETCH mode - content fits in {available_width}px")
        else:
            # Content doesn't fit - use FIXED mode with horizontal scrolling to prevent truncation
            for col in range(column_count):
                header.setSectionResizeMode(col, QHeaderView.Fixed)
                table.setColumnWidth(col, content_widths[col])
            
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            # Ensure horizontal scrollbar is visible when needed
            if hasattr(table, 'horizontalScrollBar') and table.horizontalScrollBar():
                table.horizontalScrollBar().setVisible(True)
            
            print(f"[RENTAL DEBUG] Applied FIXED mode with scrolling - total width {total_min_width}px")
        
        # Verify mode was applied
        for col in range(column_count):
            mode = header.sectionResizeMode(col)
            mode_name = {0: "Interactive", 1: "Fixed", 2: "Stretch", 3: "ResizeToContents"}.get(mode, f"Unknown({mode})")
            width = table.columnWidth(col) if mode == 1 else "auto"
            print(f"[RENTAL DEBUG] Column {col} ({table.horizontalHeaderItem(col).text() if table.horizontalHeaderItem(col) else 'N/A'}): {mode_name}, width: {width}")
        
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
        
        print(f"[RENTAL DEBUG] Table size policy and header configured")
        
        # Apply special styling to tenant name column
        self._apply_tenant_name_column_styling(table)
    
    def _ensure_stretch_mode(self, table):
        """Ensure all columns are in stretch mode - called with delay to override any conflicting settings"""
        try:
            header = table.horizontalHeader()
            if header and table.columnCount() > 0:
                print(f"[RENTAL DEBUG] Ensuring stretch mode for {table.columnCount()} columns")
                
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
                    print(f"[RENTAL DEBUG] Column {col} mode after force: {mode_name}")
                    
        except Exception as e:
            print(f"[RENTAL DEBUG] Failed to ensure stretch mode: {e}")
    
    def _force_proportional_distribution(self, table):
        """Force proportional column distribution - called after data is loaded"""
        try:
            header = table.horizontalHeader()
            if not header or table.columnCount() == 0:
                return
                
            available_width = table.viewport().width()
            if available_width <= 200:
                return
                
            print(f"[RENTAL DEBUG] Forcing proportional distribution with viewport width: {available_width}px")
            
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
            print(f"[RENTAL DEBUG] Applying proportional widths:")
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
                
                print(f"[RENTAL DEBUG]   {header_text}: {current_width}px -> {new_width}px (target: {min_width}px, weight: {weight:.2f})")
            
            # Re-enable stretch last section for edge alignment
            header.setStretchLastSection(True)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            print(f"[RENTAL DEBUG] Forced proportional distribution with weights: {column_weights}")
            
        except Exception as e:
            print(f"[RENTAL DEBUG] Failed to force proportional distribution: {e}")
        
        # Performance logging removed from this method since it doesn't have start_time
    
    def _apply_tenant_name_column_styling(self, table: TableWidget):
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

    def _on_table_resize(self, table: TableWidget):
        """Handle table resize events"""
        QTimer.singleShot(150, lambda: self._set_intelligent_column_widths(table))

    def resizeEvent(self, event):
        """Handle widget resize events - directly recalculate column widths"""
        super().resizeEvent(event)
        # Since table optimization is disabled, directly call our column width method
        if hasattr(self, 'rental_records_table') and self.rental_records_table:
            QTimer.singleShot(200, lambda: self._set_intelligent_column_widths(self.rental_records_table))
    
    def showEvent(self, event):
        """Handle tab becoming visible - directly recalculate column widths"""
        try:
            super().showEvent(event)
            
            # Since table optimization is disabled, directly call our column width method
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                QTimer.singleShot(100, lambda: self._set_intelligent_column_widths(self.rental_records_table))
        except Exception as e:
            print(f"Error in showEvent: {e}")

    def _recalculate_all_table_widths(self):
        """Recalculate column widths for all tables using batched updates and caching"""
        try:
            # Use batch update manager for flicker-free recalculation
            if hasattr(self, '_batch_manager') and self._batch_manager and hasattr(self, 'rental_records_table') and self.rental_records_table:
                try:
                    self._batch_manager.begin_batch_update()
                    self._set_intelligent_column_widths(self.rental_records_table)
                    return True
                except Exception as e:
                    print(f"Batched table width recalculation failed: {e}")
                    return False
                finally:
                    self._batch_manager.end_batch_update()
            else:
                # Fallback to direct method if batch manager not available
                if hasattr(self, 'rental_records_table') and self.rental_records_table:
                    self._set_intelligent_column_widths(self.rental_records_table)
                    return True
        except Exception as e:
            print(f"Could not recalculate table widths: {e}")
            return False

    # ===== OPTIMIZATION METHODS =====
    
    def _setup_optimization_components(self):
        """Initialize optimization components with comprehensive error handling and fallback mechanisms"""
        try:
            # Import the new optimization component manager
            from src.ui.components.table_optimization import OptimizationComponentManager
            
            # Initialize the comprehensive optimization manager
            self._optimization_manager = OptimizationComponentManager(self)
            
            # Setup table optimization for rental records table
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
            
            # Setup optimization for rental records table
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                self._optimization_manager.setup_table_optimization(
                    self.rental_records_table, 
                    'rental_table'
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
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                batch_managers = self._optimization_manager.batch_managers
                self._rental_batch_manager = batch_managers.get('rental_table')
            
        except Exception as e:
            print(f"Warning: Could not setup resize debouncing: {e}")
            # Try fallback resize handling
            self._setup_fallback_resize_handling()

    def _setup_fallback_resize_handling(self):
        """Setup basic resize handling when optimization components fail"""
        try:
            if hasattr(self, '_fallback_manager') and self._fallback_manager:
                # Setup basic table properties
                if hasattr(self, 'rental_records_table') and self.rental_records_table:
                    self._fallback_manager.perform_basic_table_setup(self.rental_records_table)
            
        except Exception as e:
            print(f"Warning: Fallback resize setup failed: {e}")

    def _setup_fallback_table_optimization(self):
        """Setup fallback table optimization when main optimization fails"""
        try:
            if hasattr(self, '_fallback_manager') and self._fallback_manager:
                if hasattr(self, 'rental_records_table') and self.rental_records_table:
                    self._fallback_manager.perform_basic_table_setup(self.rental_records_table)
                    
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
            if start_time:
                duration = (time.time() * 1000) - start_time
                self._log_resize_debug("debounced_resize", {}, duration)
                
        except Exception as e:
            print(f"Error during debounced resize: {e}")
            # Last resort fallback
            self._emergency_resize_fallback()

    def _perform_optimized_resize(self):
        """Perform optimized resize using the optimization manager"""
        try:
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                self._optimization_manager.safe_resize_table(
                    self.rental_records_table, 
                    'rental_table'
                )
            
        except Exception as e:
            # Let optimization manager handle the error
            if self._optimization_manager:
                should_retry = self._optimization_manager.error_handler.handle_error(
                    'perform_optimized_resize', e, {'table': 'rental_table'}
                )
                if not should_retry:
                    self._perform_fallback_resize()
            else:
                raise e

    def _perform_fallback_resize(self):
        """Perform fallback resize using basic mechanisms"""
        try:
            if hasattr(self, '_fallback_manager') and self._fallback_manager:
                if hasattr(self, 'rental_records_table') and self.rental_records_table:
                    self._fallback_manager.perform_basic_resize(self.rental_records_table)
            else:
                # Direct fallback to original method
                self._recalculate_all_table_widths()
                
        except Exception as e:
            print(f"Fallback resize failed: {e}")
            # Try emergency fallback
            self._emergency_resize_fallback()

    def _final_column_mode_override(self, table):
        """Final aggressive override of column modes - called after everything else is done"""
        try:
            if not table or table.columnCount() == 0:
                return
                
            header = table.horizontalHeader()
            available_width = table.viewport().width()
            
            # Simple approach: just force STRETCH mode for equal distribution
            if available_width > 200:
                print(f"[RENTAL FINAL] Forcing STRETCH mode for equal distribution")
                
                # Aggressively set STRETCH mode
                for col in range(table.columnCount()):
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                
                # Force header settings
                header.setStretchLastSection(False)
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                
                # Force table to take full width
                table.setMinimumWidth(0)
                table.setMaximumWidth(16777215)
                policy = table.sizePolicy()
                policy.setHorizontalPolicy(policy.Expanding)
                table.setSizePolicy(policy)
                
                print(f"[RENTAL FINAL] Applied STRETCH mode to all {table.columnCount()} columns")
                
                # Verify the modes were set
                for col in range(table.columnCount()):
                    mode = header.sectionResizeMode(col)
                    mode_name = {0: "Interactive", 1: "Fixed", 2: "Stretch", 3: "ResizeToContents"}.get(mode, f"Unknown({mode})")
                    print(f"[RENTAL FINAL] Column {col} mode: {mode_name}")
            
        except Exception as e:
            print(f"Failed to apply final column mode override: {e}")

    def _force_column_modes(self, table):
        """Force column modes to stick - called multiple times to override any interference"""
        try:
            if not table or table.columnCount() == 0:
                return
                
            header = table.horizontalHeader()
            available_width = table.viewport().width()
            
            # Calculate if content should fit (same logic as main method)
            content_widths = {}
            sample_size = min(5, table.rowCount())
            
            for col in range(table.columnCount()):
                header_item = table.horizontalHeaderItem(col)
                header_text = header_item.text() if header_item else ""
                header_width = len(header_text) * 8 + 20
                
                max_content_width = header_width
                for row in range(sample_size):
                    item = table.item(row, col)
                    if item:
                        content_text = item.text()
                        content_width = len(content_text) * 8 + 20
                        max_content_width = max(max_content_width, content_width)
                
                # Apply same intelligent bounds as main method
                header_lower = header_text.lower()
                if any(keyword in header_lower for keyword in ["tenant", "name"]):
                    content_widths[col] = max(120, min(max_content_width, 180))
                elif any(keyword in header_lower for keyword in ["room", "number"]):
                    content_widths[col] = max(80, min(max_content_width, 100))
                elif any(keyword in header_lower for keyword in ["advanced", "paid", "total", "cost", "bill", "amount"]):
                    content_widths[col] = max(100, min(max_content_width, 130))
                elif any(keyword in header_lower for keyword in ["created", "updated"]):
                    content_widths[col] = max(110, min(max_content_width, 130))
                else:
                    content_widths[col] = max(80, min(max_content_width, 150))
            
            # Apply hybrid approach
            total_width = sum(content_widths.values())
            content_fits = total_width <= (available_width - 30)
            
            if content_fits and available_width > 200:
                # Force STRETCH mode
                for col in range(table.columnCount()):
                    header.setSectionResizeMode(col, QHeaderView.Stretch)
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                print(f"[RENTAL FORCE] Applied STRETCH mode for {table.columnCount()} columns")
            else:
                # Force FIXED mode
                for col in range(table.columnCount()):
                    header.setSectionResizeMode(col, QHeaderView.Fixed)
                    table.setColumnWidth(col, content_widths[col])
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                print(f"[RENTAL FORCE] Applied FIXED mode with widths: {list(content_widths.values())}")
            
            # Force header settings
            header.setStretchLastSection(False)
            
        except Exception as e:
            print(f"Failed to force column modes: {e}")

    def _emergency_resize_fallback(self):
        """Emergency resize fallback when all other methods fail"""
        try:
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                # Use stretch mode for consistent behavior even in emergency fallback
                header = self.rental_records_table.horizontalHeader()
                for col in range(self.rental_records_table.columnCount()):
                    try:
                        header.setSectionResizeMode(col, QHeaderView.Stretch)
                    except Exception:
                        pass  # Continue with other columns
                
                # Ensure stretch last section is enabled
                try:
                    header.setStretchLastSection(True)
                    self.rental_records_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
                print("[RENTAL TAB] Optimization safe mode enabled")
            else:
                print("[RENTAL TAB] Cannot enable safe mode - optimization manager not available")
        except Exception as e:
            print(f"[RENTAL TAB] Failed to enable safe mode: {e}")
    
    def disable_all_optimizations(self):
        """Disable all optimizations and use fallback mode"""
        try:
            if self._optimization_manager:
                self._optimization_manager.disable_all_optimizations()
                print("[RENTAL TAB] All optimizations disabled")
            else:
                print("[RENTAL TAB] Optimizations already disabled")
        except Exception as e:
            print(f"[RENTAL TAB] Failed to disable optimizations: {e}")
    
    def reset_optimization_state(self):
        """Reset optimization state and clear errors for recovery"""
        try:
            if self._optimization_manager:
                self._optimization_manager.reset_optimization_state()
                print("[RENTAL TAB] Optimization state reset")
            else:
                # Try to reinitialize optimization components
                self._setup_optimization_components()
                print("[RENTAL TAB] Attempted to reinitialize optimization components")
        except Exception as e:
            print(f"[RENTAL TAB] Failed to reset optimization state: {e}")
    
    def print_optimization_report(self):
        """Print detailed optimization performance and error report for debugging"""
        try:
            status = self.get_optimization_status()
            
            print("\n=== RENTAL TAB OPTIMIZATION REPORT ===")
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
            
            print("=" * 45)
            
        except Exception as e:
            print(f"Failed to print optimization report: {e}")
    
    def force_column_width_refresh(self):
        """Force refresh of column widths to ensure they stick to the window"""
        try:
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                # Clear any cached widths to force recalculation
                if hasattr(self, '_cache_manager') and self._cache_manager:
                    self._cache_manager.invalidate_cache_for_table('rental_table')
                
                # Force immediate recalculation with multiple attempts
                def attempt_resize(attempt=1):
                    try:
                        viewport_width = self.rental_records_table.viewport().width()
                        print(f"[RENTAL FORCE REFRESH] Attempt {attempt}: Viewport width = {viewport_width}px")
                        
                        if viewport_width > 50:
                            self._set_intelligent_column_widths(self.rental_records_table)
                            print(f"[RENTAL FORCE REFRESH] Success on attempt {attempt}")
                        elif attempt < 5:
                            # Retry with increasing delay
                            QTimer.singleShot(attempt * 100, lambda: attempt_resize(attempt + 1))
                        else:
                            print(f"[RENTAL FORCE REFRESH] Failed after {attempt} attempts")
                    except Exception as e:
                        print(f"[RENTAL FORCE REFRESH] Error on attempt {attempt}: {e}")
                
                attempt_resize()
                
        except Exception as e:
            print(f"Failed to force column width refresh: {e}")
            # Fallback to original resize behavior
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
                    super(RentalInfoTab, self).showEvent(event)
                    
                # Trigger optimized initial table sizing
                if hasattr(self, '_debounce_manager') and self._debounce_manager:
                    QTimer.singleShot(100, self._debounce_manager.trigger_debounced_resize)
                    
            self.showEvent = optimized_showEvent
            
            # Ensure table resize handlers also use debounced system
            if hasattr(self, 'rental_records_table') and self.rental_records_table:
                # Override any existing table resize handlers
                def optimized_table_resize():
                    if hasattr(self, '_debounce_manager') and self._debounce_manager:
                        self._debounce_manager.trigger_debounced_resize()
                        
                # Replace any existing table resize connections
                try:
                    # Disconnect existing connections if any
                    self.rental_records_table.horizontalHeader().sectionResized.disconnect()
                except:
                    pass
                    
                # Connect to debounced system
                self.rental_records_table.horizontalHeader().sectionResized.connect(
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
            
            # Add sample of table content (first few rows)
            sample_rows = min(table.rowCount(), 10)
            for row in range(sample_rows):
                row_content = []
                for col in range(table.columnCount()):
                    item = table.item(row, col)
                    if item:
                        row_content.append(item.text()[:50])  # Limit text length for hash
                content_parts.append('|'.join(row_content))
            
            # Add table dimensions
            content_parts.append(f"{table.rowCount()}x{table.columnCount()}")
            
            # Create hash
            content_string = '||'.join(content_parts)
            return hashlib.md5(content_string.encode()).hexdigest()
            
        except Exception as e:
            print(f"Failed to generate cache key: {e}")
            # Fallback to simple key
            return f"table_{table.columnCount()}_{table.rowCount()}_{time.time()}"

    def _get_cached_font_metrics(self, header_item, table):
        """Get cached font metrics or calculate and cache new ones"""
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                # Generate font key
                if header_item:
                    font = header_item.font()
                else:
                    font = table.font()
                    
                font_key = f"{font.family()}_{font.pointSize()}_{font.weight()}_{font.bold()}"
                
                # Try to get cached metrics
                cached_metrics = self._cache_manager.get_cached_font_metrics(font_key)
                if cached_metrics:
                    if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                        self._debug_manager.log_cache_operation('font_metrics', True)
                    return cached_metrics['metrics']
                
                # Cache miss - calculate and cache
                from PyQt5.QtGui import QFontMetrics
                metrics = QFontMetrics(font)
                self._cache_manager.cache_font_metrics(font_key, font, metrics)
                
                if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                    self._debug_manager.log_cache_operation('font_metrics', False)
                    
                return metrics
            else:
                # No cache manager - direct calculation
                from PyQt5.QtGui import QFontMetrics
                if header_item:
                    return QFontMetrics(header_item.font())
                else:
                    return QFontMetrics(table.font())
                    
        except Exception as e:
            print(f"Font metrics caching failed: {e}")
            # Fallback to direct calculation
            from PyQt5.QtGui import QFontMetrics
            if header_item:
                return QFontMetrics(header_item.font())
            else:
                return QFontMetrics(table.font())

    def _get_cached_font_metrics_for_column(self, table: TableWidget, col: int, header_text: str):
        """Get cached font metrics for a specific column with priority-aware font configuration"""
        try:
            # Determine if this is a priority column
            is_priority = self._is_priority_column('rental_table', header_text)
            
            # Get font configuration based on priority
            if is_priority:
                font_size = self.FONT_SIZES['priority_columns']
                font_weight = self.FONT_WEIGHTS['priority_columns']
            else:
                font_size = self.FONT_SIZES['regular_columns']
                font_weight = self.FONT_WEIGHTS['regular_columns']
            
            # Generate font cache key
            font_key = f"rental_font_{font_size}_{font_weight}"
            
            # Try to get cached font metrics
            if hasattr(self, '_cache_manager') and self._cache_manager:
                cached_metrics = self._cache_manager.get_cached_font_metrics(font_key)
                if cached_metrics:
                    if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                        self._debug_manager.log_cache_operation('font_metrics', 'get_cached_metrics', True,
                                                              {'font_key': font_key, 'column': col})
                    return cached_metrics['metrics']
            
            # Cache miss - create new font and metrics
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
            if hasattr(self, '_cache_manager') and self._cache_manager and hasattr(self, 'rental_records_table'):
                self._cache_manager.invalidate_cache_for_table('rental_table')
                
                if hasattr(self, '_debug_manager') and self._debug_manager and self._debug_manager.enabled:
                    self._debug_manager.log_cache_operation('cache_invalidation', 'data_change', True,
                                                          {'table': 'rental_table', 'reason': 'data_update'})
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
                    print(f"[RENTAL DEBUG] {operation}")
                    if details:
                        for key, value in details.items():
                            print(f"  {key}: {value}")
            
            # Always log to console if debug enabled (for immediate feedback)
            elif self._resize_debug_enabled:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                if duration is not None:
                    status = "SLOW" if duration > 100 else "OK"
                    print(f"[{timestamp}] RENTAL RESIZE: {operation} - {duration:.2f}ms [{status}]")
                else:
                    print(f"[{timestamp}] RENTAL DEBUG: {operation}")
                
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
                    'table_type': 'rental_table',
                    'current_row_count': self.rental_records_table.rowCount() if hasattr(self, 'rental_records_table') and self.rental_records_table else 0,
                    'current_column_count': self.rental_records_table.columnCount() if hasattr(self, 'rental_records_table') and self.rental_records_table else 0
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
            
            print("\n=== RENTAL TAB CACHE PERFORMANCE REPORT ===")
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
            if not hasattr(self, 'rental_records_table') or not self.rental_records_table:
                print("No rental records table available for debugging")
                return
            
            table = self.rental_records_table
            print("\n=== RENTAL TAB COLUMN WIDTH DEBUG ===")
            
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

    def _apply_cached_column_widths(self, table: QTableWidget, column_widths: List[int]):
        """Apply cached column widths to table with improved proportional distribution"""
        try:
            header = table.horizontalHeader()
            available_width = table.viewport().width()
            column_count = len(column_widths)
            
            print(f"[RENTAL DEBUG] Applying cached widths with hybrid approach")
            
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


    def _handle_file_upload(self, file_type, status_label):
        """Handle file upload with modern feedback"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {file_type.replace('_', ' ').title()} Image", "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp);;All Files (*)", 
            options=options
        )
        
        if file_path:
            if not self._is_safe_path(file_path):
                QMessageBox.warning(self, "Forbidden Path", "The selected location is not permitted.")
                return
            if not self._validate_image_file(file_path):
                QMessageBox.warning(self, "Invalid File", "The selected file is not a valid image.")
                return

            # Store the file (same logic as original upload_image method)
            self.IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            
            try:
                # Generate unique filename
                file_extension = Path(file_path).suffix
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                destination_path = self.IMAGE_STORAGE_DIR / unique_filename

                # Copy file
                shutil.copy2(file_path, destination_path)
                
                # Update widget state with safety checks
                try:
                    if status_label is not None:
                        # Find the correct widget by file_type instead of navigating parent hierarchy
                        widget = None
                        if file_type == "photo":
                            widget = self.photo_widget
                        elif file_type == "nid_front":
                            widget = self.nid_front_widget
                        elif file_type == "nid_back":
                            widget = self.nid_back_widget
                        elif file_type == "police_form":
                            widget = self.police_form_widget
                        
                        if widget is not None:
                            widget.file_path = str(destination_path)
                            print(f"DEBUG: Set {file_type} file_path to: {destination_path}")
                        
                        # Update status label safely
                        status_label.setText(f"✓ {Path(file_path).name}")
                        status_label.setTextColor("#28a745", "#34d058")
                except Exception as widget_error:
                    print(f"Warning: Could not update upload widget UI for {file_type}: {widget_error}")
                
                # Update the corresponding label for compatibility with existing code
                try:
                    self._update_legacy_path_labels(file_type, str(destination_path))
                except Exception as legacy_error:
                    print(f"Warning: Could not update legacy labels for {file_type}: {legacy_error}")
                
                QMessageBox.information(self, "File Uploaded", f"File uploaded successfully: {destination_path.name}")
                
            except Exception as e:
                QMessageBox.critical(self, "Upload Error", f"Failed to upload file: {e}")
                
    def _clear_file_upload(self, file_type, status_label):
        """Clear file upload with visual feedback"""
        try:
            # Find the correct widget by file_type instead of navigating parent hierarchy
            widget = None
            if file_type == "photo":
                widget = self.photo_widget
            elif file_type == "nid_front":
                widget = self.nid_front_widget
            elif file_type == "nid_back":
                widget = self.nid_back_widget
            elif file_type == "police_form":
                widget = self.police_form_widget
            
            if widget is not None and hasattr(widget, 'file_path'):
                widget.file_path = None
                print(f"DEBUG: Cleared {file_type} file_path")
            
            # Update status label safely
            if status_label is not None:
                status_label.setText("No file selected")
                status_label.setTextColor("#999999", "#7f7f7f")
            
        except Exception as e:
            # Log the error but don't crash the application
            print(f"Warning: Could not clear file upload for {file_type}: {e}")
        
        # Update legacy labels for compatibility (this should always work)
        try:
            self._update_legacy_path_labels(file_type, "No file selected")
        except Exception as e:
            print(f"Warning: Could not update legacy labels for {file_type}: {e}")

    def _ensure_legacy_labels_exist(self):
        """Ensure legacy path labels exist for backward compatibility"""
        if not hasattr(self, 'photo_path_label') or self.photo_path_label is None:
            self.photo_path_label = LineEdit()
            self.photo_path_label.setText("No file selected")
            
        if not hasattr(self, 'nid_front_path_label') or self.nid_front_path_label is None:
            self.nid_front_path_label = LineEdit()
            self.nid_front_path_label.setText("No file selected")
            
        if not hasattr(self, 'nid_back_path_label') or self.nid_back_path_label is None:
            self.nid_back_path_label = LineEdit()
            self.nid_back_path_label.setText("No file selected")
            
        if not hasattr(self, 'police_form_path_label') or self.police_form_path_label is None:
            self.police_form_path_label = LineEdit()
            self.police_form_path_label.setText("No file selected")

    def _get_file_path_from_widget(self, widget, file_type):
        """Get file path directly from upload widget"""
        try:
            # Check if widget has file_path attribute and it's not None
            if hasattr(widget, 'file_path') and widget.file_path is not None:
                return widget.file_path
            
            # Fallback to legacy label if widget doesn't have path
            self._ensure_legacy_labels_exist()
            if file_type == "photo" and hasattr(self, 'photo_path_label'):
                return self.photo_path_label.text()
            elif file_type == "nid_front" and hasattr(self, 'nid_front_path_label'):
                return self.nid_front_path_label.text()
            elif file_type == "nid_back" and hasattr(self, 'nid_back_path_label'):
                return self.nid_back_path_label.text()
            elif file_type == "police_form" and hasattr(self, 'police_form_path_label'):
                return self.police_form_path_label.text()
            
            return "No file selected"
        except Exception as e:
            print(f"Warning: Could not get file path for {file_type}: {e}")
            return "No file selected"

    def _update_legacy_path_labels(self, file_type, path):
        """Update legacy path labels for backward compatibility"""
        # Ensure labels exist first
        self._ensure_legacy_labels_exist()
            
        if file_type == "photo":
            self.photo_path_label.setText(path)
        elif file_type == "nid_front":
            self.nid_front_path_label.setText(path)
        elif file_type == "nid_back":
            self.nid_back_path_label.setText(path)
        elif file_type == "police_form":
            self.police_form_path_label.setText(path)

    def _update_upload_widget_for_edit(self, file_type, file_path):
        """Update upload widget status when loading record for edit"""
        try:
            # Get the appropriate widget
            widget = None
            if file_type == "photo":
                widget = self.photo_widget
            elif file_type == "nid_front":
                widget = self.nid_front_widget
            elif file_type == "nid_back":
                widget = self.nid_back_widget
            elif file_type == "police_form":
                widget = self.police_form_widget
            
            if widget and hasattr(widget, 'status_label'):
                if file_path and file_path != "No file selected":
                    # Store the file path in the widget
                    widget.file_path = file_path
                    
                    # Update status label to show file is loaded
                    if file_path.startswith("http"):
                        widget.status_label.setText("✓ Cloud file")
                    else:
                        # Extract filename from path
                        filename = Path(file_path).name if file_path else "Unknown file"
                        widget.status_label.setText(f"✓ {filename}")
                    
                    widget.status_label.setTextColor("#28a745", "#34d058")
                else:
                    # Clear the widget
                    widget.file_path = None
                    widget.status_label.setText("No file selected")
                    widget.status_label.setTextColor("#999999", "#7f7f7f")
        except Exception as e:
            print(f"Warning: Could not update upload widget for {file_type}: {e}")

    def save_rental_record(self):
        try:
            tenant_name = self.tenant_name_input.text().strip()
            room_number = self.room_number_input.text().strip()
            advanced_paid_str = self.advanced_paid_input.text().strip()
            
            # Ensure legacy labels exist and get file paths safely
            try:
                self._ensure_legacy_labels_exist()
                
                # Get file paths directly from upload widgets (more reliable than legacy labels)
                photo_path = self._get_file_path_from_widget(self.photo_widget, "photo")
                nid_front_path = self._get_file_path_from_widget(self.nid_front_widget, "nid_front")
                nid_back_path = self._get_file_path_from_widget(self.nid_back_widget, "nid_back")
                police_form_path = self._get_file_path_from_widget(self.police_form_widget, "police_form")
                
                print(f"DEBUG: File paths - Photo: {photo_path}, NID Front: {nid_front_path}, NID Back: {nid_back_path}, Police: {police_form_path}")
                        
            except Exception as path_error:
                QMessageBox.critical(self, "Path Error", f"Failed to get file paths: {path_error}")
                return

            save_to_pc = self.save_to_pc_switch.isChecked()
            save_to_cloud = self.save_to_cloud_switch.isChecked()

            if not tenant_name or not room_number:
                QMessageBox.warning(self, "Input Error", "Tenant Name and Room Number cannot be empty.")
                return

            if not save_to_pc and not save_to_cloud:
                QMessageBox.warning(self, "Save Option Error", "Please select at least one destination to save the record (PC or Cloud).")
                return
            
            advanced_paid = float(advanced_paid_str) if advanced_paid_str else 0.0
            
            record_data = {
                "id": self.current_rental_id,
                "supabase_id": self.current_supabase_id,
                "tenant_name": tenant_name,
                "room_number": room_number,
                "advanced_paid": advanced_paid,
                "photo_path": photo_path if photo_path != "No file selected" else None,
                "nid_front_path": nid_front_path if nid_front_path != "No file selected" else None,
                "nid_back_path": nid_back_path if nid_back_path != "No file selected" else None,
                "police_form_path": police_form_path if police_form_path != "No file selected" else None,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "is_archived": 1 if self.current_is_archived else 0
            }
            
            # If saving to PC, make sure any remote URLs are cached locally so the
            # record remains viewable offline. We keep a separate copy so the cloud
            # upload (if requested) can still reference the original URLs and avoid
            # duplicate uploads.
            local_record_data = record_data.copy()
            if save_to_pc:
                for key in ("photo_path", "nid_front_path", "nid_back_path", "police_form_path"):
                    local_record_data[key] = self._ensure_local_copy(local_record_data.get(key))

            local_save_success = True
            cloud_save_success = True
            
            if save_to_pc:
                try:
                    if self.current_rental_id:
                        update_query = """
                            UPDATE rentals SET
                                tenant_name = :tenant_name, room_number = :room_number,
                                advanced_paid = :advanced_paid, photo_path = :photo_path,
                                nid_front_path = :nid_front_path, nid_back_path = :nid_back_path,
                                police_form_path = :police_form_path, updated_at = :updated_at,
                                is_archived = :is_archived
                            WHERE id = :id
                        """
                        self.db_manager.execute_query(update_query, local_record_data)
                        if self.db_manager.cursor.rowcount == 0:
                            try:
                                new_id = self.db_manager.insert_rental_record(local_record_data)
                                self.current_rental_id = new_id
                            except Exception as ins_e:
                                print(f"Local insert fallback failed: {ins_e}")
                                local_save_success = False
                    else:
                        self.db_manager.insert_rental_record(local_record_data)
                    print("Record saved to local DB successfully.")
                except Exception as e:
                    local_save_success = False
                    QMessageBox.critical(self, "Local DB Error", f"Failed to save record to local DB: {e}")
            
            if save_to_cloud:
                if self.main_window.supabase_manager.is_client_initialized():
                    try:
                        image_paths = {
                            "photo": record_data.get("photo_path"),
                            "nid_front": record_data.get("nid_front_path"),
                            "nid_back": record_data.get("nid_back_path"),
                            "police_form": record_data.get("police_form_path"),
                        }
                        result = self.main_window.supabase_manager.save_rental_record(record_data, image_paths)
                        if isinstance(result, str) and "Successfully" in result:
                            print("Record saved to Supabase successfully.")
                        else:
                            cloud_save_success = False
                            QMessageBox.critical(self, "Supabase Error", f"Failed to save record to Supabase: {result}")
                    except Exception as e:
                        cloud_save_success = False
                        QMessageBox.critical(self, "Supabase Error", f"Failed to save record to Supabase: {e}")
                else:
                    QMessageBox.warning(self, "Supabase Not Configured", "Supabase client is not initialized. Cannot save to cloud.")
                    cloud_save_success = False

            if local_save_success and cloud_save_success:
                QMessageBox.information(self, "Success", "Rental record saved successfully.")
                self.clear_form()
                self.load_rental_records()
            elif local_save_success or cloud_save_success:
                QMessageBox.information(self, "Partial Success", "Record saved to some destinations. Check error messages above.")
                self.load_rental_records()
            else:
                QMessageBox.critical(self, "Save Failed", "Failed to save record to any destination.")
                
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred while saving: {e}")
            print(f"Save error traceback: {traceback.format_exc()}")

    def load_rental_records(self, force_refresh: bool = False):
        # Clear current table contents first
        self.rental_records_table.clearContents()
        self.rental_records_table.setRowCount(0)
        
        # Invalidate cache when table content is cleared
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                self._cache_manager.invalidate_cache_for_table('rental_table')
        except Exception as e:
            print(f"Cache invalidation on table clear failed: {e}")

        selected_source = self.load_source_combo.currentText()

        if selected_source == "Local DB":
            # Use cache unless forced to refresh
            try:
                if self._local_records_cache is not None and not force_refresh:
                    self._populate_rental_table(selected_source, self._local_records_cache)
                    return

                records = self.db_manager.execute_query(
                    "SELECT id, tenant_name, room_number, advanced_paid, created_at, updated_at, photo_path, nid_front_path, nid_back_path, police_form_path, is_archived, supabase_id "
                    "FROM rentals WHERE is_archived = 0 ORDER BY created_at DESC"
                )
                self._local_records_cache = records
                print(f"Loaded {len(records)} records from Local DB.")
                self._populate_rental_table(selected_source, records)
            except Exception as e:
                QMessageBox.critical(self, "Local DB Error", f"Failed to load rental records from local DB: {e}")
                traceback.print_exc()
            return

        # ---------- Cloud (Supabase) using background thread with pagination ----------
        if not self.main_window.supabase_manager.is_client_initialized():
            QMessageBox.warning(
                self, "Supabase Not Configured", "Supabase client is not initialized. Cannot load from cloud."
            )
            return

        # If we have cached cloud records and not forcing refresh, render from cache and continue infinite scroll
        if self._cloud_records_cache and not force_refresh:
            self._populate_rental_table(selected_source, self._cloud_records_cache, append=False)
            # If more to load, let scroll trigger fetch
            return

        # Reset pagination state for a fresh load
        self._cloud_offset = 0
        self._cloud_has_more = True
        self._cloud_records_cache = []

        # Start first page fetch
        self._start_cloud_fetch(append=False)

    def _start_cloud_fetch(self, append: bool):
        if self._is_fetching or not self._cloud_has_more:
            return
        self._is_fetching = True
        self._cloud_append = append

        # Inline progress bar
        if IndeterminateProgressBar is not None and self._inline_progress_bar is None:
            self._inline_progress_bar = IndeterminateProgressBar(parent=self)
            self._inline_progress_bar.setFixedHeight(4)
            self._inline_progress_bar.start()
            self.table_layout.insertWidget(1, self._inline_progress_bar)

        # Disable source combo to prevent re-entrancy
        self.load_source_combo.setEnabled(False)

        # Start the background worker with pagination params
        self._fetch_worker = FetchSupabaseRentalRecordsWorker(
            self.main_window.supabase_manager,
            is_archived=False,
            select=(
                "id, supabase_id, tenant_name, room_number, advanced_paid, photo_url, nid_front_url, nid_back_url, police_form_url, is_archived, created_at, updated_at"
            ),
            limit=self._cloud_page_size,
            offset=self._cloud_offset,
            parent=self,
        )
        # Capture current source label
        source_label = self.load_source_combo.currentText()
        self._fetch_worker.records_fetched.connect(
            lambda recs: self._on_cloud_records_ready(recs, source_label)
        )
        self._fetch_worker.error_occurred.connect(self._on_cloud_records_error)
        self._fetch_worker.finished.connect(self._on_cloud_records_finished)
        self._fetch_worker.start()

    # ------------------------------------------------------------------
    # Background-worker callbacks
    # ------------------------------------------------------------------

    def _on_cloud_records_ready(self, records, source):
        """Handle successful retrieval of records."""
        # Update pagination state
        fetched_count = len(records or [])
        self._cloud_has_more = fetched_count >= self._cloud_page_size
        self._cloud_offset += fetched_count

        if records:
            self._cloud_records_cache.extend(records)
            self._populate_rental_table(source, records, append=self._cloud_append)

        # No button; infinite scroll will trigger further loads

    def _on_cloud_records_error(self, message: str):
        QMessageBox.critical(self, "Cloud DB Error", f"Failed to load rental records from Supabase: {message}")
        # >>> ADD
        # Ensure we tidy up the progress bar even on error
        if self._inline_progress_bar is not None:
            self._inline_progress_bar.stop()
            self.table_layout.removeWidget(self._inline_progress_bar)
            self._inline_progress_bar.deleteLater()
            self._inline_progress_bar = None
        # <<< ADD

    def _on_cloud_records_finished(self):
        """Always called when worker thread ends—success or fail."""
        self.load_source_combo.setEnabled(True)
        if self._inline_progress_bar is not None:
            self._inline_progress_bar.stop()
            self.table_layout.removeWidget(self._inline_progress_bar)
            self._inline_progress_bar.deleteLater()
            self._inline_progress_bar = None
        self._is_fetching = False

    def _on_table_scroll(self, value: int):
        """Called on scroll; if near bottom and cloud source is active, auto-load next page."""
        try:
            source_label = self.load_source_combo.currentText()
            if source_label != "Cloud (Supabase)":
                return
            sb = self.rental_records_table.verticalScrollBar()
            # Threshold when remaining scroll distance is small
            remaining = sb.maximum() - value
            if remaining <= max(20, int(sb.pageStep() * 0.5)):
                self._start_cloud_fetch(append=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Helper to populate table (shared between local & cloud paths)  
    # ------------------------------------------------------------------

    def _populate_rental_table(self, source_label: str, records: list, append: bool = False):
        """Fill or append to the QTableWidget with rental records."""
        if not records:
            return

        # Invalidate cache when table content changes
        try:
            if hasattr(self, '_cache_manager') and self._cache_manager:
                self._cache_manager.invalidate_cache_for_table('rental_table')
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
                # Fallback to manual sorting disable
                prev_sorting = self.rental_records_table.isSortingEnabled()
                if prev_sorting:
                    self.rental_records_table.setSortingEnabled(False)
        else:
            # Fallback: Temporarily disable sorting while inserting rows to avoid jitter
            prev_sorting = self.rental_records_table.isSortingEnabled()
            if prev_sorting:
                self.rental_records_table.setSortingEnabled(False)

        if append:
            start_row = self.rental_records_table.rowCount()
            self.rental_records_table.setRowCount(start_row + len(records))
        else:
            start_row = 0
            self.rental_records_table.setRowCount(len(records))

        for idx, record in enumerate(records):
            row_idx = start_row + idx
            if source_label == "Local DB":
                # SQLite tuple; keep same unpacking as before
                display_id, tenant_name, room_number, advanced_paid, created_at, updated_at = (
                    record[0], record[1], record[2], record[3], record[4], record[5]
                )
                full_record_data = record  # full tuple
            else:  # Cloud (Supabase) -> dict
                display_id = record.get("id")
                tenant_name = record.get("tenant_name")
                room_number = record.get("room_number")
                advanced_paid = record.get("advanced_paid")
                created_at = record.get("created_at")
                updated_at = record.get("updated_at")
                full_record_data = record

            # Create items with History tab's EXACT font styling for ALL columns
            from PyQt5.QtGui import QColor, QFont
            
            # Regular font for non-priority columns (History tab: 10px, 500 weight)
            regular_font = QFont("Segoe UI", 10)
            regular_font.setWeight(500)
            
            # Priority font for Advanced Paid (History tab: 12px, QFont.Bold)
            priority_font = QFont("Segoe UI", 12)
            priority_font.setWeight(QFont.Bold)
            
            # Create items using sophisticated History tab methods for enhanced visual hierarchy
            tenant_item = self._create_identifier_item(str(tenant_name), "tenant")
            # Use NumericTableWidgetItem for numeric sorting on Room Number
            # Copy styling from the identifier item helper to keep visuals consistent
            _styled_room = self._create_identifier_item(str(room_number), "room")
            room_item = NumericTableWidgetItem(_styled_room.text())
            room_item.setTextAlignment(_styled_room.textAlignment())
            room_item.setForeground(_styled_room.foreground())
            room_item.setFont(_styled_room.font())
            # Set numeric key for sorting
            try:
                _room_num_int = int(str(room_number).strip())
                room_item.setData(Qt.UserRole, _room_num_int)
                # Also set EditRole so proxy/model-based sorting treats it as numeric
                room_item.setData(Qt.EditRole, _room_num_int)
            except Exception:
                room_item.setData(Qt.UserRole, 0)
                room_item.setData(Qt.EditRole, 0)
            advanced_item = self._create_special_item(str(advanced_paid), "advanced_paid", is_priority=True)
            created_item = self._create_identifier_item(str(created_at), "date")
            updated_item = self._create_identifier_item(str(updated_at), "date")
            
            self.rental_records_table.setItem(row_idx, 0, tenant_item)
            self.rental_records_table.setItem(row_idx, 1, room_item)
            self.rental_records_table.setItem(row_idx, 2, advanced_item)
            self.rental_records_table.setItem(row_idx, 3, created_item)
            self.rental_records_table.setItem(row_idx, 4, updated_item)

            # Attach raw data for later dialog (store in first column)
            self.rental_records_table.item(row_idx, 0).setData(Qt.UserRole, full_record_data)
        
        # Apply intelligent column widths after populating data with delay to ensure table is fully rendered
        QTimer.singleShot(200, lambda: self._set_intelligent_column_widths(self.rental_records_table))
        
        # Clean up batch update or re-enable sorting
        try:
            if batch_manager_used:
                self._batch_manager.end_batch_update()
                # Sort after batch update is complete
                self.rental_records_table.sortItems(1, Qt.AscendingOrder)
            else:
                # Re-enable sorting and enforce numeric order by Room Number
                if 'prev_sorting' in locals() and prev_sorting:
                    self.rental_records_table.setSortingEnabled(True)
                    self.rental_records_table.sortItems(1, Qt.AscendingOrder)
        except Exception as e:
            print(f"Failed to complete batch update cleanup: {e}")
            # Ensure sorting is re-enabled as fallback
            try:
                self.rental_records_table.setSortingEnabled(True)
                self.rental_records_table.sortItems(1, Qt.AscendingOrder)
            except Exception as fallback_error:
                print(f"Fallback sorting re-enable failed: {fallback_error}")
    

        
        # Always allow horizontal scrollbar when needed
        self.rental_records_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def show_record_details_dialog(self, index):
        if not index.isValid():
            return
            
        selected_row = index.row()
        if selected_row < 0 or selected_row >= self.rental_records_table.rowCount():
            return
            
        item = self.rental_records_table.item(selected_row, 0)
        if not item:
            print(f"No item found at row {selected_row}")
            return
            
        record_data = item.data(Qt.UserRole)
        if not record_data:
            print(f"No record data found for row {selected_row}")
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
                current_source=selected_source, # Pass the current source to the dialog
                supabase_id=record_dict.get("supabase_id") # Pass supabase_id
            )
            dialog.exec_() # Show as modal dialog
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open record details: {e}")
            print(f"Error opening rental record dialog: {e}\n{traceback.format_exc()}")

    def load_record_into_form_for_edit(self, record_data: dict):
        # This method is called from the dialog to load data for editing
        # record_data is expected to be a dictionary (either from local DB or Supabase, flattened)
        self.current_rental_id = record_data.get("id") # Local DB ID
        self.current_supabase_id = record_data.get("supabase_id") # Supabase ID
        # Store archive status so we can retain it during save
        self.current_is_archived = bool(record_data.get("is_archived", False))

        # Fill text inputs
        self.tenant_name_input.setText(record_data.get("tenant_name", ""))
        self.room_number_input.setText(record_data.get("room_number", ""))
        self.advanced_paid_input.setText(str(record_data.get("advanced_paid", 0.0)))

        # Update file upload widgets with existing file paths/URLs
        self._update_upload_widget_for_edit("photo", record_data.get("photo_path") or record_data.get("photo_url"))
        self._update_upload_widget_for_edit("nid_front", record_data.get("nid_front_path") or record_data.get("nid_front_url"))
        self._update_upload_widget_for_edit("nid_back", record_data.get("nid_back_path") or record_data.get("nid_back_url"))
        self._update_upload_widget_for_edit("police_form", record_data.get("police_form_path") or record_data.get("police_form_url"))
        
        # Ensure legacy labels exist and update them for compatibility
        self._ensure_legacy_labels_exist()
        self.photo_path_label.setText(record_data.get("photo_path") or record_data.get("photo_url") or "No file selected")
        self.nid_front_path_label.setText(record_data.get("nid_front_path") or record_data.get("nid_front_url") or "No file selected")
        self.nid_back_path_label.setText(record_data.get("nid_back_path") or record_data.get("nid_back_url") or "No file selected")
        self.police_form_path_label.setText(record_data.get("police_form_path") or record_data.get("police_form_url") or "No file selected")
        
        self.save_record_btn.setText("Update Record")
        self.tenant_name_input.setFocus() # Set focus back to the form

    def clear_form(self):
        # Clear input fields
        self.tenant_name_input.clear()
        self.room_number_input.clear()
        self.advanced_paid_input.clear()
        
        # Clear file upload widgets
        self._clear_file_upload("photo", self.photo_widget.status_label)
        self._clear_file_upload("nid_front", self.nid_front_widget.status_label)
        self._clear_file_upload("nid_back", self.nid_back_widget.status_label)
        self._clear_file_upload("police_form", self.police_form_widget.status_label)
        
        # Reset form state
        self.current_rental_id = None
        self.current_supabase_id = None
        self.current_is_archived = False
        self.save_record_btn.setText("Save Record")

    def _handle_enter_pressed(self, current_index):
        """Handles Enter key press for sequential focus movement."""
        last_idx = len(self.input_fields) - 1
        # Cycle only within the three input fields
        target = self.input_fields[(current_index + 1) % (last_idx + 1)]
        target.setFocus()
        if isinstance(target, QLineEdit):
            target.selectAll()
        return True  # Event handled – stop further processing

    def eventFilter(self, obj, event):
        """Filters events to handle Up/Down arrow key navigation."""
        if event.type() == QEvent.KeyPress and obj in self.input_fields:
            current_index = self.input_fields.index(obj)
            if event.key() == Qt.Key_Down:
                target = self.input_fields[(current_index + 1) % len(self.input_fields)]
                target.setFocus()
                if isinstance(target, QLineEdit):
                    target.selectAll()
                return True  # Event handled
            elif event.key() == Qt.Key_Up:
                target = self.input_fields[(current_index - 1) % len(self.input_fields)]
                target.setFocus()
                if isinstance(target, QLineEdit):
                    target.selectAll()
                return True  # Event handled
        return super().eventFilter(obj, event)

    def _rel_to(self, p: Path, root: Path) -> bool:
        """Helper to safely check if a path is relative to a root, guarding against ValueError."""
        try:
            return p.is_relative_to(root)
        except ValueError:
            return False

    def _is_safe_path(self, p: str) -> bool:
        """
        Validate that the file path is safe to access, considering symlinks and preventing
        directory traversal attacks.

        This function performs several security checks:
        1. Ensures the path is not empty.
        2. Handles potential OSError during path normalization.
        3. Checks the original (user-supplied) path against a list of forbidden directories.
        4. Prevents directory traversal attempts by checking for ".." segments in the original path.
        5. Resolves the path to its true location, handling symlinks.
        6. Checks the resolved path against forbidden directories (defense-in-depth).
        7. Checks the resolved path against a list of allowed safe directories.
        """
        if not p:
            return False

        try:
            # Convert the input string to a Path object for easier manipulation
            original_path = Path(p)
            # Normalize original path for case-insensitive comparison on Windows
            original_path_norm = Path(os.path.normcase(str(original_path)))
        except OSError: # Catches invalid path strings (e.g. containing null bytes)
            # If path conversion fails, it's not a safe path
            return False

        # 1. Check original path against forbidden directories (before resolving symlinks)
        # This prevents access to sensitive system directories even if symlinked from a safe location.
        if any(self._rel_to(original_path_norm, Path(os.path.normcase(str(fd)))) for fd in self.FORBIDDEN):
            return False

        # 2. Reject any traversal attempt visible in the user-supplied path
        # Path.resolve() eliminates ".." segments, so this check must be done before resolution.
        if any(part == ".." for part in original_path.parts):
            return False

        # 3. Resolve the path to check its true location
        # This handles symlinks and gets the canonical path.
        try:
            resolved_path = original_path.resolve(strict=False)
            resolved_path_norm = Path(os.path.normcase(str(resolved_path)))
        except OSError:
            # If resolution fails (e.g., path does not exist or permissions issue), it's not a safe path
            return False

        # 4. Explicitly check for directory traversal segments in the resolved path (defense-in-depth)
        # While resolve() typically removes '..', this acts as an additional safeguard.
        if any(part == ".." for part in resolved_path.parts):
            return False

        # 5. Check resolved path against forbidden directories (in case a safe path symlinks to a forbidden one)
        if any(self._rel_to(resolved_path_norm, Path(os.path.normcase(str(fd)))) for fd in self.FORBIDDEN):
            return False

        # 6. Check resolved path against safe directories
        return any(self._rel_to(resolved_path_norm, Path(os.path.normcase(str(sd)))) for sd in self.SAFE_DIRS)

    def _validate_image_file(self, file_path):
        """Validate that the file is actually an image"""
        try:
            pixmap = QPixmap(file_path)
            return not pixmap.isNull()
        except Exception:
            return False

    def _scale_image(self, image_path, max_width_points, max_height_points):
        # If the path is a URL, download to temp file first
        if image_path and str(image_path).startswith("http"):
            try:
                import requests, tempfile, urllib.parse, os as _os

                # Parse the URL to safely extract the file extension (ignore query params)
                parsed = urllib.parse.urlparse(image_path)
                url_path = parsed.path  # e.g. "/storage/v1/object/public/..../image.jpg"
                _root, ext = _os.path.splitext(url_path)
                # Fallback to .jpg if extension missing or contains illegal chars (e.g. '.jpg?')
                if not ext or any(c in ext for c in "?&#%"):
                    ext = ".jpg"

                # Disable TLS certificate verification to avoid failures in bundled executables
                r = requests.get(image_path, timeout=10, verify=False)
                if r.status_code == 200:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    tmp.write(r.content)
                    tmp.close()
                    image_path = tmp.name
                    # temp files are considered safe
                    safe_bypass = True
                else:
                    return None, 0, 0
            except Exception as url_exc:
                print(f"Error downloading image {image_path}: {url_exc}")
                return None, 0, 0

        if not image_path or ('safe_bypass' not in locals() and not self._is_safe_path(image_path)) or not os.path.exists(image_path):
            return None, 0, 0
        try:
            # Use ReportLab's ImageReader to get original dimensions in points
            img_reader = ImageReader(image_path)
            original_width_points, original_height_points = img_reader.getSize()

            # Calculate scaling factors
            width_scale = max_width_points / original_width_points
            height_scale = max_height_points / original_height_points
            scale_factor = min(width_scale, height_scale)

            # If the image is already smaller than the max dimensions, don't upscale
            if scale_factor >= 1.0:
                return image_path, original_width_points, original_height_points

            new_width_points = original_width_points * scale_factor
            new_height_points = original_height_points * scale_factor

            # Return the original path and new dimensions in points
            return image_path, new_width_points, new_height_points
        except Exception as e:
            print(f"Error scaling image {image_path}: {e}")
            traceback.print_exc()
            return None, 0, 0

    def generate_rental_pdf_from_data(self, record_data):
        tenant_name = record_data[1]
        room_number = record_data[2]
        advanced_paid = record_data[3]
        created_at = record_data[4]
        updated_at = record_data[5]
        photo_path = record_data[6]
        nid_front_path = record_data[7]
        nid_back_path = record_data[8]
        police_form_path = record_data[9]

        # Define PDF file name
        def _sanitize(s):
            # Replace invalid filename characters with underscore
            return re.sub(r'[\\/*?:"<>|]', '_', str(s)).replace(' ', '_')

        pdf_filename = f"Rental_Record_{_sanitize(tenant_name)}_{_sanitize(room_number)}.pdf"
        pdf_path = os.path.join(os.path.expanduser("~/Documents"), pdf_filename)

        try:
            doc = BaseDocTemplate(pdf_path, pagesize=letter,
                                  leftMargin=0.1 * inch, rightMargin=0.1 * inch,
                                  topMargin=0.1 * inch, bottomMargin=0.1 * inch)
            styles = getSampleStyleSheet()

            # Custom style for centered bold text
            centered_bold_style = ParagraphStyle(
                'CenteredBold',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=3
            )

            # Custom style for "Associated Documents:" to control spacing
            associated_docs_style = ParagraphStyle(
                'AssociatedDocs',
                parent=styles['h3'], # Inherit font/size from h3, but override spacing
                spaceBefore=0,
                spaceAfter=0
            )

            # Define Frames for Page 1 (Rental Details)
            frame1_height = letter[1] - (2 * 0.1 * inch) # Page height - top/bottom margins
            frame1 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, frame1_height,
                           leftPadding=0, bottomPadding=0,
                           rightPadding=0, topPadding=0,
                           showBoundary=1) # Set showBoundary=1 for debugging frames

            # Define Frames for Page 2 (Tenant Photo, NID Front/Back)
            # Page width and height for calculations
            page_width, page_height = letter

            # Margins for Page 2 frames
            p2_left_margin = 0.1 * inch
            p2_right_margin = 0.1 * inch
            p2_top_margin = 0.1 * inch
            p2_bottom_margin = 0.1 * inch

            # Calculate usable width and height for frames
            usable_width = page_width - p2_left_margin - p2_right_margin
            usable_height = page_height - p2_top_margin - p2_bottom_margin

            # Define a single full-page frame for Page 2
            frame2_full = Frame(p2_left_margin, p2_bottom_margin, usable_width, usable_height,
                                leftPadding=0, bottomPadding=0,
                                rightPadding=0, topPadding=0,
                                showBoundary=1)

            # Define Frames for Page 3 (Police Form)
            frame3_height = letter[1] - (2 * 0.1 * inch)
            frame3 = Frame(doc.leftMargin, doc.bottomMargin, doc.width, frame3_height,
                           leftPadding=0, bottomPadding=0,
                           rightPadding=0, topPadding=0,
                           showBoundary=1)

            # Define Page Templates
            page_template_1 = PageTemplate(id='Page1', frames=[frame1])
            page_template_2 = PageTemplate(id='Page2', frames=[frame2_full]) # Use single frame
            page_template_3 = PageTemplate(id='Page3', frames=[frame3])

            doc.addPageTemplates([page_template_1, page_template_2, page_template_3])

            all_elements = []
            
            # --- Page 1: Rental Information Data ---
            all_elements.append(Paragraph("Rental Information Record", centered_bold_style))
            all_elements.append(Spacer(1, 0.02 * inch))

            # Tenant Details Table
            data = [
                ["Field", "Details"],
                ["Tenant Name:", tenant_name],
                ["Room Number:", room_number],
                ["Advanced Paid:", f"TK {advanced_paid:,.2f}"],
                ["Record Created:", created_at],
                ["Last Updated:", updated_at]
            ]
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ])
            table = Table(data, colWidths=[2 * inch, 4 * inch])
            table.setStyle(table_style)
            all_elements.append(table)
            all_elements.append(Spacer(1, 0.02 * inch))
            all_elements.append(NextPageTemplate('Page2')) # Set template for the next page
            all_elements.append(PageBreak()) # Force a page break

            # --- Page 2: Tenant Photo, NID Front/Back ---
            # Define a common max height for images on Page 2 to ensure they fit
            # Set a fixed maximum height for each image to ensure all three fit on the page.
            max_image_height_p2 = 3.0 * inch # Each image will be scaled to fit within 3 inches height

            all_elements.append(Paragraph("<b>Associated Documents:</b>", associated_docs_style))
            all_elements.append(Spacer(1, 0.05 * inch)) # Use a fixed spacer height

            # Tenant Photo
            if photo_path and (photo_path.startswith("http") or (os.path.exists(photo_path) and self._is_safe_path(photo_path))):
                all_elements.append(Paragraph("<b>Tenant Photo:</b>", ParagraphStyle('ImageTitle', parent=styles['Normal'], spaceAfter=0, leading=0)))
                scaled_image_path, img_width_points, img_height_points = self._scale_image(photo_path, usable_width, max_image_height_p2)
                if scaled_image_path:
                    img = Image(scaled_image_path, width=img_width_points, height=img_height_points, kind='proportional')
                    img.hAlign = 'CENTER' # Center the image horizontally
                    all_elements.append(img)
                else:
                    all_elements.append(Paragraph(f"<i>Could not load image from {photo_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>Tenant Photo: Not provided or file not found/safe.</i>", styles['Normal']))
            all_elements.append(Spacer(1, 0.05 * inch))

            # NID Front Side
            if nid_front_path and (nid_front_path.startswith("http") or (os.path.exists(nid_front_path) and self._is_safe_path(nid_front_path))):
                all_elements.append(Paragraph("<b>NID Front Side:</b>", ParagraphStyle('ImageTitle', parent=styles['Normal'], spaceAfter=0, leading=0)))
                scaled_image_path, img_width_points, img_height_points = self._scale_image(nid_front_path, usable_width, max_image_height_p2)
                if scaled_image_path:
                    img = Image(scaled_image_path, width=img_width_points, height=img_height_points, kind='proportional')
                    img.hAlign = 'CENTER' # Center the image horizontally
                    all_elements.append(img)
                else:
                    all_elements.append(Paragraph(f"<i>Could not load image from {nid_front_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>NID Front Side: Not provided or file not found/safe.</i>", styles['Normal']))
            all_elements.append(Spacer(1, 0.05 * inch)) # Small space between NID images

            # NID Back Side
            if nid_back_path and (nid_back_path.startswith("http") or (os.path.exists(nid_back_path) and self._is_safe_path(nid_back_path))):
                all_elements.append(Paragraph("<b>NID Back Side:</b>", ParagraphStyle('ImageTitle', parent=styles['Normal'], spaceAfter=0, leading=0)))
                scaled_image_path, img_width_points, img_height_points = self._scale_image(nid_back_path, usable_width, max_image_height_p2)
                if scaled_image_path:
                    img = Image(scaled_image_path, width=img_width_points, height=img_height_points, kind='proportional')
                    img.hAlign = 'CENTER' # Center the image horizontally
                    all_elements.append(img)
                else:
                    all_elements.append(Paragraph(f"<i>Could not load image from {nid_back_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>NID Back Side: Not provided or file not found/safe.</i>", styles['Normal']))
            all_elements.append(NextPageTemplate('Page3')) # Set template for the next page
            all_elements.append(PageBreak()) # Force a page break

            # --- Page 3: Police Verification Form ---
            all_elements.append(Paragraph("<b>Police Verification Form:</b>", styles['Normal']))
            all_elements.append(Spacer(1, 0.02 * inch))

            if police_form_path and (police_form_path.startswith("http") or (os.path.exists(police_form_path) and self._is_safe_path(police_form_path))):
                # Calculate max_width and max_height for the police form to fit frame3
                police_form_max_width = frame3.width # Use full frame width
                police_form_max_height = frame3_height - (1.0 * inch) # Account for some internal padding/spacing and title/spacer

                # Use _scale_image for police form as well
                scaled_image_path, img_width_points, img_height_points = self._scale_image(police_form_path, police_form_max_width, police_form_max_height)
                
                if scaled_image_path:
                    try:
                        img = Image(scaled_image_path, width=img_width_points, height=img_height_points) # No need for kind='proportional' if already scaled
                        img.hAlign = 'CENTER'
                        all_elements.append(img)
                    except Exception as img_e:
                        all_elements.append(Paragraph(f"<i>Error creating image object for police form: {img_e}</i>", styles['Normal']))
                else:
                    all_elements.append(Paragraph(f"<i>Could not load or scale police form image from {police_form_path}</i>", styles['Normal']))
            else:
                all_elements.append(Paragraph(f"<i>Police Verification Form: Not provided or file not found/safe.</i>", styles['Normal']))

            doc.build(all_elements)
            QMessageBox.information(self, "PDF Generated", f"Rental record PDF saved to:\n{pdf_path}")
            return pdf_path
        except Exception as e:
            QMessageBox.critical(self, "PDF Generation Error", f"Failed to generate PDF: {e}\n{traceback.format_exc()}")
            return None

    def _ensure_local_copy(self, path_str: str | None) -> str | None:
        """If *path_str* is an http/https URL, download it into IMAGE_STORAGE_DIR
        and return the local file path. Otherwise return *path_str* unchanged.
        """
        if not path_str or not path_str.lower().startswith("http"):
            return path_str  # Already local (or empty)

        try:
            # Ensure storage dir exists
            self.IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

            # Derive file extension from URL path or default to .img
            parsed = urllib.parse.urlparse(path_str)
            ext = Path(parsed.path).suffix or ".img"
            local_name = f"{uuid.uuid4()}{ext}"
            dest = self.IMAGE_STORAGE_DIR / local_name

            if not dest.exists():
                resp = requests.get(path_str, timeout=15, verify=False)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                print(f"Downloaded remote image to {dest}")
            return str(dest)
        except Exception as dl_exc:
            # If download fails keep original URL so record isn't lost
            print(f"Warning: could not cache remote image {path_str}: {dl_exc}")
            return path_str
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report for optimization analysis.
        
        Returns:
            Dictionary containing performance metrics, cache statistics, and recommendations
        """
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'tab_name': 'rental_info_tab',
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
            if self.rental_records_table:
                report['table_metrics'] = {
                    'row_count': self.rental_records_table.rowCount(),
                    'column_count': self.rental_records_table.columnCount(),
                    'viewport_width': self.rental_records_table.viewport().width(),
                    'table_width': self.rental_records_table.width(),
                    'is_visible': self.rental_records_table.isVisible()
                }
            
            # Generate recommendations based on performance data
            self._add_performance_recommendations(report)
            
            return report
            
        except Exception as e:
            return {
                'error': f'Failed to generate performance report: {e}',
                'timestamp': datetime.now().isoformat(),
                'tab_name': 'rental_info_tab'
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
            print("RENTAL TAB PERFORMANCE REPORT")
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