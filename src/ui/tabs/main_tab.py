import sys
import json
import os
import csv
import traceback
from datetime import datetime

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QMessageBox, QSpinBox, QComboBox, QSizePolicy,
    QGridLayout # Added QGridLayout
)
from postgrest.exceptions import APIError

from src.ui.styles import (
    get_group_box_style, get_line_edit_style, get_button_style,
    get_month_info_style, get_label_style, get_result_title_style,
    get_result_value_style
)
from src.core.utils import resource_path
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomSpinBox, CustomNavButton

class MainTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref 

        self.month_combo = None
        self.year_spinbox = None
        self.meter_entries = []
        self.diff_entries = []
        self.additional_amount_input = None
        self.total_unit_value_label = None
        self.total_diff_value_label = None
        self.per_unit_cost_value_label = None
        self.additional_amount_value_label = None
        self.in_total_value_label = None
        self.main_calculate_button = None
        self.save_to_cloud_button = None # New button for saving to cloud
        
        self.load_month_combo = None
        self.load_year_spinbox = None
        
        self.meter_layout = None 
        self.diff_layout = None  
        self.meter_count_spinbox = None
        self.diff_count_spinbox = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self) 
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        new_top_row_layout = QHBoxLayout()
        new_top_row_layout.setSpacing(20) 

        date_selection_group = QGroupBox("Date Selection") 
        date_selection_group.setStyleSheet(get_group_box_style())
        date_selection_filter_layout = QHBoxLayout() 
        date_selection_group.setLayout(date_selection_filter_layout)

        month_label = QLabel("Month:")
        month_label.setStyleSheet(get_label_style())
        self.month_combo = QComboBox() 
        self.month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.month_combo.setStyleSheet(get_month_info_style())

        year_label = QLabel("Year:")
        year_label.setStyleSheet(get_label_style())
        self.year_spinbox = QSpinBox()
        self.year_spinbox.setRange(2000, 2100)
        self.year_spinbox.setValue(datetime.now().year)
        self.year_spinbox.setStyleSheet(get_month_info_style())

        date_selection_filter_layout.addWidget(month_label)
        date_selection_filter_layout.addWidget(self.month_combo)
        date_selection_filter_layout.addSpacing(20)
        date_selection_filter_layout.addWidget(year_label)
        date_selection_filter_layout.addWidget(self.year_spinbox)
        date_selection_filter_layout.addStretch(1)
        new_top_row_layout.addWidget(date_selection_group, 1) 

        moved_load_options_group = QGroupBox("Load Data Options")
        moved_load_options_group.setStyleSheet(get_group_box_style())
        moved_load_options_internal_layout = QVBoxLayout()
        moved_load_options_group.setLayout(moved_load_options_internal_layout)

        load_info_group = self.create_load_info_group() 
        moved_load_options_internal_layout.addWidget(load_info_group)

        source_info_layout = QHBoxLayout()
        source_info_label = QLabel("Source for 'Load' Button:")
        source_info_label.setStyleSheet(get_label_style())
        source_info_layout.addWidget(source_info_label)
        source_info_layout.addWidget(self.main_window.load_info_source_combo) 
        source_info_layout.addStretch(1) 
        moved_load_options_internal_layout.addLayout(source_info_layout)
        new_top_row_layout.addWidget(moved_load_options_group, 1) 
        main_layout.addLayout(new_top_row_layout)

        middle_row_layout = QHBoxLayout()
        meter_group = QGroupBox("Meter Readings")
        meter_group.setStyleSheet(get_group_box_style())
        meter_scroll = AutoScrollArea()
        meter_scroll.setWidgetResizable(True)
        meter_container = QWidget()
        self.meter_layout = QFormLayout(meter_container)
        self.meter_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        meter_scroll.setWidget(meter_container)
        meter_group_layout = QVBoxLayout(meter_group)
        meter_group_layout.addWidget(meter_scroll)
        middle_row_layout.addWidget(meter_group, 1)
        
        diff_group = QGroupBox("Difference Readings")
        diff_group.setStyleSheet(get_group_box_style())
        diff_scroll = AutoScrollArea()
        diff_scroll.setWidgetResizable(True)
        diff_container = QWidget()
        self.diff_layout = QFormLayout(diff_container)
        self.diff_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        diff_scroll.setWidget(diff_container)
        diff_group_layout = QVBoxLayout(diff_group)
        diff_group_layout.addWidget(diff_scroll)
        middle_row_layout.addWidget(diff_group, 1)
        
        right_column_layout = QVBoxLayout()
        spinboxes_layout = QHBoxLayout()
        
        meter_count_group = QGroupBox("Number of Meters:")
        meter_count_group.setStyleSheet(get_group_box_style())
        meter_count_layout = QHBoxLayout(meter_count_group)
        meter_count_layout.setContentsMargins(5, 5, 5, 5)
        meter_count_layout.setSpacing(2)
        self.meter_count_spinbox = CustomSpinBox()
        self.meter_count_spinbox.setRange(1, 10)
        self.meter_count_spinbox.setValue(3)
        self.meter_count_spinbox.valueChanged.connect(self.update_meter_inputs)
        meter_count_layout.addWidget(self.meter_count_spinbox)
        spinboxes_layout.addWidget(meter_count_group)
        
        diff_count_group = QGroupBox("Number of Diffs:")
        diff_count_group.setStyleSheet(get_group_box_style())
        diff_count_layout = QHBoxLayout(diff_count_group)
        diff_count_layout.setContentsMargins(5, 5, 5, 5)
        diff_count_layout.setSpacing(2)
        self.diff_count_spinbox = CustomSpinBox()
        self.diff_count_spinbox.setRange(1, 10)
        self.diff_count_spinbox.setValue(3)
        self.diff_count_spinbox.valueChanged.connect(self.update_diff_inputs)
        diff_count_layout.addWidget(self.diff_count_spinbox)
        spinboxes_layout.addWidget(diff_count_group)
        
        spinboxes_layout.setSpacing(5)
        right_column_layout.addLayout(spinboxes_layout)
        
        amount_group = self.create_additional_amount_group()
        right_column_layout.addWidget(amount_group)
        middle_row_layout.addLayout(right_column_layout, 1)
        main_layout.addLayout(middle_row_layout)

        results_group = self.create_results_group()
        main_layout.addWidget(results_group)

        button_layout = QHBoxLayout()
        self.main_calculate_button = CustomNavButton("Calculate")
        self.main_calculate_button.setIcon(QIcon(resource_path("icons/calculate_icon.png")))
        self.main_calculate_button.clicked.connect(self.calculate_main)
        self.main_calculate_button.setStyleSheet(get_button_style())
        self.main_calculate_button.setFixedHeight(50)
        button_layout.addWidget(self.main_calculate_button)
        main_layout.addLayout(button_layout)
        
        self.update_meter_inputs(3)
        self.update_diff_inputs(3)
        
        self.setLayout(main_layout)

    def create_additional_amount_group(self):
        amount_group = QGroupBox("Additional Amount")
        amount_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        amount_group.setStyleSheet(get_group_box_style())
        amount_layout = QHBoxLayout()
        amount_group.setLayout(amount_layout)

        amount_label = QLabel("Additional Amount:")
        amount_label.setStyleSheet(get_label_style())
        self.additional_amount_input = CustomLineEdit()
        self.additional_amount_input.setObjectName("main_additional_amount_input")
        self.additional_amount_input.setPlaceholderText("Enter additional amount")
        self.additional_amount_input.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))
        self.additional_amount_input.setStyleSheet(get_line_edit_style())
        
        currency_label = QLabel("TK")
        currency_label.setStyleSheet(get_label_style())

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.additional_amount_input, 1)
        input_layout.addWidget(currency_label)
        input_layout.setSpacing(5)

        amount_layout.addWidget(amount_label)
        amount_layout.addLayout(input_layout, 1)
        amount_group.setToolTip("Enter any additional amount to be added to the total bill")
        return amount_group

    def get_additional_amount(self):
        try:
            return float(self.additional_amount_input.text()) if self.additional_amount_input.text() else 0.0
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric value for the additional amount.")
            return 0.0

    def create_results_group(self):
        results_group = QGroupBox("Results")
        results_group.setStyleSheet(get_group_box_style())
        results_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        results_layout = QHBoxLayout(results_group)
        results_layout.setSpacing(20)
        results_layout.setContentsMargins(15, 25, 15, 15)

        total_unit_layout = QVBoxLayout()
        total_unit_layout.setSpacing(2)
        total_unit_title_label = QLabel("Total Units")
        total_unit_title_label.setStyleSheet(get_result_title_style())
        self.total_unit_value_label = QLabel("0")
        self.total_unit_value_label.setStyleSheet(get_result_value_style())
        total_unit_layout.addWidget(total_unit_title_label)
        total_unit_layout.addWidget(self.total_unit_value_label)
        total_unit_layout.addStretch(1)
        results_layout.addLayout(total_unit_layout, 1)

        total_diff_layout = QVBoxLayout()
        total_diff_layout.setSpacing(2)
        total_diff_title_label = QLabel("Total Difference")
        total_diff_title_label.setStyleSheet(get_result_title_style())
        self.total_diff_value_label = QLabel("0")
        self.total_diff_value_label.setStyleSheet(get_result_value_style())
        total_diff_layout.addWidget(total_diff_title_label)
        total_diff_layout.addWidget(self.total_diff_value_label)
        total_diff_layout.addStretch(1)
        results_layout.addLayout(total_diff_layout, 1)

        per_unit_cost_layout = QVBoxLayout()
        per_unit_cost_layout.setSpacing(2)
        per_unit_cost_title_label = QLabel("Per Unit Cost")
        per_unit_cost_title_label.setStyleSheet(get_result_title_style())
        self.per_unit_cost_value_label = QLabel("0.00")
        self.per_unit_cost_value_label.setStyleSheet(get_result_value_style())
        per_unit_cost_layout.addWidget(per_unit_cost_title_label)
        per_unit_cost_layout.addWidget(self.per_unit_cost_value_label)
        per_unit_cost_layout.addStretch(1)
        results_layout.addLayout(per_unit_cost_layout, 1)

        added_amount_layout = QVBoxLayout()
        added_amount_layout.setSpacing(2)
        added_amount_title_label = QLabel("Added Amount")
        added_amount_title_label.setStyleSheet(get_result_title_style())
        self.additional_amount_value_label = QLabel("0")
        self.additional_amount_value_label.setStyleSheet(get_result_value_style())
        added_amount_layout.addWidget(added_amount_title_label)
        added_amount_layout.addWidget(self.additional_amount_value_label)
        added_amount_layout.addStretch(1)
        results_layout.addLayout(added_amount_layout, 1)

        in_total_layout = QVBoxLayout()
        in_total_layout.setSpacing(2)
        in_total_title_label = QLabel("In Total")
        in_total_title_label.setStyleSheet(get_result_title_style())
        self.in_total_value_label = QLabel("0.00")
        self.in_total_value_label.setStyleSheet(get_result_value_style())
        in_total_layout.addWidget(in_total_title_label)
        in_total_layout.addWidget(self.in_total_value_label)
        in_total_layout.addStretch(1)
        results_layout.addLayout(in_total_layout, 1)

        results_group.setMinimumHeight(100)
        return results_group

    def create_load_info_group(self):
        load_info_group = QGroupBox("Load Information")
        load_info_group.setStyleSheet(get_group_box_style())
        load_info_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred) 
        load_info_layout = QHBoxLayout()
        load_info_group.setLayout(load_info_layout)

        load_month_label = QLabel("Month:")
        load_month_label.setStyleSheet(get_label_style())
        self.load_month_combo = QComboBox()
        self.load_month_combo.addItems([
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ])
        self.load_month_combo.setStyleSheet(get_month_info_style())

        load_year_label = QLabel("Year:")
        load_year_label.setStyleSheet(get_label_style())
        self.load_year_spinbox = QSpinBox()
        self.load_year_spinbox.setRange(2000, 2100)
        self.load_year_spinbox.setValue(datetime.now().year)
        self.load_year_spinbox.setStyleSheet(get_month_info_style())

        load_button = QPushButton("Load")
        load_button.setStyleSheet(get_button_style())
        load_button.clicked.connect(self.load_info_to_inputs)

        load_info_layout.addWidget(load_month_label)
        load_info_layout.addWidget(self.load_month_combo)
        load_info_layout.addSpacing(20)
        load_info_layout.addWidget(load_year_label)
        load_info_layout.addWidget(self.load_year_spinbox)
        load_info_layout.addSpacing(20)
        load_info_layout.addWidget(load_button)
        load_info_layout.addStretch(1)
        return load_info_group
        
    def update_meter_inputs(self, value=None):
        num_meters = value if value is not None else self.meter_count_spinbox.value()
        current_values = {i: meter_edit.text() for i, meter_edit in enumerate(self.meter_entries)}
        
        self._clear_layout(self.meter_layout)
        self.meter_entries = []
        
        for i in range(num_meters):
            meter_edit = CustomLineEdit()
            meter_edit.setObjectName(f"meter_edit_{i}")
            meter_edit.setPlaceholderText(f"Enter meter {i+1} reading")
            numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))  # only whole numbers
            meter_edit.setValidator(numeric_validator)
            self.meter_layout.addRow(f"Meter {i+1} Reading:", meter_edit)
            if i in current_values:
                meter_edit.setText(current_values[i])
            self.meter_entries.append(meter_edit)
        
        # Re-configure navigation whenever widgets change
        self.setup_navigation_main_tab()

    def update_diff_inputs(self, value=None):
        num_diffs = value if value is not None else self.diff_count_spinbox.value()
        current_values = {i: diff_edit.text() for i, diff_edit in enumerate(self.diff_entries)}
 
        self._clear_layout(self.diff_layout)
        self.diff_entries = []
        
        for i in range(num_diffs):
            diff_edit = CustomLineEdit()
            diff_edit.setObjectName(f"diff_edit_{i}")
            diff_edit.setPlaceholderText(f"Enter difference {i+1} reading")
            numeric_validator = QRegExpValidator(QRegExp(r'^\d+$'))  # only whole numbers
            diff_edit.setValidator(numeric_validator)
            self.diff_layout.addRow(f"Difference {i+1} Reading:", diff_edit)
            if i in current_values:
                diff_edit.setText(current_values[i])
            self.diff_entries.append(diff_edit)
        
        # Re-configure navigation whenever widgets change
        self.setup_navigation_main_tab()
        
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def calculate_main(self):
        try:
            def _to_int_safe(txt: str) -> int:
                """Convert text to int, accepting float strings (e.g. '123.0').

                Returns 0 for empty strings and raises ValueError for truly invalid
                formats so that the outer except can handle the error display."""
                if not txt or not txt.strip():
                    return 0
                try:
                    return int(txt)
                except ValueError:
                    try:
                        return int(float(txt))  # Handles "123.0"
                    except ValueError:
                        raise

            meter_readings = [_to_int_safe(meter_edit.text()) for meter_edit in self.meter_entries]
            diff_readings = [_to_int_safe(diff_edit.text()) for diff_edit in self.diff_entries]
            additional_amount = self.get_additional_amount()

            total_unit = sum(meter_readings)
            total_diff = sum(diff_readings)
            per_unit_cost = (total_unit / total_diff) if total_diff != 0 else 0.0 # Ensure float division
            in_total = total_unit + additional_amount

            self.total_unit_value_label.setText(f"{total_unit}")
            self.total_diff_value_label.setText(f"{total_diff}")
            self.per_unit_cost_value_label.setText(f"{per_unit_cost:.2f} TK")
            self.additional_amount_value_label.setText(f"{additional_amount:.2f} TK")
            self.in_total_value_label.setText(f"{in_total:.2f} TK")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for all readings.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}\n{traceback.format_exc()}")

    def load_info_to_inputs(self):
        source = self.main_window.load_info_source_combo.currentText()
        selected_month = self.load_month_combo.currentText()
        selected_year = self.load_year_spinbox.value()

        if source == "Load from PC (CSV)":
            self.load_info_to_inputs_from_csv(selected_month, selected_year)
        elif source == "Load from Cloud":
            if self.main_window.supabase_manager.is_client_initialized() and self.main_window.check_internet_connectivity():
                self.load_info_to_inputs_from_supabase(selected_month, selected_year)
            elif not self.main_window.supabase_manager.is_client_initialized():
                QMessageBox.warning(self, "Supabase Not Configured", "Supabase is not configured. Please go to the 'Supabase Config' tab.")
            else: # No internet
                 QMessageBox.warning(self, "Network Error", 
                                  "No internet connection detected. Please check your network and try again.")
        else:
            QMessageBox.warning(self, "Unknown Source", "Please select a valid source to load data from.")

    def load_info_to_inputs_from_csv(self, selected_month, selected_year):
        filename = "meter_calculation_history.csv"
        selected_month_year_str_ui = f"{selected_month} {selected_year}"
        
        if not os.path.exists(filename):
            QMessageBox.warning(self, "File Not Found", f"{filename} does not exist.")
            return

        try:
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                all_rows = list(reader) # Read all rows into memory
                
                main_data_row = None
                room_data_rows = []

                def get_csv_value(row_dict, key_name, default_if_missing_or_empty):
                    for k_original, v_original in row_dict.items():
                        if k_original.strip().lower() == key_name.strip().lower():
                            stripped_v = v_original.strip() if isinstance(v_original, str) else ""
                            return stripped_v if stripped_v else default_if_missing_or_empty
                    return default_if_missing_or_empty

                # Find the main data row first
                for i, row in enumerate(all_rows):
                    csv_month_year_str = get_csv_value(row, "Month", "")
                    if csv_month_year_str.strip().lower() == selected_month_year_str_ui.lower():
                        main_data_row = row
                        # If this row also contains room data (which it should for the first room), add it
                        if get_csv_value(row, "Room Name", ""): # Check if room data exists in this row
                            room_data_rows.append(row)
                        
                        # Now, collect subsequent room-only rows
                        for j in range(i + 1, len(all_rows)):
                            next_row = all_rows[j]
                            next_month_val = get_csv_value(next_row, "Month", "")
                            if not next_month_val.strip(): # If Month is empty, it's a room-only row
                                room_data_rows.append(next_row)
                            else: # Found a new main entry, stop collecting room rows
                                break
                        break # Found main data and collected all associated rooms, exit outer loop

                if not main_data_row:
                    QMessageBox.warning(self, "Data Not Found", f"No data found for {selected_month_year_str_ui} in {filename}.")
                    return
                
                # Load main tab data
                self.month_combo.setCurrentText(selected_month)
                self.year_spinbox.setValue(selected_year)
                
                meter_values_csv = [get_csv_value(main_data_row, f"Meter-{i+1}", "0") for i in range(10)]
                diff_values_csv = [get_csv_value(main_data_row, f"Diff-{i+1}", "0") for i in range(10)]
                
                # Filter out trailing "0"s to set spinbox counts correctly
                num_meters = len(meter_values_csv)
                while num_meters > 0 and meter_values_csv[num_meters-1] == "0":
                    num_meters -=1
                num_meters = max(1, num_meters) # At least 1

                num_diffs = len(diff_values_csv)
                while num_diffs > 0 and diff_values_csv[num_diffs-1] == "0":
                    num_diffs -=1
                num_diffs = max(1, num_diffs)

                max_meters = self.meter_count_spinbox.maximum()
                max_diffs  = self.diff_count_spinbox.maximum()
                if num_meters > max_meters or num_diffs > max_diffs:
                    QMessageBox.warning(self, "Data Truncated",
                                        "Incoming data contains more readings than the UI "
                                        "can display. Extra values will be ignored.")
                self.meter_count_spinbox.setValue(min(num_meters, max_meters))
                self.diff_count_spinbox.setValue(min(num_diffs,  max_diffs))

                for i, val_str in enumerate(meter_values_csv[:num_meters]):
                    if i < len(self.meter_entries):
                        # Normalize numeric values so that "123.0" → "123" while preserving
                        # any truly non-integer strings (unlikely given validators).
                        display_val = str(val_str)
                        try:
                            num_val = float(val_str)
                            # If the float is effectively an int (e.g. 123.0) drop the decimal part
                            if num_val.is_integer():
                                display_val = str(int(num_val))
                        except (ValueError, TypeError):
                            # Leave display_val as-is if it is not a plain number
                            pass
                        self.meter_entries[i].setText(display_val)
                for i, val_str in enumerate(diff_values_csv[:num_diffs]):
                    if i < len(self.diff_entries):
                        display_val = str(val_str)
                        try:
                            num_val = float(val_str)
                            if num_val.is_integer():
                                display_val = str(int(num_val))
                        except (ValueError, TypeError):
                            pass
                        self.diff_entries[i].setText(display_val)
                    
                self.additional_amount_input.setText(get_csv_value(main_data_row, "Added Amount", "0"))

                # Load room tab data
                if room_data_rows:
                    self.main_window.rooms_tab_instance.num_rooms_spinbox.setValue(len(room_data_rows))
                    # This will trigger update_room_inputs in RoomsTab, creating the necessary widgets

                    for i, room_row in enumerate(room_data_rows):
                        if hasattr(self.main_window.rooms_tab_instance, 'load_room_data_from_csv_row'):
                            self.main_window.rooms_tab_instance.load_room_data_from_csv_row(room_row, i)
                        else:
                            print("Warning: rooms_tab_instance does not have load_room_data_from_csv_row method.")
                    
                    # After loading all room data, trigger calculation for rooms
                    self.main_window.rooms_tab_instance.calculate_rooms()
                else:
                    # If no room data found, ensure rooms tab is reset or has default number of rooms
                    self.main_window.rooms_tab_instance.num_rooms_spinbox.setValue(1) # Or a sensible default
                    self.main_window.rooms_tab_instance.calculate_rooms() # Recalculate with default rooms

                QMessageBox.information(self, "Load Successful", f"Data for {selected_month_year_str_ui} loaded into input fields from CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load data from CSV: {e}\n{traceback.format_exc()}")

    def load_info_to_inputs_from_supabase(self, selected_month, selected_year):
        if not self.main_window.supabase_manager.is_client_initialized():
            QMessageBox.critical(self, "Supabase Error", "Supabase client is not initialized.")
            return

        try:
            # Fetch main calculation data
            main_calc_record = self.main_window.supabase_manager.get_main_calculation_by_month_year(
                month=selected_month, 
                year=selected_year
            )

            if not main_calc_record:
                QMessageBox.warning(self, "Data Not Found", f"No data found for {selected_month} {selected_year} in the cloud.")
                return

            main_data = main_calc_record.get("main_data", {})
            if isinstance(main_data, str):
                try:
                    main_data = json.loads(main_data)
                except json.JSONDecodeError:
                    main_data = {}

            # Load main tab data
            self.month_combo.setCurrentText(selected_month)
            self.year_spinbox.setValue(selected_year)
            
            meter_values = main_data.get("meter_readings", [])
            diff_values = main_data.get("diff_readings", [])
            
            num_meters = len(meter_values)
            num_diffs = len(diff_values)
            
            self.meter_count_spinbox.setValue(num_meters)
            self.diff_count_spinbox.setValue(num_diffs)
            
            for i, val in enumerate(meter_values):
                if i < len(self.meter_entries):
                    # Normalize numeric values so that "123.0" → "123" while preserving
                    # any truly non-integer strings (unlikely given validators).
                    display_val = str(val)
                    try:
                        num_val = float(val)
                        # If the float is effectively an int (e.g. 123.0) drop the decimal part
                        if num_val.is_integer():
                            display_val = str(int(num_val))
                    except (ValueError, TypeError):
                        # Leave display_val as-is if it is not a plain number
                        pass
                    self.meter_entries[i].setText(display_val)
            for i, val in enumerate(diff_values):
                if i < len(self.diff_entries):
                    display_val = str(val)
                    try:
                        num_val = float(val)
                        if num_val.is_integer():
                            display_val = str(int(num_val))
                    except (ValueError, TypeError):
                        pass
                    self.diff_entries[i].setText(display_val)
                
            # Support both legacy 'added_amount' and new 'additional_amount' keys
            add_amt = main_data.get("additional_amount", main_data.get("added_amount", "0"))
            self.additional_amount_input.setText(str(add_amt))

            # Fetch and load room data
            main_calc_id = main_calc_record.get("id")
            if main_calc_id:
                room_records = self.main_window.supabase_manager.get_room_calculations(main_calc_id)
                if room_records:
                    # RoomsTab already provides a helper that takes the full list.
                    if hasattr(self.main_window.rooms_tab_instance, 'load_room_data_from_supabase_rows'):
                        self.main_window.rooms_tab_instance.load_room_data_from_supabase_rows(room_records)
                    else:
                        # Fallback: minimal per-record population to avoid data loss
                        self.main_window.rooms_tab_instance.num_rooms_spinbox.setValue(len(room_records))
                        for i, room_rec in enumerate(room_records):
                            room_data = room_rec.get("room_data", {})
                            if isinstance(room_data, str):
                                try:
                                    room_data = json.loads(room_data)
                                except json.JSONDecodeError:
                                    room_data = {}
                            # Directly call setter fields if loader helper missing
                            if i < len(self.main_window.rooms_tab_instance.room_entries):
                                re = self.main_window.rooms_tab_instance.room_entries[i]
                                re['present_entry'].setText(str(room_data.get('present_unit', '')))
                                re['previous_entry'].setText(str(room_data.get('previous_unit', '')))
                                re['gas_bill_entry'].setText(str(room_data.get('gas_bill', '')))
                                re['water_bill_entry'].setText(str(room_data.get('water_bill', '')))
                                re['house_rent_entry'].setText(str(room_data.get('house_rent', '')))
                    # After populating, ensure calculations refresh
                    self.main_window.rooms_tab_instance.calculate_rooms()

            self.calculate_main() # Recalculate results based on loaded data

            # Recalculate room bills now that per-unit cost is up-to-date
            if hasattr(self.main_window.rooms_tab_instance, 'calculate_rooms'):
                try:
                    self.main_window.rooms_tab_instance.calculate_rooms()
                except Exception as calc_err:
                    # Log but don't block main load flow; user will see message from RoomsTab
                    print(f"Warning: rooms_tab_instance.calculate_rooms raised: {calc_err}")

            QMessageBox.information(self, "Load Successful", f"Data for {selected_month} {selected_year} loaded from the cloud.")

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load data from Cloud: {e}\n{traceback.format_exc()}")

    def setup_navigation_main_tab(self):
        """Configure Enter / Up / Down focus navigation for Main tab fields.

        Order:
            meter-1 → diff-1 → meter-2 → diff-2 → … → meter-N → diff-N → additional_amount

        • Enter / Down moves focus to next widget in the sequence (wrap-around).
        • Up moves focus to the previous widget in the sequence (wrap-around).
        """
        if not (self.meter_entries or self.diff_entries or self.additional_amount_input):
            return  # Nothing to wire up yet

        meters = self.meter_entries
        diffs = self.diff_entries
        aa    = self.additional_amount_input

        # ── Enter / Return sequence (already OK) ────────────────────────────
        enter_seq = []
        max_len = max(len(meters), len(diffs))
        for i in range(max_len):
            if i < len(meters):
                enter_seq.append(meters[i])
            if i < len(diffs):
                enter_seq.append(diffs[i])
        if aa:
            enter_seq.append(aa)

        # ── Up / Down sequences (column-wise) ──────────────────────────────
        #   Up:  … m2 → m1 → AA → d3 → d2 → d1 → m3 … (wrap)
        up_seq = list(reversed(meters))
        if aa:
            up_seq.append(aa)
        up_seq.extend(reversed(diffs))

        down_seq = list(reversed(up_seq))

        # Helper to link navigation for a given mapping list
        def _link_sequence(seq, attr_name):
            if not seq:
                return
            length = len(seq)
            for idx, w in enumerate(seq):
                nxt = seq[(idx + 1) % length]
                setattr(w, attr_name, nxt)

        # Apply mappings
        _link_sequence(enter_seq, 'next_widget_on_enter')
        _link_sequence(up_seq,    'up_widget')
        _link_sequence(down_seq,  'down_widget')

        # Ensure initial focus inside the tab if none is currently in sequence
        if self.focusWidget() not in enter_seq:
            enter_seq[0].setFocus()

    # Dummy classes for testing purposes
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication, QMainWindow

    class DummyMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.load_info_source_combo = QComboBox()
            self.load_info_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
            self.supabase = None # Mock Supabase client
            self.check_internet_connectivity = lambda: True # Mock internet check
            
            # Mock RoomsTab instance
            class DummyRoomsTab(QWidget):
                def __init__(self):
                    super().__init__()
                    self.num_rooms_spinbox = QSpinBox()
                    self.num_rooms_spinbox.setRange(1, 20)
                    self.num_rooms_spinbox.setValue(1)
                    self.room_entries = [] # Mock room entries
                    self.rooms_scroll_layout = QGridLayout() # Mock layout
                    self.calculate_rooms = lambda: print("DummyRoomsTab.calculate_rooms called")
                    self.load_room_data_from_csv_row = lambda row, index: print(f"DummyRoomsTab.load_room_data_from_csv_row called with {row} at index {index}")
                    
                    # Populate some dummy room entries for testing
                    for i in range(3):
                        self.room_entries.append({
                            'present_entry': CustomLineEdit(),
                            'previous_entry': CustomLineEdit(),
                            'gas_bill_entry': CustomLineEdit(),
                            'water_bill_entry': CustomLineEdit(),
                            'house_rent_entry': CustomLineEdit(),
                            'real_unit_label': QLabel(),
                            'unit_bill_label': QLabel(),
                            'grand_total_label': QLabel()
                        })

            self.rooms_tab_instance = DummyRoomsTab()

        def setup_navigation(self):
            pass # Dummy method

    app = QApplication(sys.argv)
    main_window = DummyMainWindow()
    main_tab_widget = MainTab(main_window)
    main_tab_widget.setWindowTitle("MainTab Test")
    main_tab_widget.setGeometry(100, 100, 800, 600)
    main_tab_widget.show()
    sys.exit(app.exec_())
