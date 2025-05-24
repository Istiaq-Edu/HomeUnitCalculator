import sys
import traceback

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QLabel, QGridLayout,
    QGroupBox, QFormLayout, QMessageBox, QSizePolicy
)

# Assuming these modules are in the same directory or accessible in PYTHONPATH
from styles import (
    get_room_selection_style, get_room_group_style, get_line_edit_style, 
    get_button_style
)
from utils import resource_path # For icons
from custom_widgets import CustomLineEdit, AutoScrollArea, CustomSpinBox, CustomNavButton

# --- Copied _clear_layout ---
# Ideally, this would be in utils.py, but due to tool issues, it's copied here.
def _clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                _clear_layout(item.layout()) # Recursively clear sub-layouts
# --- End of Copied _clear_layout ---

class RoomsTab(QWidget):
    def __init__(self, main_tab_ref, main_window_ref):
        super().__init__()
        self.main_tab = main_tab_ref # Reference to MainTab instance
        self.main_window = main_window_ref # Reference to the main MeterCalculationApp instance

        # Initialize attributes that will be created in init_ui
        self.num_rooms_spinbox = None
        self.rooms_scroll_area = None
        self.rooms_scroll_widget = None
        self.rooms_scroll_layout = None
        self.room_entries = []  # List of tuples: (present_entry, previous_entry)
        self.room_results = []  # List of tuples: (real_unit_label, unit_bill_label)
        self.calculate_rooms_button = None
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self) # Main layout for RoomsTab

        # Room Selection Group
        room_selection_group = QGroupBox("Room Selection")
        room_selection_group.setStyleSheet(get_room_selection_style())
        room_selection_layout = QFormLayout(room_selection_group)

        num_rooms_label = QLabel("Number of Rooms:")
        self.num_rooms_spinbox = CustomSpinBox()
        self.num_rooms_spinbox.setRange(1, 20) # Default range
        self.num_rooms_spinbox.setValue(11)    # Default value
        self.num_rooms_spinbox.valueChanged.connect(self.update_room_inputs)
        room_selection_layout.addRow(num_rooms_label, self.num_rooms_spinbox)
        layout.addWidget(room_selection_group)

        # Scroll Area for Room Inputs
        scroll_wrapper = QWidget()
        scroll_wrapper_layout = QVBoxLayout(scroll_wrapper)
        scroll_wrapper_layout.setContentsMargins(0,0,0,0)
        
        self.rooms_scroll_area = AutoScrollArea()
        self.rooms_scroll_area.setWidgetResizable(True)
        self.rooms_scroll_widget = QWidget()
        self.rooms_scroll_layout = QGridLayout(self.rooms_scroll_widget) # Use QGridLayout
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget)
        scroll_wrapper_layout.addWidget(self.rooms_scroll_area)
        layout.addWidget(scroll_wrapper)

        # Calculate Button
        self.calculate_rooms_button = CustomNavButton("Calculate Room Bills")
        self.calculate_rooms_button.setIcon(QIcon(resource_path("icons/calculate_icon.png")))
        self.calculate_rooms_button.clicked.connect(self.calculate_rooms)
        self.calculate_rooms_button.setStyleSheet(get_button_style())
        layout.addWidget(self.calculate_rooms_button)

        self.update_room_inputs() # Initial population of room inputs
        self.setLayout(layout)


    def update_room_inputs(self):
        _clear_layout(self.rooms_scroll_layout) # Use the copied/local _clear_layout

        num_rooms = self.num_rooms_spinbox.value()
        self.room_entries = []
        self.room_results = []

        for i in range(num_rooms):
            room_group = QGroupBox(f"Room {i+1}")
            room_layout = QFormLayout(room_group)
            room_group.setStyleSheet(get_room_group_style())
            room_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            present_entry = CustomLineEdit()
            present_entry.setObjectName(f"room_{i}_present")
            present_entry.setPlaceholderText("Enter present reading")
            
            previous_entry = CustomLineEdit()
            previous_entry.setObjectName(f"room_{i}_previous")
            previous_entry.setPlaceholderText("Enter previous reading")
            
            # Add numeric validators (only digits allowed)
            numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))
            present_entry.setValidator(numeric_validator)
            previous_entry.setValidator(numeric_validator)
            
            real_unit_label = QLabel("N/A")
            unit_bill_label = QLabel("N/A")

            present_entry.setStyleSheet(get_line_edit_style())
            previous_entry.setStyleSheet(get_line_edit_style())

            room_layout.addRow("Present Unit:", present_entry)
            room_layout.addRow("Previous Unit:", previous_entry)
            room_layout.addRow("Real Unit:", real_unit_label)
            room_layout.addRow("Unit Bill:", unit_bill_label)

            self.room_entries.append((present_entry, previous_entry))
            self.room_results.append((real_unit_label, unit_bill_label))
            
            # Add to grid layout
            row, col = divmod(i, 3) # Arrange in 3 columns
            self.rooms_scroll_layout.addWidget(room_group, row, col)

        if self.rooms_scroll_layout.columnCount() > 0:
            for col in range(self.rooms_scroll_layout.columnCount()):
                 self.rooms_scroll_layout.setColumnStretch(col, 1)
        
        # These calls are redundant – the layout and scroll widget were
        # attached during initialisation (lines 75-76).
        
        # Setup navigation for room entries (simplified from original for brevity)
        # This would typically call self.main_window.setup_navigation() if it handles cross-tab nav,
        # or a more localized navigation setup if only within this tab.
        if hasattr(self.main_window, 'setup_navigation') and callable(self.main_window.setup_navigation):
            self.main_window.setup_navigation()


    def calculate_rooms(self):
        try:
            per_unit_cost_text = self.main_tab.per_unit_cost_value_label.text().strip()
            
            value_to_process = ""
            if ':' in per_unit_cost_text: # Example: "Per Unit Cost: 10.00 TK"
                parts = per_unit_cost_text.split(':', 1)
                if len(parts) > 1: value_to_process = parts[1].strip()
                else: raise ValueError(f"Per unit cost value is missing after colon: '{per_unit_cost_text}'")
            else: # Example: "10.00 TK" or "10.00"
                value_to_process = per_unit_cost_text

            if not value_to_process:
                raise ValueError(f"Per unit cost value is empty. Original: '{per_unit_cost_text}'")

            cleaned_value_text = value_to_process.lower().replace("tk", "").strip()
            if not cleaned_value_text:
                raise ValueError(f"Per unit cost value is non-numeric after cleaning. Original: '{per_unit_cost_text}'")
            
            per_unit_cost = float(cleaned_value_text)

            for i, ((present_entry, previous_entry), (real_unit_label, unit_bill_label)) in enumerate(zip(self.room_entries, self.room_results)):
                present_text = present_entry.text().strip()
                previous_text = previous_entry.text().strip()

                if present_text and previous_text:
                    try:
                        present_unit = int(present_text)
                        previous_unit = int(previous_text)
                    except ValueError:
                        raise ValueError(f"Non-numeric input in Room {i+1}. Present: '{present_text}', Previous: '{previous_text}'")

                    if present_unit < 0 or previous_unit < 0:
                        raise ValueError(f"Negative readings not allowed in Room {i+1}. Present: {present_unit}, Previous: {previous_unit}")
                    
                    if present_unit < previous_unit:
                        raise ValueError(f"Present reading cannot be less than previous reading in Room {i+1}. Present: {present_unit}, Previous: {previous_unit}")

                    real_unit = present_unit - previous_unit
                    unit_bill = round(real_unit * per_unit_cost, 2)

                    real_unit_label.setText(f"{real_unit}")
                    unit_bill_label.setText(f"{unit_bill:.2f} TK")
                else:
                    real_unit_label.setText("Incomplete")
                    unit_bill_label.setText("Incomplete")
        except ValueError as ve:
            QMessageBox.warning(self, "Calculation Error", f"Error in room calculation: {ve}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred during room calculation: {e}\n{traceback.format_exc()}")

if __name__ == '__main__':
    # This part is for testing the RoomsTab independently if needed
    app = QApplication(sys.argv)

    # Dummy MainTab reference for testing
    class DummyMainTab(QWidget):
        def __init__(self):
            super().__init__()
            self.per_unit_cost_value_label = QLabel("10.00 TK") # Example value

    # Dummy MainWindow reference for testing
    class DummyMainWindow(QWidget): # Or QMainWindow
        def __init__(self):
            super().__init__()
            # Mock setup_navigation if RoomsTab's update_room_inputs calls it
            self.setup_navigation = lambda: print("DummyMainWindow.setup_navigation called from RoomsTab")

    dummy_main_tab = DummyMainTab()
    dummy_main_window = DummyMainWindow()
    
    rooms_tab_widget = RoomsTab(dummy_main_tab, dummy_main_window)
    rooms_tab_widget.setWindowTitle("RoomsTab Test")
    rooms_tab_widget.setGeometry(100, 100, 800, 600)
    rooms_tab_widget.show()
    
    sys.exit(app.exec_())
