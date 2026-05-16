import time
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QEvent, QMargins
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
    QLinearGradient,
    QPainterPath,
)
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSizePolicy,
    QToolTip,
    QFrame,
    QApplication,
    QGraphicsDropShadowEffect,
)
from qfluentwidgets import (
    CardWidget,
    ComboBox,
    FluentIcon,
    PushButton,
    TitleLabel,
    BodyLabel,
    CaptionLabel,
    IconWidget,
    isDarkTheme,
    PrimaryPushButton,
    InfoBar,
    InfoBarPosition,
)
from src.ui.custom_widgets import (
    AutoScrollArea,
    SummaryKpiCard,
    AnimatedNumberLabel,
    ShimmerPlaceholder,
    EmptyStateWidget,
    SimpleBarChartWidget,
)


MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


class StaticCardWidget(CardWidget):
    def enterEvent(self, event):
        return

    def leaveEvent(self, event):
        return

    def event(self, e):
        if e.type() in (QEvent.HoverEnter, QEvent.HoverMove, QEvent.HoverLeave):
            return True
        return super().event(e)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    s = str(hex_color or "").strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    if len(s) != 6:
        return 0, 120, 212
    try:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    except Exception:
        return 0, 120, 212


class DashboardTheme:
    """Centralized theme constants and style helpers for the dashboard."""

    # Primary colors
    PRIMARY = "#0078D4"
    PRIMARY_HOVER = "#1084d8"
    PRIMARY_PRESSED = "#005a9e"

    # Semantic accent colors
    CYAN_CURRENT = "#49C6FF"
    GREEN_POSITIVE = "#9FE29D"
    PURPLE_SECONDARY = "#B97AFF"
    ORANGE_WARNING = "#FFB86B"
    RED_NEGATIVE = "#FF6B6B"

    # Text colors
    TEXT_PRIMARY = "#FFFFFF"
    TEXT_SECONDARY = "#B4B4B4"
    TEXT_MUTED = "#A0A0A0"

    # Card styling
    CARD_BG = "#2b2b2b"
    CARD_BORDER = "rgba(255,255,255,0.06)"
    CARD_RADIUS = 16
    CARD_SHADOW_BLUR = 20
    CARD_SHADOW_COLOR = QColor(0, 0, 0, 80)

    # Chart colors
    CHART_BG = QColor(39, 39, 39)
    CHART_GRID = QColor(80, 80, 80)
    CHART_AXIS_LABEL = QColor(220, 220, 220)

    # Typography
    HEADER_FONT_SIZE = 20
    BODY_VALUE_FONT_SIZE = 22
    CAPTION_FONT_SIZE = 12

    # Responsive
    RESPONSIVE_BREAKPOINT = 900

    # KPI themes: title -> (color_hex, FluentIcon)
    KPI_THEMES = {
        "Current Month": (CYAN_CURRENT, FluentIcon.CALENDAR),
        "Previous Month": (GREEN_POSITIVE, FluentIcon.HISTORY),
        "Highest Month": (PURPLE_SECONDARY, FluentIcon.UP),
        "Lowest Month": (ORANGE_WARNING, FluentIcon.DOWN),
    }

    # Summary KPI themes
    SUMMARY_KPI_THEMES = {
        "Total Bill": (PRIMARY, FluentIcon.SHOPPING_CART),
        "Electricity Bill": (CYAN_CURRENT, FluentIcon.SPEED_HIGH),
        "Per-Unit Cost": (PURPLE_SECONDARY, FluentIcon.SPEED_HIGH),
        "Total Units": (GREEN_POSITIVE, FluentIcon.PEOPLE),
        "Owner Electricity Bill": (ORANGE_WARNING, FluentIcon.HOME),
        "Tenant's Electricity and Water Bill": (CYAN_CURRENT, FluentIcon.PEOPLE),
        "Gas bill (Added amount)": (RED_NEGATIVE, FluentIcon.ADD),
        "Active Rooms": (GREEN_POSITIVE, FluentIcon.HOME),
    }

    @staticmethod
    def card_style(object_name: str) -> str:
        return f"""
            #{object_name} {{
                background-color: rgba(43, 43, 43, 220);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: {DashboardTheme.CARD_RADIUS}px;
            }}
        """

    @staticmethod
    def header_style() -> str:
        return f"""
            font-size: {DashboardTheme.HEADER_FONT_SIZE}px;
            font-weight: 700;
            color: {DashboardTheme.PRIMARY};
        """

    @staticmethod
    def refresh_btn_style() -> str:
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DashboardTheme.PRIMARY}, stop:1 {DashboardTheme.PRIMARY_PRESSED});
                border: 2px solid {DashboardTheme.PRIMARY};
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 14px;
                padding: 8px 16px 8px 36px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DashboardTheme.PRIMARY_HOVER}, stop:1 {DashboardTheme.PRIMARY});
            }}
        """

    @staticmethod
    def apply_card_shadow(widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(DashboardTheme.CARD_SHADOW_BLUR)
        shadow.setOffset(0, 4)
        shadow.setColor(DashboardTheme.CARD_SHADOW_COLOR)
        widget.setGraphicsEffect(shadow)


class InfoResultCard(QWidget):
    def __init__(self, title: str, icon, theme_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("infoResultCard")
        self.setAttribute(Qt.WA_Hover, False)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        r, g, b = _hex_to_rgb(theme_color)
        self.setFixedHeight(90)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("infoResultCardPanel")
        panel.setAttribute(Qt.WA_StyledBackground, True)
        panel.setAutoFillBackground(True)
        panel.setStyleSheet(
            f"""
            QFrame#infoResultCardPanel {{
                background-color: rgba({r}, {g}, {b}, 42);
                border: 1px solid rgba({r}, {g}, {b}, 140);
                border-radius: 12px;
            }}
            """
        )
        outer.addWidget(panel, 1)

        lay = QHBoxLayout(panel)
        lay.setContentsMargins(24, 6, 24, 6)
        lay.setSpacing(10)

        icon_wrap = QFrame()
        icon_wrap.setFixedSize(40, 40)
        icon_wrap.setStyleSheet(
            f"background-color: rgba({r}, {g}, {b}, 26); border-radius: 12px; border: 1px solid rgba({r}, {g}, {b}, 150);"
        )
        icon_lay = QVBoxLayout(icon_wrap)
        icon_lay.setContentsMargins(4, 4, 4, 4)
        icon_lay.setSpacing(0)
        iw = IconWidget(icon)
        iw.setFixedSize(30, 30)
        icon_lay.addWidget(iw, 1, Qt.AlignCenter)
        lay.addWidget(icon_wrap, 0, Qt.AlignVCenter)

        t = CaptionLabel(title)
        t.setStyleSheet(
            "color: #FFFFFF; font-weight: bold; font-size: 13px; letter-spacing: 0.5px;"
        )
        lay.addWidget(t, 1, Qt.AlignVCenter)

        v = BodyLabel("0")
        v.setStyleSheet(
            f"color: rgb({r}, {g}, {b}); font-size: 44px; font-weight: 700;"
        )
        v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(v, 0, Qt.AlignRight | Qt.AlignVCenter)

        self._kpi_value_label = v


class SimpleLineChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels = MONTHS
        self._values = [0.0] * 12
        self._tooltips = [""] * 12
        self._max_value = 0.0
        self._points = []
        self._hover_index = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)
        self.setMouseTracking(True)

    def set_data(
        self, labels: list[str], values: list[float], tooltips: list[str] | None = None
    ):
        self._labels = labels[:]
        self._values = values[:]
        if tooltips is None:
            self._tooltips = [""] * len(self._values)
        else:
            self._tooltips = tooltips[:]
        self._max_value = max(self._values) if self._values else 0.0
        self.update()

    def _hit_test(self, pos):
        for i, p in enumerate(self._points):
            if (p - pos).manhattanLength() <= 12:
                return i
        return None

    def mouseMoveEvent(self, event):
        idx = self._hit_test(event.pos())
        if idx != self._hover_index:
            self._hover_index = idx
            if idx is not None and idx < len(self._tooltips) and self._tooltips[idx]:
                QToolTip.showText(QCursor.pos(), self._tooltips[idx], self)
            else:
                QToolTip.hideText()
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._hover_index = None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(14, 12, -12, -12)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        dark = isDarkTheme()
        bg = QColor(39, 39, 39) if dark else QColor(250, 250, 250)
        grid = QColor(80, 80, 80) if dark else QColor(210, 210, 210)
        bar = QColor(0, 120, 212) if dark else QColor(0, 120, 212)
        bar_hi = QColor(0, 120, 212) if dark else QColor(0, 95, 180)
        text = QColor(230, 230, 230) if dark else QColor(30, 30, 30)

        painter.fillRect(rect, bg)

        left_pad = 88
        bottom_pad = 36
        top_pad = 4
        plot = rect.adjusted(left_pad, top_pad, -8, -bottom_pad)

        if plot.width() <= 0 or plot.height() <= 0:
            return

        painter.setPen(QPen(grid, 1))
        for i in range(5):
            y = plot.top() + int(i * plot.height() / 4)
            painter.drawLine(plot.left(), y, plot.right(), y)

        values = self._values or []
        n = len(values)
        if n <= 0:
            painter.setPen(text)
            painter.drawText(plot, Qt.AlignCenter, "No data")
            return

        max_v = self._max_value or 1.0
        if max_v <= 0:
            max_v = 1.0
        min_v = None
        for v in values:
            try:
                fv = float(v)
            except Exception:
                continue
            min_v = fv if min_v is None else min(min_v, fv)
        base_v = 0.0
        if min_v is not None and min_v > 0 and min_v > max_v * 0.25:
            base_v = max(0.0, min_v * 0.92)
        span = max(1e-6, max_v - base_v)

        step_x = plot.width() / max(1, n - 1)
        self._points = []
        for i, v in enumerate(values):
            x = plot.left() + (i * step_x)
            y = plot.bottom() - (((float(v) - base_v) / float(span)) * plot.height())
            self._points.append(QPoint(int(x), int(y)))

        fill_path = QPainterPath()
        fill_path.moveTo(self._points[0])
        for i in range(1, n):
            fill_path.lineTo(self._points[i])
        fill_path.lineTo(self._points[-1].x(), plot.bottom())
        fill_path.lineTo(self._points[0].x(), plot.bottom())
        fill_path.closeSubpath()

        grad = QLinearGradient(plot.left(), plot.top(), plot.left(), plot.bottom())
        grad.setColorAt(0.0, QColor(0, 120, 212, 90))
        grad.setColorAt(1.0, QColor(0, 120, 212, 0))
        painter.fillPath(fill_path, grad)

        line_pen = QPen(bar, 3)
        painter.setPen(QPen(QColor(140, 140, 140, 80), 1, Qt.DotLine))
        for p in self._points:
            painter.drawLine(p.x(), plot.bottom(), p.x(), p.y())

        painter.setPen(line_pen)
        for i in range(1, n):
            painter.drawLine(self._points[i - 1], self._points[i])

        for i, p in enumerate(self._points):
            painter.setBrush(QColor(73, 198, 255))
            painter.setPen(QPen(QColor(20, 20, 20), 2))
            painter.drawEllipse(p, 5, 5)
            if self._hover_index == i:
                painter.setBrush(QColor(73, 198, 255, 80))
                painter.setPen(QPen(QColor(73, 198, 255, 120), 2))
                painter.drawEllipse(p, 10, 10)

        painter.setPen(QPen(text, 1))
        fm = QFontMetrics(painter.font())
        label_step = 1
        try:
            sample_w = fm.horizontalAdvance("Sep")
            label_step = max(1, int((sample_w + 10) / max(1.0, step_x)) + 1)
        except Exception:
            label_step = 1
        for i, label in enumerate(self._labels[:n]):
            if i % label_step != 0:
                continue
            short = label[:3]
            x = plot.left() + i * step_x
            y = plot.bottom() + fm.ascent() + 10
            w = fm.horizontalAdvance(short)
            tx = int(x - int(w / 2))
            tx = max(plot.left() + 6, min(tx, plot.right() - w - 6))
            if i == 0:
                tx += 10
            if i == n - 1:
                tx -= 10
            painter.drawText(tx, y, short)

        painter.setPen(QPen(text, 1))
        for i in range(5):
            frac = 1.0 - (i / 4.0)
            val = base_v + frac * span
            y = plot.top() + int(i * plot.height() / 4)
            s = f"TK {val:,.0f}"
            w = fm.horizontalAdvance(s)
            painter.drawText(plot.left() - w - 8, y + int(fm.ascent() / 2), s)


class DashboardTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self._last_infobar_at = 0.0
        self._last_infobar_text = ""
        self.db_manager = getattr(self.main_window, "db_manager", None)
        self._db_path = (
            getattr(self.db_manager, "db_name", None) if self.db_manager else None
        )

        self._years_worker = None
        self._sync_worker = None
        self._owner_room_main_sync_worker = None
        self._room_sync_worker = None
        self._rentals_sync_worker = None
        self._chart_view = None
        self._chart_widget = None
        self._rate_chart_view = None
        self._rate_chart_widget = None
        self._rate_qtchart = None
        self._elec_chart_view = None
        self._elec_chart_widget = None
        self._elec_qtchart = None
        self._rate_series = None
        self._rate_axis_y = None
        self._rate_axis_x = None
        self._rate_values = [0.0] * 12
        self._rate_raw_values = [None] * 12
        self._rate_tooltips = [""] * 12
        self._elec_values = [0.0] * 12
        self._elec_raw_values = [None] * 12
        self._elec_tooltips = [""] * 12
        self._owner_room_chart_view = None
        self._owner_room_chart_widget = None
        self._owner_room_qtchart = None
        self._owner_room_bar_set = None
        self._owner_room_axis_y = None
        self._owner_room_axis_x = None
        self._owner_room_values = [0.0] * 12
        self._owner_room_raw_values = [None] * 12
        self._owner_room_tooltips = [""] * 12
        self._supabase_poll_tries = 0
        self._supabase_poll_timer = None
        self._years_fetched_from_supabase_this_session = False
        self._post_init_scheduled = False
        self._current_values = [0.0] * 12
        self._current_tooltips = [""] * 12

        self._build_ui()
        self._schedule_post_init_work()

    def _schedule_post_init_work(self):
        if self._post_init_scheduled:
            return

        self._post_init_scheduled = True
        QTimer.singleShot(0, self._run_post_init_work)

    def _run_post_init_work(self):
        self._configure_tooltips()
        self._initialize_deferred_chart_widgets()
        self._populate_years_from_cache()
        self._start_supabase_year_poll()

    def _initialize_deferred_chart_widgets(self):
        self._mount_deferred_chart_widget(
            container=self._rate_chart_container,
            attr_name="_rate_chart_widget",
            factory=self._create_rate_chart_widget,
            values=self._rate_values,
            tooltips=self._rate_tooltips,
        )
        self._mount_deferred_chart_widget(
            container=self._elec_chart_container,
            attr_name="_elec_chart_widget",
            factory=self._create_elec_chart_widget,
            values=self._elec_values,
            tooltips=self._elec_tooltips,
        )
        self._mount_deferred_chart_widget(
            container=self._owner_room_chart_container,
            attr_name="_owner_room_chart_widget",
            factory=self._create_owner_room_chart_widget,
            values=self._owner_room_values,
            tooltips=self._owner_room_tooltips,
        )

    def _mount_deferred_chart_widget(
        self,
        container,
        attr_name: str,
        factory,
        values: list[float],
        tooltips: list[str],
    ):
        chart_widget = factory()
        layout = container.layout()
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        layout.addWidget(chart_widget)
        setattr(self, attr_name, chart_widget)

        if isinstance(chart_widget, SimpleLineChartWidget):
            chart_widget.set_data(MONTHS, values, tooltips=tooltips)
        elif isinstance(chart_widget, SimpleBarChartWidget):
            chart_widget.set_data(MONTHS, values, tooltips=tooltips)

    def _create_chart_placeholder(self, min_height: int):
        placeholder = QFrame(self)
        placeholder.setMinimumHeight(min_height)
        placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        placeholder.setStyleSheet(
            "background-color: #2b2b2b; border: 1px dashed #3d3d3d; border-radius: 10px;"
        )
        return placeholder

    def _configure_tooltips(self):
        QToolTip.setFont(QFont("Segoe UI", 12))

    def _notify(self, level: str, title: str, content: str, duration: int = 4000):
        c = (content or "").strip()
        if not c:
            return
        now = time.monotonic()
        if c == self._last_infobar_text and (now - self._last_infobar_at) < 2.0:
            return
        self._last_infobar_text = c
        self._last_infobar_at = now

        parent = self.main_window if self.main_window is not None else self
        fn = InfoBar.info
        if level == "success":
            fn = InfoBar.success
        elif level == "warning":
            fn = InfoBar.warning
        elif level == "error":
            fn = InfoBar.error

        fn(
            title=title,
            content=c,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=duration,
            parent=parent,
        )

    def _start_supabase_year_poll(self):
        if self._supabase_poll_timer is not None:
            return
        self._supabase_poll_timer = QTimer(self)
        self._supabase_poll_timer.setInterval(1200)
        self._supabase_poll_timer.timeout.connect(self._poll_supabase_years)
        self._supabase_poll_timer.start()

    def _poll_supabase_years(self):
        if (
            self._years_fetched_from_supabase_this_session
            and self.year_combo.isEnabled()
            and self.year_combo.count() > 0
        ):
            self._supabase_poll_timer.stop()
            return

        self._supabase_poll_tries += 1
        supabase_manager = getattr(self.main_window, "supabase_manager", None)

        if supabase_manager and supabase_manager.is_client_initialized():
            self._refresh_years_from_supabase_async()
        else:
            if self._supabase_poll_tries == 3:
                self._set_status(
                    "Supabase not configured. Set it in Supabase Config tab, then return here."
                )

        if self._supabase_poll_tries >= 25:
            self._supabase_poll_timer.stop()

    # ------------------------------------------------------------------
    # 2A / 2B: UI building helpers
    # ------------------------------------------------------------------

    def _build_header_section(self, parent_layout):
        """Add the page title to *parent_layout*."""
        # Title
        title = TitleLabel("Recent Month Overview")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #FFFFFF;
            letter-spacing: 0.5px;
            margin: 0px 0px 12px 0px;
        """)
        parent_layout.addWidget(title)

    def _build_chart_card(self, page_layout, config):
        """Factory that builds one of the four dashboard chart cards.

        *config* keys
        -------------
        Required: ``object_name``, ``icon``, ``title``, ``hint``,
        ``year_combo_attr``, ``year_changed_slot``, ``refresh_btn_attr``,
        ``refresh_slot``, ``kpi_titles``, ``kpi_attr_prefix``,
        ``meta_label_attr``.

        Optional: ``kpi_attr_names`` (default ``["current","prev","high","low"]``),
        ``chart_container_attr`` + ``chart_min_height`` (deferred chart),
        ``direct_chart_attr`` + ``direct_chart_factory`` (immediate chart),
        ``status_label_attr``, ``extra_header_widgets`` (list of QWidget),
        ``refresh_tooltip``.
        """
        refresh_css = """
            PrimaryPushButton {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078D4, stop:1 #005a9e);
                border: 2px solid #0078D4;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                qproperty-iconSize: 20px 20px;
                padding: 8px 16px 8px 36px;
                text-align: center;
                margin: 0px;
            }
            PrimaryPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1084d8, stop:1 #106ebe);
                border-color: #1084d8;
            }
            PrimaryPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #005a9e, stop:1 #004578);
                border-color: #005a9e;
            }
        """

        card = StaticCardWidget(self)
        card.setObjectName(config["object_name"])
        card.setStyleSheet(f"""
            CardWidget#{config['object_name']} {{
                border-radius: 16px;
                background-color: rgba(43, 43, 43, 220);
                border: 1px solid rgba(255, 255, 255, 0.06);
            }}
        """)
        # Apply shadow effect
        DashboardTheme.apply_card_shadow(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # -- header row --
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # Icon with accent background
        icon_container = QWidget()
        icon_container.setFixedSize(32, 32)
        icon_container.setStyleSheet("""
            background: rgba(0, 120, 212, 15);
            border-radius: 8px;
            border: 1px solid rgba(0, 120, 212, 25);
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(6, 6, 6, 6)
        icon = IconWidget(config["icon"])
        icon.setFixedSize(20, 20)
        icon_layout.addWidget(icon, 0, Qt.AlignCenter)
        top_row.addWidget(icon_container)

        header = TitleLabel(config["title"])
        header.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #FFFFFF;
        """)
        top_row.addWidget(header)

        hint = CaptionLabel(config["hint"])
        hint.setTextColor(QColor(120, 120, 120))
        hint.setStyleSheet("font-size: 11px;")
        top_row.addWidget(hint)
        top_row.addStretch(1)

        # year combo
        year_combo = ComboBox()
        year_combo.setMinimumWidth(110)
        year_combo.currentIndexChanged.connect(config["year_changed_slot"])
        year_combo.setToolTip("Years are fetched from Supabase and cached locally")
        setattr(self, config["year_combo_attr"], year_combo)
        top_row.addWidget(year_combo)

        # optional extra header widgets (e.g. scope / room combos)
        for widget in config.get("extra_header_widgets") or []:
            top_row.addWidget(widget)

        # refresh button
        refresh_btn = PrimaryPushButton("  Refresh")
        refresh_btn.setIcon(FluentIcon.SYNC.icon(color=QColor(255, 255, 255)))
        refresh_btn.setIconSize(QSize(14, 14))
        refresh_btn.setFixedHeight(32)
        refresh_btn.setMinimumWidth(100)
        refresh_btn.setStyleSheet("""
            PrimaryPushButton {
                color: white;
                background: rgba(0, 120, 212, 20);
                border: 1px solid rgba(0, 120, 212, 40);
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
                padding-left: 24px;
                padding-right: 12px;
                padding-top: 6px;
                padding-bottom: 6px;
            }
            PrimaryPushButton:hover {
                background: rgba(0, 120, 212, 35);
                border-color: rgba(0, 120, 212, 60);
            }
        """)
        refresh_btn.clicked.connect(config["refresh_slot"])
        refresh_btn.setToolTip(
            config.get("refresh_tooltip", "Sync from Supabase and update local cache")
        )
        setattr(self, config["refresh_btn_attr"], refresh_btn)
        top_row.addWidget(refresh_btn)

        card_layout.addLayout(top_row)

        # -- divider --
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.06); border: none; margin: 4px 0px;"
        )
        card_layout.addWidget(divider)

        # -- meta row --
        meta_row = QHBoxLayout()
        meta_label = CaptionLabel("")
        meta_label.setTextColor(
            QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110)
        )
        setattr(self, config["meta_label_attr"], meta_label)
        meta_row.addWidget(meta_label)
        meta_row.addStretch(1)
        card_layout.addLayout(meta_row)

        # -- optional status label --
        status_attr = config.get("status_label_attr")
        if status_attr:
            status_label = BodyLabel("")
            status_label.setTextColor(QColor(200, 200, 200))
            status_label.setVisible(False)
            status_label.setFixedHeight(0)
            setattr(self, status_attr, status_label)
            card_layout.addWidget(status_label)

        # -- chart area --
        kpi_attr_prefix = config["kpi_attr_prefix"]
        kpi_attr_names = config.get(
            "kpi_attr_names", ["current", "prev", "high", "low"]
        )

        # chart area: immediate or deferred (placed first so it stretches)
        if "direct_chart_factory" in config:
            chart_widget = config["direct_chart_factory"]()
            setattr(self, config["direct_chart_attr"], chart_widget)
            card_layout.addWidget(chart_widget, 1)
        else:
            container = QWidget(self)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            container.setLayout(QVBoxLayout())
            container.layout().setContentsMargins(0, 0, 0, 0)
            container.layout().addWidget(
                self._create_chart_placeholder(config.get("chart_min_height", 320))
            )
            setattr(self, config["chart_container_attr"], container)
            card_layout.addWidget(container, 1)

        # Store KPI references for tooltip building (no visual cards)
        for kpi_title, attr_name in zip(config["kpi_titles"], kpi_attr_names):
            setattr(self, f"{kpi_attr_prefix}_{attr_name}", None)

        return card

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = AutoScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        root.addWidget(scroll, 1)

        page = QWidget()
        scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(24, 20, 24, 20)
        page_layout.setSpacing(20)

        self._build_header_section(page_layout)

        # -- Offline banner (hidden by default) --
        self._offline_banner = QFrame()
        self._offline_banner.setObjectName("offlineBanner")
        self._offline_banner.setStyleSheet("""
            #offlineBanner {
                background: rgba(255, 184, 107, 15);
                border: 1px solid rgba(255, 184, 107, 40);
                border-radius: 8px;
            }
        """)
        banner_layout = QHBoxLayout(self._offline_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(8)
        banner_icon = IconWidget(FluentIcon.CLOUD)
        banner_icon.setFixedSize(20, 20)
        banner_layout.addWidget(banner_icon)
        banner_text = CaptionLabel("Supabase not configured. Showing cached data.")
        banner_text.setTextColor(QColor(255, 184, 107))
        banner_layout.addWidget(banner_text, 1)
        banner_close = PushButton("✕")
        banner_close.setFixedSize(24, 24)
        banner_close.setStyleSheet("border: none; color: #FFB86B; font-size: 14px;")
        banner_close.clicked.connect(lambda: self._offline_banner.hide())
        banner_layout.addWidget(banner_close)
        self._offline_banner.hide()
        page_layout.addWidget(self._offline_banner)

        # -- Summary KPI section --
        kpi_section = QWidget()
        kpi_section_layout = QVBoxLayout(kpi_section)
        kpi_section_layout.setContentsMargins(0, 0, 0, 0)
        kpi_section_layout.setSpacing(8)

        # KPI section title
        kpi_title = CaptionLabel("📊 Recent Month Overview")
        kpi_title.setTextColor(QColor(140, 140, 140))
        kpi_title.setStyleSheet("font-size: 12px; font-weight: 600; margin-bottom: 4px;")
        kpi_section_layout.addWidget(kpi_title)

        # Summary KPI grid (2 rows x 4 columns)
        self._summary_kpi_container = QWidget()
        summary_grid = QGridLayout(self._summary_kpi_container)
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setSpacing(12)

        # Row 1: Main financial metrics (recent month)
        self._summary_total_bill = self._build_summary_kpi_card("Total Bill")
        summary_grid.addWidget(self._summary_total_bill, 0, 0)
        self._summary_elec_bill = self._build_summary_kpi_card("Electricity Bill")
        summary_grid.addWidget(self._summary_elec_bill, 0, 1)
        self._summary_rate = self._build_summary_kpi_card("Per-Unit Cost")
        summary_grid.addWidget(self._summary_rate, 0, 2)
        self._summary_units = self._build_summary_kpi_card("Total Units")
        summary_grid.addWidget(self._summary_units, 0, 3)

        # Row 2: Additional metrics (recent month)
        self._summary_owner_bill = self._build_summary_kpi_card("Owner Electricity Bill")
        summary_grid.addWidget(self._summary_owner_bill, 1, 0)
        self._summary_tenant_bill = self._build_summary_kpi_card("Tenant's Electricity and Water Bill")
        summary_grid.addWidget(self._summary_tenant_bill, 1, 1)
        self._summary_gas_bill = self._build_summary_kpi_card("Gas bill (Added amount)")
        summary_grid.addWidget(self._summary_gas_bill, 1, 2)
        self._summary_rooms = self._build_summary_kpi_card("Active Rooms")
        summary_grid.addWidget(self._summary_rooms, 1, 3)

        kpi_section_layout.addWidget(self._summary_kpi_container)
        page_layout.addWidget(kpi_section)

        # -- Charts grid (2 rows x 2 columns) --
        self._charts_grid_container = QWidget()
        charts_grid = QGridLayout(self._charts_grid_container)
        charts_grid.setContentsMargins(0, 0, 0, 0)
        charts_grid.setSpacing(16)

        # (0,0) Total Bill Trend
        yearly_card = self._build_chart_card(page_layout, {
            "object_name": "yearlyBillCard",
            "icon": FluentIcon.SHOPPING_CART,
            "title": "Total Bill Trend",
            "hint": "",
            "year_combo_attr": "year_combo",
            "year_changed_slot": self._on_year_changed,
            "refresh_btn_attr": "refresh_btn",
            "refresh_slot": self._on_refresh_clicked,
            "kpi_titles": [],
            "kpi_attr_prefix": "kpi",
            "kpi_attr_names": ["total", "avg", "high", "low"],
            "direct_chart_attr": "_chart_widget",
            "direct_chart_factory": self._create_chart_widget,
            "meta_label_attr": "meta_label",
            "status_label_attr": "status_label",
        })
        charts_grid.addWidget(yearly_card, 0, 0)

        # (0,1) Total Electricity Bill Trend
        elec_card = self._build_chart_card(page_layout, {
            "object_name": "electricityBillCard",
            "icon": FluentIcon.SPEED_HIGH,
            "title": "Total Electricity Bill Trend",
            "hint": "",
            "year_combo_attr": "elec_year_combo",
            "year_changed_slot": self._on_elec_year_changed,
            "refresh_btn_attr": "elec_refresh_btn",
            "refresh_slot": self._on_refresh_clicked,
            "kpi_titles": [],
            "kpi_attr_prefix": "elec_kpi",
            "kpi_attr_names": ["current", "prev", "high", "low"],
            "chart_container_attr": "_elec_chart_container",
            "chart_min_height": 320,
            "meta_label_attr": "elec_meta_label",
        })
        charts_grid.addWidget(elec_card, 0, 1)

        # (1,0) Per Unit Cost Trend
        rate_card = self._build_chart_card(page_layout, {
            "object_name": "perUnitCostCard",
            "icon": FluentIcon.CALENDAR,
            "title": "Per Unit Cost Trend",
            "hint": "",
            "year_combo_attr": "rate_year_combo",
            "year_changed_slot": self._on_rate_year_changed,
            "refresh_btn_attr": "rate_refresh_btn",
            "refresh_slot": self._on_refresh_clicked,
            "kpi_titles": [],
            "kpi_attr_prefix": "rate_kpi",
            "kpi_attr_names": ["current", "prev", "high", "low"],
            "chart_container_attr": "_rate_chart_container",
            "chart_min_height": 320,
            "meta_label_attr": "rate_meta_label",
        })
        charts_grid.addWidget(rate_card, 1, 0)

        # (1,1) Owner / Room Bill Trend
        self.scope_combo = ComboBox()
        self.scope_combo.addItems(["Owner", "Room"])
        self.scope_combo.setCurrentIndex(0)
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        self.scope_combo.setToolTip("Switch between owner bill and a room bill")

        self.room_combo = ComboBox()
        self.room_combo.setMinimumWidth(140)
        self.room_combo.currentIndexChanged.connect(self._on_room_changed)
        self.room_combo.setEnabled(False)
        self.room_combo.setToolTip("Select a room to view its monthly bills")

        owner_room_card = self._build_chart_card(page_layout, {
            "object_name": "ownerRoomBillCard",
            "icon": FluentIcon.PEOPLE,
            "title": "Owner / Room Bill Trend",
            "hint": "",
            "year_combo_attr": "owner_room_year_combo",
            "year_changed_slot": self._on_owner_room_year_changed,
            "refresh_btn_attr": "owner_room_refresh_btn",
            "refresh_slot": self._on_owner_room_refresh_clicked,
            "refresh_tooltip": "Sync owner/room bills and tenant info from Supabase",
            "kpi_titles": [],
            "kpi_attr_prefix": "owner_kpi",
            "kpi_attr_names": ["total", "avg", "high", "low"],
            "chart_container_attr": "_owner_room_chart_container",
            "chart_min_height": 320,
            "meta_label_attr": "owner_room_meta_label",
            "status_label_attr": "owner_room_status_label",
            "extra_header_widgets": [self.scope_combo, self.room_combo],
        })
        charts_grid.addWidget(owner_room_card, 1, 1)

        page_layout.addWidget(self._charts_grid_container)
        page_layout.addStretch(1)

    # ------------------------------------------------------------------
    # 3A-D: Summary KPI and compact KPI builders
    # ------------------------------------------------------------------

    def _build_summary_kpi_card(self, title: str) -> SummaryKpiCard:
        """Create a summary-level KPI card using DashboardTheme.SUMMARY_KPI_THEMES."""
        color_hex, icon = DashboardTheme.SUMMARY_KPI_THEMES.get(
            title, (DashboardTheme.PRIMARY, FluentIcon.SHOPPING_CART)
        )
        card = SummaryKpiCard(title, icon, color_hex, parent=self)
        DashboardTheme.apply_card_shadow(card)
        return card

    def _build_compact_kpi_card(self, title: str) -> SummaryKpiCard:
        """Create a compact KPI card for use within chart cards (smaller font)."""
        color_hex, icon = DashboardTheme.KPI_THEMES.get(
            title, (DashboardTheme.PRIMARY, FluentIcon.SHOPPING_CART)
        )
        card = SummaryKpiCard(title, icon, color_hex, parent=self)
        card.setFixedHeight(70)
        # Override value label font to 16px for compact display
        card._kpi_value_label.setStyleSheet(
            f"color: {color_hex}; font-size: 16px; font-weight: 700;"
        )
        return card

    # ------------------------------------------------------------------
    # 3E: Responsive layout
    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        """Adapt grid layouts when window width crosses the responsive breakpoint."""
        super().resizeEvent(event)
        QTimer.singleShot(50, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        w = self.width()
        breakpoint = DashboardTheme.RESPONSIVE_BREAKPOINT
        if w < breakpoint:
            # Narrow: summary 4x2, charts 4x1
            self._rebuild_summary_grid(4, 2)
            self._rebuild_charts_grid(4, 1)
        else:
            # Wide: summary 2x4, charts 2x2
            self._rebuild_summary_grid(2, 4)
            self._rebuild_charts_grid(2, 2)

    def _rebuild_summary_grid(self, rows: int, cols: int):
        container = self._summary_kpi_container
        grid = container.layout()
        if grid is None:
            return
        # Collect all widgets currently in the grid
        widgets = []
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w is not None:
                widgets.append(w)
        # Re-add widgets in new grid positions
        for idx, w in enumerate(widgets):
            r = idx // cols
            c = idx % cols
            grid.addWidget(w, r, c)

    def _rebuild_charts_grid(self, rows: int, cols: int):
        container = self._charts_grid_container
        grid = container.layout()
        if grid is None:
            return
        widgets = []
        while grid.count():
            item = grid.takeAt(0)
            w = item.widget()
            if w is not None:
                widgets.append(w)
        for idx, w in enumerate(widgets):
            r = idx // cols
            c = idx % cols
            grid.addWidget(w, r, c)

    def _create_kpi_card(self, title: str):
        theme = {
            "Current Month": ("#49C6FF", FluentIcon.CALENDAR),
            "Previous Month": ("#9FE29D", FluentIcon.HISTORY),
            "Highest Month": ("#B97AFF", FluentIcon.UP),
            "Lowest Month": ("#FFB86B", FluentIcon.DOWN),
        }.get(title, ("#49C6FF", FluentIcon.SHOPPING_CART))

        color_hex, icon = theme
        qicon = icon.icon(color=QColor(color_hex))
        return InfoResultCard(title, qicon, color_hex, parent=self)

    def _create_chart_widget(self):
        try:
            from PyQt5.QtChart import (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )

            self._qtchart = (QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis)
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(470)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._chart_view = view
            self._init_qtchart()
            return view
        except Exception:
            self._qtchart = None
            return SimpleLineChartWidget(self)

    def _create_rate_chart_widget(self):
        try:
            from PyQt5.QtChart import (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )

            self._rate_qtchart = (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(320)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._rate_chart_view = view
            self._init_rate_qtchart()
            return view
        except Exception:
            self._rate_qtchart = None
            return SimpleLineChartWidget(self)

    def _init_qtchart_common(self, qtchart_classes, chart_view, label_format, axis_title=None):
        """Common chart initialisation shared by all four chart sections.

        Returns ``(chart, axis_x, axis_y)`` so callers can store the
        references under their own attribute names.
        """
        QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis = qtchart_classes

        chart = QChart()
        chart.legend().setVisible(False)
        chart.setBackgroundBrush(QColor(43, 43, 43))
        chart.setMargins(QMargins(20, 4, 12, 34))
        try:
            chart.layout().setContentsMargins(20, 4, 12, 34)
        except Exception:
            pass
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setAnimationDuration(550)

        axis_x = QCategoryAxis()
        for i, m in enumerate(MONTHS):
            axis_x.append(m[:3], i + 1)
        axis_x.setRange(0.0, 13.0)
        axis_x.setLabelsColor(QColor(220, 220, 220))
        axis_x.setGridLineVisible(False)
        axis_x.setLinePen(QPen(QColor(95, 95, 95), 1))
        axis_x.setLabelsAngle(-35)
        try:
            f = axis_x.labelsFont()
            f.setPointSize(9)
            axis_x.setLabelsFont(f)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor(220, 220, 220))
        axis_y.setGridLinePen(QPen(QColor(80, 80, 80), 1, Qt.DashLine))
        axis_y.setMinorGridLineColor(QColor(60, 60, 60))
        axis_y.setMin(0.0)
        axis_y.setMax(1.0)
        axis_y.setLabelFormat(label_format)
        axis_y.setTickCount(6)
        if axis_title:
            try:
                axis_y.setTitleText(axis_title)
                axis_y.setTitleBrush(QColor(220, 220, 220))
            except Exception:
                pass

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        chart_view.setChart(chart)
        return chart, axis_x, axis_y

    def _init_rate_qtchart(self):
        chart, axis_x, axis_y = self._init_qtchart_common(
            self._rate_qtchart, self._rate_chart_view, "TK %.2f"
        )
        self._rate_axis_y = axis_y
        self._rate_axis_x = axis_x
        self._rate_series = []

    def _create_elec_chart_widget(self):
        try:
            from PyQt5.QtChart import (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )

            self._elec_qtchart = (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(320)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._elec_chart_view = view
            self._init_elec_qtchart()
            return view
        except Exception:
            self._elec_qtchart = None
            return SimpleBarChartWidget(self)

    def _init_elec_qtchart(self):
        chart, axis_x, axis_y = self._init_qtchart_common(
            self._elec_qtchart,
            self._elec_chart_view,
            "TK %.0f",
            axis_title="Total Electricity Bill (TK)",
        )
        self._elec_axis_y = axis_y
        self._elec_axis_x = axis_x
        self._elec_series = []

    def _init_qtchart(self):
        chart, axis_x, axis_y = self._init_qtchart_common(
            self._qtchart, self._chart_view, "TK %.0f"
        )
        self._axis_y = axis_y
        self._chart_axis_x = axis_x
        self._line_series = []

    def _create_owner_room_chart_widget(self):
        try:
            from PyQt5.QtChart import (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )

            self._owner_room_qtchart = (
                QChartView,
                QChart,
                QLineSeries,
                QValueAxis,
                QCategoryAxis,
            )
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(470)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._owner_room_chart_view = view
            self._init_owner_room_qtchart()
            return view
        except Exception:
            self._owner_room_qtchart = None
            return SimpleBarChartWidget(self)

    def _init_owner_room_qtchart(self):
        chart, axis_x, axis_y = self._init_qtchart_common(
            self._owner_room_qtchart, self._owner_room_chart_view, "TK %.0f"
        )
        self._owner_room_axis_y = axis_y
        self._owner_room_axis_x = axis_x
        self._owner_room_line_series = []

    def _fmt_tk(self, v: float) -> str:
        try:
            return f"TK {float(v):,.0f}"
        except Exception:
            return "TK 0"

    def _fmt_rate(self, v: float | None) -> str:
        if v is None:
            return "—"
        try:
            return f"TK {float(v):,.2f}"
        except Exception:
            return "—"

    def _fmt_delta(self, v: float) -> str:
        try:
            sign = "+" if v >= 0 else "-"
            return f"Δ TK {sign}{abs(float(v)):,.0f}"
        except Exception:
            return "Δ TK 0"

    def _apply_qt_line_chart(
        self,
        chart_view,
        axis_x,
        axis_y,
        series_attr: str,
        raw_values: list,
        tooltips: list[str],
        line_color: QColor | None = None,
        fill_top_color: QColor | None = None,
        fill_bottom_color: QColor | None = None,
        fill_opacity: int = 90,
    ):
        chart = chart_view.chart()
        existing = getattr(self, series_attr, []) or []
        for s in existing:
            try:
                chart.removeSeries(s)
            except Exception:
                pass

        from PyQt5.QtChart import (
            QSplineSeries,
            QLineSeries,
            QAreaSeries,
            QScatterSeries,
        )
        from PyQt5.QtGui import QLinearGradient, QBrush

        segments: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        max_v = 0.0
        min_v = None
        for i in range(12):
            v = raw_values[i] if i < len(raw_values) else None
            if v is None:
                if current:
                    segments.append(current)
                    current = []
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            max_v = max(max_v, fv)
            min_v = fv if min_v is None else min(min_v, fv)
            current.append((float(i + 1), fv))
        if current:
            segments.append(current)

        base_y = 0.0
        if min_v is not None and min_v > 0:
            if min_v > max_v * 0.25:
                base_y = max(0.0, min_v * 0.92)

        new_series = []
        accent = line_color if line_color is not None else QColor("#0078D4")
        point_fill = accent
        point_border = QColor(20, 20, 20)
        stem_pen = QPen(QColor(140, 140, 140, 90), 1, Qt.DotLine)
        _fill_top = fill_top_color if fill_top_color is not None else QColor(accent.red(), accent.green(), accent.blue(), fill_opacity)
        _fill_bottom = fill_bottom_color if fill_bottom_color is not None else QColor(accent.red(), accent.green(), accent.blue(), 0)
        for seg in segments:
            upper = QSplineSeries()
            upper.setColor(accent)
            upper.setPen(QPen(accent, 3))
            for x, y in seg:
                upper.append(x, y)

            lower = QLineSeries()
            for x, _y in seg:
                lower.append(x, base_y)

            area = QAreaSeries(upper, lower)
            grad = QLinearGradient(0, 0, 0, 1)
            grad.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
            grad.setColorAt(0.0, _fill_top)
            grad.setColorAt(1.0, _fill_bottom)
            area.setBrush(QBrush(grad))
            area.setPen(QPen(QColor(0, 0, 0, 0), 0))

            stems = []
            for x, y in seg:
                st = QLineSeries()
                st.setPen(stem_pen)
                st.append(x, base_y)
                st.append(x, y)
                stems.append(st)

            points = QScatterSeries()
            points.setMarkerShape(QScatterSeries.MarkerShapeCircle)
            points.setMarkerSize(9.0)
            points.setBrush(point_fill)
            points.setPen(QPen(point_border, 2))
            for x, y in seg:
                points.append(x, y)

            upper.hovered.connect(
                lambda p, st, tv=tooltips, cv=chart_view: self._on_line_hovered(
                    p, st, tv, cv
                )
            )
            points.hovered.connect(
                lambda p, st, tv=tooltips, cv=chart_view: self._on_line_hovered(
                    p, st, tv, cv
                )
            )

            chart.addSeries(area)
            for st in stems:
                chart.addSeries(st)
            chart.addSeries(upper)
            chart.addSeries(points)

            for series in [area, *stems, upper, points]:
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)

            new_series.extend([area, *stems, upper, points])

        setattr(self, series_attr, new_series)
        axis_y.setMin(base_y)
        span = max(1.0, max_v - base_y)
        axis_y.setMax(base_y + span * 1.01)

    def _apply_qt_bar_chart(
        self,
        chart_view,
        axis_x,
        axis_y,
        series_attr: str,
        raw_values: list,
        tooltips: list[str],
        bar_color: QColor | None = None,
    ):
        chart = chart_view.chart()
        existing = getattr(self, series_attr, []) or []
        for s in existing:
            try:
                chart.removeSeries(s)
            except Exception:
                pass

        from PyQt5.QtChart import QBarSet, QBarSeries

        bar_set = QBarSet("")
        color = bar_color if bar_color is not None else QColor("#0078D4")
        bar_set.setColor(color)

        values = []
        for i in range(12):
            v = raw_values[i] if i < len(raw_values) else None
            fv = float(v or 0.0)
            values.append(fv)
            bar_set.append(fv)

        bar_series = QBarSeries()
        bar_series.append(bar_set)
        bar_series.setBarWidth(0.6)

        bar_set.hovered.connect(
            lambda idx, state, tv=tooltips, cv=chart_view: self._on_bar_hovered(
                idx, state, tv, cv
            )
        )

        chart.addSeries(bar_series)
        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)

        new_series = [bar_series]
        setattr(self, series_attr, new_series)

        max_v = max(values) if values else 0.0
        axis_y.setMin(0.0)
        axis_y.setMax(max(max_v * 1.1, 1.0))

    def _apply_qt_grouped_bar_chart(
        self,
        chart_view,
        axis_x,
        axis_y,
        series_attr: str,
        grouped_data: dict,
        tooltips: list[str],
    ):
        """Render a grouped bar chart.

        *grouped_data* maps a label (str) to a list of 12 monthly values.
        For a single series (e.g. Owner mode) the dict has one key.
        For multiple rooms it has one key per room.
        """
        chart = chart_view.chart()
        existing = getattr(self, series_attr, []) or []
        for s in existing:
            try:
                chart.removeSeries(s)
            except Exception:
                pass

        from PyQt5.QtChart import QBarSet, QBarSeries

        rotating_colors = [
            QColor(DashboardTheme.CYAN_CURRENT),
            QColor(DashboardTheme.PURPLE_SECONDARY),
            QColor(DashboardTheme.GREEN_POSITIVE),
            QColor(DashboardTheme.ORANGE_WARNING),
            QColor(DashboardTheme.RED_NEGATIVE),
            QColor(DashboardTheme.PRIMARY),
        ]

        bar_series = QBarSeries()
        max_v = 0.0
        bar_sets = []
        for idx, (label, values) in enumerate(grouped_data.items()):
            bar_set = QBarSet(str(label))
            color = rotating_colors[idx % len(rotating_colors)]
            bar_set.setColor(color)
            for i in range(12):
                v = values[i] if i < len(values) else 0.0
                fv = float(v or 0.0)
                bar_set.append(fv)
                max_v = max(max_v, fv)
            bar_series.append(bar_set)
            bar_sets.append(bar_set)

        bar_series.setBarWidth(0.6)

        chart.addSeries(bar_series)
        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)

        if len(grouped_data) > 1:
            chart.legend().setVisible(True)
            chart.legend().setLabelColor(QColor(220, 220, 220))
        else:
            chart.legend().setVisible(False)

        for bs in bar_sets:
            bs.hovered.connect(
                lambda idx, state, tv=tooltips, cv=chart_view: self._on_bar_hovered(
                    idx, state, tv, cv
                )
            )

        new_series = [bar_series]
        setattr(self, series_attr, new_series)

        axis_y.setMin(0.0)
        axis_y.setMax(max(max_v * 1.1, 1.0))

    def _on_bar_hovered(self, index: int, state: bool, tooltips: list[str], chart_view):
        if not state:
            QToolTip.hideText()
            return
        if 0 <= index < len(tooltips):
            text = tooltips[index]
            if text:
                QToolTip.showText(QCursor.pos(), text, chart_view)

    def _on_line_hovered(self, point, state: bool, tooltips: list[str], chart_view):
        if not state:
            QToolTip.hideText()
            return
        try:
            idx = int(round(float(point.x()))) - 1
        except Exception:
            return
        if 0 <= idx < len(tooltips):
            text = tooltips[idx]
            if text:
                QToolTip.showText(QCursor.pos(), text, chart_view)

    def _set_status(self, text: str):
        t = (text or "").strip()
        if not t:
            return
        low = t.lower()
        if low.startswith("syncing") or low.startswith("fetching") or low.endswith("…"):
            return
        level = "info"
        if "paused" in low:
            level = "warning"
        elif (
            "error" in low
            or low.startswith("api error")
            or low.startswith("authentication")
        ):
            level = "error"
        elif "disconnected" in low or "timeout" in low:
            level = "warning"
        self._notify(level, "Dashboard", t, duration=4500)

    def _begin_global_update_activity(self, key: str, message: str):
        coordinator = getattr(self.main_window, "update_coordinator", None)
        if coordinator is not None:
            coordinator.begin_activity(key, message)

    def _end_global_update_activity(self, key: str):
        coordinator = getattr(self.main_window, "update_coordinator", None)
        if coordinator is not None:
            coordinator.end_activity(key)

    # ------------------------------------------------------------------
    # 2C: Consolidated year-combo management
    # ------------------------------------------------------------------

    def _all_year_combos(self):
        """Return list of all year combo widgets that currently exist."""
        combos = [self.year_combo]
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            combos.append(self.rate_year_combo)
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            combos.append(self.elec_year_combo)
        combos.append(self.owner_room_year_combo)
        return combos

    def _sync_all_year_combos(self, years: list[int]):
        """Update every year-combo with *years* (sorted descending expected)."""
        current_year_str = str(datetime.now().year)

        # Block & clear
        for combo in self._all_year_combos():
            combo.blockSignals(True)
            combo.clear()

        if years:
            for y in years:
                for combo in self._all_year_combos():
                    combo.addItem(str(y))
            for combo in self._all_year_combos():
                combo.setEnabled(True)
            for combo in self._all_year_combos():
                if combo.findText(current_year_str) >= 0:
                    combo.setCurrentText(current_year_str)
                else:
                    combo.setCurrentIndex(0)
        else:
            for combo in self._all_year_combos():
                combo.addItem("No years")
                combo.setEnabled(False)

        # Unblock
        for combo in self._all_year_combos():
            combo.blockSignals(False)

    def _populate_years_from_cache(self):
        years = []
        if self.db_manager and hasattr(self.db_manager, "get_cached_years"):
            try:
                years = self.db_manager.get_cached_years(source="supabase")
            except Exception:
                years = []

        self._sync_all_year_combos(years)

        if years:
            # Render each section from its own combo's selected year
            bill_year_str = self.year_combo.currentText()
            bill_year = int(bill_year_str) if bill_year_str.isdigit() else years[0]
            owner_year_str = self.owner_room_year_combo.currentText()
            owner_year = int(owner_year_str) if owner_year_str.isdigit() else years[0]
            self._render_year_from_cache(bill_year)
            self._render_owner_room_from_cache(owner_year)
        else:
            self._set_status("No cached years yet.")
            self._render_values([0.0] * 12)
            self._set_owner_room_status("No cached years yet.")
            self._render_owner_room_values([0.0] * 12, [""] * 12)

    def _refresh_years_from_supabase_async(self):
        from src.ui.background_workers import FetchSupabaseAvailableYearsWorker

        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            self._set_status(
                "Supabase not configured. Set it in Supabase Config tab, then return here."
            )
            return

        if self._years_worker and self._years_worker.isRunning():
            return

        self._set_status("Fetching available years from Supabase…")
        self._begin_global_update_activity(
            "dashboard-years", "Updates: syncing dashboard"
        )
        self._years_worker = FetchSupabaseAvailableYearsWorker(supabase_manager)
        self._years_worker.years_fetched.connect(self._on_years_fetched)
        self._years_worker.error_occurred.connect(self._on_years_error)
        self._years_worker.start()

    def _on_years_fetched(self, years: list):
        self._end_global_update_activity("dashboard-years")
        self._years_fetched_from_supabase_this_session = True
        years_int = []
        for y in years or []:
            try:
                years_int.append(int(y))
            except Exception:
                pass
        years_int = sorted(set(years_int), reverse=True)

        if not years_int:
            self._set_status("No years found in Supabase.")
            return

        self._sync_all_year_combos(years_int)

        # Determine the selected years from each combo for initial sync
        bill_year_str = self.year_combo.currentText()
        selected_year = int(bill_year_str) if bill_year_str.isdigit() else years_int[0]
        owner_year_str = self.owner_room_year_combo.currentText()
        selected_owner_room_year = (
            int(owner_year_str) if owner_year_str.isdigit() else years_int[0]
        )

        self._set_status("")
        self._sync_year_async(selected_year)
        self._sync_owner_room_year_async(selected_owner_room_year)

    def _on_years_error(self, msg: str):
        self._end_global_update_activity("dashboard-years")
        if msg == "PAUSED_PROJECT":
            self._set_status("Supabase project is paused.")
        else:
            self._set_status(msg)
        # Show offline banner when Supabase connection fails
        if hasattr(self, "_offline_banner"):
            self._offline_banner.show()

    def _on_refresh_clicked(self):
        sender = self.sender()
        # Determine which button triggered the refresh and use that section's year
        if (
            sender == self.rate_refresh_btn
            and hasattr(self, "rate_year_combo")
            and self.rate_year_combo is not None
        ):
            t = self.rate_year_combo.currentText().strip()
            year = int(t) if t.isdigit() else None
        elif (
            sender == self.elec_refresh_btn
            and hasattr(self, "elec_year_combo")
            and self.elec_year_combo is not None
        ):
            t = self.elec_year_combo.currentText().strip()
            year = int(t) if t.isdigit() else None
        else:
            year = self._selected_year()
        if year is None:
            self._refresh_years_from_supabase_async()
            return
        self._sync_year_async(year)

    def _selected_year(self) -> int | None:
        t = self.year_combo.currentText().strip()
        if not t:
            return None
        try:
            return int(t)
        except Exception:
            return None

    def _on_year_changed(self, index: int):
        year = self._selected_year()
        if year is None:
            return
        # Only render the yearly total bill section (no cross-combo sync)
        self._render_year_from_cache(year)
        self._sync_year_async(year)

    def _on_rate_year_changed(self, index: int):
        if not hasattr(self, "rate_year_combo") or self.rate_year_combo is None:
            return
        t = self.rate_year_combo.currentText().strip()
        if not t or t == "No years":
            return
        try:
            year = int(t)
        except Exception:
            return
        # Only render the rate section (no cross-combo sync)
        self._render_rate_from_cache(year)
        self._sync_year_async(year)

    def _on_elec_year_changed(self, index: int):
        if not hasattr(self, "elec_year_combo") or self.elec_year_combo is None:
            return
        t = self.elec_year_combo.currentText().strip()
        if not t or t == "No years":
            return
        try:
            year = int(t)
        except Exception:
            return
        # Only render the electricity section (no cross-combo sync)
        self._render_elec_from_cache(year)
        self._sync_year_async(year)

    def _sync_year_async(self, year: int):
        from src.ui.background_workers import SyncSupabaseMainCalculationsYearWorker

        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return
        if self._sync_worker and self._sync_worker.isRunning():
            return

        self._set_status("Syncing year from Supabase…")
        self._sync_worker_year = int(year)
        self._begin_global_update_activity(
            f"dashboard-main-{year}", "Updates: syncing dashboard"
        )
        self._sync_worker = SyncSupabaseMainCalculationsYearWorker(
            supabase_manager, self._db_path, year
        )
        self._sync_worker.sync_finished.connect(self._on_sync_finished)
        self._sync_worker.error_occurred.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_finished(self, year: int):
        sync_year = getattr(self, "_sync_worker_year", year)
        self._end_global_update_activity(f"dashboard-main-{sync_year}")
        self._set_status("")
        # Refresh all sections using their own combo's selected year
        self._render_year_from_cache(year)

    def _on_sync_error(self, msg: str):
        sync_year = getattr(self, "_sync_worker_year", None)
        if sync_year is not None:
            self._end_global_update_activity(f"dashboard-main-{sync_year}")
        if msg == "PAUSED_PROJECT":
            self._set_status("Supabase project is paused.")
        else:
            self._set_status(msg)

    def _render_year_from_cache(self, year: int):
        self._active_year = int(year)
        snapshot = self._get_dashboard_year_snapshot(year)
        totals = snapshot.get("monthly_totals", {}) if snapshot else {}
        values = []
        for m in MONTHS:
            values.append(float(totals.get(m, 0.0) or 0.0))
        self._update_meta(
            year, last_sync=snapshot.get("last_sync") if snapshot else None
        )
        self._render_values(values)
        # Update summary KPI cards
        self._update_summary_kpis(snapshot, year)
        # When called during global refresh, render rate/elec using their own combo years
        # Read rate combo year
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            rate_year_str = self.rate_year_combo.currentText()
            rate_year = int(rate_year_str) if rate_year_str.isdigit() else year
            self._render_rate_from_cache(
                rate_year,
                snapshot=snapshot if rate_year == int(year) else None,
            )
        # Read elec combo year
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            elec_year_str = self.elec_year_combo.currentText()
            elec_year = int(elec_year_str) if elec_year_str.isdigit() else year
            self._render_elec_from_cache(
                elec_year,
                snapshot=snapshot if elec_year == int(year) else None,
            )

    def _render_values(self, values: list[float]):
        values = (values or [])[:12]
        if len(values) < 12:
            values = values + [0.0] * (12 - len(values))

        self._current_values = values[:]
        self._current_tooltips = self._build_tooltips(values)
        self._update_kpis(values)

        if self._qtchart:
            self._apply_qt_line_chart(
                chart_view=self._chart_view,
                axis_x=self._chart_axis_x,
                axis_y=self._axis_y,
                series_attr="_line_series",
                raw_values=values,
                tooltips=self._current_tooltips,
                fill_opacity=140,
            )
            return

        if isinstance(self._chart_widget, (SimpleLineChartWidget, SimpleBarChartWidget)):
            self._chart_widget.set_data(MONTHS, values, tooltips=self._current_tooltips)

    def _render_rate_from_cache(self, year: int, snapshot: dict | None = None):
        rates = (snapshot or self._get_dashboard_year_snapshot(year)).get(
            "monthly_per_unit_cost", {}
        )

        raw = []
        vals = []
        tips = []
        for i, m in enumerate(MONTHS):
            v = rates.get(m)
            if v is None:
                raw.append(None)
                vals.append(0.0)
                tips.append(f"{m}\nPer Unit Cost: —")
            else:
                try:
                    fv = float(v)
                except Exception:
                    fv = None
                raw.append(fv)
                vals.append(float(fv or 0.0))
                tips.append(f"{m}\nPer Unit Cost: {self._fmt_rate(fv)}")

        self._rate_raw_values = raw[:12]
        self._rate_values = vals[:12]
        self._rate_tooltips = tips[:12]
        self._update_rate_kpis(self._rate_raw_values)

        if self._rate_qtchart:
            cyan = QColor(DashboardTheme.CYAN_CURRENT)
            self._apply_qt_line_chart(
                chart_view=self._rate_chart_view,
                axis_x=self._rate_axis_x,
                axis_y=self._rate_axis_y,
                series_attr="_rate_series",
                raw_values=self._rate_raw_values,
                tooltips=self._rate_tooltips,
                line_color=cyan,
                fill_top_color=QColor(73, 198, 255, 60),
                fill_bottom_color=QColor(73, 198, 255, 0),
            )
            return

        if isinstance(self._rate_chart_widget, (SimpleLineChartWidget, SimpleBarChartWidget)):
            self._rate_chart_widget.set_data(
                MONTHS, self._rate_values, tooltips=self._rate_tooltips
            )

    def _update_rate_kpis(self, raw_values: list[float | None]):
        year = int(getattr(self, "_active_year", datetime.now().year))
        self._update_section_kpis(
            kpis={
                "current": getattr(self, "rate_kpi_current", None),
                "prev": getattr(self, "rate_kpi_prev", None),
                "high": getattr(self, "rate_kpi_high", None),
                "low": getattr(self, "rate_kpi_low", None),
            },
            raw_values=raw_values,
            year=year,
            fmt_fn=self._fmt_rate,
            current_prefix="Per unit cost",
            extreme_prefix="per unit cost",
        )

    def _render_elec_from_cache(self, year: int, snapshot: dict | None = None):
        bills = (snapshot or self._get_dashboard_year_snapshot(year)).get(
            "monthly_total_electricity_bills", {}
        )

        raw = []
        vals = []
        tips = []
        for i, m in enumerate(MONTHS):
            v = bills.get(m)
            if v is None:
                raw.append(None)
                vals.append(0.0)
                tips.append(f"{m}\nTotal Elec. Bill: —")
            else:
                try:
                    fv = float(v)
                except Exception:
                    fv = None
                raw.append(fv)
                vals.append(float(fv or 0.0))
                tips.append(
                    f"{m}\nTotal Elec. Bill: TK {fv:,.2f}"
                    if fv is not None
                    else f"{m}\nTotal Elec. Bill: —"
                )

        self._elec_raw_values = raw[:12]
        self._elec_values = vals[:12]
        self._elec_tooltips = tips[:12]
        self._update_elec_kpis(self._elec_raw_values)

        if hasattr(self, "_elec_qtchart") and self._elec_qtchart:
            self._apply_qt_bar_chart(
                chart_view=self._elec_chart_view,
                axis_x=self._elec_axis_x,
                axis_y=self._elec_axis_y,
                series_attr="_elec_series",
                raw_values=self._elec_raw_values,
                tooltips=self._elec_tooltips,
                bar_color=QColor(DashboardTheme.ORANGE_WARNING),
            )
            return

        if isinstance(self._elec_chart_widget, (SimpleBarChartWidget, SimpleLineChartWidget)):
            self._elec_chart_widget.set_data(
                MONTHS, self._elec_values, tooltips=self._elec_tooltips
            )

    def _update_elec_kpis(self, raw_values: list[float | None]):
        year = int(getattr(self, "_active_year", datetime.now().year))

        def _fmt_elec(v):
            if v is None:
                return "\u2014"
            try:
                return f"TK {float(v):,.0f}"
            except Exception:
                return "\u2014"

        self._update_section_kpis(
            kpis={
                "current": getattr(self, "elec_kpi_current", None),
                "prev": getattr(self, "elec_kpi_prev", None),
                "high": getattr(self, "elec_kpi_high", None),
                "low": getattr(self, "elec_kpi_low", None),
            },
            raw_values=raw_values,
            year=year,
            fmt_fn=_fmt_elec,
            current_prefix="Total electricity bill",
            extreme_prefix="total electricity bill",
        )

    def _build_tooltips(self, values: list[float]) -> list[str]:
        out = []
        for i, m in enumerate(MONTHS):
            v = float(values[i] or 0.0)
            prev = float(values[i - 1] or 0.0) if i > 0 else 0.0
            d = v - prev if i > 0 else 0.0
            if i == 0:
                out.append(f"📅 {m}\n━━━━━━━━━━━━━━\n💰 {self._fmt_tk(v)}")
            else:
                delta_icon = "📈" if d >= 0 else "📉"
                out.append(f"📅 {m}\n━━━━━━━━━━━━━━\n💰 {self._fmt_tk(v)}\n{delta_icon} {self._fmt_delta(d)}")
        return out

    # ------------------------------------------------------------------
    # 2D: Unified KPI update
    # ------------------------------------------------------------------

    def _update_section_kpis(
        self,
        kpis,
        raw_values,
        year,
        fmt_fn,
        *,
        consider_fn=None,
        clamp_to_current_year=False,
        empty_consider_fallback=False,
        current_prefix="Bill",
        extreme_prefix="month",
        default_idx=(11, 10),
    ):
        """Unified KPI update for a dashboard section.

        *kpis* maps role names ("current", "prev", "high", "low") to
        ``InfoResultCard`` instances.  *raw_values* is a list of per-month
        values that may contain ``None``.
        """
        now = datetime.now()

        if consider_fn is None:
            consider_fn = lambda v: v is not None

        # Recent month = previous month (bills are added after month ends)
        current_idx = default_idx[0]
        prev_idx = default_idx[1]
        if year == now.year:
            # Use previous month as "recent month"
            if now.month == 1:
                current_idx = 11  # December of previous year
            else:
                current_idx = max(0, min(11, now.month - 2))  # Previous month
            prev_idx = max(0, current_idx - 1)
        else:
            present = [i for i, v in enumerate(raw_values or []) if consider_fn(v)]
            if present:
                current_idx = present[-1]
                prev_present = [i for i in present if i < current_idx]
                prev_idx = (
                    prev_present[-1]
                    if prev_present
                    else (max(0, current_idx - 1) if current_idx is not None else None)
                )

        def _value_at(idx):
            if idx is None or not (0 <= idx < len(raw_values or [])):
                return None
            return (raw_values or [])[idx]

        cv = _value_at(current_idx)
        pv = _value_at(prev_idx)

        def _month_label(idx):
            try:
                return MONTHS[idx][:3]
            except Exception:
                return "\u2014"

        cur_card = kpis.get("current")
        if cur_card:
            if current_idx is not None:
                cur_card._kpi_value_label.setText(
                    f"{_month_label(current_idx)} \u00b7 {fmt_fn(cv)}"
                )
            else:
                cur_card._kpi_value_label.setText("\u2014")

        prev_card = kpis.get("prev")
        if prev_card:
            if prev_idx is not None:
                prev_card._kpi_value_label.setText(
                    f"{_month_label(prev_idx)} \u00b7 {fmt_fn(pv)}"
                )
            else:
                prev_card._kpi_value_label.setText("\u2014")

        if clamp_to_current_year and year == now.year:
            consider = [
                i
                for i in range(0, min(current_idx + 1, len(raw_values or [])))
                if consider_fn((raw_values or [])[i])
            ]
        else:
            consider = [
                i for i, v in enumerate(raw_values or []) if consider_fn(v)
            ]

        if not consider and empty_consider_fallback:
            consider = list(range(len(raw_values or [])))

        max_idx = (
            max(consider, key=lambda i: float((raw_values or [])[i] or 0.0))
            if consider
            else None
        )
        min_idx = (
            min(consider, key=lambda i: float((raw_values or [])[i] or 0.0))
            if consider
            else None
        )

        high_card = kpis.get("high")
        if high_card:
            high_card._kpi_value_label.setText(
                f"{_month_label(max_idx)} \u00b7 {fmt_fn((raw_values or [])[max_idx])}"
                if max_idx is not None
                else "\u2014"
            )

        low_card = kpis.get("low")
        if low_card:
            low_card._kpi_value_label.setText(
                f"{_month_label(min_idx)} \u00b7 {fmt_fn((raw_values or [])[min_idx])}"
                if min_idx is not None
                else "\u2014"
            )

        # Tooltips
        if cur_card:
            if current_idx is not None:
                cur_card.setToolTip(
                    f"{current_prefix} for {MONTHS[current_idx]} {year}"
                )
            else:
                cur_card.setToolTip("No data")
        if prev_card:
            if prev_idx is not None:
                prev_card.setToolTip(
                    f"{current_prefix} for {MONTHS[prev_idx]} {year}"
                )
            else:
                prev_card.setToolTip("No previous month data")
        if high_card and max_idx is not None:
            high_card.setToolTip(
                f"Highest {extreme_prefix} in {year}: {MONTHS[max_idx]}"
            )
        if low_card and min_idx is not None:
            low_card.setToolTip(
                f"Lowest {extreme_prefix} in {year}: {MONTHS[min_idx]}"
            )

    def _update_kpis(self, values: list[float]):
        year = int(getattr(self, "_active_year", datetime.now().year))
        self._update_section_kpis(
            kpis={
                "current": getattr(self, "kpi_total", None),
                "prev": getattr(self, "kpi_avg", None),
                "high": getattr(self, "kpi_high", None),
                "low": getattr(self, "kpi_low", None),
            },
            raw_values=values,
            year=year,
            fmt_fn=self._fmt_tk,
            consider_fn=lambda v: float(v or 0.0) > 0.0,
            clamp_to_current_year=True,
            empty_consider_fallback=True,
        )

    # ------------------------------------------------------------------
    # Phase 7: Summary KPI Data Binding
    # ------------------------------------------------------------------

    def _update_summary_kpis(self, snapshot: dict, year: int):
        """Compute and update the 8 summary KPI cards from a dashboard snapshot."""
        if not snapshot:
            for card in self._all_summary_kpi_cards():
                card._kpi_value_label.setText("---")
            return

        monthly_totals = snapshot.get("monthly_totals", {})
        monthly_rates = snapshot.get("monthly_per_unit_cost", {})
        monthly_elec = snapshot.get("monthly_total_electricity_bills", {})

        # Determine recent month (previous month - bills are added after month ends)
        now = datetime.now()
        if year == now.year:
            # Previous month (if current month is Jan, previous is Dec of previous year)
            if now.month == 1:
                recent_month = "December"
            else:
                recent_month = MONTHS[now.month - 2]  # Previous month
        else:
            # For past years, find the last month with data
            recent_month = None
            for m in reversed(MONTHS):
                if m in monthly_totals and monthly_totals[m] is not None:
                    recent_month = m
                    break
            if not recent_month:
                recent_month = MONTHS[0] if monthly_totals else None

        # Get recent month data
        total_bill = 0.0
        elec_bill = 0.0
        rate_val = 0.0
        units = 0
        added_amount = 0.0
        water_bill = 0.0

        if recent_month:
            # Total bill (grand_total)
            total_bill = float(monthly_totals.get(recent_month, 0.0) or 0.0)

            # Electricity bill (total_unit_cost)
            elec_bill = float(monthly_elec.get(recent_month, 0.0) or 0.0)

            # Per unit cost
            r = monthly_rates.get(recent_month)
            rate_val = float(r) if r is not None else 0.0

            # Total units (elec_bill / per_unit_cost) - show as integer
            if rate_val > 0:
                units = int(round(elec_bill / rate_val))

        # Update KPI cards
        self._summary_total_bill._kpi_value_label.setText(self._fmt_tk(total_bill))
        self._summary_elec_bill._kpi_value_label.setText(self._fmt_tk(elec_bill))
        self._summary_rate._kpi_value_label.setText(self._fmt_rate(rate_val) if rate_val > 0 else "---")
        self._summary_units._kpi_value_label.setText(f"{units:,}" if units > 0 else "---")

        # Owner bill, Tenant bill, Added amount, and Water bill from room data
        owner_bill = 0.0
        tenant_elec_bill = 0.0
        tenant_water_bill = 0.0
        if recent_month and self.db_manager:
            try:
                # Get owner bill
                owner_data = self.db_manager.get_cached_monthly_owner_unit_bills(year, source="supabase")
                owner_bill = float(owner_data.get(recent_month, 0.0) or 0.0)

                # Get added amount
                added_data = self.db_manager.get_cached_monthly_owner_added_amounts(year, source="supabase")
                added_amount = float(added_data.get(recent_month, 0.0) or 0.0)

                # Get room bills for tenant calculation and water bills
                rooms = self.db_manager.get_cached_rooms(year, source="supabase") or []
                for room in rooms:
                    room_data = self.db_manager.get_cached_monthly_room_unit_bills(year, room, source="supabase")
                    tenant_elec_bill += float(room_data.get(recent_month, 0.0) or 0.0)

                    # Get water bills from room data
                    try:
                        water_data = self.db_manager.get_cached_monthly_room_water_bills(year, room, source="supabase")
                        tenant_water_bill += float(water_data.get(recent_month, 0.0) or 0.0)
                    except Exception:
                        pass
            except Exception:
                pass

        self._summary_owner_bill._kpi_value_label.setText(self._fmt_tk(owner_bill))

        # Tenant's Electricity and Water Bill - show electricity + water = total
        tenant_total = tenant_elec_bill + tenant_water_bill
        if tenant_total > 0:
            self._summary_tenant_bill._kpi_value_label.setText(
                f"{self._fmt_tk(tenant_elec_bill)} + {self._fmt_tk(tenant_water_bill)} = {self._fmt_tk(tenant_total)}"
            )
        else:
            self._summary_tenant_bill._kpi_value_label.setText("---")

        # Gas bill (Added amount) - show only added amount
        if added_amount > 0:
            self._summary_gas_bill._kpi_value_label.setText(self._fmt_tk(added_amount))
        else:
            self._summary_gas_bill._kpi_value_label.setText("---")

        # Active Rooms
        rooms = []
        if self.db_manager and hasattr(self.db_manager, "get_cached_rooms"):
            try:
                rooms = self.db_manager.get_cached_rooms(year, source="supabase") or []
            except Exception:
                rooms = []
        self._summary_rooms._kpi_value_label.setText(str(len(rooms)) if rooms else "---")

    def _all_summary_kpi_cards(self):
        """Return all 8 summary KPI card widgets."""
        return [
            self._summary_total_bill, self._summary_elec_bill,
            self._summary_rate, self._summary_units,
            self._summary_owner_bill, self._summary_tenant_bill,
            self._summary_gas_bill, self._summary_rooms,
        ]

    def _get_dashboard_year_snapshot(self, year: int) -> dict:
        if self.db_manager and hasattr(
            self.db_manager, "get_cached_dashboard_year_snapshot"
        ):
            try:
                return self.db_manager.get_cached_dashboard_year_snapshot(
                    year, source="supabase"
                )
            except Exception:
                return {}
        return {}

    def _update_meta(self, year: int, last_sync: str | None = None):
        if last_sync:
            text = f"Source: Supabase Cache · Last sync: {last_sync}"
            self.meta_label.setText(text)
            if hasattr(self, "rate_meta_label"):
                self.rate_meta_label.setText(text)
            if hasattr(self, "elec_meta_label"):
                self.elec_meta_label.setText(text)
        else:
            text = "Source: Supabase Cache"
            self.meta_label.setText(text)
            if hasattr(self, "rate_meta_label"):
                self.rate_meta_label.setText(text)
            if hasattr(self, "elec_meta_label"):
                self.elec_meta_label.setText(text)

    def _set_owner_room_status(self, text: str):
        t = (text or "").strip()
        if not t:
            return
        low = t.lower()
        if low.startswith("syncing") or low.endswith("…"):
            return
        level = "info"
        if "paused" in low:
            level = "warning"
        elif "disconnected" in low or "timeout" in low:
            level = "warning"
        elif (
            "error" in low
            or low.startswith("api error")
            or low.startswith("authentication")
        ):
            level = "error"
        self._notify(level, "Owner / Room", t, duration=5000)

    def _selected_owner_room_year(self) -> int | None:
        t = self.owner_room_year_combo.currentText().strip()
        if not t or t == "No years":
            return None
        try:
            return int(t)
        except Exception:
            return None

    def _on_owner_room_year_changed(self, index: int):
        year = self._selected_owner_room_year()
        if year is None:
            return
        self._render_owner_room_from_cache(year)
        self._sync_owner_room_year_async(year)

    def _on_scope_changed(self, index: int):
        mode = self.scope_combo.currentText().strip()
        if mode == "Room":
            self.room_combo.setEnabled(True)
            self._populate_rooms_from_cache()
            year = self._selected_owner_room_year()
            if year is not None:
                self._sync_room_year_async(year)
                self._sync_rentals_cache_async()
        else:
            self.room_combo.setEnabled(False)
        year = self._selected_owner_room_year()
        if year is not None:
            self._render_owner_room_from_cache(year)

    def _on_room_changed(self, index: int):
        year = self._selected_owner_room_year()
        if year is None:
            return
        if self.scope_combo.currentText().strip() != "Room":
            return
        self._render_owner_room_from_cache(year)

    def _on_owner_room_refresh_clicked(self):
        year = self._selected_owner_room_year()
        if year is None:
            self._refresh_years_from_supabase_async()
            return
        self._sync_owner_room_year_async(year)

    def _sync_owner_room_year_async(self, year: int):
        from src.ui.background_workers import SyncSupabaseMainCalculationsYearWorker

        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return

        if (
            self._owner_room_main_sync_worker
            and self._owner_room_main_sync_worker.isRunning()
        ):
            return

        self._set_owner_room_status("Syncing owner data from Supabase…")
        self._owner_room_main_sync_year = int(year)
        self._begin_global_update_activity(
            f"dashboard-owner-main-{year}", "Updates: syncing room data"
        )
        self._owner_room_main_sync_worker = SyncSupabaseMainCalculationsYearWorker(
            supabase_manager, self._db_path, year
        )
        self._owner_room_main_sync_worker.sync_finished.connect(
            self._on_owner_room_main_sync_finished
        )
        self._owner_room_main_sync_worker.error_occurred.connect(
            self._on_owner_room_main_sync_error
        )
        self._owner_room_main_sync_worker.start()

        self._sync_room_year_async(year)
        if self.scope_combo.currentText().strip() == "Room":
            self._sync_rentals_cache_async()

    def _on_owner_room_main_sync_finished(self, year: int):
        sync_year = getattr(self, "_owner_room_main_sync_year", year)
        self._end_global_update_activity(f"dashboard-owner-main-{sync_year}")
        self._set_owner_room_status("")
        self._render_owner_room_from_cache(year)

    def _on_owner_room_main_sync_error(self, msg: str):
        sync_year = getattr(self, "_owner_room_main_sync_year", None)
        if sync_year is not None:
            self._end_global_update_activity(f"dashboard-owner-main-{sync_year}")
        if msg == "PAUSED_PROJECT":
            self._set_owner_room_status("Supabase project is paused.")
        else:
            self._set_owner_room_status(msg)

    def _sync_room_year_async(self, year: int):
        from src.ui.background_workers import SyncSupabaseRoomCalculationsYearWorker

        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return
        if self._room_sync_worker and self._room_sync_worker.isRunning():
            return

        self._set_owner_room_status("Syncing room bills from Supabase…")
        self._room_sync_year = int(year)
        self._begin_global_update_activity(
            f"dashboard-room-{year}", "Updates: syncing room data"
        )
        self._room_sync_worker = SyncSupabaseRoomCalculationsYearWorker(
            supabase_manager, self._db_path, year
        )
        self._room_sync_worker.sync_finished.connect(self._on_room_sync_finished)
        self._room_sync_worker.error_occurred.connect(self._on_room_sync_error)
        self._room_sync_worker.start()

    def _on_room_sync_finished(self, year: int):
        sync_year = getattr(self, "_room_sync_year", year)
        self._end_global_update_activity(f"dashboard-room-{sync_year}")
        self._set_owner_room_status("")
        self._populate_rooms_from_cache()
        self._render_owner_room_from_cache(year)

    def _on_room_sync_error(self, msg: str):
        sync_year = getattr(self, "_room_sync_year", None)
        if sync_year is not None:
            self._end_global_update_activity(f"dashboard-room-{sync_year}")
        if msg == "PAUSED_PROJECT":
            self._set_owner_room_status("Supabase project is paused.")
        else:
            self._set_owner_room_status(msg)

    def _sync_rentals_cache_async(self):
        from src.ui.background_workers import SyncSupabaseRentalRecordsCacheWorker

        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return
        if self._rentals_sync_worker and self._rentals_sync_worker.isRunning():
            return

        self._begin_global_update_activity(
            "dashboard-rentals", "Updates: syncing rental cache"
        )
        self._rentals_sync_worker = SyncSupabaseRentalRecordsCacheWorker(
            supabase_manager, self._db_path
        )
        self._rentals_sync_worker.sync_finished.connect(self._on_rentals_sync_finished)
        self._rentals_sync_worker.error_occurred.connect(self._on_rentals_sync_error)
        self._rentals_sync_worker.start()

    def _on_rentals_sync_finished(self):
        self._end_global_update_activity("dashboard-rentals")
        year = self._selected_owner_room_year()
        if year is not None:
            self._render_owner_room_from_cache(year)

    def _on_rentals_sync_error(self, msg: str):
        self._end_global_update_activity("dashboard-rentals")
        if msg == "PAUSED_PROJECT":
            self._set_owner_room_status("Supabase project is paused.")
        else:
            self._set_owner_room_status(msg)

    def _populate_rooms_from_cache(self):
        year = self._selected_owner_room_year()
        if year is None or not self.db_manager:
            return
        rooms = []
        try:
            rooms = self.db_manager.get_cached_rooms(year, source="supabase")
        except Exception:
            rooms = []

        current = self.room_combo.currentText()
        self.room_combo.blockSignals(True)
        self.room_combo.clear()
        if rooms:

            def _room_sort_key(v: str):
                s = str(v or "").strip()
                digits = "".join(ch for ch in s if ch.isdigit())
                try:
                    n = int(digits) if digits else None
                except Exception:
                    n = None
                return (0 if n is not None else 1, n if n is not None else 0, s.lower())

            rooms = sorted(rooms, key=_room_sort_key)
            for r in rooms:
                self.room_combo.addItem(r)
        else:
            self.room_combo.addItem("No rooms")
        self.room_combo.blockSignals(False)

        if current and current in rooms:
            self.room_combo.setCurrentText(current)
        elif rooms:
            self.room_combo.setCurrentIndex(0)

    def _render_owner_room_from_cache(self, year: int):
        self._owner_room_active_year = int(year)
        mode = self.scope_combo.currentText().strip()

        if mode == "Room":
            self._update_owner_room_meta(year, mode="Room")
            room_name = self.room_combo.currentText().strip()
            if not room_name or room_name == "No rooms":
                empty_raw = [None] * 12
                self._render_owner_room_values(
                    [0.0] * 12,
                    self._build_owner_room_tooltips(
                        empty_raw, year, room_name, mode="Room"
                    ),
                    empty_raw,
                    mode="Room",
                )
                return
            month_map = {}
            try:
                month_map = (
                    self.db_manager.get_cached_monthly_room_unit_bills(
                        year, room_name, source="supabase"
                    )
                    if self.db_manager
                    else {}
                )
            except Exception:
                month_map = {}
            vals_raw = [month_map.get(m) for m in MONTHS]
            vals = [float(v or 0.0) if v is not None else 0.0 for v in vals_raw]
            room_records = self._get_rental_records_for_room(room_name)
            tenant_lookup = self._build_tenant_lookup_for_year(year, room_records)
            tips = self._build_owner_room_tooltips(
                vals_raw, year, room_name, mode="Room", tenant_lookup=tenant_lookup
            )
            self._render_owner_room_values(vals, tips, vals_raw, mode="Room")
            return

        self._update_owner_room_meta(year, mode="Owner")
        month_map = {}
        try:
            month_map = (
                self.db_manager.get_cached_monthly_owner_unit_bills(
                    year, source="supabase"
                )
                if self.db_manager
                else {}
            )
        except Exception:
            month_map = {}
        vals_raw = [month_map.get(m) for m in MONTHS]
        vals = [float(v or 0.0) if v is not None else 0.0 for v in vals_raw]
        tips = self._build_owner_room_tooltips(vals_raw, year, "", mode="Owner")
        self._render_owner_room_values(vals, tips, vals_raw, mode="Owner")

    def _render_owner_room_values(
        self,
        values: list[float],
        tooltips: list[str],
        raw_values: list | None = None,
        mode: str = "Owner",
        grouped_data: dict | None = None,
    ):
        values = (values or [])[:12]
        if len(values) < 12:
            values = values + [0.0] * (12 - len(values))

        self._owner_room_values = values[:]
        self._owner_room_tooltips = (tooltips or [""] * 12)[:12]
        self._owner_room_raw_values = (raw_values or values)[:12]
        self._update_owner_room_kpis(values, tooltips, self._owner_room_raw_values)

        if self._owner_room_qtchart:
            if grouped_data and len(grouped_data) > 1:
                self._apply_qt_grouped_bar_chart(
                    chart_view=self._owner_room_chart_view,
                    axis_x=self._owner_room_axis_x,
                    axis_y=self._owner_room_axis_y,
                    series_attr="_owner_room_bar_series",
                    grouped_data=grouped_data,
                    tooltips=self._owner_room_tooltips,
                )
            else:
                bar_color = (
                    QColor(DashboardTheme.PURPLE_SECONDARY)
                    if mode == "Owner"
                    else QColor(DashboardTheme.CYAN_CURRENT)
                )
                self._apply_qt_bar_chart(
                    chart_view=self._owner_room_chart_view,
                    axis_x=self._owner_room_axis_x,
                    axis_y=self._owner_room_axis_y,
                    series_attr="_owner_room_bar_series",
                    raw_values=self._owner_room_raw_values,
                    tooltips=self._owner_room_tooltips,
                    bar_color=bar_color,
                )
            return

        if isinstance(self._owner_room_chart_widget, (SimpleBarChartWidget, SimpleLineChartWidget)):
            if grouped_data and len(grouped_data) > 1 and isinstance(self._owner_room_chart_widget, SimpleBarChartWidget):
                self._owner_room_chart_widget.set_grouped_data(
                    MONTHS, grouped_data, tooltips=self._owner_room_tooltips
                )
            else:
                self._owner_room_chart_widget.set_data(
                    MONTHS, values, tooltips=self._owner_room_tooltips
                )

    def _build_owner_room_tooltips(
        self,
        raw_values: list[float | None],
        year: int,
        room_name: str,
        mode: str,
        room_water_values: list[float | None] | None = None,
        tenant_lookup: dict[int, str | None] | None = None,
    ) -> list[str]:
        out = []
        prev_val = None
        for i, m in enumerate(MONTHS):
            v = raw_values[i] if i < len(raw_values) else None
            has_bill = v is not None
            bill_text = self._fmt_tk(v) if has_bill else "No billing"
            delta_text = ""
            if i > 0 and has_bill and prev_val is not None:
                delta_text = self._fmt_delta(float(v) - float(prev_val))
            prev_val = v if has_bill else prev_val

            if mode == "Room":
                if tenant_lookup is not None:
                    tenant = tenant_lookup.get(i + 1)
                else:
                    tenant = self._tenant_for_month(year, i + 1, room_name)
                tenant_line = f"👤 Tenant: {tenant}" if tenant else "👤 Tenant: —"
                if delta_text:
                    delta_icon = "📈" if float(v) - float(prev_val) >= 0 else "📉"
                    out.append(
                        f"📅 {m} {year}\n━━━━━━━━━━━━━━\n⚡ Electricity: {bill_text}\n{delta_icon} {delta_text}\n{tenant_line}"
                    )
                else:
                    out.append(f"📅 {m} {year}\n━━━━━━━━━━━━━━\n⚡ Electricity: {bill_text}\n{tenant_line}")
            else:
                label = "⚡ Owner Electricity Bill"
                if delta_text:
                    delta_icon = "📈" if float(v) - float(prev_val) >= 0 else "📉"
                    out.append(f"📅 {m} {year}\n━━━━━━━━━━━━━━\n{label}: {bill_text}\n{delta_icon} {delta_text}")
                else:
                    out.append(f"📅 {m} {year}\n━━━━━━━━━━━━━━\n{label}: {bill_text}")
        return out

    def _update_owner_room_kpis(
        self, values: list[float], tooltips: list[str], raw_values: list
    ):
        year = int(getattr(self, "_owner_room_active_year", datetime.now().year))
        self._update_section_kpis(
            kpis={
                "current": getattr(self, "owner_kpi_total", None),
                "prev": getattr(self, "owner_kpi_avg", None),
                "high": getattr(self, "owner_kpi_high", None),
                "low": getattr(self, "owner_kpi_low", None),
            },
            raw_values=raw_values,
            year=year,
            fmt_fn=lambda v: self._fmt_tk(v) if v is not None else "\u2014",
            default_idx=(None, None),
        )

    def _update_owner_room_meta(self, year: int, mode: str):
        last_sync = None
        if self.db_manager:
            try:
                table = (
                    "main_calculations_cache"
                    if mode == "Owner"
                    else "room_calculations_cache"
                )
                row = self.db_manager.execute_query(
                    f"SELECT MAX(synced_at) AS last_sync FROM {table} WHERE source = ? AND year = ?",
                    ("supabase", int(year)),
                    fetch_one=True,
                )
                if row:
                    last_sync = row["last_sync"]
            except Exception:
                last_sync = None
        if last_sync:
            self.owner_room_meta_label.setText(
                f"Source: Supabase Cache · Last sync: {last_sync}"
            )
        else:
            self.owner_room_meta_label.setText("Source: Supabase Cache")

    def _parse_year_month(self, dt_str: str | None) -> tuple[int, int] | None:
        if not dt_str:
            return None
        s = str(dt_str).strip()
        if len(s) < 7:
            return None
        try:
            y = int(s[0:4])
            m = int(s[5:7])
            if 1 <= m <= 12:
                return y, m
            return None
        except Exception:
            return None

    def _month_before(self, y: int, m: int) -> tuple[int, int]:
        if m > 1:
            return y, m - 1
        return y - 1, 12

    def _get_room_number_candidates(self, room_name: str) -> list[str]:
        s = str(room_name or "").strip()
        if not s:
            return []
        digits = "".join(ch for ch in s if ch.isdigit())
        out = [s]
        if digits and digits not in out:
            out.append(digits)
        return out

    def _get_rental_records_for_room(self, room_name: str):
        if not self.db_manager:
            return []

        for key in self._get_room_number_candidates(room_name):
            try:
                records = self.db_manager.get_rental_records_for_room(key)
            except Exception:
                records = []
            if records:
                return records
        return []

    def _build_tenant_entries(self, records) -> list[dict]:
        entries = []
        for r in records or []:
            try:
                tenant_name = r["tenant_name"]
            except Exception:
                tenant_name = None

            start_parsed = self._parse_year_month(r["created_at"])
            if not start_parsed:
                continue
            sy, sm = start_parsed

            is_archived = 0
            try:
                is_archived = int(r["is_archived"] or 0)
            except Exception:
                is_archived = 0

            end_parsed = None
            if is_archived:
                end_parsed = self._parse_year_month(r["updated_at"])

            entries.append(
                {"tenant": tenant_name, "sy": sy, "sm": sm, "eym": end_parsed}
            )

        if not entries:
            return []

        entries.sort(key=lambda e: (e["sy"], e["sm"]))
        for i, e in enumerate(entries):
            end_ym = e["eym"]
            if i + 1 < len(entries):
                ny, nm = entries[i + 1]["sy"], entries[i + 1]["sm"]
                next_end = self._month_before(ny, nm)
                if end_ym is None or next_end < end_ym:
                    end_ym = next_end
            e["eym"] = end_ym

        return entries

    def _resolve_tenant_from_entries(
        self, year: int, month: int, entries: list[dict]
    ) -> str | None:
        for e in entries:
            sy, sm = e["sy"], e["sm"]
            end_ym = e["eym"]
            if (year, month) < (sy, sm):
                continue
            if end_ym is None:
                return e["tenant"]
            if (sy, sm) <= (year, month) <= end_ym:
                return e["tenant"]
        return None

    def _build_tenant_lookup_for_year(
        self, year: int, records
    ) -> dict[int, str | None]:
        entries = self._build_tenant_entries(records)
        if not entries:
            return {}
        return {
            month: self._resolve_tenant_from_entries(year, month, entries)
            for month in range(1, 13)
        }

    def _tenant_for_month(self, year: int, month: int, room_name: str) -> str | None:
        records = self._get_rental_records_for_room(room_name)
        if not records:
            return None
        entries = self._build_tenant_entries(records)
        return self._resolve_tenant_from_entries(year, month, entries)
