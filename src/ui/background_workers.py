from PyQt5.QtCore import QThread, pyqtSignal
from postgrest.exceptions import APIError
from gotrue.errors import AuthApiError
import logging

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
            self.error_occurred.emit(f"API Error: {e.message}")
        except AuthApiError as e:
            logging.error(f"Supabase Auth Error fetching rental records: {e}")
            self.error_occurred.emit(f"Authentication Error: {e.message}")
        except Exception as exc:
            logging.error(f"An unexpected error occurred fetching rental records: {exc}", exc_info=True)
            self.error_occurred.emit(f"An unexpected error occurred: {exc}")


class FetchImageWorker(QThread):
    """Background worker to fetch an image from a URL without blocking the UI."""

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