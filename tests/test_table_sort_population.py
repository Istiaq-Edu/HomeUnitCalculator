"""Regressions for table population under an active sort indicator (UI-01).

With sorting enabled and a sort indicator set, per-cell ``setItem``
population re-sorts rows mid-loop: rows move above partially-filled rows
and later cells land in the wrong rows. Population must run with sorting
suspended and the previous sorting state restored afterwards.

Verified against a real QTableWidget (offscreen): the unsuspended
population demonstrably corrupts associations.
"""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from src.ui.table_population import suspended_table_sorting


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_table(columns):
    table = QTableWidget(0, columns)
    table.setSortingEnabled(True)
    table.sortItems(0, Qt.DescendingOrder)  # user clicked the header
    return table


def _pairs_intact(table):
    rows = []
    for r in range(table.rowCount()):
        key = table.item(r, 0).text()
        payload = table.item(r, 1).text() if table.item(r, 1) else None
        rows.append((key, payload))
    return all(
        (key, f"payload-for-{key}") in rows for key, _ in rows
    ) and all(payload == f"payload-for-{key}" for key, payload in rows)


# ---------------------------------------------------------------------------
# The corruption mechanism itself (documents the original behavior)
# ---------------------------------------------------------------------------


def test_live_sort_indicator_corrupts_cell_by_cell_population(qapp):
    """Without suspension, a row inserted with a sort key that places it
    above partially-filled rows makes later cells land on the wrong row."""
    table = _make_table(2)
    rows = [("A", "payload-for-A"), ("B", "payload-for-B")]
    table.setRowCount(len(rows))
    for row_idx, (key, payload) in enumerate(rows):
        table.setItem(row_idx, 0, QTableWidgetItem(key))
        table.setItem(row_idx, 1, QTableWidgetItem(payload))

    assert not _pairs_intact(table)  # the reproduced corruption


# ---------------------------------------------------------------------------
# The suspension helper
# ---------------------------------------------------------------------------


def test_suspended_sorting_keeps_row_payload_associations_intact(qapp):
    table = _make_table(2)
    rows = [("A", "payload-for-A"), ("B", "payload-for-B")]

    with suspended_table_sorting(table):
        table.setRowCount(len(rows))
        for row_idx, (key, payload) in enumerate(rows):
            table.setItem(row_idx, 0, QTableWidgetItem(key))
            table.setItem(row_idx, 1, QTableWidgetItem(payload))

    assert _pairs_intact(table)


def test_sorting_state_and_indicator_are_restored(qapp):
    table = _make_table(2)

    with suspended_table_sorting(table):
        assert table.isSortingEnabled() is False
        table.setRowCount(1)
        table.setItem(0, 0, QTableWidgetItem("Z"))

    assert table.isSortingEnabled() is True
    header = table.horizontalHeader()
    assert header.sortIndicatorSection() == 0
    assert header.sortIndicatorOrder() == Qt.DescendingOrder


def test_sorting_restored_on_exception(qapp):
    table = _make_table(2)

    with pytest.raises(RuntimeError):
        with suspended_table_sorting(table):
            table.setRowCount(1)
            raise RuntimeError("population failed")

    assert table.isSortingEnabled() is True
    assert table.horizontalHeader().sortIndicatorSection() == 0


def test_sorting_stays_disabled_when_it_started_disabled(qapp):
    table = _make_table(2)
    table.setSortingEnabled(False)

    with suspended_table_sorting(table):
        table.setRowCount(1)
        table.setItem(0, 0, QTableWidgetItem("Z"))

    assert table.isSortingEnabled() is False


def test_restored_sort_reapplies_to_completed_rows(qapp):
    """After suspension the captured indicator is reapplied, so the final
    display order matches the user's chosen sort on complete rows."""
    table = _make_table(2)
    rows = [("A", "payload-for-A"), ("B", "payload-for-B")]

    with suspended_table_sorting(table):
        table.setRowCount(len(rows))
        for row_idx, (key, payload) in enumerate(rows):
            table.setItem(row_idx, 0, QTableWidgetItem(key))
            table.setItem(row_idx, 1, QTableWidgetItem(payload))

    # Descending indicator: B first.
    assert table.item(0, 0).text() == "B"
    assert table.item(1, 0).text() == "A"


# ---------------------------------------------------------------------------
# Archived population path (end-to-end through the fixed method)
# ---------------------------------------------------------------------------


class _FakeArchivedTab:
    """Stubbed ArchivedInfoTab surface for _populate_archived_table."""

    def __init__(self, table):
        self.archived_records_table = table
        self._cache_manager = None
        self._batch_manager = None
        self.restored_keys = []
        self._create_identifier_item = lambda text, kind: QTableWidgetItem(text)
        self._create_special_item = (
            lambda text, kind, is_priority=False: QTableWidgetItem(text)
        )
        self._apply_equal_column_widths = lambda table: None
        self._restore_record_selection = lambda key: self.restored_keys.append(key)


def test_archived_population_with_live_indicator_keeps_associations(qapp, monkeypatch):
    from src.ui.tabs.archived_info_tab import ArchivedInfoTab

    table = _make_table(5)  # tenant, room, advanced, created, updated
    tab = _FakeArchivedTab(table)
    records = [
        {
            "id": 1,
            "tenant_name": "A",
            "room_number": "101",
            "advanced_paid": 100.0,
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
        },
        {
            "id": 2,
            "tenant_name": "B",
            "room_number": "102",
            "advanced_paid": 200.0,
            "created_at": "2026-02-01",
            "updated_at": "2026-02-02",
        },
    ]

    # Bind the real method onto the fake surface.
    tab._populate_archived_table = ArchivedInfoTab._populate_archived_table.__get__(tab)
    tab._populate_archived_table("Cloud (Supabase)", records, restore_selection_key=None)

    for r in range(table.rowCount()):
        tenant = table.item(r, 0).text()
        payload = table.item(r, 0).data(Qt.UserRole)
        assert payload["tenant_name"] == tenant  # payload matches its row
    assert {table.item(r, 0).text() for r in range(table.rowCount())} == {"A", "B"}
    assert table.isSortingEnabled() is True
    assert table.horizontalHeader().sortIndicatorOrder() == Qt.DescendingOrder
    assert tab.restored_keys == [None]
