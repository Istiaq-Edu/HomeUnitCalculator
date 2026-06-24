# Calculator Tab UI/UX Redesign Plan

**Date:** 2026-05-17
**Status:** PLANNED - Ready for implementation
**Target:** `src/ui/tabs/main_tab.py` (~3272 lines)

---

## Summary

Complete UI/UX overhaul of the Calculator tab to match the premium quality of the redesigned Dashboard. Soft elevated cards (Material Design 3), section-based color accents, better typography/spacing, and subtle background treatment. No animations, no gradients, no icons — clean, professional, and functional.

---

## Design Decisions (Confirmed with User)

| Aspect | Decision |
|--------|----------|
| Card Style | Soft elevated with shadows (Material Design 3) |
| Accent Colors | Different colors per section (blue for inputs, green for results, etc.) |
| Results Display | Inline within billing card, better styled |
| Meter Reading | Compact rows, cleaner styling |
| Actions | Stay in effective areas, better UI/UX |
| Section Headers | Yes, with subtle divider lines |
| Focus Effect | Standard blue border (keep current) |
| Button Colors | Single primary color for consistency |
| Background | Subtle different shade (#1e1e1e) behind content |
| Meter Numbering | No numbering on rows |
| Add/Remove | More prominent with clear icons and labels |
| Results Highlight | Subtle green tint background |
| Room Cards | Same elevation style as calculator cards |
| Icons | Text-only, no icons |
| Collapsible | Only Load section collapsible |

---

## Color System

### Section Accent Colors
```
Billing Period:     #6B8AFF (Soft Blue)
Meter Readings:     #49C6FF (Cyan - from dashboard)
Results:            #9FE29D (Green - from dashboard)
Actions:            #B97AFF (Purple - from dashboard)
Room Calculations:  #FFB86B (Orange - from dashboard)
```

### Card Styling Constants
```python
CARD_BG = "#2b2b2b"
CARD_BORDER = "1px solid #3d3d3d"
CARD_RADIUS = 12  # px
CARD_SHADOW_COLOR = "rgba(0, 0, 0, 0.3)"
CARD_SHADOW_BLUR = 20  # px
CARD_SHADOW_OFFSET_Y = 4  # px
```

### Background
```python
TAB_BG = "#1e1e1e"  # Subtle different shade for content area
```

### Typography
```python
SECTION_HEADER_SIZE = 14  # px, bold
SECTION_HEADER_COLOR = "#E0E0E0"
BODY_TEXT_SIZE = 13  # px
CAPTION_SIZE = 11  # px
CAPTION_COLOR = "#B4B4B4"
```

### Results Highlight
```python
RESULTS_BG = "rgba(159, 226, 157, 0.08)"  # Very subtle green tint
RESULTS_BORDER = "1px solid rgba(159, 226, 157, 0.15)"
```

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Tab Background: #1e1e1e                                     │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⚡ Actions (Collapsible)                                │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Load Data Container                                 │ │ │
│ │ │ [Month ▼] [Year] [Source ▼] [Load]                 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Save Options Container                              │ │ │
│ │ │ [Save PDF]  [Save CSV]  [Save Cloud]               │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Add Next Month Container                            │ │ │
│ │ │              [Add Next Month]                       │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Billing Period & Meter Readings (Accent: #6B8AFF)       │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Billing Period                                      │ │ │
│ │ │ [Month ▼] [Year] [Tenant Name]                     │ │ │
│ │ ├─────────────────────────────────────────────────────┤ │ │
│ │ │ Meter Readings                                      │ │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │ │ │
│ │ │ │ [Meter Input] [Diff Input]              [Remove] │ │ │ │
│ │ │ │ [Meter Input] [Diff Input]              [Remove] │ │ │ │
│ │ │ │ [Meter Input] [Diff Input]              [Remove] │ │ │ │
│ │ │ └─────────────────────────────────────────────────┘ │ │ │
│ │ │ [+ Add Reading]                                     │ │ │
│ │ ├─────────────────────────────────────────────────────┤ │ │
│ │ │ Additional Amounts                                  │ │ │
│ │ │ [Amount] [Description]                              │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Results (Accent: #9FE29D) - Green tint background      │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Total Units: 150                                    │ │ │
│ │ │ Per Unit Cost: ₹8.50                                │ │ │
│ │ │ Total Cost: ₹1,275.00                               │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Room Calculations (Accent: #FFB86B)                     │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ Room 1                                              │ │ │
│ │ │ [Present] [Previous] [Units] [Cost]                 │ │ │
│ │ ├─────────────────────────────────────────────────────┤ │ │
│ │ │ Room 2                                              │ │ │
│ │ │ [Present] [Previous] [Units] [Cost]                 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 0: Theme Constants & Helpers
**Target:** `src/ui/custom_widgets.py` (add ~100 lines)

- [ ] Create `CalculatorTheme` class with all color constants
- [ ] Create `card_style()` helper method for consistent card QSS
- [ ] Create `section_header_style()` helper for section headers
- [ ] Create `apply_card_shadow()` helper for QGraphicsDropShadowEffect
- [ ] Create `results_highlight_style()` helper for green tint

### Phase 1: Background & Root Layout
**Target:** `src/ui/tabs/main_tab.py` → `init_ui()` method

- [ ] Set tab background to #1e1e1e
- [ ] Add subtle content margins (16px all sides)
- [ ] Ensure scroll area has correct background

### Phase 2: Actions Section Refinement
**Target:** `src/ui/tabs/main_tab.py` → `_create_load_data_container()` and related

- [ ] Apply soft elevated card style to all three containers
- [ ] Add section headers with purple accent (#B97AFF)
- [ ] Improve button spacing and sizing
- [ ] Keep Load section collapsible, Save and Add Month always visible
- [ ] Apply consistent border-radius (12px) and shadows

### Phase 3: Billing Period & Meter Readings Card
**Target:** `src/ui/tabs/main_tab.py` → `create_billing_and_reading_container()` and related

- [ ] Wrap in soft elevated card with blue accent (#6B8AFF)
- [ ] Add section header "Billing Period" with divider
- [ ] Add section header "Meter Readings" with divider
- [ ] Improve input field spacing (8px vertical, 12px horizontal)
- [ ] Style "Add Reading" button more prominently
- [ ] Style remove buttons with clear X icon
- [ ] Add section header "Additional Amounts" with divider

### Phase 4: Results Section
**Target:** `src/ui/tabs/main_tab.py` → `create_results_group()` or inline in billing card

- [ ] Apply green tint background (#9FE29D at 8% opacity)
- [ ] Apply green border (15% opacity)
- [ ] Add section header "Results" with green accent
- [ ] Improve typography (larger font for values, caption for labels)
- [ ] Ensure results are visually distinct but not overwhelming

### Phase 5: Room Calculations Section
**Target:** `src/ui/tabs/main_tab.py` → `_create_rooms_section()`

- [ ] Apply same card style as calculator cards
- [ ] Add section header "Room Calculations" with orange accent (#FFB86B)
- [ ] Style individual room cards with consistent elevation
- [ ] Improve room card internal spacing
- [ ] Ensure room cards match the new design language

### Phase 6: Typography & Spacing Polish
**Target:** All sections

- [ ] Ensure all section headers use 14px bold, #E0E0E0
- [ ] Ensure all body text uses 13px
- [ ] Ensure all captions use 11px, #B4B4B4
- [ ] Verify consistent spacing (8px, 12px, 16px, 24px grid)
- [ ] Verify consistent border-radius (12px for cards, 8px for inputs)

### Phase 7: Edge Cases & Responsive
**Target:** All sections

- [ ] Test at minimum window size (1000px width)
- [ ] Test with many meter readings (scroll behavior)
- [ ] Test with empty results (no data loaded)
- [ ] Test with long tenant names
- [ ] Test with many rooms
- [ ] Verify all functionality preserved

---

## Edge Cases to Handle

1. **Empty Results:** When no calculation is done, results section should show placeholder text, not empty space
2. **Many Meter Readings:** Scroll area should handle 10+ readings without breaking layout
3. **Long Text:** Tenant names, descriptions should truncate with ellipsis if too long
4. **Window Resize:** All cards should expand/contract gracefully
5. **Focus Navigation:** Tab/arrow key navigation should still work correctly
6. **Dark/Light Theme:** Current design is dark-only, no light theme support needed

---

## Files to Modify

1. `src/ui/custom_widgets.py` - Add theme constants and helper methods
2. `src/ui/tabs/main_tab.py` - Main implementation (all phases)

---

## Testing Checklist

- [ ] All buttons functional (Load, Save PDF, Save CSV, Save Cloud, Add Month)
- [ ] All inputs accept correct data types
- [ ] Add/remove meter readings works
- [ ] Results calculate correctly
- [ ] Room calculations work
- [ ] Collapsible sections expand/collapse
- [ ] Scroll behavior smooth
- [ ] Window resize works
- [ ] Tab navigation works
- [ ] No visual glitches at any size

---

## Design Principles

1. **Consistency:** All cards use same elevation, shadows, border-radius
2. **Hierarchy:** Section headers + dividers create clear visual hierarchy
3. **Breathing Room:** Generous spacing between elements
4. **Subtle Accents:** Color used sparingly to guide attention, not overwhelm
5. **Functional Beauty:** Every design choice serves a purpose
6. **No Assumptions:** All decisions validated with user

---

**Next Step:** Implement Phase 0 (Theme Constants & Helpers) in `custom_widgets.py`
