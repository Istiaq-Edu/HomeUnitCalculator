import sys
import json
import contextlib
import os
import csv
import traceback
from datetime import datetime

from PyQt5.QtCore import Qt, QRegExp, QSize
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QDialog, QAbstractItemView, QFrame
)
from postgrest.exceptions import APIError
from qfluentwidgets import (
    CardWidget, ComboBox, SpinBox, PrimaryPushButton, PushButton,
    TitleLabel, BodyLabel, CaptionLabel, TableWidget, FluentIcon,
    DropDownPushButton, RoundMenu, Action
)

# Ensure project root (containing 'src') is on sys.path when running this file standalone
try:
    from src.core.utils import resource_path  # For icons
    from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomNavButton
except ModuleNotFoundError:
    import pathlib, sys as _sys
    # Add two levels up (project root) to sys.path
    _project_root = pathlib.Path(__file__).resolve().parents[2]
    if str(_project_root) not in _sys.path:
        _sys.path.append(str(_project_root))
    from src.core.utils import resource_path
    from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea, CustomNavButton


# Dialog for Editing Records (Moved from HomeUnitCalculator.py)
class EditRecordDialog(QDialog):
    def __init__(self, record_id, main_data, room_data_list, parent=None): # parent is the HistoryTab instance
        super().__init__(parent)
        self.record_id = record_id 
        self.main_window = parent.main_window # Access main_window through HistoryTab's parent
        self.supabase_manager = self.main_window.supabase_manager # Get supabase manager from main_window
        self.room_edit_widgets = [] 
        self.meter_diff_edit_widgets = [] 
        
        self.setWindowTitle("Edit Calculation Record")
        self.setMinimumWidth(600) 
        self.setMinimumHeight(500)

        main_layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()

        self.month_year_label = TitleLabel(f"Record for: {main_data.get('month', '')} {main_data.get('year', '')}")
        main_layout.addWidget(self.month_year_label)

        main_group = CardWidget()
        main_group_vbox = QVBoxLayout(main_group)
        main_group_vbox.addWidget(TitleLabel("Main Calculation Data"))
        main_scroll_area = AutoScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_widget = QWidget()
        main_group_layout = QFormLayout(main_scroll_widget)
        main_group_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        main_scroll_area.setWidget(main_scroll_widget)
        main_group_vbox.addWidget(main_scroll_area)
        
        self.meter1_edit = CustomLineEdit(); self.meter1_edit.setObjectName("dialog_meter1_edit")
        self.meter2_edit = CustomLineEdit(); self.meter2_edit.setObjectName("dialog_meter2_edit")
        self.meter3_edit = CustomLineEdit(); self.meter3_edit.setObjectName("dialog_meter3_edit")
        self.diff1_edit = CustomLineEdit(); self.diff1_edit.setObjectName("dialog_diff1_edit")
        self.diff2_edit = CustomLineEdit(); self.diff2_edit.setObjectName("dialog_diff2_edit")
        self.diff3_edit = CustomLineEdit(); self.diff3_edit.setObjectName("dialog_diff3_edit")
        
        # Extract data from main_data JSONB structure
        meter_values = main_data.get("meter_readings", [])
        diff_values = main_data.get("diff_readings", [])
        
        # Ensure at least 3 pairs for backward compatibility or if extra readings make it longer.
        num_pairs = max(3, len(meter_values), len(diff_values))
        
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

        self.rooms_group = CardWidget()
        rooms_main_layout = QVBoxLayout(self.rooms_group)
        rooms_main_layout.addWidget(TitleLabel("Room Data"))
        scroll_area_rooms = AutoScrollArea() # Renamed to avoid conflict if self.scroll_area is used elsewhere
        scroll_area_rooms.setWidgetResizable(True)
        scroll_content_widget = QWidget()
        self.rooms_edit_layout = QVBoxLayout(scroll_content_widget)
        scroll_area_rooms.setWidget(scroll_content_widget)
        rooms_main_layout.addWidget(scroll_area_rooms)

        # Store original month/year for update
        self.original_month = main_data.get('month')
        self.original_year = main_data.get('year')

        for i, room_data in enumerate(room_data_list):
            # Handle nested room_data dict returned from SupabaseManager
            nested = room_data.get('room_data') if isinstance(room_data, dict) else None
            rd = nested if isinstance(nested, dict) else room_data
            room_name = rd.get('room_name', 'Unknown Room')
            room_edit_group = CardWidget()
            room_edit_main_layout = QVBoxLayout(room_edit_group)
            room_edit_main_layout.addWidget(TitleLabel(room_name))
            form_widget = QWidget()
            room_edit_form_layout = QFormLayout(form_widget)
            room_edit_main_layout.addWidget(form_widget)
            room_edit_form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

            present_edit = CustomLineEdit()
            present_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_present")
            previous_edit = CustomLineEdit()
            previous_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_previous")
            room_id = room_data.get('id') 

            gas_bill_edit = CustomLineEdit()
            gas_bill_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_gas")
            water_bill_edit = CustomLineEdit()
            water_bill_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_water")
            house_rent_edit = CustomLineEdit()
            house_rent_edit.setObjectName(f"dialog_room_{room_data.get('id', i)}_rent")

            room_edit_form_layout.addRow("Present Reading:", present_edit)
            room_edit_form_layout.addRow("Previous Reading:", previous_edit)
            room_edit_form_layout.addRow("Gas Bill:", gas_bill_edit)
            room_edit_form_layout.addRow("Water Bill:", water_bill_edit)
            room_edit_form_layout.addRow("House Rent:", house_rent_edit)

            self.rooms_edit_layout.addWidget(room_edit_group)
            self.room_edit_widgets.append({
                "room_id": room_id, "name": room_name,
                "present_edit": present_edit, "previous_edit": previous_edit,
                "gas_edit": gas_bill_edit, "water_edit": water_bill_edit,
                "rent_edit": house_rent_edit
            })
            
        if not room_data_list:
             no_rooms_label = QLabel("No room data associated with this record.")
             self.rooms_edit_layout.addWidget(no_rooms_label)
        main_layout.addWidget(self.rooms_group)

        self.save_button = PrimaryPushButton(FluentIcon.SAVE, "Save Changes")
        self.cancel_button = PushButton(FluentIcon.CANCEL, "Cancel")

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        main_layout.addLayout(button_layout)

        self.populate_data(main_data, room_data_list)
        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.reject)
        self._setup_navigation_edit_dialog()

    def _setup_navigation_edit_dialog(self):
        save_btn = self.save_button

        # ----------------- gather editable widgets -----------------
        meter_diff_seq: list[CustomLineEdit] = []
        for pair in self.meter_diff_edit_widgets:
            meter_diff_seq.extend([pair['meter_edit'], pair['diff_edit']])

        aa = self.additional_amount_edit

        room_seq: list[CustomLineEdit] = []
        for room_set in self.room_edit_widgets:
            room_seq.extend([
                room_set["present_edit"],
                room_set["previous_edit"],
                room_set["gas_edit"],
                room_set["water_edit"],
                room_set["rent_edit"],
            ])

        enter_sequence = meter_diff_seq + [aa] + room_seq

        # Ensure every widget starts with a clean slate
        for w in enter_sequence:
            for attr in ("next_widget_on_enter", "up_widget", "down_widget", "left_widget", "right_widget"):
                setattr(w, attr, None)

        if isinstance(save_btn, CustomNavButton):
            save_btn.next_widget_on_enter = None

        # ----------------- Enter key mapping -----------------
        for idx, w in enumerate(enter_sequence):
            w.next_widget_on_enter = enter_sequence[idx + 1] if idx < len(enter_sequence) - 1 else save_btn

        if isinstance(save_btn, CustomNavButton):
            save_btn.next_widget_on_enter = enter_sequence[0]

        # ----------------- Up/Down arrow mapping -----------------
        length = len(enter_sequence)
        for idx, w in enumerate(enter_sequence):
            w.down_widget = enter_sequence[(idx + 1) % length]
            w.up_widget   = enter_sequence[(idx - 1 + length) % length]

        # ----------------- initial focus -----------------
        if enter_sequence:
            enter_sequence[0].setFocus()

    def populate_data(self, main_data, room_data_list):
        # Extract data from main_data JSONB structure
        meter_values = main_data.get("meter_readings", [])
        diff_values = main_data.get("diff_readings", [])

        for i, pair_widgets in enumerate(self.meter_diff_edit_widgets):
            if i < len(meter_values) and pair_widgets['meter_edit']: pair_widgets['meter_edit'].setText(str(meter_values[i]))
            if i < len(diff_values) and pair_widgets['diff_edit']: pair_widgets['diff_edit'].setText(str(diff_values[i]))
                
        # Support both new and legacy key names
        aa_val = main_data.get("added_amount") if "added_amount" in main_data else main_data.get("additional_amount", "")
        self.additional_amount_edit.setText(str(aa_val or ""))
        
        for i, room_widget_set in enumerate(self.room_edit_widgets):
            if i < len(room_data_list):
                room_record = room_data_list[i]
                # Extract data from room_data JSONB structure
                room_data_jsonb = room_record.get("room_data", {})
                room_widget_set["present_edit"].setText(str(room_data_jsonb.get("present_unit", "") or ""))
                room_widget_set["previous_edit"].setText(str(room_data_jsonb.get("previous_unit", "") or ""))
                room_widget_set["gas_edit"].setText(str(room_data_jsonb.get("gas_bill", "") or ""))
                room_widget_set["water_edit"].setText(str(room_data_jsonb.get("water_bill", "") or ""))
                room_widget_set["rent_edit"].setText(str(room_data_jsonb.get("house_rent", "") or ""))
                # Store entire original room_data for later preservation
                room_widget_set["original_room_data"] = room_data_jsonb
                # Store image paths for later use in save_changes
                room_widget_set["photo_path"] = room_record.get("photo_url")
                room_widget_set["nid_front_path"] = room_record.get("nid_front_url")
                room_widget_set["nid_back_path"] = room_record.get("nid_back_url")
                room_widget_set["police_form_path"] = room_record.get("police_form_url")

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

            # Prepare main_data for JSONB column with keys matching HistoryTab expectations
            updated_main_data_jsonb = {
                "month": self.original_month,
                "year": self.original_year,
                "meter_readings": meter_vals,
                "diff_readings": diff_vals,
            }

            for idx, val in enumerate(meter_vals):
                updated_main_data_jsonb[f"meter_{idx+1}"] = val
            for idx, val in enumerate(diff_vals):
                updated_main_data_jsonb[f"diff_{idx+1}"] = val

            updated_main_data_jsonb.update({
                "total_unit_cost": total_unit_cost,
                "total_diff_units": total_diff_units,
                "per_unit_cost": per_unit_cost_calc,
                "added_amount": additional_amount,
                "grand_total": grand_total_bill,
            })

            updated_room_records_for_supabase = []
            for rws in self.room_edit_widgets:
                present = _s_float(rws["present_edit"].text()) # Use _s_float for consistency
                previous = _s_float(rws["previous_edit"].text()) # Use _s_float for consistency
                if present < previous:
                    QMessageBox.warning(self, "Input Error",
                                        f"Present reading ({present}) cannot be less than previous reading "
                                        f"({previous}) for room '{rws['name']}'.")
                    return # Do not proceed with saving if validation fails
                units_consumed = present - previous
                cost = units_consumed * per_unit_cost_calc
                gas_bill_val = _s_float(rws["gas_edit"].text(), default=0.0)
                water_bill_val = _s_float(rws["water_edit"].text(), default=0.0)
                rent_val = _s_float(rws["rent_edit"].text(), default=0.0)
                grand_total_room = cost + gas_bill_val + water_bill_val + rent_val
                
                # Start from original room_data to preserve non-edited fields
                room_data_jsonb = dict(rws.get("original_room_data", {}))
                room_data_jsonb.update({
                    "room_name": rws["name"],
                    "present_unit": present,
                    "previous_unit": previous,
                    "real_unit": units_consumed,
                    "unit_bill": cost,
                    "gas_bill": gas_bill_val,
                    "water_bill": water_bill_val,
                    "house_rent": rent_val,
                    "grand_total": grand_total_room,
                })

                # Include local image paths (which are actually URLs from Supabase Storage)
                # SupabaseManager will handle re-upload if paths change, or keep existing if same.
                room_record_to_save = {
                    "room_data": room_data_jsonb,
                    "photo_path": rws.get("photo_path"),
                    "nid_front_path": rws.get("nid_front_path"),
                    "nid_back_path": rws.get("nid_back_path"),
                    "police_form_path": rws.get("police_form_path")
                }
                
                # If this is an existing room record, include its ID
                if rws.get("room_id"):
                    room_record_to_save["id"] = rws["room_id"]
                
                updated_room_records_for_supabase.append(room_record_to_save)

            # Update main_calculations using SupabaseManager
            main_update_success = self.supabase_manager.save_main_calculation(updated_main_data_jsonb)
            
            if not main_update_success:
                QMessageBox.critical(self, "Supabase Error", "Failed to update main calculation data.")
                return

            # Save room calculations using SupabaseManager
            if updated_room_records_for_supabase:
                rooms_update_success = self.supabase_manager.save_room_calculations(
                    self.record_id, updated_room_records_for_supabase
                )
                if not rooms_update_success:
                    QMessageBox.critical(self, "Supabase Error", "Failed to update room calculation data.")
                    return

            QMessageBox.information(self, "Success", "Record updated successfully.")
            self.accept() # Close dialog on success
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"An unexpected error occurred during update: {e}\n{traceback.format_exc()}")


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

        # Combined "Load Records" group (Month/Year/Source/Load)
        load_records_group = CardWidget()
        lr_outer = QVBoxLayout(load_records_group)
        lr_outer.setContentsMargins(8,8,8,8)
        title = TitleLabel("Load Records")
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet("font-weight:bold;")
        lr_outer.addWidget(title)
        header_line = QFrame()
        header_line.setFrameShape(QFrame.HLine)
        header_line.setStyleSheet("border-top:1px solid #666; margin-bottom:6px;")
        lr_outer.addWidget(header_line)
        lr_layout = QHBoxLayout()
        lr_layout.setContentsMargins(8,6,8,6)
        lr_layout.setSpacing(10)
        lr_layout.addStretch(1)
        lr_layout.addWidget(BodyLabel("Month:"))
        self.history_month_combo = ComboBox()
        self.history_month_combo.addItems(["All","January","February","March","April","May","June","July","August","September","October","November","December"])
        lr_layout.addWidget(self.history_month_combo)
        lr_layout.addSpacing(10)
        lr_layout.addWidget(BodyLabel("Year:"))
        self.history_year_spinbox = SpinBox()
        self.history_year_spinbox.setRange(0,2100)
        self.history_year_spinbox.setSpecialValueText("All")
        self.history_year_spinbox.setValue(datetime.now().year)
        lr_layout.addWidget(self.history_year_spinbox)
        lr_layout.addSpacing(10)
        # Use Fluent DropDownPushButton instead of plain ComboBox
        self.main_window.load_history_source_combo.setVisible(False)
        self.load_history_source_button = DropDownPushButton(FluentIcon.DOCUMENT, "Load from CSV")
        self.load_history_source_button.setFixedWidth(190)
        menu = RoundMenu(parent=self.load_history_source_button)
        def _set_source(text, icon, label):
            self.main_window.load_history_source_combo.setCurrentText(text)
            self.load_history_source_button.setIcon(icon)
            self.load_history_source_button.setText(label)
        menu.addAction(Action(FluentIcon.DOCUMENT, "Load from CSV", triggered=lambda: _set_source("Load from PC (CSV)", FluentIcon.DOCUMENT.icon(), "Load from CSV")))
        menu.addAction(Action(FluentIcon.CLOUD, "Load from Cloud", triggered=lambda: _set_source("Load from Cloud", FluentIcon.CLOUD.icon(), "Load from Cloud")))
        self.load_history_source_button.setMenu(menu)
        lr_layout.addWidget(self.load_history_source_button)
        load_history_button = PrimaryPushButton(FluentIcon.DOWNLOAD, "Load")
        load_history_button.clicked.connect(self.load_history)
        load_history_button.setFixedHeight(40)
        lr_layout.addWidget(load_history_button)
        lr_layout.addStretch(1)
        controls_card = CardWidget()
        controls_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        controls_card.setLayout(lr_layout)
        lr_outer.addWidget(controls_card)
        top_layout.addWidget(load_records_group, 3)

        # Record Actions titled group
        record_actions_group = CardWidget()
        ra_outer = QVBoxLayout(record_actions_group)
        ra_outer.setContentsMargins(8,8,8,8)
        ra_outer.setSpacing(4)
        ra_title = TitleLabel("Record Actions")
        ra_title.setAlignment(Qt.AlignHCenter)
        ra_title.setStyleSheet("font-weight:bold;")
        ra_outer.addWidget(ra_title)
        ra_line = QFrame()
        ra_line.setFrameShape(QFrame.HLine)
        ra_line.setStyleSheet("border-top:1px solid #666; margin-bottom:6px;")
        ra_outer.addWidget(ra_line)
        record_actions_layout = QHBoxLayout()
        record_actions_layout.setContentsMargins(8,6,8,6)
        record_actions_layout.setSpacing(40)
        # Add stretch on both sides for perfect centering
        record_actions_layout.addStretch(1)
        self.edit_selected_record_button = PrimaryPushButton(FluentIcon.EDIT, "Edit Record")
        self.edit_selected_record_button.setMinimumWidth(150)
        self.edit_selected_record_button.setStyleSheet("QPushButton{background-color:#2e7d32;color:white;padding:6px 24px 6px 52px;border-radius:4px;}QPushButton:hover{background-color:#388e3c;}QPushButton:pressed{background-color:#1b5e20;}QPushButton:disabled{background-color:#3d3d3d;color:#777;}")
        self.edit_selected_record_button.setFixedHeight(40)
        self.edit_selected_record_button.clicked.connect(self.handle_edit_selected_record)
        self.delete_selected_record_button = PrimaryPushButton(FluentIcon.DELETE, "Delete Record")
        self.delete_selected_record_button.setMinimumWidth(160)
        self.delete_selected_record_button.setStyleSheet("QPushButton{background-color:#c62828;color:white;padding:6px 24px 6px 52px;border-radius:4px;}QPushButton:hover{background-color:#d84315;}QPushButton:pressed{background-color:#b71c1c;}QPushButton:disabled{background-color:#3d3d3d;color:#777;}")
        self.delete_selected_record_button.setFixedHeight(40)
        self.delete_selected_record_button.clicked.connect(self.handle_delete_selected_record)
        # Initially disabled until a row is selected
        self.edit_selected_record_button.setEnabled(False)
        self.delete_selected_record_button.setEnabled(False)
        record_actions_layout.addWidget(self.edit_selected_record_button)
        record_actions_layout.addWidget(self.delete_selected_record_button)
        record_actions_layout.addStretch(1)
        # Wrap in card
        controls_actions_card = CardWidget()
        
        controls_actions_card.setLayout(record_actions_layout)
        ra_outer.addWidget(controls_actions_card)
        top_layout.addWidget(record_actions_group, 3)
        layout.addLayout(top_layout)

        main_calc_group = CardWidget()
        main_calc_layout = QVBoxLayout(main_calc_group)
        main_title = TitleLabel("Main Calculation Info")
        main_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_title.setWordWrap(True)
        main_calc_layout.addWidget(main_title)
        self.main_history_table = TableWidget()
        # (moved block above to add connections) -- placeholder to satisfy exact replacement
        # Enable horizontal scrollbar for main table if content exceeds width
        self.main_history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Vertical scrolling handled by main scroll area
        self.main_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.main_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.main_history_table.setAlternatingRowColors(True)
        # Initially set columns to minimum required, will update dynamically on data load
        self.set_main_history_table_columns(3)  # default 3 meters/diffs
        # Remove all height restrictions and let table grow naturally
        self.main_history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Resize table to content height and adjust table height to show all rows
        self.main_history_table.resizeRowsToContents()
        self.resize_table_to_content(self.main_history_table)
        self._style_table(self.main_history_table)
        main_calc_layout.addWidget(self.main_history_table)
        layout.addWidget(main_calc_group)  # No stretch factor - let it size naturally

        room_calc_group = CardWidget()
        room_calc_layout = QVBoxLayout(room_calc_group)
        room_title = TitleLabel("Room Calculation Info")
        room_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        room_title.setWordWrap(True)
        room_calc_layout.addWidget(room_title)
        self.room_history_table = TableWidget()
        # (moved block above to add connections) -- placeholder to satisfy exact replacement
        self.room_history_table.setColumnCount(10)
        self.room_history_table.setHorizontalHeaderLabels([
            "Month", "Room Number", "Present Unit", "Previous Unit", "Real Unit", 
            "Unit Bill", "Gas Bill", "Water Bill", "House Rent", "Grand Total"
        ])
        # Allow interactive resizing and horizontal scrolling for room table
        self.room_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) 
        self.room_history_table.setAlternatingRowColors(True)
        # Enable horizontal scrollbar for room table if content exceeds width
        self.room_history_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.room_history_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Vertical scrolling handled by main scroll area
        self.room_history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.room_history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        # Remove all height restrictions and let table grow naturally
        self.room_history_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Resize table to content height and adjust table height to show all rows
        self.room_history_table.resizeRowsToContents()
        self._style_table(self.room_history_table)
        # Connect selection changed signals to update button states/styles now that tables exist
        self.main_history_table.itemSelectionChanged.connect(self.update_action_buttons_state)
        self.room_history_table.itemSelectionChanged.connect(self.update_action_buttons_state)
        # Ensure initial button style state
        self.update_action_buttons_state()
        self.resize_table_to_content(self.room_history_table)
        room_calc_layout.addWidget(self.room_history_table)
        layout.addWidget(room_calc_group)  # No stretch factor - let it size naturally

        # Add new totals section
        totals_group = CardWidget()
        totals_layout = QVBoxLayout(totals_group)
        totals_title = TitleLabel("Total Summary")
        totals_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        totals_title.setWordWrap(True)
        totals_layout.addWidget(totals_title)
        self.totals_table = TableWidget()
        self.totals_table.setColumnCount(5)
        self.totals_table.setHorizontalHeaderLabels([
            "Month", "Total House Rent", "Total Water Bill", "Total Gas Bill", "Total Room Unit Bill"
        ])
        self.totals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.totals_table.setAlternatingRowColors(True)
        # Remove all height restrictions and let table grow naturally
        self.totals_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # Disable scrollbars for totals table since we're using full page scrolling
        self.totals_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.totals_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Resize table to content height and adjust table height to show all rows
        self.totals_table.resizeRowsToContents()
        self.resize_table_to_content(self.totals_table)
        self._style_table(self.totals_table)
        totals_layout.addWidget(self.totals_table)
        layout.addWidget(totals_group)  # No stretch factor - let it size naturally
        
        # Set the content widget to the scroll area and add scroll area to main layout
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def _style_table(self, table: TableWidget):
        """Apply qfluentwidgets-compatible styling with enhanced visual design"""
        from qfluentwidgets import setCustomStyleSheet
        
        # Configure basic table properties
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setHighlightSections(False)
        table.setBorderVisible(True)
        table.setBorderRadius(8)
        table.setAlternatingRowColors(True)
        
        header = table.horizontalHeader()
        if hasattr(header, "setTextElideMode"):
            header.setTextElideMode(Qt.ElideNone)
        
        # Set enhanced row height for better readability
        table.verticalHeader().setDefaultSectionSize(40)
        
        # Apply custom qfluentwidgets-compatible styling
        light_qss = """
            QTableWidget {
                background-color: #fafafa;
                color: #212121;
                gridline-color: #e0e0e0;
                selection-background-color: #1976d2;
                alternate-background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-weight: 500;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #424242;
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                padding: 12px 16px;
                text-align: center;
            }
            QTableWidget::item {
                padding: 10px 14px;
                border: none;
                text-align: center;
                font-weight: 500;
            }
            QTableWidget::item:selected {
                background-color: #1976d2;
                color: white;
                font-weight: 600;
            }
            QTableWidget::item:hover {
                background-color: #e3f2fd;
            }
        """
        
        dark_qss = """
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #444444;
                selection-background-color: #1976d2;
                alternate-background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                font-weight: 500;
            }
            QHeaderView::section {
                background-color: #1f1f1f;
                color: #e0e0e0;
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #444444;
                padding: 12px 16px;
                text-align: center;
            }
            QTableWidget::item {
                padding: 10px 14px;
                border: none;
                text-align: center;
                font-weight: 500;
            }
            QTableWidget::item:selected {
                background-color: #1976d2;
                color: white;
                font-weight: 600;
            }
            QTableWidget::item:hover {
                background-color: #263045;
            }
        """
        
        # Apply theme-aware styling using qfluentwidgets method
        setCustomStyleSheet(table, light_qss, dark_qss)
        
        table.setSortingEnabled(True)
        
        # Set column resize mode to stretch for responsive design
        for col in range(table.columnCount()):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        table.horizontalHeader().setMinimumSectionSize(80)
        
        # Apply center alignment and styling to all cells
        self._apply_center_alignment(table)
        self._apply_accent_colors(table)
        
        # Center header text
        table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)

    def _apply_center_alignment(self, table: TableWidget):
        """Apply center alignment to all table cells"""
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    
    def _create_centered_item(self, text: str) -> QTableWidgetItem:
        """Create a table widget item with center alignment and modern styling"""
        from PyQt5.QtGui import QColor, QBrush, QFont
        from qfluentwidgets import isDarkTheme
        
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Apply modern semi-bold styling to numeric content
        if self._is_numeric_text(str(text)):
            font = item.font()
            font.setWeight(QFont.DemiBold)  # Semi-bold for modern look
            font.setPointSizeF(font.pointSizeF() + 0.5)
            item.setFont(font)
            
            # Theme-aware subtle color enhancement for numbers
            if isDarkTheme():
                item.setForeground(QBrush(QColor("#B3E5FC")))  # Light blue for dark theme
            else:
                item.setForeground(QBrush(QColor("#1565C0")))  # Dark blue for light theme
        
        return item
    
    def _create_special_item(self, text: str, column_type: str) -> QTableWidgetItem:
        """Create a styled item for special columns with enhanced Material Design colors"""
        from PyQt5.QtGui import QColor, QBrush, QFont
        from qfluentwidgets import isDarkTheme
        
        # Enhanced color mapping with theme awareness
        if isDarkTheme():
            color_map = {
                "grand_total": "#66BB6A",       # Light Green for dark theme
                "unit_bill": "#FF7043",         # Light Deep Orange 
                "total_unit_cost": "#AB47BC",   # Light Purple
                "per_unit_cost": "#FFA726",     # Light Orange
            }
        else:
            color_map = {
                "grand_total": "#2E7D32",       # Dark Green for light theme
                "unit_bill": "#D84315",         # Dark Deep Orange 
                "total_unit_cost": "#7B1FA2",   # Dark Purple
                "per_unit_cost": "#EF6C00",     # Dark Orange
            }
        
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        
        # Apply enhanced styling for special columns
        color = color_map.get(column_type, "#1976D2")  # Default Material Blue
        item.setForeground(QBrush(QColor(color)))
        
        # Modern typography - bold with better readability
        font = item.font()
        font.setBold(True)
        font.setWeight(QFont.Bold)
        font.setPointSizeF(font.pointSizeF() + 2)  # Larger for emphasis
        item.setFont(font)
        
        return item
                    
    def _apply_accent_colors(self, table: TableWidget):
        """Apply subtle styling enhancements to table (styling is now handled by create methods)"""
        # This method is now primarily for applying any additional table-wide styling
        # Individual cell styling is handled by _create_centered_item and _create_special_item
        pass
    
    def _is_numeric_column(self, header_text: str) -> bool:
        """Check if a column header indicates numeric content"""
        numeric_indicators = [
            "meter", "diff", "unit", "cost", "bill", "rent", "amount", "total", "reading"
        ]
        header_lower = header_text.lower()
        return any(indicator in header_lower for indicator in numeric_indicators)
    
    def _is_numeric_text(self, text: str) -> bool:
        """Check if text represents a numeric value"""
        if not text or text.lower() in ['n/a', '', 'unknown']:
            return False
        try:
            # Remove common formatting and try to parse as float
            cleaned = text.replace(',', '').replace('$', '').replace('TK', '').strip()
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False


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
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

    def load_history(self):
        try:
            selected_month = self.history_month_combo.currentText()
            selected_year_val = None if self.history_year_spinbox.specialValueText() and self.history_year_spinbox.value() == self.history_year_spinbox.minimum() else self.history_year_spinbox.value()
            source = self.main_window.load_history_source_combo.currentText() # From main_window

            if source == "Load from PC (CSV)":
                self.load_history_tables_from_csv(selected_month, selected_year_val)
            elif source == "Load from Cloud":
                if self.main_window.supabase_manager and self.main_window.check_internet_connectivity():
                    month_filter = None if selected_month == "All" else selected_month
                    year_filter  = selected_year_val        # already None if "All"
                    self.load_history_tables_from_supabase(month_filter, year_filter)
                elif not self.main_window.supabase_manager:
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
                        month_item = self._create_centered_item(month_year_str)
                        row_calc_id = main_row_data['csv_row'].get('id')
                        month_item.setData(Qt.UserRole, row_calc_id)  # Store the correct id for this row
                        self.main_history_table.setItem(row_idx, 0, month_item)
                        
                        # Set meter columns dynamically (skip zeros)
                        for i in range(max_meters):
                            meter_val = get_csv_value(row, f"Meter-{i+1}", "0")
                            # Only show non-zero values
                            display_val = meter_val if meter_val not in ["0", "", "0.0"] else ""
                            self.main_history_table.setItem(row_idx, 1 + i, self._create_centered_item(display_val))
                        
                        # Set diff columns dynamically (skip zeros)
                        for i in range(max_meters):
                            diff_val = get_csv_value(row, f"Diff-{i+1}", "0")
                            # Only show non-zero values
                            display_val = diff_val if diff_val not in ["0", "", "0.0"] else ""
                            self.main_history_table.setItem(row_idx, 1 + max_meters + i, self._create_centered_item(display_val))
                        
                        # Set fixed columns after meters/diffs
                        base_col = 1 + max_meters * 2
                        # Handle column name variations between CSV and expected names
                        total_unit_cost = get_csv_value(row, "Total Unit Cost", "") or get_csv_value(row, "Total Unit", "0")
                        total_diff_units = get_csv_value(row, "Total Diff Units", "") or get_csv_value(row, "Total Diff", "0")
                        per_unit_cost = get_csv_value(row, "Per Unit Cost", "0")
                        added_amount = get_csv_value(row, "Added Amount", "0")
                        # Use "In Total" specifically for the main table's grand total
                        grand_total = get_csv_value(row, "In Total", "0") 
                        
                        self.main_history_table.setItem(row_idx, base_col + 0, self._create_special_item(total_unit_cost, "total_unit_cost"))
                        self.main_history_table.setItem(row_idx, base_col + 1, self._create_centered_item(total_diff_units))
                        self.main_history_table.setItem(row_idx, base_col + 2, self._create_special_item(per_unit_cost, "per_unit_cost"))
                        self.main_history_table.setItem(row_idx, base_col + 3, self._create_centered_item(added_amount))
                        self.main_history_table.setItem(row_idx, base_col + 4, self._create_special_item(grand_total, "grand_total"))

                # Populate room table
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
                        
                        self.room_history_table.setItem(row_idx, 0, self._create_centered_item(month_year_str))
                        self.room_history_table.setItem(row_idx, 1, self._create_centered_item(room_name))
                        self.room_history_table.setItem(row_idx, 2, self._create_centered_item(present_unit))
                        self.room_history_table.setItem(row_idx, 3, self._create_centered_item(previous_unit))
                        self.room_history_table.setItem(row_idx, 4, self._create_centered_item(real_unit))
                        self.room_history_table.setItem(row_idx, 5, self._create_special_item(unit_bill, "unit_bill"))
                        self.room_history_table.setItem(row_idx, 6, self._create_centered_item(gas_bill))
                        self.room_history_table.setItem(row_idx, 7, self._create_centered_item(water_bill))
                        self.room_history_table.setItem(row_idx, 8, self._create_centered_item(house_rent))
                        self.room_history_table.setItem(row_idx, 9, self._create_special_item(grand_total, "grand_total"))

                # Calculate and display totals using the filtered main rows instead of all room rows
                self.calculate_and_display_totals_from_main_rows(filtered_main_rows, get_csv_value)

                # Resize tables to fit content after loading data
                self.resize_table_to_content(self.main_history_table)
                self.resize_table_to_content(self.room_history_table)
                self.resize_table_to_content(self.totals_table)

                # Apply styling now that data is fully populated and resized
                self._style_table(self.main_history_table)
                self._style_table(self.room_history_table)
                self._style_table(self.totals_table)

                if not filtered_main_rows:
                    QMessageBox.information(self, "No Data", "No records found for the selected filters in CSV.")
                else:
                    QMessageBox.information(self, "Load Successful", f"Loaded {len(filtered_main_rows)} main records and {len(all_room_rows_sorted_with_context)} room records from CSV.")

        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"Failed to load history from CSV: {e}\n{traceback.format_exc()}")

    def load_history_tables_from_supabase(self, month_filter: str | None, year_filter: int | None):
        if not self.main_window.supabase_manager.is_client_initialized() or not self.main_window.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return

        try:
            # Use the unified get_main_calculations which can handle filters or return all
            # Pass None for month/year if "All" is selected or if it's the default 0 for year
            actual_month_filter = None if month_filter == "All" else month_filter
            actual_year_filter = None if year_filter == 0 else year_filter

            # self.clear_history_tables()  # Clear tables before loading | this is the buggy line
            # Directly clear the tables instead of calling a separate method
            self.main_history_table.setRowCount(0)
            self.room_history_table.setRowCount(0)
            self.totals_table.setRowCount(0)

            main_calculations = self.main_window.supabase_manager.get_main_calculations(
                month=actual_month_filter,
                year=actual_year_filter
            )

            # NEW: Sort the results chronologically so that months appear in natural order
            if main_calculations:
                main_calculations.sort(
                    key=lambda m: (
                        m.get("year", 0),
                        self.MONTH_ORDER.get(m.get("month", ""), 0)
                    )
                )

            # Build room rows AFTER sorting main_calculations so room data follows the same order
            all_room_rows = []
            for main_calc in main_calculations:
                main_calc_id = main_calc.get("id")
                if main_calc_id:
                    room_records = self.main_window.supabase_manager.get_room_calculations(main_calc_id)
                    
                    # Add parent month/year context to each room record
                    for room in room_records:
                        room['month'] = main_calc.get('month')
                        room['year'] = main_calc.get('year')
                    
                    all_room_rows.extend(room_records)

            if main_calculations:
                self.main_history_table.setRowCount(len(main_calculations))
                
                # Determine max_meters from the fetched data
                max_meters = 3 # default
                for calc in main_calculations:
                    main_data = calc.get("main_data", {})
                    if isinstance(main_data, str):
                        try:
                            main_data = json.loads(main_data)
                        except json.JSONDecodeError:
                            main_data = {}
                    
                    for i in range(10):
                        meter_key = f"meter_{i+1}"
                        diff_key = f"diff_{i+1}"
                        if main_data.get(meter_key) or main_data.get(diff_key):
                            max_meters = max(max_meters, i + 1)
                
                self.set_main_history_table_columns(max_meters)

                for row_idx, calc in enumerate(main_calculations):
                    main_data = calc.get("main_data", {})
                    # Handle if main_data is a JSON string
                    if isinstance(main_data, str):
                        try:
                            main_data = json.loads(main_data)
                        except json.JSONDecodeError:
                            main_data = {}

                    month_year = f"{calc.get('month', 'N/A')} {calc.get('year', 'N/A')}"
                    month_item = self._create_centered_item(month_year)
                    row_calc_id = calc.get("id")
                    month_item.setData(Qt.UserRole, row_calc_id)  # Store the correct id for this row
                    self.main_history_table.setItem(row_idx, 0, month_item)

                    for i in range(max_meters):
                        meter_val = str(main_data.get(f"meter_{i+1}", ""))
                        diff_val = str(main_data.get(f"diff_{i+1}", ""))
                        self.main_history_table.setItem(row_idx, 1 + i, self._create_centered_item(meter_val))
                        self.main_history_table.setItem(row_idx, 1 + max_meters + i, self._create_centered_item(diff_val))

                    base_col = 1 + max_meters * 2
                    self.main_history_table.setItem(row_idx, base_col + 0, self._create_special_item(str(main_data.get("total_unit_cost", "")), "total_unit_cost"))
                    self.main_history_table.setItem(row_idx, base_col + 1, self._create_centered_item(str(main_data.get("total_diff_units", ""))))
                    self.main_history_table.setItem(row_idx, base_col + 2, self._create_special_item(str(main_data.get("per_unit_cost", "")), "per_unit_cost"))
                    self.main_history_table.setItem(row_idx, base_col + 3, self._create_centered_item(str(main_data.get("added_amount", ""))))
                    self.main_history_table.setItem(row_idx, base_col + 4, self._create_special_item(str(main_data.get("grand_total", "")), "grand_total"))

            if all_room_rows:
                # Ensure room rows follow the same chronological order
                all_room_rows.sort(
                    key=lambda r: (
                        r.get("year", 0),
                        self.MONTH_ORDER.get(r.get("month", ""), 0)
                    )
                )

                self.room_history_table.setRowCount(len(all_room_rows))
                
                for row_idx, room in enumerate(all_room_rows):
                    room_data = room.get("room_data", {})
                    if isinstance(room_data, str):
                        try:
                            room_data = json.loads(room_data)
                        except json.JSONDecodeError:
                            room_data = {}
                    
                    month_year = f"{room.get('month', 'N/A')} {room.get('year', 'N/A')}"

                    self.room_history_table.setItem(row_idx, 0, self._create_centered_item(month_year))
                    self.room_history_table.setItem(row_idx, 1, self._create_centered_item(str(room_data.get("room_name", ""))))
                    self.room_history_table.setItem(row_idx, 2, self._create_centered_item(str(room_data.get("present_unit", ""))))
                    self.room_history_table.setItem(row_idx, 3, self._create_centered_item(str(room_data.get("previous_unit", ""))))
                    self.room_history_table.setItem(row_idx, 4, self._create_centered_item(str(room_data.get("real_unit", ""))))
                    self.room_history_table.setItem(row_idx, 5, self._create_special_item(str(room_data.get("unit_bill", "")), "unit_bill"))
                    self.room_history_table.setItem(row_idx, 6, self._create_centered_item(str(room_data.get("gas_bill", ""))))
                    self.room_history_table.setItem(row_idx, 7, self._create_centered_item(str(room_data.get("water_bill", ""))))
                    self.room_history_table.setItem(row_idx, 8, self._create_centered_item(str(room_data.get("house_rent", ""))))
                    self.room_history_table.setItem(row_idx, 9, self._create_special_item(str(room_data.get("grand_total", "")), "grand_total"))

            self.calculate_and_display_totals_from_supabase_records(main_calculations, all_room_rows)
            
            # Resize tables to fit content
            self.resize_table_to_content(self.main_history_table)
            self.resize_table_to_content(self.room_history_table)
            self.resize_table_to_content(self.totals_table)

            QMessageBox.information(self, "Load Successful", f"Loaded {len(main_calculations)} main records and {len(all_room_rows)} room records from Supabase.")

        except Exception as e:
            QMessageBox.critical(self, "Load History Error", f"An unexpected error occurred loading history from Supabase: {e}\n{traceback.format_exc()}")
            # Clear tables on error to avoid displaying partial data
            self.calculate_and_display_totals_from_supabase_records([], []) # Clear totals

    def calculate_and_display_totals_from_supabase_records(self, main_calculations: list[dict], all_room_rows: list[dict]):
        grouped = {}
        for room in all_room_rows:
            month = room.get("month")
            year = room.get("year")
            key = f"{month} {year}" if (month and year) else "Unknown"

            room_data = room.get("room_data", {})
            if isinstance(room_data, str):
                try:
                    room_data = json.loads(room_data)
                except json.JSONDecodeError:
                    room_data = {}

            try:
                grp = grouped.setdefault(key, {"house":0.0,"water":0.0,"gas":0.0,"unit":0.0})
                grp["house"] += float(room_data.get("house_rent", 0) or 0)
                grp["water"] += float(room_data.get("water_bill", 0) or 0)
                grp["gas"]   += float(room_data.get("gas_bill", 0) or 0)
                grp["unit"]  += float(room_data.get("unit_bill", 0) or 0)
            except (ValueError, TypeError):
                continue

        # sort keys by year then month
        def month_key(m):
            parts=m.split();
            if len(parts)==2:
                mon,yr=parts; return (int(yr), self.MONTH_ORDER.get(mon,0))
            return (0,0)
        skeys=sorted(grouped.keys(), key=month_key)

        self.totals_table.setRowCount(len(skeys))
        for idx,k in enumerate(skeys):
            self.totals_table.setItem(idx,0,self._create_centered_item(k))
            t=grouped[k]
            self.totals_table.setItem(idx,1,self._create_centered_item(f"{t['house']:.2f}"))
            self.totals_table.setItem(idx,2,self._create_centered_item(f"{t['water']:.2f}"))
            self.totals_table.setItem(idx,3,self._create_centered_item(f"{t['gas']:.2f}"))
            self.totals_table.setItem(idx,4,self._create_centered_item(f"{t['unit']:.2f}"))

    def _is_click_inside_history_tables(self, global_pos):
        """Return True if the widget at the given global position is within any of the history tables."""
        w = QApplication.widgetAt(global_pos)
        if not w:
            return False
        
        # Check if click is inside any of the tables or their children
        tables = [self.main_history_table, self.room_history_table, self.totals_table]
        for table in tables:
            if table and (w == table or table.isAncestorOf(w)):
                return True
        return False

    def mousePressEvent(self, event):
        """Clear table selections when the user clicks anywhere outside the history tables."""
        if event.button() == Qt.LeftButton and not self._is_click_inside_history_tables(event.globalPos()):
            # Clear selections and update buttons
            tables_to_clear = [self.main_history_table, self.room_history_table, self.totals_table]
            for table in tables_to_clear:
                if table:
                    table.clearSelection()
            self.update_action_buttons_state()
        # Call base implementation so other widgets receive the event as usual
        super().mousePressEvent(event)

    def update_action_buttons_state(self):
        """Enable buttons when at least one row is selected and apply color styles."""
        has_selection = (self.main_history_table.selectionModel().hasSelection() or 
                        self.room_history_table.selectionModel().hasSelection())
        
        if has_selection:
            self.edit_selected_record_button.setEnabled(True)
            
            self.delete_selected_record_button.setEnabled(True)
        else:
            self.edit_selected_record_button.setEnabled(False)
            self.delete_selected_record_button.setEnabled(False)
            

    def handle_edit_selected_record(self):
        selected_items = self.main_history_table.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a record to edit.")
            return
        selected_row = selected_items[0].row()
        month_item = self.main_history_table.item(selected_row, 0)
        record_id = month_item.data(Qt.UserRole) if month_item else None
        
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
        if not self.main_window.supabase_manager.is_client_initialized() or not self.main_window.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return
        try:
            # Fetch main calculation data using SupabaseManager
            main_record = self.main_window.supabase_manager.get_main_calculations_by_id(record_id) # New method needed in SupabaseManager
            if not main_record:
                QMessageBox.critical(self, "Error", "Main calculation record not found.")
                return
            main_data = main_record.get("main_data", {}) # Extract JSONB data

            # Fetch room calculation data using SupabaseManager
            room_data_list = self.main_window.supabase_manager.get_room_calculations(record_id)

            dialog = EditRecordDialog(record_id, main_data, room_data_list, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                self.load_history() # Refresh the table after changes are saved
        except Exception as e:
            QMessageBox.critical(
                self,
                "Edit Record Error",
                f"An unexpected error occurred while editing record: {e}\n{traceback.format_exc()}"
            )

    def handle_delete_record(self, record_id): # Actual logic for deleting
        if not self.main_window.supabase_manager.is_client_initialized() or not self.main_window.check_internet_connectivity():
            QMessageBox.warning(self, "Error", "Supabase not configured or no internet.")
            return
        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this record and all associated room data?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                delete_success = self.main_window.supabase_manager.delete_calculation_record(record_id) # New method needed
                if delete_success:
                    QMessageBox.information(self, "Delete Successful", "Record deleted successfully.")
                    self.load_history() # Refresh the table
                else:
                    QMessageBox.critical(self, "Supabase Error", "Failed to delete record from Supabase.")
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", f"An unexpected error occurred during delete: {e}\n{traceback.format_exc()}")

    def calculate_and_display_totals(self, room_rows, get_csv_value):
        """Calculate and display totals for house rent, water bill, gas bill, and unit bill"""
        try:
            grouped = {}
            for room_row in room_rows:
                month_val = get_csv_value(room_row, "Month", "").strip()
                if month_val:
                    key = month_val
                    try:
                        house = float(get_csv_value(room_row, "Total House Rent", "0"))
                        water = float(get_csv_value(room_row, "Total Water Bill", "0"))
                        gas = float(get_csv_value(room_row, "Total Gas Bill", "0"))
                        unit = float(get_csv_value(room_row, "Total Room Unit Bill", "0"))
                    except ValueError:
                        continue
                    grp = grouped.setdefault(key,{"house":0.0,"water":0.0,"gas":0.0,"unit":0.0})
                    grp["house"]+=house; grp["water"]+=water; grp["gas"]+=gas; grp["unit"]+=unit

            # sort keys by year then month
            def month_key(m):
                parts=m.split();
                if len(parts)==2:
                    mon,yr=parts; return (int(yr), self.MONTH_ORDER.get(mon,0))
                return (0,0)
            skeys=sorted(grouped.keys(), key=month_key)

            self.totals_table.setRowCount(len(skeys))
            for idx,k in enumerate(skeys):
                self.totals_table.setItem(idx,0,QTableWidgetItem(k))
                t=grouped[k]
                self.totals_table.setItem(idx,1,QTableWidgetItem(f"{t['house']:.2f}"))
                self.totals_table.setItem(idx,2,QTableWidgetItem(f"{t['water']:.2f}"))
                self.totals_table.setItem(idx,3,QTableWidgetItem(f"{t['gas']:.2f}"))
                self.totals_table.setItem(idx,4,QTableWidgetItem(f"{t['unit']:.2f}"))
            
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
                self.totals_table.setItem(row_idx, 0, self._create_centered_item(month_year_str))
                
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
                    
                    self.totals_table.setItem(row_idx, 1, self._create_centered_item(f"{house_rent:.2f}"))
                    self.totals_table.setItem(row_idx, 2, self._create_centered_item(f"{water_bill:.2f}"))
                    self.totals_table.setItem(row_idx, 3, self._create_centered_item(f"{gas_bill:.2f}"))
                    self.totals_table.setItem(row_idx, 4, self._create_centered_item(f"{unit_bill:.2f}"))
                except (ValueError, TypeError):
                    # If conversion fails, set zeros for this row
                    self.totals_table.setItem(row_idx, 1, self._create_centered_item("0.00"))
                    self.totals_table.setItem(row_idx, 2, self._create_centered_item("0.00"))
                    self.totals_table.setItem(row_idx, 3, self._create_centered_item("0.00"))
                    self.totals_table.setItem(row_idx, 4, self._create_centered_item("0.00"))
            
        except Exception as e:
            # If there's an error calculating totals, just clear the table
            self.totals_table.setRowCount(0)
            print(f"Error calculating totals from main rows: {e}")



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
