# Data integrity and calculation findings

[Audit index](README.md)  
Last updated: 2026-11-12  
Disposition: all findings below are open; no fixes were implemented during the audit.

Evidence labels and priorities are defined in the [index](README.md#evidence-and-priority-vocabulary). Proposed financial and data-authority semantics require decisions before implementation.

## Record identity and persistence

### DATA-01

**Cross-source numeric IDs can target unrelated local records.**  
Priority: P1. Evidence: S.

Loading a cloud record into the edit form assigns its numeric `id` to `current_rental_id`. Saving to PC can then update a local record with that ID. Successful cloud deletion can also delete a local row by that same numeric ID. Equal integers from different stores do not establish record identity.

Evidence: [rental_info_tab.py:3165](../../../src/ui/tabs/rental_info_tab.py#L3165), [rental_info_tab.py:3799](../../../src/ui/tabs/rental_info_tab.py#L3799), [rental_record_dialog.py:1413](../../../src/ui/rental_record_dialog.py#L1413).

Recommendation: carry source/project identity with record references and maintain explicit local/cloud correspondence. Test two unrelated records that deliberately share a numeric ID. UUIDs everywhere are not required; correct scoping is.

### DATA-02

**Monthly cloud save, replacement, and deletion have partial durable outcomes.**  
Priority: P1. Evidence: R-main, S; concurrent-writer impact is C.

Main and room writes occur separately. Room replacement inserts new rows before deleting old ones; deletion errors can still return success. With existing room ID 41, an actual-method fake-client probe of an empty replacement returned `True` without issuing deletion. Monthly deletion removes children before the parent without an encompassing transaction.

Evidence: [supabase_manager.py:261](../../../src/core/supabase_manager.py#L261), [supabase_manager.py:315](../../../src/core/supabase_manager.py#L315), [supabase_manager.py:1022](../../../src/core/supabase_manager.py#L1022), [HomeUnitCalculator.py:2277](../../../src/core/HomeUnitCalculator.py#L2277).

Recommendation: an authorized, transactional monthly aggregate operation with explicit empty-replacement semantics and retry identity. Use cascading parent deletion where the verified schema supports it. Storage uploads remain outside a SQL transaction and need their own completion/cleanup contract.

### DATA-03

**Rental inserts do not establish the identity required by later updates.**  
Priority: P1. Evidence: S; deployed triggers/defaults remain C.

The bundled schema does contain a unique `supabase_id` column. However, the insert payload does not assign it, and the write path updates only when the input has `supabase_id`; a numeric `id` does not select the update path. A fresh bundled schema therefore permits inserted records without the identifier the editor relies on. The local normal-insert path also ignores its returned ID.

Evidence: [supabase_schema.py:74](../../../src/core/supabase_schema.py#L74), [supabase_manager.py:789](../../../src/core/supabase_manager.py#L789), [rental_info_tab.py:3186](../../../src/ui/tabs/rental_info_tab.py#L3186).

Recommendation: select one stable cloud identity contract and return structured receipts with persisted identifiers. Retain successful destination receipts so retries do not create duplicates. Do not describe this as a missing-column defect.

### DATA-04

**Save outcome reporting confuses unrequested and successful destinations.**  
Priority: P1. Evidence: S.

Both local and cloud success flags initialize to `True`. If only one destination is requested and fails, the unrequested destination can make the result appear partially successful. Partial retries also lack a reliable record of which destination already succeeded.

Evidence: [rental_info_tab.py:3160](../../../src/ui/tabs/rental_info_tab.py#L3160).

Recommendation: use not-requested, pending, succeeded, and failed outcomes per destination. A final result must include the completed receipt and the recoverable failure, not a success-like string.

### DATA-05

**Lookup-then-insert lacks a matching monthly uniqueness boundary.**  
Priority: P1. Evidence: S/C.

The save path selects an existing monthly record before inserting, while the bundled schema lacks a matching period uniqueness constraint. Concurrent clients can both decide to insert. Concurrent room replacements can likewise duplicate children.

Evidence: [supabase_manager.py:261](../../../src/core/supabase_manager.py#L261), [supabase_schema.py:34](../../../src/core/supabase_schema.py#L34).

Recommendation: first decide whether uniqueness is per property, account, organization, or project and period. Inspect existing duplicates before applying an appropriate constraint and transactional write path.

## Synchronization and cache correctness

### DATA-06

**Delta synchronization does not have reliable independent change cursors.**  
Priority: P1. Evidence: S, R-specialist.

Main updates do not consistently advance `updated_at`; no corresponding bundled update trigger establishes that invariant. Room signatures depend on IDs/parent IDs rather than content revisions. Independently running workers share or depend on the main watermark, allowing one lane to advance beyond changes another lane has not processed.

Evidence: [supabase_manager.py:63](../../../src/core/supabase_manager.py#L63), [supabase_manager.py:254](../../../src/core/supabase_manager.py#L254), [background_workers.py:243](../../../src/ui/background_workers.py#L243), [background_workers.py:341](../../../src/ui/background_workers.py#L341).

Qualification: empty-delta paths can fall back to full reconciliation; the application is not universally deletion-blind.

Recommendation: prefer complete selected-year reconciliation at the current monthly-data scale unless measurements justify more complex cursors. Any delta protocol needs durable server revisions, independent checkpoints, deletion semantics, and a consistent boundary.

### DATA-07

**Incomplete fetches can be treated as authoritative snapshots.**  
Priority: P1. Evidence: S/C.

Several fetches lack complete deterministic pagination while downstream reconciliation prunes rows absent from the returned IDs. Chunking parent IDs does not guarantee complete pagination of child rows. The deployed API row limit was not inspected.

Evidence: [supabase_manager.py:481](../../../src/core/supabase_manager.py#L481), [supabase_manager.py:666](../../../src/core/supabase_manager.py#L666), [supabase_manager.py:850](../../../src/core/supabase_manager.py#L850), [background_workers.py:388](../../../src/ui/background_workers.py#L388).

Recommendation: stable pagination and an explicit complete/incomplete result. Permit authoritative pruning only for a complete, correctly scoped snapshot. Test exact page boundaries and failure on a later page.

### DATA-08

**Cache rows, pruning, and checkpoints publish through separate commits.**  
Priority: P1. Evidence: S, R-specialist.

Consumers can observe mixed main/room generations. Upserts, deletion of absent rows, and checkpoint updates do not share one publication transaction. Natural-key replay involving null or renamed room values can also fail against primary keys.

Evidence: [db_manager.py:177](../../../src/core/db_manager.py#L177), [db_manager.py:368](../../../src/core/db_manager.py#L368), [db_manager.py:867](../../../src/core/db_manager.py#L867).

Recommendation: validate a complete snapshot and publish rows, pruning, and checkpoint together. Avoid relying on display names as immutable cache identity.

### DATA-09

**Project identity is missing from cache/checkpoint ownership.**  
Priority: P1. Evidence: S/C.

Cache and cursor namespaces identify the source as Supabase without consistently including project identity. Switching projects can reuse old state, and already-running old-project work can publish into current storage or views.

Evidence: [db_manager.py:150](../../../src/core/db_manager.py#L150), [remote_change_monitor.py:85](../../../src/core/remote_change_monitor.py#L85).

Recommendation: project-scoped stores/checkpoints plus a connection generation on callbacks. Clearing a screen alone does not invalidate an old worker.

### DATA-10

**Request completion can disagree with current selection and latest intent.**  
Priority: P1. Evidence: R-main, S.

The dashboard callback renders the year passed by the completed worker without establishing that it is still selected. A main-agent method probe confirmed rendering of the passed old year; the full selector race is supported by source rather than an end-to-end reproduction. History and rental loaders can drop newer requests, and archive loading permits overlapping publication.

Evidence: [dashboard_tab.py:1826](../../../src/ui/tabs/dashboard_tab.py#L1826), [history_tab.py:4308](../../../src/ui/tabs/history_tab.py#L4308), [rental_info_tab.py:3385](../../../src/ui/tabs/rental_info_tab.py#L3385), [archived_info_tab.py:481](../../../src/ui/tabs/archived_info_tab.py#L481).

Recommendation: immutable project/source/filter/page/generation context, obsolete-result rejection, and scheduling of the latest pending request. Rejection alone does not fulfill the user's newest request.

### DATA-11

**Blind local-change suppression can discard another device's update.**  
Priority: P1. Evidence: R-main.

Reproduction: establish baseline A; mark a local rental change; receive unchanged A; receive another device's edit. The suppression survives the unchanged poll, discards the unrelated difference, and advances the baseline. Zero remote events are emitted.

Evidence: [remote_change_monitor.py:85](../../../src/core/remote_change_monitor.py#L85).

Recommendation: identify a real local echo using a revision/operation identity, or reconcile without suppressing the next arbitrary difference.

### DATA-12

**Missing, invalid, empty, and failed values are conflated.**  
Priority: P2. Evidence: S.

Some numeric/cache projections turn invalid values into zero; a failed year fetch returns an empty list; tenancy start/end fields are lost in parts of cache projection/reading. These choices affect occupancy, trends, and the apparent completeness of financial results. Monetary `REAL` values and client-naive timestamps add precision and ordering concerns.

Evidence: [db_manager.py:264](../../../src/core/db_manager.py#L264), [db_manager.py:766](../../../src/core/db_manager.py#L766), [supabase_manager.py:538](../../../src/core/supabase_manager.py#L538).

Recommendation: typed outcomes for error/empty/missing, preserved business dates, and agreed monetary/time representations. Do not fabricate measured zeros from absent data.

### DATA-13

**Display position is overloaded as physical room identity.**  
Priority: P2. Evidence: S/C.

Positional `Room N` names are regenerated after structural changes and hardcoded in some persistence/export paths. Historical room associations, custom names, and current occupancy cannot safely depend on those labels being immutable.

Evidence: [main_tab.py:2008](../../../src/ui/tabs/main_tab.py#L2008), [HomeUnitCalculator.py:2292](../../../src/core/HomeUnitCalculator.py#L2292).

Recommendation: retain a stable room reference independent of display order and label. Establish the intended treatment of existing historical names before migration.

## Financial calculations, import, and export

### CALC-01

**The display format discards precision and becomes calculation input.**  
Priority: P1. Evidence: R-main.

Actual methods with synthetic text/widget doubles produced a displayed rate of `3.33` from `10000 / 3000`; the room calculation reread that rate and produced `9990` for 3000 units. An additional `0.99` was displayed as `0`. Room component and total displays also round separately to whole TK.

Evidence: [main_tab.py:1522](../../../src/ui/tabs/main_tab.py#L1522), [main_tab.py:2159](../../../src/ui/tabs/main_tab.py#L2159).

Recommendation: pure numeric results separated from formatting, with an approved Decimal/minor-unit and rounding contract. Precision loss is reproduced; the correct billing policy must not be invented during refactoring.

### CALC-02

**Calculation freshness is not represented or enforced.**  
Priority: P1. Evidence: S, R-specialist.

Input edits, period changes, and structural changes can retain old results. Room calculation can update only a prefix before a later validation failure; an empty room can retain old labels. Save/export reads displayed results without verifying that they belong to current inputs.

Evidence: [main_tab.py:930](../../../src/ui/tabs/main_tab.py#L930), [main_tab.py:1522](../../../src/ui/tabs/main_tab.py#L1522), [main_tab.py:2159](../../../src/ui/tabs/main_tab.py#L2159), [HomeUnitCalculator.py:1465](../../../src/core/HomeUnitCalculator.py#L1465).

Recommendation: input revision plus immutable complete result snapshot. Validate all rooms before publishing results; mark results stale on any relevant edit. Save/export must consume a current validated snapshot.

### CALC-03

**CSV loading can retain old fields and calculate with an old rate.**  
Priority: P1. Evidence: R-specialist, S.

The CSV loader does not calculate the main result before calculating rooms and does not symmetrically initialize all fields. A specialist probe loading meters `[100, 200]` and differences `[10, 0]` retained an old difference of `999`; a previous rate of 9 produced a room bill of 90.

Evidence: [main_tab.py:2523](../../../src/ui/tabs/main_tab.py#L2523).

Recommendation: parse into a complete draft, validate it, replace all fields, and compute main then room results from that draft. Failure must not partially overwrite the current draft.

### CALC-04

**Validation varies across UI, import, calculation, and persistence.**  
Priority: P1/P2. Evidence: S, R-specialist.

Programmatic `setText()` bypasses validators. Fractional readings can be truncated in one path and rejected by cloud integer conversion in another. Partial decimal text, non-finite values, very large inputs, sign rules, and zero denominators have inconsistent outcomes. A zero denominator can look like a successful zero rate.

Evidence: [main_tab.py:97](../../../src/ui/tabs/main_tab.py#L97), [main_tab.py:1524](../../../src/ui/tabs/main_tab.py#L1524), [main_tab.py:2180](../../../src/ui/tabs/main_tab.py#L2180), [main_tab.py:2343](../../../src/ui/tabs/main_tab.py#L2343).

Recommendation: one boundary parser with approved finite/range/sign/precision/missing-value rules. Widget validators are assistance, not the only validation layer.

### CALC-05

**CSV representation and selection rules do not match the UI.**  
Priority: P1/P2. Evidence: R-specialist, S.

The UI permits more than ten reading pairs but the writer stores ten. A specialist case with eleven readings totaling 66 exported ten totaling 55 while retaining total 66. Duplicate saves append while loading can select the earliest matching period. Integer values pass through float normalization; writer encoding is implicit while the reader expects UTF-8.

Evidence: [HomeUnitCalculator.py:2011](../../../src/core/HomeUnitCalculator.py#L2011), [main_tab.py:2501](../../../src/ui/tabs/main_tab.py#L2501), [main_tab.py:2527](../../../src/ui/tabs/main_tab.py#L2527).

Recommendation: a versioned lossless format, explicit revision selection, encoding, and complete atomic writes. An immediate explicit capacity limit is safer than silent truncation if format evolution is deferred.

### CALC-06

**History edits can lose unchanged inputs, metadata, and attachments.**  
Priority: P1. Evidence: S.

Reading arrays and scalar fields are populated asymmetrically, some scalar handling truncates after three fields, and reconstructed JSON can drop unrelated keys. Existing remote image URLs can be sent as local file paths, rejected by upload, converted to `None`, and lost when old rows are removed. Main and room saves are separate operations.

Evidence: [history_tab.py:327](../../../src/ui/tabs/history_tab.py#L327), [history_tab.py:655](../../../src/ui/tabs/history_tab.py#L655), [history_tab.py:738](../../../src/ui/tabs/history_tab.py#L738), [history_tab.py:861](../../../src/ui/tabs/history_tab.py#L861), [supabase_manager.py:175](../../../src/core/supabase_manager.py#L175).

Recommendation: lossless no-op edit round trips and explicit unchanged/removed/replaced/failed-upload attachment states. Do not accept a dialog as fully saved after only one aggregate component persisted.

### CALC-07

**Exports interpret markup and can silently undercount.**  
Priority: P2. Evidence: R-specialist, S/C.

Synthetic markup reached the ReportLab `Paragraph` path through a mocked probe; actual external content fetching was not executed. Spreadsheet formula interpretation is a conditional concern at text-export boundaries. Some summary loops catch errors midway and continue, yielding plausible but incomplete totals.

Evidence: [HomeUnitCalculator.py:1623](../../../src/core/HomeUnitCalculator.py#L1623), [HomeUnitCalculator.py:1810](../../../src/core/HomeUnitCalculator.py#L1810), [HomeUnitCalculator.py:2120](../../../src/core/HomeUnitCalculator.py#L2120), [main_tab.py:2375](../../../src/ui/tabs/main_tab.py#L2375).

Recommendation: escape ReportLab markup, handle spreadsheet text intentionally, and export only a fully validated calculation snapshot. An incomplete financial export should clearly fail rather than hide missing components.

### CALC-08

**Undo can restore the removed room's old derived bill.**  
Priority: P2. Evidence: S, R-specialist.

Undo correctly checks the newest token, editable snapshot, count, and maximum. It rebuilds surviving rooms from their current snapshots, preserving their recalculated results. However, the removed room is reinserted from its earlier snapshot, including derived labels, even if the rate changed meanwhile.

Evidence: [main_tab.py:1986](../../../src/ui/tabs/main_tab.py#L1986), [main_tab.py:2084](../../../src/ui/tabs/main_tab.py#L2084), [main_tab.py:2122](../../../src/ui/tabs/main_tab.py#L2122).

Recommendation: preserve the existing safeguards; restore the removed room's identity/inputs and recompute under the current result revision. Do not describe all undo behavior as broken.

### CALC-09

**Carry-forward is not a pure, explicitly scoped draft transformation.**  
Priority: P2. Evidence: S, R-specialist.

Shallow copies can mutate nested source data. The selected source can be latest cloud data rather than the implied current month; there is no dirty-draft replacement guard. Malformed data can become zero, precision can be lost during formatting, and December 2100 can advance beyond the supported year range. The cached manager can retain a previous connection.

Evidence: [add_month_manager.py:129](../../../src/core/add_month_manager.py#L129), [add_month_manager.py:164](../../../src/core/add_month_manager.py#L164), [add_month_manager.py:261](../../../src/core/add_month_manager.py#L261), [main_tab.py:2745](../../../src/ui/tabs/main_tab.py#L2745).

Recommendation: a pure normalized transformation with explicit source-period preview, boundary checks, and replace-draft confirmation. A new draft is uncalculated, not a successful zero-valued bill.

### CALC-10

**Exports discover domain information through obsolete widget structure.**  
Priority: P2. Evidence: S.

Some paths expect QGroupBox/grid structure while the screen uses cards/FlowLayout, then fall back to generic room names. Cloud serialization hardcodes positional names. PDF creation-period labeling can use a next-month label without a year and omit some auditable inputs.

Evidence: [HomeUnitCalculator.py:1731](../../../src/core/HomeUnitCalculator.py#L1731), [HomeUnitCalculator.py:1774](../../../src/core/HomeUnitCalculator.py#L1774), [HomeUnitCalculator.py:2109](../../../src/core/HomeUnitCalculator.py#L2109), [HomeUnitCalculator.py:2292](../../../src/core/HomeUnitCalculator.py#L2292).

Recommendation: model-backed export with exact room names, period/year, input readings, calculation revision, and approved formatting. Layout changes must not alter serialized business meaning.

## Shared acceptance criteria

See [verification and roadmap](verification-and-roadmap.md#acceptance-tests) for cross-source collisions, partial writes, retries, round trips, stale calculations, cursor ordering, pagination, and project-switch tests. The [architecture proposal](architecture-and-ux.md#recommended-boundaries) deliberately avoids introducing a generic synchronization framework before these concrete contracts are resolved.
