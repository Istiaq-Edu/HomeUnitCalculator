from src.ui.tabs.archived_info_tab import ArchivedInfoTab
from src.ui.tabs.rental_info_tab import RentalInfoTab


class _DummyItem:
    def __init__(self, payload):
        self.payload = payload

    def data(self, _role):
        return self.payload


class _DummyTable:
    def __init__(self, payloads, current_row=-1):
        self._payloads = payloads
        self._current_row = current_row
        self.selected_rows = []
        self.current_cells = []

    def currentRow(self):
        return self._current_row

    def item(self, row, col):
        if col != 0 or row < 0 or row >= len(self._payloads):
            return None
        payload = self._payloads[row]
        if payload is None:
            return None
        return _DummyItem(payload)

    def rowCount(self):
        return len(self._payloads)

    def selectRow(self, row):
        self.selected_rows.append(row)

    def setCurrentCell(self, row, col):
        self.current_cells.append((row, col))


def test_rental_selection_helper_restores_by_supabase_id():
    rental = RentalInfoTab.__new__(RentalInfoTab)
    rental.rental_records_table = _DummyTable(
        [
            {"supabase_id": "a1", "tenant_name": "Alice"},
            {"supabase_id": "b2", "tenant_name": "Bob"},
        ]
    )

    rental._restore_record_selection("b2")

    assert rental.rental_records_table.selected_rows == [1]
    assert rental.rental_records_table.current_cells == [(1, 0)]


def test_archived_selected_record_key_prefers_supabase_id_then_id():
    archived = ArchivedInfoTab.__new__(ArchivedInfoTab)
    archived.archived_records_table = _DummyTable(
        [
            (7, "Tenant", "101", 0, "", "", "", "", "", "", 1, "sup-7"),
        ],
        current_row=0,
    )

    assert archived._get_selected_record_key() == "sup-7"
