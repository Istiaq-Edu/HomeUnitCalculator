"""Regressions for room-undo result freshness (CALC-08).

Undo must restore the removed room's identity and inputs, but recompute
its derived bill under the current result revision: the snapshot taken at
removal time carries derived labels from the rate in effect then, and
reinserting them presents a stale bill as if it were current.
"""

from types import SimpleNamespace

from src.ui.tabs.main_tab import MainTab


class _FakeToast:
    calls = []

    @classmethod
    def record(cls, kind, title, content):
        cls.calls.append((kind, title, content))


def _make_tab(current_rooms, removed, index, maximum=10):
    tab = MainTab.__new__(MainTab)
    tab._pending_room_undo = (7, index, removed, None)
    tab._room_undo_token = 7
    tab.num_rooms_spinbox = SimpleNamespace(maximum=lambda: maximum)
    tab._snapshot_room_data = lambda: [dict(room) for room in current_rooms]
    applied = []
    tab._apply_room_data = lambda room_data: applied.append(list(room_data))
    recalculated = []
    tab.calculate_rooms = lambda: recalculated.append(True)
    tab._show_room_toast = lambda kind, title, content, **kwargs: _FakeToast.record(
        kind, title, content
    )
    # Precompute the same expected_state the removal path would have stored.
    tab._pending_room_undo = (
        7,
        index,
        removed,
        MainTab._editable_state([room for i, room in enumerate(current_rooms)]),
    )
    return tab, applied, recalculated


def test_undo_strips_stale_derived_labels_from_restored_room():
    """The removed room's snapshot carries derived labels computed with an
    older rate; restoring them verbatim presents a stale bill as current."""
    _FakeToast.calls = []
    survivors = [
        {
            "room_name": "Flat A",
            "present": "100",
            "previous": "50",
            "gas_bill": "0",
            "water_bill": "0",
            "house_rent": "500",
            "real_unit": "50",
            "unit_bill": "165.00 TK",
            "grand_total": "665.00 TK",
            "supabase_id": None,
        }
    ]
    removed = {
        "room_name": "Flat B",
        "present": "80",
        "previous": "70",
        "gas_bill": "0",
        "water_bill": "0",
        "house_rent": "400",
        "real_unit": "10",
        "unit_bill": "33.00 TK",  # derived with the OLD rate
        "grand_total": "433.00 TK",
        "supabase_id": "uuid-b",
    }
    tab, applied, recalculated = _make_tab(survivors, removed, index=0)

    tab._undo_remove_room()

    assert len(applied) == 1
    restored = applied[0]
    assert len(restored) == 2
    restored_room = restored[0]
    assert restored_room["room_name"] == "Flat B"
    assert restored_room["supabase_id"] == "uuid-b"
    assert restored_room["present"] == "80"  # inputs preserved
    # Stale derived values must not be reinserted.
    assert "real_unit" not in restored_room
    assert "unit_bill" not in restored_room
    assert "grand_total" not in restored_room
    # Survivors keep their current (already recalculated) labels.
    assert restored[1]["unit_bill"] == "165.00 TK"
    assert recalculated == [True]  # recomputed under the current revision
    assert any(title == "Room restored" for _, title, _ in _FakeToast.calls)


def test_undo_survives_recalculation_failure():
    """Without a valid current rate, undo still restores the room with an
    honest N/A state and never crashes."""
    _FakeToast.calls = []
    survivors = [{"room_name": "Flat A", "present": "1", "previous": "0",
                  "gas_bill": "0", "water_bill": "0", "house_rent": "0",
                  "supabase_id": None}]
    removed = {"room_name": "Flat B", "present": "2", "previous": "0",
               "gas_bill": "0", "water_bill": "0", "house_rent": "0",
               "unit_bill": "stale", "supabase_id": None}
    tab, applied, _ = _make_tab(survivors, removed, index=0)
    tab.calculate_rooms = lambda: (_ for _ in ()).throw(ValueError("rate empty"))

    tab._undo_remove_room()

    assert "unit_bill" not in applied[0][0]
    assert any(title == "Room restored" for _, title, _ in _FakeToast.calls)


def test_undo_still_rejects_after_any_room_edit():
    """The existing safeguard is preserved: any editable change since the
    removal invalidates the undo."""
    _FakeToast.calls = []
    survivors = [{"room_name": "Flat A", "present": "100", "previous": "50",
                  "gas_bill": "0", "water_bill": "0", "house_rent": "500",
                  "supabase_id": None}]
    removed = {"room_name": "Flat B", "present": "80", "previous": "70",
               "gas_bill": "0", "water_bill": "0", "house_rent": "400",
               "supabase_id": None}
    tab, applied, recalculated = _make_tab(survivors, removed, index=0)
    # The user edited a surviving room after the removal.
    tab._snapshot_room_data = lambda: [dict(survivors[0], present="101")]

    tab._undo_remove_room()

    assert applied == []  # nothing restored
    assert recalculated == []
    assert any(title == "Undo unavailable" for _, title, _ in _FakeToast.calls)


def test_undo_keeps_removed_room_position():
    survivors = [
        {"room_name": "Flat A", "present": "1", "previous": "0",
         "gas_bill": "0", "water_bill": "0", "house_rent": "0",
         "supabase_id": None},
        {"room_name": "Flat C", "present": "3", "previous": "0",
         "gas_bill": "0", "water_bill": "0", "house_rent": "0",
         "supabase_id": None},
    ]
    removed = {"room_name": "Flat B", "present": "2", "previous": "0",
               "gas_bill": "0", "water_bill": "0", "house_rent": "0",
               "supabase_id": None}
    tab, applied, _ = _make_tab(survivors, removed, index=1)

    tab._undo_remove_room()

    names = [room["room_name"] for room in applied[0]]
    assert names == ["Flat A", "Flat B", "Flat C"]
