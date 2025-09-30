import sys
import traceback

from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QIcon, QRegExpValidator, QPainter, QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFormLayout, QMessageBox, QSizePolicy, QFrame, QLineEdit
)
from PyQt5.QtCore import QTimer, QSize
from PyQt5.QtGui import QPalette
from qfluentwidgets import (
    CardWidget, SpinBox, PrimaryPushButton,
    TitleLabel, BodyLabel, CaptionLabel, FluentIcon, StrongBodyLabel
)

# Assuming these modules are in the same directory or accessible in PYTHONPATH
from src.core.utils import resource_path # For icons
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea
from src.ui.flow_layout import FlowLayout

# Local _clear_layout function to avoid circular dependency with utils
def _clear_layout(layout):
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                _clear_layout(item.layout())

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
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Room Selection Group (using CardWidget with object name to disable hover)
        room_selection_group = CardWidget()
        room_selection_group.setObjectName("room_selection_card")
        room_selection_layout = QFormLayout(room_selection_group)
        room_selection_layout.setSpacing(8)
        room_selection_layout.setContentsMargins(12, 12, 12, 12)


        num_rooms_label = BodyLabel("Number of Rooms:")
        num_rooms_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        self.num_rooms_spinbox = SpinBox()
        self.num_rooms_spinbox.setRange(1, 20) # Default range
        self.num_rooms_spinbox.setValue(11)    # Default value
        self.num_rooms_spinbox.valueChanged.connect(self.update_room_inputs)
        
        # Apply year spinbox configuration from home tab (complete)
        # Prevent focus state so underline color doesn't appear
        self.num_rooms_spinbox.setFocusPolicy(Qt.NoFocus)
        
        # Get line edit and configure it
        def configure_spinbox_editor():
            try:
                le = self.num_rooms_spinbox.lineEdit() if hasattr(self.num_rooms_spinbox, 'lineEdit') else None
                if le is None:
                    le = self.num_rooms_spinbox.findChild(QLineEdit)
                if le:
                    # Inner editor should not accept focus
                    le.setFocusPolicy(Qt.NoFocus)
                    # Make the value bold
                    f = le.font()
                    f.setBold(True)
                    le.setFont(f)
                    # Make selection invisible - use transparent color
                    try:
                        pal = le.palette()
                        pal.setColor(QPalette.Highlight, QColor(0, 0, 0, 0))  # Transparent
                        pal.setColor(QPalette.HighlightedText, pal.color(QPalette.Text))
                        le.setPalette(pal)
                    except Exception:
                        pass
                    # Clear selection initially and after interactions
                    def _clear_sel():
                        try:
                            le.deselect()
                            le.setCursorPosition(len(le.text()))
                        except Exception:
                            pass
                    _clear_sel()
                    # Connect to selection changed to auto-clear
                    try:
                        le.selectionChanged.connect(_clear_sel)
                    except Exception:
                        pass
                    # When value changes, clear selection/focus immediately after
                    try:
                        self.num_rooms_spinbox.valueChanged.connect(
                            lambda *_: QTimer.singleShot(0, lambda: (self.num_rooms_spinbox.clearFocus(), _clear_sel()))
                        )
                    except Exception:
                        pass
            except Exception:
                pass
        
        # Try immediately and defer if not ready
        configure_spinbox_editor()
        QTimer.singleShot(0, configure_spinbox_editor)
        QTimer.singleShot(100, configure_spinbox_editor)  # Extra fallback
        
        room_selection_layout.addRow(num_rooms_label, self.num_rooms_spinbox)
        layout.addWidget(room_selection_group)

        # Scroll Area for Room Inputs
        scroll_wrapper = QWidget()
        scroll_wrapper_layout = QVBoxLayout(scroll_wrapper)
        scroll_wrapper_layout.setContentsMargins(0,0,0,0)
        
        self.rooms_scroll_area = AutoScrollArea()
        self.rooms_scroll_area.setWidgetResizable(True)
        self.rooms_scroll_widget = QWidget()
        self.rooms_scroll_layout = FlowLayout(self.rooms_scroll_widget) # Use FlowLayout
        self.rooms_scroll_area.setWidget(self.rooms_scroll_widget)
        scroll_wrapper_layout.addWidget(self.rooms_scroll_area)
        layout.addWidget(scroll_wrapper)

        # Calculate Button with home tab styling
        self.calculate_rooms_button = PrimaryPushButton("Calculate Room Bills")
        self.calculate_rooms_button.clicked.connect(self.calculate_rooms)
        
        # Apply home tab configuration
        self.calculate_rooms_button.setIcon(FluentIcon.ACCEPT_MEDIUM.icon(color=QColor(255, 255, 255)))
        self.calculate_rooms_button.setIconSize(QSize(20, 20))
        self.calculate_rooms_button.setMinimumHeight(40)
        self.calculate_rooms_button.setFixedHeight(40)
        self.calculate_rooms_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Apply premium primary styling from home tab
        self.calculate_rooms_button.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #0078D4, stop:1 #005a9e);
                border: 2px solid #0078D4;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
                text-align: center;
                margin: 0px;
            }
            PrimaryPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #1084d8, stop:1 #106ebe);
                border-color: #1084d8;
            }
            PrimaryPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #005a9e, stop:1 #004578);
                border-color: #005a9e;
            }
        """)
        layout.addWidget(self.calculate_rooms_button)

        self.update_room_inputs() # Initial population of room inputs
        self.setLayout(layout)


    def update_room_inputs(self):
        _clear_layout(self.rooms_scroll_layout) # Use the copied/local _clear_layout

        num_rooms = self.num_rooms_spinbox.value()
        self.room_entries = []

        for i in range(num_rooms):
            room_group = CardWidget()
            room_group.setObjectName(f"room_{i}_card")  # Set object name to disable hover
            outer_layout = QVBoxLayout(room_group)
            outer_layout.setSpacing(12)
            outer_layout.setContentsMargins(16, 12, 16, 16)  # Reduced top padding
            
            title = TitleLabel(f"Room {i+1}")
            title.setStyleSheet("""
                font-size: 26px;
                font-weight: 800;
                color: #0078D4;
                letter-spacing: 0.5px;
                margin: 0px 0px;
            """)
            outer_layout.addWidget(title)
            
            # Horizontal line under the room title (blue like home tab)
            header_line = QFrame()
            header_line.setFrameShape(QFrame.HLine)
            header_line.setFrameShadow(QFrame.Plain)
            header_line.setStyleSheet("""
                color: #0078D4;
                background-color: #0078D4;
                border: none;
                height: 2px;
                margin: 4px 0px 8px 0px;
            """)
            outer_layout.addWidget(header_line)
            room_group.setMinimumWidth(295)  # Set to ensure 4 boxes per row with better space utilization
            room_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            # room_group border removed as per design feedback

            present_entry = CustomLineEdit()
            present_entry.setObjectName(f"room_{i}_present")
            present_entry.setPlaceholderText("0")
            
            previous_entry = CustomLineEdit()
            previous_entry.setObjectName(f"room_{i}_previous")
            previous_entry.setPlaceholderText("0")
            
            # Add numeric validators (only digits allowed)
            numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))
            present_entry.setValidator(numeric_validator)
            previous_entry.setValidator(numeric_validator)
            
            real_unit_label = CaptionLabel("N/A")
            real_unit_label.setStyleSheet("color:#4FC3F7;font-weight:bold;")
            real_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            unit_bill_label = CaptionLabel("N/A")
            unit_bill_label.setStyleSheet("color:#FFB74D;font-weight:bold;")
            unit_bill_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            gas_bill_entry = CustomLineEdit()
            gas_bill_entry.setObjectName(f"room_{i}_gas_bill")
            
            gas_bill_entry.setValidator(numeric_validator)

            water_bill_entry = CustomLineEdit()
            water_bill_entry.setObjectName(f"room_{i}_water_bill")
            
            water_bill_entry.setValidator(numeric_validator)

            house_rent_entry = CustomLineEdit()
            house_rent_entry.setObjectName(f"room_{i}_house_rent")
            
            house_rent_entry.setValidator(numeric_validator)

            grand_total_label = StrongBodyLabel("N/A")
            grand_total_label.setStyleSheet("color:#81C784;font-weight:bold;")
            grand_total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Create a horizontal layout for Present and Previous Unit fields side by side
            units_row_widget = QWidget()
            units_row_layout = QGridLayout(units_row_widget)
            units_row_layout.setContentsMargins(0, 0, 0, 0)
            units_row_layout.setSpacing(8)
            
            # Present Unit column
            present_label = BodyLabel("Present Unit")
            units_row_layout.addWidget(present_label, 0, 0)
            units_row_layout.addWidget(present_entry, 1, 0)
            
            # Previous Unit column
            previous_label = BodyLabel("Previous Unit")
            units_row_layout.addWidget(previous_label, 0, 1)
            units_row_layout.addWidget(previous_entry, 1, 1)
            
            outer_layout.addWidget(units_row_widget)
            
            # Gas Bill with label on top
            gas_bill_widget = QWidget()
            gas_bill_layout = QVBoxLayout(gas_bill_widget)
            gas_bill_layout.setContentsMargins(0, 0, 0, 0)
            gas_bill_layout.setSpacing(4)
            gas_bill_layout.addWidget(BodyLabel("Gas Bill"))
            gas_bill_layout.addWidget(gas_bill_entry)
            outer_layout.addWidget(gas_bill_widget)
            
            # Water Bill with label on top
            water_bill_widget = QWidget()
            water_bill_layout = QVBoxLayout(water_bill_widget)
            water_bill_layout.setContentsMargins(0, 0, 0, 0)
            water_bill_layout.setSpacing(4)
            water_bill_layout.addWidget(BodyLabel("Water Bill"))
            water_bill_layout.addWidget(water_bill_entry)
            outer_layout.addWidget(water_bill_widget)
            
            # House Rent with label on top
            house_rent_widget = QWidget()
            house_rent_layout = QVBoxLayout(house_rent_widget)
            house_rent_layout.setContentsMargins(0, 0, 0, 0)
            house_rent_layout.setSpacing(4)
            house_rent_layout.addWidget(BodyLabel("House Rent"))
            house_rent_layout.addWidget(house_rent_entry)
            outer_layout.addWidget(house_rent_widget)
            
            # Real Unit result with frosted container (horizontal layout)
            real_unit_container = QWidget()
            real_unit_container.setAttribute(Qt.WA_StyledBackground, True)
            real_unit_container.setAutoFillBackground(True)
            real_unit_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
            real_unit_container.setStyleSheet("""
                QWidget {
                    background-color: rgba(79, 195, 247, 0.14);
                    border: 1px solid rgba(79, 195, 247, 0.45);
                    border-radius: 6px;
                }
            """)
            real_unit_layout = QHBoxLayout(real_unit_container)
            real_unit_layout.setContentsMargins(12, 10, 12, 10)
            real_unit_layout.setSpacing(8)
            real_unit_title = BodyLabel("Real Unit")
            real_unit_title.setStyleSheet("color:#4FC3F7; font-weight:bold; background:transparent; border:none;")
            real_unit_layout.addWidget(real_unit_title)
            real_unit_layout.addStretch()
            real_unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            real_unit_label.setStyleSheet("color:#4FC3F7; font-weight:bold; background:transparent; border:none; font-size:14px;")
            real_unit_layout.addWidget(real_unit_label)
            outer_layout.addWidget(real_unit_container)
            
            # Unit Bill result with frosted container (horizontal layout)
            unit_bill_container = QWidget()
            unit_bill_container.setAttribute(Qt.WA_StyledBackground, True)
            unit_bill_container.setAutoFillBackground(True)
            unit_bill_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
            unit_bill_container.setStyleSheet("""
                QWidget {
                    background-color: rgba(255, 183, 77, 0.14);
                    border: 1px solid rgba(255, 183, 77, 0.45);
                    border-radius: 6px;
                }
            """)
            unit_bill_layout = QHBoxLayout(unit_bill_container)
            unit_bill_layout.setContentsMargins(12, 10, 12, 10)
            unit_bill_layout.setSpacing(8)
            unit_bill_title = BodyLabel("Unit Bill")
            unit_bill_title.setStyleSheet("color:#FFB74D; font-weight:bold; background:transparent; border:none;")
            unit_bill_layout.addWidget(unit_bill_title)
            unit_bill_layout.addStretch()
            unit_bill_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            unit_bill_label.setStyleSheet("color:#FFB74D; font-weight:bold; background:transparent; border:none; font-size:14px;")
            unit_bill_layout.addWidget(unit_bill_label)
            outer_layout.addWidget(unit_bill_container)
            
            # Grand Total result with frosted container (horizontal layout)
            grand_total_container = QWidget()
            grand_total_container.setAttribute(Qt.WA_StyledBackground, True)
            grand_total_container.setAutoFillBackground(True)
            grand_total_container.setGraphicsEffect(None)  # Remove shadow to avoid dotted edges
            grand_total_container.setStyleSheet("""
                QWidget {
                    background-color: rgba(129, 199, 132, 0.14);
                    border: 1px solid rgba(129, 199, 132, 0.45);
                    border-radius: 6px;
                }
            """)
            grand_total_layout = QHBoxLayout(grand_total_container)
            grand_total_layout.setContentsMargins(12, 10, 12, 10)
            grand_total_layout.setSpacing(8)
            grand_total_title = BodyLabel("Grand Total")
            grand_total_title.setStyleSheet("color:#81C784; font-weight:bold; background:transparent; border:none;")
            grand_total_layout.addWidget(grand_total_title)
            grand_total_layout.addStretch()
            grand_total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grand_total_label.setStyleSheet("color:#81C784; font-weight:bold; background:transparent; border:none; font-size:14px;")
            grand_total_layout.addWidget(grand_total_label)
            outer_layout.addWidget(grand_total_container)

            self.room_entries.append({
                'present_entry': present_entry,
                'previous_entry': previous_entry,
                'gas_bill_entry': gas_bill_entry,
                'water_bill_entry': water_bill_entry,
                'house_rent_entry': house_rent_entry,
                'real_unit_label': real_unit_label,
                'unit_bill_label': unit_bill_label,
                'grand_total_label': grand_total_label,
                'room_group': room_group # Store reference to the QGroupBox
            })
            
            # Add to grid layout
            self.rooms_scroll_layout.addWidget(room_group)
        
        # Re-configure navigation whenever room widgets change
        self.setup_navigation_rooms_tab()

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

                def _to_int_safe(txt: str):
                    if not txt or not txt.strip():
                        return 0
                    try:
                        return int(txt)
                    except ValueError:
                        try:
                            return int(float(txt))  # Handles '123.0'
                        except ValueError:
                            raise

                try:
                    present_unit = _to_int_safe(present_text)
                    previous_unit = _to_int_safe(previous_text)
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
                unit_bill_label.setText(f"{int(unit_bill + 0.5)} TK")
                grand_total_label.setText(f"{int(grand_total + 0.5)} TK")
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
            print(f"Warning: CSV row has data for room {room_index+1}, but only {len(self.room_entries)} rooms are displayed. Skipping.")
            return

        room_data = self.room_entries[room_index]

        def get_csv_value(row_dict, key_name, default_if_missing_or_empty):
            # This helper can be removed if it's centralized in the main tab
            for k_original, v_original in row_dict.items():
                if k_original.strip().lower() == key_name.strip().lower():
                    stripped_v = v_original.strip() if isinstance(v_original, str) else ""
                    # Replace "N/A" with "0"
                    if stripped_v.upper() == "N/A":
                        stripped_v = "0"
                    return stripped_v if stripped_v else default_if_missing_or_empty
            return default_if_missing_or_empty

        try:
            # Extract values from CSV row
            present_unit_csv = get_csv_value(row, "Present Unit", "0")
            previous_unit_csv = get_csv_value(row, "Previous Unit", "0")
            gas_bill_csv = get_csv_value(row, "Gas Bill", "0.00")
            water_bill_csv = get_csv_value(row, "Water Bill", "0.00")
            house_rent_csv = get_csv_value(row, "House Rent", "0.00")

            # Set text for input fields
            room_data['present_entry'].setText(present_unit_csv)
            room_data['previous_entry'].setText(previous_unit_csv)
            room_data['gas_bill_entry'].setText(gas_bill_csv)
            room_data['water_bill_entry'].setText(water_bill_csv)
            room_data['house_rent_entry'].setText(house_rent_csv)
            
        except Exception as e:
            QMessageBox.critical(self, "Load Room Data Error", f"Failed to load room data for room {room_index+1}: {e}\n{traceback.format_exc()}")

    def get_room_data_for_supabase(self):
        """
        Collects all room data from UI inputs and formats it for Supabase JSONB storage.
        Returns a list of dictionaries, each representing a room's data.
        """
        room_data_list: list[dict] = []
        errors: list[str] = []

        for i, room_data_entries in enumerate(self.room_entries):
            try:
                room_name = room_data_entries["room_group"].title()  # Group box title

                present_unit = int(room_data_entries["present_entry"].text() or "0")
                previous_unit = int(room_data_entries["previous_entry"].text() or "0")
                gas_bill = float(room_data_entries["gas_bill_entry"].text() or "0.0")
                water_bill = float(room_data_entries["water_bill_entry"].text() or "0.0")
                house_rent = float(room_data_entries["house_rent_entry"].text() or "0.0")

                # Calculated values
                real_unit_text = room_data_entries["real_unit_label"].text()
                unit_bill_text = room_data_entries["unit_bill_label"].text()
                grand_total_text = room_data_entries["grand_total_label"].text()

                real_unit = int(real_unit_text) if real_unit_text.isdigit() else 0
                unit_bill = (
                    float(unit_bill_text.replace(" TK", "").strip())
                    if unit_bill_text and unit_bill_text not in ["N/A", "Incomplete"]
                    else 0.0
                )
                grand_total = (
                    float(grand_total_text.replace(" TK", "").strip())
                    if grand_total_text and grand_total_text not in ["N/A", "Incomplete"]
                    else 0.0
                )

                room_data_jsonb = {
                    "room_name": room_name,
                    "present_unit": present_unit,
                    "previous_unit": previous_unit,
                    "real_unit": real_unit,
                    "unit_bill": unit_bill,
                    "gas_bill": gas_bill,
                    "water_bill": water_bill,
                    "house_rent": house_rent,
                    "grand_total": grand_total,
                }

                room_data_list.append(room_data_jsonb)
            except Exception as e:
                # Collect error but continue processing the remaining rooms.
                errors.append(f"Room {i+1}: {e}")

        # After processing all rooms, inform the user if any room failed.
        if errors:
            QMessageBox.warning(
                self,
                "Partial Data Collected",
                "Some rooms had errors and were skipped:\n\n" + "\n".join(errors),
            )

        return room_data_list

    def load_room_data_from_supabase_rows(self, room_records, auto_calculate=True):
        """
        Loads room data from Supabase records (list of dictionaries) into the UI.
        Each record is expected to have 'room_data' (JSONB) and potentially 'id' for updates.
        
        Args:
            room_records: List of room calculation records from Supabase
            auto_calculate: Whether to automatically calculate room bills after loading (default: True)
        """
        if not room_records:
            self.num_rooms_spinbox.setValue(1)
            self.clear_room_inputs()
            return

        # Adjust number of rooms in UI to match loaded data
        self.num_rooms_spinbox.setValue(len(room_records))
        # update_room_inputs will be triggered by valueChanged signal, clearing and recreating inputs

        for i, record in enumerate(room_records):
            if i >= len(self.room_entries):
                # This should ideally not happen if num_rooms_spinbox.setValue triggers update_room_inputs correctly
                # but as a safeguard, we can break or log.
                print(f"Warning: More room records from Supabase than UI inputs available. Skipping record {i}.")
                break

            room_data_jsonb = record.get("room_data", {})
            room_id = record.get("id") # Keep track of Supabase ID for updates

            room_ui_entries = self.room_entries[i]
            
            # Set room name (from group box title)
            room_group_widget = room_ui_entries['room_group']
            new_title = room_data_jsonb.get('room_name', f"Room {i+1}")
            if hasattr(room_group_widget, 'setTitle'):
                room_group_widget.setTitle(new_title)
            else:
                # CardWidget: first child in layout is the TitleLabel we added at creation
                title_label = room_group_widget.findChild(TitleLabel)
                if title_label:
                    title_label.setText(new_title)

            def _to_number_str_safe(val):
                """Return a clean string representation of a number (int if whole, float otherwise)."""
                if val == '' or val is None:
                    return ''
                try:
                    if isinstance(val, int):
                        return str(val)
                    elif isinstance(val, float):
                        # Show as integer if it's a whole number
                        if val.is_integer():
                            return str(int(val))
                        else:
                            # Remove trailing zeros for cleaner display
                            return f"{val:g}"
                    elif isinstance(val, str):
                        if val.isdigit():
                            return val
                        num = float(val)
                        if num.is_integer():
                            return str(int(num))
                        else:
                            return f"{num:g}"
                    else:
                        num = float(val)
                        if num.is_integer():
                            return str(int(num))
                        else:
                            return f"{num:g}"
                except (ValueError, TypeError):
                    return str(val)

            room_ui_entries['present_entry'].setText(_to_number_str_safe(room_data_jsonb.get('present_unit', '')))
            room_ui_entries['previous_entry'].setText(_to_number_str_safe(room_data_jsonb.get('previous_unit', '')))
            room_ui_entries['gas_bill_entry'].setText(_to_number_str_safe(room_data_jsonb.get('gas_bill', '')))
            room_ui_entries['water_bill_entry'].setText(_to_number_str_safe(room_data_jsonb.get('water_bill', '')))
            room_ui_entries['house_rent_entry'].setText(_to_number_str_safe(room_data_jsonb.get('house_rent', '')))
            
            # Store the Supabase ID with the UI entries for later updates
            room_ui_entries['supabase_id'] = room_id

            # Calculated fields are not set directly, they will be recalculated by calculate_rooms
            # after all data is loaded.
        
        # Only calculate rooms if auto_calculate is True (default behavior)
        if auto_calculate:
            self.calculate_rooms()

    def clear_room_inputs(self):
        """Clears all input fields and calculated labels in the rooms tab."""
        for room_data in self.room_entries:
            room_data['present_entry'].clear()
            room_data['previous_entry'].clear()
            room_data['gas_bill_entry'].clear()
            room_data['water_bill_entry'].clear()
            room_data['house_rent_entry'].clear()
            room_data['real_unit_label'].setText("N/A")
            room_data['unit_bill_label'].setText("N/A")
            room_data['grand_total_label'].setText("N/A")
            room_data['room_group'].setTitle(f"Room {self.room_entries.index(room_data)+1}") # Reset title
            if 'supabase_id' in room_data:
                del room_data['supabase_id'] # Remove Supabase ID if clearing

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

    def setup_navigation_rooms_tab(self):
        """Configure focus navigation (Enter / Up / Down) across all room input fields."""
        nav_sequence = []
        # Build sequence: present → previous → gas → water → house for each room in order
        for room in self.room_entries:
            nav_sequence.extend([
                room['present_entry'],
                room['previous_entry'],
                room['gas_bill_entry'],
                room['water_bill_entry'],
                room['house_rent_entry'],
            ])

        if not nav_sequence:
            return

        length = len(nav_sequence)
        for idx, widget in enumerate(nav_sequence):
            next_idx = (idx + 1) % length
            prev_idx = (idx - 1) % length

            widget.next_widget_on_enter = nav_sequence[next_idx]
            widget.down_widget = nav_sequence[next_idx]
            widget.up_widget = nav_sequence[prev_idx]

        # Focus first field if current focus not within rooms tab
        if self.focusWidget() not in nav_sequence:
            nav_sequence[0].setFocus()

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
