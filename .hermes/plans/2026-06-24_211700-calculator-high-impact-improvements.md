# Calculator Page High-Impact Improvements Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Elevate the calculator page from "functional" to "billion dollar" by fixing visual hierarchy, color mismatches, box-behind-text remnants, button consistency, and adding micro-interactions.

**Architecture:** All changes are in `src/ui/tabs/main_tab.py` (ResultCard, FinalAmountCard, ReadingPairWidget, AddPairButton, room cards, main card layout) and `src/ui/custom_widgets.py` (CalculatorTheme). No new files. No logic changes — purely visual/UX.

**Tech Stack:** PyQt5, QFluent-Widgets 1.9.1, Python 3.12

---

## Task 1: Make FinalAmountCard visually dominant (hero metric)

**Objective:** The Final Amount card should be the visual climax of the results column — bigger, distinct background, larger value typography.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:502-617` (FinalAmountCard class)

**Changes:**
1. Increase card height from 90px → 110px
2. Increase value font from 32px → 40px, font-weight 800 → 800 (keep)
3. Increase icon chip from 52px → 56px, icon pixmap from 40 → 44px
4. Add a subtle background tint: `background-color: rgba(0, 120, 212, 0.08)` on the card itself (not an inner panel — directly on `#final_amount_card`)
5. Change the top border from `2px solid rgba(0,120,212,0.35)` to `1px solid rgba(255,255,255,0.08)` — a neutral separator, not a colored stripe
6. Increase title font from 14px → 16px
7. Increase content_layout spacing from 4 → 6
8. Increase card layout margins from (20, 10, 20, 10) → (24, 14, 24, 14)

**Verification:**
- Compile: `python -c "import py_compile; py_compile.compile('src/ui/tabs/main_tab.py', doraise=True)"`
- FinalAmountCard height should be 110px, value font 40px
- Card should have a subtle blue tint visible on the #2b2b2b card background

---

## Task 2: Remove box-behind-text from room card result rows

**Objective:** Room card result rows (Real Unit, Unit Bill, Grand Total) still have `rgba(r,g,b,0.14)` background + `1px solid` border — same box-behind-text issue fixed on main result cards.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1780-1800` (room card frosted result rows loop)

**Changes:**
Replace the container styling from:
```python
container.setStyleSheet(f"background-color: rgba({r},{g},{b},0.14); border: 1px solid rgba({r},{g},{b},0.45); border-radius: 8px;")
```
To:
```python
container.setStyleSheet(f"background: transparent; border: none; border-bottom: 1px solid rgba({r},{g},{b},0.15);")
```

Also reduce padding from `(12, 8, 12, 8)` → `(10, 4, 10, 4)` to match the compact result card style.

**Verification:**
- Compile check
- Room card result rows should have no visible box/border behind the text — just a subtle colored bottom line

---

## Task 3: Fix room card title color to match section accent

**Objective:** Room section header uses `#FFB86B` orange, but room card titles use `#0078D4` blue — visual mismatch.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1702-1709` (room card title and header line)

**Changes:**
1. Change title color from `#0078D4` → `#FFB86B`
2. Change header_line color from `#0078D4` → `#FFB86B`
3. Keep title font-size 20px, font-weight 800

**Verification:**
- Compile check
- Room card titles should be orange, matching the "Room Calculations" section header

---

## Task 4: Remove visible border from result card icon chips

**Objective:** Icon chips have `border: 1px solid {dark_accent}` which creates a boxy outline around icons.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:392-397` (ResultCard icon_chip stylesheet)
- Modify: `src/ui/tabs/main_tab.py:551-556` (FinalAmountCard icon_chip stylesheet)

**Changes:**
1. In ResultCard, change icon_chip stylesheet from:
```python
border: 1px solid {dark_accent};
```
To:
```python
border: none;
```

2. In FinalAmountCard, same change — remove `border: 1px solid {dark_accent}` → `border: none`

3. Increase chip_bg_rgba opacity from 0.10 → 0.14 to compensate for the lost border definition

**Verification:**
- Compile check
- Icon chips should have a soft tinted background with no visible border outline

---

## Task 5: Increase period bar visibility

**Objective:** Period bar `rgba(0,120,212,0.12)` is nearly invisible on `#2b2b2b` card background.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1075-1079` (period_bar stylesheet)

**Changes:**
Change period_bar stylesheet from:
```python
background-color: rgba(0, 120, 212, 0.12);
border: 1px solid rgba(0, 120, 212, 0.30);
```
To:
```python
background-color: rgba(0, 120, 212, 0.18);
border: 1px solid rgba(0, 120, 212, 0.40);
```

**Verification:**
- Compile check
- Period bar should be visibly distinct from the card background

---

## Task 6: Unify button heights to 40px

**Objective:** Calculate is 42px, AddPairButton is 40px, save buttons are 40px — inconsistent.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1197` (Calculate button setFixedHeight)

**Changes:**
Change Calculate button height from 42px → 40px to match all other buttons.

**Verification:**
- Compile check
- All buttons in the calculator page should be 40px height

---

## Task 7: Fix AddPairButton color hierarchy

**Objective:** AddPairButton and Calculate button are both `#0078D4` blue — no action hierarchy. AddPair should be subtle/ghost, Calculate should be the prominent primary.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:316-331` (AddPairButton paintEvent)

**Changes:**
Change AddPairButton paintEvent colors from blue to neutral gray:
```python
if self._hover:
    bg = QColor(80, 80, 80, 180)
    border = QColor(120, 120, 120, 200)
else:
    bg = QColor(60, 60, 60, 120)
    border = QColor(90, 90, 90, 140)
```

This makes AddPairButton a ghost/secondary button while Calculate remains the blue primary.

**Verification:**
- Compile check
- AddPairButton should be gray/subtle, Calculate should be blue/prominent — clear visual hierarchy

---

## Task 8: Increase ReadingPairWidget hover visibility

**Objective:** Current hover `rgba(255,255,255,0.03)` is nearly invisible.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:199-210` (ReadingPairWidget stylesheet)

**Changes:**
Change hover from:
```python
background: rgba(255, 255, 255, 0.03);
border-bottom: 1px solid rgba(255, 255, 255, 0.08);
```
To:
```python
background: rgba(255, 255, 255, 0.06);
border-bottom: 1px solid rgba(255, 255, 255, 0.12);
```

**Verification:**
- Compile check
- Hovering a reading pair row should show a visibly lighter background

---

## Task 9: Increase remove button touch target

**Objective:** Remove button is 24x24px — below the 32px recommended minimum.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:103-106` (remove_button setFixedSize and iconSize)

**Changes:**
1. Change `setFixedSize(24, 24)` → `setFixedSize(28, 28)`
2. Change `setIconSize(QSize(12, 12))` → `setIconSize(QSize(14, 14))`

**Verification:**
- Compile check
- Remove button should be 28x28px — larger and easier to click

---

## Task 10: Standardize separator line weights

**Objective:** Result cards use `1px border-bottom`, FinalAmountCard uses `2px border-top` — inconsistent.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:610-616` (FinalAmountCard border-top)

**Changes:**
Change FinalAmountCard border-top from:
```python
border-top: 2px solid {_rgba_from_hex(theme_color, 0.35)};
```
To:
```python
border-top: 1px solid rgba(255, 255, 255, 0.08);
```

This matches the 1px weight used by result cards and uses a neutral color instead of blue.

**Verification:**
- Compile check
- All separator lines should be 1px

---

## Task 11: Add units to result card values

**Objective:** "Total Cost: 2300" should say "Total Cost: 2300 TK" — values need units.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1350-1360` (calculate_main method — where result labels are set)

**Changes:**
Update the setText calls in `calculate_main`:
- `self.total_unit_value_label.setText(f"{int(total_unit)}")` → keep as-is (units are count, no currency)
- `self.total_diff_value_label.setText(f"{int(total_diff)}")` → keep as-is (count)
- `self.per_unit_cost_value_label.setText(f"{per_unit_cost:.2f} TK")` → already has TK
- `self.additional_amount_value_label.setText(f"{int(additional_amount)} TK")` → already has TK
- `self.total_cost_card.update_value(f"{int(total_cost)} TK")` → already has TK
- `self.in_total_value_label.setText(f"{int(in_total)} TK")` → already has TK

Most already have TK — only verify and ensure consistency.

**Verification:**
- Compile check
- All currency values should end with " TK"

---

## Task 12: Add tooltips to key buttons

**Objective:** Calculate and Add Next Month buttons have no tooltips.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1194` (Calculate button — add setToolTip)
- Modify: `src/ui/tabs/main_tab.py:1128` (Add Next Month button — add setToolTip)

**Changes:**
1. After Calculate button creation, add:
```python
self.main_calculate_button.setToolTip("Calculate total units, per-unit cost, and final amount from meter readings")
```

2. After Add Next Month button creation, add:
```python
add_next_month_btn.setToolTip("Copy current month's final readings as next month's previous readings")
```

**Verification:**
- Compile check
- Hovering buttons should show tooltip text

---

## Task 13: Replace emojis with Fluent icons in section headers

**Objective:** Emojis (📊 📋 💰 ✅) may not render on all Windows builds. Use text-only headers with colored styling instead.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1052` (card title "📊 Main Calculation")
- Modify: `src/ui/tabs/main_tab.py:1167` (Reading Pairs header "📋 Reading Pairs")
- Modify: `src/ui/tabs/main_tab.py:1213` (Additional Amount header "💰 Additional Amount")
- Modify: `src/ui/tabs/main_tab.py:1265` (Results header "✅ Calculation Results")

**Changes:**
Remove all emoji prefixes from header text:
1. `"📊 Main Calculation"` → `"Main Calculation"`
2. `"📋 Reading Pairs"` → `"Reading Pairs"`
3. `"💰 Additional Amount"` → `"Additional Amount"`
4. `"✅ Calculation Results"` → `"Calculation Results"`

The colored text already provides visual distinction — emojis are unnecessary and risk rendering inconsistently.

**Verification:**
- Compile check
- Headers should show plain text with colored styling, no emoji characters

---

## Task 14: Add subtle result card update animation on Calculate

**Objective:** When Calculate is clicked, result cards should pulse/fade to show values updated — not just change instantly.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:496-499` (ResultCard `_pulse_effect` method)
- Modify: `src/ui/tabs/main_tab.py:640-645` (FinalAmountCard `_premium_update_effect` method)

**Changes:**
1. In ResultCard `_pulse_effect`, implement a simple opacity flash:
```python
def _pulse_effect(self):
    """Brief opacity flash when value updates."""
    try:
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(200)
        anim.setStartValue(0.5)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
    except Exception:
        pass
```

2. In FinalAmountCard `_premium_update_effect`, same pattern with slightly longer duration:
```python
def _premium_update_effect(self):
    try:
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
    except Exception:
        pass
```

Note: `windowOpacity` on child widgets doesn't work in Qt — instead use `QGraphicsOpacityEffect`:
```python
from PyQt5.QtWidgets import QGraphicsOpacityEffect
def _pulse_effect(self):
    try:
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()
    except Exception:
        pass
```

**Verification:**
- Compile check
- Clicking Calculate should produce a subtle fade-in on result cards

---

## Task 15: Style TK currency label as a badge

**Objective:** "TK" is plain text — style it as a subtle badge/prefix for the additional amount input.

**Files:**
- Modify: `src/ui/tabs/main_tab.py:1231-1232` (currency_label in additional amount section)

**Changes:**
Change currency_label styling from:
```python
currency_label.setStyleSheet("font-weight: bold; color: #ffffff; font-size: 12px; padding: 8px 4px; background: transparent; border: none;")
```
To:
```python
currency_label.setStyleSheet("font-weight: bold; color: #0078D4; font-size: 13px; padding: 6px 10px; background-color: rgba(0, 120, 212, 0.12); border: 1px solid rgba(0, 120, 212, 0.25); border-radius: 8px;")
```

**Verification:**
- Compile check
- "TK" should appear as a small blue-tinted badge next to the additional amount input

---

## Verification (Final)

After all tasks:

```bash
# Compile check
python -c "import py_compile; py_compile.compile('src/ui/tabs/main_tab.py', doraise=True); py_compile.compile('src/ui/custom_widgets.py', doraise=True); print('OK')"

# Run the app and verify visually:
# 1. Final Amount card is visibly larger than other result cards
# 2. Room card result rows have no box behind text
# 3. Room card titles are orange (matching section header)
# 4. Icon chips have no visible border
# 5. Period bar is visibly blue-tinted
# 6. All buttons are 40px height
# 7. AddPairButton is gray, Calculate is blue
# 8. Hovering reading pairs shows visible background change
# 9. Remove buttons are 28x28
# 10. All separator lines are 1px
# 11. Currency values show " TK" suffix
# 12. Buttons show tooltips on hover
# 13. No emojis in headers
# 14. Calculate click triggers subtle fade on results
# 15. "TK" badge next to additional amount input
```

## Files Modified
- `src/ui/tabs/main_tab.py` — all tasks
- `src/ui/custom_widgets.py` — no changes needed (CalculatorTheme already correct)

## Risks
- Task 14 (animation) uses `QGraphicsOpacityEffect` which can conflict with other graphics effects — wrapped in try/except
- Task 13 (emoji removal) changes visual identity — user may prefer emojis, can revert easily
- All other tasks are low-risk CSS/layout changes
