# Home Unit Calculator Startup Flicker Fix Plan

Date: 2026-04-07
Status: Implemented
Owner: OpenCode + User
Depends on: `docs/plans/2026-04-04-application-optimization-plan.md`

## Purpose

This document records the assessment, chosen fix strategy, implementation plan, and validation for the packaged-app startup flicker seen before the dashboard appears.

The goal was to remove the visible first-frame flicker without regressing:

1. startup speed
2. dashboard responsiveness
3. the new realtime polling and coordinator flow
4. deferred cloud initialization

## Problem Summary

In the installed EXE, the app visibly flickered before the dashboard became stable.

This degraded the perceived quality of the app even though warm startup timing was already good.

## Assessment

### Likely causes

1. The main window was shown before the default dashboard page was stable.
2. The default dashboard route used a placeholder-first lazy mount, then swapped to the real dashboard immediately after first show.
3. The dashboard applied an application-wide tooltip stylesheet after startup UI was already visible.
4. The title bar icon could be re-applied again on the initial tab-change path, adding another startup-time repaint.
5. Packaged runtime overhead made those transitions visible for longer than in local source runs.

### Root cause ranking

1. Placeholder-first default dashboard mount
2. Late dashboard-wide stylesheet mutation
3. Initial title-bar icon reset on first tab selection

### Constraints

The fix had to preserve:

1. deferred cloud initialization
2. lazy loading for non-default tabs
3. current dashboard background worker behavior
4. realtime polling responsiveness
5. current startup optimizations from earlier phases

## Chosen Solution

The safest high-confidence approach was:

1. synchronously mount the dashboard shell before the window is shown
2. keep all heavy and cloud-related work deferred
3. move tooltip appearance to the existing global stylesheet path instead of mutating the app stylesheet after startup
4. suppress the startup-time title-bar icon reapply and keep it only for later tab switches

This preserves the startup architecture while removing the most visible repaint and placeholder transitions.

## Implementation Plan

## Step 1 - Stable First Paint

Change:

1. Pre-mount the dashboard shell before first show.
2. Keep the dashboard as the default page.
3. Keep other tabs lazy.

Reason:

This removes the visible placeholder-to-dashboard swap from the user-visible startup path.

## Step 2 - Remove Late Global Repaint Trigger

Change:

1. Stop resetting the entire application stylesheet from `DashboardTab._configure_tooltips()`.
2. Move the tooltip styling into the existing global dark stylesheet.

Reason:

Late `app.setStyleSheet(...)` calls can trigger broad widget repolish and visible first-frame flicker.

## Step 3 - Stabilize Initial Title Bar Visuals

Change:

1. Keep title-bar icon setup before show.
2. Avoid the extra startup-time icon reapply on the initial tab-change path.
3. Continue allowing icon reapply on later user-driven tab changes.

Reason:

This removes a startup repaint source without losing the later protection against QFluentWidgets resetting the title-bar icon on navigation changes.

## Step 4 - Preserve Existing Responsiveness Strategy

Do not change:

1. deferred cloud initialization timing
2. dashboard post-init background work structure
3. realtime polling setup
4. hidden-tab queued refresh behavior

Reason:

The fix should be visual-stability-focused, not a broader startup architecture rewrite.

## Implemented Changes

### `src/core/HomeUnitCalculator.py`

1. Added `_prepare_initial_interface_for_show()`.
2. Synchronously mounted the dashboard shell before first show.
3. Added `_startup_visuals_stable` guard.
4. Prevented the initial `on_current_interface_changed()` path from re-applying the title-bar icon during startup.
5. Added `showEvent()` to mark the app as visually stable after the first show.

### `src/ui/tabs/dashboard_tab.py`

1. Removed the late `app.setStyleSheet(...)` mutation from `_configure_tooltips()`.
2. Kept tooltip font setup only.

### `src/core/HomeUnitCalculator.py` global stylesheet

1. Updated the global `QToolTip` style to match the dashboard tooltip appearance.
2. This makes tooltip styling available before first paint.

## Validation and Verification

### Automated verification

1. `python -m py_compile` on changed modules passed.
2. Focused regression suite passed:
   - `tests/test_startup_smoke.py`
   - `tests/test_update_coordinator.py`
   - `tests/test_remote_change_monitor.py`
   - `tests/test_realtime_local_changes.py`
3. A new startup smoke test was added to verify synchronous dashboard-shell preparation.

### Startup profiling

1. Startup profiler was re-run after the flicker fix.
2. No code change in this slice intentionally moved cloud work onto the startup-critical path.
3. The fix remained focused on first-frame stability rather than adding blocking work.

### Realtime safety

The implemented fix does not change:

1. dashboard worker lifecycle
2. remote polling monitor behavior
3. local/remote coordinator event routing
4. queued hidden-tab refresh behavior
5. history async cloud loading

## Remaining Risks / Follow-up

1. Packaged EXE visual behavior still needs user confirmation after rebuild because visual flicker cannot be fully asserted by automated tests alone.
2. Title-bar icon handling is still more complex than ideal and could be simplified further later if residual chrome flicker remains.
3. If packaged cold start still shows a visible visual flash after this fix, the next escalation path should be a hidden-first-show or splash strategy, but only after validating this lower-risk fix first.

## Success Criteria

This fix is considered successful if:

1. the installed EXE no longer shows a visible placeholder or rapid visual swap before the dashboard appears
2. the first visible frame is a stable dashboard shell
3. startup timing does not materially regress
4. dashboard realtime responsiveness remains unchanged

## Change Log

### 2026-04-07

1. Assessed packaged startup flicker causes.
2. Identified placeholder-first dashboard mounting, late tooltip stylesheet mutation, and startup-time title-bar icon reapply as the highest-confidence causes.
3. Implemented a stable first-paint startup path without touching deferred cloud/realtime behavior.
