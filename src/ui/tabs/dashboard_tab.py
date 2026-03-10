import time
from datetime import datetime
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize, QEvent, QMargins
from PyQt5.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter, QPen, QLinearGradient, QPainterPath
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QToolTip, QFrame, QApplication
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
from src.ui.custom_widgets import AutoScrollArea

from src.ui.background_workers import (
    FetchSupabaseAvailableYearsWorker,
    SyncSupabaseMainCalculationsYearWorker,
    SyncSupabaseRoomCalculationsYearWorker,
    SyncSupabaseRentalRecordsCacheWorker,
)


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
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
        t.setStyleSheet("color: #FFFFFF; font-weight: bold; font-size: 13px; letter-spacing: 0.5px;")
        lay.addWidget(t, 1, Qt.AlignVCenter)

        v = BodyLabel("0")
        v.setStyleSheet(f"color: rgb({r}, {g}, {b}); font-size: 44px; font-weight: 700;")
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

    def set_data(self, labels: list[str], values: list[float], tooltips: list[str] | None = None):
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
        self._configure_tooltips()
        self.db_manager = getattr(self.main_window, "db_manager", None)
        self._db_path = getattr(self.db_manager, "db_name", None) if self.db_manager else None

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
        self._owner_room_chart_view = None
        self._owner_room_chart_widget = None
        self._owner_room_qtchart = None
        self._owner_room_bar_set = None
        self._owner_room_axis_y = None
        self._supabase_poll_tries = 0
        self._supabase_poll_timer = None
        self._years_fetched_from_supabase_this_session = False
        self._current_values = [0.0] * 12
        self._current_tooltips = [""] * 12
        self._owner_room_values = [0.0] * 12
        self._owner_room_tooltips = [""] * 12

        self._build_ui()
        self._populate_years_from_cache()
        self._start_supabase_year_poll()

    def _configure_tooltips(self):
        QToolTip.setFont(QFont("Segoe UI", 12))
        app = QApplication.instance()
        if not app:
            return
        tooltip_qss = """
            /* dashboard-tooltip */
            QToolTip {
                color: #ffffff;
                background-color: rgba(0, 0, 0, 220);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 8px;
                padding: 9px 10px;
                font-size: 12px;
            }
        """
        existing = app.styleSheet() or ""
        if "dashboard-tooltip" in existing:
            start = existing.rfind("/* dashboard-tooltip */")
            end = existing.find("}", start)
            if start >= 0 and end >= 0:
                existing = existing[:start] + existing[end + 1 :]
        app.setStyleSheet(existing + "\n" + tooltip_qss)

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
        if self._years_fetched_from_supabase_this_session and self.year_combo.isEnabled() and self.year_combo.count() > 0:
            self._supabase_poll_timer.stop()
            return

        self._supabase_poll_tries += 1
        supabase_manager = getattr(self.main_window, "supabase_manager", None)

        if supabase_manager and supabase_manager.is_client_initialized():
            self._refresh_years_from_supabase_async()
        else:
            if self._supabase_poll_tries == 3:
                self._set_status("Supabase not configured. Set it in Supabase Config tab, then return here.")

        if self._supabase_poll_tries >= 25:
            self._supabase_poll_timer.stop()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = AutoScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        root.addWidget(scroll, 1)

        page = QWidget()
        scroll.setWidget(page)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(12, 12, 12, 12)
        page_layout.setSpacing(12)

        title = TitleLabel("Dashboard")
        title.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #0078D4; letter-spacing: 1px; margin: 8px 0px;"
        )
        page_layout.addWidget(title)
        title_line = QFrame()
        title_line.setFixedHeight(2)
        title_line.setStyleSheet("background-color: #0078D4; border: none; margin: 0px 20px;")
        page_layout.addWidget(title_line)
        subtitle = CaptionLabel("Overview and trends")
        subtitle.setTextColor(QColor(180, 180, 180) if isDarkTheme() else QColor(90, 90, 90))
        page_layout.addWidget(subtitle)

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

        rate_card = StaticCardWidget(self)
        rate_card.setObjectName("perUnitCostCard")
        rate_card.setStyleSheet("""
            CardWidget#perUnitCostCard {
                border-radius: 12px;
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
            }
        """)
        rate_layout = QVBoxLayout(rate_card)
        rate_layout.setContentsMargins(6, 6, 6, 6)
        rate_layout.setSpacing(6)

        rate_top = QHBoxLayout()
        rate_icon = IconWidget(FluentIcon.CALENDAR)
        rate_icon.setFixedSize(18, 18)
        rate_top.addWidget(rate_icon)
        rate_header = TitleLabel("Per Unit Cost Trend")
        rate_header.setStyleSheet("font-size: 22px; font-weight: 800; color: #0078D4;")
        rate_top.addWidget(rate_header)
        rate_hint = CaptionLabel("Hover points to see details")
        rate_hint.setTextColor(QColor(160, 160, 160) if isDarkTheme() else QColor(110, 110, 110))
        rate_top.addWidget(rate_hint)
        rate_top.addStretch(1)

        self.rate_year_combo = ComboBox()
        self.rate_year_combo.setMinimumWidth(110)
        self.rate_year_combo.currentIndexChanged.connect(self._on_rate_year_changed)
        self.rate_year_combo.setToolTip("Years are fetched from Supabase and cached locally")
        rate_top.addWidget(self.rate_year_combo)

        self.rate_refresh_btn = PrimaryPushButton("Refresh")
        self.rate_refresh_btn.setIcon(FluentIcon.SYNC.icon(color=QColor(255, 255, 255)))
        self.rate_refresh_btn.setIconSize(QSize(20, 20))
        self.rate_refresh_btn.setFixedHeight(40)
        self.rate_refresh_btn.setMinimumHeight(40)
        self.rate_refresh_btn.setStyleSheet(refresh_css)
        self.rate_refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.rate_refresh_btn.setToolTip("Sync from Supabase and update local cache")
        rate_top.addWidget(self.rate_refresh_btn)

        rate_layout.addLayout(rate_top)

        rate_divider = QFrame()
        rate_divider.setFixedHeight(2)
        rate_divider.setStyleSheet("background-color: #0078D4; border: none; margin: 2px 16px;")
        rate_layout.addWidget(rate_divider)

        rate_meta_row = QHBoxLayout()
        self.rate_meta_label = CaptionLabel("")
        self.rate_meta_label.setTextColor(QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110))
        rate_meta_row.addWidget(self.rate_meta_label)
        rate_meta_row.addStretch(1)
        rate_layout.addLayout(rate_meta_row)

        self._rate_chart_widget = self._create_rate_chart_widget()
        rate_stats_row = QHBoxLayout()
        rate_stats_row.setSpacing(14)
        rate_kpi_col = QVBoxLayout()
        rate_kpi_col.setSpacing(12)
        self.rate_kpi_current = self._create_kpi_card("Current Month")
        self.rate_kpi_prev = self._create_kpi_card("Previous Month")
        self.rate_kpi_high = self._create_kpi_card("Highest Month")
        self.rate_kpi_low = self._create_kpi_card("Lowest Month")
        rate_kpi_col.addWidget(self.rate_kpi_current)
        rate_kpi_col.addWidget(self.rate_kpi_prev)
        rate_kpi_col.addWidget(self.rate_kpi_high)
        rate_kpi_col.addWidget(self.rate_kpi_low)
        rate_kpi_col.addStretch(1)
        rate_stats_row.addLayout(rate_kpi_col, 0)
        rate_stats_row.addWidget(self._rate_chart_widget, 1)
        rate_layout.addLayout(rate_stats_row, 1)

        page_layout.addWidget(rate_card)

        elec_card = StaticCardWidget(self)
        elec_card.setObjectName("electricityBillCard")
        elec_card.setStyleSheet("""
            CardWidget#electricityBillCard {
                border-radius: 12px;
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
            }
        """)
        elec_layout = QVBoxLayout(elec_card)
        elec_layout.setContentsMargins(6, 6, 6, 6)
        elec_layout.setSpacing(6)

        elec_top = QHBoxLayout()
        elec_icon = IconWidget(FluentIcon.SPEED_HIGH)
        elec_icon.setFixedSize(18, 18)
        elec_top.addWidget(elec_icon)
        elec_header = TitleLabel("Total Electricity Bill")
        elec_header.setStyleSheet("font-size: 22px; font-weight: 800; color: #0078D4;")
        elec_top.addWidget(elec_header)
        elec_hint = CaptionLabel("Hover points to see details")
        elec_hint.setTextColor(QColor(160, 160, 160) if isDarkTheme() else QColor(110, 110, 110))
        elec_top.addWidget(elec_hint)
        elec_top.addStretch(1)

        self.elec_year_combo = ComboBox()
        self.elec_year_combo.setMinimumWidth(110)
        self.elec_year_combo.currentIndexChanged.connect(self._on_elec_year_changed)
        self.elec_year_combo.setToolTip("Years are fetched from Supabase and cached locally")
        elec_top.addWidget(self.elec_year_combo)

        self.elec_refresh_btn = PrimaryPushButton("Refresh")
        self.elec_refresh_btn.setIcon(FluentIcon.SYNC.icon(color=QColor(255, 255, 255)))
        self.elec_refresh_btn.setIconSize(QSize(20, 20))
        self.elec_refresh_btn.setFixedHeight(40)
        self.elec_refresh_btn.setMinimumHeight(40)
        self.elec_refresh_btn.setStyleSheet(refresh_css)
        self.elec_refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.elec_refresh_btn.setToolTip("Sync from Supabase and update local cache")
        elec_top.addWidget(self.elec_refresh_btn)

        elec_layout.addLayout(elec_top)

        elec_divider = QFrame()
        elec_divider.setFixedHeight(2)
        elec_divider.setStyleSheet("background-color: #0078D4; border: none; margin: 2px 16px;")
        elec_layout.addWidget(elec_divider)

        elec_meta_row = QHBoxLayout()
        self.elec_meta_label = CaptionLabel("")
        self.elec_meta_label.setTextColor(QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110))
        elec_meta_row.addWidget(self.elec_meta_label)
        elec_meta_row.addStretch(1)
        elec_layout.addLayout(elec_meta_row)

        self._elec_chart_widget = self._create_elec_chart_widget()
        elec_stats_row = QHBoxLayout()
        elec_stats_row.setSpacing(14)
        elec_kpi_col = QVBoxLayout()
        elec_kpi_col.setSpacing(12)
        self.elec_kpi_current = self._create_kpi_card("Current Month")
        self.elec_kpi_prev = self._create_kpi_card("Previous Month")
        self.elec_kpi_high = self._create_kpi_card("Highest Month")
        self.elec_kpi_low = self._create_kpi_card("Lowest Month")
        elec_kpi_col.addWidget(self.elec_kpi_current)
        elec_kpi_col.addWidget(self.elec_kpi_prev)
        elec_kpi_col.addWidget(self.elec_kpi_high)
        elec_kpi_col.addWidget(self.elec_kpi_low)
        elec_kpi_col.addStretch(1)
        elec_stats_row.addLayout(elec_kpi_col, 0)
        elec_stats_row.addWidget(self._elec_chart_widget, 1)
        elec_layout.addLayout(elec_stats_row, 1)

        page_layout.addWidget(elec_card)

        card = StaticCardWidget(self)
        card.setObjectName("yearlyBillCard")
        card.setStyleSheet("""
            CardWidget#yearlyBillCard {
                border-radius: 12px;
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(6, 6, 6, 6)
        card_layout.setSpacing(6)

        top_row = QHBoxLayout()
        icon = IconWidget(FluentIcon.SHOPPING_CART)
        icon.setFixedSize(18, 18)
        top_row.addWidget(icon)
        header = TitleLabel("Yearly Total Bill")
        header.setStyleSheet("font-size: 22px; font-weight: 800; color: #0078D4;")
        top_row.addWidget(header)
        hint = CaptionLabel("Hover points to see details")
        hint.setTextColor(QColor(160, 160, 160) if isDarkTheme() else QColor(110, 110, 110))
        top_row.addWidget(hint)
        top_row.addStretch(1)

        self.year_combo = ComboBox()
        self.year_combo.setMinimumWidth(110)
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        self.year_combo.setToolTip("Years are fetched from Supabase and cached locally")
        top_row.addWidget(self.year_combo)

        self.refresh_btn = PrimaryPushButton("Refresh")
        self.refresh_btn.setIcon(FluentIcon.SYNC.icon(color=QColor(255, 255, 255)))
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.setFixedHeight(40)
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.setStyleSheet(refresh_css)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.refresh_btn.setToolTip("Sync from Supabase and update local cache")
        top_row.addWidget(self.refresh_btn)

        card_layout.addLayout(top_row)
        card_divider = QFrame()
        card_divider.setFixedHeight(2)
        card_divider.setStyleSheet("background-color: #0078D4; border: none; margin: 2px 16px;")
        card_layout.addWidget(card_divider)

        meta_row = QHBoxLayout()
        self.meta_label = CaptionLabel("")
        self.meta_label.setTextColor(QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110))
        meta_row.addWidget(self.meta_label)
        meta_row.addStretch(1)
        card_layout.addLayout(meta_row)

        self.status_label = BodyLabel("")
        self.status_label.setTextColor(QColor(200, 200, 200))
        self.status_label.setVisible(False)
        self.status_label.setFixedHeight(0)
        card_layout.addWidget(self.status_label)

        self._chart_widget = self._create_chart_widget()
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        kpi_col = QVBoxLayout()
        kpi_col.setSpacing(12)
        self.kpi_total = self._create_kpi_card("Current Month")
        self.kpi_avg = self._create_kpi_card("Previous Month")
        self.kpi_high = self._create_kpi_card("Highest Month")
        self.kpi_low = self._create_kpi_card("Lowest Month")
        kpi_col.addWidget(self.kpi_total)
        kpi_col.addWidget(self.kpi_avg)
        kpi_col.addWidget(self.kpi_high)
        kpi_col.addWidget(self.kpi_low)
        kpi_col.addStretch(1)
        stats_row.addLayout(kpi_col, 0)
        stats_row.addWidget(self._chart_widget, 1)
        card_layout.addLayout(stats_row, 1)

        page_layout.addWidget(card)

        owner_card = StaticCardWidget(self)
        owner_card.setObjectName("ownerRoomBillCard")
        owner_card.setStyleSheet("""
            CardWidget#ownerRoomBillCard {
                border-radius: 12px;
                background-color: #2b2b2b;
                border: 1px solid #3d3d3d;
            }
        """)
        owner_layout = QVBoxLayout(owner_card)
        owner_layout.setContentsMargins(6, 6, 6, 6)
        owner_layout.setSpacing(6)

        owner_top = QHBoxLayout()
        owner_icon = IconWidget(FluentIcon.PEOPLE)
        owner_icon.setFixedSize(18, 18)
        owner_top.addWidget(owner_icon)
        owner_header = TitleLabel("Owner / Room Bill Trend")
        owner_header.setStyleSheet("font-size: 22px; font-weight: 800; color: #0078D4;")
        owner_top.addWidget(owner_header)
        owner_hint = CaptionLabel("Owner is default · hover points for details")
        owner_hint.setTextColor(QColor(160, 160, 160) if isDarkTheme() else QColor(110, 110, 110))
        owner_top.addWidget(owner_hint)
        owner_top.addStretch(1)

        self.owner_room_year_combo = ComboBox()
        self.owner_room_year_combo.setMinimumWidth(110)
        self.owner_room_year_combo.currentIndexChanged.connect(self._on_owner_room_year_changed)
        self.owner_room_year_combo.setToolTip("Years are fetched from Supabase and cached locally")
        owner_top.addWidget(self.owner_room_year_combo)

        self.scope_combo = ComboBox()
        self.scope_combo.addItems(["Owner", "Room"])
        self.scope_combo.setCurrentIndex(0)
        self.scope_combo.currentIndexChanged.connect(self._on_scope_changed)
        self.scope_combo.setToolTip("Switch between owner bill and a room bill")
        owner_top.addWidget(self.scope_combo)

        self.room_combo = ComboBox()
        self.room_combo.setMinimumWidth(140)
        self.room_combo.currentIndexChanged.connect(self._on_room_changed)
        self.room_combo.setEnabled(False)
        self.room_combo.setToolTip("Select a room to view its monthly bills")
        owner_top.addWidget(self.room_combo)

        self.owner_room_refresh_btn = PrimaryPushButton("Refresh")
        self.owner_room_refresh_btn.setIcon(FluentIcon.SYNC.icon(color=QColor(255, 255, 255)))
        self.owner_room_refresh_btn.setIconSize(QSize(20, 20))
        self.owner_room_refresh_btn.setFixedHeight(40)
        self.owner_room_refresh_btn.setMinimumHeight(40)
        self.owner_room_refresh_btn.setStyleSheet(self.refresh_btn.styleSheet())
        self.owner_room_refresh_btn.clicked.connect(self._on_owner_room_refresh_clicked)
        self.owner_room_refresh_btn.setToolTip("Sync owner/room bills and tenant info from Supabase")
        owner_top.addWidget(self.owner_room_refresh_btn)

        owner_layout.addLayout(owner_top)
        owner_divider = QFrame()
        owner_divider.setFixedHeight(2)
        owner_divider.setStyleSheet("background-color: #0078D4; border: none; margin: 2px 16px;")
        owner_layout.addWidget(owner_divider)

        owner_meta_row = QHBoxLayout()
        self.owner_room_meta_label = CaptionLabel("")
        self.owner_room_meta_label.setTextColor(QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110))
        owner_meta_row.addWidget(self.owner_room_meta_label)
        owner_meta_row.addStretch(1)
        owner_layout.addLayout(owner_meta_row)

        self.owner_room_status_label = BodyLabel("")
        self.owner_room_status_label.setTextColor(QColor(200, 200, 200))
        self.owner_room_status_label.setVisible(False)
        self.owner_room_status_label.setFixedHeight(0)
        owner_layout.addWidget(self.owner_room_status_label)

        self._owner_room_chart_widget = self._create_owner_room_chart_widget()
        owner_stats_row = QHBoxLayout()
        owner_stats_row.setSpacing(14)
        owner_kpi_col = QVBoxLayout()
        owner_kpi_col.setSpacing(12)
        self.owner_kpi_total = self._create_kpi_card("Current Month")
        self.owner_kpi_avg = self._create_kpi_card("Previous Month")
        self.owner_kpi_high = self._create_kpi_card("Highest Month")
        self.owner_kpi_low = self._create_kpi_card("Lowest Month")
        owner_kpi_col.addWidget(self.owner_kpi_total)
        owner_kpi_col.addWidget(self.owner_kpi_avg)
        owner_kpi_col.addWidget(self.owner_kpi_high)
        owner_kpi_col.addWidget(self.owner_kpi_low)
        owner_kpi_col.addStretch(1)
        owner_stats_row.addLayout(owner_kpi_col, 0)
        owner_stats_row.addWidget(self._owner_room_chart_widget, 1)
        owner_layout.addLayout(owner_stats_row, 1)

        page_layout.addWidget(owner_card)
        page_layout.addStretch(1)

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
            from PyQt5.QtChart import QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis

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
            from PyQt5.QtChart import QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis

            self._rate_qtchart = (QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis)
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

    def _init_rate_qtchart(self):
        QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis = self._rate_qtchart

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
        axis_y.setLabelFormat("TK %.2f")
        axis_y.setTickCount(6)

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        self._rate_axis_y = axis_y
        self._rate_axis_x = axis_x
        self._rate_series = []
        self._rate_chart_view.setChart(chart)

    def _create_elec_chart_widget(self):
        try:
            from PyQt5.QtChart import QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis

            self._elec_qtchart = (QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis)
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(320)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._elec_chart_view = view
            self._init_elec_qtchart()
            return view
        except Exception:
            self._elec_qtchart = None
            return SimpleLineChartWidget(self)

    def _init_elec_qtchart(self):
        QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis = self._elec_qtchart

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
        axis_y.setLabelFormat("TK %.0f")
        axis_y.setTickCount(6)
        try:
            axis_y.setTitleText("Total Electricity Bill (TK)")
            axis_y.setTitleBrush(QColor(220, 220, 220))
        except Exception:
            pass

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        self._elec_axis_y = axis_y
        self._elec_axis_x = axis_x
        self._elec_series = []
        self._elec_chart_view.setChart(chart)

    def _init_qtchart(self):
        QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis = self._qtchart

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
        axis_y.setLabelFormat("TK %.0f")
        axis_y.setTickCount(6)

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        self._axis_y = axis_y
        self._chart_axis_x = axis_x
        self._line_series = []
        self._chart_view.setChart(chart)

    def _create_owner_room_chart_widget(self):
        try:
            from PyQt5.QtChart import QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis

            self._owner_room_qtchart = (QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis)
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(470)
            view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._owner_room_chart_view = view
            self._init_owner_room_qtchart()
            return view
        except Exception:
            self._owner_room_qtchart = None
            return SimpleLineChartWidget(self)

    def _init_owner_room_qtchart(self):
        QChartView, QChart, QLineSeries, QValueAxis, QCategoryAxis = self._owner_room_qtchart

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
        axis_y.setLabelFormat("TK %.0f")
        axis_y.setTickCount(6)

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)

        self._owner_room_axis_y = axis_y
        self._owner_room_axis_x = axis_x
        self._owner_room_line_series = []
        self._owner_room_chart_view.setChart(chart)

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

    def _apply_qt_line_chart(self, chart_view, axis_x, axis_y, series_attr: str, raw_values: list, tooltips: list[str]):
        chart = chart_view.chart()
        existing = getattr(self, series_attr, []) or []
        for s in existing:
            try:
                chart.removeSeries(s)
            except Exception:
                pass

        from PyQt5.QtChart import QSplineSeries, QLineSeries, QAreaSeries, QScatterSeries
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
        accent = QColor("#0078D4")
        point_fill = QColor("#49C6FF")
        point_border = QColor(20, 20, 20)
        stem_pen = QPen(QColor(140, 140, 140, 90), 1, Qt.DotLine)
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
            grad.setColorAt(0.0, QColor(0, 120, 212, 90))
            grad.setColorAt(1.0, QColor(0, 120, 212, 0))
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

            upper.hovered.connect(lambda p, st, tv=tooltips, cv=chart_view: self._on_line_hovered(p, st, tv, cv))
            points.hovered.connect(lambda p, st, tv=tooltips, cv=chart_view: self._on_line_hovered(p, st, tv, cv))

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
        elif "error" in low or low.startswith("api error") or low.startswith("authentication"):
            level = "error"
        elif "disconnected" in low or "timeout" in low:
            level = "warning"
        self._notify(level, "Dashboard", t, duration=4500)

    def _populate_years_from_cache(self):
        years = []
        if self.db_manager and hasattr(self.db_manager, "get_cached_years"):
            try:
                years = self.db_manager.get_cached_years(source="supabase")
            except Exception:
                years = []

        current_year_str = str(datetime.now().year)

        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            self.rate_year_combo.blockSignals(True)
            self.rate_year_combo.clear()
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            self.elec_year_combo.blockSignals(True)
            self.elec_year_combo.clear()
        self.owner_room_year_combo.blockSignals(True)
        self.owner_room_year_combo.clear()
        if years:
            for y in years:
                self.year_combo.addItem(str(y))
                if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
                    self.rate_year_combo.addItem(str(y))
                if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
                    self.elec_year_combo.addItem(str(y))
                self.owner_room_year_combo.addItem(str(y))
            self.year_combo.setEnabled(True)
            if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
                self.rate_year_combo.setEnabled(True)
            if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
                self.elec_year_combo.setEnabled(True)
            self.owner_room_year_combo.setEnabled(True)
            # Default each combo to current year; fall back to most recent (index 0, DESC)
            if self.year_combo.findText(current_year_str) >= 0:
                self.year_combo.setCurrentText(current_year_str)
            else:
                self.year_combo.setCurrentIndex(0)
            if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
                if self.rate_year_combo.findText(current_year_str) >= 0:
                    self.rate_year_combo.setCurrentText(current_year_str)
                else:
                    self.rate_year_combo.setCurrentIndex(0)
            if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
                if self.elec_year_combo.findText(current_year_str) >= 0:
                    self.elec_year_combo.setCurrentText(current_year_str)
                else:
                    self.elec_year_combo.setCurrentIndex(0)
            if self.owner_room_year_combo.findText(current_year_str) >= 0:
                self.owner_room_year_combo.setCurrentText(current_year_str)
            else:
                self.owner_room_year_combo.setCurrentIndex(0)
        else:
            self.year_combo.addItem("No years")
            self.year_combo.setEnabled(False)
            if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
                self.rate_year_combo.addItem("No years")
                self.rate_year_combo.setEnabled(False)
            if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
                self.elec_year_combo.addItem("No years")
                self.elec_year_combo.setEnabled(False)
            self.owner_room_year_combo.addItem("No years")
            self.owner_room_year_combo.setEnabled(False)
        self.year_combo.blockSignals(False)
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            self.rate_year_combo.blockSignals(False)
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            self.elec_year_combo.blockSignals(False)
        self.owner_room_year_combo.blockSignals(False)

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
        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            self._set_status("Supabase not configured. Set it in Supabase Config tab, then return here.")
            return

        if self._years_worker and self._years_worker.isRunning():
            return

        self._set_status("Fetching available years from Supabase…")
        self._years_worker = FetchSupabaseAvailableYearsWorker(supabase_manager)
        self._years_worker.years_fetched.connect(self._on_years_fetched)
        self._years_worker.error_occurred.connect(self._on_years_error)
        self._years_worker.start()

    def _on_years_fetched(self, years: list):
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

        current_year_str = str(datetime.now().year)
        years_str = [str(y) for y in years_int]

        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            self.rate_year_combo.blockSignals(True)
            self.rate_year_combo.clear()
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            self.elec_year_combo.blockSignals(True)
            self.elec_year_combo.clear()
        self.owner_room_year_combo.blockSignals(True)
        self.owner_room_year_combo.clear()
        for y in years_int:
            self.year_combo.addItem(str(y))
            if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
                self.rate_year_combo.addItem(str(y))
            if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
                self.elec_year_combo.addItem(str(y))
            self.owner_room_year_combo.addItem(str(y))
        self.year_combo.setEnabled(True)
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            self.rate_year_combo.setEnabled(True)
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            self.elec_year_combo.setEnabled(True)
        self.owner_room_year_combo.setEnabled(True)
        # Default each combo to current year; fall back to most recent (index 0, DESC)
        if current_year_str in years_str:
            self.year_combo.setCurrentText(current_year_str)
        else:
            self.year_combo.setCurrentIndex(0)
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            if current_year_str in years_str:
                self.rate_year_combo.setCurrentText(current_year_str)
            else:
                self.rate_year_combo.setCurrentIndex(0)
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            if current_year_str in years_str:
                self.elec_year_combo.setCurrentText(current_year_str)
            else:
                self.elec_year_combo.setCurrentIndex(0)
        if current_year_str in years_str:
            self.owner_room_year_combo.setCurrentText(current_year_str)
        else:
            self.owner_room_year_combo.setCurrentIndex(0)
        self.year_combo.blockSignals(False)
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            self.rate_year_combo.blockSignals(False)
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            self.elec_year_combo.blockSignals(False)
        self.owner_room_year_combo.blockSignals(False)

        # Determine the selected years from each combo for initial sync
        bill_year_str = self.year_combo.currentText()
        selected_year = int(bill_year_str) if bill_year_str.isdigit() else years_int[0]
        owner_year_str = self.owner_room_year_combo.currentText()
        selected_owner_room_year = int(owner_year_str) if owner_year_str.isdigit() else years_int[0]

        self._set_status("")
        self._sync_year_async(selected_year)
        self._sync_owner_room_year_async(selected_owner_room_year)

    def _on_years_error(self, msg: str):
        if msg == "PAUSED_PROJECT":
            self._set_status("Supabase project is paused.")
        else:
            self._set_status(msg)

    def _on_refresh_clicked(self):
        sender = self.sender()
        # Determine which button triggered the refresh and use that section's year
        if sender == self.rate_refresh_btn and hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            t = self.rate_year_combo.currentText().strip()
            year = int(t) if t.isdigit() else None
        elif sender == self.elec_refresh_btn and hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
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
        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return
        if self._sync_worker and self._sync_worker.isRunning():
            return

        self._set_status("Syncing year from Supabase…")
        self._sync_worker = SyncSupabaseMainCalculationsYearWorker(supabase_manager, self._db_path, year)
        self._sync_worker.sync_finished.connect(self._on_sync_finished)
        self._sync_worker.error_occurred.connect(self._on_sync_error)
        self._sync_worker.start()

    def _on_sync_finished(self, year: int):
        self._set_status("")
        # Refresh all sections using their own combo's selected year
        self._render_year_from_cache(year)

    def _on_sync_error(self, msg: str):
        if msg == "PAUSED_PROJECT":
            self._set_status("Supabase project is paused.")
        else:
            self._set_status(msg)

    def _render_year_from_cache(self, year: int):
        self._active_year = int(year)
        totals = {}
        if self.db_manager and hasattr(self.db_manager, "get_cached_monthly_totals"):
            try:
                totals = self.db_manager.get_cached_monthly_totals(year, source="supabase")
            except Exception:
                totals = {}
        values = []
        for m in MONTHS:
            values.append(float(totals.get(m, 0.0) or 0.0))
        self._update_meta(year)
        self._render_values(values)
        # When called during global refresh, render rate/elec using their own combo years
        # Read rate combo year
        if hasattr(self, "rate_year_combo") and self.rate_year_combo is not None:
            rate_year_str = self.rate_year_combo.currentText()
            rate_year = int(rate_year_str) if rate_year_str.isdigit() else year
            self._render_rate_from_cache(rate_year)
        # Read elec combo year
        if hasattr(self, "elec_year_combo") and self.elec_year_combo is not None:
            elec_year_str = self.elec_year_combo.currentText()
            elec_year = int(elec_year_str) if elec_year_str.isdigit() else year
            self._render_elec_from_cache(elec_year)

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
            )
            return

        if isinstance(self._chart_widget, SimpleLineChartWidget):
            self._chart_widget.set_data(MONTHS, values, tooltips=self._current_tooltips)

    def _render_rate_from_cache(self, year: int):
        rates = {}
        if self.db_manager and hasattr(self.db_manager, "get_cached_monthly_per_unit_cost"):
            try:
                rates = self.db_manager.get_cached_monthly_per_unit_cost(year, source="supabase")
            except Exception:
                rates = {}

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
            self._apply_qt_line_chart(
                chart_view=self._rate_chart_view,
                axis_x=self._rate_axis_x,
                axis_y=self._rate_axis_y,
                series_attr="_rate_series",
                raw_values=self._rate_raw_values,
                tooltips=self._rate_tooltips,
            )
            return

        if isinstance(self._rate_chart_widget, SimpleLineChartWidget):
            self._rate_chart_widget.set_data(MONTHS, self._rate_values, tooltips=self._rate_tooltips)

    def _update_rate_kpis(self, raw_values: list[float | None]):
        year = int(getattr(self, "_active_year", datetime.now().year))
        now = datetime.now()

        current_idx = 11
        prev_idx = 10
        if year == now.year:
            current_idx = max(0, min(11, now.month - 1))
            prev_idx = max(0, current_idx - 1)
        else:
            present = [i for i, v in enumerate(raw_values or []) if v is not None]
            if present:
                current_idx = present[-1]
                prev_present = [i for i in present if i < current_idx]
                prev_idx = prev_present[-1] if prev_present else max(0, current_idx - 1)

        cv = raw_values[current_idx] if 0 <= current_idx < len(raw_values) else None
        pv = raw_values[prev_idx] if 0 <= prev_idx < len(raw_values) else None

        self.rate_kpi_current._kpi_value_label.setText(f"{MONTHS[current_idx][:3]} · {self._fmt_rate(cv)}")
        self.rate_kpi_prev._kpi_value_label.setText(f"{MONTHS[prev_idx][:3]} · {self._fmt_rate(pv)}")

        consider = [i for i, v in enumerate(raw_values or []) if v is not None]
        max_idx = max(consider, key=lambda i: float(raw_values[i] or 0.0)) if consider else None
        min_idx = min(consider, key=lambda i: float(raw_values[i] or 0.0)) if consider else None

        self.rate_kpi_high._kpi_value_label.setText(
            f"{MONTHS[max_idx][:3]} · {self._fmt_rate(raw_values[max_idx])}" if max_idx is not None else "—"
        )
        self.rate_kpi_low._kpi_value_label.setText(
            f"{MONTHS[min_idx][:3]} · {self._fmt_rate(raw_values[min_idx])}" if min_idx is not None else "—"
        )

        self.rate_kpi_current.setToolTip(f"Per unit cost for {MONTHS[current_idx]} {year}")
        self.rate_kpi_prev.setToolTip(f"Per unit cost for {MONTHS[prev_idx]} {year}")
        if max_idx is not None:
            self.rate_kpi_high.setToolTip(f"Highest per unit cost in {year}: {MONTHS[max_idx]}")
        if min_idx is not None:
            self.rate_kpi_low.setToolTip(f"Lowest per unit cost in {year}: {MONTHS[min_idx]}")

    def _render_elec_from_cache(self, year: int):
        bills = {}
        if self.db_manager and hasattr(self.db_manager, "get_cached_monthly_total_electricity_bills"):
            try:
                bills = self.db_manager.get_cached_monthly_total_electricity_bills(year, source="supabase")
            except Exception:
                bills = {}

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
                tips.append(f"{m}\nTotal Elec. Bill: TK {fv:,.2f}" if fv is not None else f"{m}\nTotal Elec. Bill: —")

        self._elec_raw_values = raw[:12]
        self._elec_values = vals[:12]
        self._elec_tooltips = tips[:12]
        self._update_elec_kpis(self._elec_raw_values)

        if hasattr(self, "_elec_qtchart") and self._elec_qtchart:
            self._apply_qt_line_chart(
                chart_view=self._elec_chart_view,
                axis_x=self._elec_axis_x,
                axis_y=self._elec_axis_y,
                series_attr="_elec_series",
                raw_values=self._elec_raw_values,
                tooltips=self._elec_tooltips,
            )
            return

        if isinstance(self._elec_chart_widget, SimpleLineChartWidget):
            self._elec_chart_widget.set_data(MONTHS, self._elec_values, tooltips=self._elec_tooltips)

    def _update_elec_kpis(self, raw_values: list[float | None]):
        year = int(getattr(self, "_active_year", datetime.now().year))
        now = datetime.now()

        current_idx = 11
        prev_idx = 10
        if year == now.year:
            current_idx = max(0, min(11, now.month - 1))
            prev_idx = max(0, current_idx - 1)
        else:
            present = [i for i, v in enumerate(raw_values or []) if v is not None]
            if present:
                current_idx = present[-1]
                prev_present = [i for i in present if i < current_idx]
                prev_idx = prev_present[-1] if prev_present else max(0, current_idx - 1)

        cv = raw_values[current_idx] if 0 <= current_idx < len(raw_values) else None
        pv = raw_values[prev_idx] if 0 <= prev_idx < len(raw_values) else None

        def _fmt_elec(v: float | None) -> str:
            if v is None:
                return "—"
            try:
                return f"TK {float(v):,.0f}"
            except Exception:
                return "—"

        self.elec_kpi_current._kpi_value_label.setText(f"{MONTHS[current_idx][:3]} · {_fmt_elec(cv)}")
        self.elec_kpi_prev._kpi_value_label.setText(f"{MONTHS[prev_idx][:3]} · {_fmt_elec(pv)}")

        consider = [i for i, v in enumerate(raw_values or []) if v is not None]
        max_idx = max(consider, key=lambda i: float(raw_values[i] or 0.0)) if consider else None
        min_idx = min(consider, key=lambda i: float(raw_values[i] or 0.0)) if consider else None

        self.elec_kpi_high._kpi_value_label.setText(
            f"{MONTHS[max_idx][:3]} · {_fmt_elec(raw_values[max_idx])}" if max_idx is not None else "—"
        )
        self.elec_kpi_low._kpi_value_label.setText(
            f"{MONTHS[min_idx][:3]} · {_fmt_elec(raw_values[min_idx])}" if min_idx is not None else "—"
        )

        self.elec_kpi_current.setToolTip(f"Total electricity bill for {MONTHS[current_idx]} {year}")
        self.elec_kpi_prev.setToolTip(f"Total electricity bill for {MONTHS[prev_idx]} {year}")
        if max_idx is not None:
            self.elec_kpi_high.setToolTip(f"Highest total electricity bill in {year}: {MONTHS[max_idx]}")
        if min_idx is not None:
            self.elec_kpi_low.setToolTip(f"Lowest total electricity bill in {year}: {MONTHS[min_idx]}")

    def _build_tooltips(self, values: list[float]) -> list[str]:
        out = []
        for i, m in enumerate(MONTHS):
            v = float(values[i] or 0.0)
            prev = float(values[i - 1] or 0.0) if i > 0 else 0.0
            d = v - prev if i > 0 else 0.0
            if i == 0:
                out.append(f"{m}\n{self._fmt_tk(v)}")
            else:
                out.append(f"{m}\n{self._fmt_tk(v)}\n{self._fmt_delta(d)}")
        return out

    def _update_kpis(self, values: list[float]):
        year = int(getattr(self, "_active_year", datetime.now().year))
        now = datetime.now()

        current_idx = 11
        prev_idx = 10
        if year == now.year:
            current_idx = max(0, min(11, now.month - 1))
            prev_idx = max(0, current_idx - 1)
        else:
            present = [i for i, v in enumerate(values or []) if float(v or 0.0) > 0.0]
            if present:
                current_idx = present[-1]
                prev_present = [i for i in present if i < current_idx]
                prev_idx = prev_present[-1] if prev_present else max(0, current_idx - 1)

        def _month_label(idx: int) -> str:
            try:
                return MONTHS[idx][:3]
            except Exception:
                return "—"

        self.kpi_total._kpi_value_label.setText(f"{_month_label(current_idx)} · {self._fmt_tk(values[current_idx])}")
        self.kpi_avg._kpi_value_label.setText(f"{_month_label(prev_idx)} · {self._fmt_tk(values[prev_idx])}")

        if year == now.year:
            consider = [i for i in range(0, current_idx + 1) if float(values[i] or 0.0) > 0.0]
        else:
            consider = [i for i, v in enumerate(values or []) if float(v or 0.0) > 0.0]
        if not consider:
            consider = list(range(len(values or [])))

        max_idx = max(consider, key=lambda i: float(values[i] or 0.0)) if consider else None
        min_idx = min(consider, key=lambda i: float(values[i] or 0.0)) if consider else None

        self.kpi_high._kpi_value_label.setText(
            f"{MONTHS[max_idx][:3]} · {self._fmt_tk(values[max_idx])}" if max_idx is not None else "—"
        )
        self.kpi_low._kpi_value_label.setText(
            f"{MONTHS[min_idx][:3]} · {self._fmt_tk(values[min_idx])}" if min_idx is not None else "—"
        )

        self.kpi_total.setToolTip(f"Bill for {MONTHS[current_idx]} {year}")
        self.kpi_avg.setToolTip(f"Bill for {MONTHS[prev_idx]} {year}")
        if max_idx is not None:
            self.kpi_high.setToolTip(f"Highest month in {year}: {MONTHS[max_idx]}")
        if min_idx is not None:
            self.kpi_low.setToolTip(f"Lowest month in {year}: {MONTHS[min_idx]}")

    def _update_meta(self, year: int):
        last_sync = None
        if self.db_manager:
            try:
                row = self.db_manager.execute_query(
                    "SELECT MAX(synced_at) AS last_sync FROM main_calculations_cache WHERE source = ? AND year = ?",
                    ("supabase", int(year)),
                    fetch_one=True,
                )
                if row:
                    last_sync = row["last_sync"]
            except Exception:
                last_sync = None
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
        elif "error" in low or low.startswith("api error") or low.startswith("authentication"):
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
        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return

        if self._owner_room_main_sync_worker and self._owner_room_main_sync_worker.isRunning():
            return

        self._set_owner_room_status("Syncing owner data from Supabase…")
        self._owner_room_main_sync_worker = SyncSupabaseMainCalculationsYearWorker(supabase_manager, self._db_path, year)
        self._owner_room_main_sync_worker.sync_finished.connect(self._on_owner_room_main_sync_finished)
        self._owner_room_main_sync_worker.error_occurred.connect(self._on_owner_room_main_sync_error)
        self._owner_room_main_sync_worker.start()

        self._sync_room_year_async(year)
        if self.scope_combo.currentText().strip() == "Room":
            self._sync_rentals_cache_async()

    def _on_owner_room_main_sync_finished(self, year: int):
        self._set_owner_room_status("")
        self._render_owner_room_from_cache(year)

    def _on_owner_room_main_sync_error(self, msg: str):
        if msg == "PAUSED_PROJECT":
            self._set_owner_room_status("Supabase project is paused.")
        else:
            self._set_owner_room_status(msg)

    def _sync_room_year_async(self, year: int):
        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return
        if self._room_sync_worker and self._room_sync_worker.isRunning():
            return

        self._set_owner_room_status("Syncing room bills from Supabase…")
        self._room_sync_worker = SyncSupabaseRoomCalculationsYearWorker(supabase_manager, self._db_path, year)
        self._room_sync_worker.sync_finished.connect(self._on_room_sync_finished)
        self._room_sync_worker.error_occurred.connect(self._on_room_sync_error)
        self._room_sync_worker.start()

    def _on_room_sync_finished(self, year: int):
        self._set_owner_room_status("")
        self._populate_rooms_from_cache()
        self._render_owner_room_from_cache(year)

    def _on_room_sync_error(self, msg: str):
        if msg == "PAUSED_PROJECT":
            self._set_owner_room_status("Supabase project is paused.")
        else:
            self._set_owner_room_status(msg)

    def _sync_rentals_cache_async(self):
        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            return
        if not self._db_path:
            return
        if self._rentals_sync_worker and self._rentals_sync_worker.isRunning():
            return

        self._rentals_sync_worker = SyncSupabaseRentalRecordsCacheWorker(supabase_manager, self._db_path)
        self._rentals_sync_worker.sync_finished.connect(self._on_rentals_sync_finished)
        self._rentals_sync_worker.error_occurred.connect(self._on_rentals_sync_error)
        self._rentals_sync_worker.start()

    def _on_rentals_sync_finished(self):
        year = self._selected_owner_room_year()
        if year is not None:
            self._render_owner_room_from_cache(year)

    def _on_rentals_sync_error(self, msg: str):
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
                self._render_owner_room_values([0.0] * 12, self._build_owner_room_tooltips(empty_raw, year, room_name, mode="Room"), empty_raw)
                return
            month_map = {}
            try:
                month_map = self.db_manager.get_cached_monthly_room_unit_bills(year, room_name, source="supabase") if self.db_manager else {}
            except Exception:
                month_map = {}
            vals_raw = [month_map.get(m) for m in MONTHS]
            vals = [float(v or 0.0) if v is not None else 0.0 for v in vals_raw]
            tips = self._build_owner_room_tooltips(vals_raw, year, room_name, mode="Room")
            self._render_owner_room_values(vals, tips, vals_raw)
            return

        self._update_owner_room_meta(year, mode="Owner")
        month_map = {}
        try:
            month_map = self.db_manager.get_cached_monthly_owner_unit_bills(year, source="supabase") if self.db_manager else {}
        except Exception:
            month_map = {}
        vals_raw = [month_map.get(m) for m in MONTHS]
        vals = [float(v or 0.0) if v is not None else 0.0 for v in vals_raw]
        tips = self._build_owner_room_tooltips(vals_raw, year, "", mode="Owner")
        self._render_owner_room_values(vals, tips, vals_raw)

    def _render_owner_room_values(self, values: list[float], tooltips: list[str], raw_values: list | None = None):
        values = (values or [])[:12]
        if len(values) < 12:
            values = values + [0.0] * (12 - len(values))

        self._owner_room_values = values[:]
        self._owner_room_tooltips = (tooltips or [""] * 12)[:12]
        self._owner_room_raw_values = (raw_values or values)[:12]
        self._update_owner_room_kpis(values, tooltips, self._owner_room_raw_values)

        if self._owner_room_qtchart:
            self._apply_qt_line_chart(
                chart_view=self._owner_room_chart_view,
                axis_x=self._owner_room_axis_x,
                axis_y=self._owner_room_axis_y,
                series_attr="_owner_room_line_series",
                raw_values=self._owner_room_raw_values,
                tooltips=self._owner_room_tooltips,
            )
            return

        if isinstance(self._owner_room_chart_widget, SimpleLineChartWidget):
            self._owner_room_chart_widget.set_data(MONTHS, values, tooltips=self._owner_room_tooltips)

    def _build_owner_room_tooltips(self, raw_values: list[float | None], year: int, room_name: str, mode: str, room_water_values: list[float | None] | None = None) -> list[str]:
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
                tenant = self._tenant_for_month(year, i + 1, room_name)
                tenant_line = f"Tenant: {tenant}" if tenant else "Tenant: —"
                if delta_text:
                    out.append(f"{m}\nElectricity: {bill_text}\n{delta_text}\n{tenant_line}")
                else:
                    out.append(f"{m}\nElectricity: {bill_text}\n{tenant_line}")
            else:
                label = "Owner Unit Bill"
                if delta_text:
                    out.append(f"{m}\n{label}: {bill_text}\n{delta_text}")
                else:
                    out.append(f"{m}\n{label}: {bill_text}")
        return out

    def _update_owner_room_kpis(self, values: list[float], tooltips: list[str], raw_values: list):
        valid = []
        for v in raw_values or []:
            if v is None:
                continue
            try:
                valid.append(float(v))
            except Exception:
                continue

        year = int(getattr(self, "_owner_room_active_year", datetime.now().year))
        now = datetime.now()

        current_idx = None
        prev_idx = None
        if year == now.year:
            current_idx = max(0, min(11, now.month - 1))
            prev_idx = max(0, current_idx - 1)
        else:
            present_idx = [i for i, v in enumerate(raw_values) if v is not None]
            if present_idx:
                current_idx = present_idx[-1]
                prev_present = [i for i in present_idx if i < current_idx]
                prev_idx = prev_present[-1] if prev_present else None

        max_idx = None
        min_idx = None
        try:
            present_idx = [i for i, v in enumerate(raw_values) if v is not None]
            max_idx = max(present_idx, key=lambda i: float(raw_values[i])) if present_idx else None
            min_idx = min(present_idx, key=lambda i: float(raw_values[i])) if present_idx else None
        except Exception:
            max_idx = None
            min_idx = None

        def _value_at(idx: int | None) -> float | None:
            if idx is None:
                return None
            if 0 <= idx < len(raw_values):
                v = raw_values[idx]
                return float(v) if v is not None else None
            return None

        cv = _value_at(current_idx)
        pv = _value_at(prev_idx)

        if current_idx is not None:
            self.owner_kpi_total._kpi_value_label.setText(f"{MONTHS[current_idx][:3]} · {self._fmt_tk(cv)}" if cv is not None else f"{MONTHS[current_idx][:3]} · —")
            self.owner_kpi_total.setToolTip(f"Bill for {MONTHS[current_idx]} {year}")
        else:
            self.owner_kpi_total._kpi_value_label.setText("—")
            self.owner_kpi_total.setToolTip("No data")

        if prev_idx is not None:
            self.owner_kpi_avg._kpi_value_label.setText(f"{MONTHS[prev_idx][:3]} · {self._fmt_tk(pv)}" if pv is not None else f"{MONTHS[prev_idx][:3]} · —")
            self.owner_kpi_avg.setToolTip(f"Bill for {MONTHS[prev_idx]} {year}")
        else:
            self.owner_kpi_avg._kpi_value_label.setText("—")
            self.owner_kpi_avg.setToolTip("No previous month data")

        if max_idx is not None:
            self.owner_kpi_high._kpi_value_label.setText(f"{MONTHS[max_idx][:3]} · {self._fmt_tk(values[max_idx])}")
        else:
            self.owner_kpi_high._kpi_value_label.setText("—")

        if min_idx is not None:
            self.owner_kpi_low._kpi_value_label.setText(f"{MONTHS[min_idx][:3]} · {self._fmt_tk(values[min_idx])}")
        else:
            self.owner_kpi_low._kpi_value_label.setText("—")

        if max_idx is not None:
            self.owner_kpi_high.setToolTip(f"Highest month in {year}: {MONTHS[max_idx]}")
        if min_idx is not None:
            self.owner_kpi_low.setToolTip(f"Lowest month in {year}: {MONTHS[min_idx]}")

    def _update_owner_room_meta(self, year: int, mode: str):
        last_sync = None
        if self.db_manager:
            try:
                table = "main_calculations_cache" if mode == "Owner" else "room_calculations_cache"
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
            self.owner_room_meta_label.setText(f"Source: Supabase Cache · Last sync: {last_sync}")
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

    def _tenant_for_month(self, year: int, month: int, room_name: str) -> str | None:
        if not self.db_manager:
            return None

        records = []
        for key in self._get_room_number_candidates(room_name):
            try:
                records = self.db_manager.get_rental_records_for_room(key)
            except Exception:
                records = []
            if records:
                break
        if not records:
            return None

        entries = []
        for r in records:
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

            entries.append({"tenant": tenant_name, "sy": sy, "sm": sm, "eym": end_parsed})

        if not entries:
            return None

        entries.sort(key=lambda e: (e["sy"], e["sm"]))
        for i, e in enumerate(entries):
            end_ym = e["eym"]
            if i + 1 < len(entries):
                ny, nm = entries[i + 1]["sy"], entries[i + 1]["sm"]
                by, bm = self._month_before(ny, nm)
                next_end = (by, bm)
                if end_ym is None or next_end < end_ym:
                    end_ym = next_end
            e["eym"] = end_ym

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
