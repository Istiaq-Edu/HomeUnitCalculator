## Goal (Your Requirements)
- Add a **new Dashboard tab** and make it the **default / main landing page**.
- Rename the current “Main” page to a more accurate name (recommended: **Calculator**).
- First dashboard feature: a **Yearly chart of Total Bill Amount**.
- The chart’s **year dropdown must be populated from Supabase availability**.
- Add a **proper SQLite cache + delta update sync** so Dashboard loads fast and works offline.

## UI/Navigation Changes
- Create a new tab: `DashboardTab` (new file `src/ui/tabs/dashboard_tab.py`).
- Keep existing `MainTab` class as-is (to avoid breaking code), but **rename its navigation label** to **Calculator**.
- Update navigation so:
  - **Dashboard** appears as the first/main page (Home).
  - Calculator becomes a regular page.
  - Initial selected tab = Dashboard.
- Update lazy tab loader registrations accordingly (Dashboard eager-load, others lazy as today).

## Dashboard: Yearly Total Bill Chart (First Build)
- Dashboard card: **“Yearly Total Bill (Jan–Dec)”**.
- Top-right of the card: **Year dropdown** (ComboBox).
- Data displayed:
  - 12 months (Jan..Dec) bar chart (preferred).
  - Optional total sum label.

## Chart Rendering
- Preferred: **PyQt5.QtChart** (no extra dependency) bar chart.
- Fallback: custom-painted bar chart widget if QtChart isn’t available in some environments.

## Supabase-Driven Year Dropdown
- Populate year dropdown from Supabase data:
  - Query years from cached table first.
  - If cache empty/stale and Supabase available: fetch years from Supabase and update cache.
- Implementation approach:
  - Add a `supabase_manager.get_available_years()` helper that retrieves `year` values and returns unique sorted list.
  - If PostgREST distinct isn’t convenient, fetch `select('year')` and unique client-side (low volume).

## SQLite Cache (Industry-Standard Structure)
- Use the existing SQLite DB (already in user AppData) and add dedicated cache tables.
- New tables (example):
  - `main_calculations_cache`:
    - `source TEXT` ("supabase")
    - `record_id TEXT/INT` (Supabase primary key)
    - `month TEXT`, `year INT`
    - `grand_total REAL`
    - `main_data_json TEXT` (optional raw JSON)
    - `created_at TEXT NULL`, `updated_at TEXT NULL`
    - `synced_at TEXT` (local timestamp)
    - `PRIMARY KEY (source, record_id)`
    - `UNIQUE (source, month, year)` (so overwrites are clean)
  - `sync_state`:
    - `key TEXT PRIMARY KEY` (e.g. "supabase_main_calculations")
    - `value TEXT` (e.g. last_sync watermark)

## Delta Update Strategy (Important)
Because delta sync depends on what Supabase columns exist, I’ll do this:
1) **Use Supabase MCP to inspect `main_calculations` columns** and confirm whether `updated_at` (or similar) exists.
2) Choose the best delta method:
   - If `updated_at` exists:
     - Store `last_sync_updated_at` in SQLite.
     - Fetch only changed rows: `updated_at > last_sync_updated_at`.
     - Upsert into cache.
   - If only `created_at` exists:
     - Delta sync new rows via `created_at > last_sync_created_at`.
     - For edits/overwrites (same month/year) that don’t change created_at, do a lightweight “validation pass”:
       - when user selects a year, fetch that year’s rows and upsert (small dataset; at most ~12 records in normal use).
       - This still behaves like delta in practice and guarantees correctness.

## Dashboard Data Flow
- On Dashboard open:
  - Load years from SQLite cache → populate dropdown instantly.
  - Kick off background sync (Supabase) if configured.
  - When sync completes → update dropdown + redraw chart.
- On year change:
  - Render from SQLite cache immediately.
  - If Supabase available and cache is stale → run year-specific refresh and then re-render.

## Verification
- Unit-ish checks:
  - Cache table creation and upsert logic.
  - Year list generation from cache.
- UI smoke:
  - Dashboard loads quickly even offline.
  - Year dropdown populated when Supabase configured.
  - Switching year updates chart.

## Files Likely Touched/Added
- Add: `src/ui/tabs/dashboard_tab.py`
- Update: `src/core/HomeUnitCalculator.py` (navigation + tab registration changes)
- Update: `src/core/db_manager.py` (bootstrap cache tables + helper queries)
- Update: `src/core/supabase_manager.py` (get_available_years + optional delta fetch helper)

If you accept this plan, I’ll implement Dashboard + chart + cache/delta sync end-to-end first, then we can add more dashboard cards later.