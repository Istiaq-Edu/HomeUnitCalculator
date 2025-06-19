import sys
import json
import contextlib
import os
import csv
import traceback
from datetime import datetime

from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QMessageBox, QSpinBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QSizePolicy,
    QDialog, QAbstractItemView
)
from postgrest.exceptions import APIError

from src.ui.styles import (
    get_stylesheet, get_group_box_style, get_line_edit_style, get_button_style,
    get_room_group_style, get_month_info_style, get_table_style, get_label_style
)
from src.core.utils import resource_path # For icons
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomSpinBox, CustomNavButton


# Dialog for Editing Records (Moved from HomeUnitCalculator.py)
class EditRecordDialog(QDialog):
    def __init__(self, record_id, main_data, room_data_list, parent=None): # parent is the HistoryTab instance
        super().__init__(parent)
        self.record_id = record_id 
        self.main_window = parent.main_window # Access main_window through HistoryTab's parent
        self.supabase = self.main_window.supabase # Get supabase client from main_window
        self.room_edit_widgets = [] 
        self.meter_diff_edit_widgets = [] 
        
        self.setWindowTitle("Edit Calculation Record")
        self.setMinimumWidth(600) 
        self.setMinimumHeight(500) 
        self.setStyleSheet(get_stylesheet()) 

        main_layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()

        self.month_year_label = QLabel(f"Record for: {main_data.get('month', '')} {main_data.get('year', '')}")
        main_layout.addWidget(self.month_year_label)

        main_group = QGroupBox("Main Calculation Data")
        main_scroll_area = AutoScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_widget = QWidget()
        main_group_layout = QFormLayout(main_scroll_widget)
        main_group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        main_scroll_area.setWidget(main_scroll_widget)
        main_group_vbox = QVBoxLayout(main_group)
        main_group_vbox.addWidget(main_scroll_area)
        
        self.meter1_edit = CustomLineEdit(); self.meter1_edit.setObjectName("dialog_meter1_edit")
        self.meter2_edit = CustomLineEdit(); self.meter2_edit.setObjectName("dialog_meter2_edit")
        self.meter3_edit = CustomLineEdit(); self.meter3_edit.setObjectName("dialog_meter3_edit")
        self.diff1_edit = CustomLineEdit(); self.diff1_edit.setObjectName("dialog_diff1_edit")
        self.diff2_edit = CustomLineEdit(); self.diff2_edit.setObjectName("dialog_diff2_edit")
        self.diff3_edit = CustomLineEdit(); self.diff3_edit.setObjectName("dialog_diff3_edit")
        
        meter_values = [
            main_data.get("meter1_reading", "") or "",
            main_data.get("meter2_reading", "") or "",
            main_data.get("meter3_reading", "") or ""
        ]
        diff_values = [
            main_data.get("diff1", "") or "",
            main_data.get("diff2", "") or "",
            main_data.get("diff3", "") or ""
        ]
        
        extra_meter_readings = main_data.get("extra_meter_readings", None)
        extra_diff_readings = main_data.get("extra_diff_readings", None)
        
        if extra_meter_readings:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                extra_meters = json.loads(extra_meter_readings)
                if isinstance(extra_meters, list): 
                    meter_values.extend(extra_meters)
        
        if extra_diff_readings:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                extra_diffs = json.loads(extra_diff_readings)
                if isinstance(extra_diffs, list): 
                    diff_values.extend(extra_diffs)
        
        num_pairs = max(3, len(meter_values), len(diff_values)) # Ensure at least 3 pairs for backward compatibility
                                                                # or if extra readings make it longer.
        
        for i in range(num_pairs):
            if i < 3:
                meter_edit = [self.meter1_edit, self.meter2_edit, self.meter3_edit][i]
                diff_edit = [self.diff1_edit, self.diff2_edit, self.diff3_edit][i]
            else:
                meter_edit = CustomLineEdit()
                meter_edit.setObjectName(f"dialog_meter{i+1}_edit")
                diff_edit = CustomLineEdit()
                diff_edit.setObjectName(f"dialog_diff{i+1}_edit")
            
            main_group_layout.addRow(f"Meter {i+1} Reading:", meter_edit)
            main_group_layout.addRow(f"Difference {i+1}:", diff_edit)
            
            self.meter_diff_edit_widgets.append({'meter_edit': meter_edit, 'diff_edit': diff_edit, 'index': i})
        
        self.additional_amount_edit = CustomLineEdit()
        self.additional_amount_edit.setObjectName("dialog_additional_amount_edit")
        self.additional_amount_edit.setValidator(QRegExpValidator(QRegExp(r'^\d*\.?\d*$')))
        main_group_layout.addRow("Additional Amount:", self.additional_amount_edit)
        main_layout.addWidget(main_group)

        self.rooms_group = QGroupBox("Room Data") 
        rooms_main_layout = QVBoxLayout(self.rooms_group)
        scroll_area_rooms = QScrollArea() # Renamed to avoid conflict if self.scroll_area is used elsewhere
        scroll_area_rooms.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        self.rooms_edit_layout = QVBoxLayout(scroll_content_widget)
        scroll_area_rooms.setWidget(scroll_content_widget)
        rooms_main_layout.addWidget(scroll_area_rooms)

        for i, room_data in enumerate(room_data_list):
            room_name = room_data.get('room_name', 'Unknown Room')
            room_edit_group = QGroupBox(room_name)
            room_edit_group.setStyleSheet(get_room_group_style())
            room_edit_form_layout = QFormLayout(room_edit_group)
            room_edit_form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

            present_edit = CustomLineEdit()
            present_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_present")
            previous_edit = CustomLineEdit()
            previous_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_previous")
            room_id = room_data.get('id') 

            room_edit_form_layout.addRow("Present Reading:", present_edit)
            room_edit_form_layout.addRow("Previous Reading:", previous_edit)

            self.rooms_edit_layout.addWidget(room_edit_group)
            self.room_edit_widgets.append({
                "room_id": room_id, "name": room_name, 
                "present_edit": present_edit, "previous_edit": previous_edit
            })
            
        if not room_data_list:
             no_rooms_label = QLabel("No room data associated with this record.")
             self.rooms_edit_layout.addWidget(no_rooms_label)
        main_layout.addWidget(self.rooms_group)

        self.save_button = CustomNavButton("Save Changes")
        self.cancel_button = QPushButton("Cancel")
        self.save_button.setStyleSheet(get_button_style())
        self.cancel_button.setStyleSheet("background-color: #6c757d; color: white; border: none; border-radius: 4px; padding: 10px; font-weight: bold; font-size: 14px;") 

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

        self.populate_data(main_data, room_data_list)
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.reject)
        self._setup_navigation_edit_dialog()

    def _setup_navigation_edit_dialog(self):
        meter_diff_edits = [pair['meter_edit'] for pair in self.meter_diff_edit_widgets] + \
                           [pair['diff_edit'] for pair in self.meter_diff_edit_widgets]
        aa = self.additional_amount_edit
        save_btn = self.save_button
        
        all_line_edits_in_dialog = meter_diff_edits + [aa]
        for room_set in self.room_edit_widgets:
            all_line_edits_in_dialog.extend([room_set["present_edit"], room_set["previous_edit"]])

        for widget in all_line_edits_in_dialog:
            if widget:
                widget.next_widget_on_enter = None
                widget.up_widget = None
                widget.down_widget = None
                widget.left_widget = None # Ensure these are cleared
                widget.right_widget = None # Ensure these are cleared
        
        if isinstance(save_btn, CustomNavButton): save_btn.next_widget_on_enter = None

        enter_sequence = meter_diff_edits + [aa]
        for room_set in self.room_edit_widgets:
            enter_sequence.extend([room_set["present_edit"], room_set["previous_edit"]])
        
        for i, widget in enumerate(enter_sequence):
            widget.next_widget_on_enter = enter_sequence[i+1] if i < len(enter_sequence) - 1 else save_btn
        
        if isinstance(save_btn, CustomNavButton) and enter_sequence:
            save_btn.next_widget_on_enter = enter_sequence[0]

        # Simplified Up/Down navigation (single loop through all fields)
        up_down_sequence = enter_sequence # Use the same sequence for Up/Down for simplicity here
        if up_down_sequence:
            for i, widget in enumerate(up_down_sequence):
                widget.down_widget = up_down_sequence[(i + 1) % len(up_down_sequence)]
                widget.up_widget = up_down_sequence[(i - 1 + len(up_down_sequence)) % len(up_down_sequence)]
        
        if enter_sequence: enter_sequence[0].setFocus()

    def populate_data(self, main_data, room_data_list):
        meter_values = [
            main_data.get("meter1_reading", "") or "", main_data.get("meter2_reading", "") or "", main_data.get("meter3_reading", "") or ""
        ]
        diff_values = [
            main_data.get("diff1", "") or "", main_data.get("diff2", "") or "", main_data.get("diff3", "") or ""
        ]
        
        if main_data.get("extra_meter_readings"):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                meter_values.extend(json.loads(main_data["extra_meter_readings"]))
        if main_data.get("extra_diff_readings"):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                diff_values.extend(json.loads(main_data["extra_diff_readings"]))

        for i, pair_widgets in enumerate(self.meter_diff_edit_widgets):
            if i < len(meter_values) and pair_widgets['meter_edit']: pair_widgets['meter_edit'].setText(str(meter_values[i]))
            if i < len(diff_values) and pair_widgets['diff_edit']: pair_widgets['diff_edit'].setText(str(diff_values[i]))
                
        self.additional_amount_edit.setText(str(main_data.get("additional_amount", "") or ""))
        
        for i, room_widget_set in enumerate(self.room_edit_widgets):
            if i < len(room_data_list):
                room_data = room_data_list[i]
                room_widget_set["present_edit"].setText(str(room_data.get("present_reading_room", "") or ""))
                room_widget_set["previous_edit"].setText(str(room_data.get("previous_reading_room", "") or ""))

    def save_changes(self):
        def _s_int(v_str, default=0): 
            try:
                if not v_str or not v_str.strip():
                    return default
                # Handle decimal strings by converting to float first, then int
                return int(float(v_str.strip()))
            except (ValueError, TypeError):
                return default
        def _s_float(v_str, default=0.0): 
            try: 
                return float(v_str) if v_str and v_str.strip() else default
            except (ValueError, TypeError): 
                return default

        try:
            meter_vals = [_s_int(pair['meter_edit'].text()) for pair in self.meter_diff_edit_widgets]
            diff_vals = [_s_int(pair['diff_edit'].text()) for pair in self.meter_diff_edit_widgets]
            
            # Pad with zeros if fewer than 3 entries were dynamically created
            while len(meter_vals) < 3: meter_vals.append(0)
            while len(diff_vals) < 3: diff_vals.append(0)

            additional_amount = _s_float(self.additional_amount_edit.text())
            total_unit_cost = sum(meter_vals)
            total_diff_units = sum(diff_vals)
            per_unit_cost_calc = (total_unit_cost / total_diff_units) if total_diff_units != 0 else 0.0
            grand_total_bill = total_unit_cost + additional_amount

            updated_main_data = {
                "meter1_reading": meter_vals[0], "meter2_reading": meter_vals[1], "meter3_reading": meter_vals[2],
                "diff1": diff_vals[0], "diff2": diff_vals[1], "diff3": diff_vals[2],
                "additional_amount": additional_amount,
                "total_unit_cost": total_unit_cost, "total_diff_units": total_diff_units,
                "per_unit_cost_calculated": per_unit_cost_calc, "grand_total_bill": grand_total_bill,
                "extra_meter_readings": json.dumps(meter_vals[3:]) if len(meter_vals) > 3 else None,
                "extra_diff_readings": json.dumps(diff_vals[3:]) if len(diff_vals) > 3 else None
            }

            updated_room_data_list = []
            for rws in self.room_edit_widgets:
                present = _s_int(rws["present_edit"].text())
                previous = _s_int(rws["previous_edit"].text())
                if present < previous:
                    raise ValueError(
                        f"Present reading ({present}) cannot be less than previous reading "
                        f"({previous}) for room '{rws['name']}'."
                    )
                units_consumed = present - previous
                cost = units_consumed * per_unit_cost_calc
                room_data_to_append = {
                    "main_calculation_id": self.record_id, "room_name": rws["name"],
                    "present_reading_room": present, "previous_reading_room": previous,
                    "units_consumed_room": units_consumed, "cost_room": cost
                }
                if rws.get("room_id"): # Include room_id if it exists for upsert
                    room_data_to_append["id"] = rws["room_id"]
                updated_room_data_list.append(room_data_to_append)

            # Update main_calculations
            self.supabase.table("main_calculations").update(updated_main_data).eq("id", self.record_id).execute()
            
            # Use upsert for room_calculations to prevent data loss on partial failure
            # upsert will insert new records or update existing ones based on primary key (id)
            if updated_room_data_list:
                self.supabase.table("room_calculations").upsert(updated_room_data_list).execute()

            QMessageBox.information(self, "Success", "Record updated successfully.")
            self.accept()
        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to update: {e.message}\n{e.details}")
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Error: {e}\n{traceback.format_exc()}")


class HistoryTab(QWidget):
    MONTH_ORDER = {
        "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
    }

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref

        # Initialize UI elements that will be created in init_ui
        self.history_month_combo = None
        self.history_year_spinbox = None
        self.main_history_table = None
        self.room_history_table = None
        self.edit_selected_record_button = None
        self.delete_selected_record_button = None
        # load_history_source_combo is accessed via self.main_window

        self.init_ui()

    def init_ui(self):
        # Create main layout for the tab
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create AutoScrollArea for full page scrolling (same as rooms tab)
        scroll_area = AutoScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create content widget that will be scrollable
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)

        filter_group = QGroupBox("Filter Options")
        filter_group.setStyleSheet(get_group_box_style())
        filter_layout = QHBoxLayout(filter_group)
        month_label = QLabel("Month:")
        month_label.setStyleSheet(get_label_style())
        self.history_month_combo = QComboBox()
        self.history_month_combo.addItems(["All", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        self.history_month_combo.setStyleSheet(get_month_info_style())
        year_label = QLabel("Year:")
        year_label.setStyleSheet(get_label_style())
        self.history_year_spinbox = QSpinBox()
        # Use 0 as sentinel for “All”
        self.history_year_spinbox.setRange(0, 2100)
        self.history_year_spinbox.setSpecialValueText("All")
        self.history_year_spinbox.setValue(0)          # default to “All”, or keep current-year if preferred
        self.history_year_spinbox.setStyleSheet(get_month_info_style())
        filter_layout.addWidget(month_label)
        filter_layout.addWidget(self.history_month_combo)
        filter_layout.addSpacing(15)
        filter_layout.addWidget(year_label)
        filter_layout.addWidget(self.history_year_spinbox)
        filter_layout.addStretch(1)
        top_layout.addWidget(filter_group, 2)

        load_history_options_group = QGroupBox("Load History Options")
        load_history_options_group.setStyleSheet(get_group_box_style())
        load_history_options_layout = QHBoxLayout(load_history_options_group)
        load_history_options_layout.setSpacing(10)
        history_source_label = QLabel("Source:")
        history_source_label.setStyleSheet(get_label_style())
        load_history_options_layout.addWidget(history_source_label)
        load_history_options_layout.addWidget(self.main_window.load_history_source_combo) # Accessed from main_window
        load_history_button = QPushButton("Load History Table")
        load_history_button.clicked.connect(self.load_history)
        load_history_button.setStyleSheet(get_button_style())
        load_history_button.setFixedHeight(35)
        load_history_options_layout.addWidget(load_history_button)
        load_history_options_layout.addStretch(1)
        top_layout.addWidget(load_history_options_group, 2)

        record_actions_group = QGroupBox("Record Actions")
        record_actions_group.setStyleSheet(get_group_box_style())
        record_actions_layout = QHBoxLayout(record_actions_group)
        record_actions_layout.setSpacing(10)
        self.edit_selected_record_button = QPushButton("Edit Record")
        self.edit_selected_record_button.setStyleSheet(get_button_style())
        self.edit_selected_record_button.setFixedHeight(35)
        self.edit_selected_record_button.clicked.connect(self.handle_edit_selected_record)
        self.delete_selected_record_button = QPushButton("Delete Record")
        delete_button_style = "background-color: #dc3545; color: white; border: none; border-radius: 4px; padding: 8px; font-weight: bold; font-size: 13px;"
        self.delete_selected_record_button.setStyleSheet(delete_button_style)
        self.delete_selected_record_button.setFixedHeight(35)
        self.delete_selected_record_button.clicked.connect(self.handle_delete_selected_record)
        record_actions_layout.addWidget(self.edit_selected_record_button)
        record_actions_layout.addWidget(self.delete_selected_record_button)
        record_actions_layout.addStretch(1)
        top_layout.addWidget(record_actions_group, 1)
        layout.addLayout(top_layout)

        main_calc_group = QGroupBox("Main Calculation Info")
        main_calc_group.setStyleSheet(get_group_box_style())
        main_calc_layout = QVBoxLayout(main_calc_group)
        self.main_history_table = QTableWidget()
        # Enable horizontal scrollbar for main table if content exceeds width
        self.main_history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Vertical scrolling handled by main scroll area
        self.main_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.main_history_table.setAlternatingRowColors(True)
        self.main_history_table.setStyleSheet(get_table_style())
        # Initially set columns to minimum required, will update dynamically on data load
        self.set_main_history_table_columns(3)  # default 3 meters/diffs
        # Remove all height restrictions and let table grow naturally
        self.main_history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Resize table to content height and adjust table height to show all rows
        self.main_history_table.resizeRowsToContents()
        self.resize_table_to_content(self.main_history_table)
        main_calc_layout.addWidget(self.main_history_table)
        layout.addWidget(main_calc_group)  # No stretch factor - let it size naturally

        room_calc_group = QGroupBox("Room Calculation Info")
        room_calc_group.setStyleSheet(get_group_box_style())
        room_calc_layout = QVBoxLayout(room_calc_group)
        self.room_history_table = QTableWidget()
        self.room_history_table.setColumnCount(10)
        self.room_history_table.setHorizontalHeaderLabels([
            "Month", "Room Number", "Present Unit", "Previous Unit", "Real Unit", 
            "Unit Bill", "Gas Bill", "Water Bill", "House Rent", "Grand Total"
        ])
        # Allow interactive resizing and horizontal scrolling for room table
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) 
        self.room_history_table.setAlternatingRowColors(True)
        self.room_history_table.setStyleSheet(get_table_style())
        # Enable horizontal scrollbar for room table if content exceeds width
        self.room_history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.room_history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Vertical scrolling handled by main scroll area
        self.room_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.room_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Remove all height restrictions and let table grow naturally
        self.room_history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Resize table to content height and adjust table height to show all rows
        self.room_history_table.resizeRowsToContents()
        self.resize_table_to_content(self.room_history_table)
        room_calc_layout.addWidget(self.room_history_table)
        layout.addWidget(room_calc_group)  # No stretch factor - let it size naturally

        # Add new totals section
        totals_group = QGroupBox("Total Summary")
        totals_group.setStyleSheet(get_group_box_style())
        totals_layout = QVBoxLayout(totals_group)
        self.totals_table = QTableWidget()
        self.totals_table.setColumnCount(5)
        self.totals_table.setHorizontalHeaderLabels([
            "Month", "Total House Rent", "Total Water Bill", "Total Gas Bill", "Total Room Unit Bill"
        ])
        self.totals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.totals_table.setAlternatingRowColors(True)
        self.totals_table.setStyleSheet(get_table_style())
        # Remove all height restrictions and let table grow naturally
        self.totals_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Disable scrollbars for totals table since we're using full page scrolling
        self.totals_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.totals_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Resize table to content height and adjust table height to show all rows
        self.totals_table.resizeRowsToContents()
        self.resize_table_to_content(self.totals_table)
        totals_layout.addWidget(self.totals_table)
        layout.addWidget(totals_group)  # No stretch factor - let it size naturally
        
        # Set the content widget to the scroll area and add scroll area to main layout
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def resize_table_to_content(self, table):
        """Resize table height to fit all rows without scrolling"""
        if table.rowCount() == 0:
            table.setFixedHeight(table.horizontalHeader().height() + 10)
            return
        
        # Calculate total height needed
        header_height = table.horizontalHeader().height()
        row_height = 0
        
        # Get the height of all rows
        for row in range(table.rowCount()):
            row_height += table.rowHeight(row)
        
        # Add some padding for borders and margins
        total_height = header_height + row_height + 10
        
        # Set the table to this exact height
        table.setFixedHeight(total_height)
        table.setMaximumHeight(total_height)
        table.setMinimumHeight(total_height)

    def set_main_history_table_columns(self, num_meters):
        # num_meters: number of meter/diff pairs to show, max 10
        num_meters = min(max(num_meters, 3), 10)  # clamp between 3 and 10
        # Fixed columns before meters/diffs
        fixed_columns = ["Month"]
        # Dynamic meter columns
        meter_columns = [f"Meter-{i+1}" for i in range(num_meters)]
        diff_columns = [f"Diff-{i+1}" for i in range(num_meters)]
        # Fixed columns after meters/diffs
        fixed_after_columns = ["Total Unit Cost", "Total Diff Units", "Per Unit Cost", "Added Amount", "Grand Total"]
        all_columns = fixed_columns + meter_columns + diff_columns + fixed_after_columns
        self.main_history_table.setColumnCount(len(all_columns))
        self.main_history_table.setHorizontalHeaderLabels(all_columns)
        header = self.main_history_table.horizontalHeader()
        # Set resize mode: stretch for fixed columns, resize to contents for meters/diffs
        for i in range(len(all_columns)):
            if i == 0 or i >= (1 + num_meters*2):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

    def load_history(self):
        try:
            selected_month = self.history_month_combo.currentText()
            selected_year_val = None if self.history_year_spinbox.specialValueText() and self.history_year_spinbox.value() == self.history_year_spinbox.minimum() else self.history_year_spinbox.value()
            source = self.main_window.load_history_source_combo.currentText() # From main_window

            if source == "Load from PC (CSV)":
                self.load_history_tables_from_csv(selected_month, selected_year_val)
            elif source == "Load from Cloud":
                if self.main_window.supabase and self.main_window.check_internet_connectivity():
                    month_filter = None if selected_month == "All" else selected_month
                    year_filter  = selected_year_val        # already None if “All”
                    self.load_history_tables_from_supabase(month_filter, year_filter)
                elif not self.main_window.supabase:
                    QMessageBox.warning(self, "Supabase Not Configured", "Supabase is not configured.")
                else:
                    QMessageBox.warning(self, "Network Error", "No internet connection.")
            else:
                QMessageBox.warning(self, "Unknown Source", "Select a valid source.")
        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"Error: {e}\n{traceback.format_exc()}")


    def load_history_tables_from_csv(self, selected_month, selected_year_val):
        filename = "meter_calculation_history.csv"
        
        if not os.path.exists(filename):
            QMessageBox.warning(self, "File Not Found", f"{filename} does not exist.")
            return

        try:
            with open(filename, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                all_rows = list(reader)
                
                def get_csv_value(row_dict, key_name, default_if_missing_or_empty):
                    for k_original, v_original in row_dict.items():
                        if k_original.strip().lower() == key_name.strip().lower():
                            stripped_v = v_original.strip() if isinstance(v_original, str) else ""
                            return stripped_v if stripped_v else default_if_missing_or_empty
                    return default_if_missing_or_empty

                # Filter rows based on selected filters
                filtered_main_rows = []
                all_room_rows = []
                
                i = 0
                while i < len(all_rows):
                    row = all_rows[i]
                    csv_month_year_str = get_csv_value(row, "Month", "")
                    
                    if csv_month_year_str.strip():  # This is a main calculation row
                        # Parse month and year from CSV
                        try:
                            parts = csv_month_year_str.strip().split()
                            if len(parts) >= 2:
                                csv_month = parts[0]
                                csv_year = int(parts[1])
                                
                                # Apply filters
                                month_matches = (selected_month == "All" or csv_month == selected_month)
                                year_matches = (selected_year_val is None or csv_year == selected_year_val)
                                
                                if month_matches and year_matches:
                                    main_row_data = {
                                        'csv_row': row,
                                        'month': csv_month,
                                        'year': csv_year,
                                        'room_rows': []
                                    }
                                    
                                    # If this row also contains room data, add it
                                    if get_csv_value(row, "Room Name", ""):
                                        main_row_data['room_rows'].append(row)
                                    
                                    # Collect subsequent room-only rows
                                    j = i + 1
                                    while j < len(all_rows):
                                        next_row = all_rows[j]
                                        next_month_val = get_csv_value(next_row, "Month", "")
                                        if not next_month_val.strip():  # Empty month = room-only row
                                            main_row_data['room_rows'].append(next_row)
                                            j += 1
                                        else:
                                            break
                                    
                                    filtered_main_rows.append(main_row_data)
                                    # all_room_rows.extend(main_row_data['room_rows']) # Defer populating all_room_rows
                                    i = j - 1  # Skip the room rows we just processed
                        except (ValueError, IndexError):
                            pass  # Skip malformed rows
                    i += 1

                # Sort filtered_main_rows chronologically (most recent first)
                filtered_main_rows.sort(key=lambda x: (x['year'], self.MONTH_ORDER.get(x['month'], 0)), reverse=True)

                # Clear existing data
                self.main_history_table.setRowCount(0)
                self.room_history_table.setRowCount(0)

                # Prepare chronologically ordered room entries
                all_room_rows_sorted_with_context = []
                if filtered_main_rows:
                    for main_row_data_sorted in filtered_main_rows:
                        parent_month = main_row_data_sorted['month']
                        parent_year = main_row_data_sorted['year']
                        for room_csv_row_data in main_row_data_sorted['room_rows']:
                            all_room_rows_sorted_with_context.append({
                                'csv_row': room_csv_row_data,
                                'month': parent_month,
                                'year': parent_year
                            })

                if filtered_main_rows:
                    # Determine max number of meters/diffs dynamically (skip zeros)
                    max_meters = 3
                    for main_row_data in filtered_main_rows:
                        row = main_row_data['csv_row']
                        for i in range(10):  # Check up to 10 meters/diffs
                            meter_val = get_csv_value(row, f"Meter-{i+1}", "0")
                            diff_val = get_csv_value(row, f"Diff-{i+1}", "0")
                            # Only count if meter or diff is not 0 or empty
                            if (meter_val not in ["0", "", "0.0"]) or (diff_val not in ["0", "", "0.0"]):
                                max_meters = max(max_meters, i + 1)
                    max_meters = min(max_meters, 10)  # Clamp to 10

                    self.set_main_history_table_columns(max_meters)
                    self.main_history_table.setRowCount(len(filtered_main_rows))
                    
                    for row_idx, main_row_data in enumerate(filtered_main_rows):
                        row = main_row_data['csv_row']
                        
                        # Set month column
                        month_year_str = f"{main_row_data['month']} {main_row_data['year']}"
                        self.main_history_table.setItem(row_idx, 0, QTableWidgetItem(month_year_str))
                        
                        # Set meter columns dynamically (skip zeros)
                        for i in range(max_meters):
                            meter_val = get_csv_value(row, f"Meter-{i+1}", "0")
                            # Only show non-zero values
                            display_val = meter_val if meter_val not in ["0", "", "0.0"] else ""
                            self.main_history_table.setItem(row_idx, 1 + i, QTableWidgetItem(display_val))
                        
                        # Set diff columns dynamically (skip zeros)
                        for i in range(max_meters):
                            diff_val = get_csv_value(row, f"Diff-{i+1}", "0")
                            # Only show non-zero values
                            display_val = diff_val if diff_val not in ["0", "", "0.0"] else ""
                            self.main_history_table.setItem(row_idx, 1 + max_meters + i, QTableWidgetItem(display_val))
                        
                        # Set fixed columns after meters/diffs
                        base_col = 1 + max_meters * 2
                        # Handle column name variations between CSV and expected names
                        total_unit_cost = get_csv_value(row, "Total Unit Cost", "") or get_csv_value(row, "Total Unit", "0")
                        total_diff_units = get_csv_value(row, "Total Diff Units", "") or get_csv_value(row, "Total Diff", "0")
                        per_unit_cost = get_csv_value(row, "Per Unit Cost", "0")
                        added_amount = get_csv_value(row, "Added Amount", "0")
                        # Use "In Total" specifically for the main table's grand total
                        grand_total = get_csv_value(row, "In Total", "0") 
                        
                        self.main_history_table.setItem(row_idx, base_col + 0, QTableWidgetItem(total_unit_cost))
                        self.main_history_table.setItem(row_idx, base_col + 1, QTableWidgetItem(total_diff_units))
                        self.main_history_table.setItem(row_idx, base_col + 2, QTableWidgetItem(per_unit_cost))
                        self.main_history_table.setItem(row_idx, base_col + 3, QTableWidgetItem(added_amount))
                        self.main_history_table.setItem(row_idx, base_col + 4, QTableWidgetItem(grand_total))

                # Load room history data using the chronologically prepared list
                if all_room_rows_sorted_with_context:
                    self.room_history_table.setRowCount(len(all_room_rows_sorted_with_context))
                    
                    for row_idx, room_entry in enumerate(all_room_rows_sorted_with_context):
                        room_csv_data = room_entry['csv_row']
                        month_year_str = f"{room_entry['month']} {room_entry['year']}"
                        
                        room_name = get_csv_value(room_csv_data, "Room Name", "")
                        present_unit = get_csv_value(room_csv_data, "Present Unit", "0")
                        previous_unit = get_csv_value(room_csv_data, "Previous Unit", "0")
                        real_unit = get_csv_value(room_csv_data, "Real Unit", "0")
                        unit_bill = get_csv_value(room_csv_data, "Unit Bill", "0")
                        gas_bill = get_csv_value(room_csv_data, "Gas Bill", "0")
                        water_bill = get_csv_value(room_csv_data, "Water Bill", "0")
                        house_rent = get_csv_value(room_csv_data, "House Rent", "0")
                        grand_total = get_csv_value(room_csv_data, "Grand Total", "0")
                        
                        self.room_history_table.setItem(row_idx, 0, QTableWidgetItem(month_year_str))
                        self.room_history_table.setItem(row_idx, 1, QTableWidgetItem(room_name))
                        self.room_history_table.setItem(row_idx, 2, QTableWidgetItem(present_unit))
                        self.room_history_table.setItem(row_idx, 3, QTableWidgetItem(previous_unit))
                        self.room_history_table.setItem(row_idx, 4, QTableWidgetItem(real_unit))
                        self.room_history_table.setItem(row_idx, 5, QTableWidgetItem(unit_bill))
                        self.room_history_table.setItem(row_idx, 6, QTableWidgetItem(gas_bill))
                        self.room_history_table.setItem(row_idx, 7, QTableWidgetItem(water_bill))
                        self.room_history_table.setItem(row_idx, 8, QTableWidgetItem(house_rent))
                        self.room_history_table.setItem(row_idx, 9, QTableWidgetItem(grand_total))

                # Calculate and display totals using the filtered main rows instead of all room rows
                self.calculate_and_display_totals_from_main_rows(filtered_main_rows, get_csv_value)

                # Resize tables to fit content after loading data
                self.resize_table_to_content(self.main_history_table)
                self.resize_table_to_content(self.room_history_table)
                self.resize_table_to_content(self.totals_table)

                if not filtered_main_rows:
                    QMessageBox.information(self, "No Data", "No records found for the selected filters in CSV.")
                else:
                    QMessageBox.information(self, "Load Successful", f"Loaded {len(filtered_main_rows)} main records and {len(all_room_rows_sorted_with_context)} room records from CSV.")

        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"Failed to load history from CSV: {e}\n{traceback.format_exc()}")

    def load_history_tables_from_supabase(self, month_filter, year_filter):
        if not self.main_window.supabase or not self.main_window.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return

        try:
            # Build the query dynamically based on filters
            main_query = self.main_window.supabase.table("main_calculations").select("*")
            room_query = self.main_window.supabase.table("room_calculations").select("*")

            # Fetch main calculation IDs first
            ids_query = self.main_window.supabase.table("main_calculations").select("id")
            if month_filter:
                ids_query = ids_query.eq("month", month_filter)
            if year_filter is not None:
                ids_query = ids_query.eq("year", year_filter)
            
            ids_resp = ids_query.execute()
            ids = [r["id"] for r in ids_resp.data] if ids_resp.data else []

            # Fetch main calculations using the fetched IDs
            main_query = self.main_window.supabase.table("main_calculations").select("*")
            if ids:
                main_query = main_query.in_("id", ids)
            else:
                main_query = main_query.eq("id", -1) # No main records, so fetch none
            
            main_resp = main_query.order("year", desc=True).execute() # Order by year in Supabase
            main_records = main_resp.data if main_resp.data else []

            # Sort main_records by month chronologically in Python
            main_records.sort(key=lambda x: (x["year"], self.MONTH_ORDER.get(x["month"], 0)), reverse=True)

            # Build room history query
            room_query = self.main_window.supabase.table("room_calculations").select("*")
            if ids: # Use the same IDs for room history
                room_query = room_query.in_("main_calculation_id", ids)
            else:
                room_query = room_query.eq("main_calculation_id", -1) # Return no records
            
            room_resp = room_query.execute()
            room_records = room_resp.data if room_resp.data else []

            # Debug: Print main records order
            print("DEBUG: Main records order:")
            for idx, record in enumerate(main_records):
                print(f"  {idx}: ID={record['id']}, {record['month']} {record['year']}")
            
            # Create a mapping of main_calculation_id to chronological order
            main_calc_order = {record["id"]: idx for idx, record in enumerate(main_records)}
            
            # Debug: Print room records before sorting
            print("DEBUG: Room records before sorting:")
            for idx, record in enumerate(room_records[:10]):  # Show first 10
                print(f"  {idx}: main_calc_id={record['main_calculation_id']}, room={record.get('room_name', '')}")
            
            # Sort room_records chronologically by main calculation order, then by room_name
            room_records.sort(key=lambda x: (
                main_calc_order.get(x["main_calculation_id"], 999999),  # Use high number for missing IDs
                x.get("room_name", "")
            ))
            
            # Debug: Print room records after sorting
            print("DEBUG: Room records after sorting:")
            for idx, record in enumerate(room_records[:10]):  # Show first 10
                print(f"  {idx}: main_calc_id={record['main_calculation_id']}, room={record.get('room_name', '')}")

            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)

            if main_records:
                # Determine max number of meters/diffs dynamically
                max_meters = 3
                for record in main_records:
                    extra_meters = []
                    extra_diffs = []
                    if record.get("extra_meter_readings"):
                        with contextlib.suppress(json.JSONDecodeError, TypeError):
                            extra_meters = json.loads(record["extra_meter_readings"])
                    if record.get("extra_diff_readings"):
                        with contextlib.suppress(json.JSONDecodeError, TypeError):
                            extra_diffs = json.loads(record["extra_diff_readings"])
                    max_meters = max(max_meters, len(extra_meters) + 3, len(extra_diffs) + 3)
                max_meters = min(max_meters, 10)  # Clamp max to 10

                self.set_main_history_table_columns(max_meters)
                self.main_history_table.setRowCount(len(main_records))
                for row_idx, record in enumerate(main_records):
                    self.main_history_table.setItem(row_idx, 0, QTableWidgetItem(record.get("month", "")))
                    # Set meter columns dynamically
                    for i in range(max_meters):
                        if i == 0:
                            val = str(record.get("meter1_reading", ""))
                        elif i == 1:
                            val = str(record.get("meter2_reading", ""))
                        elif i == 2:
                            val = str(record.get("meter3_reading", ""))
                        else:
                            val = ""
                        if i >= 3 and record.get("extra_meter_readings"):
                            with contextlib.suppress(json.JSONDecodeError, TypeError):
                                extra_meters = json.loads(record["extra_meter_readings"])
                                if i - 3 < len(extra_meters):
                                    val = str(extra_meters[i - 3])
                        self.main_history_table.setItem(row_idx, 1 + i, QTableWidgetItem(val))
                    # Set diff columns dynamically
                    for i in range(max_meters):
                        if i == 0:
                            val = str(record.get("diff1", ""))
                        elif i == 1:
                            val = str(record.get("diff2", ""))
                        elif i == 2:
                            val = str(record.get("diff3", ""))
                        else:
                            val = ""
                        if i >= 3 and record.get("extra_diff_readings"):
                            with contextlib.suppress(json.JSONDecodeError, TypeError):
                                extra_diffs = json.loads(record["extra_diff_readings"])
                                if i - 3 < len(extra_diffs):
                                    val = str(extra_diffs[i - 3])
                        self.main_history_table.setItem(row_idx, 1 + max_meters + i, QTableWidgetItem(val))
                    # Set fixed columns after meters/diffs
                    base_col = 1 + max_meters * 2
                    self.main_history_table.setItem(row_idx, base_col + 0, QTableWidgetItem(f"{record.get('total_unit_cost', 0):.2f}"))
                    self.main_history_table.setItem(row_idx, base_col + 1, QTableWidgetItem(f"{record.get('total_diff_units', 0):.2f}"))
                    self.main_history_table.setItem(row_idx, base_col + 2, QTableWidgetItem(f"{record.get('per_unit_cost_calculated', 0):.2f}"))
                    self.main_history_table.setItem(row_idx, base_col + 3, QTableWidgetItem(f"{record.get('additional_amount', 0):.2f}"))
                    self.main_history_table.setItem(row_idx, base_col + 4, QTableWidgetItem(f"{record.get('grand_total_bill', 0):.2f}"))
                    self.main_history_table.item(row_idx, 0).setData(Qt.UserRole, record.get("id")) # Store ID for editing/deleting

            if room_records:
                self.room_history_table.setRowCount(len(room_records))
                for row_idx, record in enumerate(room_records):
                    # Find corresponding main calculation to get month/year
                    main_calc = next((m for m in main_records if m["id"] == record["main_calculation_id"]), None)
                    month_year_str = f"{main_calc['month']} {main_calc['year']}" if main_calc else "N/A"

                    # Populate all 10 columns consistently
                    self.room_history_table.setItem(row_idx, 0, QTableWidgetItem(month_year_str))
                    self.room_history_table.setItem(row_idx, 1, QTableWidgetItem(record.get("room_name", "")))
                    self.room_history_table.setItem(row_idx, 2, QTableWidgetItem(str(record.get("present_reading_room", "") or "")))
                    self.room_history_table.setItem(row_idx, 3, QTableWidgetItem(str(record.get("previous_reading_room", "") or "")))
                    self.room_history_table.setItem(row_idx, 4, QTableWidgetItem(str(record.get("units_consumed_room", "") or "")))
                    
                    # Unit Bill (cost_room)
                    cost_room_value = record.get('cost_room')
                    unit_bill_str = f"{cost_room_value:.2f}" if cost_room_value is not None else "0.00"
                    self.room_history_table.setItem(row_idx, 5, QTableWidgetItem(unit_bill_str))
                    
                    # Gas Bill
                    gas_bill_value = record.get('gas_bill')
                    gas_bill_str = f"{gas_bill_value:.2f}" if gas_bill_value is not None else "0.00"
                    self.room_history_table.setItem(row_idx, 6, QTableWidgetItem(gas_bill_str))
                    
                    # Water Bill
                    water_bill_value = record.get('water_bill')
                    water_bill_str = f"{water_bill_value:.2f}" if water_bill_value is not None else "0.00"
                    self.room_history_table.setItem(row_idx, 7, QTableWidgetItem(water_bill_str))
                    
                    # House Rent
                    house_rent_value = record.get('house_rent')
                    house_rent_str = f"{house_rent_value:.2f}" if house_rent_value is not None else "0.00"
                    self.room_history_table.setItem(row_idx, 8, QTableWidgetItem(house_rent_str))
                    
                    # Grand Total (calculate if not available)
                    grand_total_value = record.get('grand_total')
                    if grand_total_value is not None:
                        grand_total_str = f"{grand_total_value:.2f}"
                    else:
                        # Calculate grand total from available components
                        unit_bill = cost_room_value or 0
                        gas_bill = gas_bill_value or 0
                        water_bill = water_bill_value or 0
                        house_rent = house_rent_value or 0
                        calculated_total = unit_bill + gas_bill + water_bill + house_rent
                        grand_total_str = f"{calculated_total:.2f}"
                    self.room_history_table.setItem(row_idx, 9, QTableWidgetItem(grand_total_str))

            # Calculate and display totals for Supabase data
            self.calculate_and_display_totals_supabase(room_records)

            # Resize tables to fit content after loading data
            self.resize_table_to_content(self.main_history_table)
            self.resize_table_to_content(self.room_history_table)
            self.resize_table_to_content(self.totals_table)

            if not main_records and not room_records:
                QMessageBox.information(self, "No Data", "No records found for the selected filters.")

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to load history: {e.message}\n{e.details}")
        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"Error: {e}\n{traceback.format_exc()}")

    def handle_edit_selected_record(self):
        selected_items = self.main_history_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a record to edit.")
            return
        selected_row = selected_items[0].row()
        first_item_in_row = self.main_history_table.item(selected_row, 0)
        if not first_item_in_row: return
        record_id = first_item_in_row.data(Qt.UserRole)
        if record_id:
            if self.main_window.load_history_source_combo.currentText() == "Load from Cloud":
                self.handle_edit_record(record_id)
            else:
                QMessageBox.information(self, "Not Supported", "Editing CSV records directly is not supported here.")
        else:
            QMessageBox.warning(self, "No Record ID", "Record ID not found for selection.")

    def handle_delete_selected_record(self):
        selected_items = self.main_history_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a record to delete.")
            return
        selected_row = selected_items[0].row()
        first_item_in_row = self.main_history_table.item(selected_row, 0)
        if not first_item_in_row: return
        record_id = first_item_in_row.data(Qt.UserRole)
        if record_id:
            if self.main_window.load_history_source_combo.currentText() == "Load from Cloud":
                self.handle_delete_record(record_id)
            else:
                QMessageBox.information(self, "Not Supported", "Deleting CSV records directly is not supported here.")
        else:
            QMessageBox.warning(self, "No Record ID", "Record ID not found for selection.")

    def handle_edit_record(self, record_id): # Actual logic for editing
        if not self.main_window.supabase or not self.main_window.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return
        try:
            response = self.main_window.supabase.table("main_calculations") \
                           .select("*, room_calculations(*)") \
                           .eq("id", record_id).maybe_single().execute()
            if response.data:
                dialog = EditRecordDialog(record_id, response.data, response.data.get("room_calculations", []), parent=self)
                if dialog.exec_() == QDialog.Accepted: self.load_history()
            else: QMessageBox.warning(self, "Not Found", f"Record ID {record_id} not found.")
        except Exception as e: QMessageBox.critical(self, "Error", f"Error fetching record: {e}")

    def handle_delete_record(self, record_id): # Actual logic for deleting
        if not self.main_window.supabase or not self.main_window.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return
        reply = QMessageBox.question(self, 'Confirm Delete', "Are you sure you want to delete this record?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                # Delete associated room_calculations first (or rely on ON DELETE CASCADE if defined in DB)
                # For robustness, explicitly deleting room calculations first is safer if CASCADE isn't guaranteed.
                self.main_window.supabase.table("room_calculations").delete().eq("main_calculation_id", record_id).execute()
                self.main_window.supabase.table("main_calculations").delete().eq("id", record_id).execute()
                QMessageBox.information(self, "Success", "Record deleted successfully.")
                self.load_history() # Refresh the table
            except APIError as e:
                QMessageBox.critical(self, "Supabase API Error", f"Failed to delete: {e.message}\n{e.details}")
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"Error: {e}\n{traceback.format_exc()}")

    def calculate_and_display_totals(self, room_rows, get_csv_value):
        """Calculate and display totals for house rent, water bill, gas bill, and unit bill"""
        try:
            total_house_rent = 0.0
            total_water_bill = 0.0
            total_gas_bill = 0.0
            total_unit_bill = 0.0
            
            # The CSV structure has pre-calculated totals in the main calculation rows
            # We need to extract these from the main rows, not calculate from individual rooms
            processed_main_rows = set()  # To avoid double counting
            
            for room_row in room_rows:
                # Check if this row has totals data (main calculation row)
                csv_total_house_rent = get_csv_value(room_row, "Total House Rent", "")
                csv_total_water_bill = get_csv_value(room_row, "Total Water Bill", "")
                csv_total_gas_bill = get_csv_value(room_row, "Total Gas Bill", "")
                csv_total_unit_bill = get_csv_value(room_row, "Total Room Unit Bill", "")
                
                # If this row has totals data and we haven't processed it yet
                if csv_total_house_rent and csv_total_house_rent.strip():
                    # Create a unique identifier for this main row to avoid duplicates
                    month_val = get_csv_value(room_row, "Month", "")
                    meter1_val = get_csv_value(room_row, "Meter-1", "")
                    row_id = f"{month_val}_{meter1_val}"
                    
                    if row_id not in processed_main_rows:
                        processed_main_rows.add(row_id)
                        
                        # Add the pre-calculated totals from this main row
                        try:
                            total_house_rent += float(csv_total_house_rent or "0")
                            total_water_bill += float(csv_total_water_bill or "0")
                            total_gas_bill += float(csv_total_gas_bill or "0")
                            total_unit_bill += float(csv_total_unit_bill or "0")
                        except (ValueError, TypeError):
                            # If conversion fails, skip this row
                            continue
            
            # Clear existing totals and add new row
            self.totals_table.setRowCount(1)
            self.totals_table.setItem(0, 0, QTableWidgetItem(f"{total_house_rent:.2f}"))
            self.totals_table.setItem(0, 1, QTableWidgetItem(f"{total_water_bill:.2f}"))
            self.totals_table.setItem(0, 2, QTableWidgetItem(f"{total_gas_bill:.2f}"))
            self.totals_table.setItem(0, 3, QTableWidgetItem(f"{total_unit_bill:.2f}"))
            
        except Exception as e:
            # If there's an error calculating totals, just clear the table
            self.totals_table.setRowCount(0)
            print(f"Error calculating totals: {e}")

    def calculate_and_display_totals_from_main_rows(self, filtered_main_rows, get_csv_value):
        """Calculate and display totals from filtered main calculation rows"""
        try:
            # Clear existing totals
            self.totals_table.setRowCount(0)
            
            if not filtered_main_rows:
                return
            
            # Set the number of rows to match the number of filtered main rows
            self.totals_table.setRowCount(len(filtered_main_rows))
            
            # Add totals for each main calculation row
            for row_idx, main_row_data in enumerate(filtered_main_rows):
                row = main_row_data['csv_row']
                
                # Set the month/year in the first column
                month_year_str = f"{main_row_data['month']} {main_row_data['year']}"
                self.totals_table.setItem(row_idx, 0, QTableWidgetItem(month_year_str))
                
                # Extract pre-calculated totals from the main calculation row
                csv_total_house_rent = get_csv_value(row, "Total House Rent", "0")
                csv_total_water_bill = get_csv_value(row, "Total Water Bill", "0")
                csv_total_gas_bill = get_csv_value(row, "Total Gas Bill", "0")
                csv_total_unit_bill = get_csv_value(row, "Total Room Unit Bill", "0")
                
                # Set the totals for this row (shifted by 1 column due to month column)
                try:
                    house_rent = float(csv_total_house_rent or "0")
                    water_bill = float(csv_total_water_bill or "0")
                    gas_bill = float(csv_total_gas_bill or "0")
                    unit_bill = float(csv_total_unit_bill or "0")
                    
                    self.totals_table.setItem(row_idx, 1, QTableWidgetItem(f"{house_rent:.2f}"))
                    self.totals_table.setItem(row_idx, 2, QTableWidgetItem(f"{water_bill:.2f}"))
                    self.totals_table.setItem(row_idx, 3, QTableWidgetItem(f"{gas_bill:.2f}"))
                    self.totals_table.setItem(row_idx, 4, QTableWidgetItem(f"{unit_bill:.2f}"))
                except (ValueError, TypeError):
                    # If conversion fails, set zeros for this row
                    self.totals_table.setItem(row_idx, 1, QTableWidgetItem("0.00"))
                    self.totals_table.setItem(row_idx, 2, QTableWidgetItem("0.00"))
                    self.totals_table.setItem(row_idx, 3, QTableWidgetItem("0.00"))
                    self.totals_table.setItem(row_idx, 4, QTableWidgetItem("0.00"))
            
        except Exception as e:
            # If there's an error calculating totals, just clear the table
            self.totals_table.setRowCount(0)
            print(f"Error calculating totals from main rows: {e}")

    def calculate_and_display_totals_supabase(self, room_records):
        """Calculate and display totals for Supabase room records"""
        try:
            total_house_rent = 0.0
            total_water_bill = 0.0
            total_gas_bill = 0.0
            total_unit_bill = 0.0
            
            for record in room_records:
                # Get values from Supabase records, defaulting to 0 if not found or None
                # Note: Supabase data structure might be different from CSV
                # For now, we'll use cost_room as unit_bill since that's what's available
                house_rent = float(record.get("house_rent", 0) or 0)
                water_bill = float(record.get("water_bill", 0) or 0)
                gas_bill = float(record.get("gas_bill", 0) or 0)
                unit_bill = float(record.get("cost_room", 0) or 0)  # Using cost_room as unit bill
                
                total_house_rent += house_rent
                total_water_bill += water_bill
                total_gas_bill += gas_bill
                total_unit_bill += unit_bill
            
            # Clear existing totals and add new row
            self.totals_table.setRowCount(1)
            self.totals_table.setItem(0, 0, QTableWidgetItem(f"{total_house_rent:.2f}"))
            self.totals_table.setItem(0, 1, QTableWidgetItem(f"{total_water_bill:.2f}"))
            self.totals_table.setItem(0, 2, QTableWidgetItem(f"{total_gas_bill:.2f}"))
            self.totals_table.setItem(0, 3, QTableWidgetItem(f"{total_unit_bill:.2f}"))
            
        except Exception as e:
            # If there's an error calculating totals, just clear the table
            self.totals_table.setRowCount(0)
            print(f"Error calculating totals for Supabase data: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    class DummyMainWindow(QWidget): # Using QWidget for simplicity in dummy
        def __init__(self):
            super().__init__()
            self.load_history_source_combo = QComboBox()
            self.load_history_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
            self.supabase = None # Mock if needed
            self.check_internet_connectivity = lambda: True # Mock
            self.db_manager = None # Mock if needed

    dummy_main_window = DummyMainWindow()
    history_tab_widget = HistoryTab(dummy_main_window)
    history_tab_widget.setWindowTitle("HistoryTab Test")
    history_tab_widget.setGeometry(100, 100, 1000, 600)
    history_tab_widget.show()
    sys.exit(app.exec_())
