"""Regressions for rental write identity (DATA-03).

New rental records must establish a stable cross-store ``supabase_id``:
the cloud insert persists it, the local insert/update persists it, and
the form keeps it so later saves update instead of duplicating.
"""

import re
from types import SimpleNamespace

from src.core.supabase_manager import SupabaseManager
from src.ui.tabs import rental_info_tab as ri_module
from src.ui.tabs.rental_info_tab import RentalInfoTab

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

RR = "rental_records"


class _Response:
    def __init__(self, data):
        self.data = data

    def json(self):
        return {"data": self.data}


class _Table:
    def __init__(self, name, client):
        self._name = name
        self._client = client
        self._ops = []

    def select(self, columns):
        self._ops.append(("select", columns))
        return self

    def insert(self, payload, returning=None):
        self._ops.append(("insert", payload))
        return self

    def update(self, payload, returning=None):
        self._ops.append(("update", payload))
        return self

    def delete(self):
        self._ops.append(("delete", None))
        return self

    def eq(self, column, value):
        self._ops.append(("eq", (column, value)))
        return self

    def in_(self, column, values):
        self._ops.append(("in_", (column, values)))
        return self

    def execute(self):
        key = (self._name, self._ops[0][0], self._ops[1][0] if len(self._ops) > 1 else "execute")
        self._client.executed.append((self._name, tuple(self._ops)))
        outcome = self._client.script.get(key, [{"id": 1}])
        if isinstance(outcome, Exception):
            raise outcome
        return _Response(outcome)


class _FakeSupabase:
    def __init__(self, script):
        self.script = script
        self.executed = []

    def table(self, name):
        return _Table(name, self)


def _make_manager(script):
    manager = SupabaseManager.__new__(SupabaseManager)
    manager.supabase = _FakeSupabase(script)
    manager.is_client_initialized = lambda: True
    manager._upload_rental_images = lambda paths: {k: None for k in paths}
    return manager


# ---------------------------------------------------------------------------
# Cloud write path
# ---------------------------------------------------------------------------


def test_cloud_insert_assigns_supabase_identity():
    """An insert without supabase_id must persist a generated uuid so the
    row becomes addressable by identity (the old insert omitted the key)."""
    manager = _make_manager({})

    result = manager.save_rental_record(
        {"tenant_name": "Tenant A", "room_number": "101", "advanced_paid": 100.0},
        {"photo": None, "nid_front": None, "nid_back": None, "police_form": None},
    )

    assert "Successfully" in result
    insert_chains = [
        ops for name, ops in manager.supabase.executed if name == RR and ops[0][0] == "insert"
    ]
    assert len(insert_chains) == 1
    payload = insert_chains[0][0][1]
    assert UUID_RE.match(payload["supabase_id"])


def test_cloud_update_reuses_caller_identity():
    provided = "existing-uuid-a"
    manager = _make_manager({})

    manager.save_rental_record(
        {
            "tenant_name": "Tenant A",
            "room_number": "101",
            "supabase_id": provided,
        },
        {"photo": None, "nid_front": None, "nid_back": None, "police_form": None},
    )

    chains = [
        ops for name, ops in manager.supabase.executed if name == RR and ops[0][0] == "update"
    ]
    assert len(chains) == 1
    update_ops = chains[0]
    assert ("eq", ("supabase_id", provided)) in update_ops
    payload = update_ops[0][1]
    assert payload["supabase_id"] == provided


# ---------------------------------------------------------------------------
# UI save path
# ---------------------------------------------------------------------------


class _FakeInput:
    def __init__(self, text=""):
        self._text = text

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text

    def setFocus(self):
        pass

    def clear(self):
        self._text = ""


class _FakeCheckbox:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _FakeLocalDB:
    def __init__(self, rowcount=1):
        self.queries = []
        self.inserted = []
        self._ids = iter(range(100, 199))
        self._rowcount = rowcount

    @property
    def cursor(self):
        return SimpleNamespace(rowcount=self._rowcount)

    def execute_query(self, query, params=None, fetch_one=False):
        self.queries.append((query, params))
        return None

    def insert_rental_record(self, record_data):
        self.inserted.append(dict(record_data))
        return next(self._ids)


class _FakeMessageBox:
    calls = []

    @classmethod
    def information(cls, *args):
        cls.calls.append(("information", args[1]))
        return None

    @classmethod
    def warning(cls, *args):
        cls.calls.append(("warning", args[1]))
        return None

    @classmethod
    def critical(cls, *args):
        cls.calls.append(("critical", args[1]))
        return None


class _FakeCloudManager:
    """Records the payload handed to save_rental_record."""

    def __init__(self):
        self.saved = []

    def is_client_initialized(self):
        return True

    def save_rental_record(self, record_data, image_paths):
        self.saved.append(dict(record_data))
        return f"Successfully saved record for {record_data.get('tenant_name')}. (Cloud)"


def _make_tab(db):
    tab = RentalInfoTab.__new__(RentalInfoTab)
    tab.db_manager = db
    tab.current_rental_id = None
    tab.current_supabase_id = None
    tab.current_is_archived = False
    tab.tenant_name_input = _FakeInput("Tenant A")
    tab.room_number_input = _FakeInput("101")
    tab.advanced_paid_input = _FakeInput("100")
    tab.photo_widget = None
    tab.nid_front_widget = None
    tab.nid_back_widget = None
    tab.police_form_widget = None
    tab._ensure_legacy_labels_exist = lambda: None
    tab._get_file_path_from_widget = lambda widget, file_type: None
    tab._ensure_local_copy = lambda path: path
    tab.save_to_pc_checkbox = _FakeCheckbox(True)
    tab.save_to_cloud_checkbox = _FakeCheckbox(True)
    tab.load_rental_records = lambda: None
    return tab


def test_new_record_gets_one_shared_identity_across_destinations(monkeypatch):
    """A brand-new record saved to PC and Cloud must end up with the same
    supabase_id in the local insert, the cloud payload, and the form; the
    local insert's returned id must become the form's local id (the old
    code ignored it and inserted nothing linkable)."""
    _FakeMessageBox.calls = []
    monkeypatch.setattr(ri_module, "QMessageBox", _FakeMessageBox)

    db = _FakeLocalDB()
    cloud = _FakeCloudManager()
    tab = _make_tab(db)
    snapshots = []
    tab.clear_form = lambda: snapshots.append(
        (tab.current_rental_id, tab.current_supabase_id)
    )
    tab.main_window = SimpleNamespace(supabase_manager=cloud, _emit_local_change=None)

    tab.save_rental_record()

    assert len(db.inserted) == 1
    local_identity = db.inserted[0]["supabase_id"]
    assert UUID_RE.match(local_identity)
    assert len(cloud.saved) == 1
    assert cloud.saved[0]["supabase_id"] == local_identity
    # Form kept the receipt of both writes before clearing.
    local_id, form_identity = snapshots[0]
    assert local_id == 100  # insert_rental_record return value, not ignored
    assert form_identity == local_identity
    assert any(level == "information" for level, _ in _FakeMessageBox.calls)


def test_existing_local_row_gains_persisted_identity_on_update(monkeypatch):
    """Editing a local row that lacks supabase_id must persist the new
    identity through the UPDATE, not just hold it in memory."""
    _FakeMessageBox.calls = []
    monkeypatch.setattr(ri_module, "QMessageBox", _FakeMessageBox)

    db = _FakeLocalDB(rowcount=1)
    cloud = _FakeCloudManager()
    tab = _make_tab(db)
    tab.current_rental_id = 41  # genuine local row, no cloud link yet
    tab.current_supabase_id = None
    tab.clear_form = lambda: None
    tab.main_window = SimpleNamespace(supabase_manager=cloud, _emit_local_change=None)

    tab.save_rental_record()

    updates = [(q, p) for q, p in db.queries if "UPDATE rentals" in q]
    assert len(updates) == 1
    query, params = updates[0]
    assert "supabase_id = :supabase_id" in query
    assert UUID_RE.match(params["supabase_id"])
    assert db.inserted == []  # update matched; no duplicate insert
    assert cloud.saved[0]["supabase_id"] == params["supabase_id"]


def test_existing_identity_is_not_regenerated(monkeypatch):
    """A record that already has an identity keeps it across saves."""
    _FakeMessageBox.calls = []
    monkeypatch.setattr(ri_module, "QMessageBox", _FakeMessageBox)

    db = _FakeLocalDB(rowcount=1)
    cloud = _FakeCloudManager()
    tab = _make_tab(db)
    tab.current_rental_id = 41
    tab.current_supabase_id = "existing-uuid-a"
    tab.clear_form = lambda: None
    tab.main_window = SimpleNamespace(supabase_manager=cloud, _emit_local_change=None)

    tab.save_rental_record()

    _, params = [entry for entry in db.queries if "UPDATE rentals" in entry[0]][0]
    assert params["supabase_id"] == "existing-uuid-a"
    assert cloud.saved[0]["supabase_id"] == "existing-uuid-a"
