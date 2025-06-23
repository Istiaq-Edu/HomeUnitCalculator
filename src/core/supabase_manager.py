import os
import json
from supabase import create_client, Client
from postgrest.exceptions import APIError
from gotrue.errors import AuthApiError
from src.core.db_manager import DBManager # To get Supabase URL and Key
from datetime import datetime

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

        print(f"DEBUG: Connecting to Supabase project with URL: {supabase_url}")

        try:
            self.supabase = create_client(supabase_url, supabase_key)
            print("Supabase client initialized successfully from stored config.")
        except Exception as e:
            self.supabase = None
            print(f"Failed to initialize Supabase client: {e}")

    def is_client_initialized(self) -> bool:
        """Checks if the Supabase client is initialized and ready for use."""
        return self.supabase is not None

    def upload_image(self, local_file_path: str, bucket_name: str = "rental-images", folder: str = "rentals") -> str | None:
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
                # Set "upsert" to "true" (as a string) in file_options to overwrite if it exists.
                self.supabase.storage.from_(bucket_name).upload(
                    path=storage_path, 
                    file=f.read(), 
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )
                
                # If we reach here, the upload was successful. Get the public URL.
                public_url_response = self.supabase.storage.from_(bucket_name).get_public_url(storage_path)
                return public_url_response
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
            query = self.supabase.table("main_calculations").select("id, month, year, main_data")
            if month is not None:
                query = query.eq("month", month)
            if year is not None:
                query = query.eq("year", year)
            
            # If both are None, it's effectively get_all_main_calculations, but with limit 1
            # If only one is None, it filters by the other.
            response = query.limit(1).execute()
            if response.data:
                return response.data[0] # Return the full record
            return None
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving main calculation: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred retrieving main calculation: {e}")
            return None

    def get_main_calculations(self, month: str | None = None, year: int | None = None) -> list[dict]:
        """
        Retrieves main calculation records from Supabase, optionally filtered by month and year.
        If both month and year are None, it retrieves all records.
        :param month: The month of the calculation (optional).
        :param year: The year of the calculation (optional).
        :return: A list of main calculation records.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve main calculations.")
            return []
        try:
            query = self.supabase.table("main_calculations").select("id, month, year, main_data")
            
            if month is not None:
                query = query.eq("month", month)
            if year is not None:
                query = query.eq("year", year)
            
            response = query.order("year", desc=True).order("created_at", desc=True).execute()
            return response.data if response.data else []
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving main calculations: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred retrieving main calculations: {e}")
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

    def _upload_rental_images(self, image_paths: dict) -> dict:
        """Upload local images and return mapping key->url. Existing URLs are passed through."""
        image_urls = {}
        for key, path in image_paths.items():
            if not path:
                continue
            # If the path is already an http URL, assume it's already uploaded
            if str(path).lower().startswith("http"):
                image_urls[key] = path
                continue
            # Otherwise upload only if the file exists locally
            if os.path.exists(path):
                url = self.upload_image(path)
                if url:
                    image_urls[key] = url
        return image_urls

    def save_rental_record(self, record_data: dict, image_paths: dict) -> str:
        """
        Saves a rental record to Supabase, including uploading images.
        Uses separate columns for each piece of data.
        """
        if not self.is_client_initialized():
            return "Error: Supabase client not initialized."

        try:
            # Step 1: Upload images and get URLs
            image_urls = self._upload_rental_images(image_paths)

            # Check for upload failures before proceeding
            for key, path in image_paths.items():
                if path and not str(path).lower().startswith("http") and not image_urls.get(key):
                    return f"Error: Failed to upload image for {key}."

            # Step 2: Prepare the record for insertion/update
            record_to_save = {
                "tenant_name": record_data.get("tenant_name"),
                "room_number": record_data.get("room_number"),
                "advanced_paid": record_data.get("advanced_paid"),
                "photo_url": image_urls.get("photo"),
                "nid_front_url": image_urls.get("nid_front"),
                "nid_back_url": image_urls.get("nid_back"),
                "police_form_url": image_urls.get("police_form"),
                "is_archived": record_data.get("is_archived", False),
                "updated_at": datetime.now().isoformat()
            }

            # Step 3: Insert or Update the record
            if record_data.get("id"):
                # Update existing record by primary key id
                response = self.supabase.table("rental_records").update(record_to_save).eq("id", record_data["id"]).execute()
            else:
                # Insert new record
                response = self.supabase.table("rental_records").insert(record_to_save).execute()

            if response.data:
                return f"Successfully saved record for {record_data.get('tenant_name')}."
            else:
                # This path should ideally not be taken if exceptions are handled, but as a fallback.
                return f"Error: Failed to save record to Supabase. Response: {response}"

        except Exception as e:
            return f"Error saving rental record: {e}"

    def get_rental_records(self, is_archived: bool | None = None) -> list[dict]:
        """
        Retrieves rental records from Supabase, optionally filtering by archive status.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve rental records.")
            return []
        try:
            # Select individual columns
            query = self.supabase.table("rental_records").select(
                "id, supabase_id, tenant_name, room_number, advanced_paid, photo_url, nid_front_url, nid_back_url, police_form_url, is_archived, created_at, updated_at"
            )

            if is_archived is not None:
                query = query.eq("is_archived", is_archived)

            response = query.order("created_at", desc=True).execute()

            return response.data if response.data else []

        except Exception as e:
            print(f"Supabase API error retrieving rental records: {e}")
            return []

    def update_rental_record_archive_status(self, supabase_id: str, is_archived: bool) -> bool:
        """
        Updates the is_archived status of a rental record in Supabase.
        :param supabase_id: The supabase_id of the rental record to update.
        :param is_archived: The new archive status (True for archived, False for active).
        :return: True if successful, False otherwise.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot update archive status.")
            return False
        try:
            response = self.supabase.table("rental_records").update({"is_archived": is_archived}).eq("supabase_id", supabase_id).execute()
            if response.data:
                print(f"Rental record supabase_id {supabase_id} archive status updated to {is_archived}.")
                return True
            else:
                print(f"Failed to update archive status for record supabase_id {supabase_id}: {response.json()}")
                return False
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error updating archive status: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred updating archive status: {e}")
            return False

    def delete_rental_record(self, record_identifier) -> bool:
        """
        Deletes a rental record from Supabase.
        Note: This does NOT delete associated images from Supabase Storage.
        Image deletion would require tracking image URLs and calling storage.remove().
        For simplicity, we're only deleting the record here.
        :param record_identifier: Either numeric primary-key id or uuid supabase_id.
        :return: True if successful, False otherwise.
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot delete rental record.")
            return False
        try:
            col = "id" if isinstance(record_identifier, int) or str(record_identifier).isdigit() else "supabase_id"
            response = self.supabase.table("rental_records").delete().eq(col, record_identifier).execute()
            if response.data:
                print(f"Rental record {record_identifier} deleted.")
                return True
            else:
                print(f"Failed to delete rental record {record_identifier}: {response.json()}")
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
            rental_id = manager.save_rental_record(test_rental_data, image_paths={"photo": dummy_image_path, "nid_front": dummy_image_path})
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
                updated_id = manager.save_rental_record(updated_rental_data, image_paths={"photo": None, "nid_front": dummy_image_path})
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