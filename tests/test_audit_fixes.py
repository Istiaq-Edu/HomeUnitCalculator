"""Test cases for the security & stability audit fixes.

Each test corresponds to a specific finding from the audit:

C1  — TLS verification enabled on all image downloads
C2  — RLS policies tightened with auth.role()
C3  — requirements.txt version pins corrected
H1  — XSS escape in OAuth callback error page
H3  — Windows ACL protection for encryption key file
H5  — Generated Supabase DB password is stored
M1  — No bare except: clauses
M2  — DBManager.__del__ has try/except safety
M4  — Error logging no longer leaks params
M6  — Polling interval increased to avoid rate limits
M7  — OAuth server lifecycle uses try/finally
"""

import os
import re
import inspect
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from html import escape as html_escape

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# C1: TLS verification enabled on all image downloads
# ═══════════════════════════════════════════════════════════════════════════

class TestC1TLSVerification:
    """Verify TLS verification is enabled on all image download paths."""

    def test_optimized_image_fetcher_uses_verify_true(self):
        """OptimizedImageFetcher._fetch_from_network must use verify=True."""
        from src.core.optimized_image_fetcher import OptimizedImageFetcher
        src = inspect.getsource(OptimizedImageFetcher._fetch_from_network)
        assert "verify=True" in src, "TLS verification must be enabled"
        assert "verify=False" not in src, "TLS verification must not be disabled"

    def test_fetch_image_worker_default_verify_tls_is_true(self):
        """FetchImageWorker.__init__ default verify_tls parameter must be True."""
        from src.ui.background_workers import FetchImageWorker
        sig = inspect.signature(FetchImageWorker.__init__)
        param = sig.parameters.get("verify_tls")
        assert param is not None, "verify_tls parameter must exist"
        assert param.default is True, f"verify_tls default must be True, got {param.default}"

    def test_rental_info_tab_uses_verify_true(self):
        """rental_info_tab.py image download must use verify=True."""
        filepath = Path(__file__).parent.parent / "src" / "ui" / "tabs" / "rental_info_tab.py"
        content = filepath.read_text(encoding="utf-8")
        # Find all requests.get calls with verify=
        verify_false_matches = re.findall(r'verify\s*=\s*False', content)
        assert len(verify_false_matches) == 0, f"Found {len(verify_false_matches)} verify=False in rental_info_tab.py"
        assert "verify=True" in content, "No verify=True found in rental_info_tab.py"

    def test_rental_record_dialog_uses_verify_tls_true(self):
        """rental_record_dialog.py FetchImageWorker call must pass verify_tls=True."""
        filepath = Path(__file__).parent.parent / "src" / "ui" / "rental_record_dialog.py"
        content = filepath.read_text(encoding="utf-8")
        assert "verify_tls=True" in content, "FetchImageWorker call must use verify_tls=True"
        assert "verify_tls=False" not in content, "No verify_tls=False should remain"

    def test_no_ssl_warning_suppression_anywhere(self):
        """No urllib3.disable_warnings calls should remain in the codebase."""
        src_dir = Path(__file__).parent.parent / "src"
        files_with_suppression = []
        for pyfile in src_dir.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            content = pyfile.read_text(encoding="utf-8")
            if "disable_warnings" in content or "InsecureRequestWarning" in content:
                files_with_suppression.append(str(pyfile))
        assert files_with_suppression == [], \
            f"SSL warning suppression found in: {files_with_suppression}"


# ═══════════════════════════════════════════════════════════════════════════
# C2: RLS policies tightened with auth.role()
# ═══════════════════════════════════════════════════════════════════════════

class TestC2RLSPolicies:
    """Verify RLS policies use auth.role() instead of USING (true)."""

    def test_schema_version_is_2(self):
        """SCHEMA_VERSION must be bumped to 2 after policy change."""
        from src.core.supabase_schema import SCHEMA_VERSION
        assert SCHEMA_VERSION == 2, f"Expected SCHEMA_VERSION=2, got {SCHEMA_VERSION}"

    def test_policies_use_auth_role_anon(self):
        """All policies must use auth.role() = 'anon' instead of USING (true)."""
        from src.core.supabase_schema import get_migration_sql
        sql = get_migration_sql()
        assert "auth.role() = 'anon'" in sql, "Policies must use auth.role() = 'anon'"
        assert "USING (true) WITH CHECK (true)" not in sql, \
            "Policies must not use unconditional USING (true)"

    def test_old_policy_name_is_dropped(self):
        """Old 'Allow all for anon' policies must be dropped for idempotency."""
        from src.core.supabase_schema import get_migration_sql
        sql = get_migration_sql()
        assert 'DROP POLICY IF EXISTS "Allow all for anon"' in sql, \
            "Old policy name must be dropped for migration idempotency"

    def test_new_policy_name_is_dropped_too(self):
        """New 'Allow anon read-write' must also be dropped (for re-runs)."""
        from src.core.supabase_schema import get_migration_sql
        sql = get_migration_sql()
        assert 'DROP POLICY IF EXISTS "Allow anon read-write"' in sql, \
            "New policy name must also be dropped for idempotency"

    def test_version_insert_is_2(self):
        """The _huc_schema_version insert must be VALUES (2)."""
        from src.core.supabase_schema import get_migration_sql
        sql = get_migration_sql()
        assert "VALUES (2)" in sql, "Schema version insert must be 2"

    def test_all_three_tables_have_rls(self):
        """All three tables must have ENABLE ROW LEVEL SECURITY."""
        from src.core.supabase_schema import get_migration_sql
        sql = get_migration_sql()
        for table in ["main_calculations", "room_calculations", "rental_records"]:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql, \
                f"Table {table} must have RLS enabled"

    def test_drop_before_create_count_balanced(self):
        """Each table must have DROP POLICY before CREATE POLICY."""
        from src.core.supabase_schema import get_migration_sql
        sql = get_migration_sql()
        drop_count = sql.count("DROP POLICY IF EXISTS")
        create_count = sql.count("CREATE POLICY")
        assert drop_count >= create_count, \
            f"DROP count ({drop_count}) must be >= CREATE count ({create_count})"


# ═══════════════════════════════════════════════════════════════════════════
# C3: requirements.txt version pins
# ═══════════════════════════════════════════════════════════════════════════

class TestC3RequirementsTxt:
    """Verify requirements.txt pins match installed versions."""

    @pytest.fixture(scope="class")
    def reqs_content(self):
        filepath = Path(__file__).parent.parent / "requirements.txt"
        return filepath.read_text(encoding="utf-8")

    def test_supabase_pinned_to_v2(self, reqs_content):
        assert "supabase>=2.22.0" in reqs_content
        assert "supabase==1.0.4" not in reqs_content

    def test_websockets_pinned_to_v12_plus(self, reqs_content):
        assert "websockets>=12.0" in reqs_content
        assert "websockets==10.4" not in reqs_content

    def test_urllib3_pinned_to_v2_plus(self, reqs_content):
        assert "urllib3>=2.0.0" in reqs_content

    def test_all_deps_have_lower_bounds(self, reqs_content):
        """All pinned deps should use >= not == to allow patch updates."""
        lines = [l.strip() for l in reqs_content.splitlines() if l.strip()]
        for line in lines:
            if "==" in line and "python-dotenv" not in line:
                pytest.fail(f"Exact pin found (should use >=): {line}")


# ═══════════════════════════════════════════════════════════════════════════
# H1: XSS escape in OAuth callback error page
# ═══════════════════════════════════════════════════════════════════════════

class TestH1XSSEscape:
    """Verify XSS escape is applied to user-controlled HTML in OAuth callback."""

    def test_escape_imported(self):
        """html.escape must be imported in oauth_callback_server.py."""
        from src.ui.oauth_callback_server import _CallbackHandler
        # If import succeeded, the module loaded fine
        import src.ui.oauth_callback_server as mod
        assert hasattr(mod, 'escape') or 'escape' in inspect.getsource(_CallbackHandler.do_GET)

    def test_error_params_are_escaped(self):
        """server.error and server.error_description must be wrapped in escape()."""
        from src.ui.oauth_callback_server import _CallbackHandler
        src = inspect.getsource(_CallbackHandler.do_GET)
        assert "escape(server.error)" in src, "server.error must be escaped"
        assert "escape(server.error_description" in src, \
            "server.error_description must be escaped"

    def test_escape_neutralizes_script_tag(self):
        """html.escape must convert <script> to &lt;script&gt;."""
        payload = '<script>alert("xss")</script>'
        escaped = html_escape(payload)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_no_unescaped_f_string_interpolation_of_user_input(self):
        """No f-string should directly interpolate server.error without escape."""
        from src.ui.oauth_callback_server import _CallbackHandler
        src = inspect.getsource(_CallbackHandler.do_GET)
        # Find all f-strings that contain {server.error
        # They must be wrapped in escape()
        lines = src.split("\n")
        for line in lines:
            if "f\"" in line and "server.error" in line:
                if "escape(" not in line:
                    pytest.fail(f"Unescaped server.error in f-string: {line.strip()}")


# ═══════════════════════════════════════════════════════════════════════════
# H3: Windows ACL protection for encryption key file
# ═══════════════════════════════════════════════════════════════════════════

class TestH3WindowsACL:
    """Verify Windows ACL protection for encryption key file."""

    def test_restrict_method_exists(self):
        """KeyManager must have _restrict_file_permissions_windows method."""
        from src.core.key_manager import KeyManager
        assert hasattr(KeyManager, "_restrict_file_permissions_windows")

    def test_uses_icacls(self):
        """The method must use icacls command."""
        from src.core.key_manager import KeyManager
        src = inspect.getsource(KeyManager._restrict_file_permissions_windows)
        assert "icacls" in src

    def test_uses_inheritance_removal(self):
        """The method must use /inheritance:r to remove inherited permissions."""
        from src.core.key_manager import KeyManager
        src = inspect.getsource(KeyManager._restrict_file_permissions_windows)
        assert "/inheritance:r" in src

    def test_uses_list_args_not_shell(self):
        """subprocess.run must use list args, not shell=True (injection safety)."""
        from src.core.key_manager import KeyManager
        src = inspect.getsource(KeyManager._restrict_file_permissions_windows)
        # Check the actual subprocess.run call, not comments
        # Remove comment lines before checking
        code_lines = [line for line in src.split("\n")
                      if not line.strip().startswith("#")]
        code = "\n".join(code_lines)
        # shell=True should not be in the actual code (only in comments)
        assert "shell=True" not in code, "shell=True is a security risk"
        assert "[" in code and "]" in code, "Must use list arguments"

    def test_username_is_quoted_for_icacls(self):
        """Username must be quoted in icacls arg to handle spaces."""
        from src.core.key_manager import KeyManager
        src = inspect.getsource(KeyManager._restrict_file_permissions_windows)
        # The f-string should contain quotes around {username}
        assert '"{username}"' in src or "'\"{username}\"'" in src or '\\"{username}\\"' in src, \
            "Username must be quoted for icacls to handle spaces"

    def test_store_key_securely_calls_windows_acl(self):
        """_store_key_securely must call _restrict_file_permissions_windows on non-posix."""
        from src.core.key_manager import KeyManager
        src = inspect.getsource(KeyManager._store_key_securely)
        assert "_restrict_file_permissions_windows" in src


# ═══════════════════════════════════════════════════════════════════════════
# H5: Generated Supabase DB password is stored
# ═══════════════════════════════════════════════════════════════════════════

class TestH5DBPasswordStorage:
    """Verify generated Supabase DB password is stored and retrievable."""

    def test_db_manager_has_save_db_password(self):
        from src.core.db_manager import DBManager
        assert hasattr(DBManager, "save_db_password")

    def test_db_manager_has_get_db_password(self):
        from src.core.db_manager import DBManager
        assert hasattr(DBManager, "get_db_password")

    def test_db_manager_has_clear_db_password(self):
        from src.core.db_manager import DBManager
        assert hasattr(DBManager, "clear_db_password")

    def test_create_new_project_returns_tuple(self):
        """_create_new_project must return (ref, password) tuple."""
        from src.core.supabase_provisioner import SupabaseProvisioner
        src = inspect.getsource(SupabaseProvisioner._create_new_project)
        assert 'return result["ref"], db_password' in src, \
            "Must return tuple of (ref, db_password)"

    def test_provision_stores_db_password(self):
        """provision() must call save_db_password when db_password is set."""
        from src.core.supabase_provisioner import SupabaseProvisioner
        src = inspect.getsource(SupabaseProvisioner.provision)
        assert "save_db_password" in src

    def test_provision_calls_save_db_password_before_save_project_ref(self):
        """save_db_password must be called BEFORE save_project_ref (race condition fix)."""
        from src.core.supabase_provisioner import SupabaseProvisioner
        src = inspect.getsource(SupabaseProvisioner.provision)
        # Find the positions
        save_config_pos = src.find("save_config")
        save_db_password_pos = src.find("save_db_password")
        save_project_ref_pos = src.find("save_project_ref")
        assert save_config_pos < save_db_password_pos < save_project_ref_pos, \
            "Order must be: save_config → save_db_password → save_project_ref"

    def test_db_password_roundtrip(self, tmp_path):
        """Test actual encrypt/decrypt roundtrip for DB password."""
        from src.core.db_manager import DBManager
        db = DBManager(db_name=str(tmp_path / "test_pwd.db"))
        try:
            test_password = "SuperSecret123!@#"
            db.save_db_password(test_password)
            retrieved = db.get_db_password()
            assert retrieved == test_password, \
                f"Password roundtrip failed: expected {test_password!r}, got {retrieved!r}"
        finally:
            db.close()

    def test_db_password_clear(self, tmp_path):
        """Test that clear_db_password removes the stored password."""
        from src.core.db_manager import DBManager
        db = DBManager(db_name=str(tmp_path / "test_clear.db"))
        try:
            db.save_db_password("test123")
            assert db.get_db_password() == "test123"
            db.clear_db_password()
            assert db.get_db_password() is None
        finally:
            db.close()

    def test_db_password_encrypted_in_storage(self, tmp_path):
        """Verify password is encrypted, not stored in plaintext."""
        from src.core.db_manager import DBManager
        db = DBManager(db_name=str(tmp_path / "test_enc.db"))
        try:
            test_password = "PlaintextShouldNotAppear"
            db.save_db_password(test_password)
            # Read the raw DB value — it should NOT contain the plaintext
            raw = db.execute_query(
                "SELECT value FROM app_config WHERE key = 'DB_PASSWORD'"
            )
            assert len(raw) == 1
            raw_bytes = raw[0]["value"]
            assert isinstance(raw_bytes, bytes)
            assert test_password.encode() not in raw_bytes, \
                "Password must be encrypted, not stored as plaintext"
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════════════════════
# M1: No bare except: clauses
# ═══════════════════════════════════════════════════════════════════════════

class TestM1NoBareExcept:
    """Verify no bare except: clauses remain in src/."""

    def test_zero_bare_except_in_src(self):
        """Scan all .py files in src/ for bare 'except:' (not 'except Exception:')."""
        src_dir = Path(__file__).parent.parent / "src"
        bare_count = 0
        locations = []
        for pyfile in src_dir.rglob("*.py"):
            if "__pycache__" in str(pyfile):
                continue
            with open(pyfile, encoding="utf-8") as f:
                for lineno, line in enumerate(f, 1):
                    if re.match(r'\s*except\s*:', line):
                        bare_count += 1
                        locations.append(f"{pyfile.name}:{lineno}")
        assert bare_count == 0, \
            f"Found {bare_count} bare except: clauses: {locations}"


# ═══════════════════════════════════════════════════════════════════════════
# M2: DBManager.__del__ has try/except safety
# ═══════════════════════════════════════════════════════════════════════════

class TestM2DelSafety:
    """Verify __del__ is wrapped in try/except to prevent GC crashes."""

    def test_del_has_try_except(self):
        from src.core.db_manager import DBManager
        src = inspect.getsource(DBManager.__del__)
        assert "try:" in src
        assert "except" in src

    def test_del_does_not_raise_on_none_conn(self):
        """__del__ should not crash if conn is already None."""
        from src.core.db_manager import DBManager
        db = DBManager()
        db.close()  # Sets conn to None
        # __del__ should not raise
        db.__del__()  # Should be a no-op


# ═══════════════════════════════════════════════════════════════════════════
# M4: Error logging no longer leaks params
# ═══════════════════════════════════════════════════════════════════════════

class TestM4ErrorLoggingRedaction:
    """Verify error logging no longer prints params (which may contain secrets)."""

    def test_no_params_in_execute_query_error(self):
        from src.core.db_manager import DBManager
        src = inspect.getsource(DBManager.execute_query)
        assert "Params:" not in src, "Error log must not include params"

    def test_query_truncated_in_error(self):
        from src.core.db_manager import DBManager
        src = inspect.getsource(DBManager.execute_query)
        assert "query[:200]" in src, "Query must be truncated in error log"

    def test_no_params_in_execute_many_error(self):
        from src.core.db_manager import DBManager
        src = inspect.getsource(DBManager.execute_many)
        assert "Params:" not in src


# ═══════════════════════════════════════════════════════════════════════════
# M6: Polling interval increased
# ═══════════════════════════════════════════════════════════════════════════

class TestM6PollingInterval:
    """Verify active polling interval was increased from 3s to 10s."""

    def test_active_interval_is_10000ms(self):
        from src.core.remote_change_monitor import RemoteChangeMonitor
        src = inspect.getsource(RemoteChangeMonitor._update_interval)
        assert "interval_ms = 10000" in src, "Active interval must be 10000ms"
        assert "interval_ms = 3000\n" not in src, "Old 3000ms interval must not remain"

    def test_minimized_interval_is_30000ms(self):
        from src.core.remote_change_monitor import RemoteChangeMonitor
        src = inspect.getsource(RemoteChangeMonitor._update_interval)
        assert "interval_ms = 30000" in src, "Minimized interval must be 30000ms"


# ═══════════════════════════════════════════════════════════════════════════
# M7: OAuth server lifecycle uses try/finally
# ═══════════════════════════════════════════════════════════════════════════

class TestM7ServerLifecycle:
    """Verify OAuth callback server is always closed via try/finally."""

    def test_has_finally_block(self):
        from src.ui.tabs.cloud_connect_tab import CloudConnectTab
        src = inspect.getsource(CloudConnectTab._run_oauth_flow)
        assert "finally:" in src

    def test_finally_closes_server(self):
        from src.ui.tabs.cloud_connect_tab import CloudConnectTab
        src = inspect.getsource(CloudConnectTab._run_oauth_flow)
        assert "server.server_close()" in src
        # The server_close must be inside the finally block
        finally_pos = src.find("finally:")
        close_pos = src.find("server.server_close()")
        assert close_pos > finally_pos, "server_close must be after finally:"

    def test_server_initialized_as_none_before_try(self):
        from src.ui.tabs.cloud_connect_tab import CloudConnectTab
        src = inspect.getsource(CloudConnectTab._run_oauth_flow)
        none_pos = src.find("server = None")
        try_pos = src.find("try:")
        assert none_pos < try_pos, "server = None must come before try:"

    def test_exactly_one_server_close_call(self):
        """Only 1 server_close() should exist (in finally), not 4 scattered."""
        from src.ui.tabs.cloud_connect_tab import CloudConnectTab
        src = inspect.getsource(CloudConnectTab._run_oauth_flow)
        close_count = src.count("server.server_close()")
        assert close_count == 1, \
            f"Expected exactly 1 server_close() in finally, found {close_count}"

    def test_finally_checks_server_is_not_none(self):
        """finally block must guard against server being None."""
        from src.ui.tabs.cloud_connect_tab import CloudConnectTab
        src = inspect.getsource(CloudConnectTab._run_oauth_flow)
        finally_pos = src.find("finally:")
        finally_block = src[finally_pos:]
        assert "if server is not None" in finally_block, \
            "finally must check server is not None before closing"
