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
from src.ui.styles import (
    get_room_selection_style, get_room_group_style, get_line_edit_style,
    get_button_style
)
from src.core.utils import resource_path, _clear_layout # For icons and layout clearing
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomSpinBox, CustomNavButton

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
        self.room_entries = []  # List of dictionaries for all room-related entries and results
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

            gas_bill_entry = CustomLineEdit()
            gas_bill_entry.setObjectName(f"room_{i}_gas_bill")
            gas_bill_entry.setPlaceholderText("Enter Gas Bill")
            gas_bill_entry.setValidator(numeric_validator)
            gas_bill_entry.setStyleSheet(get_line_edit_style())

            water_bill_entry = CustomLineEdit()
            water_bill_entry.setObjectName(f"room_{i}_water_bill")
            water_bill_entry.setPlaceholderText("Enter Water Bill")
            water_bill_entry.setValidator(numeric_validator)
            water_bill_entry.setStyleSheet(get_line_edit_style())

            house_rent_entry = CustomLineEdit()
            house_rent_entry.setObjectName(f"room_{i}_house_rent")
            house_rent_entry.setPlaceholderText("Enter House Rent")
            house_rent_entry.setValidator(numeric_validator)
            house_rent_entry.setStyleSheet(get_line_edit_style())

            grand_total_label = QLabel("N/A")
            grand_total_label.setStyleSheet("font-weight: bold;") # Bold style for grand total

            room_layout.addRow("Present Unit:", present_entry)
            room_layout.addRow("Previous Unit:", previous_entry)
            room_layout.addRow("Gas Bill:", gas_bill_entry)
            room_layout.addRow("Water Bill:", water_bill_entry)
            room_layout.addRow("House Rent:", house_rent_entry)
            room_layout.addRow("Real Unit:", real_unit_label)
            room_layout.addRow("Unit Bill:", unit_bill_label)
            room_layout.addRow("Grand Total:", grand_total_label)

            self.room_entries.append({
                'present_entry': present_entry,
                'previous_entry': previous_entry,
                'gas_bill_entry': gas_bill_entry,
                'water_bill_entry': water_bill_entry,
                'house_rent_entry': house_rent_entry,
                'real_unit_label': real_unit_label,
                'unit_bill_label': unit_bill_label,
                'grand_total_label': grand_total_label
            })
            
            # Add to grid layout
            row, col = divmod(i, 3) # Arrange in 3 columns
            self.rooms_scroll_layout.addWidget(room_group, row, col)

        # Ensure columns are stretched correctly for the QGridLayout
        # QGridLayout.columnCount() always returns 0 in PyQt5, so manually set stretch for 3 columns
        for col in range(3):
            self.rooms_scroll_layout.setColumnStretch(col, 1)
        
        # The layout and scroll widget were attached during initialisation (lines 60-61).
        # Navigation setup will be handled by main window after all tabs are created.


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

            for i, room_data in enumerate(self.room_entries):
                present_text = room_data['present_entry'].text().strip()
                previous_text = room_data['previous_entry'].text().strip()
                gas_bill_text = room_data['gas_bill_entry'].text().strip()
                water_bill_text = room_data['water_bill_entry'].text().strip()
                house_rent_text = room_data['house_rent_entry'].text().strip()

                real_unit_label = room_data['real_unit_label']
                unit_bill_label = room_data['unit_bill_label']
                grand_total_label = room_data['grand_total_label']

                if present_text and previous_text:
                    try:
                        present_unit = int(present_text)
                        previous_unit = int(previous_text)
                    except ValueError:
                        raise ValueError(
                            f"Non-numeric input in Room {i+1}. "
                            f"Present: '{present_text}', Previous: '{previous_text}'"
                        )

                    if present_unit < 0 or previous_unit < 0:
                        raise ValueError(f"Negative readings not allowed in Room {i+1}. Present: {present_unit}, Previous: {previous_unit}")
                    
                    if present_unit < previous_unit:
                        raise ValueError(f"Present reading cannot be less than previous reading in Room {i+1}. Present: {present_unit}, Previous: {previous_unit}")

                    real_unit = present_unit - previous_unit
                    unit_bill = round(real_unit * per_unit_cost, 2)

                    def _to_amount(txt, field_name):
                        if not txt:
                            return 0.0
                        try:
                            value = float(txt)
                        except ValueError:
                            raise ValueError(f"{field_name} must be a number in Room {i+1}: '{txt}'") from None
                        if value < 0:
                            raise ValueError(f"{field_name} cannot be negative in Room {i+1}: {value}")
                        return value

                    gas_bill   = _to_amount(gas_bill_text,   "Gas Bill")
                    water_bill = _to_amount(water_bill_text, "Water Bill")
                    house_rent = _to_amount(house_rent_text, "House Rent")

                    grand_total = unit_bill + gas_bill + water_bill + house_rent

                    real_unit_label.setText(f"{real_unit}")
                    unit_bill_label.setText(f"{unit_bill:.2f} TK")
                    grand_total_label.setText(f"{grand_total:.2f} TK")
                else:
                    real_unit_label.setText("Incomplete")
                    unit_bill_label.setText("Incomplete")
                    grand_total_label.setText("Incomplete")
        except ValueError as ve:
            QMessageBox.warning(self, "Calculation Error", f"Error in room calculation: {ve}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred during room calculation: {e}\n{traceback.format_exc()}")

    def load_room_data_from_csv_row(self, row, room_index):
        """
        Loads room-specific data from a CSV row (dictionary) into the corresponding room inputs.
        Assumes the row dictionary contains keys like 'Room Name', 'Present Unit', etc.
        """
        if room_index >= len(self.room_entries):
            # This can happen if the CSV has more rooms than currently displayed in UI
            # For now, we'll just log and skip, or could dynamically add rooms if needed.
            print(f"Warning: CSV row has data for room {room_index+1}, but only {len(self.room_entries)} rooms are displayed. Skipping.")
            return

        room_data = self.room_entries[room_index]

        def get_csv_value(row_dict, key_name, default_if_missing_or_empty):
            for k_original, v_original in row_dict.items():
                if k_original.strip().lower() == key_name.strip().lower():
                    stripped_v = v_original.strip() if isinstance(v_original, str) else ""
                    return stripped_v if stripped_v else default_if_missing_or_empty
            return default_if_missing_or_empty

        try:
            # Extract values from CSV row
            present_unit_csv = get_csv_value(row, "Present Unit", "0")
            previous_unit_csv = get_csv_value(row, "Previous Unit", "0")
            gas_bill_csv = get_csv_value(row, "Gas Bill", "0.00")
            water_bill_csv = get_csv_value(row, "Water Bill", "0.00")
            house_rent_csv = get_csv_value(row, "House Rent", "0.00")
            
            # Note: Real Unit, Unit Bill, Grand Total are calculated, not directly loaded
            # from CSV for input fields, but we can set their labels if needed for display.
            # However, the calculate_rooms method will re-calculate them.
            # So, we only load the input fields.

            # Set text for input fields
            room_data['present_entry'].setText(present_unit_csv)
            room_data['previous_entry'].setText(previous_unit_csv)
            room_data['gas_bill_entry'].setText(gas_bill_csv)
            room_data['water_bill_entry'].setText(water_bill_csv)
            room_data['house_rent_entry'].setText(house_rent_csv)

            # After loading, trigger calculation for this room or all rooms
            # It's safer to trigger calculate_rooms() for all rooms after all data is loaded
            # in the main_tab.py, to ensure per_unit_cost is correctly set.
            
        except Exception as e:
            QMessageBox.critical(self, "Load Room Data Error", f"Failed to load room data for room {room_index+1}: {e}\n{traceback.format_exc()}")

    def get_all_room_bill_totals(self):
        """
        Calculates and returns the total House Rent, Water Bill, Gas Bill, and Room Unit Bill
        across all rooms.
        """
        total_house_rent = 0.0
        total_water_bill = 0.0
        total_gas_bill = 0.0
        total_room_unit_bill = 0.0

        for room_data in self.room_entries:
            try:
                # Safely get values, defaulting to 0.0 if "N/A" or empty
                house_rent = float(room_data['house_rent_entry'].text() or '0.0')
                water_bill = float(room_data['water_bill_entry'].text() or '0.0')
                gas_bill = float(room_data['gas_bill_entry'].text() or '0.0')
                
                # Unit Bill might be "Incomplete" or "N/A", handle it
                unit_bill_text = room_data['unit_bill_label'].text()
                if unit_bill_text and unit_bill_text not in ["N/A", "Incomplete"]:
                    unit_bill = float(unit_bill_text.replace(" TK", "").strip())
                else:
                    unit_bill = 0.0

                total_house_rent += house_rent
                total_water_bill += water_bill
                total_gas_bill += gas_bill
                total_room_unit_bill += unit_bill
            except ValueError as ve:
                print(f"Warning: Could not convert room bill value to float. Skipping this room's contribution. Error: {ve}")
            except Exception as e:
                print(f"An unexpected error occurred while summing room bills: {e}")

        return {
            "total_house_rent": total_house_rent,
            "total_water_bill": total_water_bill,
            "total_gas_bill": total_gas_bill,
            "total_room_unit_bill": total_room_unit_bill
        }

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
