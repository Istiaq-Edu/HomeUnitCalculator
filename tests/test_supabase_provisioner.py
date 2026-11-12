"""Tests for DBManager OAuth token storage, provisioning orchestrator, and UI tab."""

import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from src.core.db_manager import DBManager
from src.core.supabase_provisioner import SupabaseProvisioner
from src.core.supabase_schema import SCHEMA_VERSION


# ─── Test Helpers ───


def _get_test_db():
    """Create a DBManager with an in-memory SQLite DB."""
    db = object.__new__(DBManager)
    db.db_name = ":memory:"
    db.conn = sqlite3.connect(":memory:")
    db.conn.row_factory = sqlite3.Row
    db.cursor = db.conn.cursor()
    db.encryption_util = type("DummyEnc", (), {
        "encrypt_data": staticmethod(lambda s: s.encode()),
        "decrypt_data": staticmethod(lambda b: b.decode() if isinstance(b, bytes) else str(b)),
    })()
    db.cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value BLOB
        )
    """)
    db.conn.commit()
    return db


# ─── DB Token Storage Tests ───


def test_save_and_get_oauth_tokens():
    db = _get_test_db()
    tokens = {
        "access_token": "sbp_oauth_access_123",
        "refresh_token": "sbp_oauth_refresh_456",
        "expires_at": "2026-06-25T13:00:00Z",
    }
    db.save_oauth_tokens(tokens)
    retrieved = db.get_oauth_tokens()
    assert retrieved is not None
    assert retrieved["access_token"] == "sbp_oauth_access_123"
    assert retrieved["refresh_token"] == "sbp_oauth_refresh_456"


def test_get_oauth_tokens_returns_none_when_not_set():
    db = _get_test_db()
    assert db.get_oauth_tokens() is None


def test_clear_oauth_tokens():
    db = _get_test_db()
    db.save_oauth_tokens({"access_token": "a", "refresh_token": "r", "expires_at": "x"})
    db.clear_oauth_tokens()
    assert db.get_oauth_tokens() is None


def test_save_and_get_project_ref():
    db = _get_test_db()
    db.save_project_ref("abcdef123456")
    assert db.get_project_ref() == "abcdef123456"


def test_get_project_ref_returns_none_when_not_set():
    db = _get_test_db()
    assert db.get_project_ref() is None


def test_clear_project_ref():
    db = _get_test_db()
    db.save_project_ref("ref123")
    db.clear_project_ref()
    assert db.get_project_ref() is None


# ─── Orchestrator Tests ───


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_finds_existing_huc_project(mock_mgmt_class):
    """If a project named 'HUC Data' exists, reuse it."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = [
        {"ref": "existing-ref", "name": "HUC Data", "status": "ACTIVE"},
    ]
    # Schema version check → already up to date
    mock_client.run_query.return_value = [{"version": SCHEMA_VERSION}]
    mock_client.get_anon_api_key.return_value = "eyJanon_key"

    provisioner = SupabaseProvisioner(access_token="test_token")
    result = provisioner.provision(db_manager=_get_test_db())

    assert result["project_ref"] == "existing-ref"
    assert result["anon_key"] == "eyJanon_key"
    mock_client.create_project.assert_not_called()


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_creates_new_project_when_none_exist(mock_mgmt_class):
    """If no projects exist, create one and provision it."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = []
    mock_client.list_organizations.return_value = [
        {"slug": "my-org", "name": "My Org"}
    ]
    mock_client.create_project.return_value = {
        "ref": "new-ref",
        "name": "HUC Data",
    }
    mock_client.is_project_healthy.return_value = True
    mock_client.apply_migration.return_value = {"id": 1}
    mock_client.get_anon_api_key.return_value = "eyJnew_anon"

    provisioner = SupabaseProvisioner(access_token="test_token")
    result = provisioner.provision(db_manager=_get_test_db())

    assert result["project_ref"] == "new-ref"
    mock_client.create_project.assert_called_once()
    call_kwargs = mock_client.create_project.call_args[1]
    assert call_kwargs["organization_slug"] == "my-org"


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_raises_on_free_tier_limit(mock_mgmt_class):
    """If project creation fails with limit error, raise clear exception."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = []
    mock_client.list_organizations.return_value = [{"slug": "org"}]
    mock_client.create_project.side_effect = Exception(
        "Project creation failed: HTTP 400 — Limit reached"
    )

    provisioner = SupabaseProvisioner(access_token="test_token")
    with pytest.raises(Exception, match="Limit reached"):
        provisioner.provision(db_manager=_get_test_db())


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_applies_schema_migration(mock_mgmt_class):
    """Verify the provisioner calls apply_migration with the schema SQL."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = []
    mock_client.list_organizations.return_value = [{"slug": "org"}]
    mock_client.create_project.return_value = {"ref": "schema-ref", "name": "HUC Data"}
    mock_client.is_project_healthy.return_value = True
    mock_client.apply_migration.return_value = {"id": 1}
    mock_client.get_anon_api_key.return_value = "anon_key"

    provisioner = SupabaseProvisioner(access_token="test_token")
    provisioner.provision(db_manager=_get_test_db())

    mock_client.apply_migration.assert_called()
    call_args = mock_client.apply_migration.call_args
    assert call_args[1]["project_ref"] == "schema-ref"
    assert "main_calculations" in call_args[1]["query"]


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_stores_credentials_in_db(mock_mgmt_class):
    """Verify the provisioner stores project ref and API key in the DB."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = [
        {"ref": "store-ref", "name": "HUC Data", "status": "ACTIVE"},
    ]
    mock_client.run_query.return_value = [{"version": SCHEMA_VERSION}]
    mock_client.get_anon_api_key.return_value = "stored_anon_key"

    db = _get_test_db()
    provisioner = SupabaseProvisioner(access_token="test_token")
    provisioner.provision(db_manager=db)

    assert db.get_project_ref() == "store-ref"
    config = db.get_config()
    assert config.get("SUPABASE_KEY") == "stored_anon_key"


# ─── Schema Version Detection Tests ───


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_skips_schema_when_already_applied(mock_mgmt_class):
    """Scenario B: existing project with matching schema version → skip migration."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = [
        {"ref": "existing-ref", "name": "HUC Data", "status": "ACTIVE"},
    ]
    mock_client.run_query.return_value = [{"version": SCHEMA_VERSION}]
    mock_client.get_anon_api_key.return_value = "anon_key_existing"

    provisioner = SupabaseProvisioner(access_token="test_token")
    provisioner.provision(db_manager=_get_test_db())

    mock_client.apply_migration.assert_not_called()
    mock_client.get_anon_api_key.assert_called_once_with("existing-ref")


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_applies_schema_when_version_is_zero(mock_mgmt_class):
    """Scenario C: existing project with no schema table → apply migration."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = [
        {"ref": "empty-ref", "name": "HUC Data", "status": "ACTIVE"},
    ]
    # run_query fails → version 0
    mock_client.run_query.side_effect = Exception("table does not exist")
    mock_client.apply_migration.return_value = {"id": 1}
    mock_client.get_anon_api_key.return_value = "anon_key_empty"

    provisioner = SupabaseProvisioner(access_token="test_token")
    provisioner.provision(db_manager=_get_test_db())

    mock_client.apply_migration.assert_called_once()
    call_args = mock_client.apply_migration.call_args
    assert call_args[1]["project_ref"] == "empty-ref"
    assert "main_calculations" in call_args[1]["query"]


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_reuses_single_unnamed_project(mock_mgmt_class):
    """Scenario E: one active project with different name → reuse it."""
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = [
        {"ref": "other-ref", "name": "My Other Project", "status": "ACTIVE"},
    ]
    mock_client.run_query.side_effect = Exception("no schema")
    mock_client.apply_migration.return_value = {"id": 1}
    mock_client.get_anon_api_key.return_value = "anon_other"

    provisioner = SupabaseProvisioner(access_token="test_token")
    result = provisioner.provision(db_manager=_get_test_db())

    assert result["project_ref"] == "other-ref"
    mock_client.create_project.assert_not_called()
    mock_client.apply_migration.assert_called_once()


@patch("src.core.supabase_provisioner.SupabaseManagementClient")
def test_provisioner_reuses_first_project_when_multiple_unnamed_exist(mock_mgmt_class):
    """Scenario F: multiple active projects, none named HUC → reuse first one.

    Previously this would create a new project, but that fails on the free-tier
    2-project limit. Now we reuse the first available project instead.
    """
    mock_client = MagicMock()
    mock_mgmt_class.return_value = mock_client

    mock_client.list_projects.return_value = [
        {"ref": "ref-1", "name": "Project A", "status": "ACTIVE"},
        {"ref": "ref-2", "name": "Project B", "status": "ACTIVE"},
    ]
    mock_client.run_query.side_effect = Exception("no schema table")
    mock_client.apply_migration.return_value = {"id": 1}
    mock_client.get_anon_api_key.return_value = "anon_reused"

    provisioner = SupabaseProvisioner(access_token="test_token")
    result = provisioner.provision(db_manager=_get_test_db())

    # Should NOT create a new project (would hit free-tier limit)
    mock_client.create_project.assert_not_called()
    # Should reuse the first active project
    assert result["project_ref"] == "ref-1"
    mock_client.apply_migration.assert_called_once()


# ─── Paused Project Detection Tests ───


from src.core.supabase_error_handler import SupabaseErrorHandler, SupabaseErrorType


def test_detect_paused_project_from_connection_refused():
    err = ConnectionError("Connection refused")
    assert SupabaseErrorHandler.detect_error_type(err) == SupabaseErrorType.PAUSED_PROJECT


def test_paused_project_message_contains_restore_link():
    title, msg, icon = SupabaseErrorHandler.get_error_message(
        SupabaseErrorType.PAUSED_PROJECT,
        supabase_url="https://myproject.supabase.co",
    )
    assert "supabase.com/dashboard/projects" in msg
    assert "Restore" in msg or "Resume" in msg


def test_paused_project_message_extracts_project_id_from_url():
    title, msg, icon = SupabaseErrorHandler.get_error_message(
        SupabaseErrorType.PAUSED_PROJECT,
        supabase_url="https://abcdefgh.supabase.co",
    )
    assert "abcdefgh" in msg


# ─── Cloud Connect UI Tab Tests ───


def test_cloud_connect_tab_constructs_without_crash(qapp):
    """Cloud connect tab must construct without crashing."""
    from src.ui.tabs.cloud_connect_tab import CloudConnectTab

    class DummyMainWindow:
        class _DummyDB:
            def get_oauth_tokens(self): return None
            def get_project_ref(self): return None
            def get_config(self): return {}
        db_manager = _DummyDB()
        supabase_manager = None

    tab = CloudConnectTab(DummyMainWindow())
    assert tab.connect_button is not None
    assert tab.status_card is not None
    assert tab.progress_card is not None


def test_cloud_connect_tab_shows_connected_when_credentials_exist(qapp):
    """If OAuth tokens and project ref exist, tab shows connected state."""
    from src.ui.tabs.cloud_connect_tab import CloudConnectTab

    class DummyMainWindow:
        class _DummyDB:
            def get_oauth_tokens(self):
                return {"access_token": "x", "refresh_token": "y", "expires_at": "2099-01-01T00:00:00Z"}
            def get_project_ref(self):
                return "test-ref-123"
            def get_config(self):
                return {"SUPABASE_URL": "https://test-ref-123.supabase.co", "SUPABASE_KEY": "anon_key"}
        db_manager = _DummyDB()
        supabase_manager = None

    tab = CloudConnectTab(DummyMainWindow())
    # Status card title should mention "Connected"
    assert "Connected" in tab.status_card.status_title.text()
