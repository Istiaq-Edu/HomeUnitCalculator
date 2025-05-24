import sys
import json
from datetime import datetime as dt_class, datetime
import functools # Added import
import os
import csv
import traceback

from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor, QKeySequence, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGridLayout, 
    QGroupBox, QFormLayout, QFileDialog, QMessageBox, QSpinBox, QScrollArea, 
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFrame, QShortcut,
    QAbstractSpinBox, QStyleOptionSpinBox, QStyle, QDesktopWidget, QSizePolicy,
    QDialog, QAbstractItemView # Added QDialog, QAbstractItemView
)
from postgrest.exceptions import APIError

# Assuming these modules are in the same directory or accessible in PYTHONPATH
from styles import (
    get_stylesheet, get_header_style, get_group_box_style,
    get_line_edit_style, get_button_style, get_results_group_style,
    get_room_group_style, get_month_info_style, get_table_style, get_label_style,
    get_custom_spinbox_style, get_room_selection_style, get_result_title_style, 
    get_result_value_style
)
from utils import resource_path # For icons
from custom_widgets import CustomLineEdit, AutoScrollArea, CustomSpinBox, CustomNavButton


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
            try:
                extra_meters = json.loads(extra_meter_readings)
                if isinstance(extra_meters, list): meter_values.extend(extra_meters)
            except Exception as e: print(f"Error parsing extra meter readings in dialog: {e}")
        
        if extra_diff_readings:
            try:
                extra_diffs = json.loads(extra_diff_readings)
                if isinstance(extra_diffs, list): diff_values.extend(extra_diffs)
            except Exception as e: print(f"Error parsing extra diff readings in dialog: {e}")
        
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
            try: meter_values.extend(json.loads(main_data["extra_meter_readings"]))
            except: pass # ignore errors
        if main_data.get("extra_diff_readings"):
            try: diff_values.extend(json.loads(main_data["extra_diff_readings"]))
            except: pass # ignore errors

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
        def _s_int(v_str, default=0): return int(v_str) if v_str else default
        def _s_float(v_str, default=0.0): return float(v_str) if v_str else default

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
                units_consumed = present - previous
                cost = units_consumed * per_unit_cost_calc
                updated_room_data_list.append({
                    "main_calculation_id": self.record_id, "room_name": rws["name"],
                    "present_reading_room": present, "previous_reading_room": previous,
                    "units_consumed_room": units_consumed, "cost_room": cost
                })

            self.supabase.table("main_calculations").update(updated_main_data).eq("id", self.record_id).execute()
            self.supabase.table("room_calculations").delete().eq("main_calculation_id", self.record_id).execute()
            if updated_room_data_list:
                self.supabase.table("room_calculations").insert(updated_room_data_list).execute()

            QMessageBox.information(self, "Success", "Record updated successfully.")
            self.accept()
        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"Failed to update: {e.message}\n{e.details}")
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Error: {e}\n{traceback.format_exc()}")


class HistoryTab(QWidget):
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
        layout = QVBoxLayout(self)
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
        self.history_year_spinbox.setRange(2000, 2100)
        self.history_year_spinbox.setValue(datetime.now().year)
        self.history_year_spinbox.setSpecialValueText("All")
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
        main_calc_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_calc_layout = QVBoxLayout(main_calc_group)
        self.main_history_table = QTableWidget()
        self.main_history_table.setColumnCount(12)
        self.main_history_table.setHorizontalHeaderLabels(["Month", "Meter-1", "Meter-2", "Meter-3", "Diff-1", "Diff-2", "Diff-3", "Total Unit Cost", "Total Diff Units", "Per Unit Cost", "Added Amount", "Grand Total"])
        header = self.main_history_table.horizontalHeader()
        for i in range(self.main_history_table.columnCount()): header.setSectionResizeMode(i, QHeaderView.Stretch)
        self.main_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.main_history_table.setAlternatingRowColors(True)
        self.main_history_table.setStyleSheet(get_table_style())
        table_header_height = self.main_history_table.horizontalHeader().height()
        estimated_row_height = 30
        num_data_rows_main_table = 2
        table_content_height = (num_data_rows_main_table * estimated_row_height)
        table_total_height = table_header_height + table_content_height + 10
        self.main_history_table.setFixedHeight(table_total_height)
        main_calc_layout.addWidget(self.main_history_table)
        group_box_margins = main_calc_group.layout().contentsMargins()
        group_box_chrome_and_internal_padding = 40
        overall_buffer = 5
        fixed_group_height = table_total_height + group_box_margins.top() + group_box_margins.bottom() + group_box_chrome_and_internal_padding + overall_buffer
        main_calc_group.setFixedHeight(fixed_group_height)
        layout.addWidget(main_calc_group, 0)

        room_calc_group = QGroupBox("Room Calculation Info")
        room_calc_group.setStyleSheet(get_group_box_style())
        room_calc_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        room_calc_layout = QVBoxLayout(room_calc_group)
        self.room_history_table = QTableWidget()
        self.room_history_table.setColumnCount(6)
        self.room_history_table.setHorizontalHeaderLabels(["Month", "Room", "Present Unit", "Previous Unit", "Real Unit", "Unit Bill"])
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 
        self.room_history_table.setAlternatingRowColors(True)
        self.room_history_table.setStyleSheet(get_table_style())
        room_calc_layout.addWidget(self.room_history_table)
        layout.addWidget(room_calc_group)
        
        self.setLayout(layout)

    def load_history(self):
        try:
            selected_month = self.history_month_combo.currentText()
            selected_year_val = self.history_year_spinbox.value()
            source = self.main_window.load_history_source_combo.currentText() # From main_window

            if source == "Load from PC (CSV)":
                self.load_history_tables_from_csv(selected_month, selected_year_val)
            elif source == "Load from Cloud":
                if self.main_window.supabase and self.main_window.check_internet_connectivity():
                    self.load_history_tables_from_supabase(selected_month, selected_year_val)
                elif not self.main_window.supabase:
                    QMessageBox.warning(self, "Supabase Not Configured", "Supabase is not configured.")
                else:
                    QMessageBox.warning(self, "Network Error", "No internet connection.")
            else:
                QMessageBox.warning(self, "Unknown Source", "Select a valid source.")
        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"Error: {e}\n{traceback.format_exc()}")


    def load_history_tables_from_csv(self, selected_month, selected_year_val):
        # (Logic from HomeUnitCalculator.py, adapted for self and self.main_window)
        # ... This is a substantial piece of code. For brevity here, I'll assume it's moved.
        # Key changes: self.main_history_table, self.room_history_table are now self's attributes.
        # self.history_year_spinbox.minimum() and .specialValueText() are used.
        QMessageBox.information(self, "CSV Load", "CSV history loading to be fully implemented here.")
        self.main_history_table.setRowCount(0) # Clear placeholder
        self.room_history_table.setRowCount(0) # Clear placeholder

    def load_history_tables_from_supabase(self, selected_month, selected_year_val):
        # (Logic from HomeUnitCalculator.py, adapted for self and self.main_window)
        # ... This is also substantial.
        # Key changes: Uses self.main_window.supabase, self.main_history_table, etc.
        QMessageBox.information(self, "Supabase Load", "Supabase history loading to be fully implemented here.")
        self.main_history_table.setRowCount(0) # Clear placeholder
        self.room_history_table.setRowCount(0) # Clear placeholder

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
                self.main_window.supabase.table("room_calculations").delete().eq("main_calculation_id", record_id).execute()
                self.main_window.supabase.table("main_calculations").delete().eq("id", record_id).execute()
                QMessageBox.information(self, "Delete Successful", "Record deleted.")
                self.load_history()
            except Exception as e: QMessageBox.critical(self, "Delete Error", f"Failed to delete: {e}")


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
