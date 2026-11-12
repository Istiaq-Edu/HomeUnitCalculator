# UI, dashboard, and runtime findings

[Audit index](README.md)  
Last updated: 2026-11-12  
Disposition: RUN-01 is locally verified; other findings remain open. Native smoke verification is not a claim that all user journeys, accessibility, or packaged behavior passed.

## Record workflows and interaction

### UI-01

**Sorting during per-cell table population can corrupt row associations.**  
Priority: P1. Evidence: R-specialist, S.

Archive population was reproduced using the actual method with sorting active: inserting sort-column cells can move rows while later cells and payloads are still assigned using old row indexes. History contains similar population patterns. Selection restoration can also capture selection after clearing it.

Evidence: [archived_info_tab.py:575](../../../src/ui/tabs/archived_info_tab.py#L575), [history_tab.py:4484](../../../src/ui/tabs/history_tab.py#L4484), [history_tab.py:4732](../../../src/ui/tabs/history_tab.py#L4732).

Recommendation: capture stable selected identities first; suspend sorting; construct complete rows and payloads; restore prior sorting state; then restore selection by identity.

### UI-02

**History action availability does not match its action target.**  
Priority: P2. Evidence: S/C.

Either main or room selection enables Edit/Delete, but handlers read main-table selection. Room-only selection is guarded with a no-selection message; it does not automatically delete an arbitrary room. If a main selection remains while attention moves to a room, targeting becomes ambiguous.

Evidence: [history_tab.py:5274](../../../src/ui/tabs/history_tab.py#L5274), [history_tab.py:5289](../../../src/ui/tabs/history_tab.py#L5289), [history_tab.py:5317](../../../src/ui/tabs/history_tab.py#L5317).

Recommendation: align enabled state, visible selected scope, and handler target. Test retained main A plus room B rather than treating all room selection as the same failure.

### UI-03

**Room sorting can rewrite the displayed room identifier.**  
Priority: P2. Evidence: S.

Using numeric edit-role values as a sorting mechanism can replace identifiers such as `A-1` with `0` or `01` with `1`. Display identity and numeric ordering are separate requirements.

Evidence: [rental_info_tab.py:3667](../../../src/ui/tabs/rental_info_tab.py#L3667).

Recommendation: a dedicated sort role/item comparison preserving the display text and stable record identity.

### UI-04

**Persistent drafts and asynchronous list refresh do not share clear ownership.**  
Priority: P2. Evidence: S.

Rental modal edit protection ends when the dialog transfers data into the persistent form, although the user is still editing. Dirty-draft replacement guards are incomplete. Rental refresh resets paging before its in-flight guard; archived loads permit overlaps; history can discard newer filters.

Evidence: [rental_info_tab.py:3784](../../../src/ui/tabs/rental_info_tab.py#L3784), [rental_info_tab.py:3796](../../../src/ui/tabs/rental_info_tab.py#L3796), [rental_info_tab.py:3385](../../../src/ui/tabs/rental_info_tab.py#L3385), [archived_info_tab.py:481](../../../src/ui/tabs/archived_info_tab.py#L481).

Recommendation: draft ownership tokens, explicit replace/discard decisions, and context-tagged requests. See [DATA-10](data-and-calculation.md#data-10).

### UI-05

**Paging and synchronous operations can obstruct interaction.**  
Priority: P2. Evidence: S/C; performance is unmeasured.

Scroll-trigger-only pagination may not request another page when the first page fits the viewport. Saves, exports, and some image/local-copy work run synchronously on the GUI path. Modal minimum sizes and coordinate assumptions may be problematic at high DPI or on small displays.

Evidence: [rental_info_tab.py:3385](../../../src/ui/tabs/rental_info_tab.py#L3385), [rental_record_dialog.py:288](../../../src/ui/rental_record_dialog.py#L288), [HomeUnitCalculator.py:1465](../../../src/core/HomeUnitCalculator.py#L1465).

Recommendation: explicit load-more/end-of-data behavior, measured nonblocking work, and tested logical-pixel sizing. Do not assert a universal freeze or a measured latency from source alone.

### UI-06

**Attachment deletion checks location rather than complete ownership.**  
Priority: P2. Evidence: S/C.

Local deletion removes attachment paths that pass broad safe-path checks, without a full app-ownership/reference-count contract. Clearing selection can leave copied files behind. A file can be in an allowed directory without being exclusively owned by one record.

Evidence: [rental_record_dialog.py:1396](../../../src/ui/rental_record_dialog.py#L1396), [rental_info_tab.py:2860](../../../src/ui/tabs/rental_info_tab.py#L2860).

Recommendation: managed attachment identity, ownership, retention, and shared-reference semantics. Avoid deleting a file merely because its directory is considered safe.

## Dashboard semantics

### DASH-01

**Bar hover callback arguments are reversed.**  
Priority: P2. Evidence: S.

**Status: locally verified (2026-11-12).** Both signal adapters originally reversed Qt's boolean/index argument order. Real-signal tests reproduced hidden January feedback and December selecting February's tooltip. The two lambda parameter lists now use `state, idx`; eight focused tests pass after failing before the correction. The Charts-enabled full suite passes 172 tests; the normal fallback suite passes 164 with eight explicit optional skips. Native verification later passed against real Qt Charts with synthetic data: every bar index produced enter/leave events, tooltip text matched the injected data on each event, and tooltips hid on leave (single renderer 12/12; grouped renderer 23/23 with one edge entry outside the swept line). The optional Charts package remains absent from the normal environment and exists only in a temporary test directory. During this verification `SeriesAnimations` reproduced native access violations on Qt 5.15.2 + PyQtChart 5.15.7; per user decision animations are not wanted, and production now sets `QChart.NoAnimation`. One crash observed in five animation-free environment runs is recorded as an unexplained environment-level instability, not an application finding. See the [progress log](verification-and-roadmap.md#remediation-log).

Evidence: [dashboard_tab.py:1486](../../../src/ui/tabs/dashboard_tab.py#L1486), [dashboard_tab.py:1564](../../../src/ui/tabs/dashboard_tab.py#L1564).

Recommendation: match the documented signal signature and test every bar/category, including leaving the hovered region.

### DASH-02

**Category-axis labels and plotted positions can disagree.**  
Priority: P2. Evidence: S.

Centered category labels do not necessarily align with the point positions used by the chart.

Evidence: [dashboard_tab.py:1178](../../../src/ui/tabs/dashboard_tab.py#L1178), [dashboard_tab.py:1372](../../../src/ui/tabs/dashboard_tab.py#L1372).

Recommendation: explicitly define category boundaries/positions and verify a small known dataset visually and through the accessible data table.

### DASH-03

**Year changes and worker completion are not one coherent scope.**  
Priority: P1/P2. Evidence: R-main method probe, S.

**Status: implemented, locally tested (2026-11-12).** Every dashboard async lane (years, main, owner-main, room, rentals) now carries a monotonic request generation attached to its worker; completions publish only when their generation is still current, and a request made while the lane is busy is retained and re-dispatched after the current completion instead of being silently discarded. Nine focused regressions cover stale completions, latest-intent retention, and per-lane drain; the full suite passes 173 tests. This is the dashboard manifestation of [DATA-10](data-and-calculation.md#data-10); DATA-10's other consumers remain open.

Evidence: [dashboard_tab.py](../../../src/ui/tabs/dashboard_tab.py) (`_lane_request`, `_lane_is_current`, `_drain_lane_pending`, and the five rewired request/completion paths).

### DASH-04

**January comparisons can use the wrong December.**  
Priority: P2. Evidence: S.

**Status: implemented, locally tested (2026-11-12).** `_update_section_kpis` accepts `prev_year_raw`; in January of the current year the recent-month card resolves December and November of the previous year (summary KPIs read the previous year's snapshot and caches). Without previous-year data the cards show an em-dash placeholder. Boundary regressions cover the January case with and without previous-year data.

Evidence: [dashboard_tab.py](../../../src/ui/tabs/dashboard_tab.py) (`_update_section_kpis`, `_update_summary_kpis`, callers).

### DASH-05

**Missing, empty, failed, and partial data appear as measured zero.**  
Priority: P1/P2. Evidence: S.

**Status: implemented, locally tested (2026-11-12).** The main lane now keeps absent months as ``None`` through rendering; tooltips say "No data" for absent months, KPI cards render an em-dash, and summary cards render "---" while a recorded zero still renders as ``TK 0``. The high/low cards are None-aware. Charts keep segment behaviour (line breaks at absent months; bar indexes stay aligned so tooltip indexes remain correct). Additionally, when the calendar's "previous month" has no recorded data, the cards fall back to the most recent month that actually has data instead of blanking. Rate, electricity, and owner/room lanes already carried ``None``-aware rendering.

Evidence: [dashboard_tab.py](../../../src/ui/tabs/dashboard_tab.py) (`_render_year_from_cache`, `_render_values`, `_build_tooltips`, `_update_section_kpis`, `_update_summary_kpis`).

### DASH-06

**Freshness and dependent metrics do not follow independent data scopes.**  
Priority: P2. Evidence: S.

**Status: implemented, locally tested (2026-11-12).** `_update_meta` was replaced by `_set_section_meta`; the main, rate, and electricity sections each write their own freshness label from their own year's snapshot. A room-lane completion now refreshes the summary KPI cards when it matches the displayed year, so room-dependent figures cannot stay stale.

Evidence: [dashboard_tab.py](../../../src/ui/tabs/dashboard_tab.py) (`_set_section_meta`, `_render_rate_from_cache`, `_render_elec_from_cache`, `_on_room_sync_finished`).

### DASH-07

**Offline/configuration status can misdescribe recovery.**  
Priority: P2. Evidence: S.

A configured service failure can produce a not-configured banner, and the banner is not consistently reset after success.

Evidence: [dashboard_tab.py:609](../../../src/ui/tabs/dashboard_tab.py#L609), [dashboard_tab.py:863](../../../src/ui/tabs/dashboard_tab.py#L863), [dashboard_tab.py:1747](../../../src/ui/tabs/dashboard_tab.py#L1747).

Recommendation: distinguish absent configuration, denied access, offline/error, cached availability, and recovered synchronization.

### DASH-08

**One owner delta path destroys the previous comparison value too early.**  
Priority: P2. Evidence: S.

**Status: implemented, locally tested (2026-11-12).** `_build_owner_room_tooltips` computes the delta and its direction icon from the immutable old/new values before the previous-value state advances; the negative-delta case now renders the down icon. A regression asserts the down icon for a falling bill.

Evidence: [dashboard_tab.py](../../../src/ui/tabs/dashboard_tab.py) (`_build_owner_room_tooltips`).

### DASH-09

**Active Rooms is not a verified current-occupancy measure.**  
Priority: P2. Evidence: S/C.

The metric counts distinct historical room names for the year. Other occupancy logic can infer tenure from record creation/archive update times and digits in room labels, not explicit business dates.

Evidence: [dashboard_tab.py:2343](../../../src/ui/tabs/dashboard_tab.py#L2343), [db_manager.py:525](../../../src/core/db_manager.py#L525).

Recommendation: define current occupancy using stable rooms and tenancy intervals; label historical participation differently. Preserve missing dates as unknown rather than manufacturing tenure.

### DASH-10

**Chart presentation and render work need measurement and interpretation review.**  
Priority: P3. Evidence: S/C/D.

Spline interpolation, truncated baselines, negative residual bars, per-room GUI queries, and resize-time rebuilding deserve targeted review. No representative performance benchmark or user-comprehension study established their real-world impact.

Recommendation: use known datasets, truthful scales, accessible tabular equivalents, and measured render latency before adding animation or optimization layers.

## Shared widgets, image resources, and platform behavior

### RUN-01

**Global card event monkeypatching causes hover recursion.**  
Priority: P1. Evidence: R-main.

**Status: locally verified fixed, 2026-11-12.** The original sequential handler replacement captured an inherited already-patched method as an original. Isolated probes reproduced `RecursionError` for SimpleCardWidget and ElevatedCardWidget; CardWidget did not recurse but its native handler was replaced.

The global enter/leave wrappers and their animation code have been removed. The dark-palette callbacks remain; Fluent retains its own inherited event handlers. Local `StaticRoomCard` and `StaticHeaderCardWidget` subclasses preserve the established static room/rental appearance without replacing third-party class methods.

Evidence: [HomeUnitCalculator.py:995](../../../src/core/HomeUnitCalculator.py#L995), [main_tab.py:38](../../../src/ui/tabs/main_tab.py#L38), [rental_info_tab.py:96](../../../src/ui/tabs/rental_info_tab.py#L96), [test_startup_smoke.py:158](../../../tests/test_startup_smoke.py#L158).

Verification: original regression 3 failed/1 passed before removal, 4 passed afterward; the final suite passed 164 tests with one third-party warning. Native execution mounted all seven tabs, checked repeated events on all three Fluent classes and 11 room/four rental static cards, exercised room input and remove/undo, captured zero exceptions, and exited 0. Calculator and Rental screenshots were inspected. See the [remediation record](verification-and-roadmap.md#remediation-log).

Remaining limits: tests are still ignored/untracked (REL-08); global color-helper coupling remains design debt, not a claim of a replaced design system. No packaged/live-cloud verification was performed.

### RUN-02

**Keyboard navigation dispatch targets obsolete interfaces.**  
Priority: P2. Evidence: S, R-specialist.

The manager expects `tab_widget`, missing save/reload methods, and searches QMainWindow children for modal dialogs on Escape.

Evidence: [keyboard_navigation.py:62](../../../src/ui/keyboard_navigation.py#L62).

Recommendation: shared QActions bound to current route/operation contracts and correct active-modal handling. Verify enabled state and keyboard behavior in the real application.

### RUN-03

**Worker cancellation and timeout do not establish completion.**  
Priority: P1/P2. Evidence: S.

Blocking worker runs do not inspect interruption. Calling `quit()` does not cancel a blocking request, and a 100-ms wait is not completion acknowledgement. Image `future.result(timeout=...)` after `as_completed()` does not impose an operation-wide deadline. Parent/thread lifecycle failure is a risk, not a reproduced application crash.

Evidence: [background_workers.py:11](../../../src/ui/background_workers.py#L11), [optimized_image_fetcher.py:406](../../../src/core/optimized_image_fetcher.py#L406), [rental_record_dialog.py:1490](../../../src/ui/rental_record_dialog.py#L1490).

Recommendation: bounded requests, cancellation-aware work where possible, generation invalidation, and a shutdown protocol that observes actual completion.

### RUN-04

**Image download/cache limits and privacy scope are incomplete.**  
Priority: P2. Evidence: S/C.

Response bytes are not comprehensively bounded; MIME, redirect, and host policies are incomplete. Thumbnail failure can return original raw bytes. Identity-document cache data is plaintext and not account/project-scoped, without complete quota/purge integration. URLs may reach logs.

Evidence: [optimized_image_fetcher.py:135](../../../src/core/optimized_image_fetcher.py#L135), [optimized_image_fetcher.py:237](../../../src/core/optimized_image_fetcher.py#L237), [optimized_image_fetcher.py:450](../../../src/core/optimized_image_fetcher.py#L450).

Recommendation: boundary limits, atomic validated publication, private project-scoped cache ownership, retention, and redacted logging. Do not assume URL hashing provides document confidentiality.

### RUN-05

**Image cache publication, deduplication, and singleton initialization race.**  
Priority: P2. Evidence: R-specialist, S.

Specialist probes accepted a partial cache file, scheduled duplicate URL work, and obtained two concurrent singleton instances. Writes target final paths, cache validity can rely on existence, and initialization is unsynchronized.

Evidence: [optimized_image_fetcher.py:39](../../../src/core/optimized_image_fetcher.py#L39), [optimized_image_fetcher.py:135](../../../src/core/optimized_image_fetcher.py#L135), [optimized_image_fetcher.py:450](../../../src/core/optimized_image_fetcher.py#L450).

Recommendation: atomic file replacement, validated cache entries, shared in-flight ownership, and a deliberate singleton/session lifecycle.

### RUN-06

**A URL-to-single-slot mapping cannot represent repeated document URLs.**  
Priority: P2. Evidence: S.

When multiple image slots use the same URL, the map retains only one destination. Some previews can remain unresolved despite successful download. Existing current-URL guards are useful and should remain.

Evidence: [rental_record_dialog.py:1104](../../../src/ui/rental_record_dialog.py#L1104).

Recommendation: map a URL to all current destinations or assign independent request/slot identities.

### RUN-07

**Optimization abstractions are duplicated, misplaced, or disconnected.**  
Priority: P3, with correctness fixes at P2. Evidence: S, R-specialist.

Later class definitions shadow earlier ones. A misplaced `BatchUpdateManager.get_config_dict` raises AttributeError. Some intelligent sizing is simply ResizeToContents; some caches are unused. Rental/archive optimization integration is deliberately disabled.

Evidence: [table_optimization.py:82](../../../src/ui/components/table_optimization.py#L82), [table_optimization.py:1023](../../../src/ui/components/table_optimization.py#L1023), [table_optimization.py:1578](../../../src/ui/components/table_optimization.py#L1578), [table_optimization.py:1756](../../../src/ui/components/table_optimization.py#L1756).

Recommendation: identify effective runtime paths, remove superseded code only after that verification, and measure before replacing it. Class names do not prove an optimization is active or effective.

### RUN-08

**Sampled cache invalidation and batch restoration have correctness holes.**  
Priority: P2/P3. Evidence: R-specialist, S.

An unsampled last-row edit retained cached width 124 while invalidation yielded 3492 in a geometry probe; these are not performance timings. Nested batch scopes can release an outer freeze early. Recovery can restore the wrong sorting state; repeated safe-mode replacement can retain obsolete aliases/managers.

Evidence: [enhanced_table_mixin.py:119](../../../src/ui/components/enhanced_table_mixin.py#L119), [enhanced_table_mixin.py:345](../../../src/ui/components/enhanced_table_mixin.py#L345), [table_optimization.py:768](../../../src/ui/components/table_optimization.py#L768), [table_optimization.py:1914](../../../src/ui/components/table_optimization.py#L1914).

Recommendation: actual content revisions, nesting-safe ownership, and exact restoration of previous state. Dormant batch integration must not be described as an established production leak.

### RUN-09

**Qt5 units, margins, and coordinate spaces are mixed.**  
Priority: P2. Evidence: R-specialist, S.

CSS-like font weights 500/600/700/800 map incorrectly through Qt5's weight range. DPR-2 image handling can render a 190 logical-pixel target as 95. FlowLayout ignores relevant contents margins, and some dialog placement treats parent-local coordinates as screen coordinates.

Evidence: [responsive_image.py:15](../../../src/ui/responsive_image.py#L15), [flow_layout.py:31](../../../src/ui/flow_layout.py#L31), [responsive_components.py:100](../../../src/ui/responsive_components.py#L100), [custom_widgets.py:1697](../../../src/ui/custom_widgets.py#L1697).

Recommendation: Qt font constants, explicit logical/device-pixel conversions, correct coordinate mapping, and real multi-monitor DPI tests.

### RUN-10

**Responsive tests can mutate the subject and falsely certify behavior.**  
Priority: P2. Evidence: R-specialist, S.

A child font changed from 20 pt to 10 pt after a probe. Descendant geometry uses inconsistent coordinate spaces; the DPI test is only a resize operation.

Evidence: [responsive_testing.py:35](../../../src/ui/responsive_testing.py#L35), [responsive_testing.py:129](../../../src/ui/responsive_testing.py#L129), [responsive_testing.py:219](../../../src/ui/responsive_testing.py#L219).

Recommendation: exact state restoration and genuine DPI-aware checks. A test helper's successful output is not independent evidence if its assumptions are wrong.

### RUN-11

**Custom save-dialog path handling diverges from platform expectations.**  
Priority: P2. Evidence: R-specialist, S.

The selected filter is ignored in relevant handling; `REPORT.PDF` can become `REPORT.PDF.pdf`; reserved names such as `CON` are accepted; absolute filenames can override the selected directory.

Evidence: [save_dialog.py:146](../../../src/ui/save_dialog.py#L146), [save_dialog.py:445](../../../src/ui/save_dialog.py#L445).

Recommendation: native QFileDialog/public Qt behavior or a fully tested Windows path contract. Preserve default-No overwrite behavior.

### RUN-12

**Accessibility and input behavior require behavior-level verification.**  
Priority: P2. Evidence: S; usability impact is partly C/D.

Disclosure/add interactions are mouse-centric; some year controls explicitly reject focus; focus search can include hidden/disabled widgets; window-scoped shortcuts can conflict; pixel-only/horizontal wheel events can be consumed without scrolling; grouped-chart hit testing can confuse group and month.

Evidence: [history_tab.py:994](../../../src/ui/tabs/history_tab.py#L994), [custom_widgets.py:281](../../../src/ui/custom_widgets.py#L281), [custom_widgets.py:850](../../../src/ui/custom_widgets.py#L850), [custom_widgets.py:1318](../../../src/ui/custom_widgets.py#L1318), [custom_widgets.py:1498](../../../src/ui/custom_widgets.py#L1498).

Recommendation: keyboard-complete shared actions, accessible names and states, correct focus eligibility, wheel behavior, chart table equivalents, and screen-reader checks. Source review is not an accessibility certification.

## Positive patterns and limits

Useful existing patterns include stale-URL guards, bounded image presentation caches, GET-only retry behavior, background byte fetching with queued GUI delivery, selection helpers, default-No overwrite, and token-guarded room undo. Preserve them while correcting ownership and state boundaries.

The native smoke test mounted all tabs in a temporary local-only environment. It did not exercise live OAuth, real tenant records, all chart backends, sustained memory behavior, packaged deployment, or assistive technology. See [verification](verification-and-roadmap.md).
