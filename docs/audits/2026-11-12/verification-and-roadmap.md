# Verification, limitations, and implementation roadmap

[Audit index](README.md)  
Last updated: 2026-11-12  
Status: sequential local remediation in progress on branch `dev`; RUN-01, DASH-01, the dashboard truthfulness slice, REL-01..03/REL-08, DATA-01, DATA-02, and DATA-03 are locally verified and committed. No deployment or live cloud mutations.

## Scope and environment

- Workspace: HomeUnitCalculator on Windows, branch `dev` during the audit.
- Source inventory: 65 Python files across source, tests, and tools; approximately 40,172 lines.
- Python used for local audit: 3.12.10. Release workflows use Python 3.10.
- Relevant observed packages: PyQt5 5.15.11; PyQt-Fluent-Widgets 1.9.1; supabase/postgrest/realtime 2.22.1; httpx 0.27.2; cryptography 46.0.3; keyring 25.6.0; reportlab 4.4.4; pytest 8.4.2.
- Ruff and pip-audit were not installed. No project dependency CVE assessment was completed.
- Global `pip check` reported unrelated pyrebase4 conflicts; these were not classified as established project defects.

Reviewed areas included core orchestration, SQLite persistence, Supabase integration and provisioning, OAuth, polling/coordinator workers, calculations, records/history/archive, dashboards, shared widgets, images, responsive helpers, keyboard handling, save dialogs, tests, build/release workflows, installer/spec/hooks, tooling, and project documentation.

The seven domain reviewers inspected their assigned source areas. An independent architecture reviewer challenged the proposed approach, and a state-machine reviewer traced application-defined temporal state. A separate design-inventory agent failed and is not counted among the nine completed reviews; its coverage was recovered using direct inventory/search and the completed UI/widget/dashboard reviews.

Historical plans were treated as intent, not proof of implementation. Real application databases, tenant CSV/PDF content, identity images, and secrets were not inspected.

## Executed verification

| Check | Result | What it establishes and does not establish |
| --- | --- | --- |
| Python AST syntax scan | No syntax errors across the inventoried Python files | Parsing succeeds; not semantic or runtime correctness |
| Isolated local pytest suite | 157 passed, one third-party deprecation warning, about 38.41 seconds | Existing tests pass under the audit harness; does not establish deployed RLS, real async ordering, or packaged behavior |
| Card hover probe | Recursion reproduced for SimpleCardWidget and ElevatedCardWidget; CardWidget passed | Real isolated widget/method behavior, not a claim that every hover in the full UI crashes |
| Remote suppression probe | Another-device change was suppressed after an unchanged poll | Concrete loss of a remote notification under the tested sequence |
| Calculation probe | `10000 / 3000` displayed/reused as 3.33; room result 9990; added 0.99 displayed as 0 | Precision/display coupling; correct rounding policy still requires agreement |
| Empty room replacement probe | Returned true without deleting existing room ID 41 | Concrete actual-method behavior with a fake client, not a live cloud mutation |
| Dashboard completion probe | Callback rendered the passed old year | Method behavior; full selector/worker race is source-confirmed rather than end-to-end reproduced |
| Native local-only application smoke | All seven tabs mounted; no captured exceptions; process exit 0 | Native construction/navigation in an empty temporary profile; not live-service or full feature correctness |
| Native resize observation | 800 by 600 request resulted in 1000 by 700 window | Observed application minimum in this environment; not a comprehensive responsive test |
| Final audit Git check | Status/diff clean before documentation creation | No application source/config changes were made by the audit; Markdown files were created afterward at user request |

Specialists additionally reported synthetic reproductions for table-sorting corruption, cache/width races, CSV/carry-forward/undo edge cases, responsive helper behavior, and save-dialog paths. These are marked `R-specialist` rather than represented as rerun by the coordinating audit. A data specialist also reported 27 guarded tests; that result is not added to the 157-test full-suite total.

## Remediation log

### RUN-01 — locally verified, 2026-11-12

- Removed recursive global enter/leave replacement; retained existing palette helpers and native Fluent inheritance. Local room/header subclasses preserve the previous static appearance.
- Original focused regression: 3 failed/1 passed before the fix, then 4 passed. Static-container refinement added three cases, including child-button delivery; its two missing subclasses failed before implementation.
- Final isolated suite: **164 passed, 1 third-party scipy deprecation warning in 42.90 seconds**. This is not a performance comparison with the audit baseline.
- Native temporary-profile run: all seven tabs mounted; CardWidget, SimpleCardWidget, and ElevatedCardWidget handled repeated enter/leave with native handlers; 11 room cards and four rental cards remained static. Typed into a room input, removed the room, undid removal, and verified the input survived. Zero captured exceptions; exit 0.
- Inspected temporary screenshots: [Calculator](file:///C:/Users/Mr-N0N4M3/AppData/Local/Temp/huc-card-native-8c840axh/calculator-after-card-fix.png) and [Rental](file:///C:/Users/Mr-N0N4M3/AppData/Local/Temp/huc-card-native-8c840axh/rental-after-card-fix.png). Temporary artifacts may be cleaned later.
- An initial native harness rejected a legitimate temporary key write because short/long Windows paths were compared inconsistently. Canonicalizing the sandbox path corrected the test boundary without changing production key handling or permitting real-profile writes.
- Independent read-only review accepted the recursion correction and identified the static-appearance gap; that gap was addressed and tested before closure.
- The test directory is still ignored/untracked (REL-08). No Git commit, dependency change, live cloud operation, or deployment was made. Global palette coupling and unrelated UI limitations remain open.

### DASH-01 — implemented; native verification incomplete, 2026-11-12

1. Verify the installed Qt signal contract. Qt Charts is optional and absent from the normal environment, so install pinned PyQtChart 5.15.7 / PyQtChart-Qt5 5.15.2 only in a temporary test directory; do not change project requirements.
2. Extend the existing startup smoke test module (after its QApplication lifecycle checks) with real bar-set signal coverage for both single and grouped renderers, all 12 months, enter and leave, empty tooltip lists, and reconstruction with new tooltip context. Confirm the original wiring fails.
3. Change only the two lambda parameter lists from `idx, state` to `state, idx`; retain `_on_bar_hovered(index, state, tooltips, chart_view)` and existing data/rendering semantics.
4. Run focused and full isolated tests with Qt Charts enabled, preserve the normal fallback suite result separately, then launch native Qt Charts with synthetic data and verify actual pointer/tooltips. Record results before closing DASH-01; do not claim category-axis alignment (DASH-02) is fixed.

Current DASH-01 progress:

- Real Qt bar signals verified the `hovered(bool,int)` contract. All eight focused tests failed before the change: January hover hid the tooltip and rebuilt December data selected February's text. After correcting both lambda parameter lists, **8 passed** with one third-party warning.
- The normal fallback full-suite run initially produced **163 passed, 8 skipped, 1 failed** in the OAuth callback test while another full-suite process was running. The tests use fixed loopback ports (8766–8768). A serial rerun passed: **164 passed, 8 skipped, 1 third-party warning in 34.84 seconds**. The skips are the eight optional Qt Charts cases, not hidden failures.
- The first Qt Charts-enabled full suite terminated with a Windows access violation during a later `processEvents()` call. After deterministic deletion of new test chart views and a serial rerun, the complete Charts-enabled suite passed: **172 passed, 1 third-party warning in 29.18 seconds**. No production lifecycle workaround was introduced. The original crash's exact C++ cause was not proven; the correction prevents the new fixtures from deferring deletion into unrelated tests.
- Native Charts application execution terminated with an access violation before synthetic hover injection, at `app.exec_()`. Unbuffered fatal-error diagnostics confirmed this. A comparison restored both original HEAD hover methods **in memory only** and reproduced the same crash, so the two-parameter correction is not sufficient to explain it. The underlying native cause remains unestablished. An independent specialist completed seven standalone native QWidget/chart/axis/bar probes and three staged chart-update/render repeats, all exit 0, with no project imports. Actual runtime Qt is 5.15.2 on the Windows platform; Charts loads from the temporary package directory. This does not support a generally unusable Charts installation. Those probes used no animations; the application enables series animations, so a controlled in-memory comparison is next. The specialist corrected an initial test assertion that incorrectly expected a return value from `QBarSet.replace()`; those harness aborts are not application findings. DASH-01 is **not marked verified** and no successful Charts screenshot has been claimed.
- Controlled application comparison: wrapping `_init_qtchart_common` **in memory only** to set `QChart.NoAnimation` after normal initialization allowed native startup and reached synthetic chart testing. The original native crash no longer occurred in that run, but the pointer probe then observed no hover events and failed its assertion. No native success is claimed. Animation-specific minimal reproduction and pointer-harness diagnosis are separate next checks; no production animation change has been made.
- Qt Charts packages exist only in a temporary directory. Project requirements, installed base packages, live cloud resources, and user data have not been changed.

### DASH-01 — locally verified; animations removed by decision, 2026-11-12

1. Specialist diagnosis of the zero-hover probe found a harness defect, not an application defect: the probe passed `'_owner_room_line_series'` to `_apply_qt_grouped_bar_chart`, but the application stores grouped bar series under `_owner_room_bar_series` (dashboard_tab.py:2693/2707), so observers attached to a stale empty series. The single-renderer miss was a window z-order flake. Correct mapping was confirmed: `plotArea()` is already scene coordinates, `chart.mapToScene` is identity here, and `QTest.qWait(10)` is sufficient. The verified injection pattern uses the correct attribute, hides the still-visible main window, applies `Qt.WindowStaysOnTopHint` with `raise_()`, and waits 40 ms per move.
2. `SeriesAnimations` was proven the crash-dominant factor: native startup reached full synthetic hover verification only without it. An animation-free control still crashed once in five environment runs, so an environment-level native instability exists that is not attributed to application code.
3. Production change (user decision, 2026-11-12): the user stated animations are not needed; `_init_qtchart_common` now sets `QChart.NoAnimation` and no animation duration. This removes the crash class rather than debugging Qt internals.
4. Native verification with the production configuration passed on the first attempt: single renderer 12/12 bar indexes entered and left; grouped renderer 23/23 events across both sets (one set-0 edge entry outside the swept line); tooltip text asserted equal to the synthetic tooltip on every enter; tooltips hidden on leave; zero captured exceptions; exit 0. Screenshots (temporary artifacts): `C:/Users/MR-N0N4M3/AppData/Local/Temp/huc-bar-native-qm3rqhaa/single-bar-hover.png` and `.../grouped-bar-hover.png`. Tooltips are separate native windows, so screenshot correctness comes from the in-callback text assertions rather than pixel inspection.
5. Post-change isolated fallback suite: **164 passed, 8 optional Qt Charts skips, 1 third-party warning in 12.39 seconds**. The Charts-enabled suite had passed 172 before the animation change; the change removes animation behavior the focused tests never asserted. No commit, dependency change, or cloud mutation.

### Dashboard truthfulness slice, window state, startup — locally verified, 2026-11-12

Scope: DASH-03 (request scope), DASH-04 (January/December boundary), DASH-05 (missing vs zero), DASH-06 (per-snapshot freshness), DASH-08 (delta direction), plus user-directed additions: recent-month fallback so cards do not blank when the calendar month has no data, window geometry remembrance, and faster startup. A Plan specialist verified the flow and line targets before implementation.

- Request scope: monotonic per-lane generations (years, main, owner-main, room, rentals) attach to each worker; completions publish only when current; busy-lane requests are retained and re-dispatched (latest intent wins). Stale-completion and retention regressions added.
- January comparisons resolve the previous year's December/November in section KPIs and summary KPIs (previous year's snapshot and caches); without previous-year data cards show a placeholder.
- Missing months stay `None`: tooltips "No data", KPI em-dash, summary "---"; recorded zeros still render as measured data. Calendar-month fallback shows the last month with data instead of blank cards (user-reported "cards stay black").
- Freshness labels are per-section/per-snapshot; room-lane completion refreshes displayed-year summary cards.
- Owner delta direction is computed before the previous-value state advances.
- New regression module `tests/test_dashboard_request_scope.py` (9 tests). Final isolated suite: **173 passed, 8 optional skips, 1 third-party warning**.
- Window state: `MeterCalculationApp` restores saved geometry on start and saves it in `closeEvent` via `QSettings("HomeUnitCalculator", "Window")`. Exercised by the native smoke run's clean window close.
- Startup: `python -X importtime` showed `qfluentwidgets` → `scipy.ndimage.filters` costing ~0.57 s of ~1.13 s module import. A lazy module shim (`_install_lazy_scipy_shim` in `src/core/HomeUnitCalculator.py`, same pattern as the existing supabase transformers shim) defers real scipy import to first call; verified `gaussian_filter` still computes correctly when invoked, with zero scipy imports at startup. Import time dropped to ~0.56 s; the native smoke's startup timer improved from ~3.19 s to **2.59 s** total.
- No commit, dependency change, or cloud mutation; tests remain gitignored under REL-08.

### DATA-01 — locally verified, committed, 2026-11-12

- Cross-source identity containment: cloud `rental_records.id` (a Supabase sequence value) no longer addresses local `rentals` rows. `RentalInfoTab.load_record_into_form_for_edit` gained a `source` argument; cloud-source edits resolve the local counterpart through the unique `rentals.supabase_id` link (`_resolve_local_rental_id`, fail-safe to insert on any lookup failure), and the dialog passes its `current_source`. The dialog's cloud-delete path removes the local counterpart by `supabase_id`, and a cloud record without `supabase_id` is blocked from deletion instead of falling back to the numeric id.
- Focused regressions `tests/test_rental_record_identity.py` (9 tests): **6 of 9 failed against the pre-fix source** (verified by a temporary stash of the two source files), **9 of 9 passed** after the fix. Full isolated suite: **182 passed, 8 optional Qt Charts skips, 1 third-party scipy deprecation warning in 12.43 s**.
- Committed on `dev` as `515edbe` (source + tests). Not pushed. Dependency, packaging, and cloud state unchanged.
- Remaining limits recorded in [DATA-01](data-and-calculation.md#data-01): NULL cloud `supabase_id` rows (DATA-03) cannot be linked; the local save's UPDATE statement itself is unchanged as SQL; no deployed or live cloud verification.

### DATA-02 — locally verified (client-side containment), committed, 2026-11-12

- Monthly persistence outcomes made explicit without a deployed schema change: `save_room_calculations` gained true empty-replacement semantics (empty list deletes the previous rows), counts insert persistence, and reports failed/partial old-row deletion as failure with retry-convergence logging instead of swallowed success. `delete_calculation_record` now deletes the parent first relying on the bundled FK cascade, verifies orphaned children read-only, removes orphans explicitly on cascade-less schemas, and reports partial cleanup as failure. Both callers (`save_calculation_to_supabase`, history edit) now invoke the room save even with an empty list.
- Regressions `tests/test_monthly_persistence_atomicity.py` (13 tests): **9 of 13 failed against the pre-fix source** (verified via temporary stash), **13 of 13 passed** after. Full isolated suite: **195 passed, 8 optional Qt Charts skips, 1 third-party scipy deprecation warning in 12.39 s**.
- Committed on `dev` as `c729819`. Not pushed. No deployed Supabase mutation: true transactionality (RPC/migration) remains an authorized-deployment decision; main and room writes remain separate operations; concurrent-writer races stay with DATA-05.
- Remaining limits recorded in [DATA-02](data-and-calculation.md#data-02).

### DATA-03 — locally verified, committed, 2026-11-12

- Rental writes now establish a stable cross-store identity: the tab save path generates a `supabase_id` uuid for identity-less records and writes the same value to the local insert, the cloud insert payload (previously omitted), and the form; the local UPDATE persists `supabase_id` so unlinked rows gain identity on next save; the plain local insert branch retains its returned row id. `save_rental_record` assigns a fallback identity when a direct caller supplies none.
- Regressions `tests/test_rental_write_identity.py` (5 tests): **4 of 5 failed against the pre-fix source** (verified via temporary stash), **5 of 5 passed** after. Full isolated suite: **200 passed, 8 optional Qt Charts skips, 1 third-party scipy deprecation warning in 12.26 s**.
- Committed on `dev` as `db8fc36`. Not pushed. No deployed Supabase mutation.
- Remaining limits recorded in [DATA-03](data-and-calculation.md#data-03): pre-fix NULL-identity records stay unlinkable until their next edit-and-save; structured per-destination receipts remain with DATA-04.

## Test harness isolation

The full-suite harness used:

- `PYTHONDONTWRITEBYTECODE=1` and a temporary pycache prefix.
- Temporary LOCALAPPDATA, APPDATA, HOME, and USERPROFILE.
- `QT_QPA_PLATFORM=offscreen` for the suite.
- A process-local failing keyring backend, preventing normal credential-backend use.
- A precreated temporary application directory for fallback-key/database paths.
- A Python audit hook blocking external socket connections while allowing loopback for callback tests.
- Explicit allowance for SQLite `:memory:`.
- Restrictions against repository writes and real application data reads.
- Pytest cache disabled: `pytest tests -q -p no:cacheprovider --tb=short` through the guarded harness.

This was not a container or complete OS sandbox. Third-party pytest plugin autoload was not disabled. The protections are recorded precisely rather than described as total isolation.

The first harness attempt produced 136 passes and 21 failures because the harness blocked localhost, mishandled `:memory:`, and did not precreate the fallback-key parent. Correcting those harness restrictions produced 157 passes. The initial failures are not application findings.

## Native application smoke

The final native probe initialized Python's normal dependency/DLL support before redirecting application directories inside the child process. It isolated keyring, blocked network connections, restricted writes to a temporary directory, and prevented reads of real repository application data.

It launched the actual application, selected Dashboard, Calculator, History, Rental, Archive, Cloud Connection, and About, and checked lazy mounting. It captured the Calculator, requested a smaller size, closed the window, and observed process exit 0 with zero captured exceptions.

The inspected screenshot is a temporary local artifact: [calculator-empty.png](file:///C:/Users/Mr-N0N4M3/AppData/Local/Temp/huc-ui-audit-6ifxdcna/calculator-empty.png). It may disappear when temporary files are cleaned; the verification result is summarized here rather than relying only on that file.

Earlier attempts failed due to harness quoting, hidden user-site dependencies, console encoding, and pywin32 DLL loading after premature profile redirection. Those are not classified as application startup defects. The final corrected probe succeeded. The temporary keyring fallback warning was expected under deliberate keyring isolation.

No browser test was substituted for the native Qt UI. No complete golden-path cloud workflow, packaged installer test, or accessibility certification was performed.

## Supabase access

The user authorized read-only Supabase MCP access for the audit.

### 2026-11-12 (first session): tool path failure, then resolution

1. Initially, session tool discovery exposed no Supabase tools.
2. Read-only Qoder connector inspection showed one enabled/ready connector and a separate plugin requiring authentication. No configuration or authentication changes were made.
3. Two read-only `list_projects` invocations returned `MCP tool invocation did not complete` with error code -32603.
4. No backend calls were attempted without a working invocation path, and no root cause was established in that session.

### 2026-11-12 (second session): successful read-only inspection

The user asked that the Supabase MCP be added and OAuth invoked if needed. The MCP was already present and authorized in the new session; `list_projects` succeeded immediately, returning `invoice-studio` and `HUC Data` (`ldbzwpovomglwqkdwxeo`, ap-southeast-1, Postgres 15.8.1.114). The audit then performed a read-only inspection of `HUC Data` only:

- `list_tables` (verbose, schema `public`): `main_calculations` (RLS on, 1 row), `room_calculations` (RLS on, 11 rows), `rental_records` (RLS on, 0 rows), `_huc_schema_version` (RLS off, 0 rows), with the foreign key `room_calculations.main_calculation_id → main_calculations.id`.
- `pg_policies` query: each business table has two PERMISSIVE `ALL` policies granting unconditional access to `anon` (details in [SEC-01](security-and-delivery.md#sec-01)).
- `storage.buckets` query: one bucket, `rental-images`, `public: true`, no size or MIME limits (details in [SEC-04](security-and-delivery.md#sec-04)).
- Security advisor: `_huc_schema_version` RLS-disabled (ERROR), GraphQL anon/authenticated exposure of all four tables (WARN), Postgres security patches available (WARN).

No writes, migrations, policy changes, bucket changes, or data reads beyond table metadata and row counts were performed. Tenant record contents, Storage object policies and objects, auth user configuration, and API-gateway logs remain uninspected. Whether this project is the one the user's installations connect to is inferred from its name and creation date, not confirmed against a configured client. Any remediation (locking policies to `authenticated`, privatizing the bucket, enabling RLS on `_huc_schema_version`) is a deployed mutation requiring its own explicit authorization plus the coordinated app-auth decision, because the application currently depends on anonymous access.

## Acceptance tests

Use synthetic records, fake managers/workers, controlled signal delivery, and temporary stores for local regression tests. Live authorization tests need an explicitly authorized environment and identities.

| Scenario | Required assertion | Related findings |
| --- | --- | --- |
| Local/cloud numeric collision | Two unrelated records sharing ID 7 remain independent through edit, save-to-PC, archive, and cloud delete | [DATA-01](data-and-calculation.md#data-01) |
| Single requested destination fails | Result is failure for that destination, not partial success from an unrequested one | [DATA-04](data-and-calculation.md#data-04) |
| Partial save then retry | Successful destination retains identity/receipt and is not duplicated; only failed work is retried | [DATA-03](data-and-calculation.md#data-03), [DATA-04](data-and-calculation.md#data-04) |
| Aggregate failure injection | Fail after main write, after new rooms, and during old-room deletion; no false success or unaccounted partial aggregate | [DATA-02](data-and-calculation.md#data-02) |
| Empty/concurrent replacement | Agreed empty semantics enforced; concurrent saves respect scoped uniqueness and retry identity | [DATA-02](data-and-calculation.md#data-02), [DATA-05](data-and-calculation.md#data-05) |
| Calculation freshness | Edit inputs/period/structure after calculation; each save/export rejects or recalculates stale output | [CALC-02](data-and-calculation.md#calc-02) |
| Later-room failure/empty room | No partial result set is published; a previously calculated now-empty room does not retain an apparently current bill | [CALC-02](data-and-calculation.md#calc-02) |
| Numeric boundaries | Finite/range/sign/precision/zero-denominator rules match across UI, import, compute, save, and export | [CALC-01](data-and-calculation.md#calc-01), [CALC-04](data-and-calculation.md#calc-04) |
| CSV round trip | More than ten readings, Unicode, large integers, duplicate periods, and malformed data are handled losslessly or explicitly rejected | [CALC-03](data-and-calculation.md#calc-03), [CALC-05](data-and-calculation.md#calc-05) |
| No-op history edit | All readings, metadata, names, and unchanged attachments survive an unchanged edit | [CALC-06](data-and-calculation.md#calc-06) |
| Undo after rate change | Surviving rooms retain current results; restored room inputs recompute under current policy/revision; stale tokens still reject | [CALC-08](data-and-calculation.md#calc-08) |
| Carry-forward boundaries | Original nested source remains unchanged; dirty draft protection and December/year limits work | [CALC-09](data-and-calculation.md#calc-09) |
| Disconnect/reconnect | Late old OAuth, monitor, or worker signals cannot persist credentials, disable the new connection, or publish into its views/cache | [SEC-07](security-and-delivery.md#sec-07), [DATA-09](data-and-calculation.md#data-09) |
| History source/filter switch | Start cloud A, request B, switch to CSV, deliver A; CSV remains authoritative and latest intent is not silently lost | [DATA-10](data-and-calculation.md#data-10) |
| Rental append versus refresh | Start append at offset 25, force refresh, then deliver old page; fresh pagination/cache/table remain coherent | [UI-04](ui-and-runtime.md#ui-04) |
| Archived overlapping loads | Old A cannot overwrite B or remove B's loading indicator | [DATA-10](data-and-calculation.md#data-10) |
| Dashboard year switch | Complete 2025 after selecting 2026; display remains scoped to 2026 and its requested sync eventually runs | [DASH-03](ui-and-runtime.md#dash-03) |
| Overlapping edit owners | Acquire a domain twice; releasing one does not release the other's protection; deferred status clears correctly | [state inventory](state-machines.md#highest-risk-interactions) |
| Cursor ordering/project switch | Main advancing first cannot skip room changes; project B cannot inherit project A's checkpoint/cache | [DATA-06](data-and-calculation.md#data-06), [DATA-09](data-and-calculation.md#data-09) |
| Exact page boundary/later-page failure | Partial data is never pruned as authoritative; all pages use stable order and scope | [DATA-07](data-and-calculation.md#data-07) |
| Sorted refresh | Display cells and payload identities stay aligned; selection restores to the same entity | [UI-01](ui-and-runtime.md#ui-01) |
| Close/cancel blocked images | X, Escape, accept, reject, and app shutdown invalidate callbacks and observe actual worker completion | [RUN-03](ui-and-runtime.md#run-03), [RUN-06](ui-and-runtime.md#run-06) |
| Resize/cache/batch | Nested ownership, reentrant debounce, fallback/reset, safe-mode aliases, and unsampled content edits preserve state | [RUN-08](ui-and-runtime.md#run-08) |
| Dashboard meaning | January compares with previous December; missing months stay missing; occupancy and freshness labels match data scope | [DASH-04](ui-and-runtime.md#dash-04), [DASH-05](ui-and-runtime.md#dash-05), [DASH-09](ui-and-runtime.md#dash-09) |
| Native platform behavior | Keyboard-only operations, high DPI, multi-monitor placement, filenames/overwrite, focus, and screen-reader labels work | [RUN-09](ui-and-runtime.md#run-09), [RUN-11](ui-and-runtime.md#run-11), [RUN-12](ui-and-runtime.md#run-12) |
| Release integrity | Exact expected assets and checksums correspond to one immutable SHA; missing/failed upload fails the release step | [REL-01](security-and-delivery.md#rel-01), [REL-02](security-and-delivery.md#rel-02), [REL-03](security-and-delivery.md#rel-03) |

## Implementation roadmap

The user authorized careful sequential local remediation after the audit. Stage 1 has RUN-01 and DASH-01 locally verified. On 2026-11-12 the user redirected subsequent work: chart animations are dropped (already removed), and the next slice is meaningful UI/UX and flow improvement rather than animation work. The broader stages remain a roadmap, not authorization for cloud changes, a commit, deployment, or unresolved business-policy choices.

| Stage | Scope | Dependencies and exit evidence |
| --- | --- | --- |
| 1. Containment | Wrong-record operations, false success, unsafe provisioning, hover recursion, release asset safety | Focused regressions that demonstrate original failure and corrected behavior; no unrelated refactor |
| 2. Contracts and data inspection | Ownership, authority, rounding, physical rooms, tenancy dates, uniqueness, empty replacement, retention | Approved semantics; successful read-only deployed inspection; duplicate assessment; backup/restore rehearsal before migrations |
| 3. Calculation and persistence | Pure current result snapshots, lossless import/edit, receipts, atomic authorized aggregate writes | Round-trip preservation; failure-injection coverage; retry safety; explicit Storage lifecycle |
| 4. Sync and lifecycle | Project-scoped state, complete pagination, transactional publication, generations/latest intent, worker shutdown | Controlled out-of-order completion tests, page-boundary tests, and acknowledged close/cancel behavior |
| 5. UI/design-system slice | Shared tokens/actions, one corrected table or list/inspector, truthful result/loading/status states | Native keyboard, narrow-window, high-DPI, multi-monitor, empty/error/stale, and assistive-technology checks |
| 6. Delivery hardening | Tracked tests, locked dependencies, supported Python, packaged functional smoke, installer upgrade | Clean-machine build/install/upgrade; restoration test; immutable release manifest and verified assets |

Do not combine accounting-policy changes, deployed schema migration, and a broad visual rewrite into one change. Each stage should leave a verifiable boundary that later work can rely on.

## Unresolved decisions

The [architecture document](architecture-and-ux.md#decisions-required-before-implementation) records the product decisions. Principal unknowns are project/ownership scope, independent destinations versus replicas, authority and concurrency, financial policy, empty replacement, room identity, document access/retention, and offline editing requirements.

## Remaining blind spots

- Deployed authorization, grants, API exposure, bucket privacy, schema drift, and actual volume.
- Real multi-device races, token renewal/revocation, provisioning recovery, and live service failures.
- Packaged executable behavior, installer upgrade/uninstall, signed artifacts, and restoration.
- Representative sustained CPU/memory/latency, cold/warm cache behavior, and large-table measurements.
- Screen-reader use, real high-DPI/multi-monitor interactions, and user usability research.
- Dependency vulnerabilities and distribution-license compliance.
- Framework/SDK internals and every possible runtime interleaving.

These limits are not a reason to discard source-confirmed defects; they identify which claims must remain conditional and what evidence to obtain next.

## Documentation validation

On 2026-11-12, the newly written documentation set was checked without changing application code:

- Eight Markdown files.
- 71 unique finding IDs, 34 state-machine families, and 22 design-system groups.
- 420 local links checked for target existence, internal Markdown anchors, and source-line bounds.
- Final-newline and unintended-whitespace checks passed.
- `git check-ignore` confirmed the documents are not ignored.
- Git status showed only the new audit documentation directory; tracked application files remained unchanged.

Link and line-bound validation establishes navigability, not independent semantic proof of every finding. No Git commit was created. The documents will be updated as subsequent work changes evidence, decisions, or implementation status; no unattended update service was configured.

## Research sources

Official references consulted by the coordinating audit or specialist reviewers; they support platform contracts, not observations of this deployment:

- [Supabase Management integrations and OAuth](https://supabase.com/docs/guides/integrations/build-a-supabase-integration).
- [Supabase API security: grants and RLS](https://supabase.com/docs/guides/api/securing-your-api).
- [Supabase API keys](https://supabase.com/docs/guides/api/api-keys).
- [Supabase Storage bucket fundamentals](https://supabase.com/docs/guides/storage/buckets/fundamentals).
- [Supabase monitoring and debugging](https://supabase.com/docs/guides/monitoring-and-debugging).
- [Supabase change: tables not automatically exposed](https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically).
- [Supabase change: OAuth token endpoint success status](https://supabase.com/changelog/45468-breaking-change-oauth-token-endpoint-will-return-http-200-instead-of-201).
- [Supabase scoped personal access tokens](https://supabase.com/changelog/scoped-personal-access-tokens-ga).
- [OAuth for native applications, RFC 8252](https://www.rfc-editor.org/rfc/rfc8252).
- [OAuth security best current practice, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700).
- [Qt thread and object ownership](https://doc.qt.io/qt-5/threads-qobject.html).
- [Qt QBarSet signal contracts](https://doc.qt.io/qt-5/qbarset.html).
- [Qt QCategoryAxis behavior](https://doc.qt.io/qt-5/qcategoryaxis.html).
- [Python 3.10 lifecycle notice](https://www.python.org/downloads/release/python-31020/).

A guessed OAuth documentation path returned 404 during research and was not used as evidence. Generic summaries that confused Management OAuth with end-user Auth were not accepted as proof.

## Document update checklist

When new work changes the evidence:

- Update the finding's status and distinguish implemented from verified.
- Record date, test scope, outcome, and remaining conditional impact.
- Update source references, state transitions, design contracts, and roadmap dependencies affected by the change.
- Add live verification only when a tool/query actually succeeded against the identified authorized project.
- Do not count a saved setting, emitted stop request, available tool schema, or successful class construction as proof of the corresponding runtime effect.
- Correct outdated claims explicitly, preserving stable finding IDs and the reason for the correction.
- Keep secrets, tenant records, and raw sensitive logs out of the audit documents.
