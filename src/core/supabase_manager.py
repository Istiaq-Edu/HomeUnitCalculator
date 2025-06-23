import os
import json
from supabase import create_client, Client
from postgrest.exceptions import APIError
from gotrue.errors import AuthApiError
from src.core.db_manager import DBManager # To get Supabase URL and Key

class SupabaseManager:
    def __init__(self):
        self.supabase: Client = None
        self.db_manager = DBManager() # Use DBManager to get Supabase config
        self._initialize_supabase_client()

    def _initialize_supabase_client(self):
        """Initializes the Supabase client using credentials from the local DB."""
        config = self.db_manager.get_config()
        supabase_url = config.get("SUPABASE_URL")
        supabase_key = config.get("SUPABASE_KEY")

        if not (supabase_url and supabase_key):
            self.supabase = None
            print("Supabase URL/Key not found in local DB. Supabase features disabled.")
            return

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            print("Supabase client initialized successfully from stored config.")
        except Exception as e:
            self.supabase = None
            print(f"Failed to initialize Supabase client: {e}")

    def is_client_initialized(self) -> bool:
        """Checks if the Supabase client is initialized and ready for use."""
        return self.supabase is not None

    def upload_image(self, local_file_path: str, bucket_name: str = "rental_images", folder: str = "rentals") -> str | None:
        """
        Uploads an image to Supabase Storage and returns its public URL.
        :param local_file_path: The path to the local image file.
        :param bucket_name: The name of the Supabase Storage bucket.
        :param folder: The folder within the bucket to store the image.
        :return: The public URL of the uploaded image, or None if upload fails.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot upload image.")
            return None

        if not os.path.exists(local_file_path):
            print(f"Local file not found: {local_file_path}")
            return None

        file_name = os.path.basename(local_file_path)
        storage_path = f"{folder}/{file_name}"

        try:
            with open(local_file_path, 'rb') as f:
                # Upload the file
                response = self.supabase.storage.from_(bucket_name).upload(storage_path, f.read(), {"content-type": "image/jpeg"})
                
                # If upload is successful, get the public URL
                if response.status_code == 200: # Supabase storage upload returns 200 on success
                    public_url_response = self.supabase.storage.from_(bucket_name).get_public_url(storage_path)
                    return public_url_response
                else:
                    print(f"Image upload failed with status code {response.status_code}: {response.json()}")
                    return None
        except Exception as e:
            print(f"Error uploading image {local_file_path}: {e}")
            return None

    def save_main_calculation(self, main_calc_data: dict) -> int | None:
        """
        Saves or updates main calculation data to Supabase.
        :param main_calc_data: Dictionary containing main calculation data.
                               Expected to include 'month', 'year', and other dynamic data.
        :return: The ID of the inserted/updated record, or None on failure.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot save main calculation.")
            return None

        month = main_calc_data.get("month")
        year = main_calc_data.get("year")

        if not (month and year):
            print("Month and year are required for main calculation.")
            return None

        # Prepare data for JSONB column
        data_to_save = {
            "month": month,
            "year": year,
            "main_data": main_calc_data # The entire dict will be stored as JSONB
        }

        try:
            # Check for existing record
            response = self.supabase.table("main_calculations").select("id").eq("month", month).eq("year", year).execute()
            main_calc_id = None
            if response.data:
                main_calc_id = response.data[0]['id']

            if main_calc_id:
                # Update existing record
                update_response = self.supabase.table("main_calculations").update(data_to_save).eq("id", main_calc_id).execute()
                if update_response.data:
                    print(f"Main calculation data updated for {month} {year}")
                    return main_calc_id
                else:
                    print(f"Failed to update main calculation data: {update_response.json()}")
                    return None
            else:
                # Insert new record
                insert_response = self.supabase.table("main_calculations").insert(data_to_save).execute()
                if insert_response.data:
                    new_id = insert_response.data[0]['id']
                    print(f"Main calculation data inserted for {month} {year} with ID: {new_id}")
                    return new_id
                else:
                    print(f"Failed to insert main calculation data: {insert_response.json()}")
                    return None
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error saving main calculation: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred saving main calculation: {e}")
            return None

    def save_room_calculations(self, main_calc_id: int, room_data_list: list[dict]) -> bool:
        """
        Saves room calculation data to Supabase, handling image uploads.
        Deletes existing room calculations for the given main_calc_id before inserting new ones.
        :param main_calc_id: The ID of the associated main calculation.
        :param room_data_list: A list of dictionaries, each containing room data and local image paths.
        :return: True if successful, False otherwise.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot save room calculations.")
            return False

        if not main_calc_id:
            print("main_calc_id is required to save room calculations.")
            return False

        try:
            with self.supabase.postgrest.transaction() as trx:
                # Delete existing room calculations for this main_calc_id
                trx.table("room_calculations").delete().eq("main_calculation_id", main_calc_id).execute()
                print(f"Deleted existing room calculations for main_calc_id: {main_calc_id}")

                records_to_insert = []
                for room_data in room_data_list:
                    # Upload images and get URLs
                    photo_url = self.upload_image(room_data.get("photo_path")) if room_data.get("photo_path") else None
                    nid_front_url = self.upload_image(room_data.get("nid_front_path")) if room_data.get("nid_front_path") else None
                    nid_back_url = self.upload_image(room_data.get("nid_back_path")) if room_data.get("nid_back_path") else None
                    police_form_url = self.upload_image(room_data.get("police_form_path")) if room_data.get("police_form_path") else None

                    # Prepare data for JSONB column and URL columns
                    record = {
                        "main_calculation_id": main_calc_id,
                        "room_data": {k: v for k, v in room_data.items() if not k.endswith("_path")}, # Exclude local paths
                        "photo_url": photo_url,
                        "nid_front_url": nid_front_url,
                        "nid_back_url": nid_back_url,
                        "police_form_url": police_form_url
                    }
                    records_to_insert.append(record)
                
                if records_to_insert:
                    insert_response = trx.table("room_calculations").insert(records_to_insert).execute()
                    if insert_response.data:
                        print(f"Inserted {len(insert_response.data)} room calculation records.")
                        return True
                    else:
                        print(f"Failed to insert room calculation data: {insert_response.json()}")
                        return False
                else:
                    print("No room calculation records to insert.")
                    return True # No rooms to insert, still considered successful

        except (APIError, AuthApiError) as e:
            print(f"Supabase API error saving room calculations: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred saving room calculations: {e}")
            return False

    def get_main_calculations(self, month: str, year: int) -> dict | None:
        """
        Retrieves a specific main calculation record from Supabase.
        :param month: The month of the calculation.
        :param year: The year of the calculation.
        :return: The full main calculation record (including id, month, year, main_data), or None if not found.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve main calculation.")
            return None
        try:
            response = self.supabase.table("main_calculations").select("id, month, year, main_data").eq("month", month).eq("year", year).limit(1).execute()
            if response.data:
                return response.data[0] # Return the full record
            return None
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving main calculation: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred retrieving main calculation: {e}")
            return None

    def get_all_main_calculations(self) -> list[dict]:
        """
        Retrieves all main calculation records from Supabase.
        :return: A list of all main calculation records.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve all main calculations.")
            return []
        try:
            response = self.supabase.table("main_calculations").select("id, month, year, main_data").order("year", desc=True).order("created_at", desc=True).execute()
            return response.data if response.data else []
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving all main calculations: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred retrieving all main calculations: {e}")
            return []

    def get_room_calculations(self, main_calculation_id: int) -> list[dict]:
        """
        Retrieves room calculation data for a given main calculation ID.
        :param main_calculation_id: The ID of the associated main calculation.
        :return: A list of dictionaries, each containing room data and image URLs.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve room calculations.")
            return []
        try:
            response = self.supabase.table("room_calculations").select("room_data, photo_url, nid_front_url, nid_back_url, police_form_url").eq("main_calculation_id", main_calculation_id).execute()
            if response.data:
                return [
                    {
                        **record.get("room_data", {}),
                        "photo_url": record.get("photo_url"),
                        "nid_front_url": record.get("nid_front_url"),
                        "nid_back_url": record.get("nid_back_url"),
                        "police_form_url": record.get("police_form_url")
                    }
                    for record in response.data
                ]
            return []
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving room calculations: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred retrieving room calculations: {e}")
            return []

    def save_rental_record(self, record_data: dict, record_id: int | None = None) -> int | None:
        """
        Saves or updates a rental record to Supabase, handling image uploads.
        :param record_data: Dictionary containing rental record data (tenant_name, room_number, advanced_paid, image_paths).
        :param record_id: Optional ID of the record to update. If None, a new record is inserted.
        :return: The ID of the inserted/updated record, or None on failure.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot save rental record.")
            return None

        tenant_name = record_data.get("tenant_name")
        room_number = record_data.get("room_number")
        advanced_paid = record_data.get("advanced_paid")
        is_archived = record_data.get("is_archived", False)

        if not (tenant_name and room_number):
            print("Tenant name and room number are required for rental record.")
            return None

        try:
            # Upload images and get URLs
            photo_url = self.upload_image(record_data.get("photo_path")) if record_data.get("photo_path") else None
            nid_front_url = self.upload_image(record_data.get("nid_front_path")) if record_data.get("nid_front_path") else None
            nid_back_url = self.upload_image(record_data.get("nid_back_path")) if record_data.get("nid_back_path") else None
            police_form_url = self.upload_image(record_data.get("police_form_path")) if record_data.get("police_form_path") else None

            # Prepare data for JSONB columns
            data_to_save = {
                "tenant_data": {
                    "tenant_name": tenant_name,
                    "room_number": room_number,
                    "advanced_paid": advanced_paid
                },
                "image_urls": {
                    "photo_url": photo_url,
                    "nid_front_url": nid_front_url,
                    "nid_back_url": nid_back_url,
                    "police_form_url": police_form_url
                },
                "is_archived": is_archived
            }

            if record_id:
                # Update existing record
                update_response = self.supabase.table("rental_records").update(data_to_save).eq("id", record_id).execute()
                if update_response.data:
                    print(f"Rental record updated for ID: {record_id}")
                    return record_id
                else:
                    print(f"Failed to update rental record: {update_response.json()}")
                    return None
            else:
                # Insert new record
                insert_response = self.supabase.table("rental_records").insert(data_to_save).execute()
                if insert_response.data:
                    new_id = insert_response.data[0]['id']
                    print(f"Rental record inserted with ID: {new_id}")
                    return new_id
                else:
                    print(f"Failed to insert rental record: {insert_response.json()}")
                    return None
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error saving rental record: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred saving rental record: {e}")
            return None

    def get_rental_records(self, is_archived: bool | None = None) -> list[dict]:
        """
        Retrieves rental records from Supabase.
        :param is_archived: If True, retrieves archived records. If False, retrieves non-archived. If None, retrieves all.
        :return: A list of rental record dictionaries.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve rental records.")
            return []
        try:
            query = self.supabase.table("rental_records").select("id, tenant_data, image_urls, created_at, updated_at, is_archived")
            if is_archived is not None:
                query = query.eq("is_archived", is_archived)
            response = query.order("created_at", desc=True).execute()
            
            if response.data:
                # Flatten the JSONB data for easier consumption
                flattened_records = []
                for record in response.data:
                    flattened_record = {
                        "id": record.get("id"),
                        "tenant_name": record.get("tenant_data", {}).get("tenant_name"),
                        "room_number": record.get("tenant_data", {}).get("room_number"),
                        "advanced_paid": record.get("tenant_data", {}).get("advanced_paid"),
                        "photo_url": record.get("image_urls", {}).get("photo_url"),
                        "nid_front_url": record.get("image_urls", {}).get("nid_front_url"),
                        "nid_back_url": record.get("image_urls", {}).get("nid_back_url"),
                        "police_form_url": record.get("image_urls", {}).get("police_form_url"),
                        "created_at": record.get("created_at"),
                        "updated_at": record.get("updated_at"),
                        "is_archived": record.get("is_archived")
                    }
                    flattened_records.append(flattened_record)
                return flattened_records
            return []
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving rental records: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred retrieving rental records: {e}")
            return []

    def update_rental_record_archive_status(self, record_id: int, is_archived: bool) -> bool:
        """
        Updates the is_archived status of a rental record in Supabase.
        :param record_id: The ID of the rental record to update.
        :param is_archived: The new archive status (True for archived, False for active).
        :return: True if successful, False otherwise.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot update archive status.")
            return False
        try:
            response = self.supabase.table("rental_records").update({"is_archived": is_archived}).eq("id", record_id).execute()
            if response.data:
                print(f"Rental record ID {record_id} archive status updated to {is_archived}.")
                return True
            else:
                print(f"Failed to update archive status for record ID {record_id}: {response.json()}")
                return False
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error updating archive status: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred updating archive status: {e}")
            return False

    def delete_rental_record(self, record_id: int) -> bool:
        """
        Deletes a rental record from Supabase.
        Note: This does NOT delete associated images from Supabase Storage.
        Image deletion would require tracking image URLs and calling storage.remove().
        For simplicity, we're only deleting the record here.
        :param record_id: The ID of the rental record to delete.
        :return: True if successful, False otherwise.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot delete rental record.")
            return False
        try:
            response = self.supabase.table("rental_records").delete().eq("id", record_id).execute()
            if response.data:
                print(f"Rental record ID {record_id} deleted.")
                return True
            else:
                print(f"Failed to delete rental record ID {record_id}: {response.json()}")
                return False
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error deleting rental record: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred deleting rental record: {e}")
            return False

# Example usage (for testing purposes, can be removed later)
if __name__ == "__main__":
    print("Testing SupabaseManager...")
    # Ensure you have a test_app_config.db with SUPABASE_URL and SUPABASE_KEY
    # For local testing, you might need to manually set up a dummy db_manager or
    # ensure your actual app_config.db has valid Supabase credentials.

    # Dummy DBManager for testing if app_config.db is not available
    class MockDBManager:
        def get_config(self):
            # Replace with your actual test Supabase URL and Key
            return {
                "SUPABASE_URL": "YOUR_SUPABASE_URL",
                "SUPABASE_KEY": "YOUR_SUPABASE_ANON_KEY"
            }

    # Temporarily replace the real DBManager with the mock one for testing
    # This is a hack for standalone testing and should not be done in production code
    import sys
    sys.modules['src.core.db_manager'] = MockDBManager()
    from src.core.db_manager import DBManager as OriginalDBManager
    OriginalDBManager = MockDBManager # Reassign to use the mock for this test block

    # Create a dummy image file for testing upload
    dummy_image_path = "dummy_image.jpg"
    try:
        from PIL import Image
        img = Image.new('RGB', (60, 30), color = 'red')
        img.save(dummy_image_path)
        print(f"Created dummy image: {dummy_image_path}")
    except ImportError:
        print("Pillow not installed. Skipping dummy image creation. Image upload test will fail.")
        dummy_image_path = None

    manager = SupabaseManager()

    if manager.is_client_initialized():
        print("\nSupabase client initialized. Proceeding with tests.")

        # Test saving main calculation
        test_main_data = {
            "month": "June",
            "year": 2025,
            "meter_readings": [100, 200, 300],
            "diff_readings": [50, 60, 70],
            "additional_amount": 150.0,
            "total_unit_cost": 1500.0,
            "total_diff_units": 180,
            "per_unit_cost_calculated": 8.33,
            "grand_total_bill": 1650.0,
            "extra_field": "some_dynamic_value"
        }
        main_id = manager.save_main_calculation(test_main_data)
        print(f"Saved main calculation with ID: {main_id}")

        if main_id:
            # Test saving room calculations with dummy image paths
            test_room_data_list = [
                {
                    "room_name": "Room A",
                    "present_unit": 50,
                    "previous_unit": 20,
                    "real_unit": 30,
                    "unit_bill": 249.9,
                    "gas_bill": 100.0,
                    "water_bill": 50.0,
                    "house_rent": 5000.0,
                    "grand_total": 5399.9,
                    "photo_path": dummy_image_path,
                    "nid_front_path": dummy_image_path
                },
                {
                    "room_name": "Room B",
                    "present_unit": 120,
                    "previous_unit": 70,
                    "real_unit": 50,
                    "unit_bill": 416.5,
                    "gas_bill": 120.0,
                    "water_bill": 60.0,
                    "house_rent": 6000.0,
                    "grand_total": 6596.5,
                    "police_form_path": dummy_image_path
                }
            ]
            rooms_saved = manager.save_room_calculations(main_id, test_room_data_list)
            print(f"Room calculations saved: {rooms_saved}")

            # Test retrieving main calculation
            retrieved_main = manager.get_main_calculations("June", 2025)
            print("\nRetrieved Main Calculation:")
            print(json.dumps(retrieved_main, indent=2))
            # assert retrieved_main == test_main_data # This assertion will fail due to ID and created_at/updated_at fields

            # Test retrieving room calculations
            retrieved_rooms = manager.get_room_calculations(main_id)
            print("\nRetrieved Room Calculations:")
            print(json.dumps(retrieved_rooms, indent=2))
            assert len(retrieved_rooms) == 2
            assert "photo_url" in retrieved_rooms[0]
            assert "room_name" in retrieved_rooms[0]
            assert retrieved_rooms[0]["room_name"] == "Room A"
            assert retrieved_rooms[1]["room_name"] == "Room B"

            # --- New Rental Record Tests ---
            print("\n--- Testing Rental Records ---")
            test_rental_data = {
                "tenant_name": "John Doe",
                "room_number": "C-205",
                "advanced_paid": 1000.0,
                "photo_path": dummy_image_path,
                "nid_front_path": dummy_image_path
            }
            rental_id = manager.save_rental_record(test_rental_data)
            print(f"Saved rental record with ID: {rental_id}")

            if rental_id:
                # Test retrieving all rental records
                all_rentals = manager.get_rental_records()
                print("\nAll Rental Records:")
                print(json.dumps(all_rentals, indent=2))
                assert any(r['id'] == rental_id for r in all_rentals)

                # Test retrieving non-archived rental records
                active_rentals = manager.get_rental_records(is_archived=False)
                print("\nActive Rental Records:")
                print(json.dumps(active_rentals, indent=2))
                assert any(r['id'] == rental_id for r in active_rentals)

                # Test updating archive status
                archive_success = manager.update_rental_record_archive_status(rental_id, True)
                print(f"Archived record {rental_id}: {archive_success}")
                assert archive_success

                # Test retrieving archived rental records
                archived_rentals = manager.get_rental_records(is_archived=True)
                print("\nArchived Rental Records:")
                print(json.dumps(archived_rentals, indent=2))
                assert any(r['id'] == rental_id for r in archived_rentals)

                # Test updating the record
                updated_rental_data = {
                    "tenant_name": "Jane Doe",
                    "room_number": "C-205",
                    "advanced_paid": 1200.0,
                    "photo_path": None, # No new photo
                    "nid_front_path": dummy_image_path # Re-upload same NID front
                }
                updated_id = manager.save_rental_record(updated_rental_data, record_id=rental_id)
                print(f"Updated rental record with ID: {updated_id}")
                assert updated_id == rental_id

                # Test deleting the record
                delete_success = manager.delete_rental_record(rental_id)
                print(f"Deleted record {rental_id}: {delete_success}")
                assert delete_success

                # Verify deletion
                remaining_rentals = manager.get_rental_records()
                assert not any(r['id'] == rental_id for r in remaining_rentals)
            else:
                print("Skipping rental record tests due to save failure.")

        else:
            print("Skipping room calculation and retrieval tests due to main calculation save failure.")
    else:
        print("Supabase client not initialized. Skipping all SupabaseManager tests.")

    # Clean up dummy image
    if dummy_image_path and os.path.exists(dummy_image_path):
        os.remove(dummy_image_path)
        print(f"Cleaned up dummy image: {dummy_image_path}")