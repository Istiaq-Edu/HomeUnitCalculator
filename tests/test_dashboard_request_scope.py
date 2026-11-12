"""Regressions for dashboard request scoping and data truthfulness.

Covers audit findings DASH-03/DATA-10 (stale completions, dropped
requests), DASH-04 (January must use the previous year's December),
DASH-05 (missing data is not a measured zero), DASH-06 (per-snapshot
freshness) and DASH-08 (delta direction computed before state advance).
"""

from datetime import datetime as _real_datetime
from types import SimpleNamespace

from src.ui.tabs import dashboard_tab as dt_module
from src.ui.tabs.dashboard_tab import DashboardTab


LANES = ("years", "main", "owner_main", "room", "rentals")


class _Signal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)


class _FakeLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _FakeCard:
    def __init__(self):
        self._kpi_value_label = _FakeLabel()

    def setToolTip(self, text):
        self.tooltip = text


def _make_dashboard():
    dashboard = DashboardTab.__new__(DashboardTab)
    dashboard._lane_generations = {lane: 0 for lane in LANES}
    dashboard._lane_pending = {lane: None for lane in LANES}
    # Explicit None worker attrs: an unwrapped __new__ instance must never
    # fall through to QWidget attribute resolution (RuntimeError).
    dashboard._years_worker = None
    dashboard._sync_worker = None
    dashboard._owner_room_main_sync_worker = None
    dashboard._room_sync_worker = None
    dashboard._rentals_sync_worker = None
    dashboard.main_window = SimpleNamespace(
        supabase_manager=SimpleNamespace(is_client_initialized=lambda: True)
    )
    dashboard._db_path = "sandbox.db"
    dashboard._set_status = lambda *args, **kwargs: None
    dashboard._begin_global_update_activity = lambda *args, **kwargs: None
    dashboard._end_global_update_activity = lambda *args, **kwargs: None
    dashboard._sync_worker_year = None
    rendered = []
    dashboard._render_year_from_cache = lambda year: rendered.append(int(year))
    return dashboard, rendered


class _FakeMainWorker:
    instances = []

    def __init__(self, manager, db_path, year):
        self.year = year
        self.sync_finished = _Signal()
        self.error_occurred = _Signal()
        self._running = False
        _FakeMainWorker.instances.append(self)

    def isRunning(self):
        return self._running

    def start(self):
        self._running = True


def _install_fake_worker(monkeypatch):
    _FakeMainWorker.instances = []
    monkeypatch.setattr(
        "src.ui.background_workers.SyncSupabaseMainCalculationsYearWorker",
        _FakeMainWorker,
    )
    return _FakeMainWorker.instances


def test_stale_year_completion_is_rejected_and_latest_request_retried(monkeypatch):
    dashboard, rendered = _make_dashboard()
    created = _install_fake_worker(monkeypatch)

    dashboard._sync_year_async(2024)
    assert dashboard._lane_generations["main"] == 1
    assert len(created) == 1

    # Newest user intent arrives while the first worker is still running.
    dashboard._sync_year_async(2025)
    assert dashboard._lane_generations["main"] == 2
    assert dashboard._lane_pending["main"] is not None
    assert len(created) == 1  # no second worker was started

    stale = created[0]
    assert getattr(stale, "_scope_gen", None) == 1
    stale._running = False  # worker finished, but its request is now stale
    dashboard._sync_worker_year = 2024
    dashboard._on_sync_finished(2024)

    # The stale completion must not render the old year...
    assert rendered == []
    # ...and the retained latest request must be re-dispatched.
    assert dashboard._lane_pending["main"] is None
    assert len(created) == 2
    assert created[1].year == 2025
    assert dashboard._sync_worker is created[1]
    assert getattr(created[1], "_scope_gen", None) == 3

    created[1]._running = False
    dashboard._sync_worker_year = 2025
    dashboard._on_sync_finished(2025)
    assert rendered == [2025]


def test_current_year_completion_renders(monkeypatch):
    dashboard, rendered = _make_dashboard()
    created = _install_fake_worker(monkeypatch)

    dashboard._sync_year_async(2024)
    created[0]._running = False
    dashboard._sync_worker_year = 2024
    dashboard._on_sync_finished(2024)

    assert rendered == [2024]
    assert dashboard._lane_pending["main"] is None


class _FixedDateTime(_real_datetime):
    """datetime replacement so January branches are deterministic."""

    @classmethod
    def now(cls):
        return cls(2027, 1, 15)


def _make_kpi_cards(dashboard):
    names = (
        "kpi_total",
        "kpi_avg",
        "kpi_high",
        "kpi_low",
        "rate_kpi_current",
        "rate_kpi_prev",
        "rate_kpi_high",
        "rate_kpi_low",
        "elec_kpi_current",
        "elec_kpi_prev",
        "elec_kpi_high",
        "elec_kpi_low",
        "owner_kpi_total",
        "owner_kpi_avg",
        "owner_kpi_high",
        "owner_kpi_low",
        "_summary_total_bill",
        "_summary_elec_bill",
        "_summary_rate",
        "_summary_units",
        "_summary_owner_bill",
        "_summary_tenant_bill",
        "_summary_gas_bill",
        "_summary_rooms",
    )
    for name in names:
        setattr(dashboard, name, _FakeCard())


def test_january_section_kpis_use_previous_year_december(monkeypatch):
    monkeypatch.setattr(dt_module, "datetime", _FixedDateTime)
    dashboard = DashboardTab.__new__(DashboardTab)
    _make_kpi_cards(dashboard)

    current_year_raw = [100.0] * 12
    prev_year_raw = [None] * 11 + [999.0]

    dashboard._update_section_kpis(
        kpis={
            "current": dashboard.kpi_total,
            "prev": dashboard.kpi_avg,
            "high": dashboard.kpi_high,
            "low": dashboard.kpi_low,
        },
        raw_values=current_year_raw,
        year=2027,
        fmt_fn=dashboard._fmt_tk,
        consider_fn=lambda v: v is not None,
        clamp_to_current_year=True,
        empty_consider_fallback=True,
        prev_year_raw=prev_year_raw,
    )

    # Recent month is December 2026 (999), not December 2027 (100).
    assert dashboard.kpi_total._kpi_value_label.text == "Dec \u00b7 TK 999"
    # Previous month is November 2026, which has no recorded data.
    assert dashboard.kpi_avg._kpi_value_label.text == "Nov \u00b7 \u2014"


def test_january_section_kpis_without_previous_year_show_placeholder(monkeypatch):
    monkeypatch.setattr(dt_module, "datetime", _FixedDateTime)
    dashboard = DashboardTab.__new__(DashboardTab)
    _make_kpi_cards(dashboard)

    dashboard._update_section_kpis(
        kpis={
            "current": dashboard.kpi_total,
            "prev": dashboard.kpi_avg,
            "high": dashboard.kpi_high,
            "low": dashboard.kpi_low,
        },
        raw_values=[100.0] * 12,
        year=2027,
        fmt_fn=dashboard._fmt_tk,
        prev_year_raw=None,
    )

    assert dashboard.kpi_total._kpi_value_label.text == "\u2014"
    assert dashboard.kpi_avg._kpi_value_label.text == "\u2014"


def test_missing_month_tooltips_say_no_data_and_recorded_zero_stays_zero():
    dashboard = DashboardTab.__new__(DashboardTab)

    tooltips = dashboard._build_tooltips([None, 100.0, 0.0] + [None] * 9)

    assert "No data" in tooltips[0]
    # First present month has no predecessor to compare with.
    assert "\U0001F4C8" not in tooltips[1]
    assert "TK 100" in tooltips[1]
    # A recorded zero is measured data, not missing data.
    assert "No data" not in tooltips[2]
    assert "TK 0" in tooltips[2]


def test_owner_room_delta_icon_uses_direction_before_state_advance():
    dashboard = DashboardTab.__new__(DashboardTab)

    tooltips = dashboard._build_owner_room_tooltips(
        raw_values=[200.0, 100.0] + [None] * 10,
        year=2026,
        room_name="",
        mode="Owner",
    )

    # Bill fell from 200 to 100: the icon must point down (DASH-08).
    assert "\U0001F4C9" in tooltips[1]
    assert "\U0001F4C8" not in tooltips[1]


def test_summary_kpis_distinguish_missing_from_zero(monkeypatch):
    dashboard = DashboardTab.__new__(DashboardTab)
    _make_kpi_cards(dashboard)
    dashboard.db_manager = None
    dashboard._get_dashboard_year_snapshot = lambda year: {}

    # Snapshot for a past year with only November recorded as a real zero.
    snapshot = {"monthly_totals": {"November": 0.0}}
    dashboard._update_summary_kpis(snapshot, 2025)

    # Recent month (November, last present month) is a measured zero.
    assert dashboard._summary_total_bill._kpi_value_label.text == "TK 0"
    # Electricity/other lanes have no data for that month: placeholder.
    assert dashboard._summary_elec_bill._kpi_value_label.text == "---"


def test_summary_january_reads_previous_year_snapshot(monkeypatch):
    monkeypatch.setattr(dt_module, "datetime", _FixedDateTime)
    dashboard = DashboardTab.__new__(DashboardTab)
    _make_kpi_cards(dashboard)
    dashboard.db_manager = None

    snapshots = {
        2027: {"monthly_totals": {"December": 100.0}},
        2026: {"monthly_totals": {"December": 777.0}},
    }
    dashboard._get_dashboard_year_snapshot = lambda year: snapshots.get(year, {})

    dashboard._update_summary_kpis(snapshots[2027], 2027)

    assert dashboard._summary_total_bill._kpi_value_label.text == "TK 777"


def test_rate_and_elec_render_use_their_own_snapshot_freshness(monkeypatch):
    dashboard = DashboardTab.__new__(DashboardTab)
    _make_kpi_cards(dashboard)
    dashboard.db_manager = None
    dashboard._qtchart = None
    dashboard._chart_widget = None
    dashboard._rate_qtchart = None
    dashboard._rate_chart_widget = None
    dashboard._elec_qtchart = None
    dashboard._elec_chart_widget = None
    dashboard.rate_meta_label = _FakeLabel()
    dashboard.elec_meta_label = _FakeLabel()
    dashboard._set_owner_room_status = lambda *args, **kwargs: None
    dashboard._update_rate_kpis = lambda *args, **kwargs: None
    dashboard._update_elec_kpis = lambda *args, **kwargs: None

    snapshots = {
        2025: {
            "monthly_per_unit_cost": {"November": 7.5},
            "monthly_total_electricity_bills": {"November": 250.0},
            "last_sync": "rate-elec-stamp",
        },
    }
    dashboard._get_dashboard_year_snapshot = lambda year: snapshots.get(year, {})

    dashboard._render_rate_from_cache(2025)
    dashboard._render_elec_from_cache(2025)

    assert "rate-elec-stamp" in dashboard.rate_meta_label.text
    assert "rate-elec-stamp" in dashboard.elec_meta_label.text
