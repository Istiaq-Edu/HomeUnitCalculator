"""Shared table population helpers (UI-01).

With a QTableWidget sort indicator active, per-cell population re-sorts
rows mid-loop: ``setItem`` on the sort column moves already-filled rows,
so later cells land in the wrong rows and row/payload associations
corrupt. Sorting must be suspended for the whole population pass and the
previous sorting state restored afterwards, before selection is restored
by identity.
"""

from contextlib import contextmanager


@contextmanager
def suspended_table_sorting(table):
    """Suspend a QTableWidget's sorting during a population pass.

    Captures the prior sorting-enabled state and sort indicator, disables
    sorting for the wrapped block, and restores both afterwards (reapplying
    the captured indicator to the completed rows). Restores state even when
    the block raises.
    """
    was_enabled = table.isSortingEnabled()
    sort_section = table.horizontalHeader().sortIndicatorSection()
    sort_order = table.horizontalHeader().sortIndicatorOrder()
    table.setSortingEnabled(False)
    try:
        yield
    finally:
        if was_enabled:
            table.setSortingEnabled(True)
            table.sortItems(sort_section, sort_order)
