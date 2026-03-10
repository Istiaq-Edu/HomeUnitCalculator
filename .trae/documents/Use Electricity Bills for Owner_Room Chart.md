## Clarification (You’re right)
Right now the “Room” chart is using **room grand total** (rent + gas + water + electricity). That’s why it doesn’t match what you mean by “electricity bill”.

## What amounts exist in this app (and where they come from)
- **Room Electricity Bill** = `room_data.unit_bill` (stored per room per month).
- **Room Grand Total** = `room_data.grand_total` (electricity + gas + water + house rent).
- **Owner Electricity Bill (PDF section)** = **Owner Unit Bill**:
  - `Owner Unit Bill = total_unit_cost - (total_water_bill + total_room_unit_bill)`
  - Source in PDF: [HomeUnitCalculator.py](file:///d:/hmc/HomeUnitCalculator/src/core/HomeUnitCalculator.py#L1281-L1296)

## What I will change
### 1) Make the Owner/Room chart truly “Electricity Bill Trend”
- In **Room mode**, plot **unit_bill** per month (not grand_total).
- Tooltip will show:
  - `Electricity: TK …` (unit_bill)
  - `Water: TK …` (water_bill) as extra info (not used for the plotted value)
  - Tenant name for that month (as before)

### 2) Fix Owner mode to align with electricity logic
- In **Owner mode**, plot **Owner Unit Bill** (same formula as PDF) using cached data:
  - `main_calculations_cache.main_data_json.total_unit_cost`
  - Sum all rooms’ `room_data_json.unit_bill` and `room_data_json.water_bill` per month
  - Then compute Owner Unit Bill per month

### 3) Storage / caching (no schema change required)
- We already store full `room_data_json` for each room-month, so we can extract `unit_bill` and `water_bill` without changing Supabase.
- I’ll add DB helper functions:
  - `get_cached_monthly_room_unit_bills(year, room_name)`
  - (optionally) `get_cached_monthly_room_water_bills(year, room_name)` for tooltips

### 4) Verification
- py_compile on touched modules.
- Quick UI check:
  - Room mode line matches the **Unit Bill** numbers you see in room UI/PDF.
  - Owner mode line matches the **Owner Unit Bill** shown in the PDF.

## Files to update
- `src/core/db_manager.py` (new query helpers extracting unit_bill/water_bill)
- `src/ui/tabs/dashboard_tab.py` (Room mode switches to unit_bill; tooltip text updates)

If you approve, I’ll implement these updates immediately.