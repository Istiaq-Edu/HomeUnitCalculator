# Design: Calculator Tab Action Section Restructuring

**Date:** 2026-05-17
**Status:** Approved for implementation

## Problem

The current Action section on the Calculator (Main) tab places all controls in a single flat horizontal flow inside one card. Month loading, save buttons, and the "Add Next Month" button share the same container without visual separation, making it hard to distinguish between different action types.

## Goal

Separate the three action groups into distinct visual containers within the existing `CollapsibleSection("⚡ Actions")` wrapper while maintaining:
- Minimal color palette (same base colors)
- No UI distortion at any window size
- All existing functionality preserved
- Consistent dark theme styling

## Design Decisions

### Layout: Vertical Stack
Three vertically stacked card containers inside the single collapsible. This pattern:
- Works at all window sizes without horizontal cramping
- Matches the existing frosted subsection pattern in the billing card
- Provides clear visual hierarchy without crowding

### Visual Differentiation: Structural, Not Chromatic
Same base background (`#2b2b2b`), border (`#3d3d3d`), and border-radius (`8px`). Differentiated through:
- Layout rhythm (horizontal flow vs button grid vs centered single)
- Separator styles (solid hairline vs dotted vs none)
- Internal spacing (compact vs generous vs prominent)
- Title headers with descriptive labels

### Single Collapsible Wrapper
All three containers remain inside one `CollapsibleSection("⚡ Actions")`. Independent collapsibles would add unnecessary friction; the internal card separation provides enough structure.

## Container Specifications

### Container 1: "Load Data"
- **Purpose:** Select month/year, choose load source, load data into inputs
- **Layout:** Horizontal flow with controls
- **Contents:** Month combo | Year spinbox | Source dropdown | Load button
- **Spacing:** Compact (8px between items)
- **Separator:** Thin left accent border (1px solid `#3d3d3d`)
- **Padding:** 12px all sides
- **Button height:** 36px (consistent with existing)

### Container 2: "Save Options"
- **Purpose:** Export calculation results in various formats
- **Layout:** Three equal-width buttons in a row
- **Contents:** Save PDF | Save CSV | Save Cloud
- **Spacing:** 8px between buttons, generous internal padding
- **Separator:** Top hairline (1px solid `#3d3d3d`) above button row
- **Padding:** 12px all sides
- **Button height:** 40px (prominent action feel)

### Container 3: "Add Next Month"
- **Purpose:** Quick action to add the next month's calculation
- **Layout:** Single centered button
- **Contents:** "Add Next Month" button only
- **Spacing:** Generous vertical padding (16px top/bottom)
- **Separator:** Dotted line (1px dotted `#4a4a4a`) above button
- **Padding:** 16px all sides
- **Button height:** 36px

## Shared Styling
- Background: `#2b2b2b`
- Border: `1px solid #3d3d3d`
- Border-radius: `8px`
- Font: Inherited from application defaults
- No color accents, no glassmorphism, no glow effects
- `WA_StyledBackground = True`, `WA_Hover = False`, `MouseTracking = False`
- `FocusPolicy = Qt.NoFocus` on containers

## Edge Cases

### Responsive Behavior
- All containers use `QSizePolicy.Expanding` horizontally
- Buttons use stretch factors to distribute space evenly
- No fixed widths that could cause overflow at narrow windows
- Minimum window size (1000px) already enforced by main window

### Existing Functionality Preservation
- `load_info_source_combo` visibility toggle (hidden, replaced by dropdown button)
- `_update_source_button_color()` method for source button styling
- All `clicked` signal connections preserved
- `add_month_action()` method unchanged
- `load_info_to_inputs()` method unchanged
- `save_to_pdf()`, `save_calculation_to_csv()`, `save_calculation_to_supabase()` unchanged

### Layout Stability
- No geometry conflicts from fixed heights
- Containers use `QSizePolicy.Minimum` vertically to hug content
- Spacing values chosen to prevent overlap at any size
- `resizeEvent` handler unchanged (no column adjustments needed for vertical flow)

## Files Modified

- `src/ui/tabs/main_tab.py` — `create_load_info_group()` method refactored into three container methods

## Implementation Approach

Replace the current `create_load_info_group()` method with three new methods:
1. `_create_load_data_container()` — Container 1
2. `_create_save_options_container()` — Container 2
3. `_create_add_next_month_container()` — Container 3

The `init_ui()` method's Actions section setup is updated to call these three methods and stack them vertically inside the existing `actions_layout`.

All existing widget references (`load_month_combo`, `load_year_spinbox`, `load_source_button`, etc.) are preserved on `self` to maintain compatibility with other methods.
