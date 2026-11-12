"""Regressions for save-outcome truthfulness (DATA-04).

Unrequested destinations must neither fabricate success nor turn a
single requested failure into a misleading "partial success".
"""

from types import SimpleNamespace

from src.ui.tabs import rental_info_tab as ri_module
from src.ui.tabs.rental_info_tab import RentalInfoTab


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
    def __init__(self, rowcount=1, fail_insert=False):
        self.queries = []
        self.inserted = []
        self._ids = iter(range(100, 199))
        self._rowcount = rowcount
        self._fail_insert = fail_insert

    @property
    def cursor(self):
        return SimpleNamespace(rowcount=self._rowcount)

    def execute_query(self, query, params=None, fetch_one=False):
        self.queries.append((query, params))
        return None

    def insert_rental_record(self, record_data):
        if self._fail_insert:
            raise RuntimeError("disk full")
        self.inserted.append(dict(record_data))
        return next(self._ids)


class _FakeMessageBox:
    calls = []  # (level, title, message)

    @classmethod
    def _record(cls, level, args):
        cls.calls.append((level, args[1], args[2] if len(args) > 2 else ""))
        return None

    @classmethod
    def information(cls, *args):
        return cls._record("information", args)

    @classmethod
    def warning(cls, *args):
        return cls._record("warning", args)

    @classmethod
    def critical(cls, *args):
        return cls._record("critical", args)


class _FakeCloudManager:
    def __init__(self, initialized=True, fail=False):
        self._initialized = initialized
        self._fail = fail
        self.saved = []

    def is_client_initialized(self):
        return self._initialized

    def save_rental_record(self, record_data, image_paths):
        self.saved.append(dict(record_data))
        if self._fail:
            return "Error: simulated cloud failure"
        return f"Successfully saved record for {record_data.get('tenant_name')}. (Cloud)"


def _make_tab(db, cloud, save_pc, save_cloud):
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
    tab.save_to_pc_checkbox = _FakeCheckbox(save_pc)
    tab.save_to_cloud_checkbox = _FakeCheckbox(save_cloud)
    tab.load_rental_records = lambda: None
    tab.clear_form = lambda: None
    tab.main_window = SimpleNamespace(
        supabase_manager=cloud, _emit_local_change=lambda *a, **k: None
    )
    return tab


def _patch_boxes(monkeypatch):
    _FakeMessageBox.calls = []
    monkeypatch.setattr(ri_module, "QMessageBox", _FakeMessageBox)
    return _FakeMessageBox.calls


def test_single_cloud_failure_is_failure_not_partial_success(monkeypatch):
    """Only the cloud destination is requested and it fails: the old flags
    (initialized True) produced a "Partial Success" message."""
    boxes = _patch_boxes(monkeypatch)
    cloud = _FakeCloudManager(fail=True)
    tab = _make_tab(_FakeLocalDB(), cloud, save_pc=False, save_cloud=True)

    tab.save_rental_record()

    entries = [(title, message) for _, title, message in boxes]
    assert any("Save Failed" in str(title) for title, _ in entries)
    assert not any("Partial Success" in str(title) for title, _ in entries)
    assert not any("saved successfully" in str(title) for title, _ in entries)


def test_single_local_failure_is_failure_not_partial_success(monkeypatch):
    boxes = _patch_boxes(monkeypatch)
    db = _FakeLocalDB(rowcount=0, fail_insert=True)
    tab = _make_tab(db, _FakeCloudManager(), save_pc=True, save_cloud=False)

    tab.save_rental_record()

    entries = [(title, message) for _, title, message in boxes]
    assert any("Save Failed" in str(title) for title, _ in entries)
    assert not any("Partial Success" in str(title) for title, _ in entries)


def test_unrequested_destination_does_not_block_success(monkeypatch):
    """Only the local destination is requested and succeeds: the outcome is
    plain success, unpolluted by the unrequested cloud destination."""
    boxes = _patch_boxes(monkeypatch)
    tab = _make_tab(
        _FakeLocalDB(), _FakeCloudManager(), save_pc=True, save_cloud=False
    )

    tab.save_rental_record()

    entries = [(title, message) for _, title, message in boxes]
    assert any("Rental record saved successfully" in message for _, message in entries)
    assert not any("Partial Success" in str(title) for title, _ in entries)


def test_mixed_requested_outcomes_report_partial_success(monkeypatch):
    boxes = _patch_boxes(monkeypatch)
    cloud = _FakeCloudManager(fail=True)
    tab = _make_tab(_FakeLocalDB(), cloud, save_pc=True, save_cloud=True)

    tab.save_rental_record()

    entries = [(title, message) for _, title, message in boxes]
    assert any("Partial Success" in str(title) for title, _ in entries)
    assert not any("Rental record saved successfully" in str(title) for title, _ in entries)


def test_cloud_not_configured_counts_as_requested_failure(monkeypatch):
    boxes = _patch_boxes(monkeypatch)
    cloud = _FakeCloudManager(initialized=False)
    tab = _make_tab(_FakeLocalDB(), cloud, save_pc=True, save_cloud=True)

    tab.save_rental_record()

    entries = [(title, message) for _, title, message in boxes]
    assert any("Partial Success" in str(title) for title, _ in entries)
