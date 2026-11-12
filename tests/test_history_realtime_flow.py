from PyQt5.QtWidgets import QDialog

import src.ui.tabs.history_tab as history_module
from src.ui.tabs.history_tab import HistoryTab


class _CallRecorder:
    def __init__(self, return_value=None):
        self.calls = []
        self.return_value = return_value

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value


def test_finalize_history_tables_after_load_coalesces_to_one_deferred_resize(
    monkeypatch,
):
    history = HistoryTab.__new__(HistoryTab)
    history.main_history_table = type("Table", (), {"_month_styled": True})()
    history.room_history_table = type("Table", (), {"_month_styled": True})()
    history.totals_table = type("Table", (), {"_month_styled": True})()
    history.resize_table_to_content = _CallRecorder()
    history._set_intelligent_column_widths = _CallRecorder(return_value=True)
    history._apply_month_column_styling = _CallRecorder()
    history._disconnect_resize_handlers = _CallRecorder()
    history._reconnect_resize_handlers = _CallRecorder()
    history._log_resize_debug = _CallRecorder()
    history.force_table_resize = _CallRecorder()

    timer_calls = []
    monkeypatch.setattr(
        history_module.QTimer,
        "singleShot",
        lambda delay, callback: timer_calls.append((delay, callback)),
    )

    history._finalize_history_tables_after_load("Supabase")

    assert len(history.resize_table_to_content.calls) == 3
    assert len(history._set_intelligent_column_widths.calls) == 3
    assert len(history._apply_month_column_styling.calls) == 2
    assert history.main_history_table._month_styled is False
    assert history.room_history_table._month_styled is False
    assert history.totals_table._month_styled is False
    assert timer_calls == [(75, history.force_table_resize)]


def test_finalize_history_tables_after_load_falls_back_when_force_resize_missing(
    monkeypatch,
):
    history = HistoryTab.__new__(HistoryTab)
    history.main_history_table = type("Table", (), {"_month_styled": True})()
    history.room_history_table = type("Table", (), {"_month_styled": True})()
    history.totals_table = type("Table", (), {"_month_styled": True})()
    history.resize_table_to_content = _CallRecorder()
    history._set_intelligent_column_widths = _CallRecorder(return_value=True)
    history._apply_month_column_styling = _CallRecorder()
    history._disconnect_resize_handlers = _CallRecorder()
    history._reconnect_resize_handlers = _CallRecorder()
    history._log_resize_debug = _CallRecorder()
    history._trigger_debounced_resize = _CallRecorder()

    timer_calls = []
    monkeypatch.setattr(
        history_module.QTimer,
        "singleShot",
        lambda delay, callback: timer_calls.append((delay, callback)),
    )

    history._finalize_history_tables_after_load("Supabase")

    assert timer_calls == [(75, history._trigger_debounced_resize)]


def test_resize_table_to_content_uses_bounded_height_for_history_scroll_tables():
    history = HistoryTab.__new__(HistoryTab)
    history._log_resize_debug = _CallRecorder()
    history._log_resize_error = _CallRecorder()
    history._validate_table_for_resize = lambda table, _name: True

    class _Header:
        def height(self):
            return 30

    class _VerticalHeader:
        def defaultSectionSize(self):
            return 35

    class _Table:
        _prefer_internal_vertical_scroll = True

        def __init__(self):
            self.minimum_height = None
            self.maximum_height = None
            self.size_policy = None

        def horizontalHeader(self):
            return _Header()

        def verticalHeader(self):
            return _VerticalHeader()

        def rowCount(self):
            return 40

        def setMinimumHeight(self, value):
            self.minimum_height = value

        def setMaximumHeight(self, value):
            self.maximum_height = value

        def setSizePolicy(self, horizontal, vertical):
            self.size_policy = (horizontal, vertical)

    table = _Table()

    history.resize_table_to_content(table)

    assert table.minimum_height == 252
    assert table.maximum_height == 462


def test_resize_table_to_content_respects_custom_visible_row_bounds():
    history = HistoryTab.__new__(HistoryTab)
    history._log_resize_debug = _CallRecorder()
    history._log_resize_error = _CallRecorder()
    history._validate_table_for_resize = lambda table, _name: True

    class _Header:
        def height(self):
            return 30

    class _VerticalHeader:
        def defaultSectionSize(self):
            return 35

    class _Table:
        _prefer_internal_vertical_scroll = True
        _minimum_visible_rows = 11
        _maximum_visible_rows = 11

        def __init__(self):
            self.minimum_height = None
            self.maximum_height = None

        def horizontalHeader(self):
            return _Header()

        def verticalHeader(self):
            return _VerticalHeader()

        def rowCount(self):
            return 40

        def setMinimumHeight(self, value):
            self.minimum_height = value

        def setMaximumHeight(self, value):
            self.maximum_height = value

        def setSizePolicy(self, horizontal, vertical):
            return None

    table = _Table()

    history.resize_table_to_content(table)

    assert table.minimum_height == 427
    assert table.maximum_height == 427


def test_handle_edit_record_brackets_edit_session_and_emits_local_change(monkeypatch):
    events = []
    local_changes = []

    class _FakeCoordinator:
        def begin_edit_session(self, domain):
            events.append(("begin", domain))

        def end_edit_session(self, domain):
            events.append(("end", domain))

    class _FakeSupabaseManager:
        def is_client_initialized(self):
            return True

        def get_main_calculations_by_id(self, record_id):
            return {"main_data": {"year": 2025}}

        def get_room_calculations(self, record_id):
            return []

    class _FakeDialog:
        def __init__(self, record_id, main_data, room_data_list, parent=None):
            self.record_id = record_id

        def exec_(self):
            return QDialog.Accepted

    monkeypatch.setattr(history_module, "EditRecordDialog", _FakeDialog)

    main_window = type(
        "MainWindow",
        (),
        {
            "supabase_manager": _FakeSupabaseManager(),
            "update_coordinator": _FakeCoordinator(),
            "_emit_local_change": lambda self,
            domain,
            action,
            payload=None: local_changes.append((domain, action, payload)),
        },
    )()

    history = HistoryTab.__new__(HistoryTab)
    history.main_window = main_window

    history.handle_edit_record(7)

    assert events == [("begin", "main_calculation"), ("end", "main_calculation")]
    assert local_changes == [
        ("main_calculation", "edited", {"record_id": 7, "year": 2025})
    ]
