# Home Unit Calculator Realtime UI Responsiveness Plan

Date: 2026-04-06
Status: In Progress
Owner: OpenCode + User
Depends on: `docs/plans/2026-04-04-application-optimization-plan.md`

## Purpose

This plan defines the next optimization phase focused on:

1. real-time data propagation
2. cross-tab UI consistency
3. safe external-change handling
4. UI responsiveness during live updates
5. preserving user context during background refresh

This plan does not change core functionality.

## Confirmed Decisions

1. Supabase remains the canonical source of truth for main calculations/history and rental records/documents.
2. Local SQLite remains the cache/performance/offline-read layer.
3. Realtime target model is hybrid local+cloud.
4. Local actions should update the UI optimistically.
5. External changes from other devices should appear within about 1-3 seconds.
6. Realtime scope includes dashboard, history tab, rental info, archived info, main calculation view, and cross-tab state.
7. Conflicting remote changes should notify and defer apply when the user is actively editing.
8. The system should preserve selection as the highest-priority UI continuity rule.
9. Live-update feedback should be subtle.
10. Feedback should use a single global status area.
11. Realtime scope is records and derived UI data, not live media-content refresh.
12. If push/realtime is unavailable, the app should fall back to polling.
13. Visible-tab priority should win over keeping all tabs equally hot.
14. Smoothness should win over absolute freshness when there is short-term tension.
15. During active editing, relevant remote changes should be held back until the edit session ends.
16. External changes are primarily expected to come from the user's other devices/sessions.

## Current Architecture Assessment

### What exists today

1. The app is mostly pull-based, not true realtime.
2. Dashboard uses cache-first rendering plus worker-based background sync.
3. Rental and archived tabs use worker threads for cloud fetch.
4. History tab cloud loading is still synchronous on the UI thread.
5. Cross-tab refresh behavior is inconsistent and mostly explicit/manual.
6. There is no centralized update coordinator or event model.
7. There is no active Supabase realtime subscription layer in runtime code.

### Main architectural gaps

1. No app-wide change propagation model.
2. No unified distinction between local optimistic changes, remote external changes, and stale-cache reconciliation.
3. No shared policy for active editing, deferring remote updates, and preserving UI context.
4. History tab is especially vulnerable to UI churn if naive realtime is added.
5. Rental mutations do not consistently propagate to dashboard/history/archived/main views.
6. Tabs currently learn about data changes in different ways.

## Goals

### Primary goals

1. Make in-app local actions reflect immediately across relevant UI surfaces.
2. Make external cloud changes appear within about 1-3 seconds.
3. Keep the UI responsive and stable while updates are applied.
4. Prevent remote changes from clobbering active user edits.
5. Preserve selection and avoid disruptive full-screen or full-table refreshes where possible.
6. Add one global status area for live-state visibility.

### Secondary goals

1. Reduce duplicate refresh logic across tabs.
2. Improve consistency of stale-data handling.
3. Build a clear platform for later medium-risk refactors.
4. Keep background work proportional to app visibility and active tab.

## Current Progress

### Completed in the first implementation slice

1. Added `src/core/update_coordinator.py` as the initial app-wide update coordinator skeleton.
2. Added a single subtle global status area in the main window title bar.
3. Wired coordinator status into the main window so it can show startup, local-only, polling-fallback, syncing, and deferred-edit states.
4. Connected initial cloud initialization state to the coordinator.
5. Connected dashboard worker lifecycle to the coordinator so the global status area reflects real background sync activity.
6. Added focused regression tests for coordinator status transitions and edit-session deferral behavior.

### Completed in the second implementation slice

1. Routed local `main_calculation` and `rental` mutation events through the coordinator from successful save, archive, and delete paths.
2. Added minimal main-window local-change handlers that refresh dependent loaded surfaces instead of relying only on ad hoc direct calls.
3. Added rental dialog edit-session begin and end hooks through the coordinator.
4. Removed redundant direct rental-tab refresh calls from the rental dialog where the coordinator path now owns propagation.
5. Added focused regression coverage for local realtime mutation handling across dashboard, history, and rental surfaces.

### Completed in the third implementation slice

1. Added `FetchSupabaseHistoryWorker` so cloud history loading can happen off the UI thread.
2. Switched the history tab's cloud load entry path to the new async worker flow.
3. Reused the existing history rendering path after async fetch completion so the visual behavior stayed consistent.
4. Wired history cloud loading into the global update activity state.
5. Added focused regression tests for async history fetching and prefetched room-record reuse.

### Completed in the fourth implementation slice

1. Added coordinator-aware edit-session protection around the history edit dialog flow.
2. Emitted local `main_calculation` change events from accepted history edits and successful history deletes.
3. Collapsed the worst duplicate post-load history resize and width-application passes into one shared finalization helper.
4. Reduced delayed force-resize scheduling after history data load from multiple redundant timers to one coordinated deferred resize.
5. Added focused regression coverage for history edit-session wiring and coalesced post-load finalization behavior.

### Completed in the fifth implementation slice

1. Added polling-based remote external-change detection instead of websocket realtime, matching the current packaged runtime constraints.
2. Added signature helpers for main calculations, room calculations, and rental records.
3. Added a remote snapshot worker plus `RemoteChangeMonitor` to poll cloud change signatures in the background.
4. Connected remote change events through the coordinator and added deferred remote replay after edit sessions end.
5. Wired remote change handling into dashboard, history, rental, and archived surfaces.
6. Added one-event local echo suppression so a local save does not immediately trigger a duplicate remote refresh on the next poll.
7. Added focused regression coverage for deferred remote replay and remote polling suppression behavior.

### Completed in the sixth implementation slice

1. Added visible-tab priority behavior for heavy surfaces using a queued refresh model for hidden tabs.
2. Implemented pending refresh flushing when a queued tab becomes active.
3. Added archived record dialog coordinator edit-session hooks, matching rental and history flows.
4. Added focused regression coverage for queued tab refresh behavior.

### Completed in the seventh implementation slice

1. Added selection preservation helpers for rental and archived tables so active row continuity survives refreshes where possible.
2. Restored selection by stable record identifier after rental and archived table repopulation.
3. Added focused regression coverage for rental and archived selection restoration behavior.

## Non-Goals

1. Replacing PyQt5, QFluentWidgets, or Supabase.
2. Making media/image/document content itself live-reload in realtime.
3. Turning the app into a fully offline-first sync engine.
4. Rebuilding all tabs around a new architecture in one pass.
5. Making every hidden tab update at the same rate as the visible tab.

## Design Principles

1. Realtime should update models and caches first, widgets second.
2. No direct widget mutation from network callbacks or worker threads.
3. No full-table or full-tab reload for every incoming change.
4. Coalesce first, repaint second.
5. Preserve user continuity over theoretical freshness.
6. Defer conflicting remote changes during active edits.
7. Keep changes incremental and testable.

## Target Architecture

## 1. Update Coordinator

Introduce one central app-level update coordinator responsible for:

1. receiving local mutation events
2. receiving remote change events
3. receiving fallback polling results
4. deduplicating and coalescing changes
5. deciding whether a change should apply immediately, mark a surface stale, queue until editing ends, or be ignored as duplicate

Recommended responsibilities:

1. domain-scoped event dispatch
2. visible-tab priority logic
3. edit-session protection
4. global status updates
5. tab-facing refresh signals with minimal payloads

Recommended event categories:

1. main calculation changed
2. room calculations changed
3. rental changed
4. archive status changed
5. record deleted
6. cloud connection state changed
7. live updates degraded to polling
8. deferred remote update pending

## 2. Global Status Area

Add one global status area in the main window.

It should show subtle state such as:

1. Live
2. Syncing
3. Polling fallback
4. Offline or stale
5. External updates pending
6. Editing protected from remote changes

Design requirements:

1. always visible from all tabs
2. low-noise
3. no toast spam for normal updates
4. can show timestamp or last-successful-live-refresh
5. can surface conflict or deferred state without interrupting work

## 3. Change Detection Layer

Use a two-tier model.

### Primary

Supabase realtime subscriptions, if reliable in the packaged Windows runtime.

Scope:

1. main calculations
2. room calculations
3. rental records

### Fallback

Short-interval polling, signature, or watermark checks.

Rules:

1. push and polling both feed the same coordinator
2. push does not directly refresh widgets
3. push and polling events must be deduplicated
4. if realtime disconnects, the status area changes to fallback mode
5. polling cadence should be adaptive based on visibility

## 4. Local Mutation Pipeline

When the user changes data inside the app:

1. update the local view model or cache optimistically
2. notify relevant surfaces through the coordinator
3. mark pending-confirmation state if needed
4. write to cloud
5. on success:
   - clear pending state
   - update sync metadata
6. on failure:
   - show subtle failure state in the global status area
   - reconcile or rollback the affected surface safely

Must cover:

1. save main calculation
2. save room calculations
3. save rental record
4. edit rental record
5. archive or unarchive rental
6. delete main calculation
7. delete rental record

## 5. Edit-Session Protection

When the user is actively editing a record:

1. remote changes to that same record or domain must not be applied directly
2. coordinator queues the remote change
3. global status area shows a subtle deferred-update state
4. after save, cancel, or close:
   - reconcile queued remote changes
   - prompt or apply depending on change type

Recommended default:

1. hold relevant remote changes until the edit session ends
2. still allow unrelated surfaces to update normally

## Per-Surface Strategy

## Dashboard

Target behavior:

1. local calculation and rental changes update relevant KPIs and charts quickly
2. external changes update within 1-3 seconds
3. rerenders are scoped to affected year, scope, or room only
4. chart updates are coalesced

Implementation direction:

1. keep dashboard cache-first
2. coordinator invalidates only affected cache-backed slices
3. avoid starting duplicate sync workers
4. avoid rerendering all dashboard sections for one small change
5. keep room tenant labels in sync with rental changes

## History Tab

Target behavior:

1. reflects local and remote record changes without manual full reload
2. avoids blocking the UI thread
3. preserves selection where possible
4. does not trigger resize storms

Implementation direction:

1. move cloud history load to worker-based path
2. introduce incremental or section-based refresh logic
3. coalesce row updates before any table resize logic runs
4. avoid calling full load or rebuild paths for small deltas

## Rental Info

Target behavior:

1. local save, edit, archive, and delete update visible records immediately
2. remote changes appear quietly
3. active list stays in sync without full-table churn
4. selection continuity is preserved when practical

Implementation direction:

1. merge row-level changes into current model or page when possible
2. avoid rebuilding the full table on each change
3. preserve sort and filter state
4. keep cloud paging consistent with live updates

## Archived Info

Target behavior:

1. archive and unarchive transitions appear consistently with active rental info
2. external changes flow in with minimal delay
3. hidden archived tab can remain less aggressive than the visible tab

Implementation direction:

1. mirror the rental-info update contract
2. prefer incremental changes over full rebuild
3. add similar consistency guarantees across active and archived views

## Main Calculation View

Target behavior:

1. local saves update dependent surfaces immediately
2. remote changes to the same month or year are deferred if the user is editing
3. stale state is visible subtly, not destructively

Implementation direction:

1. emit explicit local mutation events after save
2. detect same-record remote changes
3. queue conflicts during active editing
4. reconcile after edit completes

## Cross-Tab State

Target behavior:

1. no manual mystery stale state
2. relevant tabs know when their data is dirty
3. the global status area reflects app-wide live state

Implementation direction:

1. tab-level dirty markers from the coordinator
2. optional tiny internal counters or state flags
3. avoid navigation changes or noisy interruptions

## Refresh Priority Model

### Visible and foreground behavior

1. active tab gets fastest update cadence
2. visible-but-not-active surfaces can update less aggressively
3. minimized app should throttle strongly

Recommended policy:

1. active tab:
   - push-driven immediate coalesced apply
   - polling fallback short interval
2. loaded but hidden tabs:
   - mark dirty or stale
   - defer heavy UI work until focus
3. minimized app:
   - maintain lightweight change detection only
   - delay expensive UI or model recompute until restore

## Implementation Phases

## Phase R0 - Baseline and Instrumentation

Goals:

1. map current refresh triggers and blocking paths precisely
2. add metrics for update latency, worker overlap, table rebuild count, resize trigger count, and rerender count per tab

Deliverables:

1. update-latency instrumentation
2. change-source tagging
3. baseline runtime scenarios

## Phase R1 - Coordinator and Global Status

Goals:

1. add central update coordinator
2. add single global status area
3. route local mutation events through the coordinator first

Candidate files:

- `src/core/HomeUnitCalculator.py`
- new coordinator module under `src/core/`
- tab hookup points in dashboard, history, rental, archived, and main

Exit criteria:

1. one app-wide status area exists
2. local mutations propagate through a unified path
3. no functional regressions

## Phase R2 - Remote Detection Layer

Goals:

1. add push-based realtime if runtime reliability is acceptable
2. add polling fallback that feeds the same event model

Candidate files:

- `src/core/supabase_manager.py`
- `src/ui/background_workers.py`
- new coordinator or realtime adapter module

Exit criteria:

1. external changes can be detected within target latency
2. fallback mode is explicit and safe
3. no duplicate application of the same remote change

## Phase R3 - Edit Protection and Conflict Handling

Goals:

1. protect active editing
2. queue conflicting remote changes
3. show deferred state subtly

Candidate files:

- `src/ui/rental_record_dialog.py`
- `src/ui/tabs/main_tab.py`
- `src/ui/tabs/history_tab.py`
- coordinator module
- `src/core/HomeUnitCalculator.py`

Exit criteria:

1. editing is not interrupted by remote changes
2. deferred state is visible in the global status area
3. reconcile-after-edit behavior is deterministic

## Phase R4 - Per-Surface Incremental Updates

Goals:

1. remove full-refresh default behavior from live update paths
2. add incremental or coalesced updates for each surface

Order:

1. dashboard
2. rental info
3. archived info
4. history
5. main calculation view

Exit criteria:

1. affected surfaces update without obvious UI churn
2. selection continuity is preserved where applicable
3. live update does not force heavy repeated resize paths

## Phase R5 - Responsiveness Hardening

Goals:

1. reduce resize and repaint storms under live-update conditions
2. remove remaining synchronous hot paths that conflict with realtime behavior

Priority targets:

1. `src/ui/tabs/history_tab.py`
2. `src/ui/tabs/rental_info_tab.py`
3. `src/ui/tabs/archived_info_tab.py`
4. `src/ui/tabs/dashboard_tab.py`

Exit criteria:

1. active use remains smooth under repeated incoming changes
2. tab switching is not degraded by background updates
3. no obvious repaint storm or full-table thrash patterns remain

## Edge Cases

1. external update arrives for currently edited rental record
2. external delete arrives for visible history or main record
3. remote archive or unarchive affects both active and archived tabs
4. remote room rename or remove under changed parent
5. duplicate push and polling event for the same change
6. app loses realtime and falls back to polling
7. app regains realtime after degraded mode
8. visible filtered table receives update for an off-screen row
9. selected row is deleted remotely
10. local optimistic save fails after the UI already updated
11. many remote changes arrive while app is minimized
12. hidden lazy-loaded tab becomes visible after many queued changes
13. stale cache plus valid remote push on resume
14. Supabase partial or error response during live update cycle

## Validation Matrix

### Automated tests

1. coordinator event routing
2. local optimistic update propagation
3. deferred remote update during active edit
4. push and poll deduplication
5. visible-tab priority behavior
6. stale marker and status-area state transitions
7. cross-tab consistency after local save, edit, delete, and archive
8. incremental room, main, and rental update application
9. history worker-based refresh behavior
10. selection-preservation behavior where practical

### Runtime verification

1. local save in main calculation updates dashboard, history, and main consistently
2. rental save, edit, archive, and delete update rental, archived, and dashboard state consistently
3. second-device changes appear within 1-3 seconds
4. active editing is not interrupted
5. minimized app does not churn excessively
6. reconnect from polling fallback to push mode is visible and stable
7. no full-screen placeholder or stale stuck states

### Performance checks

1. no repeated full-table rebuild on every event
2. history live updates do not trigger repeated forced resize passes
3. dashboard chart and KPI updates remain smooth
4. active tab remains responsive under repeated incoming changes
5. memory does not grow abnormally during long-running sessions

## Risks

1. realtime subscriptions may behave differently in packaged Windows builds versus local source runs
2. naive event fan-out can create duplicate UI work
3. history tab may need more structural cleanup than other surfaces
4. pagination plus live updates in rental and archive can complicate row continuity
5. active-edit deferral requires clear ownership of what is being edited

## Recommended Success Criteria

1. local actions feel immediate across dependent surfaces
2. external changes appear within 1-3 seconds on the active tab
3. active editing is never silently clobbered
4. the UI remains smooth under normal live-update volume
5. the app communicates live, degraded, and deferred state via one subtle global status area
6. no core workflow regressions

## Proposed File Targets

- `src/core/HomeUnitCalculator.py`
- new coordinator and status modules under `src/core/`
- `src/core/supabase_manager.py`
- `src/ui/background_workers.py`
- `src/ui/tabs/dashboard_tab.py`
- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/tabs/archived_info_tab.py`
- `src/ui/rental_record_dialog.py`

## Immediate Next Actions

1. Start deeper per-surface incremental update integration with dashboard, rental info, and archived info.
2. Replace remaining full-table refresh paths with row-level or page-level apply logic where practical.
3. Continue reducing remaining history-table resize churn outside the main post-load path.
4. Refine remote poll cadence and scope further if runtime measurements show unnecessary churn.
5. Add broader end-to-end runtime validation of polling-driven external updates across visible and hidden tabs.

## Open Questions

1. None blocking for the design phase.

## Change Log

### 2026-04-06

1. Created dedicated planning direction for realtime data propagation, cross-tab UI consistency, and UI responsiveness under live updates.
2. Confirmed hybrid local+cloud realtime model, optimistic local updates, deferred remote apply during active edits, visible-tab priority, polling fallback, and a single global status area.
3. Implemented the first realtime foundation slice with an update coordinator skeleton, a single global status area, and initial dashboard/cloud-status wiring.
4. Implemented the second realtime slice with local mutation routing for main and rental changes plus rental edit-session coordinator hooks.
5. Implemented the third realtime slice by moving history cloud loading onto a worker-based async path and integrating it with the global update activity state.
6. Implemented the fourth realtime slice by wiring history edit protection into the coordinator and consolidating the heaviest post-load history resize passes.
7. Implemented the fifth realtime slice by adding polling-based remote external-change detection, queued remote replay after editing, and coordinator-driven remote fan-out.
8. Implemented the sixth realtime slice by adding visible-tab priority with queued refreshes for hidden heavy tabs.
9. Implemented the seventh realtime slice by preserving active selection across rental and archived table refreshes.
