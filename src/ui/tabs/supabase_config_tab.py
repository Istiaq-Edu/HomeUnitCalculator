import sys
import logging
import re
import sqlite3 # Added import for sqlite3
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QApplication
)

# Assuming these modules are in the same directory or accessible in PYTHONPATH
from src.ui.styles import (
    get_header_style, get_group_box_style, get_line_edit_style,
    get_button_style
)
# Note: resource_path from utils might be needed if icons were used here, but they aren't in this tab.

class SupabaseConfigTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref # Reference to the main MeterCalculationApp instance

        # Initialize UI elements that will be created in init_ui
        self.supabase_url_input = None
        self.supabase_key_input = None
        self.toggle_url_visibility_button = None
        self.toggle_key_visibility_button = None
        self.save_supabase_config_button = None

        self.init_ui()

    def init_ui(self):
        # Original logic from MeterCalculationApp.create_supabase_config_tab
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        header_label = QLabel("Supabase Configuration")
        header_label.setStyleSheet(get_header_style())
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        config_group = QGroupBox("Supabase Credentials")
        config_group.setStyleSheet(get_group_box_style())
        config_layout = QFormLayout(config_group)
        config_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Supabase URL Input
        url_input_layout = QHBoxLayout()
        self.supabase_url_input = QLineEdit()
        self.supabase_url_input.setPlaceholderText("Enter your Supabase Project URL")
        self.supabase_url_input.setStyleSheet(get_line_edit_style())
        self.supabase_url_input.setToolTip("e.g., https://your-project-ref.supabase.co")
        self.supabase_url_input.setEchoMode(QLineEdit.Password) # Mask input
        url_input_layout.addWidget(self.supabase_url_input)

        self.toggle_url_visibility_button = QPushButton("Show")
        self.toggle_url_visibility_button.setCheckable(True)
        self.toggle_url_visibility_button.setFixedWidth(60)
        self.toggle_url_visibility_button.setStyleSheet("QPushButton { background-color: #555; color: white; border: none; border-radius: 4px; padding: 5px; } QPushButton:checked { background-color: #007bff; }")
        self.toggle_url_visibility_button.clicked.connect(lambda: self._toggle_password_visibility(self.supabase_url_input, self.toggle_url_visibility_button))
        url_input_layout.addWidget(self.toggle_url_visibility_button)
        config_layout.addRow("Supabase URL:", url_input_layout)

        # Supabase Key Input
        key_input_layout = QHBoxLayout()
        self.supabase_key_input = QLineEdit()
        self.supabase_key_input.setPlaceholderText("Enter your Supabase Anon Key")
        self.supabase_key_input.setStyleSheet(get_line_edit_style())
        self.supabase_key_input.setToolTip("e.g., eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        self.supabase_key_input.setEchoMode(QLineEdit.Password) # Mask input
        key_input_layout.addWidget(self.supabase_key_input)

        self.toggle_key_visibility_button = QPushButton("Show")
        self.toggle_key_visibility_button.setCheckable(True)
        self.toggle_key_visibility_button.setFixedWidth(60)
        self.toggle_key_visibility_button.setStyleSheet("QPushButton { background-color: #555; color: white; border: none; border-radius: 4px; padding: 5px; } QPushButton:checked { background-color: #007bff; }")
        self.toggle_key_visibility_button.clicked.connect(lambda: self._toggle_password_visibility(self.supabase_key_input, self.toggle_key_visibility_button))
        key_input_layout.addWidget(self.toggle_key_visibility_button)
        config_layout.addRow("Supabase Anon Key:", key_input_layout)

        layout.addWidget(config_group)

        self.save_supabase_config_button = QPushButton("Save Supabase Configuration")
        self.save_supabase_config_button.setStyleSheet(get_button_style())
        self.save_supabase_config_button.setFixedHeight(40)
        self.save_supabase_config_button.clicked.connect(self.save_supabase_config)
        layout.addWidget(self.save_supabase_config_button)

        layout.addStretch(1) # Push content to the top
        self.setLayout(layout)

        self._load_supabase_config_to_ui() # Load existing config on tab creation

    def _toggle_password_visibility(self, line_edit, button):
        """Toggles the echo mode of a QLineEdit between Normal and Password."""
        if button.isChecked():
            line_edit.setEchoMode(QLineEdit.Normal)
            button.setText("Hide")
        else:
            line_edit.setEchoMode(QLineEdit.Password)
            button.setText("Show")

    def _load_supabase_config_to_ui(self):
        """Loads existing Supabase config from DB and populates UI fields."""
        # Access db_manager via self.main_window
        config = self.main_window.db_manager.get_config()
        if config:
            self.supabase_url_input.setText(config.get("SUPABASE_URL", ""))
            self.supabase_key_input.setText(config.get("SUPABASE_KEY", ""))
            print("Loaded Supabase config into UI.")
        else:
            self.supabase_url_input.clear()
            self.supabase_key_input.clear()
            print("No Supabase config found in DB to load into UI.")

    def save_supabase_config(self):
        """Saves the Supabase URL and Key to the database."""
        from urllib.parse import urlparse

        url = self.supabase_url_input.text().strip()
        key = self.supabase_key_input.text().strip()

        if not url or not key:
            QMessageBox.warning(self, "Input Error", "Supabase URL and Key cannot be empty.")
            return

        parsed = urlparse(url)
        url_ok = parsed.scheme in {"http", "https"} and parsed.netloc
        key_ok = re.fullmatch(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$', key) is not None

        if not (url_ok and key_ok):
            QMessageBox.warning(
                self, "Input Error",
                "Please enter a valid Supabase URL (https://…) and a valid Anon key."
            )
            return

        try:
            # Access db_manager and _initialize_supabase_client via self.main_window
            self.main_window.db_manager.save_config(url, key)
            QMessageBox.information(self, "Success", "Supabase configuration saved and encrypted successfully!")
            self.main_window._initialize_supabase_client() # Re-initialize client with new config
        except sqlite3.Error as db_err:
            logging.exception("Database error while saving Supabase config")
            QMessageBox.critical(
                self,
                "Database Error",
                f"Could not persist Supabase config.\n{db_err}"
            )
        except (ValueError, TypeError) as e:
            logging.exception("Validation error while saving Supabase config")
            QMessageBox.critical(self, "Validation Error", f"Configuration validation failed: {e}")
        except Exception as e: # Catch-all for truly unexpected errors
            logging.exception("An unexpected error occurred while saving Supabase config")
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    # This part is for testing the SupabaseConfigTab independently if needed
    app = QApplication(sys.argv)
    
    # Dummy MainWindow reference for testing
    class DummyMainWindow(QWidget): # Or QMainWindow
        def __init__(self):
            super().__init__()
            # Mock db_manager and its methods
            class DummyDBManager:
                def get_config(self):
                    print("DummyDBManager.get_config called")
                    return {"SUPABASE_URL": "dummy_url", "SUPABASE_KEY": "dummy_key"}
                def save_config(self, url, key):
                    print(f"DummyDBManager.save_config called with URL: {url}, Key: {key}")
            
            self.db_manager = DummyDBManager()
            self._initialize_supabase_client = lambda: print("DummyMainWindow._initialize_supabase_client called")

    dummy_main_window = DummyMainWindow()
    
    config_tab_widget = SupabaseConfigTab(dummy_main_window)
    config_tab_widget.setWindowTitle("Supabase Config Tab Test")
    config_tab_widget.setGeometry(100, 100, 600, 400)
    config_tab_widget.show()
    
    sys.exit(app.exec_())
