from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QCursor, QFontMetrics, QPainter, QPen
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QToolTip
from qfluentwidgets import CardWidget, ComboBox, FluentIcon, PushButton, TitleLabel, BodyLabel, CaptionLabel, IconWidget, isDarkTheme

from src.ui.background_workers import FetchSupabaseAvailableYearsWorker, SyncSupabaseMainCalculationsYearWorker


MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class SimpleBarChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels = MONTHS
        self._values = [0.0] * 12
        self._tooltips = [""] * 12
        self._max_value = 0.0
        self._bar_rects = []
        self._hover_index = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(260)
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
        for i, r in enumerate(self._bar_rects):
            if r.contains(pos):
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

        rect = self.rect().adjusted(18, 18, -18, -18)
        if rect.width() <= 0 or rect.height() <= 0:
            return

        dark = isDarkTheme()
        bg = QColor(39, 39, 39) if dark else QColor(250, 250, 250)
        grid = QColor(80, 80, 80) if dark else QColor(210, 210, 210)
        bar = QColor(108, 92, 231) if dark else QColor(86, 70, 210)
        bar_hi = QColor(0, 120, 212) if dark else QColor(0, 95, 180)
        text = QColor(230, 230, 230) if dark else QColor(30, 30, 30)

        painter.fillRect(rect, bg)

        left_pad = 72
        bottom_pad = 38
        top_pad = 10
        plot = rect.adjusted(left_pad, top_pad, -10, -bottom_pad)

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
        gap = 6
        bar_w = max(6, int((plot.width() - gap * (n - 1)) / n))

        max_idx = None
        try:
            max_idx = max(range(n), key=lambda i: float(values[i]))
        except Exception:
            max_idx = None

        self._bar_rects = []
        painter.setPen(Qt.NoPen)
        for i, v in enumerate(values):
            x = plot.left() + i * (bar_w + gap)
            h = int((float(v) / float(max_v)) * plot.height()) if max_v > 0 else 0
            y = plot.bottom() - h
            r = plot.adjusted(0, 0, 0, 0)
            br = r.__class__(x, y, bar_w, h)
            self._bar_rects.append(br)
            painter.setBrush(bar_hi if (max_idx is not None and i == max_idx) else bar)
            if self._hover_index == i:
                painter.setBrush(QColor(155, 140, 255) if dark else QColor(120, 105, 235))
            painter.drawRoundedRect(x, y, bar_w, h, 6, 6)

        painter.setPen(QPen(text, 1))
        fm = QFontMetrics(painter.font())
        label_step = 1
        if n > 12:
            label_step = 2
        for i, label in enumerate(self._labels[:n]):
            if i % label_step != 0:
                continue
            short = label[:3]
            x = plot.left() + i * (bar_w + gap) + int(bar_w / 2)
            y = plot.bottom() + 18
            w = fm.horizontalAdvance(short)
            painter.drawText(x - int(w / 2), y, short)

        painter.setPen(QPen(text, 1))
        for i in range(5):
            frac = 1.0 - (i / 4.0)
            val = frac * max_v
            y = plot.top() + int(i * plot.height() / 4)
            s = f"TK {val:,.0f}"
            w = fm.horizontalAdvance(s)
            painter.drawText(plot.left() - w - 8, y + int(fm.ascent() / 2), s)


class DashboardTab(QWidget):
    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.db_manager = getattr(self.main_window, "db_manager", None)
        self._db_path = getattr(self.db_manager, "db_name", None) if self.db_manager else None

        self._years_worker = None
        self._sync_worker = None
        self._chart_view = None
        self._chart_widget = None
        self._supabase_poll_tries = 0
        self._supabase_poll_timer = None
        self._current_values = [0.0] * 12
        self._current_tooltips = [""] * 12

        self._build_ui()
        self._populate_years_from_cache()
        self._start_supabase_year_poll()

    def _start_supabase_year_poll(self):
        if self._supabase_poll_timer is not None:
            return
        self._supabase_poll_timer = QTimer(self)
        self._supabase_poll_timer.setInterval(1200)
        self._supabase_poll_timer.timeout.connect(self._poll_supabase_years)
        self._supabase_poll_timer.start()

    def _poll_supabase_years(self):
        if self.year_combo.isEnabled() and self.year_combo.count() > 0:
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
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        title = TitleLabel("Dashboard")
        root.addWidget(title)
        subtitle = CaptionLabel("Overview and trends")
        subtitle.setTextColor(QColor(180, 180, 180) if isDarkTheme() else QColor(90, 90, 90))
        root.addWidget(subtitle)

        card = CardWidget(self)
        card.setObjectName("yearlyBillCard")
        card.setStyleSheet("""
            CardWidget#yearlyBillCard {
                border-radius: 12px;
            }
            CardWidget#yearlyBillCard:hover {
                border: 1px solid rgba(108, 92, 231, 140);
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        top_row = QHBoxLayout()
        icon = IconWidget(FluentIcon.SHOPPING_CART)
        icon.setFixedSize(18, 18)
        top_row.addWidget(icon)
        header = TitleLabel("Yearly Total Bill")
        top_row.addWidget(header)
        hint = CaptionLabel("Hover bars to see details")
        hint.setTextColor(QColor(160, 160, 160) if isDarkTheme() else QColor(110, 110, 110))
        top_row.addWidget(hint)
        top_row.addStretch(1)

        self.year_combo = ComboBox()
        self.year_combo.setMinimumWidth(110)
        self.year_combo.currentIndexChanged.connect(self._on_year_changed)
        self.year_combo.setToolTip("Years are fetched from Supabase and cached locally")
        top_row.addWidget(self.year_combo)

        self.refresh_btn = PushButton("Refresh")
        self.refresh_btn.setIcon(FluentIcon.SYNC.icon(color=QColor(255, 255, 255)))
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.refresh_btn.setToolTip("Sync from Supabase and update local cache")
        top_row.addWidget(self.refresh_btn)

        card_layout.addLayout(top_row)

        meta_row = QHBoxLayout()
        self.meta_label = CaptionLabel("")
        self.meta_label.setTextColor(QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110))
        meta_row.addWidget(self.meta_label)
        meta_row.addStretch(1)
        card_layout.addLayout(meta_row)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self.kpi_total = self._create_kpi_card("Year Total")
        self.kpi_avg = self._create_kpi_card("Avg / Month")
        self.kpi_high = self._create_kpi_card("Highest Month")
        self.kpi_low = self._create_kpi_card("Lowest Month")
        kpi_row.addWidget(self.kpi_total, 1)
        kpi_row.addWidget(self.kpi_avg, 1)
        kpi_row.addWidget(self.kpi_high, 1)
        kpi_row.addWidget(self.kpi_low, 1)
        card_layout.addLayout(kpi_row)

        self.status_label = BodyLabel("")
        self.status_label.setTextColor(QColor(200, 200, 200))
        card_layout.addWidget(self.status_label)

        self._chart_widget = self._create_chart_widget()
        card_layout.addWidget(self._chart_widget, 1)

        root.addWidget(card, 1)

    def _create_kpi_card(self, title: str):
        w = CardWidget(self)
        w.setObjectName("kpiCard")
        w.setStyleSheet("""
            CardWidget#kpiCard {
                border-radius: 10px;
            }
            CardWidget#kpiCard:hover {
                border: 1px solid rgba(108, 92, 231, 120);
            }
        """)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        t = CaptionLabel(title)
        t.setTextColor(QColor(170, 170, 170) if isDarkTheme() else QColor(110, 110, 110))
        v = TitleLabel("—")
        lay.addWidget(t)
        lay.addWidget(v)
        w._kpi_value_label = v
        return w

    def _create_chart_widget(self):
        try:
            from PyQt5.QtChart import QChartView, QChart, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis

            self._qtchart = (QChartView, QChart, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis)
            view = QChartView()
            view.setRenderHint(QPainter.Antialiasing)
            view.setMinimumHeight(260)
            self._chart_view = view
            self._init_qtchart()
            return view
        except Exception:
            self._qtchart = None
            return SimpleBarChartWidget(self)

    def _init_qtchart(self):
        QChartView, QChart, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis = self._qtchart

        self._bar_set = QBarSet("Total")
        for _ in MONTHS:
            self._bar_set.append(0.0)
        self._bar_set.setColor(QColor(108, 92, 231))
        self._bar_set.hovered.connect(self._on_bar_hovered)

        series = QBarSeries()
        series.append(self._bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(False)
        chart.setBackgroundBrush(QColor(43, 43, 43))
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setAnimationDuration(550)

        axis_x = QBarCategoryAxis()
        axis_x.append([m[:3] for m in MONTHS])
        axis_x.setLabelsColor(QColor(220, 220, 220))

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor(220, 220, 220))
        axis_y.setGridLineColor(QColor(80, 80, 80))
        axis_y.setMin(0.0)
        axis_y.setMax(1.0)
        axis_y.setLabelFormat("TK %.0f")

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        self._axis_y = axis_y
        self._series = series
        self._chart_view.setChart(chart)

    def _fmt_tk(self, v: float) -> str:
        try:
            return f"TK {float(v):,.0f}"
        except Exception:
            return "TK 0"

    def _fmt_delta(self, v: float) -> str:
        try:
            sign = "+" if v >= 0 else "-"
            return f"Δ TK {sign}{abs(float(v)):,.0f}"
        except Exception:
            return "Δ TK 0"

    def _set_status(self, text: str):
        self.status_label.setText(text or "")

    def _populate_years_from_cache(self):
        years = []
        if self.db_manager and hasattr(self.db_manager, "get_cached_years"):
            try:
                years = self.db_manager.get_cached_years(source="supabase")
            except Exception:
                years = []

        self.year_combo.clear()
        if years:
            for y in years:
                self.year_combo.addItem(str(y))
            self.year_combo.setEnabled(True)
        else:
            self.year_combo.addItem("No years")
            self.year_combo.setEnabled(False)

        if years:
            self._render_year_from_cache(years[0])
        else:
            self._set_status("No cached years yet.")
            self._render_values([0.0] * 12)

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

        current = self.year_combo.currentText()
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        for y in years_int:
            self.year_combo.addItem(str(y))
        self.year_combo.setEnabled(True)
        self.year_combo.blockSignals(False)

        if current and current in [str(y) for y in years_int]:
            self.year_combo.setCurrentText(current)
            selected_year = int(current)
        else:
            self.year_combo.setCurrentIndex(0)
            selected_year = years_int[0]

        self._set_status("")
        self._sync_year_async(selected_year)

    def _on_years_error(self, msg: str):
        if msg == "PAUSED_PROJECT":
            self._set_status("Supabase project is paused.")
        else:
            self._set_status(msg)

    def _on_refresh_clicked(self):
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
        self._render_year_from_cache(year)
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
        self._render_year_from_cache(year)

    def _on_sync_error(self, msg: str):
        if msg == "PAUSED_PROJECT":
            self._set_status("Supabase project is paused.")
        else:
            self._set_status(msg)

    def _render_year_from_cache(self, year: int):
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

    def _render_values(self, values: list[float]):
        values = (values or [])[:12]
        if len(values) < 12:
            values = values + [0.0] * (12 - len(values))

        self._current_values = values[:]
        self._current_tooltips = self._build_tooltips(values)
        self._update_kpis(values)

        if self._qtchart:
            for i, v in enumerate(values):
                self._bar_set.replace(i, float(v))
            max_v = max(values) if values else 0.0
            self._axis_y.setMax(max(1.0, max_v * 1.15))
            return

        if isinstance(self._chart_widget, SimpleBarChartWidget):
            self._chart_widget.set_data(MONTHS, values, tooltips=self._current_tooltips)

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

    def _on_bar_hovered(self, status: bool, index: int):
        if not status:
            QToolTip.hideText()
            return
        if index is None:
            return
        if 0 <= int(index) < len(self._current_tooltips):
            text = self._current_tooltips[int(index)]
            if text:
                QToolTip.showText(QCursor.pos(), text, self._chart_view)

    def _update_kpis(self, values: list[float]):
        total = sum(float(v or 0.0) for v in values)
        avg = total / 12.0 if values else 0.0

        max_idx = None
        min_idx = None
        try:
            max_idx = max(range(len(values)), key=lambda i: float(values[i]))
            min_idx = min(range(len(values)), key=lambda i: float(values[i]))
        except Exception:
            max_idx = None
            min_idx = None

        self.kpi_total._kpi_value_label.setText(self._fmt_tk(total))
        self.kpi_avg._kpi_value_label.setText(self._fmt_tk(avg))

        if max_idx is not None:
            self.kpi_high._kpi_value_label.setText(f"{MONTHS[max_idx][:3]} · {self._fmt_tk(values[max_idx])}")
        else:
            self.kpi_high._kpi_value_label.setText("—")

        if min_idx is not None:
            self.kpi_low._kpi_value_label.setText(f"{MONTHS[min_idx][:3]} · {self._fmt_tk(values[min_idx])}")
        else:
            self.kpi_low._kpi_value_label.setText("—")

        self.kpi_total.setToolTip("Sum of all 12 months")
        self.kpi_avg.setToolTip("Year total divided by 12")
        if max_idx is not None:
            self.kpi_high.setToolTip(f"{MONTHS[max_idx]} is the highest month")
        if min_idx is not None:
            self.kpi_low.setToolTip(f"{MONTHS[min_idx]} is the lowest month")

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
            self.meta_label.setText(f"Source: Supabase Cache · Last sync: {last_sync}")
        else:
            self.meta_label.setText("Source: Supabase Cache")
