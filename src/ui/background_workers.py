from PyQt5.QtCore import QThread, pyqtSignal
from postgrest.exceptions import APIError
from gotrue.errors import AuthApiError
import logging
from typing import Dict, List, Optional
from src.core.supabase_error_handler import SupabaseErrorHandler

class FetchSupabaseRentalRecordsWorker(QThread):
    """Background worker that retrieves rental records from Supabase without blocking the UI."""

    records_fetched = pyqtSignal(list)  # Emitted with the list of records on success
    error_occurred = pyqtSignal(str)    # Emitted with an error message if something goes wrong

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
            if not self._supabase_manager or not self._supabase_manager.is_client_initialized():
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
            logging.error(f"An unexpected error occurred fetching rental records: {exc}", exc_info=True)
            # Detect if it's a paused project
            error_type = SupabaseErrorHandler.detect_error_type(exc)
            logging.info(f"[DEBUG] Detected error type: {error_type} for exception: {str(exc)[:100]}")
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
            if not self._supabase_manager or not self._supabase_manager.is_client_initialized():
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
            if not self._supabase_manager or not self._supabase_manager.is_client_initialized():
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

                records, field_used = self._supabase_manager.get_main_calculations_for_year_delta(
                    year=self._year,
                    since=since,
                    since_field=since_field,
                )

                if field_used != "updated_at":
                    records = self._supabase_manager.get_main_calculations(year=self._year) or records
                    field_used = None

                if records:
                    local_db.upsert_main_calculations_cache(records, source="supabase")
                    if field_used in ("updated_at", "created_at"):
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


class FetchImageWorker(QThread):
    """
    Background worker to fetch an image from a URL without blocking the UI.
    
    DEPRECATED: Use FetchMultipleImagesWorker for better performance with parallel downloads.
    This class is kept for backward compatibility.
    """

    image_downloaded = pyqtSignal(bytes)  # Emitted with image bytes on success
    error_occurred = pyqtSignal(str)      # Emitted with an error message on failure

    def __init__(self, url: str, timeout: int = 8, verify_tls: bool = False, parent=None):
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
            logging.info(f"⚡ Starting parallel fetch of {len(valid_urls)} {image_type}...")
            
            # Get the global optimized fetcher
            fetcher = get_global_fetcher()
            
            # Fetch all images in parallel (with thumbnail generation if for_display=True)
            results = fetcher.fetch_multiple_parallel(valid_urls, for_display=self._for_display)
            
            # Emit results
            self.images_fetched.emit(results)
            
            # Log cache statistics
            stats = fetcher.get_cache_stats()
            logging.info(f"📊 Cache stats: {stats['cache_hits']} hits, "
                        f"{stats['cache_misses']} misses, "
                        f"{stats['hit_rate_percent']:.1f}% hit rate")
            
        except Exception as exc:
            logging.error(f"Error in parallel image fetch: {exc}", exc_info=True)
            self.error_occurred.emit(str(exc))
