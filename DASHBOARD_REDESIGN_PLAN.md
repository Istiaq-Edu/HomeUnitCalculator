# Dashboard Redesign - Implementation Plan

> **Status**: IMPLEMENTATION COMPLETE - All 8 phases done, 12/12 tests passing
> **Created**: 2026-05-15
> **Target**: `src/ui/tabs/dashboard_tab.py` (2714 lines -> ~1100 lines)

## Summary

Complete overhaul of the dashboard to create a modern, professional design with:
- 8 summary KPI cards in a 2x4 grid at the top
- 4 chart cards in a 2x2 grid below (each with a different chart type)
- Refined dark theme with glass-morphism, better typography, and animations
- Edge case handling for empty states, loading, offline, and responsive layouts

---

## Progress Tracker

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0 | [x] COMPLETED | New Reusable Widgets in `custom_widgets.py` |
| Phase 1 | [x] COMPLETED | Theme System and Style Constants |
| Phase 2 | [x] COMPLETED | Structural Refactor (No Visual Changes) - 403 lines removed |
| Phase 3 | [x] COMPLETED | New Layout - Summary KPI Row + 2x2 Chart Grid |
| Phase 4 | [x] COMPLETED | Chart Type Differentiation |
| Phase 5 | [x] COMPLETED | Visual Refinements |
| Phase 6 | [x] COMPLETED | Edge Cases and State Management |
| Phase 7 | [x] COMPLETED | Summary KPI Data Binding |

---

## Phase 0: New Reusable Widgets in `custom_widgets.py`

**Status**: [x] COMPLETED
**Target**: `src/ui/custom_widgets.py` (+200 lines)

### 0A. `SummaryKpiCard(QWidget)` (~65 lines)
- [x] Create class with horizontal layout
- [ ] 3px left accent bar painted via `paintEvent`
- [ ] 36x36 icon box with `rgba(accent,25)` background, 8px border-radius
- [ ] CaptionLabel title (11px, #B4B4B4)
- [ ] BodyLabel value (22px bold, accent color)
- [ ] Expose `_kpi_value_label` for backward-compatible `.setText()` calls

### 0B. `AnimatedNumberLabel(BodyLabel)` (~45 lines)
- [ ] Create class with `fmt_fn` constructor parameter
- [ ] Implement `animate_to(target, duration_ms=600)` using `QVariantAnimation`
- [ ] Use `QEasingCurve.OutCubic` for smooth deceleration
- [ ] Store `_current_value: float = 0.0`

### 0C. `ShimmerPlaceholder(QWidget)` (~55 lines)
- [ ] Create class with `min_height` parameter
- [ ] Implement shimmer animation with `QTimer` at 33ms (30fps)
- [ ] Paint gradient band oscillating left-to-right
- [ ] `set_active(bool)` to start/stop animation

### 0D. `EmptyStateWidget(QWidget)` (~40 lines)
- [ ] Create class with icon, message, subtitle parameters
- [ ] Center-aligned vertical layout
- [ ] IconWidget (48x48, #A0A0A0) + BodyLabel (16px bold) + CaptionLabel (13px)
- [ ] Background: `rgba(43,43,43,200)`, border-radius 12px

---

## Phase 1: Theme System and Style Constants

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py` (insert after line 80)

### 1A. `DashboardTheme` class (~50 lines)
- [ ] Define color constants:
  - `PRIMARY = "#0078D4"`, `PRIMARY_HOVER = "#1084d8"`, `PRIMARY_PRESSED = "#005a9e"`
  - `CYAN_CURRENT = "#49C6FF"`, `GREEN_POSITIVE = "#9FE29D"`
  - `PURPLE_SECONDARY = "#B97AFF"`, `ORANGE_WARNING = "#FFB86B"`, `RED_NEGATIVE = "#FF6B6B"`
  - `TEXT_PRIMARY = "#FFFFFF"`, `TEXT_SECONDARY = "#B4B4B4"`, `TEXT_MUTED = "#A0A0A0"`
- [ ] Define card constants:
  - `CARD_BG = "#2b2b2b"`, `CARD_BORDER = "rgba(255,255,255,0.06)"`
  - `CARD_RADIUS = 16`, `CARD_SHADOW_BLUR = 20`
- [ ] Define typography constants:
  - `HEADER_FONT_SIZE = 20`, `BODY_VALUE_FONT_SIZE = 22`, `CAPTION_FONT_SIZE = 12`
- [ ] Define `KPI_THEMES` dict (moved from `_create_kpi_card`)
- [ ] Define `SUMMARY_KPI_THEMES` dict for 8 new summary KPIs

### 1B. Helper methods (~30 lines)
- [ ] `card_style(object_name)` - standardized card QSS
- [ ] `header_style()` - header label stylesheet
- [ ] `refresh_btn_style()` - consolidated refresh button QSS
- [ ] `apply_card_shadow(widget)` - QGraphicsDropShadowEffect setup

---

## Phase 2: Structural Refactor (No Visual Changes)

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py` (reduce from 2714 to ~1500 lines)

### 2A. Extract `_build_header_section()` (~20 lines)
- [ ] Move title + divider + subtitle into self-contained method
- [ ] Use `DashboardTheme` constants

### 2B. Extract `_build_chart_card(config)` (~60 lines)
- [ ] Create factory method with config dict parameter
- [ ] Replace 4 copy-pasted card construction blocks
- [ ] Support: object_name, icon, title, hint, year_combo_attr, refresh_btn_attr, kpi_titles, chart_container_attr

### 2C. Consolidate year combo management (~20 lines saved)
- [ ] Create `_sync_all_year_combos(years)` method
- [ ] Replace duplicated logic in `_populate_years_from_cache` and `_on_years_fetched`

### 2D. Consolidate KPI update logic (~140 lines saved)
- [ ] Create `_update_section_kpis(kpis, raw_values, year, fmt_fn, tooltip_prefix)` method
- [ ] Replace `_update_kpis`, `_update_rate_kpis`, `_update_elec_kpis`, `_update_owner_room_kpis`

### 2E. Consolidate chart initialization (~100 lines saved)
- [ ] Create `_init_qtchart_common(chart_view, label_format, title)` method
- [ ] Replace 4 near-identical `_init_*_qtchart` methods

### 2F. Preserve tenant resolution methods unchanged
- [ ] Keep `_parse_year_month` through `_tenant_for_month` (lines 2598-2714) as-is
- [ ] Ensure `test_dashboard_room_tooltips.py` tests still pass

**Checkpoint**: Run `pytest tests/test_dashboard_room_tooltips.py tests/test_startup_smoke.py`

---

## Phase 3: New Layout - Summary KPI Row + 2x2 Chart Grid

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py`

### 3A. Rewrite `_build_ui` method
- [ ] New layout structure:
  ```
  page_layout (QVBoxLayout, margins=20, spacing=16)
    header_section
    self._summary_kpi_container (2x4 QGridLayout)
    self._charts_grid_container (2x2 QGridLayout)
    addStretch(1)
  ```

### 3B. Build summary KPI grid (2x4)
- [ ] Create 8 `SummaryKpiCard` instances using `SUMMARY_KPI_THEMES`
- [ ] Store as: `_summary_annual`, `_summary_avg_monthly`, `_summary_highest`, `_summary_lowest`, `_summary_current_bill`, `_summary_rate`, `_summary_units`, `_summary_rooms`
- [ ] Place in `QGridLayout`: Row 0 (Annual|Avg|Highest|Lowest), Row 1 (Current|Rate|Units|Rooms)

### 3C. Build chart cards in 2x2 grid
- [ ] Use `_build_chart_card` factory for 4 cards
- [ ] Place in `QGridLayout`: (0,0) Per Unit Cost, (0,1) Electricity Bill, (1,0) Yearly Total, (1,1) Owner/Room

### 3D. Move KPIs below chart within each card
- [ ] Change from left-KPI + right-chart to top-chart + bottom-KPIs
- [ ] Create compact horizontal KPI row (4 cards, ~60px height, 16px value font)

### 3E. Responsive layout via `resizeEvent`
- [ ] When width < 900px: summary grid -> 4x2, chart grid -> 4x1
- [ ] Debounce via `QTimer.singleShot(50, ...)`

---

## Phase 4: Chart Type Differentiation

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py`

### 4A. Per Unit Cost: QSplineSeries (enhanced)
- [ ] Line color: `CYAN_CURRENT` (#49C6FF)
- [ ] Fill gradient: `rgba(73,198,255,60)` to transparent

### 4B. Electricity Bill: QBarSeries (new)
- [ ] Create `_apply_qt_bar_chart()` method
- [ ] Use `QBarSet` + `QBarSeries` with bar width 0.6
- [ ] Connect `QBarSet.hovered` signal for tooltips

### 4C. Yearly Total Bill: Emphasized area chart
- [ ] Enhanced fill opacity (140 vs 90)
- [ ] Add lighter area series underneath for depth

### 4D. Owner/Room Bill: Grouped bar chart (new)
- [ ] Create `_apply_qt_grouped_bar_chart()` method
- [ ] Owner mode: single `QBarSet` in `PURPLE_SECONDARY`
- [ ] Room mode: one `QBarSet` per room with rotating colors

### 4E. `SimpleBarChartWidget` fallback (~110 lines)
- [ ] Custom-painted bar chart for when PyQt5.QtChart unavailable
- [ ] Implement `paintEvent`, `_hit_test`, `mouseMoveEvent`, `leaveEvent`
- [ ] Support `set_data()` and `set_grouped_data()`

### 4F. Update render methods
- [ ] `_render_values` (yearly): area chart emphasis
- [ ] `_render_rate_from_cache`: spline chart
- [ ] `_render_elec_from_cache`: bar chart
- [ ] `_render_owner_room_values`: bar chart (single or grouped)

---

## Phase 5: Visual Refinements

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py` + `src/ui/custom_widgets.py`

### 5A. Glass-morphism cards
- [ ] `QGraphicsDropShadowEffect` blurRadius=20, offset(0,4), color=QColor(0,0,0,80)
- [ ] Background: `rgba(43,43,43,220)`, border: `1px solid rgba(255,255,255,0.06)`, radius: 16px

### 5B. Typography hierarchy
- [ ] Card headers: 20px/700 (was 22px/800)
- [ ] KPI values: 22px bold (summary), 16px (per-chart compact)
- [ ] All via `DashboardTheme` constants

### 5C. Summary KPI card styling
- [ ] Left accent bar, icon box with tinted background, proper spacing

### 5D. Animated number counters
- [ ] Use `AnimatedNumberLabel.animate_to()` in summary and per-chart KPIs
- [ ] Skip animation on initial load and when delta is zero

### 5E. Better icons
- [ ] Per Unit Cost: `FluentIcon.SPEED_HIGH`
- [ ] Electricity Bill: `FluentIcon.SPEED_HIGH`
- [ ] Yearly Total: `FluentIcon.SHOPPING_CART`
- [ ] Owner/Room: `FluentIcon.PEOPLE`
- [ ] Summary: `SHOPPING_CART`, `CALENDAR`, `UP`/`DOWN`, `SPEED_HIGH`, `PEOPLE`, `HOME`

---

## Phase 6: Edge Cases and State Management

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py`

### 6A. Empty/no-data state
- [ ] Show `EmptyStateWidget` when `all(v is None for v in raw_values)`
- [ ] Set all KPI values to "---"

### 6B. Shimmer/loading state
- [ ] Show `ShimmerPlaceholder` during sync
- [ ] Disable refresh buttons, show "Syncing..."

### 6C. Offline/disconnected banner
- [ ] Persistent warning banner when Supabase not configured
- [ ] Styled with `ORANGE_WARNING` accent
- [ ] Dismissible via close button

### 6D. Refresh button state management
- [ ] Create `_set_refresh_buttons_enabled(enabled, exclude)` method
- [ ] Consistent "Syncing..." text + disabled state during sync

---

## Phase 7: Summary KPI Data Binding

**Status**: [ ] NOT STARTED
**Target**: `src/ui/tabs/dashboard_tab.py`

### 7A. `_update_summary_kpis(snapshot, year)` (~60 lines)
- [ ] Annual Total: `sum(monthly_totals)`
- [ ] Avg Monthly: `annual / nonzero_months`
- [ ] Highest Month: `max(monthly_totals)`
- [ ] Lowest Month: `min(nonzero monthly_totals)`
- [ ] Current Month Bill: `monthly_totals[current_month]`
- [ ] Per-Unit Rate: `monthly_per_unit_cost[current_month]`
- [ ] Units Consumed: `sum(total / rate)` where both nonzero
- [ ] Active Rooms: `len(get_cached_rooms(year))`

### 7B. Integration
- [ ] Call `_update_summary_kpis` from `_render_year_from_cache`

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| `QBarSeries` not available in QtChart | try/except fallback to `SimpleBarChartWidget` |
| Shadow effects on 12 widgets | Within acceptable limits; monitor performance |
| Responsive layout flicker | Debounce via `QTimer.singleShot(50, ...)` |
| Animation CPU spikes | 500ms duration, OutCubic easing, skip when delta=0 |
| `_kpi_value_label` backward compat | Both `SummaryKpiCard` and `InfoResultCard` expose it |
| Lazy loading smoke test | Don't change module-level imports in `dashboard_tab.py` |
| Tenant resolution tests | Keep `_parse_year_month` through `_tenant_for_month` unchanged |

---

## Testing Checklist

- [ ] `pytest tests/test_dashboard_room_tooltips.py` - all 3 tests pass
- [ ] `pytest tests/test_startup_smoke.py` - lazy loading preserved
- [ ] Visual: 4 charts render in 2x2 grid
- [ ] Visual: 8 summary KPIs show correct values
- [ ] Functional: year combo switching updates all sections
- [ ] Functional: scope combo (Owner/Room) works
- [ ] Functional: room selection works
- [ ] Edge: empty database shows empty states
- [ ] Edge: Supabase not configured shows offline banner
- [ ] Edge: window < 900px stacks to single column
- [ ] Edge: rapid year switching during sync

---

## Files Modified

| File | Changes |
|------|---------|
| `src/ui/custom_widgets.py` | +200 lines (4 new widget classes) |
| `src/ui/tabs/dashboard_tab.py` | 2714 lines -> ~1100 lines (refactored) |

## Files Referenced (No Changes)

| File | Purpose |
|------|---------|
| `src/ui/background_workers.py` | Data fetching (understand data flow) |
| `src/core/db_manager.py` | Data layer interface |
| `src/ui/flow_layout.py` | Existing FlowLayout (may use for responsive grid) |
| `tests/test_dashboard_room_tooltips.py` | Existing tests (must remain passing) |
| `tests/test_startup_smoke.py` | Lazy loading test (must remain passing) |
