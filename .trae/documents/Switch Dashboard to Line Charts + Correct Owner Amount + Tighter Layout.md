## What I found about the correct “Owner Amount”
- In your PDF, “Owner” is not `added_amount`.
- The PDF calculates **Owner Unit Bill** as:
  - `Owner Unit Bill = Total Unit Cost - (Total Water Bill + Total Room Unit Bill)`
  - Source: [HomeUnitCalculator.py](file:///d:/hmc/HomeUnitCalculator/src/core/HomeUnitCalculator.py#L1281-L1304)

## Changes you requested
1) Change the pillar/bar graphs to **line graphs** (both dashboard charts).
2) Give **more space to the graph** and reduce “too much padding” in the cards.
3) Fix the **Owner amount** to match the PDF’s “Owner Unit Bill”.

## Implementation Plan
### 1) Correct Owner amount (match PDF)
- Compute Owner series per month using cached data:
  - From `main_calculations_cache.main_data_json`: read `total_unit_cost` for each month.
  - From `room_calculations_cache.room_data_json`: sum per month:
    - `total_water_bill = Σ water_bill`
    - `total_room_unit_bill = Σ unit_bill`
  - Then compute per month:
    - `owner_unit_bill = total_unit_cost - (total_water_bill + total_room_unit_bill)`
- Update the “Owner” mode in the Owner/Room chart to use this computed series.
- Update tooltips/KPIs to show this owner value in **TK**.

### 2) Convert charts to Line Chart
- Replace QtChart bar series with **QLineSeries** + visible points.
- Support “blank month” behavior:
  - If a month has no bill (None), the line will **break** (no point drawn).
  - Tooltips will say **No billing**.
- Hover tooltips:
  - Use line/point hover signals to show the same tooltip content you already like.

### 3) Make chart larger and reduce padding
- Reduce card internal margins and spacing (less empty space around KPI tiles).
- Make KPI tiles more compact (smaller height) so the **chart area gets more vertical space**.
- Increase chart minimum height so it visually dominates the card.

### 4) Sync behavior adjustments
- Owner chart refresh will sync both:
  - main calculations (for total unit cost)
  - room calculations (for water + room unit totals)
  - so Owner Unit Bill is always accurate.

### 5) Verification
- Run `py_compile` on touched modules.
- Run a UI smoke test to ensure:
  - Both charts render as line graphs
  - Hover tooltips work
  - Owner value matches PDF formula
  - Layout has reduced padding and larger chart

## Files to change
- `src/ui/tabs/dashboard_tab.py` (line chart, layout tuning, owner formula)
- `src/core/db_manager.py` (add helper queries to get monthly water/unit sums, and main_data_json reads)
- (maybe) `src/ui/background_workers.py` (ensure owner refresh also triggers room-year sync)

If you approve, I’ll implement this next.