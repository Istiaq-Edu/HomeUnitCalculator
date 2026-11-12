"""Regressions for monthly cloud persistence outcomes (DATA-02).

Covers the empty-replacement contract (an empty room list must remove the
previous cloud rows), no false success when old-row deletion fails after a
successful insert, and cascade-first monthly deletion with orphan
verification.
"""

from types import SimpleNamespace

from src.core.supabase_manager import SupabaseManager


class _Response:
    def __init__(self, data):
        self.data = data

    def json(self):
        return {"data": self.data}


def _key(table, ops):
    return (table, ops[0][0], ops[1][0] if len(ops) > 1 else "execute")


class _Table:
    def __init__(self, name, client):
        self._name = name
        self._client = client
        self._ops = []

    def select(self, columns):
        self._ops.append(("select", columns))
        return self

    def insert(self, payload):
        self._ops.append(("insert", payload))
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
        key = _key(self._name, self._ops)
        self._client.executed.append((self._name, tuple(self._ops)))
        outcome = self._client.script.get(key, [])
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
    return manager


def _room_ops(client, table="room_calculations"):
    return [entry for entry in client.executed if entry[0] == table]


RC = "room_calculations"
MC = "main_calculations"


# ---------------------------------------------------------------------------
# save_room_calculations
# ---------------------------------------------------------------------------


def test_empty_replacement_deletes_existing_room_rows():
    """Empty room list with existing cloud rows must delete them (DATA-02).
    The old behavior returned True without issuing any deletion."""
    script = {
        (RC, "select", "eq"): [{"id": 41}],
        (RC, "delete", "in_"): [{"id": 41}],
    }
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, []) is True

    ops = [entry[1] for entry in _room_ops(manager.supabase)]
    insert_chains = [chain for chain in ops if chain[0][0] == "insert"]
    delete_chains = [chain for chain in ops if chain[0][0] == "delete"]
    assert insert_chains == []  # nothing to insert
    assert len(delete_chains) == 1
    assert delete_chains[0][1] == ("in_", ("id", [41]))


def test_empty_replacement_with_no_existing_rows_succeeds_without_delete():
    script = {(RC, "select", "eq"): []}
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, []) is True
    ops = [entry[1] for entry in _room_ops(manager.supabase)]
    assert all(op[0][0] != "delete" for op in ops)


def test_empty_replacement_delete_failure_is_reported_not_success():
    script = {
        (RC, "select", "eq"): [{"id": 41}],
        (RC, "delete", "in_"): RuntimeError("delete failed"),
    }
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, []) is False


def test_empty_replacement_partial_delete_is_reported_not_success():
    script = {
        (RC, "select", "eq"): [{"id": 41}, {"id": 42}],
        (RC, "delete", "in_"): [{"id": 41}],  # one row vanished unnoticed
    }
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, []) is False


def test_insert_success_then_old_delete_failure_is_not_success():
    """Insert succeeded, old rows survived: the aggregate must not report
    plain success (the old behavior swallowed the deletion error)."""
    new_records = [{"room_data": {"room_name": "Room 1"}}]
    script = {
        (RC, "select", "eq"): [{"id": 41}],
        (RC, "insert", "execute"): [{"id": 91}],
        (RC, "delete", "in_"): RuntimeError("delete failed"),
    }
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, new_records) is False
    # The insert itself was executed (new rows are durable).
    chains = [entry[1] for entry in _room_ops(manager.supabase)]
    insert_chains = [chain for chain in chains if chain[0][0] == "insert"]
    assert len(insert_chains) == 1


def test_full_replacement_insert_then_delete_old_rows():
    new_records = [
        {"room_data": {"room_name": "Room 1"}},
        {"room_data": {"room_name": "Room 2"}},
    ]
    script = {
        (RC, "select", "eq"): [{"id": 41}, {"id": 42}],
        (RC, "insert", "execute"): [{"id": 91}, {"id": 92}],
        (RC, "delete", "in_"): [{"id": 41}, {"id": 42}],
    }
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, new_records) is True
    ops = [entry[1] for entry in _room_ops(manager.supabase)]
    order = [op[0][0] for op in ops]
    assert order == ["select", "insert", "delete"]  # old rows deleted after insert


def test_partial_insert_persistence_is_reported_not_success():
    new_records = [{"room_data": {"room_name": "Room 1"}}]
    script = {
        (RC, "select", "eq"): [],
        (RC, "insert", "execute"): [],  # nothing persisted
    }
    manager = _make_manager(script)

    assert manager.save_room_calculations(7, new_records) is False


# ---------------------------------------------------------------------------
# delete_calculation_record
# ---------------------------------------------------------------------------


def test_monthly_delete_uses_parent_delete_and_cascade():
    """Parent-first delete relies on the FK cascade; a read-only check finds
    no orphans and no extra child delete is issued."""
    script = {
        (MC, "delete", "eq"): [{"id": 7}],
        (RC, "select", "eq"): [],
    }
    manager = _make_manager(script)

    assert manager.delete_calculation_record(7) is True

    executed = manager.supabase.executed
    assert executed[0][0] == MC  # parent deleted first
    assert executed[0][1][0][0] == "delete"
    room_deletes = [
        entry for entry in executed if entry[0] == RC and entry[1][0][0] == "delete"
    ]
    assert room_deletes == []


def test_monthly_delete_parent_delete_failure_returns_false():
    script = {(MC, "delete", "eq"): []}  # no rows matched
    manager = _make_manager(script)

    assert manager.delete_calculation_record(7) is False
    # No room-table work was attempted.
    assert _room_ops(manager.supabase) == []


def test_monthly_delete_orphan_cleanup_failure_is_not_success():
    """Without cascade, orphaned children plus a failed cleanup must not
    report success (parent already deleted, children remain)."""
    script = {
        (MC, "delete", "eq"): [{"id": 7}],
        (RC, "select", "eq"): [{"id": 41}, {"id": 42}],
        (RC, "delete", "eq"): [{"id": 41}],  # partial cleanup
    }
    manager = _make_manager(script)

    assert manager.delete_calculation_record(7) is False


def test_monthly_delete_without_cascade_cleans_orphans_explicitly():
    script = {
        (MC, "delete", "eq"): [{"id": 7}],
        (RC, "select", "eq"): [{"id": 41}, {"id": 42}],
        (RC, "delete", "eq"): [{"id": 41}, {"id": 42}],
    }
    manager = _make_manager(script)

    assert manager.delete_calculation_record(7) is True


# ---------------------------------------------------------------------------
# Caller: monthly save must invoke the room save even with an empty list
# ---------------------------------------------------------------------------


class _FakeInput:
    def __init__(self, text="100"):
        self._text = text

    def text(self):
        return self._text


class _FakeLabel:
    def __init__(self, text="1.00"):
        self._text = text

    def text(self):
        return self._text


class _FakeCombo:
    def currentText(self):
        return "June"


class _FakeSpin:
    def value(self):
        return 2025


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

    @classmethod
    def question(cls, *args, **kwargs):
        return cls.No


def _make_app(fake_manager):
    import src.core.HomeUnitCalculator as huc_module

    app = huc_module.MeterCalculationApp.__new__(huc_module.MeterCalculationApp)
    app.supabase_manager = fake_manager
    app.check_internet_connectivity = lambda: True
    # main_tab_instance / rooms_tab_instance are read-only properties backed
    # by the tab loader, so the loader itself is faked.
    fake_main_tab = SimpleNamespace(
        month_combo=_FakeCombo(),
        year_spinbox=_FakeSpin(),
        meter_entries=[_FakeInput()],
        diff_entries=[_FakeInput()],
        total_unit_value_label=_FakeLabel(),
        total_diff_value_label=_FakeLabel(),
        per_unit_cost_value_label=_FakeLabel(),
        additional_amount_value_label=_FakeLabel(),
        in_total_value_label=_FakeLabel(),
        room_entries=[],
    )
    app.tab_loader = SimpleNamespace(get_tab=lambda name: fake_main_tab)
    app._emit_local_change = lambda *args, **kwargs: None
    return app, huc_module


def test_monthly_save_with_no_rooms_still_calls_room_replacement(monkeypatch):
    """Overwriting a month with zero rooms must still reach
    save_room_calculations so the previous cloud rows are removed (DATA-02).
    The old caller skipped the call entirely for an empty room list."""
    _FakeMessageBox.calls = []
    _FakeMessageBox.No = object()
    monkeypatch.setattr("src.core.HomeUnitCalculator.QMessageBox", _FakeMessageBox)

    room_calls = []

    class _FakeManager:
        def is_client_initialized(self):
            return True

        def get_main_calculation_by_month_year(self, month, year):
            return None

        def save_main_calculation(self, data):
            return 7

        def save_room_calculations(self, main_id, room_list):
            room_calls.append((main_id, room_list))
            return True

    app, huc_module = _make_app(_FakeManager())
    app.save_calculation_to_supabase()

    assert room_calls == [(7, [])]  # invoked with the empty replacement list
    assert any(level == "information" for level, _ in _FakeMessageBox.calls)


def test_monthly_save_empty_replacement_failure_is_reported(monkeypatch):
    _FakeMessageBox.calls = []
    _FakeMessageBox.No = object()
    monkeypatch.setattr("src.core.HomeUnitCalculator.QMessageBox", _FakeMessageBox)

    class _FakeManager:
        def is_client_initialized(self):
            return True

        def get_main_calculation_by_month_year(self, month, year):
            return None

        def save_main_calculation(self, data):
            return 7

        def save_room_calculations(self, main_id, room_list):
            return False

    app, huc_module = _make_app(_FakeManager())
    app.save_calculation_to_supabase()

    levels = [level for level, _ in _FakeMessageBox.calls]
    assert "warning" in levels
    assert "information" not in levels  # no false success
