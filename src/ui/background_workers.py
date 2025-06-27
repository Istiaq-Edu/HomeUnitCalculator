from PyQt5.QtCore import QThread, pyqtSignal

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
            records = self._supabase_manager.get_rental_records(is_archived=self._is_archived)
            # Ensure a list is always emitted (even if empty) to signal completion.
            self.records_fetched.emit(records or [])
        except Exception as exc:
            # Emit the string representation of the error so the UI thread can handle it.
            self.error_occurred.emit(str(exc)) 