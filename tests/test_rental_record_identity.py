"""Regressions for rental record identity across local/cloud stores (DATA-01).

A cloud ``rental_records.id`` is a Supabase sequence value. A local
``rentals.id`` is an independent SQLite sequence. Equal integers from the
two stores do not establish record identity, so cloud numeric ids must
never address local rows when editing or deleting.
"""

from types import SimpleNamespace

from src.ui import rental_record_dialog as rrd_module
from src.ui.rental_record_dialog import RentalRecord, RentalRecordDialog
from src.ui.tabs import rental_info_tab as ri_module
from src.ui.tabs.rental_info_tab import RentalInfoTab

CLOUD_ID = 7
CLOUD_UUID = "cloud-uuid-a"
LOCAL_ID = 41


class _Row:
    def __init__(self, mapping):
        self._mapping = mapping

    def __getitem__(self, key):
        return self._mapping[key]


class _FakeMessageBox:
    calls = []

    @classmethod
    def _record(cls, level):
        cls.calls.append((level, tuple(_args(level))))
        return None

    @classmethod
    def information(cls, *args):
        return cls._record("information")

    @classmethod
    def warning(cls, *args):
        return cls._record("warning")

    @classmethod
    def critical(cls, *args):
        return cls._record("critical")


def _args(level):
    # Placeholder so the recorded tuple length stays uniform; the arguments
    # themselves are not asserted by these tests.
    return []


class _FakeLocalDB:
    """Records queries; answers supabase_id lookups from a fixed mapping."""

    def __init__(self, local_rows_by_uuid=None):
        self.queries = []
        self.inserted = []
        self._insert_ids = iter(range(100, 199))
        self.rowcount = 1  # UPDATE statements report a matched row
        self.local_rows_by_uuid = local_rows_by_uuid or {}

    @property
    def cursor(self):
        return SimpleNamespace(rowcount=self.rowcount)

    def execute_query(self, query, params=None, fetch_one=False):
        self.queries.append((query, params))
        if "SELECT id FROM rentals WHERE supabase_id = ?" in query:
            uuid = params[0] if params else None
            local_id = self.local_rows_by_uuid.get(uuid)
            if local_id is None:
                return None if fetch_one else []
            return _Row({"id": local_id}) if fetch_one else [_Row({"id": local_id})]
        return None

    def insert_rental_record(self, record_data):
        self.inserted.append(dict(record_data))
        return next(self._insert_ids)


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

    def selectAll(self):
        pass


class _FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _FakeCheckbox:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


def _make_tab(local_rows_by_uuid=None):
    """A RentalInfoTab stripped of Qt construction (DashboardTab.__new__ style)."""
    tab = RentalInfoTab.__new__(RentalInfoTab)
    tab.db_manager = _FakeLocalDB(local_rows_by_uuid)
    tab.current_rental_id = None
    tab.current_supabase_id = None
    tab.current_is_archived = False
    tab.tenant_name_input = _FakeInput("Tenant A")
    tab.room_number_input = _FakeInput("101")
    tab.advanced_paid_input = _FakeInput("100")
    tab.photo_path_label = _FakeLabel()
    tab.nid_front_path_label = _FakeLabel()
    tab.nid_back_path_label = _FakeLabel()
    tab.police_form_path_label = _FakeLabel()
    tab.save_record_btn = _FakeLabel()
    tab._ensure_legacy_labels_exist = lambda: None
    tab._update_upload_widget_for_edit = lambda file_type, file_path: None
    # Real attribute lookups (self.photo_widget) happen before the stub is
    # called, so the widget attributes themselves must exist.
    tab.photo_widget = None
    tab.nid_front_widget = None
    tab.nid_back_widget = None
    tab.police_form_widget = None
    tab._get_file_path_from_widget = lambda widget, file_type: None
    tab._ensure_local_copy = lambda path: path
    return tab


def _make_dialog(record_data, source="Cloud (Supabase)"):
    dialog = RentalRecordDialog.__new__(RentalRecordDialog)
    dialog.current_source = source
    dialog.record_data = record_data
    dialog.supabase_id = record_data.supabase_id
    dialog.is_archived_record = bool(record_data.is_archived)
    dialog.db_manager = _FakeLocalDB()
    deleted = []
    dialog.supabase_manager = SimpleNamespace(
        is_client_initialized=lambda: True,
        delete_rental_record=lambda identifier: (deleted.append(identifier), True)[1],
    )
    dialog.supabase_delete_calls = deleted
    dialog.main_window = None
    dialog.accepted = False
    dialog.accept = lambda: setattr(dialog, "accepted", True)
    return dialog


def _cloud_record_dict(**overrides):
    record = {
        "id": CLOUD_ID,  # Supabase sequence value
        "supabase_id": CLOUD_UUID,
        "tenant_name": "Tenant A",
        "room_number": "101",
        "advanced_paid": 100.0,
        "is_archived": False,
        "photo_path": None,
        "nid_front_path": None,
        "nid_back_path": None,
        "police_form_path": None,
        "photo_url": None,
        "nid_front_url": None,
        "nid_back_url": None,
        "police_form_url": None,
        "created_at": "2026-11-12 10:00:00",
        "updated_at": "2026-11-12 10:00:00",
    }
    record.update(overrides)
    return record


def _patch_boxes(monkeypatch):
    _FakeMessageBox.calls = []
    monkeypatch.setattr(ri_module, "QMessageBox", _FakeMessageBox)
    monkeypatch.setattr(rrd_module, "QMessageBox", _FakeMessageBox)
    monkeypatch.setattr(
        rrd_module.ConfirmDialog, "ask", staticmethod(lambda *a, **k: True)
    )
    return _FakeMessageBox.calls


# ---------------------------------------------------------------------------
# Edit form identity
# ---------------------------------------------------------------------------


def test_cloud_edit_without_local_counterpart_does_not_adopt_cloud_id(monkeypatch):
    """No local row shares the cloud supabase_id: the form must not hold the
    cloud numeric id, because a later save-to-PC would UPDATE an unrelated
    local row whose id happens to equal the cloud id (DATA-01)."""
    tab = _make_tab(local_rows_by_uuid={"other-uuid": LOCAL_ID})
    tab.load_record_into_form_for_edit(
        _cloud_record_dict(), source="Cloud (Supabase)"
    )
    assert tab.current_rental_id is None
    assert tab.current_rental_id != CLOUD_ID
    assert tab.current_supabase_id == CLOUD_UUID


def test_cloud_edit_resolves_local_counterpart_by_supabase_id(monkeypatch):
    """A genuine local counterpart (same supabase_id) resolves to its real
    local id, never to the colliding cloud numeric id."""
    tab = _make_tab(local_rows_by_uuid={CLOUD_UUID: LOCAL_ID})
    tab.load_record_into_form_for_edit(
        _cloud_record_dict(), source="Cloud (Supabase)"
    )
    assert tab.current_rental_id == LOCAL_ID
    assert tab.current_rental_id != CLOUD_ID


def test_cloud_edit_with_failed_lookup_falls_back_to_insert(monkeypatch):
    """A resolver failure must fail safe: without a confirmed local id the
    next local save inserts instead of updating an arbitrary row."""
    tab = _make_tab()

    def _boom(query, params=None, fetch_one=False):
        raise RuntimeError("db unavailable")

    tab.db_manager.execute_query = _boom
    tab.load_record_into_form_for_edit(
        _cloud_record_dict(), source="Cloud (Supabase)"
    )
    assert tab.current_rental_id is None


def test_local_edit_keeps_local_id(monkeypatch):
    """Local-source editing keeps its existing behavior (local DB id)."""
    tab = _make_tab()
    tab.load_record_into_form_for_edit(_cloud_record_dict(id=LOCAL_ID))
    assert tab.current_rental_id == LOCAL_ID


def test_cloud_dict_edit_via_default_source_keeps_dict_id(monkeypatch):
    """The default source stays 'Local DB' so existing callers that pass a
    genuine local dict keep updating the same local row."""
    tab = _make_tab()
    tab.load_record_into_form_for_edit(_cloud_record_dict(id=LOCAL_ID))
    assert tab.current_rental_id == LOCAL_ID


# ---------------------------------------------------------------------------
# Save path: no wrong-record UPDATE from a cloud-loaded form
# ---------------------------------------------------------------------------


def test_save_to_pc_after_cloud_edit_inserts_instead_of_updating_by_cloud_id(
    monkeypatch,
):
    """Cloud record loaded with no local counterpart; saving to PC must
    insert a new local row. The old behavior issued
    ``UPDATE rentals ... WHERE id = 7`` against an unrelated local row."""
    boxes = _patch_boxes(monkeypatch)
    tab = _make_tab(local_rows_by_uuid={"unrelated-uuid": LOCAL_ID})
    tab.save_to_pc_checkbox = _FakeCheckbox(True)
    tab.save_to_cloud_checkbox = _FakeCheckbox(False)
    tab.main_window = SimpleNamespace(
        supabase_manager=SimpleNamespace(is_client_initialized=lambda: False)
    )
    tab.load_rental_records = lambda: None
    cleared = []
    tab.clear_form = lambda: cleared.append(tab.current_rental_id)

    tab.load_record_into_form_for_edit(
        _cloud_record_dict(), source="Cloud (Supabase)"
    )
    assert tab.current_rental_id is None

    tab.save_rental_record()

    update_queries = [q for q, _ in tab.db_manager.queries if "UPDATE rentals" in q]
    assert update_queries == []  # cloud id 7 never addressed a local row
    assert len(tab.db_manager.inserted) == 1
    inserted = tab.db_manager.inserted[0]
    assert inserted["supabase_id"] == CLOUD_UUID
    assert inserted["tenant_name"] == "Tenant A"
    assert any(level == "information" for level, _ in boxes)


def test_save_to_pc_after_cloud_edit_updates_resolved_local_row(monkeypatch):
    """When a genuine local counterpart exists, the local save targets that
    row's real id (41) and never the cloud numeric id (7)."""
    _patch_boxes(monkeypatch)
    tab = _make_tab(local_rows_by_uuid={CLOUD_UUID: LOCAL_ID})
    tab.save_to_pc_checkbox = _FakeCheckbox(True)
    tab.save_to_cloud_checkbox = _FakeCheckbox(False)
    tab.main_window = SimpleNamespace(
        supabase_manager=SimpleNamespace(is_client_initialized=lambda: False)
    )
    tab.load_rental_records = lambda: None
    tab.clear_form = lambda: None

    tab.load_record_into_form_for_edit(
        _cloud_record_dict(), source="Cloud (Supabase)"
    )
    tab.save_rental_record()

    updates = [(q, p) for q, p in tab.db_manager.queries if "UPDATE rentals" in q]
    assert len(updates) == 1
    query, params = updates[0]
    assert params["id"] == LOCAL_ID
    assert params["id"] != CLOUD_ID


# ---------------------------------------------------------------------------
# Dialog delete path
# ---------------------------------------------------------------------------


def test_cloud_delete_removes_local_counterpart_by_supabase_id(monkeypatch):
    """After a successful cloud delete, the local row is removed through the
    supabase_id link. The old behavior deleted ``rentals WHERE id = 7`` —
    potentially an unrelated local record."""
    boxes = _patch_boxes(monkeypatch)
    record = RentalRecord(
        id=CLOUD_ID,
        tenant_name="Tenant A",
        room_number="101",
        advanced_paid=100.0,
        created_at="2026-11-12 10:00:00",
        updated_at="2026-11-12 10:00:00",
        photo_path=None,
        nid_front_path=None,
        nid_back_path=None,
        police_form_path=None,
        is_archived=False,
        supabase_id=CLOUD_UUID,
        photo_url=None,
        nid_front_url=None,
        nid_back_url=None,
        police_form_url=None,
    )
    dialog = _make_dialog(record)
    dialog.db_manager.local_rows_by_uuid = {CLOUD_UUID: LOCAL_ID}

    dialog.delete_record()

    assert dialog.supabase_delete_calls == [CLOUD_UUID]
    delete_queries = [
        (q, p) for q, p in dialog.db_manager.queries if q.startswith("DELETE")
    ]
    assert delete_queries == [("DELETE FROM rentals WHERE supabase_id = ?", (CLOUD_UUID,))]
    numeric_deletes = [q for q, _ in delete_queries if "WHERE id" in q]
    assert numeric_deletes == []
    assert dialog.accepted
    assert any(level == "information" for level, _ in boxes)


def test_cloud_delete_without_supabase_id_is_blocked(monkeypatch):
    """A cloud record lacking supabase_id cannot be safely addressed; the
    delete must be blocked rather than falling back to the numeric id."""
    boxes = _patch_boxes(monkeypatch)
    record = RentalRecord(
        id=CLOUD_ID,
        tenant_name="Tenant A",
        room_number="101",
        advanced_paid=100.0,
        created_at="2026-11-12 10:00:00",
        updated_at="2026-11-12 10:00:00",
        photo_path=None,
        nid_front_path=None,
        nid_back_path=None,
        police_form_path=None,
        is_archived=False,
        supabase_id=None,
        photo_url=None,
        nid_front_url=None,
        nid_back_url=None,
        police_form_url=None,
    )
    dialog = _make_dialog(record)

    dialog.delete_record()

    assert dialog.supabase_delete_calls == []
    assert dialog.db_manager.queries == []  # nothing deleted locally
    assert not dialog.accepted
    assert any(level == "warning" for level, _ in boxes)
