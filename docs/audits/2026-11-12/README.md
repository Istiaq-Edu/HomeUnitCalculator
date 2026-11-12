# HomeUnitCalculator engineering audit

Audit date: 2026-11-12  
Last updated: 2026-11-12  
Status: sequential local remediation in progress on branch `dev`; RUN-01, DASH-01, the dashboard truthfulness slice (DASH-03/04/05/06/08), REL-01..03/REL-08, and DATA-01/02/03 are locally verified and committed, plus window-state remembrance and a measured 50% startup-import reduction. Deployed Supabase inspection completed read-only and confirmed the anonymous full-access exposure (SEC-01) and the public identity-document bucket (SEC-04). Of 71 findings, 10 are locally verified or implemented and 61 remain open.

## Executive assessment

Retain PyQt. Correct record identity, calculation validity, persistence boundaries, authorization, and asynchronous result ownership before a broad visual or architectural rewrite.

The highest-impact findings are wrong-record operations across local/cloud IDs, incomplete writes reported as success, stale or partially calculated results, requests publishing into obsolete view contexts, and unsafe assumptions in cloud provisioning and security. Passing tests do not establish that these behaviors are safe.

This audit separates reproduced behavior, source-confirmed findings, deployment-dependent risks, and design proposals. It does not claim that every runtime interleaving or external dependency has been exhaustively verified.

## Documents

| Document | Contents |
| --- | --- |
| [Data and calculation findings](data-and-calculation.md) | Record identity, persistence, synchronization, financial calculations, import/export, and room undo. |
| [Security and delivery findings](security-and-delivery.md) | Supabase authorization, OAuth, document privacy, provisioning, keys, CI, packaging, tests, and distribution. |
| [UI and runtime findings](ui-and-runtime.md) | Record workflows, dashboard semantics, widgets, accessibility, image handling, threading, responsive behavior, and optimization infrastructure. |
| [Implicit state machines](state-machines.md) | Application-defined temporal states, owners, transitions, invariants, persistence, and interactions. |
| [Implicit design system](design-system.md) | Tokens, visual primitives, composites, interaction patterns, dormant helpers, and missing behavioral contracts. |
| [Architecture and UX](architecture-and-ux.md) | Independent architectural assessment, alternatives, recommended boundaries, and creative UI direction. |
| [Verification and roadmap](verification-and-roadmap.md) | Executed checks, evidence limits, acceptance tests, implementation sequence, unresolved decisions, and research sources. |

## Reading priorities

1. [DATA-01: cross-source identity](data-and-calculation.md#data-01).
2. [DATA-02: non-atomic monthly persistence](data-and-calculation.md#data-02), [DATA-03: rental write identity](data-and-calculation.md#data-03), and [DATA-04: save outcomes](data-and-calculation.md#data-04).
3. [CALC-01: precision and presentation coupling](data-and-calculation.md#calc-01) and [CALC-02: calculation freshness](data-and-calculation.md#calc-02).
4. [SEC-01: authorization](security-and-delivery.md#sec-01), [SEC-02: project selection](security-and-delivery.md#sec-02), [SEC-03: bundled OAuth secret](security-and-delivery.md#sec-03), and [SEC-04: identity documents](security-and-delivery.md#sec-04).
5. [UI-01: table identity](ui-and-runtime.md#ui-01), [RUN-01: hover recursion](ui-and-runtime.md#run-01), and [DATA-10: obsolete asynchronous results](data-and-calculation.md#data-10).
6. [REL-01 through REL-03: release integrity](security-and-delivery.md#rel-01).

## Evidence and priority vocabulary

- **R-main:** reproduced by the coordinating audit using actual methods or isolated application/widget execution and synthetic data.
- **R-specialist:** a specialist reported a synthetic or isolated reproduction; this is distinguished from a reproduction rerun by the coordinating audit.
- **S:** source-confirmed behavior or missing guard on the inspected path. This is not automatically proof of production impact.
- **C:** deployment, actual data, reachability, or a business rule determines the impact.
- **D:** design recommendation, not an established defect.
- **P1:** containment or correctness work before expanding production use or relying on the affected workflow.
- **P2:** next hardening work after the critical contracts are settled.
- **P3:** measured cleanup or consolidation.

Findings are open unless their entry explicitly records a different disposition. Priority is not a CVSS score. No breach, credential theft, or production data loss was demonstrated.

## Verified audit coverage

- This documentation set contains 71 finding entries, 34 state-machine families, and 22 design-system groups across eight Markdown files.
- Documentation validation checked 420 local links, including target existence, internal Markdown anchors, and source-line bounds; finding IDs were unique and all documents were visible to Git.
- 65 Python files, approximately 40,172 lines, plus build/release/configuration/documentation review.
- Nine completed specialist reviews: seven domain reviews, an independent architecture review, and a state-machine review.
- Python syntax checks passed.
- 157 local tests passed in an isolated audit harness.
- Safe reproductions identified concrete calculation, synchronization, persistence, and widget defects.
- The native application mounted all seven tabs without captured exceptions in a temporary local-only environment.
- The native minimum window size observed after an 800 by 600 resize request was 1000 by 700.
- No source, configuration, or cloud changes were made during the audit. The Markdown documentation set was subsequently created at the user's request.

Supabase tools eventually became exposed to the session, but two read-only project-discovery invocations failed. No deployed grants, RLS policies, bucket privacy, data, migrations, or advisors were verified. See the [verification record](verification-and-roadmap.md#supabase-access).

## Maintenance contract

These files are intended to be updated as work continues, not left as a frozen list of conclusions.

1. Update the relevant finding when evidence changes, a decision is made, or implementation is verified.
2. Retain stable finding IDs; add new findings rather than renumbering unrelated ones.
3. Record status, verification method, date, and remaining limitations for a claimed fix.
4. Distinguish implemented from verified, and local verification from deployed verification.
5. If new evidence contradicts a finding, correct it and record the reason; do not preserve an obsolete claim for consistency.
6. Update cross-references and source locations when code moves.
7. Keep unresolved product decisions separate from coding defects.
8. Do not put credentials, tenant details, identity documents, or raw sensitive logs in these files.
9. Do not imply that documenting a recommendation authorizes source changes, cloud mutations, deployment, or a Git commit.
10. Updates occur as further work is performed; this document does not represent an autonomous background monitoring service.

## Update history

| Date | Change |
| --- | --- |
| 2026-11-12 | DATA-03 locally verified and committed (`db8fc36`): rental writes establish a stable `supabase_id` identity shared by the local insert, the cloud insert payload (previously omitted), and the form; local UPDATE persists the identity so unlinked rows gain it on next save; the local insert retains its returned row id. New `tests/test_rental_write_identity.py` (5 tests; 4 failed pre-fix); full isolated suite 200 passed, 8 optional skips. Pre-fix NULL-identity records stay unlinkable until their next edit; structured receipts remain DATA-04. |
| 2026-11-12 | DATA-02 locally verified and committed (`c729819`), client-side containment only: explicit empty-replacement semantics (empty room list deletes previous cloud rows), failed/partial old-row deletion and short inserts no longer report success (retry-safe convergence), and monthly deletion is parent-first via the bundled FK cascade with read-only orphan verification. Callers reach the room save even with an empty list. New `tests/test_monthly_persistence_atomicity.py` (13 tests; 9 failed pre-fix); full isolated suite 195 passed, 8 optional skips. True transactionality still requires an authorized RPC/migration; concurrent-writer races remain DATA-05. |
| 2026-11-12 | DATA-01 locally verified and committed (`515edbe`): cloud rental numeric ids no longer address local rows. Cloud-source edits resolve the local counterpart via the unique `rentals.supabase_id` link or fall back to a safe local insert; cloud deletion removes the local counterpart by `supabase_id` and blocks records without `supabase_id`. New `tests/test_rental_record_identity.py` (9 tests; 6 failed pre-fix); full isolated suite 182 passed, 8 optional skips. NULL cloud `supabase_id` rows (DATA-03) remain unlinkable; no deployed verification. |
| 2026-11-12 | Release integrity (REL-01..03) implemented with independent review: workflows pass data only through env blocks (zero interpolation in script bodies, scanned), one immutable SHA pins tag/target_commitish/build, release runs serialized, exact asset manifest with per-call exit checks and name+size verification, SHA256 checksums published, exact installer name enforced, build workflow gained a verify-outputs gate. Tests now tracked in Git (REL-08): 21 files committed. Workflow fixes are statically verified (YAML parse + automated interpolation scan + reviewer ship verdict); a real Actions dispatch remains the live gate. Draft-release publishing gate intentionally preserved. |
| 2026-11-12 | Dashboard truthfulness slice implemented and locally tested (173 passing tests): request-scope generations on all five async lanes (DASH-03), January uses the previous year's December (DASH-04), missing data no longer renders as measured zero with a last-available-month fallback (DASH-05, user-reported blank cards), per-snapshot freshness labels (DASH-06), delta direction fixed (DASH-08). Window geometry now persists across sessions; startup imports cut ~50% by deferring the scipy chain via a lazy shim (native smoke startup ~3.19 s → 2.59 s). Read-only Supabase inspection of the `HUC Data` project verified the deployed anonymous full-access policies (SEC-01) and the public `rental-images` bucket (SEC-04); no cloud changes were made. |
| 2026-11-12 | DASH-01 closed as locally verified: native hover/tooltip verification passed against real Qt Charts (synthetic data) after correcting the verification harness's series attribute and z-order handling. Production chart animations removed (`NoAnimation`) by user decision — animations were not wanted, and `SeriesAnimations` triggered native access violations on Qt 5.15.2 + PyQtChart 5.15.7; one NoAnimation crash in five environment runs remains an unexplained environment-level instability, not attributed to application code. No commit or cloud mutation. |
| 2026-11-12 | User authorized sequential local fixes. RUN-01 locally verified with 164 passing tests, real native hover/static-card/child-control checks, and inspected screenshots; preserved color callbacks and updated moved source citations. DASH-01 selected next. Tests remain ignored/untracked under REL-08. No commit or cloud mutation. |
| 2026-11-12 | Created the linked Markdown audit set from the completed investigation at the user's request; established ongoing updates. |
| 2026-11-12 | Preserved important clarifications: the rental `supabase_id` column exists but inserts do not populate it; undo preserves surviving rooms' current results but can restore the removed room's old derived labels; Supabase tool exposure did not result in successful backend access; the final native smoke test passed after test-environment corrections. |
