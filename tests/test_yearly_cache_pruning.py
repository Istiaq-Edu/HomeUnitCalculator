from src.ui.background_workers import (
    SyncSupabaseMainCalculationsYearWorker,
    SyncSupabaseRoomCalculationsYearWorker,
)


class _FakeDBManager:
    def __init__(self, sync_state=None):
        self.sync_state = dict(sync_state or {})
        self.deleted_main = []
        self.deleted_room = []
        self.deleted_room_by_main = []
        self.upserted_main = None
        self.upserted_room = None

    def bootstrap_dashboard_cache_tables(self):
        return None

    def get_sync_state(self, key):
        return self.sync_state.get(key)

    def set_sync_state(self, key, value):
        self.sync_state[key] = value

    def upsert_main_calculations_cache(self, records, source="supabase"):
        self.upserted_main = list(records)

    def delete_missing_main_calculations_cache(
        self, year, valid_record_ids, source="supabase"
    ):
        self.deleted_main.append((year, list(valid_record_ids), source))

    def upsert_room_calculations_cache(self, entries, source="supabase"):
        self.upserted_room = list(entries)

    def delete_missing_room_calculations_cache(
        self, year, valid_room_record_ids, source="supabase"
    ):
        self.deleted_room.append((year, list(valid_room_record_ids), source))

    def delete_missing_room_calculations_for_main_record(
        self, main_record_id, valid_room_record_ids, source="supabase"
    ):
        self.deleted_room_by_main.append(
            (main_record_id, list(valid_room_record_ids), source)
        )

    def close(self):
        return None


class _FakeSupabaseMainManager:
    def __init__(self, delta_records, field_used="updated_at", full_records=None):
        self.delta_records = list(delta_records)
        self.field_used = field_used
        self.full_records = list(
            full_records if full_records is not None else delta_records
        )

    def is_client_initialized(self):
        return True

    def get_main_calculations_for_year_delta(self, **_kwargs):
        return list(self.delta_records), self.field_used

    def get_main_calculations(self, year):
        return list(self.full_records)


class _FakeSupabaseRoomManager(_FakeSupabaseMainManager):
    def __init__(
        self,
        delta_records,
        room_records_by_main,
        field_used="updated_at",
        full_records=None,
    ):
        super().__init__(
            delta_records, field_used=field_used, full_records=full_records
        )
        self.room_records_by_main = room_records_by_main

    def get_room_calculations_bulk(self, ids):
        return {str(i): list(self.room_records_by_main.get(str(i), [])) for i in ids}


def test_main_yearly_sync_prunes_only_on_full_sync(monkeypatch):
    import src.core.db_manager as db_manager_module

    full_db = _FakeDBManager()
    monkeypatch.setattr(db_manager_module, "DBManager", lambda _path: full_db)
    worker = SyncSupabaseMainCalculationsYearWorker(
        _FakeSupabaseMainManager(
            [
                {
                    "id": 1,
                    "month": "January",
                    "year": 2025,
                    "updated_at": "2025-01-10T00:00:00",
                    "main_data": {},
                }
            ]
        ),
        "test.db",
        2025,
    )
    worker.run()

    assert full_db.deleted_main == [(2025, [1], "supabase")]

    delta_db = _FakeDBManager(
        {"supabase_main_calculations_year_2025_updated_at": "2025-01-01T00:00:00"}
    )
    monkeypatch.setattr(db_manager_module, "DBManager", lambda _path: delta_db)
    worker = SyncSupabaseMainCalculationsYearWorker(
        _FakeSupabaseMainManager(
            [
                {
                    "id": 2,
                    "month": "February",
                    "year": 2025,
                    "updated_at": "2025-02-10T00:00:00",
                    "main_data": {},
                }
            ]
        ),
        "test.db",
        2025,
    )
    worker.run()

    assert delta_db.deleted_main == []


def test_room_yearly_sync_prunes_only_on_full_sync(monkeypatch):
    import src.core.db_manager as db_manager_module

    full_db = _FakeDBManager()
    monkeypatch.setattr(db_manager_module, "DBManager", lambda _path: full_db)
    worker = SyncSupabaseRoomCalculationsYearWorker(
        _FakeSupabaseRoomManager(
            [{"id": 1, "month": "January", "year": 2025}],
            {"1": [{"id": 10, "room_data": {"room_name": "101", "grand_total": 100}}]},
        ),
        "test.db",
        2025,
    )
    worker.run()

    assert full_db.deleted_room == [(2025, [10], "supabase")]
    assert full_db.deleted_room_by_main == []

    delta_db = _FakeDBManager(
        {"supabase_main_calculations_year_2025_updated_at": "2025-01-01T00:00:00"}
    )
    monkeypatch.setattr(db_manager_module, "DBManager", lambda _path: delta_db)
    worker = SyncSupabaseRoomCalculationsYearWorker(
        _FakeSupabaseRoomManager(
            [{"id": 2, "month": "February", "year": 2025}],
            {"2": [{"id": 20, "room_data": {"room_name": "102", "grand_total": 200}}]},
        ),
        "test.db",
        2025,
    )
    worker.run()

    assert delta_db.deleted_room == []
    assert delta_db.deleted_room_by_main == [(2, [20], "supabase")]
