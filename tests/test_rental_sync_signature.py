from src.ui.background_workers import SyncSupabaseRentalRecordsCacheWorker


class _FakeDBManager:
    def __init__(self, initial_state=None):
        self.state = dict(initial_state or {})
        self.upserted_records = None
        self.deleted_ids = None

    def bootstrap_dashboard_cache_tables(self):
        return None

    def get_sync_state(self, key):
        return self.state.get(key)

    def set_sync_state(self, key, value):
        self.state[key] = value

    def upsert_rental_records_cache(self, records, source="supabase"):
        self.upserted_records = list(records)

    def delete_missing_rental_records_cache(
        self, valid_supabase_ids, source="supabase"
    ):
        self.deleted_ids = list(valid_supabase_ids)

    def close(self):
        return None


class _FakeSupabaseManager:
    def __init__(self, signature_rows, full_rows=None):
        self.signature_rows = list(signature_rows)
        self.full_rows = list(full_rows if full_rows is not None else signature_rows)
        self.calls = []

    def is_client_initialized(self):
        return True

    def get_rental_records(self, **kwargs):
        self.calls.append(kwargs)
        select = kwargs.get("select")
        if select == "id, supabase_id, created_at, updated_at":
            return list(self.signature_rows)
        return list(self.full_rows)


def test_rental_signature_is_order_independent():
    rows_a = [
        {"supabase_id": "b", "updated_at": "2025-02-01T00:00:00"},
        {"supabase_id": "a", "updated_at": "2025-01-01T00:00:00"},
    ]
    rows_b = list(reversed(rows_a))

    assert SyncSupabaseRentalRecordsCacheWorker._build_rental_signature(
        rows_a
    ) == SyncSupabaseRentalRecordsCacheWorker._build_rental_signature(rows_b)


def test_rental_sync_skips_full_fetch_when_signature_matches(monkeypatch):
    signature_rows = [
        {
            "supabase_id": "abc",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-02T00:00:00",
        }
    ]
    existing_signature = SyncSupabaseRentalRecordsCacheWorker._build_rental_signature(
        signature_rows
    )
    fake_db = _FakeDBManager(
        {"supabase_rental_records_cache_signature": existing_signature}
    )
    fake_supabase = _FakeSupabaseManager(signature_rows)

    import src.core.db_manager as db_manager_module

    monkeypatch.setattr(db_manager_module, "DBManager", lambda _path: fake_db)

    worker = SyncSupabaseRentalRecordsCacheWorker(fake_supabase, "test.db")
    worker.run()

    assert len(fake_supabase.calls) == 1
    assert fake_db.upserted_records is None
    assert fake_db.deleted_ids is None


def test_rental_sync_runs_full_fetch_and_updates_signature_when_changed(monkeypatch):
    signature_rows = [
        {
            "supabase_id": "abc",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-02T00:00:00",
        }
    ]
    full_rows = [
        {
            "supabase_id": "abc",
            "tenant_name": "Alice",
            "room_number": "101",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-02T00:00:00",
            "is_archived": 0,
        }
    ]
    fake_db = _FakeDBManager()
    fake_supabase = _FakeSupabaseManager(signature_rows, full_rows=full_rows)

    import src.core.db_manager as db_manager_module

    monkeypatch.setattr(db_manager_module, "DBManager", lambda _path: fake_db)

    worker = SyncSupabaseRentalRecordsCacheWorker(fake_supabase, "test.db")
    worker.run()

    assert len(fake_supabase.calls) == 2
    assert fake_db.upserted_records == full_rows
    assert fake_db.deleted_ids == ["abc"]
    assert fake_db.state["supabase_rental_records_cache_signature"] == (
        SyncSupabaseRentalRecordsCacheWorker._build_rental_signature(signature_rows)
    )
