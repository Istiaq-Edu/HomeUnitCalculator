# Home Unit Calculator Optimization Plan

Date: 2026-04-04
Status: In Progress
Owner: OpenCode + User
Primary target: Installed Windows app on a typical mid-range PC

## Purpose

This is the living implementation plan for improving the Home Unit Calculator application without changing its core functionality.

Related follow-on plan:

- `docs/plans/2026-04-06-realtime-ui-responsiveness-plan.md`

This plan is based on:

- direct codebase assessment
- parallel architecture, performance, data-flow, and test-gap reviews
- confirmed product and technical decisions from the interview

This file should be updated as work progresses.

## Confirmed Decisions

These decisions are treated as constraints for all implementation work unless explicitly changed later.

1. Supabase is the canonical source of truth for main calculations and history.
2. Supabase is the canonical source of truth for rental records and documents.
3. Local SQLite remains for app config, encrypted credentials, caches, and read-only offline support.
4. CSV remains supported for import/export and legacy interoperability, not as the primary workflow.
5. Offline support is read-only cache, not full offline-first write syncing.
6. The highest-priority outcome is startup speed, with a target of roughly 2-3 seconds for the installed Windows app on typical hardware.
7. Other top priorities are smoother large-data UI, better cloud efficiency, better maintainability, and lower memory usage.
8. Significant UX cleanup is acceptable as long as core workflows and business behavior do not change.
9. Testing investment should be high before risky refactors.
10. Delivery should be a balanced mix of quick wins and foundational cleanup.
11. Core stack stays in place, with only minor dependency upgrades allowed.
12. Core workflows are all equally non-negotiable and must not regress.

## Core Principles

1. No feature removal disguised as optimization.
2. No rewrite unless a smaller safe path is exhausted first.
3. No storage ambiguity: cloud-first correctness, local cache-first performance.
4. Every phase must have verification gates and rollback boundaries.
5. Extract pure logic before large UI refactors whenever practical.
6. Prefer smaller, behavior-preserving changes over broad speculative redesign.

## Success Criteria

### Primary success criteria

1. Installed app startup reaches a typical 2-3 second range on a mid-range Windows machine.
2. First paint happens quickly and the UI does not freeze during startup.
3. Large history, rental, and dashboard views remain responsive during load, resize, scroll, and filter actions.
4. Cloud-backed reads are measurably more efficient and avoid obvious N+1 patterns.
5. The codebase is safer to change because key behavior is covered by automated tests.

### Secondary success criteria

1. Memory usage after visiting heavy views is lower or more stable.
2. Packaged app behavior is more consistent than source-run behavior.
3. Error handling and stale-cache behavior are clearer to users.
4. CSV is demoted to a support format rather than a competing runtime model.

## Current Progress

### Completed in the first implementation slice

1. Added an initial pytest-based startup smoke suite.
2. Added an offscreen Qt test setup for safe headless verification.
3. Deferred `MainTab` and `RoomsTab` imports behind startup factories.
4. Deferred `SaveDialog` import until the PDF save path is used.
5. Removed one redundant startup-time `EncryptionUtil` initialization from the main window.
6. Fixed the startup profiler and performance comparison tools to use ASCII-safe console output on Windows.

### Completed in the second implementation slice

1. Removed additional unused top-level imports from `src/core/HomeUnitCalculator.py`.
2. Deferred `DashboardTab` import so it no longer loads at `HomeUnitCalculator` module import time.
3. Deferred `APIError` import to the Supabase save path.
4. Moved keyboard navigation manager initialization just after first paint.
5. Deferred dashboard post-construction work so tooltip styling, cache hydration, and Supabase year polling no longer run directly inside `DashboardTab.__init__`.
6. Deferred dashboard worker-class imports to the methods that first use them.
7. Added `tools/measure_packaged_startup.ps1` for repeatable portable or installed packaged-startup measurement.

### Completed in the third implementation slice

1. Removed a leftover synchronous tooltip-style setup call from `DashboardTab.__init__`.
2. Deferred the secondary dashboard chart widgets behind lightweight placeholders.
3. Hydrated deferred chart widgets after first paint using already-cached values.
4. Added a startup smoke test that constructs `DashboardTab` with deferred post-init work.

### Completed in the fourth implementation slice

1. Switched the dashboard route from eager tab creation to the same placeholder-backed lazy mounting path used by the other tabs.
2. Kept the dashboard as the default selected navigation page while moving actual dashboard construction to the first event-loop turn.
3. Reduced `MeterCalculationApp` constructor cost sharply by removing dashboard shell construction from the blocking startup path.

### Completed in the fifth implementation slice

1. Created a local portable PyInstaller build and captured the first real packaged startup baseline.
2. Checked in a deterministic `HomeUnitCalculator.spec` build path and updated CI to use it.
3. Enabled repo-local PyInstaller hooks for Supabase and realtime packaging behavior.
4. Confirmed that `matplotlib`, `IPython`, `pytest`, and `tkinter` were not the main packaged startup bottleneck.
5. Verified that `qfluentwidgets` only uses `numpy` and `scipy` for optional acrylic blur.
6. Excluded `numpy` and `scipy` from the packaged app and relied on qfluentwidgets' acrylic fallback path.
7. Rebuilt and re-measured the portable package after the dependency trim.

### Completed in the sixth implementation slice

1. Added batched SQLite write support for cache syncs in `src/core/db_manager.py`.
2. Switched main-calculation, room-calculation, and rental-record cache upserts from row-by-row commits to one transaction per sync batch.
3. Added focused regression tests for cache upsert replacement behavior.
4. Added a bulk Supabase room-fetch helper keyed by `main_calculation_id`.
5. Replaced the main N+1 room-fetch paths in dashboard sync and history cloud load/export with the new bulk path.
6. Added focused regression tests for grouped bulk room fetch behavior.

### Completed in the seventh implementation slice

1. Changed dashboard rental-cache sync to fetch the full rental set instead of active-only rows.
2. Added cache reconciliation for `rental_records_cache` so deleted cloud rows are pruned locally.
3. Preserved archived rental rows in cache so dashboard tenant timeline resolution can remain correct.
4. Recorded rental cache sync watermark state for later incremental-sync work.
5. Added focused regression coverage for stale-rental cache removal.

### Completed in the eighth implementation slice

1. Added a stable signature for rental cloud metadata based on record identity plus effective timestamps.
2. Changed the rental cache worker to fetch a narrow metadata set first and skip the full sync when the cloud signature has not changed.
3. Ensured the full rental sync still runs when inserts, updates, deletes, or archive changes alter the cloud signature.
4. Added focused regression tests covering signature stability, sync skipping, and successful full-sync fallback.

### Completed in the ninth implementation slice

1. Optimized dashboard room-mode tooltip rendering to load rental history once per room render instead of re-querying SQLite for each month.
2. Precomputed tenant timeline entries once and reused them across all 12 monthly tooltip lookups.
3. Added focused regression tests for tenant timeline resolution, precomputed tooltip lookup use, and room-number candidate fallback behavior.

### Completed in the tenth implementation slice

1. Added a shared yearly `main_calculations_cache` snapshot helper in `DBManager` that reads totals, per-unit cost, total electricity, and last-sync metadata in one pass.
2. Switched dashboard bill, rate, electricity, and metadata rendering to reuse the shared yearly snapshot instead of issuing separate repeated cache reads and JSON parses.
3. Added focused regression coverage for the yearly snapshot helper, including invalid JSON handling.

### Completed in the eleventh implementation slice

1. Added small normalization helpers in `history_tab.py` for Supabase JSON payloads.
2. Switched cloud history-load and cloud CSV-export paths to normalize `main_data` and `room_data` once per fetched record instead of repeatedly reparsing the same JSON strings.
3. Preserved existing sort order, max-meter logic, and output shape while reducing duplicate work.
4. Added focused regression coverage for the Supabase history normalization helpers.

### Completed in the twelfth implementation slice

1. Added stale-row pruning helpers for yearly `main_calculations_cache` and `room_calculations_cache` reconciliation.
2. Changed yearly main and room sync workers to prune missing local rows after successful full-year cloud syncs.
3. Explicitly limited pruning to full-sync paths so delta syncs cannot accidentally delete unchanged cache rows.
4. Added focused regression tests for cache pruning helpers and full-sync-only worker behavior.

### Completed in the thirteenth implementation slice

1. Added targeted pruning for incremental room syncs so changed `main_record_id` parents can remove stale cached child room rows even during delta syncs.
2. Added focused regression coverage proving that incremental room pruning is scoped to the changed parent only.

### Completed in the fourteenth implementation slice

1. Enabled SQLite `WAL` mode and `busy_timeout` for better local cache concurrency behavior.
2. Added surgical indexes for the current hot cache and rental query paths.
3. Replaced deprecated `datetime.utcnow()` calls in `DBManager` with timezone-aware UTC timestamps.
4. Reduced the focused test-suite warning count to dependency-only warnings.

### Current baseline data

Source-run startup profiler after the first patch set:

1. Earlier source-run baseline after first patch set: about `1.692s`
2. Current source-run baseline after the second startup slices: about `1.810s`
3. Current source-run baseline after the third startup slice: about `1.815s`
4. Current source-run baseline after the fourth startup slice: about `1.447s`
5. `Import application (core.HomeUnitCalculator)` dropped from about `0.317s` to about `0.050s`
6. `Create MeterCalculationApp` dropped from about `0.485s` to about `0.117s`
7. Internal startup timer total inside the app window path dropped from about `0.535s` to about `0.167s`
8. First packaged portable baseline before trimming `numpy` and `scipy`:
9. Portable cold start: about `13.2s`
10. Portable warm starts: about `1.38s` to `1.39s`
11. Portable packaged baseline after trimming `numpy` and `scipy`:
12. Portable cold start: about `6.0s`
13. Portable warm starts: about `0.98s` to `1.01s`

Notes:

1. This is a source-run baseline, not the final installed-app baseline.
2. Installed portable and installed packaged measurements are still required for the primary success target.
3. The latest startup work confirms that eager dashboard construction was the main remaining app-side startup bottleneck.
4. Lazy-mounting the dashboard preserved the default page while materially reducing constructor time.
5. The largest remaining startup costs are now framework import cost and post-show event-loop work, not app-shell construction.
6. The largest packaged cold-start penalty was strongly correlated with shipping `numpy` and `scipy` for an optional acrylic blur path the app does not use.
7. Warm portable packaged startup is now under the 2-3 second target.

## Current Architecture Snapshot

### Main composition root

- `src/core/HomeUnitCalculator.py`
  - startup bootstrapping
  - app shell and navigation
  - theme and styling
  - tab orchestration
  - save/load orchestration
  - some cross-cutting UI behavior

### Large high-risk UI modules

- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/tabs/dashboard_tab.py`

### Data and integration modules

- `src/core/db_manager.py`
- `src/core/supabase_manager.py`
- `src/ui/background_workers.py`
- `src/core/optimized_image_fetcher.py`

### Shared UI performance-related modules

- `src/core/lazy_tab_loader.py`
- `src/core/startup_timer.py`
- `src/ui/components/enhanced_table_mixin.py`
- `src/ui/components/table_optimization.py`
- `src/ui/responsive_testing.py`

## Main Problems To Solve

1. Startup still performs too much synchronous work and imports too much too early.
2. History and some sync paths appear to use N+1 cloud fetch patterns.
3. SQLite cache writes are heavier than they need to be.
4. Some table resize and render paths do repeated expensive work.
5. Archived and some cloud views scale worse than active rental views.
6. Cross-tab coupling and large files make safe optimization harder.
7. Automated regression coverage is much weaker than the complexity level of the app.
8. Cache invalidation and multi-device stale-data behavior are not explicit enough.

## Non-Goals

1. Replacing PyQt5, QFluentWidgets, or Supabase.
2. Turning the app into a fully offline-first system.
3. Removing CSV support entirely in the near term.
4. Introducing breaking data changes without migration safeguards.
5. Performing large stylistic refactors that do not support the optimization goals.

## Workstreams

The implementation program is split into five parallel concerns that can be advanced in coordinated phases.

1. Safety and testing
2. Startup and packaging performance
3. Data flow and sync efficiency
4. Heavy-view responsiveness and memory usage
5. Structural cleanup and UX polish

## Phase Plan

## Phase 0 - Baseline, Rules, and Safety Setup

Status: In Progress
Priority: Critical

### Goals

1. Lock in the architectural rules so later optimizations do not pull the app in conflicting directions.
2. Establish measurable baselines before changing behavior.
3. Set up regression protection around the most critical flows.

### Scope

1. Create a source-of-truth matrix by feature.
2. Document cache ownership and invalidation rules.
3. Define acceptable startup, memory, and responsiveness baselines.
4. Add lightweight startup and runtime smoke checks.
5. Add initial automated tests around the highest-risk modules.

### Candidate files

- `src/core/HomeUnitCalculator.py`
- `src/core/lazy_tab_loader.py`
- `src/core/startup_timer.py`
- `src/core/db_manager.py`
- `src/core/encryption_utils.py`
- `src/core/key_manager.py`
- `src/ui/responsive_testing.py`
- `tools/startup_profiler.py`
- `tools/compare_performance.py`
- test files to be added under a dedicated test directory

### Deliverables

1. A baseline metrics capture for source run and packaged installed run.
2. A smoke test path for app startup and shutdown.
3. Initial tests for pure utility and infrastructure behavior.
4. A documented validation matrix.

### Exit criteria

1. Startup and packaging numbers are recorded.
2. A basic automated safety net exists.
3. Architectural decisions in this plan are treated as implementation constraints.

## Phase 1 - Startup Optimization First

Status: Planned
Priority: Critical

### Goals

1. Improve perceived and measured startup time first.
2. Get the installed app near the 2-3 second target without destabilizing core flows.

### Scope

1. Audit eager imports in the startup path.
2. Remove or defer imports that defeat lazy loading.
3. Move non-critical initialization off the first visible window path.
4. Ensure connectivity checks and Supabase initialization do not block the UI thread.
5. Re-measure source, packaged portable, and installed startup behavior after each logical improvement.

### Candidate files

- `src/core/HomeUnitCalculator.py`
- `src/core/lazy_tab_loader.py`
- `src/core/startup_timer.py`
- `src/core/utils.py`
- `src/ui/background_workers.py`
- `src/ui/tabs/dashboard_tab.py`
- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/tabs/archived_info_tab.py`

### Planned tactics

1. Remove tab imports from the startup path when they are meant to be lazy.
2. Delay cloud setup until after first paint unless truly required.
3. Move non-essential image/cache preparation out of startup.
4. Isolate startup-critical versus post-startup initialization.
5. Use the startup timer to prove each change moved the right checkpoint.

### Risks

1. Lazy-import changes may expose hidden circular dependencies.
2. Deferred initialization may break code that assumes a service exists too early.

### Exit criteria

1. First visible window time is substantially improved.
2. Startup no longer blocks on avoidable network or heavy module work.
3. Lazy tab creation remains correct under smoke and navigation tests.

## Phase 2 - Cloud and Cache Efficiency

Status: In Progress
Priority: Critical

### Goals

1. Make Supabase-backed behavior efficient and predictable.
2. Make SQLite caches faster and better aligned with the cloud-first model.

### Scope

1. Remove obvious N+1 fetch patterns.
2. Batch cache writes and reduce unnecessary commits.
3. Clarify and improve cache invalidation rules.
4. Ensure multi-device single-user behavior handles stale data gracefully.
5. Review Supabase query patterns against best practices.

### Candidate files

- `src/core/supabase_manager.py`
- `src/core/db_manager.py`
- `src/ui/background_workers.py`
- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/dashboard_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/tabs/archived_info_tab.py`

### Planned tactics

1. Replace per-record room-history fetches with bulk retrieval.
2. Wrap cache upserts in transactions or batch execution.
3. Add or validate indexes that match real query patterns.
4. Make delete, archive, and update cache behavior explicit.
5. Document the refresh and stale-data strategy for multi-device use.

### Risks

1. Bulk fetch changes may alter record ordering or grouping if not validated carefully.
2. Cache cleanup changes may hide or remove records unexpectedly if the source-of-truth assumptions are wrong.

### Exit criteria

1. History and dashboard data loads are faster under medium-scale data.
2. Cache updates are measurably cheaper.
3. Stale data behavior is understandable and intentionally handled.

## Phase 3 - Heavy UI Responsiveness and Memory

Status: Planned
Priority: High

### Goals

1. Make heavy views feel smooth during real use.
2. Reduce memory pressure from tables, images, and repeated UI work.

### Scope

1. Simplify repeated table-resize passes.
2. Improve large table population strategy.
3. Add parity between active and archived rental loading strategies.
4. Improve image loading and scaling behavior.
5. Profile memory after visiting the heaviest screens.

### Candidate files

- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/tabs/archived_info_tab.py`
- `src/ui/tabs/dashboard_tab.py`
- `src/ui/components/table_optimization.py`
- `src/ui/components/enhanced_table_mixin.py`
- `src/core/optimized_image_fetcher.py`
- `src/ui/rental_record_dialog.py`
- `src/ui/responsive_image.py`

### Planned tactics

1. Reduce repeated expensive column and row sizing passes.
2. Avoid unnecessary repaints and full table rebuilds.
3. Use background loading where the UI currently blocks.
4. Debounce image rescaling and avoid expensive resize-path work.
5. Ensure archived cloud views paginate or load incrementally when needed.

### Risks

1. Table changes can cause subtle layout regressions.
2. Image caching changes can surface stale-image bugs after edits.

### Exit criteria

1. Heavy tabs remain responsive with medium data volumes.
2. UI operations feel smoother without changing business behavior.
3. Memory use after visiting heavy screens is reduced or stabilized.

## Phase 4 - Structural Refactor Seams

Status: Planned
Priority: High

### Goals

1. Reduce the cost and risk of future changes.
2. Break up the most dangerous coupling without rewriting the app.

### Scope

1. Extract pure calculation logic from UI classes.
2. Split `db_manager.py` responsibilities behind smaller interfaces.
3. Introduce central mapping functions for Supabase, cache, and CSV data shapes.
4. Reduce cross-tab direct widget mutation.
5. Consolidate duplicate table optimization logic.

### Candidate files

- `src/core/HomeUnitCalculator.py`
- `src/core/db_manager.py`
- `src/core/add_month_manager.py`
- `src/core/supabase_error_handler.py`
- `src/ui/tabs/main_tab.py`
- `src/ui/tabs/rooms_tab.py`
- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/components/table_optimization.py`

### Planned tactics

1. Extract pure functions before introducing broader abstractions.
2. Preserve existing runtime behavior while moving logic behind narrower seams.
3. Clean obvious duplication only when directly tied to the extracted seam.
4. Prefer repository-like wrappers over a giant persistence class.

### Risks

1. Cross-tab behavior may have hidden assumptions that only appear at runtime.
2. Large-file refactors can create regressions if they are not staged behind tests.

### Exit criteria

1. Core business logic is more testable outside the UI.
2. The heaviest modules have narrower responsibilities.
3. Future optimization work becomes simpler and safer.

## Phase 5 - UX Polish and Workflow Clarification

Status: Planned
Priority: Medium

### Goals

1. Improve perceived quality after the technical bottlenecks are addressed.
2. Make the cloud-first model clearer without changing core features.

### Scope

1. Improve startup and loading feedback.
2. Clarify cloud versus cached state in the UI.
3. Reduce confusing dual-mode language where the app is now cloud-first.
4. Make CSV feel like import/export rather than a competing main mode.
5. Polish heavy workflows that still feel rough after technical improvements.

### Candidate files

- `src/core/HomeUnitCalculator.py`
- `src/ui/tabs/main_tab.py`
- `src/ui/tabs/history_tab.py`
- `src/ui/tabs/rental_info_tab.py`
- `src/ui/tabs/archived_info_tab.py`
- `src/ui/tabs/dashboard_tab.py`
- related dialogs and shared widgets

### Exit criteria

1. The app communicates loading, cache, and cloud state more clearly.
2. The UX better matches the actual architecture.
3. Core workflows remain intact while feeling more polished.

## Validation Matrix

Every phase should verify the affected scope at the smallest safe loop.

### Fast checks after each logical change

1. `python -m py_compile` on changed modules.
2. Import smoke for changed startup-sensitive modules.
3. A basic app construction smoke test.

### Automated test coverage targets

1. startup and shutdown smoke path
2. lazy tab loading behavior
3. calculation logic
4. DB config and cache helpers
5. Supabase sync fallback and batching behavior using mocks
6. image fetch/cache logic where feasible
7. heavy-view regression checks for resize and data population where automation is practical

### Runtime verification targets

1. first run with no cloud config
2. configured cloud run
3. medium-scale dataset
4. cloud unavailable or slow
5. installed app smoke run
6. startup timing comparison before and after milestones

## Edge Cases That Must Be Preserved or Explicitly Improved

1. user opens the app with no Supabase config
2. user opens the app with stale local cache and valid cloud credentials
3. user switches devices and sees data updated elsewhere
4. history contains medium-sized datasets across several years
5. archived records exist in meaningful volume
6. image URLs fail, are slow, or point to unavailable content
7. Supabase returns partial or unexpected fields
8. local migration encounters older SQLite schema or older CSV shape
9. cache contains records that were deleted or archived remotely
10. startup happens on a slower disk or cold boot environment

## Dependency Order

The phases should be implemented in this order unless a specific task is clearly independent.

1. Phase 0 baseline and safety setup
2. Phase 1 startup optimization
3. Phase 2 cloud and cache efficiency
4. Phase 3 heavy UI responsiveness and memory
5. Phase 4 structural refactor seams
6. Phase 5 UX polish

Within a phase, prefer this sequence:

1. add or strengthen tests
2. make the smallest behavior-preserving improvement
3. verify metrics or correctness
4. then continue to the next improvement

## Rollback Strategy

1. Keep changes phase-scoped and small enough to revert independently.
2. Avoid bundling startup, data, and UI behavior changes into one edit.
3. Preserve existing user-visible flows until replacement paths are verified.
4. Treat migration-related changes as separately testable units.
5. If a performance improvement introduces correctness risk, revert or gate it behind a safer path.

## Milestone Tracking

Use this section as the living status tracker.

### Milestone status

- [ ] Phase 0 - Baseline, Rules, and Safety Setup
- [ ] Phase 1 - Startup Optimization First
- [ ] Phase 2 - Cloud and Cache Efficiency
- [ ] Phase 3 - Heavy UI Responsiveness and Memory
- [ ] Phase 4 - Structural Refactor Seams
- [ ] Phase 5 - UX Polish and Workflow Clarification

### Immediate next actions

- [x] Create the initial test harness and smoke-test path
- [x] Add a packaged-startup measurement script
- [x] Capture a startup baseline for the packaged portable run
- [ ] Capture an installed-app startup baseline
- [x] Audit startup imports in `src/core/HomeUnitCalculator.py`
- [x] Identify the first safe startup edits to make behind smoke coverage
- [ ] Continue Phase 1 startup optimization from dashboard and first-page construction bottlenecks
- [ ] Evaluate whether the dashboard shell itself should become partially or fully lazy after navigation is visible
- [ ] Validate the no-acrylic packaged build on normal interactive use beyond startup timing
- [x] Start Phase 2 by batching cache writes and removing the first N+1 room-fetch paths
- [x] Reconcile rental cache state so archived and deleted cloud rows stop leaving stale tenant data locally
- [x] Skip repeated full rental syncs when the cloud rental signature has not changed
- [x] Remove repeated per-month SQLite rental lookups from dashboard room tooltip rendering
- [x] Consolidate repeated yearly `main_calculations_cache` reads for dashboard bill/rate/electricity sections
- [x] Normalize Supabase history payloads once in cloud load/export paths instead of reparsing repeatedly
- [x] Reconcile stale yearly main and room cache rows during full cloud syncs
- [x] Prune stale cached room rows for changed parents during incremental room syncs
- [x] Add low-risk SQLite tuning for cache concurrency and hot-query indexes
- [ ] Measure dashboard/history cloud operations after the Phase 2 data-path changes
- [ ] Evaluate the next Phase 2 candidate: bulk room fetches for any remaining cloud paths or cache invalidation cleanup
- [ ] Evaluate the next rental-cache step: move from full-signature checks to a cheaper server-side watermark if the cloud schema supports it safely
- [ ] Evaluate the next read-path candidate: repeated JSON parsing or duplicate pass structure in history cloud load/export paths

## Open Questions

Only unresolved items that materially affect implementation should stay here.

1. For multi-device edits to the same cloud-backed record, confirm whether conflict handling should be last-write-wins based on server timestamps.

## Change Log

### 2026-04-04

1. Created the initial optimization plan from codebase assessment and user interview.
2. Locked the cloud-first architecture direction and the phased implementation strategy.
3. Added initial startup smoke tests under `tests/`.
4. Deferred `MainTab`, `RoomsTab`, and `SaveDialog` imports to reduce startup work.
5. Removed one redundant main-window encryption initialization.
6. Fixed Windows console encoding issues in `tools/startup_profiler.py` and `tools/compare_performance.py`.
7. Captured the first source-run startup baseline after the initial startup patch set.
8. Deferred `DashboardTab` import and several dashboard post-init operations.
9. Deferred dashboard worker imports and moved keyboard navigation setup out of the constructor path.
10. Added `tools/measure_packaged_startup.ps1` to measure portable or installed packaged startup externally.
11. Captured updated source-run startup measurements showing import-time wins and a remaining dashboard/navigation construction bottleneck.
12. Deferred secondary dashboard chart creation and added dashboard construction smoke coverage.
13. Lazy-mounted the dashboard itself and cut app-shell startup time substantially.
14. Built and measured the portable package locally.
15. Trimmed the packaged build by excluding `numpy` and `scipy`, reducing portable cold and warm startup times significantly.
16. Batched cache-sync writes in SQLite and removed the first major room-fetch N+1 paths from dashboard/history cloud flows.
17. Reconciled rental cache sync with full cloud state so deleted or archived tenant rows stop lingering locally.
18. Added a rental metadata signature check so repeated dashboard rental syncs can skip unnecessary full cloud fetches.
19. Removed repeated per-month rental cache reads from dashboard room tooltip generation by precomputing tenant timelines once per render.
20. Consolidated dashboard yearly main-cache reads so bill totals, rate charts, electricity charts, and sync metadata now share one parsed snapshot per year.
21. Normalized Supabase history payloads once for cloud history loading and CSV export so those paths no longer repeatedly parse the same JSON fields.
22. Added full-year cache reconciliation so deleted main and room cloud rows no longer linger indefinitely in local yearly caches.
23. Closed the remaining delta room-cache stale-child gap for changed parents during incremental syncs.
24. Tuned SQLite connection behavior and indexes for the app's current cache-heavy hot paths, and cleaned the remaining owned UTC deprecation warnings.
25. Created a dedicated follow-on plan for realtime data propagation, cross-tab UI consistency, and UI responsiveness under live updates.
