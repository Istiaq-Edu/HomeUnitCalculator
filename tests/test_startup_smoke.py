import importlib
import os
import sys

import pytest
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QApplication, QWidget

from src.core.lazy_tab_loader import LazyTabLoader


def _fresh_import(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_import_homeunitcalculator_exports_app_class():
    module = _fresh_import("src.core.HomeUnitCalculator")

    assert hasattr(module, "MeterCalculationApp")
    assert os.environ["QFLUENTWIDGETS_DISABLE_TIPS"] == "1"


def test_import_homeunitcalculator_does_not_create_qapplication():
    assert QApplication.instance() is None

    _fresh_import("src.core.HomeUnitCalculator")

    assert QApplication.instance() is None


def test_import_homeunitcalculator_keeps_heavy_tabs_deferred():
    sys.modules.pop("src.ui.tabs.dashboard_tab", None)
    sys.modules.pop("src.core.HomeUnitCalculator", None)

    _fresh_import("src.core.HomeUnitCalculator")

    assert "src.ui.tabs.dashboard_tab" not in sys.modules


def test_startup_timer_autostarts_on_import():
    module = _fresh_import("src.core.startup_timer")

    assert module.StartupTimer._start_time is not None
    assert module.StartupTimer._checkpoints
    assert module.StartupTimer._checkpoints[0][0] == "Application started"


def test_lazy_tab_loader_only_loads_lazy_tabs_on_access(qapp):
    host = QWidget()
    loader = LazyTabLoader(host)
    created_tabs = []

    def eager_factory():
        created_tabs.append("eager")
        return QWidget()

    def lazy_factory():
        created_tabs.append("lazy")
        return QWidget()

    loader.register_tab("eager", eager_factory, eager_load=True)
    loader.register_tab("lazy", lazy_factory, eager_load=False)

    assert loader.is_loaded("eager") is True
    assert loader.is_loaded("lazy") is False
    assert created_tabs == ["eager"]
    assert loader.get_placeholder("lazy") is not None

    lazy_tab = loader.get_tab("lazy")

    assert isinstance(lazy_tab, QWidget)
    assert loader.is_loaded("lazy") is True
    assert created_tabs == ["eager", "lazy"]


def test_startup_profiler_parse_args_defaults(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["startup_profiler.py"])

    module = _fresh_import("tools.startup_profiler")
    args = module._parse_args()

    assert args.event_loop_ms == 800
    assert args.no_show is False


def test_ensure_current_interface_loaded_uses_current_stacked_widget():
    class DummyStackedWidget:
        def __init__(self):
            self._current = object()

        def currentWidget(self):
            return self._current

    app = object.__new__(type("DummyApp", (), {}))
    app.stackedWidget = DummyStackedWidget()
    captured = {}

    def _ensure_interface_loaded(widget):
        captured["widget"] = widget
        return "loaded"

    app._ensure_interface_loaded = _ensure_interface_loaded

    result = _fresh_import(
        "src.core.HomeUnitCalculator"
    ).MeterCalculationApp._ensure_current_interface_loaded(app)

    assert result == "loaded"
    assert captured["widget"] is app.stackedWidget.currentWidget()


def test_prepare_initial_interface_for_show_mounts_dashboard_shell_immediately():
    captured = []

    dashboard_placeholder = QWidget()
    app = object.__new__(type("DummyApp", (), {}))
    app._tab_interfaces = {"dashboard": dashboard_placeholder}

    def _mount_lazy_tab(tab_key, interface_widget):
        captured.append((tab_key, interface_widget))
        interface_widget._hmc_loaded_widget = QWidget()

    app._mount_lazy_tab = _mount_lazy_tab

    result = _fresh_import(
        "src.core.HomeUnitCalculator"
    ).MeterCalculationApp._prepare_initial_interface_for_show(app)

    assert captured == [("dashboard", dashboard_placeholder)]
    assert hasattr(dashboard_placeholder, "_hmc_loaded_widget")


def test_dashboard_tab_constructs_with_deferred_post_init_work(qapp):
    from src.ui.tabs.dashboard_tab import DashboardTab

    class DummyDbManager:
        db_name = ":memory:"

        def get_cached_years(self, source="supabase"):
            return []

    class DummyMainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.db_manager = DummyDbManager()
            self.supabase_manager = None

    main_window = DummyMainWindow()
    dashboard = DashboardTab(main_window)

    assert dashboard._post_init_scheduled is True
    assert dashboard._rate_chart_container is not None
    assert dashboard._elec_chart_container is not None
    assert dashboard._owner_room_chart_container is not None


@pytest.fixture
def dark_style_cards(qapp):
    from qfluentwidgets import CardWidget, SimpleCardWidget, ElevatedCardWidget
    from src.core.HomeUnitCalculator import MeterCalculationApp

    card_types = (CardWidget, SimpleCardWidget, ElevatedCardWidget)
    attributes = (
        "_normalBackgroundColor", "_hoverBackgroundColor", "_pressedBackgroundColor",
        "enterEvent", "leaveEvent", "_original_enterEvent", "_original_leaveEvent",
        "__hmc_dark_patched__",
    )
    missing = object()
    original = {
        cls: {name: cls.__dict__.get(name, missing) for name in attributes}
        for cls in card_types
    }
    handlers = {cls: (cls.enterEvent, cls.leaveEvent) for cls in card_types}
    try:
        for cls in card_types:
            if "__hmc_dark_patched__" in cls.__dict__:
                delattr(cls, "__hmc_dark_patched__")
        MeterCalculationApp._patch_cardwidget_dark_style(None)
        MeterCalculationApp._patch_cardwidget_dark_style(None)
        yield card_types, handlers
    finally:
        for cls, values in original.items():
            for name, value in values.items():
                if value is missing:
                    if name in cls.__dict__:
                        delattr(cls, name)
                else:
                    setattr(cls, name, value)


@pytest.mark.parametrize("card_index", range(3))
def test_card_dark_style_preserves_native_hover(dark_style_cards, card_index):
    card_types, handlers = dark_style_cards
    cls = card_types[card_index]
    card = cls()
    try:
        for _ in range(3):
            card.enterEvent(QEvent(QEvent.Enter))
            assert card.isHover is True
            card.leaveEvent(QEvent(QEvent.Leave))
            assert card.isHover is False
        assert (cls.enterEvent, cls.leaveEvent) == handlers[cls]
        assert not hasattr(card, "_hover_animation")
    finally:
        card.deleteLater()


@pytest.mark.parametrize("module_name,class_name", (
    ("src.ui.tabs.main_tab", "StaticRoomCard"),
    ("src.ui.tabs.rental_info_tab", "StaticHeaderCardWidget"),
    ("src.ui.tabs.rental_info_tab", "StaticCardWidget"),
))
def test_card_dark_style_static_containers_keep_child_controls(
    dark_style_cards, module_name, class_name,
):
    from PyQt5.QtCore import Qt
    from PyQt5.QtTest import QTest
    from PyQt5.QtWidgets import QPushButton

    cls = getattr(importlib.import_module(module_name), class_name)
    card = cls()
    button = QPushButton("Action", card)
    clicks = []
    button.clicked.connect(lambda: clicks.append(True))
    try:
        normal = card.backgroundColor.getRgb()
        for _ in range(3):
            QApplication.sendEvent(card, QEvent(QEvent.Enter))
            assert card.isHover is False
            assert card.backgroundColor.getRgb() == normal
            QTest.mouseClick(button, Qt.LeftButton)
            QApplication.sendEvent(card, QEvent(QEvent.Leave))
            assert card.isHover is False
        assert clicks == [True, True, True]
    finally:
        card.deleteLater()


def test_card_dark_style_keeps_existing_palette(dark_style_cards):
    card_types, _ = dark_style_cards
    cases = (
        ("", (43, 43, 43, 255), (54, 54, 54, 255), (37, 37, 37, 255)),
        ("billing_meter_container", (43, 43, 43, 255), (43, 43, 43, 255), (37, 37, 37, 255)),
        ("billing_period_box", (255, 255, 255, 72), (255, 255, 255, 72), (255, 255, 255, 72)),
        ("reading_pairs_box", (255, 255, 255, 72), (255, 255, 255, 72), (255, 255, 255, 72)),
        ("additional_amount_box", (255, 255, 255, 72), (255, 255, 255, 72), (255, 255, 255, 72)),
    )
    for cls in card_types:
        card = cls()
        try:
            for name, normal, hover, pressed in cases:
                card.setObjectName(name)
                assert card._normalBackgroundColor().getRgb() == normal
                assert card._hoverBackgroundColor().getRgb() == hover
                assert card._pressedBackgroundColor().getRgb() == pressed
        finally:
            card.deleteLater()


@pytest.fixture
def dashboard_bar_chart(qapp):
    from types import SimpleNamespace
    from PyQt5.QtCore import Qt
    from src.ui.tabs.dashboard_tab import DashboardTab

    charts = pytest.importorskip("PyQt5.QtChart", exc_type=ImportError)
    chart = charts.QChart()
    view = charts.QChartView(chart)
    axis_x = charts.QBarCategoryAxis()
    axis_x.append([str(i) for i in range(12)])
    axis_y = charts.QValueAxis()
    chart.addAxis(axis_x, Qt.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignLeft)
    dashboard = SimpleNamespace(
        _on_bar_hovered=lambda *args: DashboardTab._on_bar_hovered(None, *args),
    )

    def render(grouped, tooltips):
        values = list(range(1, 13))
        method = DashboardTab._apply_qt_bar_chart
        if grouped:
            method = DashboardTab._apply_qt_grouped_bar_chart
            values = {"Room A": values, "Room B": list(range(13, 25))}
        method(dashboard, view, axis_x, axis_y, "_test_series", values, tooltips)
        return dashboard._test_series[0].barSets()

    try:
        yield view, render
    finally:
        view.deleteLater()
        qapp.sendPostedEvents(view, QEvent.DeferredDelete)


@pytest.mark.parametrize("grouped", (False, True))
@pytest.mark.parametrize("tooltips", (
    [f"Month {i + 1}" for i in range(12)],
    [],
    ["January", "", "March"],
))
def test_dashboard_bar_hover_signal_order(dashboard_bar_chart, monkeypatch, grouped, tooltips):
    from unittest.mock import Mock
    from src.ui.tabs import dashboard_tab

    view, render = dashboard_bar_chart
    show, hide = Mock(), Mock()
    monkeypatch.setattr(dashboard_tab.QToolTip, "showText", show)
    monkeypatch.setattr(dashboard_tab.QToolTip, "hideText", hide)
    for bar_set in render(grouped, tooltips):
        assert bar_set.hovered.signal.endswith("hovered(bool,int)")
        for index in range(12):
            show.reset_mock()
            hide.reset_mock()
            bar_set.hovered.emit(True, index)
            hide.assert_not_called()
            text = tooltips[index] if index < len(tooltips) else ""
            if text:
                show.assert_called_once()
                assert show.call_args.args[1:] == (text, view)
            else:
                show.assert_not_called()
            show.reset_mock()
            bar_set.hovered.emit(False, index)
            hide.assert_called_once_with()
            show.assert_not_called()


@pytest.mark.parametrize("grouped", (False, True))
def test_dashboard_bar_hover_uses_rebuilt_tooltips(dashboard_bar_chart, monkeypatch, grouped):
    from unittest.mock import Mock
    from src.ui.tabs import dashboard_tab

    view, render = dashboard_bar_chart
    show = Mock()
    monkeypatch.setattr(dashboard_tab.QToolTip, "showText", show)
    render(grouped, ["Old"] * 12)
    updated = render(grouped, [f"New {i}" for i in range(12)])
    assert len(view.chart().series()) == 1
    for bar_set in updated:
        show.reset_mock()
        bar_set.hovered.emit(True, 11)
        show.assert_called_once()
        assert show.call_args.args[1:] == ("New 11", view)
