"""Global keyboard shortcut manager implemented with PyQt5 and qfluentwidgets.

This module centralises every application-wide keyboard navigation rule.
Import once (e.g., from MeterCalculationApp.__init__) and forget—the
manager lives for the lifetime of the main window.
"""
from __future__ import annotations

from typing import List, Tuple, Callable

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut, QMainWindow

try:
    # Only for type-checking / theming convenience; no runtime dependency if missing
    from qfluentwidgets import ShortcutTip  # type: ignore
except ImportError:  # pragma: no cover – optional
    ShortcutTip = None  # type: ignore


class KeyboardNavigationManager(QObject):
    """Attach common shortcuts to a *QMainWindow* instance.

    Currently supported keys (feel free to expand):
    ────────────────────────────────────────────────────────────
      Ctrl+Tab            → next tab
      Ctrl+Shift+Tab      → previous tab
      Ctrl+S              → save (delegates based on active tab)
      Ctrl+P              → export PDF (main / room tabs only)
      Ctrl+Shift+S        → save to cloud (main / room tabs only)
      F5                  → refresh / reload (History & Archived tabs)
      Esc                 → close topmost dialog or exit full-screen
    """

    def __init__(self, main_window: QMainWindow):  # noqa: D401
        super().__init__(main_window)
        self._mw = main_window
        self._shortcuts: List[QShortcut] = []

        # Sequence → handler mapping
        bindings: List[Tuple[str, Callable[[], None]]] = [
            ("Ctrl+Tab", self._next_tab),
            ("Ctrl+Shift+Tab", self._prev_tab),
            ("Ctrl+S", self._save),
            ("Ctrl+P", self._export_pdf),
            ("Ctrl+Shift+S", self._save_cloud),
            ("F5", self._refresh_current_tab),
            ("Esc", self._escape_handler),
        ]

        for seq, slot in bindings:
            sc = QShortcut(QKeySequence(seq), main_window)
            sc.activated.connect(slot)
            self._shortcuts.append(sc)

            # Optional—show a Fluent "ShortcutTip" overlay (requires qfluentwidgets >= 1.4)
            if ShortcutTip is not None:
                ShortcutTip.bind(sc, slot.__doc__ or seq)

    # ────────────────────── helpers ──────────────────────────
    def _current_tab_name(self) -> str:
        return self._mw.tab_widget.tabText(self._mw.tab_widget.currentIndex())

    # ────────────────────── actions ───────────────────────────
    def _next_tab(self):  # noqa: D401
        idx = self._mw.tab_widget.currentIndex()
        self._mw.tab_widget.setCurrentIndex((idx + 1) % self._mw.tab_widget.count())

    def _prev_tab(self):  # noqa: D401
        idx = self._mw.tab_widget.currentIndex()
        self._mw.tab_widget.setCurrentIndex((idx - 1) % self._mw.tab_widget.count())

    def _save(self):  # noqa: D401
        """Ctrl+S handler – context-aware save."""
        tab = self._current_tab_name()
        if tab == "Main Calculation":
            self._mw.main_tab_instance.save_main_calculation()
        elif tab == "Room Calculations":
            self._mw.rooms_tab_instance.save_room_calculations()
        elif tab == "Rental Info":
            self._mw.rental_info_tab_instance.save_rental_record()
        # Else: no-op

    def _export_pdf(self):  # noqa: D401
        if self._current_tab_name() in {"Main Calculation", "Room Calculations"}:
            self._mw.save_to_pdf()

    def _save_cloud(self):  # noqa: D401
        if self._current_tab_name() in {"Main Calculation", "Room Calculations"}:
            self._mw.save_calculation_to_supabase()

    def _refresh_current_tab(self):  # noqa: D401
        tab = self._current_tab_name()
        if tab == "Calculation History":
            self._mw.history_tab_instance.reload_history()
        elif tab == "Archived Info":
            self._mw.archived_info_tab_instance.load_archived_records()

    def _escape_handler(self):  # noqa: D401
        # Close top-level modal if any; else no-op.
        for w in self._mw.findChildren(QMainWindow):
            if w.isModal() and w.isVisible():
                w.close()
                return 