import os
import json
# Apply compatibility patch before importing supabase
try:
    from src.core.supabase_patch import *
except ImportError:
    pass
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


        try:
            self.supabase = create_client(supabase_url, supabase_key)
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
        Existing room calculations are **replaced** in a two-step process that mimics a
        transaction: we first insert the new records and only if that succeeds do we
        delete the previous ones. This prevents data loss if the insert fails.
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
            # Fetch the IDs of any existing records FIRST so we can remove them **after** a successful insert.
            # This mimics a simple transaction-like behaviour to avoid permanent data loss if the insert fails.
            old_records_resp = (
                self.supabase.table("room_calculations")
                .select("id")
                .eq("main_calculation_id", main_calc_id)
                .execute()
            )

            old_record_ids: list[int] = []
            if old_records_resp and old_records_resp.data:
                old_record_ids = [rec["id"] for rec in old_records_resp.data if "id" in rec]
                print(f"Found {len(old_record_ids)} existing room calculations that will be deleted after a successful insert.")

            records_to_insert = []
            for room_data in room_data_list:
                # Upload images and get URLs
                photo_url = self.upload_image(room_data.get("photo_path")) if room_data.get("photo_path") else None
                nid_front_url = self.upload_image(room_data.get("nid_front_path")) if room_data.get("nid_front_path") else None
                nid_back_url = self.upload_image(room_data.get("nid_back_path")) if room_data.get("nid_back_path") else None
                police_form_url = self.upload_image(room_data.get("police_form_path")) if room_data.get("police_form_path") else None

                # Determine the JSONB payload for room_data
                if "room_data" in room_data and isinstance(room_data["room_data"], dict):
                    room_jsonb = room_data["room_data"]
                else:
                    # Build JSONB from all keys that are not image path references
                    room_jsonb = {k: v for k, v in room_data.items() if not k.endswith("_path") and k != "room_data"}

                # Prepare data for JSONB column and URL columns
                record = {
                    "main_calculation_id": main_calc_id,
                    "room_data": room_jsonb,
                    "photo_url": photo_url,
                    "nid_front_url": nid_front_url,
                    "nid_back_url": nid_back_url,
                    "police_form_url": police_form_url
                }
                records_to_insert.append(record)
            
            if records_to_insert:
                insert_response = self.supabase.table("room_calculations").insert(records_to_insert).execute()
                if insert_response.data:
                    print(
                        f"Inserted {len(insert_response.data)} room calculation records."
                    )

                    # Only delete the old records **after** we know the insert succeeded.
                    if old_record_ids:
                        try:
                            del_resp = (
                                self.supabase.table("room_calculations")
                                .delete()
                                .in_("id", old_record_ids)
                                .execute()
                            )
                            print(
                                f"Deleted {len(old_record_ids)} old room calculation records after successful insert."
                            )
                        except Exception as delete_exc:
                            # Log the failure but do not report overall failure; duplicates are easier to handle
                            print(
                                f"Warning: Insert succeeded but deleting old room calculation records failed: {delete_exc}"
                            )

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

    def get_main_calculation_by_month_year(self, month: str, year: int) -> dict | None:
        """
        Retrieve a single `main_calculations` row that matches the given month and year.

        :param month: Month (e.g., "June").
        :param year: Year (e.g., 2025).
        :return: The full record including JSONB payload, or ``None`` if not found.
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
                # Keep room_data nested so that UI code can access it consistently
                return [
                    {
                        "room_data": record.get("room_data", {}),
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
            # Ensure the boolean property is a proper Python bool for Postgres boolean column
            is_archived_val = bool(record_data.get("is_archived", False))

            record_to_save = {
                "tenant_name": record_data.get("tenant_name"),
                "room_number": record_data.get("room_number"),
                "advanced_paid": record_data.get("advanced_paid"),
                "photo_url": image_urls.get("photo"),
                "nid_front_url": image_urls.get("nid_front"),
                "nid_back_url": image_urls.get("nid_back"),
                "police_form_url": image_urls.get("police_form"),
                "is_archived": is_archived_val,
                "updated_at": datetime.now().isoformat()
            }

            # For inserts, also populate created_at so ordering works even if the DB column lacks a default.
            if not record_data.get("id"):
                record_to_save["created_at"] = datetime.now().isoformat()

            # Step 3: Insert or Update the record
            if record_data.get("supabase_id"):
                # Update existing record using its UUID supabase_id (more stable across environments)
                response = (
                    self.supabase
                        .table("rental_records")
                        .update(record_to_save, returning="representation")
                        .eq("supabase_id", record_data["supabase_id"]).execute()
                )
            else:
                # Insert new record
                response = (
                    self.supabase
                        .table("rental_records")
                        .insert(record_to_save, returning="representation")
                        .execute()
                )

            if response.data and isinstance(response.data, list) and len(response.data) > 0:
                return f"Successfully saved record for {record_data.get('tenant_name')}. (Cloud)"
            else:
                return f"Error: Failed to save record to Supabase. Response: {response}"

        except Exception as e:
            return f"Error saving rental record: {e}"

    def get_rental_records(
        self,
        is_archived: bool | None = None,
        select: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str = "created_at",
        desc: bool = True,
    ) -> list[dict]:
        """
        Retrieve rental records with optional filtering, projection, pagination and ordering.

        Args:
            is_archived: filter by archive status if provided.
            select: comma-separated list of columns to select. Defaults to full set used previously.
            limit: page size. If provided with offset, applies Supabase range pagination.
            offset: starting row index for pagination (0-based).
            order_by: column to order by (default: created_at).
            desc: sort direction (default: True for descending).
        """
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve rental records.")
            return []
        try:
            # Default to the previously returned full set to preserve compatibility
            select_clause = (
                select
                or "id, supabase_id, tenant_name, room_number, advanced_paid, photo_url, nid_front_url, nid_back_url, police_form_url, is_archived, created_at, updated_at"
            )

            query = self.supabase.table("rental_records").select(select_clause)

            if is_archived is not None:
                query = query.eq("is_archived", is_archived)

            # Apply ordering
            try:
                query = query.order(order_by, desc=desc)
            except Exception:
                # Fallback to created_at if the provided column is invalid
                query = query.order("created_at", desc=True)

            # Apply pagination via range if both provided
            if limit is not None and offset is not None and limit > 0 and offset >= 0:
                # Supabase .range is inclusive: range(from, to)
                query = query.range(offset, offset + limit - 1)

            response = query.execute()

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

    # ------------------------------------------------------------------
    # Utility helpers used by HistoryTab (edit/delete operations)
    # ------------------------------------------------------------------

    def get_main_calculations_by_id(self, record_id: int | str) -> dict | None:
        """Retrieve a single main_calculations row by primary-key id."""
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot retrieve main calculation by id.")
            return None
        try:
            response = self.supabase.table("main_calculations").select("*").eq("id", record_id).limit(1).execute()
            return response.data[0] if response.data else None
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error retrieving main calculation by id: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error retrieving main calculation by id: {e}")
            return None

    def delete_calculation_record(self, record_id: int | str) -> bool:
        """Delete a main_calculations record and all associated room_calculations rows."""
        if not self.is_client_initialized():
            print("Supabase client not initialized. Cannot delete calculation record.")
            return False
        try:
            # First remove room_calculations rows
            self.supabase.table("room_calculations").delete().eq("main_calculation_id", record_id).execute()
            # Then remove the main_calculations row
            main_del_resp = self.supabase.table("main_calculations").delete().eq("id", record_id).execute()
            return bool(main_del_resp.data)
        except (APIError, AuthApiError) as e:
            print(f"Supabase API error deleting calculation record: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error deleting calculation record: {e}")
            return False