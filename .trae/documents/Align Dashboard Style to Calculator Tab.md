## What I found (Calculator tab design strategy)
- **Accent color:** Fluent blue `#0078D4` is the main brand color across Calculator UI (titles, dividers, focus borders, primary buttons). See examples in [main_tab.py](file:///d:/hmc/HomeUnitCalculator/src/ui/tabs/main_tab.py#L1988-L2014) and [rooms_tab.py](file:///d:/hmc/HomeUnitCalculator/src/ui/tabs/rooms_tab.py#L196-L217).
- **Section headers:** Big sections use a **styled TitleLabel + a 2px blue divider line** immediately below.
- **Containers:** Large blocks tend to be **static dark surfaces** (often plain `QWidget` with `background #2b2b2b`, `border #3d3d3d`, radius 12) with hover minimized.
- **Spacing:** Page margins commonly `12`, spacing `8–12`. `MainTab` uses a scroll area wrapper with inner page margins `12`.
- **Buttons:** Primary actions have consistent height (≈40), icon size (≈20), and blue gradient styling.

## How Dashboard differs today
- Dashboard currently uses **purple accent/hover** (`rgba(108, 92, 231, …)`) and a different header style.
- Dashboard big blocks are `CardWidget` with hover borders, not the calculator “static surface + blue divider” look.

## Plan to align DashboardTab
### 1) Unify page scaffolding
- Match Calculator’s pattern: root layout with 0 margins, scroll container, inner page margins **12** and spacing **8–12**.

### 2) Replace purple accents with calculator blue
- Replace purple hover borders and chart line color highlights with blue family:
  - Primary: `#0078D4`
  - Hover: slightly brighter blue (same pattern used by calculator buttons)

### 3) Apply calculator-style section headers
- For each dashboard block (“Yearly Total Bill”, “Owner / Room …”):
  - Style the header text like calculator section titles (larger, bold, blue)
  - Add the 2px blue divider line under the header

### 4) Convert large cards to “static surfaces”
- Either:
  - Switch from `CardWidget` to a styled `QWidget` container (static) like calculator sections, or
  - Keep `CardWidget` but remove hover border/shadow behavior and match the calculator surface colors.

### 5) Align controls/buttons
- Make Dashboard “Refresh” buttons match calculator button sizing/padding/icon size and blue style.
- Ensure ComboBoxes and labels match calculator typography/spacing.

### 6) Verification
- Quick compile check.
- Launch the app and visually compare Calculator vs Dashboard:
  - Title + divider consistency
  - Color consistency (blue)
  - Padding/margins consistency

If you approve, I’ll implement these UI-only changes in `src/ui/tabs/dashboard_tab.py` without touching the dashboard data logic.