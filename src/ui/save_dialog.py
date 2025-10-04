"""
Modern file save dialog with purple theme matching the application design.
"""
import os
from pathlib import Path
from PyQt5.QtCore import Qt, QDir, QFileInfo, QSize
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTreeView, QFileSystemModel,
    QLineEdit, QPushButton, QComboBox, QMessageBox, QWidget
)
from qfluentwidgets import (
    LineEdit, PrimaryPushButton, PushButton, TitleLabel, FluentIcon,
    BodyLabel, ComboBox, TreeView, ScrollArea
)
from src.ui.responsive_components import ResponsiveDialog


class SaveDialog(ResponsiveDialog):
    """Modern file save dialog with purple theme."""
    
    def __init__(self, parent=None, title="Save File", default_filename="", file_filter="All Files (*)"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.selected_path = None
        self.default_filename = default_filename
        self.file_filter = file_filter
        self.current_dir = str(Path.home() / "Documents")
        
        # Parse file filter to get extensions
        self.extensions = self._parse_file_filter(file_filter)
        
        self.init_ui()
        
    def _parse_file_filter(self, filter_str):
        """Parse file filter string to extract extensions."""
        # Example: "PDF Files (*.pdf);;All Files (*)"
        extensions = []
        parts = filter_str.split(";;")
        for part in parts:
            if "(*." in part:
                ext = part.split("(*.")[1].split(")")[0]
                extensions.append(ext)
        return extensions if extensions else ["*"]
    
    def init_ui(self):
        """Initialize the UI with modern purple theme."""
        # Main container
        container = QWidget()
        container.setObjectName("dialogContainer")
        container.setStyleSheet("""
            QWidget#dialogContainer {
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
        
        # Custom title bar
        self._create_title_bar(container_layout)
        
        # Content area
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #2b2b2b; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.addWidget(content_widget)
        
        # Location bar
        self._create_location_bar(content_layout)
        
        # File browser
        self._create_file_browser(content_layout)
        
        # File name input
        self._create_filename_input(content_layout)
        
        # Buttons
        self._create_buttons(content_layout)
    
    def _create_title_bar(self, layout):
        """Create custom title bar."""
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: #1f1f1f;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(12, 0, 8, 0)
        title_bar_layout.setSpacing(8)
        
        # Icon - properly aligned
        icon_label = QLabel()
        icon_label.setPixmap(FluentIcon.SAVE.icon(color=QColor(108, 92, 231)).pixmap(20, 20))
        icon_label.setFixedSize(20, 20)
        icon_label.setAlignment(Qt.AlignCenter)
        title_bar_layout.addWidget(icon_label, 0, Qt.AlignVCenter)
        
        # Title
        title_text = QLabel(self.windowTitle())
        title_text.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px; background: transparent;")
        title_bar_layout.addWidget(title_text, 0, Qt.AlignVCenter)
        title_bar_layout.addStretch()
        
        # Close button - always red with centered X
        close_btn = QPushButton("×")
        close_btn.setFixedSize(40, 40)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #c42b1c;
                border: none;
                border-radius: 4px;
                color: #ffffff;
                font-size: 22px;
                font-weight: bold;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #d84315;
            }
            QPushButton:pressed {
                background-color: #a02315;
            }
        """)
        title_bar_layout.addWidget(close_btn, 0, Qt.AlignVCenter)
        
        # Make draggable
        title_bar.mousePressEvent = lambda e: setattr(self, '_drag_pos', e.globalPos() - self.frameGeometry().topLeft()) if e.button() == Qt.LeftButton else None
        title_bar.mouseMoveEvent = lambda e: self.move(e.globalPos() - self._drag_pos) if e.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos') else None
        
        layout.addWidget(title_bar)
    
    def _create_location_bar(self, layout):
        """Create location/path bar."""
        location_layout = QHBoxLayout()
        location_layout.setSpacing(8)
        location_layout.setAlignment(Qt.AlignVCenter)
        
        # Quick access buttons with proper icon size and alignment
        home_btn = PushButton()
        home_btn.setIcon(FluentIcon.HOME.icon(color=QColor(255, 255, 255)))
        home_btn.setIconSize(QSize(18, 18))
        home_btn.setFixedSize(44, 44)
        home_btn.setToolTip("Home")
        home_btn.clicked.connect(lambda: self._navigate_to(str(Path.home())))
        home_btn.setStyleSheet("""
            PushButton {
                background-color: #6C5CE7;
                border: none;
                border-radius: 8px;
                padding: 0px;
            }
            PushButton:hover {
                background-color: #7C6CF7;
            }
            PushButton:pressed {
                background-color: #5C4CD7;
            }
        """)
        location_layout.addWidget(home_btn, 0, Qt.AlignVCenter)
        
        docs_btn = PushButton()
        docs_btn.setIcon(FluentIcon.FOLDER.icon(color=QColor(255, 255, 255)))
        docs_btn.setIconSize(QSize(18, 18))
        docs_btn.setFixedSize(44, 44)
        docs_btn.setToolTip("Documents")
        docs_btn.clicked.connect(lambda: self._navigate_to(str(Path.home() / "Documents")))
        docs_btn.setStyleSheet("""
            PushButton {
                background-color: #6C5CE7;
                border: none;
                border-radius: 8px;
                padding: 0px;
            }
            PushButton:hover {
                background-color: #7C6CF7;
            }
            PushButton:pressed {
                background-color: #5C4CD7;
            }
        """)
        location_layout.addWidget(docs_btn, 0, Qt.AlignVCenter)
        
        desktop_btn = PushButton()
        # Try DESKTOP icon, fallback to FOLDER if not available
        try:
            desktop_btn.setIcon(FluentIcon.DESKTOP.icon(color=QColor(255, 255, 255)))
        except AttributeError:
            desktop_btn.setIcon(FluentIcon.FOLDER.icon(color=QColor(255, 255, 255)))
        desktop_btn.setIconSize(QSize(18, 18))
        desktop_btn.setFixedSize(44, 44)
        desktop_btn.setToolTip("Desktop")
        desktop_btn.clicked.connect(lambda: self._navigate_to(str(Path.home() / "Desktop")))
        desktop_btn.setStyleSheet("""
            PushButton {
                background-color: #6C5CE7;
                border: none;
                border-radius: 8px;
                padding: 0px;
            }
            PushButton:hover {
                background-color: #7C6CF7;
            }
            PushButton:pressed {
                background-color: #5C4CD7;
            }
        """)
        location_layout.addWidget(desktop_btn, 0, Qt.AlignVCenter)
        
        # Current path display
        self.path_label = BodyLabel()
        self.path_label.setText(self.current_dir)
        self.path_label.setStyleSheet("""
            color: #ffffff;
            background-color: rgba(61, 61, 61, 0.5);
            border: 1px solid #3d3d3d;
            border-radius: 6px;
            padding: 8px 12px;
        """)
        location_layout.addWidget(self.path_label, 1)
        
        layout.addLayout(location_layout)
        layout.addSpacing(10)
    
    def _create_file_browser(self, layout):
        """Create file/folder browser."""
        # File system model
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath("")
        self.fs_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        
        # Tree view
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.fs_model)
        
        # Set initial path safely
        docs_path = str(Path.home() / "Documents")
        if os.path.exists(docs_path):
            self.tree_view.setRootIndex(self.fs_model.index(docs_path))
            self.current_dir = docs_path
        else:
            home_path = str(Path.home())
            self.tree_view.setRootIndex(self.fs_model.index(home_path))
            self.current_dir = home_path
        
        self.tree_view.setColumnWidth(0, 400)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setMinimumHeight(300)
        
        # Hide size, type, date columns - only show name
        for i in range(1, 4):
            self.tree_view.hideColumn(i)
        
        # Style the tree view - remove scrollbar styling, let qfluentwidgets handle it
        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #1f1f1f;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                color: #ffffff;
                padding: 5px;
            }
            QTreeView::item {
                padding: 8px;
                border-radius: 4px;
            }
            QTreeView::item:hover {
                background-color: rgba(108, 92, 231, 0.2);
            }
            QTreeView::item:selected {
                background-color: #6C5CE7;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Connect selection
        self.tree_view.clicked.connect(self._on_folder_selected)
        
        # Wrap in ScrollArea for fluent scrollbars
        scroll_area = ScrollArea()
        scroll_area.setWidget(self.tree_view)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(350)
        scroll_area.setStyleSheet("""
            ScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
        
        layout.addWidget(scroll_area)
        layout.addSpacing(10)
    
    def _create_filename_input(self, layout):
        """Create filename input field."""
        filename_layout = QHBoxLayout()
        
        label = BodyLabel("File name:")
        label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filename_layout.addWidget(label)
        
        self.filename_input = LineEdit()
        self.filename_input.setText(self.default_filename)
        self.filename_input.setPlaceholderText("Enter filename...")
        self.filename_input.setMinimumHeight(40)
        self.filename_input.setStyleSheet("""
            LineEdit {
                background-color: #1f1f1f;
                border: 2px solid #6C5CE7;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 12px;
                font-size: 14px;
            }
            LineEdit:focus {
                border: 2px solid #7C6CF7;
                background-color: #2a2a2a;
            }
        """)
        filename_layout.addWidget(self.filename_input, 1)
        
        layout.addLayout(filename_layout)
        layout.addSpacing(10)
        
        # File type filter
        filter_layout = QHBoxLayout()
        
        filter_label = BodyLabel("Save as type:")
        filter_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        filter_layout.addWidget(filter_label)
        
        self.filter_combo = ComboBox()
        for part in self.file_filter.split(";;"):
            self.filter_combo.addItem(part.strip())
        self.filter_combo.setMinimumHeight(40)
        self.filter_combo.setStyleSheet("""
            ComboBox {
                background-color: #1f1f1f;
                border: 2px solid #6C5CE7;
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 12px;
                font-size: 14px;
            }
        """)
        filter_layout.addWidget(self.filter_combo, 1)
        
        layout.addLayout(filter_layout)
    
    def _create_buttons(self, layout):
        """Create action buttons."""
        layout.addSpacing(20)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = PushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setFixedWidth(100)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            PushButton {
                color: white;
                background-color: #757575;
                border: 1px solid #757575;
                border-radius: 6px;
                font-weight: bold;
            }
            PushButton:hover {
                background-color: #9e9e9e;
            }
            PushButton:pressed {
                background-color: #616161;
            }
        """)
        button_layout.addWidget(cancel_btn)
        
        # Save button
        save_btn = PrimaryPushButton("Save")
        save_btn.setFixedHeight(36)
        save_btn.setFixedWidth(100)
        save_btn.clicked.connect(self._on_save)
        save_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background-color: #6C5CE7;
                border: 1px solid #6C5CE7;
                border-radius: 6px;
                font-weight: bold;
            }
            PrimaryPushButton:hover {
                background-color: #7C6CF7;
            }
            PrimaryPushButton:pressed {
                background-color: #5C4CD7;
            }
        """)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _navigate_to(self, path):
        """Navigate to a specific path."""
        if os.path.exists(path):
            self.tree_view.setRootIndex(self.fs_model.index(path))
            self.path_label.setText(path)
            self.current_dir = path
    
    def _on_folder_selected(self, index):
        """Handle folder selection."""
        path = self.fs_model.filePath(index)
        if os.path.isdir(path):
            self.current_dir = path
            self.path_label.setText(path)
    
    def _on_save(self):
        """Handle save button click."""
        filename = self.filename_input.text().strip()
        
        if not filename:
            QMessageBox.warning(self, "Invalid Filename", "Please enter a filename.")
            return
        
        # Get current directory
        current_dir = getattr(self, 'current_dir', str(Path.home() / "Documents"))
        
        # Ensure extension
        if self.extensions and self.extensions[0] != "*":
            ext = self.extensions[0]
            if not filename.endswith(f".{ext}"):
                filename += f".{ext}"
        
        # Build full path
        self.selected_path = os.path.join(current_dir, filename)
        
        # Check if file exists
        if os.path.exists(self.selected_path):
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"The file '{filename}' already exists.\nDo you want to replace it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.accept()
    
    @staticmethod
    def get_save_filename(parent=None, title="Save File", default_filename="", file_filter="All Files (*)"):
        """
        Show modern file save dialog and return selected path.
        
        Returns:
            str: Selected file path, or None if cancelled
        """
        try:
            dialog = SaveDialog(parent, title, default_filename, file_filter)
            
            if dialog.exec_():
                return dialog.selected_path
            return None
        except Exception as e:
            print(f"Error in SaveDialog: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to standard dialog
            from PyQt5.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(parent, title, default_filename, file_filter)
            return file_path if file_path else None
