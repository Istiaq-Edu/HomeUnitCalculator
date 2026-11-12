from src.ui.background_workers import FetchSupabaseHistoryWorker
from src.ui.tabs.history_tab import HistoryTab


class _FakeSupabaseManager:
    def __init__(self, main_records, room_records_by_main):
        self.main_records = list(main_records)
        self.room_records_by_main = dict(room_records_by_main)
        self.calls = []

    def is_client_initialized(self):
        return True

    def get_main_calculations(self, month=None, year=None):
        self.calls.append(("main", month, year))
        return list(self.main_records)

    def get_room_calculations_bulk(self, ids):
        self.calls.append(("rooms", list(ids)))
        return dict(self.room_records_by_main)


def test_fetch_supabase_history_worker_emits_main_and_grouped_room_records():
    manager = _FakeSupabaseManager(
        [{"id": 1, "month": "January", "year": 2025, "main_data": {}}],
        {"1": [{"id": 10, "room_data": {"room_name": "101"}}]},
    )
    worker = FetchSupabaseHistoryWorker(
        manager, month_filter="January", year_filter=2025
    )
    seen = []
    worker.history_fetched.connect(lambda main, rooms: seen.append((main, rooms)))

    worker.run()

    assert manager.calls == [("main", "January", 2025), ("rooms", [1])]
    assert len(seen) == 1
    assert seen[0][0][0]["id"] == 1
    assert seen[0][1]["1"][0]["id"] == 10


def test_prepare_supabase_history_records_uses_prefetched_room_map_without_refetch():
    history = HistoryTab.__new__(HistoryTab)
    history.main_window = type("MainWindow", (), {})()

    class _NoFetchSupabaseManager:
        def get_room_calculations_bulk(self, _ids):
            raise AssertionError(
                "Should not refetch room data when prefetched map is provided"
            )

    history.main_window.supabase_manager = _NoFetchSupabaseManager()
    main_calculations = [{"id": 1, "month": "January", "year": 2025, "main_data": {}}]
    prefetched = {"1": [{"id": 10, "room_data": {"room_name": "101"}}]}

    records_with_rooms, all_room_rows = history._prepare_supabase_history_records(
        main_calculations,
        room_records_by_main_id=prefetched,
    )

    assert records_with_rooms[0]["room_records"][0]["room_data"]["room_name"] == "101"
    assert all_room_rows[0]["month"] == "January"
