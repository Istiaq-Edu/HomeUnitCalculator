from PyQt5.QtCore import QThread, pyqtSignal
from postgrest.exceptions import APIError
from gotrue.errors import AuthApiError
import logging

class FetchSupabaseRentalRecordsWorker(QThread):
    """Background worker that retrieves rental records from Supabase without blocking the UI."""

    records_fetched = pyqtSignal(list)  # Emitted with the list of records on success
    error_occurred = pyqtSignal(str)    # Emitted with an error message if something goes wrong

    def __init__(self, supabase_manager, is_archived=False, parent=None):
        super().__init__(parent)
        self._supabase_manager = supabase_manager
        self._is_archived = is_archived

    def run(self):
        """Executes in a separate thread."""
        try:
            if not self._supabase_manager or not self._supabase_manager.is_client_initialized():
                self.error_occurred.emit("Supabase client not initialized.")
                return
            
            records = self._supabase_manager.get_rental_records(is_archived=self._is_archived)
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