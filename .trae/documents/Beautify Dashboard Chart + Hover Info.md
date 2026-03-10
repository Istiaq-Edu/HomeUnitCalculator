## What I’ll Improve (UI/UX)
- Make the Dashboard card look more “Fluent”:
  - Better spacing, header hierarchy (title + caption), rounded borders, subtle hover highlight.
  - Add a small “Source / Last sync” line so users know where data comes from.
- Add a quick KPI row above the chart:
  - Year Total, Avg/Month, Highest Month, Lowest Month (each with hover tooltip).

## TK Currency Formatting (Your Requirement)
- Format all money values as **Taka**:
  - Y-axis labels display like: `TK 12,345`
  - Hover tooltips display like: `TK 12,345` and `Δ TK +1,200`
  - KPI cards display the same TK format

## Chart Beautification
- Enable smooth chart animations.
- Use a darker chart background and softer grid lines.
- Color improvements:
  - Default bar color matches app accent.
  - Highlight the max month bar slightly brighter.
- Improve axis labels:
  - Better font sizing/contrast.
  - Custom Y-axis label formatting for `TK …`

## Hover Infos
- Hover a bar → tooltip: Month name, total bill (TK), and Δ vs previous month (TK).
- Hover the year dropdown → tooltip: “Years fetched from Supabase (cached locally)”.
- Hover Refresh → tooltip: “Sync from Supabase and update local cache”.

## How Hover Tooltips Will Work
- If QtChart is available:
  - Connect bar hover events and show a tooltip near the cursor.
- If fallback painter chart is used:
  - Add mouse tracking + bar hit-testing and show the same tooltip.

## Implementation Details (Files)
- Update `src/ui/tabs/dashboard_tab.py`
  - New KPI widgets row.
  - Styling (CardWidget stylesheet + consistent spacing).
  - TK formatter helper used by axis/tooltip/KPIs.
  - Hover handlers for QtChart and fallback chart.

## Verification
- Run `py_compile` for touched files.
- Run the app and verify:
  - Card hover highlight works.
  - Tooltip appears on bar hover with correct `TK` values.
  - KPI values update when switching year.
  - No crashes when Supabase is not configured.

If you approve, I’ll implement these beautifications next.