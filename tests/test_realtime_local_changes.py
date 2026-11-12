from src.core.HomeUnitCalculator import MeterCalculationApp


class _FakeTabLoader:
    def __init__(self, loaded, tabs=None):
        self.loaded = set(loaded)
        self.tabs = dict(tabs or {})

    def is_loaded(self, name):
        return name in self.loaded

    def get_tab(self, name):
        return self.tabs[name]


class _CallRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class _DummyWidget:
    def __init__(self, name):
        self._name = name

    def objectName(self):
        return self._name


class _DummyStackedWidget:
    def __init__(self, name):
        self._widget = _DummyWidget(name)

    def currentWidget(self):
        return self._widget


def test_handle_local_rental_change_refreshes_loaded_surfaces_only():
    rental_reload = _CallRecorder()
    dashboard_sync = _CallRecorder()
    rental_tab = type("RentalTab", (), {"load_rental_records": rental_reload})()
    dashboard_tab = type(
        "DashboardTab", (), {"_sync_rentals_cache_async": dashboard_sync}
    )()

    app = MeterCalculationApp.__new__(MeterCalculationApp)
    app.tab_loader = _FakeTabLoader(
        {"rental", "dashboard"},
        tabs={"rental": rental_tab, "dashboard": dashboard_tab},
    )
    app._pending_tab_refreshes = set()
    app._route_to_tab = {}

    MeterCalculationApp._handle_local_rental_change(
        app, "saved", {"room_number": "101"}
    )

    assert rental_reload.calls == [((), {"force_refresh": True})]
    assert len(dashboard_sync.calls) == 1


def test_handle_local_main_calculation_change_refreshes_dashboard_and_history():
    dashboard_year_sync = _CallRecorder()
    dashboard_owner_sync = _CallRecorder()
    history_reload = _CallRecorder()
    dashboard_tab = type(
        "DashboardTab",
        (),
        {
            "_sync_year_async": dashboard_year_sync,
            "_sync_owner_room_year_async": dashboard_owner_sync,
            "_refresh_years_from_supabase_async": _CallRecorder(),
        },
    )()
    history_tab = type("HistoryTab", (), {"load_history": history_reload})()

    app = MeterCalculationApp.__new__(MeterCalculationApp)
    app.tab_loader = _FakeTabLoader(
        {"dashboard", "history"},
        tabs={"dashboard": dashboard_tab, "history": history_tab},
    )
    app._pending_tab_refreshes = set()
    app._route_to_tab = {}
    app.load_history_source_combo = type(
        "Combo", (), {"currentText": lambda self: "Load from Cloud"}
    )()

    MeterCalculationApp._handle_local_main_calculation_change(
        app,
        "saved",
        {"year": 2025, "month": "January"},
    )

    assert dashboard_year_sync.calls == [((2025,), {})]
    assert dashboard_owner_sync.calls == [((2025,), {})]
    assert history_reload.calls == [((), {})]


def test_handle_local_main_calculation_change_without_year_refreshes_available_years():
    dashboard_refresh_years = _CallRecorder()
    dashboard_tab = type(
        "DashboardTab",
        (),
        {
            "_sync_year_async": _CallRecorder(),
            "_sync_owner_room_year_async": _CallRecorder(),
            "_refresh_years_from_supabase_async": dashboard_refresh_years,
        },
    )()

    app = MeterCalculationApp.__new__(MeterCalculationApp)
    app.tab_loader = _FakeTabLoader({"dashboard"}, tabs={"dashboard": dashboard_tab})
    app._pending_tab_refreshes = set()
    app._route_to_tab = {}

    MeterCalculationApp._handle_local_main_calculation_change(app, "saved", {})

    assert dashboard_refresh_years.calls == [((), {})]


def test_refresh_or_queue_tab_queues_hidden_tab_and_flushes_on_activation():
    rental_reload = _CallRecorder()
    rental_tab = type("RentalTab", (), {"load_rental_records": rental_reload})()

    app = MeterCalculationApp.__new__(MeterCalculationApp)
    app.tab_loader = _FakeTabLoader({"rental"}, tabs={"rental": rental_tab})
    app._pending_tab_refreshes = set()
    app._route_to_tab = {"DashboardId": "dashboard", "RentalId": "rental"}
    app.stackedWidget = _DummyStackedWidget("DashboardId")

    MeterCalculationApp._refresh_or_queue_tab(app, "rental")

    assert rental_reload.calls == []
    assert app._pending_tab_refreshes == {"rental"}

    app.stackedWidget = _DummyStackedWidget("RentalId")
    MeterCalculationApp._flush_pending_tab_refresh(app, "rental")

    assert rental_reload.calls == [((), {"force_refresh": True})]
    assert app._pending_tab_refreshes == set()
