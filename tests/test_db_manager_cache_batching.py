from pathlib import Path

import pytest


@pytest.fixture
def db_manager_module(monkeypatch, tmp_path):
    import src.core.db_manager as db_manager_module

    class DummyEncryptionUtil:
        def encrypt_data(self, data):
            return data.encode()

        def decrypt_data(self, encrypted_data):
            return encrypted_data.decode()

    monkeypatch.setattr(db_manager_module, "EncryptionUtil", DummyEncryptionUtil)
    return db_manager_module


@pytest.fixture
def db_manager(db_manager_module, tmp_path):
    db_path = tmp_path / "test_app.db"
    manager = db_manager_module.DBManager(str(db_path))
    manager.bootstrap_dashboard_cache_tables()
    manager.bootstrap_rentals_table()
    yield manager
    manager.close()


def test_db_connection_uses_wal_and_busy_timeout(db_manager):
    journal_mode_row = db_manager.execute_query("PRAGMA journal_mode;", fetch_one=True)
    busy_timeout_row = db_manager.execute_query("PRAGMA busy_timeout;", fetch_one=True)

    assert str(journal_mode_row[0]).lower() == "wal"
    assert int(busy_timeout_row[0]) == 5000


def test_expected_cache_and_rental_indexes_exist(db_manager):
    rows = db_manager.execute_query(
        "SELECT name FROM sqlite_master WHERE type = 'index' ORDER BY name"
    )
    index_names = {row["name"] for row in rows}

    assert "idx_main_calc_source_year_month" in index_names
    assert "idx_room_calc_source_year_room_month" in index_names
    assert "idx_room_calc_source_main_record" in index_names
    assert "idx_rental_records_cache_room_created" in index_names
    assert "idx_rentals_archived_created" in index_names
    assert "idx_rentals_archived_updated" in index_names
    assert "idx_rentals_room_created" in index_names


def test_upsert_main_calculations_cache_replaces_existing_month_year(db_manager):
    db_manager.upsert_main_calculations_cache(
        [
            {
                "id": 1,
                "month": "January",
                "year": 2025,
                "main_data": {
                    "grand_total": 1000,
                    "added_amount": 50,
                    "per_unit_cost": 10,
                },
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00",
            },
            {
                "id": 2,
                "month": "February",
                "year": 2025,
                "main_data": {
                    "grand_total": 2000,
                    "added_amount": 75,
                    "per_unit_cost": 20,
                },
                "created_at": "2025-02-01T00:00:00",
                "updated_at": "2025-02-02T00:00:00",
            },
        ]
    )

    db_manager.upsert_main_calculations_cache(
        [
            {
                "id": 3,
                "month": "January",
                "year": 2025,
                "main_data": {
                    "grand_total": 1500,
                    "added_amount": 60,
                    "per_unit_cost": 15,
                },
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-03T00:00:00",
            }
        ]
    )

    rows = db_manager.execute_query(
        "SELECT record_id, month, year, grand_total, added_amount FROM main_calculations_cache ORDER BY month"
    )

    assert len(rows) == 2
    assert rows[0]["month"] == "February"
    assert rows[1]["month"] == "January"
    assert rows[1]["record_id"] == "3"
    assert rows[1]["grand_total"] == 1500
    assert rows[1]["added_amount"] == 60


def test_upsert_rental_records_cache_replaces_matching_supabase_id(db_manager):
    db_manager.upsert_rental_records_cache(
        [
            {
                "id": "abc",
                "tenant_name": "Alice",
                "room_number": "101",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00",
                "start_year": 2025,
                "start_month": 1,
                "end_year": 2025,
                "end_month": 12,
                "is_archived": 0,
            },
            {
                "id": "def",
                "tenant_name": "Bob",
                "room_number": "102",
                "created_at": "2025-02-01T00:00:00",
                "updated_at": "2025-02-02T00:00:00",
                "start_year": 2025,
                "start_month": 2,
                "end_year": 2025,
                "end_month": 11,
                "is_archived": 0,
            },
        ]
    )

    db_manager.upsert_rental_records_cache(
        [
            {
                "supabase_id": "abc",
                "tenant_name": "Alice Updated",
                "room_number": "201",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-03-01T00:00:00",
                "start_year": 2025,
                "start_month": 3,
                "end_year": 2026,
                "end_month": 1,
                "is_archived": 1,
            }
        ]
    )

    rows = db_manager.execute_query(
        "SELECT supabase_id, tenant_name, room_number, is_archived FROM rental_records_cache ORDER BY supabase_id"
    )

    assert len(rows) == 2
    assert rows[0]["supabase_id"] == "abc"
    assert rows[0]["tenant_name"] == "Alice Updated"
    assert rows[0]["room_number"] == "201"
    assert rows[0]["is_archived"] == 1


def test_delete_missing_rental_records_cache_removes_stale_rows(db_manager):
    db_manager.upsert_rental_records_cache(
        [
            {
                "id": "abc",
                "tenant_name": "Alice",
                "room_number": "101",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-02T00:00:00",
                "start_year": 2025,
                "start_month": 1,
                "end_year": 2025,
                "end_month": 12,
                "is_archived": 0,
            },
            {
                "id": "def",
                "tenant_name": "Bob",
                "room_number": "102",
                "created_at": "2025-02-01T00:00:00",
                "updated_at": "2025-02-02T00:00:00",
                "start_year": 2025,
                "start_month": 2,
                "end_year": 2025,
                "end_month": 11,
                "is_archived": 0,
            },
        ]
    )

    db_manager.delete_missing_rental_records_cache(["abc"], source="supabase")

    rows = db_manager.execute_query(
        "SELECT supabase_id FROM rental_records_cache ORDER BY supabase_id"
    )

    assert [row["supabase_id"] for row in rows] == ["abc"]


def test_get_cached_dashboard_year_snapshot_reads_totals_rates_and_last_sync(
    db_manager,
):
    db_manager.execute_query(
        """
        INSERT INTO main_calculations_cache
            (source, record_id, month, year, grand_total, added_amount, main_data_json, created_at, updated_at, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "supabase",
            "1",
            "January",
            2025,
            100.0,
            10.0,
            '{"per_unit_cost": 5.5, "total_unit_cost": 500}',
            "2025-01-01T00:00:00",
            "2025-01-02T00:00:00",
            "2025-01-10T00:00:00",
        ),
    )
    db_manager.execute_query(
        """
        INSERT INTO main_calculations_cache
            (source, record_id, month, year, grand_total, added_amount, main_data_json, created_at, updated_at, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "supabase",
            "2",
            "February",
            2025,
            200.0,
            20.0,
            "{bad json",
            "2025-02-01T00:00:00",
            "2025-02-02T00:00:00",
            "2025-02-10T00:00:00",
        ),
    )

    snapshot = db_manager.get_cached_dashboard_year_snapshot(2025)

    assert snapshot["monthly_totals"]["January"] == 100.0
    assert snapshot["monthly_totals"]["February"] == 200.0
    assert snapshot["monthly_per_unit_cost"]["January"] == 5.5
    assert snapshot["monthly_per_unit_cost"]["February"] is None
    assert snapshot["monthly_total_electricity_bills"]["January"] == 500.0
    assert snapshot["monthly_total_electricity_bills"]["February"] is None
    assert snapshot["last_sync"] == "2025-02-10T00:00:00"


def test_delete_missing_main_calculations_cache_removes_stale_year_rows_only(
    db_manager,
):
    db_manager.upsert_main_calculations_cache(
        [
            {
                "id": 1,
                "month": "January",
                "year": 2025,
                "main_data": {"grand_total": 100},
            },
            {
                "id": 2,
                "month": "February",
                "year": 2025,
                "main_data": {"grand_total": 200},
            },
            {
                "id": 3,
                "month": "January",
                "year": 2024,
                "main_data": {"grand_total": 300},
            },
        ]
    )

    db_manager.delete_missing_main_calculations_cache(2025, [1], source="supabase")

    rows = db_manager.execute_query(
        "SELECT record_id, year FROM main_calculations_cache ORDER BY year, record_id"
    )

    assert [(row["record_id"], row["year"]) for row in rows] == [
        ("3", 2024),
        ("1", 2025),
    ]


def test_delete_missing_room_calculations_cache_removes_stale_year_rows_only(
    db_manager,
):
    db_manager.upsert_room_calculations_cache(
        [
            {
                "main_record_id": 1,
                "room_record_id": 10,
                "month": "January",
                "year": 2025,
                "room_name": "101",
                "grand_total": 100,
                "room_data": {"room_name": "101"},
            },
            {
                "main_record_id": 2,
                "room_record_id": 20,
                "month": "February",
                "year": 2025,
                "room_name": "102",
                "grand_total": 200,
                "room_data": {"room_name": "102"},
            },
            {
                "main_record_id": 3,
                "room_record_id": 30,
                "month": "January",
                "year": 2024,
                "room_name": "103",
                "grand_total": 300,
                "room_data": {"room_name": "103"},
            },
        ]
    )

    db_manager.delete_missing_room_calculations_cache(2025, [10], source="supabase")

    rows = db_manager.execute_query(
        "SELECT room_record_id, year FROM room_calculations_cache ORDER BY year, room_record_id"
    )

    assert [(row["room_record_id"], row["year"]) for row in rows] == [
        ("30", 2024),
        ("10", 2025),
    ]


def test_delete_missing_room_calculations_for_main_record_removes_only_that_parent_rows(
    db_manager,
):
    db_manager.upsert_room_calculations_cache(
        [
            {
                "main_record_id": 1,
                "room_record_id": 10,
                "month": "January",
                "year": 2025,
                "room_name": "101",
                "grand_total": 100,
                "room_data": {"room_name": "101"},
            },
            {
                "main_record_id": 1,
                "room_record_id": 11,
                "month": "January",
                "year": 2025,
                "room_name": "102",
                "grand_total": 110,
                "room_data": {"room_name": "102"},
            },
            {
                "main_record_id": 2,
                "room_record_id": 20,
                "month": "February",
                "year": 2025,
                "room_name": "201",
                "grand_total": 200,
                "room_data": {"room_name": "201"},
            },
        ]
    )

    db_manager.delete_missing_room_calculations_for_main_record(
        1, [10], source="supabase"
    )

    rows = db_manager.execute_query(
        "SELECT main_record_id, room_record_id FROM room_calculations_cache ORDER BY main_record_id, room_record_id"
    )

    assert [(row["main_record_id"], row["room_record_id"]) for row in rows] == [
        ("1", "10"),
        ("2", "20"),
    ]
