"""
Add Month Manager - Handles automatic month progression functionality.

This module provides functionality to:
1. Find the latest month record from cloud storage
2. Calculate the next billing period (month/year)
3. Transform room data for the next month (present -> previous)
4. Load prepared data into the UI
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from PyQt5.QtWidgets import QMessageBox


class AddMonthManager:
    """Manages the Add Month functionality for automatic billing period progression."""
    
    def __init__(self, supabase_manager, main_window_ref):
        """
        Initialize AddMonthManager.
        
        Args:
            supabase_manager: Instance of SupabaseManager for cloud operations
            main_window_ref: Reference to main window for UI access
        """
        self.supabase_manager = supabase_manager
        self.main_window = main_window_ref
        
        # Month names for navigation
        self.month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
    
    def get_latest_month_record(self) -> Optional[Dict]:
        """
        Find the most recent month/year record from cloud storage.
        
        Returns:
            Dict containing the latest record, or None if no records found
            
        Raises:
            Exception: If there are issues accessing cloud data
        """
        if not self.supabase_manager.is_client_initialized():
            raise Exception("Supabase client not initialized")
        
        try:
            # Get all main calculations ordered by year desc, then by created_at desc
            all_records = self.supabase_manager.get_main_calculations()
            
            if not all_records:
                return None
            
            # Find the record with the most recent month/year combination
            latest_record = None
            latest_year = 0
            latest_month_index = -1
            
            for record in all_records:
                month_str = record.get("month", "")
                year_int = record.get("year", 0)
                
                if month_str in self.month_names and year_int > 0:
                    month_index = self.month_names.index(month_str)
                    
                    # Compare by year first, then by month
                    if (year_int > latest_year or 
                        (year_int == latest_year and month_index > latest_month_index)):
                        latest_year = year_int
                        latest_month_index = month_index
                        latest_record = record
            
            return latest_record
            
        except Exception as e:
            raise Exception(f"Failed to retrieve latest month record: {str(e)}")
    
    def calculate_next_month(self, current_month: str, current_year: int) -> Tuple[str, int]:
        """
        Calculate the next month and year from the current month/year.
        
        Args:
            current_month: Current month name (e.g., "January")
            current_year: Current year (e.g., 2024)
            
        Returns:
            Tuple of (next_month_str, next_year_int)
            
        Raises:
            ValueError: If current_month is not a valid month name
        """
        if current_month not in self.month_names:
            raise ValueError(f"Invalid month name: {current_month}")
        
        current_month_index = self.month_names.index(current_month)
        
        # Calculate next month and year
        if current_month_index == 11:  # December (index 11)
            next_month_str = self.month_names[0]  # January
            next_year_int = current_year + 1
        else:
            next_month_str = self.month_names[current_month_index + 1]
            next_year_int = current_year
        
        return next_month_str, next_year_int
    
    def prepare_next_month_data(self, room_records: List[Dict]) -> List[Dict]:
        """
        Transform room data for the next billing period.
        
        Logic:
        - Move present_unit to previous_unit
        - Clear present_unit field
        - Keep other fields (gas_bill, water_bill, house_rent) unchanged
        
        Args:
            room_records: List of room calculation records from cloud
            
        Returns:
            List of transformed room records ready for next month
        """
        transformed_records = []
        
        for room_record in room_records:
            # Create a copy to avoid modifying original data
            transformed_record = room_record.copy()
            room_data = transformed_record.get("room_data", {})
            
            if isinstance(room_data, str):
                try:
                    room_data = json.loads(room_data)
                except json.JSONDecodeError:
                    room_data = {}
            
            # Get current present_unit value
            present_unit = room_data.get("present_unit", 0)
            
            # Transform data: present -> previous, clear present
            room_data["previous_unit"] = present_unit
            room_data["present_unit"] = ""  # Clear for new input
            
            # Keep other fields unchanged for reference
            # gas_bill, water_bill, house_rent remain as-is
            
            transformed_record["room_data"] = room_data
            transformed_records.append(transformed_record)
        
        return transformed_records
    
    def load_next_month_to_ui(self, next_month: str, next_year: int, room_records: List[Dict], additional_amount: str = "0"):
        """
        Load the prepared next month data into the UI components.
        
        Args:
            next_month: Next month name
            next_year: Next year value  
            room_records: Transformed room records for next month
            additional_amount: Additional amount from previous month
        """
        try:
            # Set the month/year in main tab
            main_tab = self.main_window.main_tab_instance
            main_tab.month_combo.setCurrentText(next_month)
            main_tab.year_spinbox.setValue(next_year)
            
            # Load additional amount from previous month
            if main_tab.additional_amount_input:
                # Format additional amount to show clean numbers (no .0 for whole numbers)
                formatted_amount = self._format_number_string(additional_amount)
                main_tab.additional_amount_input.setText(formatted_amount)
            
            # Clear meter and difference readings (as per requirements)
            self._clear_meter_and_diff_readings()
            
            # Load room data using existing functionality without triggering automatic calculation
            if room_records and hasattr(self.main_window.rooms_tab_instance, 'load_room_data_from_supabase_rows'):
                self.main_window.rooms_tab_instance.load_room_data_from_supabase_rows(room_records, auto_calculate=False)
            else:
                # Set default number of rooms if no records
                self.main_window.rooms_tab_instance.num_rooms_spinbox.setValue(1)
            
        except Exception as e:
            raise Exception(f"Failed to load data to UI: {str(e)}")
    
    def _clear_meter_and_diff_readings(self):
        """Clear all meter and difference reading inputs in the main tab."""
        main_tab = self.main_window.main_tab_instance
        
        # Clear meter readings
        for meter_entry in main_tab.meter_entries:
            meter_entry.clear()
        
        # Clear difference readings
        for diff_entry in main_tab.diff_entries:
            diff_entry.clear()
        
        # Note: Don't clear additional amount - it should be loaded from previous month data
    
    def _format_number_string(self, val):
        """Return a clean string representation of a number (int if whole, float otherwise)."""
        if val == '' or val is None:
            return ''
        try:
            if isinstance(val, int):
                return str(val)
            elif isinstance(val, float):
                if val.is_integer():
                    return str(int(val))
                else:
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
    
    def execute_add_month(self, parent_widget=None) -> bool:
        """
        Execute the complete Add Month workflow.
        
        Args:
            parent_widget: Parent widget for message boxes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Step 1: Validate prerequisites
            if not self.supabase_manager.is_client_initialized():
                QMessageBox.warning(
                    parent_widget, 
                    "Supabase Not Configured", 
                    "Supabase is not configured. Please go to the 'Supabase Config' tab."
                )
                return False
            
            if not self.main_window.check_internet_connectivity():
                QMessageBox.warning(
                    parent_widget,
                    "Network Error",
                    "No internet connection detected. Please check your network and try again."
                )
                return False
            
            # Step 2: Get latest month record
            latest_record = self.get_latest_month_record()
            if not latest_record:
                QMessageBox.warning(
                    parent_widget,
                    "No Previous Records",
                    "No previous calculation records found in the cloud. "
                    "Please create at least one record before using Add Month."
                )
                return False
            
            # Step 3: Calculate next month/year
            current_month = latest_record.get("month")
            current_year = latest_record.get("year")
            
            if not current_month or not current_year:
                QMessageBox.critical(
                    parent_widget,
                    "Invalid Data",
                    "Latest record contains invalid month/year data."
                )
                return False
            
            next_month, next_year = self.calculate_next_month(current_month, current_year)
            
            # Step 4: Check if next month already exists
            existing_next_record = self.supabase_manager.get_main_calculation_by_month_year(
                next_month, next_year
            )
            if existing_next_record:
                reply = QMessageBox.question(
                    parent_widget,
                    "Record Already Exists",
                    f"A record for {next_month} {next_year} already exists. "
                    f"Do you want to load it instead of creating a new one?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    # Load existing record normally
                    main_tab = self.main_window.main_tab_instance
                    main_tab.load_month_combo.setCurrentText(next_month)
                    main_tab.load_year_spinbox.setValue(next_year)
                    main_tab.load_info_to_inputs_from_supabase(next_month, next_year)
                    return True
                else:
                    return False
            
            # Step 5: Get room data from latest record
            latest_record_id = latest_record.get("id")
            room_records = []
            if latest_record_id:
                room_records = self.supabase_manager.get_room_calculations(latest_record_id)
            
            # Step 6: Extract additional amount from latest record
            additional_amount = "0"
            main_data = latest_record.get("main_data", {})
            if isinstance(main_data, str):
                try:
                    main_data = json.loads(main_data)
                except json.JSONDecodeError:
                    main_data = {}
            
            # Support both legacy 'added_amount' and new 'additional_amount' keys
            additional_amount = str(main_data.get("additional_amount", main_data.get("added_amount", "0")))
            
            # Step 7: Transform room data for next month
            transformed_room_records = self.prepare_next_month_data(room_records)
            
            # Step 8: Load data to UI
            self.load_next_month_to_ui(next_month, next_year, transformed_room_records, additional_amount)
            
            # Step 8: Show success message
            QMessageBox.information(
                parent_widget,
                "Add Month Successful",
                f"Data prepared for {next_month} {next_year}.\n\n"
                f"Room data loaded from {current_month} {current_year} with:\n"
                f"• Present units moved to previous units\n"
                f"• Present unit fields cleared for new readings\n"
                f"• Meter and difference readings cleared\n\n"
                f"You can now enter new meter readings and present unit values."
            )
            
            return True
            
        except Exception as e:
            QMessageBox.critical(
                parent_widget,
                "Add Month Error",
                f"An error occurred while preparing next month data:\n\n{str(e)}"
            )
            return False
