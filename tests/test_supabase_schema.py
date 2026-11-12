"""Tests for Supabase schema SQL constants and version detection."""

from src.core.supabase_schema import SCHEMA_VERSION, get_migration_sql, get_version_check_sql


def test_schema_version_is_positive_integer():
    assert isinstance(SCHEMA_VERSION, int)
    assert SCHEMA_VERSION >= 1


def test_get_migration_sql_contains_all_three_tables():
    sql = get_migration_sql()
    assert "CREATE TABLE IF NOT EXISTS main_calculations" in sql
    assert "CREATE TABLE IF NOT EXISTS room_calculations" in sql
    assert "CREATE TABLE IF NOT EXISTS rental_records" in sql


def test_get_migration_sql_contains_rls_policies():
    sql = get_migration_sql()
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY" in sql


def test_get_migration_sql_contains_schema_version_table():
    sql = get_migration_sql()
    assert "_huc_schema_version" in sql
    assert f"VALUES ({SCHEMA_VERSION})" in sql


def test_get_version_check_sql_returns_select_query():
    sql = get_version_check_sql()
    assert "SELECT" in sql
    assert "_huc_schema_version" in sql


def test_get_migration_sql_is_idempotent():
    """All CREATE TABLE statements use IF NOT EXISTS."""
    sql = get_migration_sql()
    create_count = sql.count("CREATE TABLE")
    if_not_exists_count = sql.count("CREATE TABLE IF NOT EXISTS")
    assert create_count == if_not_exists_count, "All CREATE TABLE must use IF NOT EXISTS"
