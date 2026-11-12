# Architecture and UI/UX recommendations

[Audit index](README.md)  
Last updated: 2026-11-12  
Status: recommendations for evaluation, not an approved implementation or migration plan.

## Recommendation

Retain PyQt and the existing modular-monolith shape. Contain immediate defects, then introduce a few explicit boundaries around calculations, identity, persistence, asynchronous publication, and shared UI behavior.

The highest-impact defects come from meaning and ownership being implicit: labels serve as numeric state; numeric IDs cross store boundaries; separately committed writes look like one operation; worker completion is not tied to current intent; and stored credentials are treated as operational readiness. A framework or frontend rewrite does not independently solve any of these.

## Independent architecture assessment

The architecture specialist challenged broad-refactor options rather than assuming the largest redesign was best. Its recommended sequence was surgical containment followed by selected vertical slices. The main audit agrees with that recommendation, subject to the unresolved product contracts below.

| Option | Benefit | Cost or constraint | Disposition |
| --- | --- | --- | --- |
| Surgical fixes only | Fastest containment; limited migration surface | Leaves label-based calculation and identity coupling in place | Appropriate first stage, not sufficient as the entire strategy |
| Retain Qt with selective modularization | Addresses observed root causes while preserving working UI/platform investment | Requires clear contracts and behavior tests | Recommended default |
| SQLite-only with explicit backup/export | Simpler operational model | Cloud collaboration may be a product requirement | Product alternative, not an assumed change |
| Small authoritative backend while retaining Qt | Can support confidential OAuth exchange, shared tenancy, strong authorization, and transactional operations | Hosting, monitoring, deployment, and recovery responsibilities | Justified only by actual security/product requirements |
| Web rewrite | Potentially different distribution/collaboration model | Large migration, accessibility, offline, packaging, and testing costs; does not fix accounting semantics | Not justified merely by the defects found |

Avoid speculative CQRS, event sourcing, universal repositories, a dependency-injection framework, a general FSM engine, or an offline outbox. Authoritative offline cloud-bound editing has not been established as a requirement. Cached offline viewing is a different and simpler capability.

## Recommended boundaries

```text
Qt views and shared actions
        |
Small application operations
        |
Pure calculation values and explicit record/result identities
        |
Existing SQLite, Supabase, and document adapters
```

### Calculation boundary

- Collect a complete draft from the UI.
- Parse and validate boundary input once with agreed numeric rules.
- Calculate without widgets and publish one complete result snapshot.
- Associate the result with a draft revision, period, and structure.
- Render formatting from numeric results; never reparse formatted labels for downstream calculations.
- Save/export only a current validated result.

The smallest useful extraction is a few values and pure functions, not a large domain framework. Establish the rounding policy first; an architectural extraction must not silently change historical financial meaning.

Related findings: [CALC-01](data-and-calculation.md#calc-01), [CALC-02](data-and-calculation.md#calc-02), [CALC-04](data-and-calculation.md#calc-04).

### Identity boundary

- Carry source and project scope with record references.
- Maintain explicit local/cloud mappings when a record exists in both stores.
- Keep stable physical room identity separate from display name and position.
- Define aggregate and monthly uniqueness only after property/account/organization scope is agreed.
- Make edit/delete confirmations identify the actual selected entity and destination.

Replacing every integer with a UUID is not necessary; correctly scoped identity is. Before changing deployed identity constraints, inspect actual duplicates and rehearse backup restoration.

Related findings: [DATA-01](data-and-calculation.md#data-01), [DATA-03](data-and-calculation.md#data-03), [DATA-05](data-and-calculation.md#data-05), [DATA-13](data-and-calculation.md#data-13).

### Persistence boundary

- Treat a monthly main calculation and its room records as one authorized database aggregate.
- Establish explicit empty-replacement and delete semantics.
- Return operation receipts with durable identifiers and per-destination outcomes.
- Make retries safe for completed destinations rather than replaying all work.
- Separate unchanged/removed/replaced/failed-upload document states.

A SQL transaction does not include Storage uploads. Stage/complete/clean up those resources under a separate bounded contract. Do not promise distributed atomicity across PC, cloud database, and Storage when the implementation cannot provide it.

Related findings: [DATA-02](data-and-calculation.md#data-02), [DATA-04](data-and-calculation.md#data-04), [CALC-06](data-and-calculation.md#calc-06).

### Asynchronous publication boundary

Every request should capture immutable context: connection generation, project, source, selected period/filter, and pagination/replacement intent. A completion may publish only if that context still applies.

Rejection of obsolete results is necessary but insufficient. Retain the latest request and schedule it after the current operation when appropriate; otherwise the newest user intent is still lost.

Use ownership tokens for overlapping edits and operations. Distinguish cancellation requested, cancellation acknowledged, and callback invalidation. Blocking network requests need real deadlines; `quit()` is not a general cancellation mechanism.

Related findings: [DATA-09](data-and-calculation.md#data-09), [DATA-10](data-and-calculation.md#data-10), [RUN-03](ui-and-runtime.md#run-03).

### Cache boundary

At the current apparent monthly-data scale, favor a complete authorized, deterministically paginated, server-consistent selected-year snapshot over an unreliable complex delta protocol. Confirm real scale before deciding the final fetch strategy.

Publish cache upserts, pruning, and checkpoint as one SQLite transaction. Partition by project and source. Expose completeness and freshness from that snapshot, including room-dependent metrics. Prune only when completeness is established.

Related findings: [DATA-06](data-and-calculation.md#data-06), [DATA-07](data-and-calculation.md#data-07), [DATA-08](data-and-calculation.md#data-08), [DASH-06](ui-and-runtime.md#dash-06).

### Presentation boundary

Keep concrete managers as adapters with explicit contracts. Introduce only the application operations currently needed, such as calculate, save monthly aggregate, and refresh scoped snapshot.

Use shared QActions and supported Qt/Fluent styling. Extract shared components where interaction semantics match, not merely where source code looks similar. Pilot Qt Model/View on one table or list/inspector screen; measure correctness and responsiveness before expanding it.

Related inventory: [design system](design-system.md).

## Creative UI direction

### Billing ledger, with a pulse

The proposed product character is a dependable billing workstation: clear period/source context, auditable financial relationships, calm status feedback, and recovery that remains visible. This is a design hypothesis, not a result from user interviews or a usability study.

### Information architecture

- **Billing:** current-period input, calculation, reconciliation, and save/export.
- **Rooms and tenants:** searchable list with an adjacent inspector; Active/Archived is a filter within a coherent workflow.
- **History:** a period/revision ledger with clearly scoped edit/delete/export actions.
- **Overview:** a summary of measured outcomes and data health rather than a second calculation workspace.
- **Cloud settings:** administrative authorization, selected project, data access, and synchronization health.

These are proposed groupings, not a requirement to rename every current route. Local and cloud destinations must remain explicit until their authority/replication contract is decided.

### Billing workspace

- Keep period, property/project, and source context visible.
- Present inputs alongside an auditable calculation breakdown, with a narrow-window stacked arrangement.
- Show Not calculated, Up to date, or Inputs changed as persistent result state.
- Give one dominant total; show intermediate quantities with consistent units and tabular numerals.
- Explain main cost, room allocations, additional charges, and residuals only after those accounting meanings are agreed.
- Keep the most important calculate/save actions discoverable; do not rely solely on a collapsed action region or undocumented shortcuts.

### Save and recovery experience

Show separate PC and Cloud outcomes. A receipt should state what completed and offer Retry failed destination when applicable. Do not erase the form or identity needed to recover a partial result.

Transient notices are appropriate for transient success; incomplete saves, authorization problems, and stale results require persistent visible state. Confirmation must identify the actual entity and destination, not just the action name.

### Records and documents

A list/inspector layout can reduce modal context switching while retaining focused edit dialogs where appropriate. Preserve selection by identity during refresh. Expose explicit archive/restore and document replace/remove controls.

Documents are sensitive resources, not decorative thumbnails. Show missing, loading, unavailable, unauthorized, and invalid states accurately. Avoid exposing internal storage URLs or implying that a preview failure means the underlying record was deleted.

### Dashboard

- Put period, source, completeness, and freshness before decorative metrics.
- Distinguish zero from missing data.
- Use explicit previous-period boundaries, especially January/December.
- Name occupancy metrics according to what they actually measure.
- Keep independent panel-year selectors visible if independent comparison remains intentional.
- Provide chart-to-table access and use non-color cues.
- Avoid interpolated curves, baselines, or trend icons that imply unsupported meaning.

### Visual language

Retain Fluent's platform familiarity. Reduce competing accents, use semantic colors for state, strengthen alignment, and distinguish primary financial values from contextual metrics. Choose type and size rules that work with actual Qt5 font semantics and supported display scaling.

Motion should explain a state change, not stand in for progress or correctness. Respect reduced-motion needs where supported and avoid unnecessary animation in dense financial reading tasks.

### Accessibility and platform acceptance

Use shared actions, keyboard-complete interactions, visible focus, correct focus eligibility, accessible labels, predictable Escape, and focus restoration. Test real high-DPI/multi-monitor coordinates and logical-pixel sizes. The observed 1000 by 700 application minimum is a fact from one native smoke run, not proof that smaller displays or all dialogs are usable.

## Decisions required before implementation

1. Does a cloud project represent a person, property, organization, or another scope?
2. Are PC and Cloud independent save destinations or replicas? Which is authoritative?
3. Are concurrent writers supported, and what is the conflict rule?
4. What are the approved rounding, fractional amount, zero-consumption, residual, and historical-correction policies?
5. Does empty room replacement mean remove all rooms or reject the operation?
6. What identifies a physical room across renaming and historical records?
7. Who may access identity documents, and what are retention and deletion obligations?
8. Is authoritative offline editing required, or is offline cached viewing sufficient?

These questions are recorded as unresolved decisions, not assumptions and not a request to implement them immediately.

## Sequence

1. Containment and reproducible tests.
2. Decide identity/billing/access contracts; inspect deployed schema/data; rehearse restore.
3. Authorized, atomic, retry-safe aggregate saving and current calculation snapshots.
4. Complete synchronization, transactional cache publication, request generations, and shutdown ownership.
5. One semantic UI/design-system vertical slice, then measured expansion.
6. Reproducible builds, packaged functional checks, and controlled release verification.

Detailed gates are in [verification and roadmap](verification-and-roadmap.md#implementation-roadmap). Avoid combining accounting changes, schema migration, and visual redesign into one unreviewable change.

## Maintenance

When a decision is approved, record the chosen contract and its rationale here, link affected findings, and update acceptance tests. Preserve the distinction between a recommendation, an approved design, implemented code, and verified behavior. No architectural option is treated as selected merely because it appears in this document.
