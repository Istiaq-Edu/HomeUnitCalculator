from PyQt5.QtCore import QThread, pyqtSignal
from postgrest.exceptions import APIError
from gotrue.errors import AuthApiError
import hashlib
import json
import logging
from typing import Dict, List, Optional
from src.core.supabase_error_handler import SupabaseErrorHandler


class FetchSupabaseRentalRecordsWorker(QThread):
    """Background worker that retrieves rental records from Supabase without blocking the UI."""

    records_fetched = pyqtSignal(list)  # Emitted with the list of records on success
    error_occurred = pyqtSignal(
        str
    )  # Emitted with an error message if something goes wrong

    def __init__(
        self,
        supabase_manager,
        is_archived=False,
        select: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str = "created_at",
        desc: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._supabase_manager = supabase_manager
        self._is_archived = is_archived
        self._select = select
        self._limit = limit
        self._offset = offset
        self._order_by = order_by
        self._desc = desc

    def run(self):
        """Executes in a separate thread."""
        try:
            if (
                not self._supabase_manager
                or not self._supabase_manager.is_client_initialized()
            ):
                self.error_occurred.emit("Supabase client not initialized.")
                return

            records = self._supabase_manager.get_rental_records(
                is_archived=self._is_archived,
                select=self._select,
                limit=self._limit,
                offset=self._offset,
                order_by=self._order_by,
                desc=self._desc,
            )
            self.records_fetched.emit(records or [])
        except APIError as e:
            logging.error(f"Supabase API Error fetching rental records: {e}")
            # Detect error type for better user message
            error_type = SupabaseErrorHandler.detect_error_type(e)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")  # Special marker
            else:
                self.error_occurred.emit(f"API Error: {e.message}")
        except AuthApiError as e:
            logging.error(f"Supabase Auth Error fetching rental records: {e}")
            self.error_occurred.emit(f"Authentication Error: {e.message}")
        except Exception as exc:
            logging.error(
                f"An unexpected error occurred fetching rental records: {exc}",
                exc_info=True,
            )
            # Detect if it's a paused project
            error_type = SupabaseErrorHandler.detect_error_type(exc)
            logging.info(
                f"[DEBUG] Detected error type: {error_type} for exception: {str(exc)[:100]}"
            )
            if error_type == "paused_project":
                logging.info("[DEBUG] Emitting PAUSED_PROJECT marker")
                self.error_occurred.emit("PAUSED_PROJECT")  # Special marker
            else:
                logging.info(f"[DEBUG] Emitting generic error: {str(exc)[:100]}")
                self.error_occurred.emit(f"An unexpected error occurred: {exc}")


class FetchSupabaseAvailableYearsWorker(QThread):
    years_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, supabase_manager, parent=None):
        super().__init__(parent)
        self._supabase_manager = supabase_manager

    def run(self):
        try:
            if (
                not self._supabase_manager
                or not self._supabase_manager.is_client_initialized()
            ):
                self.error_occurred.emit("Supabase client not initialized.")
                return
            years = self._supabase_manager.get_available_years()
            self.years_fetched.emit(years or [])
        except APIError as e:
            error_type = SupabaseErrorHandler.detect_error_type(e)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"API Error: {getattr(e, 'message', str(e))}")
        except Exception as exc:
            error_type = SupabaseErrorHandler.detect_error_type(exc)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"An unexpected error occurred: {exc}")


class SyncSupabaseMainCalculationsYearWorker(QThread):
    sync_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, supabase_manager, db_path: str, year: int, parent=None):
        super().__init__(parent)
        self._supabase_manager = supabase_manager
        self._db_path = db_path
        self._year = int(year)

    def run(self):
        try:
            if (
                not self._supabase_manager
                or not self._supabase_manager.is_client_initialized()
            ):
                self.error_occurred.emit("Supabase client not initialized.")
                return
            if not self._db_path:
                self.error_occurred.emit("Database not available.")
                return

            from src.core.db_manager import DBManager

            local_db = DBManager(self._db_path)
            local_db.bootstrap_dashboard_cache_tables()
            try:
                key_updated = f"supabase_main_calculations_year_{self._year}_updated_at"
                key_created = f"supabase_main_calculations_year_{self._year}_created_at"

                since = None
                since_field = None

                last_updated = local_db.get_sync_state(key_updated)
                if last_updated:
                    since = last_updated
                    since_field = "updated_at"
                else:
                    last_created = local_db.get_sync_state(key_created)
                    if last_created:
                        since = last_created
                        since_field = "created_at"

                records, field_used = (
                    self._supabase_manager.get_main_calculations_for_year_delta(
                        year=self._year,
                        since=since,
                        since_field=since_field,
                    )
                )

                full_year_sync = since is None or field_used != "updated_at"
                if field_used != "updated_at":
                    records = (
                        self._supabase_manager.get_main_calculations(year=self._year)
                        or records
                    )
                    field_used = None

                if records:
                    local_db.upsert_main_calculations_cache(records, source="supabase")
                if full_year_sync:
                    local_db.delete_missing_main_calculations_cache(
                        self._year,
                        [record.get("id") for record in records or []],
                        source="supabase",
                    )

                if records and field_used in ("updated_at", "created_at"):
                    max_val = None
                    for r in records:
                        v = r.get(field_used)
                        if not v:
                            continue
                        if max_val is None or str(v) > str(max_val):
                            max_val = v
                    if max_val:
                        if field_used == "updated_at":
                            local_db.set_sync_state(key_updated, str(max_val))
                        else:
                            local_db.set_sync_state(key_created, str(max_val))
            finally:
                local_db.close()
            self.sync_finished.emit(self._year)
        except APIError as e:
            error_type = SupabaseErrorHandler.detect_error_type(e)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"API Error: {getattr(e, 'message', str(e))}")
        except Exception as exc:
            error_type = SupabaseErrorHandler.detect_error_type(exc)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"An unexpected error occurred: {exc}")


class SyncSupabaseRoomCalculationsYearWorker(QThread):
    sync_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, supabase_manager, db_path: str, year: int, parent=None):
        super().__init__(parent)
        self._supabase_manager = supabase_manager
        self._db_path = db_path
        self._year = int(year)

    def run(self):
        try:
            if (
                not self._supabase_manager
                or not self._supabase_manager.is_client_initialized()
            ):
                self.error_occurred.emit("Supabase client not initialized.")
                return
            if not self._db_path:
                self.error_occurred.emit("Database not available.")
                return

            from src.core.db_manager import DBManager

            local_db = DBManager(self._db_path)
            local_db.bootstrap_dashboard_cache_tables()
            try:
                key_main_updated = (
                    f"supabase_main_calculations_year_{self._year}_updated_at"
                )
                since = local_db.get_sync_state(key_main_updated)

                main_records, field_used = (
                    self._supabase_manager.get_main_calculations_for_year_delta(
                        year=self._year,
                        since=since,
                        since_field="updated_at" if since else None,
                    )
                )
                full_year_sync = since is None or field_used != "updated_at"
                if field_used != "updated_at":
                    main_records = (
                        self._supabase_manager.get_main_calculations(year=self._year)
                        or main_records
                    )
                    field_used = None

                entries = []
                room_records_by_main_id = (
                    self._supabase_manager.get_room_calculations_bulk(
                        [main.get("id") for main in main_records or []]
                    )
                )
                for main in main_records or []:
                    main_id = main.get("id")
                    month = main.get("month")
                    year_val = main.get("year")
                    if main_id is None or not month or not year_val:
                        continue
                    room_records = room_records_by_main_id.get(str(main_id), [])
                    for rr in room_records:
                        room_data = rr.get("room_data") or {}
                        entries.append(
                            {
                                "main_record_id": main_id,
                                "room_record_id": rr.get("id"),
                                "month": month,
                                "year": year_val,
                                "room_name": room_data.get("room_name"),
                                "grand_total": room_data.get("grand_total"),
                                "room_data": room_data,
                            }
                        )

                if entries:
                    local_db.upsert_room_calculations_cache(entries, source="supabase")
                if full_year_sync:
                    local_db.delete_missing_room_calculations_cache(
                        self._year,
                        [entry.get("room_record_id") for entry in entries],
                        source="supabase",
                    )
                else:
                    for main in main_records or []:
                        main_id = main.get("id")
                        if main_id is None:
                            continue
                        room_records = room_records_by_main_id.get(str(main_id), [])
                        local_db.delete_missing_room_calculations_for_main_record(
                            main_id,
                            [room.get("id") for room in room_records],
                            source="supabase",
                        )
            finally:
                local_db.close()

            self.sync_finished.emit(self._year)
        except APIError as e:
            error_type = SupabaseErrorHandler.detect_error_type(e)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"API Error: {getattr(e, 'message', str(e))}")
        except Exception as exc:
            error_type = SupabaseErrorHandler.detect_error_type(exc)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"An unexpected error occurred: {exc}")


class SyncSupabaseRentalRecordsCacheWorker(QThread):
    sync_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, supabase_manager, db_path: str, parent=None):
        super().__init__(parent)
        self._supabase_manager = supabase_manager
        self._db_path = db_path

    @staticmethod
    def _build_rental_signature(records: list[dict]) -> str:
        normalized = []
        for record in records or []:
            stable_id = record.get("supabase_id") or record.get("id")
            if stable_id is None:
                continue
            effective_timestamp = (
                record.get("updated_at") or record.get("created_at") or ""
            )
            normalized.append((str(stable_id), str(effective_timestamp)))

        normalized.sort()
        payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def run(self):
        try:
            if (
                not self._supabase_manager
                or not self._supabase_manager.is_client_initialized()
            ):
                self.error_occurred.emit("Supabase client not initialized.")
                return
            if not self._db_path:
                self.error_occurred.emit("Database not available.")
                return

            from src.core.db_manager import DBManager

            local_db = DBManager(self._db_path)
            local_db.bootstrap_dashboard_cache_tables()
            try:
                sync_state_key = "supabase_rental_records_cache_last_sync"
                signature_state_key = "supabase_rental_records_cache_signature"

                signature_rows = (
                    self._supabase_manager.get_rental_records(
                        is_archived=None,
                        select="id, supabase_id, created_at, updated_at",
                    )
                    or []
                )
                cloud_signature = self._build_rental_signature(signature_rows)
                previous_signature = local_db.get_sync_state(signature_state_key)

                if previous_signature == cloud_signature:
                    self.sync_finished.emit()
                    return

                try:
                    records = (
                        self._supabase_manager.get_rental_records(
                            is_archived=None,
                            select="id, supabase_id, tenant_name, room_number, advanced_paid, is_archived, created_at, updated_at",
                        )
                        or []
                    )
                except APIError:
                    records = (
                        self._supabase_manager.get_rental_records(is_archived=None)
                        or []
                    )

                local_db.upsert_rental_records_cache(records, source="supabase")
                local_db.delete_missing_rental_records_cache(
                    [
                        record.get("supabase_id") or record.get("id")
                        for record in records
                    ],
                    source="supabase",
                )

                if records:
                    max_updated_at = None
                    for record in records:
                        updated_at = record.get("updated_at") or record.get(
                            "created_at"
                        )
                        if not updated_at:
                            continue
                        if max_updated_at is None or str(updated_at) > str(
                            max_updated_at
                        ):
                            max_updated_at = updated_at

                    if max_updated_at:
                        local_db.set_sync_state(sync_state_key, str(max_updated_at))

                local_db.set_sync_state(signature_state_key, cloud_signature)
            finally:
                local_db.close()

            self.sync_finished.emit()
        except APIError as e:
            error_type = SupabaseErrorHandler.detect_error_type(e)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"API Error: {getattr(e, 'message', str(e))}")
        except Exception as exc:
            error_type = SupabaseErrorHandler.detect_error_type(exc)
            if error_type == "paused_project":
                self.error_occurred.emit("PAUSED_PROJECT")
            else:
                self.error_occurred.emit(f"An unexpected error occurred: {exc}")


class FetchImageWorker(QThread):
    """
    Background worker to fetch an image from a URL without blocking the UI.

    DEPRECATED: Use FetchMultipleImagesWorker for better performance with parallel downloads.
    This class is kept for backward compatibility.
    """

    image_downloaded = pyqtSignal(bytes)  # Emitted with image bytes on success
    error_occurred = pyqtSignal(str)  # Emitted with an error message on failure

    def __init__(
        self, url: str, timeout: int = 8, verify_tls: bool = False, parent=None
    ):
        super().__init__(parent)
        self._url = url
        self._timeout = timeout
        self._verify = verify_tls

    def run(self):
        try:
            import requests

            # Mirror existing behavior: allow TLS verify to be disabled in packaged builds
            resp = requests.get(self._url, timeout=self._timeout, verify=self._verify)
            if resp.status_code == 200 and resp.content:
                self.image_downloaded.emit(resp.content)
            else:
                self.error_occurred.emit(f"HTTP {resp.status_code} for {self._url}")
        except Exception as exc:
            logging.error(f"Error downloading image from {self._url}: {exc}")
            self.error_occurred.emit(str(exc))


class FetchMultipleImagesWorker(QThread):
    """
    Optimized background worker to fetch multiple images in parallel.

    This worker uses the OptimizedImageFetcher to download multiple images
    concurrently, which is 3-4x faster than sequential downloads.

    Features:
    - Parallel downloads (3-4x faster than sequential)
    - Automatic thumbnail generation for UI display
    - Full-resolution images for PDF generation
    - Disk caching for instant loading

    Example:
        Sequential (old): 4 images × 2s each = 8s total
        Parallel (new):   4 images × 2s = 2s total (4x faster!)

    Signals:
        images_fetched: Emitted with dict mapping URL to image bytes
        progress_updated: Emitted with (current, total) progress
        error_occurred: Emitted with error message if something goes wrong
    """

    images_fetched = pyqtSignal(dict)  # {url: bytes or None}
    progress_updated = pyqtSignal(int, int)  # (current, total)
    error_occurred = pyqtSignal(str)

    def __init__(self, urls: List[str], for_display: bool = True, parent=None):
        """
        Initialize the parallel image fetcher worker.

        Args:
            urls: List of image URLs to fetch
            for_display: If True, returns thumbnails (200x200) for UI display.
                        If False, returns full-resolution images (for PDF).
            parent: Parent QObject
        """
        super().__init__(parent)
        self._urls = urls
        self._for_display = for_display

    def run(self):
        """Execute parallel image fetch in background thread."""
        try:
            from src.core.optimized_image_fetcher import get_global_fetcher

            if not self._urls:
                self.images_fetched.emit({})
                return

            # Filter out empty URLs
            valid_urls = [url for url in self._urls if url and url.strip()]
            if not valid_urls:
                self.images_fetched.emit({})
                return

            image_type = "thumbnails" if self._for_display else "full-resolution images"
            logging.info(
                f"⚡ Starting parallel fetch of {len(valid_urls)} {image_type}..."
            )

            # Get the global optimized fetcher
            fetcher = get_global_fetcher()

            # Fetch all images in parallel (with thumbnail generation if for_display=True)
            results = fetcher.fetch_multiple_parallel(
                valid_urls, for_display=self._for_display
            )

            # Emit results
            self.images_fetched.emit(results)

            # Log cache statistics
            stats = fetcher.get_cache_stats()
            logging.info(
                f"📊 Cache stats: {stats['cache_hits']} hits, "
                f"{stats['cache_misses']} misses, "
                f"{stats['hit_rate_percent']:.1f}% hit rate"
            )

        except Exception as exc:
            logging.error(f"Error in parallel image fetch: {exc}", exc_info=True)
            self.error_occurred.emit(str(exc))
