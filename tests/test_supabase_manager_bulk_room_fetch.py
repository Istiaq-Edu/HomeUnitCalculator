from src.core.supabase_manager import SupabaseManager


class _FakeQuery:
    def __init__(self, records):
        self._records = records
        self._ids = []

    def select(self, _fields):
        return self

    def in_(self, _column, ids):
        self._ids = list(ids)
        return self

    def order(self, _column):
        return self

    def execute(self):
        filtered = [
            record
            for record in self._records
            if str(record.get("main_calculation_id")) in self._ids
        ]
        return type("Response", (), {"data": filtered})()


class _FakeSupabase:
    def __init__(self, records):
        self._records = records

    def table(self, _name):
        return _FakeQuery(self._records)


def test_get_room_calculations_bulk_groups_rows_by_main_record_id():
    manager = object.__new__(SupabaseManager)
    manager.supabase = _FakeSupabase(
        [
            {"id": 10, "main_calculation_id": 1, "room_data": {"room_name": "Room 1"}},
            {"id": 11, "main_calculation_id": 1, "room_data": {"room_name": "Room 2"}},
            {"id": 20, "main_calculation_id": 2, "room_data": {"room_name": "Room A"}},
        ]
    )
    manager.is_client_initialized = lambda: True

    grouped = manager.get_room_calculations_bulk([1, 2])

    assert list(grouped.keys()) == ["1", "2"]
    assert [row["id"] for row in grouped["1"]] == [10, 11]
    assert grouped["1"][0]["room_data"]["room_name"] == "Room 1"
    assert grouped["2"][0]["room_data"]["room_name"] == "Room A"


def test_get_room_calculations_bulk_returns_empty_for_no_ids():
    manager = object.__new__(SupabaseManager)
    manager.supabase = _FakeSupabase([])
    manager.is_client_initialized = lambda: True

    assert manager.get_room_calculations_bulk([]) == {}
