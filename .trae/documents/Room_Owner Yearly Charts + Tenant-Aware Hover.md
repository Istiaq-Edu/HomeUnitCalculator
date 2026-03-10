## Goal

* Add a **second Dashboard chart** like the existing one, but for:

  * **Owner bill amount** (default view)

  * **Per-room bill amount** (select a room)

* Controls in the chart corner:

  * **Year** dropdown

  * **Owner/Room** selector (Owner default)

  * **Room** dropdown (only enabled when Room is selected)

* Hover tooltip must show:

  * Month bill (TK)

  * If Room view: tenant name for that month (tenant changes across months supported)

  * If no billing for a month: show “No billing” and keep bar effectively blank

## Data Definitions

* **Owner bill amount** = `main_calculations.main_data.added_amount` (TK) per month.

* **Room bill amount** = `room_calculations.room_data.grand_total` (TK) per month for selected room.

## Tenant Linking (Supports “Tenant changed mid-year”)

Because the current rental record model doesn’t explicitly store “lived from month X to month Y”, I’ll implement a two-tier approach:

1. **Future-accurate (recommended): add occupancy fields**

   * Add fields to rental records:

     * `start_year`, `start_month`, `end_year`, `end_month` (end optional)

   * Update Rental Info UI so when saving a tenant you can set the start (and optional end).

   * This makes next-year and future data accurate.
2. **Backward-compatible fallback (keeps current data working): infer occupancy**

   * For records without occupancy fields, infer by ordering records for the same room by `created_at`:

     * start = created\_at month

     * end = month before next tenant record

   * This keeps your existing history usable.

## SQLite Cache + Delta Updates

* Add new cache tables:

  * `room_calculations_cache` (per month/year/room\_name + grand\_total + JSON)

  * `rental_records_cache` (tenant\_name, room\_number, created\_at, optional occupancy fields)

* Delta sync behavior:

  * For main\_calculations owner amounts: already cached; extend tooltip/axis use.

  * For room\_calculations:

    * Fetch a year’s main\_calculations IDs (<=12) then fetch room\_calculations for each ID.

    * Cache results locally.

    * Use sync\_state watermark if `updated_at` exists; otherwise do year refresh (still small).

  * For rental records:

    * Cache all non-archived rental records (or per-room on demand) and refresh periodically.

## Dashboard UI Changes

* Add a new card below the existing “Yearly Total Bill”:

  * Title: “Owner / Room Bill Trend”

  * Controls: Year + (Owner/Room) + Room

  * KPI row: Total / Avg / Highest / Lowest (TK)

  * Chart: same bar chart styling + hover tooltip

## Tooltip Content

* **Owner view** tooltip:

  * Month

  * Owner amount: `TK …`

  * Δ vs previous month: `Δ TK …`

* **Room view** tooltip:

  * Month

  * Room amount: `TK …` (or “No billing”)

  * Tenant: correct tenant name for that month (from occupancy mapping)

## Supabase Changes

* If you want the future-accurate tenant linking in cloud too:

  * Add columns to `rental_records` for `start_year/start_month/end_year/end_month`.

  * I can apply the migration using your Supabase MCP.

* Code will remain compatible if these columns are not present (fallback inference still works).

## Files Likely Touched

* `src/ui/tabs/dashboard_tab.py` (new card, selectors, chart rendering)

* `src/ui/background_workers.py` (year sync worker for room\_calculations + rental records)

* `src/core/db_manager.py` (new cache tables + helpers)

* `src/core/supabase_manager.py` (helpers to fetch room\_calculations/year and rental records)

* `src/ui/tabs/rental_info_tab.py` (add start/end month/year inputs; default start = current month/year)

## Verification

* py\_compile for touched modules

* Run app and verify:

  * Owner/Room selector changes dataset

  * Room dropdown populates from available rooms

  * Tooltips show tenant names per month (with correct switches)

  * Months with no billing show blank/“No billing” tooltip

  * All money shown as `TK …`

