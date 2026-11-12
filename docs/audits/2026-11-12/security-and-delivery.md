# Security and delivery findings

[Audit index](README.md)  
Last updated: 2026-11-12  
Disposition: all findings below are open; no permissions, credentials, workflows, or cloud resources were changed by the audit.

The security assessment is authorized defensive review. No exploitation of a live service, secret extraction, tenant-data inspection, or destructive test was performed. A read-only deployed inspection of the user's `HUC Data` project succeeded on 2026-11-12; see [the access record](verification-and-roadmap.md#supabase-access).

## Security and connection lifecycle

### SEC-01

**Bundled anonymous-role policies are not record ownership authorization.**  
Priority: P1. Evidence: S/C.

The three business tables enable RLS but permit all operations when `auth.role()` is `anon`, without an owner or membership predicate. Actual reachability also depends on grants and API exposure. The schema-version table is not RLS-protected or placed in an unexposed schema. Management OAuth authorizes management operations; it does not establish an end-user Supabase Auth identity for row authorization.

Evidence: [supabase_schema.py:43](../../../src/core/supabase_schema.py#L43), [supabase_schema.py:66](../../../src/core/supabase_schema.py#L66), [supabase_schema.py:93](../../../src/core/supabase_schema.py#L93).

Recommendation: decide ownership and align grants, authentication, and row authorization. Changing key format or replacing `auth.role()` with a role clause alone does not solve authorization. Include ownership-preserving checks on updates. No breach was demonstrated.

**Status: deployed exposure verified read-only, 2026-11-12.** Project `ldbzwpovomglwqkdwxeo` ("HUC Data") carries exactly the audited design: `main_calculations`, `room_calculations`, and `rental_records` each have two PERMISSIVE `ALL` policies — one for role `public` conditioned on `auth.role() = 'anon'`, one for role `anon` with `true`/`true` predicates — so anyone holding the public anon key has unconditional full read-write. `public._huc_schema_version` has RLS disabled entirely (Supabase security advisor: ERROR; SELECT granted to `anon` and `authenticated`), and all four tables are visible to anon in the GraphQL schema. The advisor also reports Postgres 15.8.1.114 has outstanding security patches. Observed row counts: main_calculations 1, room_calculations 11, rental_records 0. No policy, grant, or data change was made. Remediation requires the coordinated app-auth decision recorded in [unresolved decisions](architecture-and-ux.md#decisions-required-before-implementation); restricting policies to `authenticated` without the app adopting Supabase Auth would break the app's current access path.

### SEC-02

**Provisioning can select and mutate an unrelated project.**  
Priority: P1. Evidence: S.

Project discovery and fallback can choose the first active/existing project or first organization. A schema-check exception becomes version zero, which can trigger schema application. Creation failures containing broad strings such as `400` or `limit` can enter project-reuse behavior. This is inconsistent with an unqualified promise of an isolated project.

Evidence: [supabase_provisioner.py:77](../../../src/core/supabase_provisioner.py#L77), [supabase_provisioner.py:101](../../../src/core/supabase_provisioner.py#L101), [supabase_provisioner.py:192](../../../src/core/supabase_provisioner.py#L192), [cloud_connect_tab.py:355](../../../src/ui/tabs/cloud_connect_tab.py#L355).

Recommendation: explicit confirmed organization/project reference, compatible-schema inspection, and a fail-closed distinction between absent schema and failed inspection. Unknown state is not authorization to mutate a fallback target.

### SEC-03

**A confidential OAuth client secret is configured for desktop distribution.**  
Priority: P1. Evidence: S/C.

Build workflows create an OAuth credentials module from secrets; the application imports the client secret and packaging includes the module. A distributed desktop executable cannot guarantee confidentiality of an embedded shared secret. This finding does not establish that a particular published artifact contains a usable secret, nor that any token has been stolen. PKCE remains valuable but does not make embedded secrets confidential.

Evidence: [supabase_oauth.py:27](../../../src/core/supabase_oauth.py#L27), [supabase_oauth.py:111](../../../src/core/supabase_oauth.py#L111), [release.yml:131](../../../.github/workflows/release.yml#L131), [HomeUnitCalculator.spec](../../../HomeUnitCalculator.spec).

Recommendation: use a documented provider-supported public/native flow if available. The reviewed Management OAuth documentation requires confidential client authentication; do not invent a secretless replacement. Alternatives include a controlled backend exchange or an explicit scoped administrative setup flow.

### SEC-04

**Identity-document access assumes public Storage URLs.**  
Priority: P1. Evidence: S/C.

The upload path produces public URLs for photos, identity-card images, and police forms. Actual public accessibility depends on bucket privacy and policies; private or missing buckets instead create functional failures. Basename-based upsert keys can collide. The inspected provisioning/schema does not establish the required Storage bucket/policy contract.

Evidence: [supabase_manager.py:157](../../../src/core/supabase_manager.py#L157), [supabase_manager.py:211](../../../src/core/supabase_manager.py#L211), [supabase_manager.py:789](../../../src/core/supabase_manager.py#L789).

Recommendation: private buckets, opaque record-scoped object keys, authorized or short-lived signed access, and explicit document retention/removal. Storage replacement permissions and metadata authorization must be tested together.

**Status: deployed bucket verified read-only, 2026-11-12.** The project's only Storage bucket, `rental-images` (created 2025-06-23), is `public: true` with no file-size limit and no MIME restrictions. With zero deployed `rental_records` rows today, no actual tenant document is known to be exposed, but any future identity document uploaded through the app is publicly fetchable by URL. No bucket change was made.

### SEC-05

**OAuth callback validation and deadlines need stronger boundaries.**  
Priority: P2. Evidence: S/C.

Query-bearing requests on unexpected paths can reach callback handling. The received latch can become terminal before full validation of state and required parameters; a matching state without a code can consume the attempt. This supports interruption/availability concerns, not a demonstrated account takeover. Server-level timeout is not necessarily a per-client header-read deadline.

Evidence: [oauth_callback_server.py:18](../../../src/ui/oauth_callback_server.py#L18), [oauth_callback_server.py:40](../../../src/ui/oauth_callback_server.py#L40), [oauth_callback_server.py:98](../../../src/ui/oauth_callback_server.py#L98).

Recommendation: exact path, bounded parameters, state, and code/error validation before accepting the terminal callback; bounded connection and overall attempt deadlines. Preserve loopback binding and escaped browser errors.

### SEC-06

**Key fallback and recovery can sacrifice confidentiality or recoverability.**  
Priority: P1 for recoverability; P2 for hardening. Evidence: S/C.

ACL-setting failures are ignored in relevant paths. Corrupt keys can be deleted/regenerated rather than preserved for recovery. The key-manager `__main__` self-test uses normal keyring/file locations and prints key material. Encryption cannot protect data from a fully compromised logged-in account.

Evidence: [key_manager.py:40](../../../src/core/key_manager.py#L40), [key_manager.py:63](../../../src/core/key_manager.py#L63), [key_manager.py:124](../../../src/core/key_manager.py#L124), [key_manager.py:150](../../../src/core/key_manager.py#L150).

Recommendation: verified backend/ACL behavior, restricted atomic file creation, non-destructive recovery, and isolated self-tests. Never regenerate a key as a silent repair when existing encrypted data may depend on it.

### SEC-07

**Stored credentials are mistaken for operational connection readiness.**  
Priority: P2. Evidence: S.

Status can be based on stored tokens and project reference rather than working data access or expiry. Refresh support is not integrated into an observed renewal lifecycle. Credential persistence errors can be logged without failing the overall success state. Disconnect clears local state but does not mean consent or existing remote credentials were revoked.

Evidence: [cloud_connect_tab.py:442](../../../src/ui/tabs/cloud_connect_tab.py#L442), [cloud_connect_tab.py:534](../../../src/ui/tabs/cloud_connect_tab.py#L534), [cloud_connect_tab.py:656](../../../src/ui/tabs/cloud_connect_tab.py#L656), [cloud_connect_tab.py:707](../../../src/ui/tabs/cloud_connect_tab.py#L707).

Recommendation: separate administrative consent, selected project, data-client readiness, and sync health. Commit identity coherently, invalidate old attempts on disconnect, minimize retained privilege, and describe local disconnect accurately.

### SEC-08

**Legacy manual configuration has weak endpoint/key boundaries.**  
Priority: P2. Evidence: S/C.

The legacy configuration UI permits HTTP/arbitrary hosts and service-role-looking JWT input while rejecting modern publishable-key formats. It is not the current navigation destination, so practical reachability must not be overstated.

Evidence: [supabase_config_tab.py:123](../../../src/ui/tabs/supabase_config_tab.py#L123).

Recommendation: HTTPS by default, explicit self-hosted support if required, current key-format support, and rejection of privileged client credentials. Do not silently remove valid self-hosted requirements without a product decision.

### SEC-09

**API exposure and key retrieval assume older platform defaults.**  
Priority: P2. Evidence: S/C.

The schema lacks explicit table grants, while current Supabase behavior can require opt-in table exposure. Existing projects can retain older grants, so missing grants on new projects do not cancel the permissive-policy concern on existing ones. Key retrieval assumes legacy anonymous keys.

Evidence: [supabase_schema.py:26](../../../src/core/supabase_schema.py#L26), [supabase_management.py:136](../../../src/core/supabase_management.py#L136).

Recommendation: verify actual grants/exposure and supported key types against current documentation, then encode the intended access contract explicitly. Read-only live verification remains outstanding.

### SEC-10

**Error reporting can leak details or imply an unsupported diagnosis.**  
Priority: P2. Evidence: S/C.

Raw OAuth responses and exceptions can reach logs/UI. Network/DNS failures can be classified as a paused project. Document URLs and operational details may be sensitive even when they are not passwords.

Evidence: [supabase_oauth.py:119](../../../src/core/supabase_oauth.py#L119), [cloud_connect_tab.py:554](../../../src/ui/tabs/cloud_connect_tab.py#L554), [supabase_error_handler.py:38](../../../src/core/supabase_error_handler.py#L38), [supabase_error_handler.py:261](../../../src/core/supabase_error_handler.py#L261).

Recommendation: sanitized categories, stable codes, request IDs, and explicit uncertainty. Never prescribe a destructive or privilege-changing recovery based solely on a guessed error category.

### SEC-11

**A schema version marker does not establish an actual upgrade.**  
Priority: P1/P2. Evidence: S/C.

The bundled migration creates tables with `IF NOT EXISTS` and records version 2, but does not alter existing table shapes to add missing columns. On a preexisting schema, the marker can advance without establishing compatibility. Applying this SQL is not a substitute for inspection and versioned upgrades.

Evidence: [supabase_schema.py:16](../../../src/core/supabase_schema.py#L16), [supabase_schema.py:34](../../../src/core/supabase_schema.py#L34), [supabase_schema.py:99](../../../src/core/supabase_schema.py#L99).

Recommendation: explicit migration preconditions and postconditions, actual schema comparison, backups, and a restoration rehearsal before changing existing deployments.

## Build, release, packaging, and tests

### REL-01

**Workflow data is interpolated into executable shell and JavaScript.**  
Priority: P1. Evidence: S/C.

Version input, generated changelog text, and credential values enter executable script source through workflow expressions. Ordinary backticks/quoting can break generated JavaScript; malicious control requires access to the relevant input, dispatch, secret, or commit surface. This is not an established unauthenticated pull-request exploit.

Evidence: [release.yml:33](../../../.github/workflows/release.yml#L33), [release.yml:45](../../../.github/workflows/release.yml#L45), [release.yml:62](../../../.github/workflows/release.yml#L62), [release.yml:131](../../../.github/workflows/release.yml#L131), [release.yml:263](../../../.github/workflows/release.yml#L263).

Recommendation: once-validated versions, environment variables, and proper serialization rather than executable-source interpolation. Preserve normal hooks and signing controls.

### REL-02

**Tag, binary, and changelog can describe different commits.**  
Priority: P1. Evidence: S.

The workflow force-creates a local tag without pushing it, creates a release without an explicit `target_commitish`, builds from the dispatched/ref context, and later regenerates the changelog after tagging default-branch HEAD. Concurrent runs and ref movement are not resolved by this sequence.

Evidence: [release.yml:45](../../../.github/workflows/release.yml#L45), [release.yml:84](../../../.github/workflows/release.yml#L84), [release.yml:240](../../../.github/workflows/release.yml#L240).

Recommendation: resolve one immutable commit SHA, validate the intended tag, serialize conflicting release runs, and assert that binaries/changelog/release metadata refer to that SHA. No tags were changed by this audit.

### REL-03

**Asset replacement is broader than its comment, and failures can be masked.**  
Priority: P1. Evidence: S.

The rerun loop deletes every existing release asset, not only expected name collisions. Upload commands do not immediately check each native exit code, so an earlier failure may be obscured by a later success. Installer selection takes the first executable rather than one exact expected filename. A separate artifact upload lacks a missing-files failure gate.

Evidence: [release.yml:201](../../../.github/workflows/release.yml#L201), [release.yml:216](../../../.github/workflows/release.yml#L216), [release.yml:221](../../../.github/workflows/release.yml#L221), [build-pyinstaller.yml](../../../.github/workflows/build-pyinstaller.yml).

Recommendation: exact expected asset manifest, narrow replacement, immediate exit checks, and final verification of names, sizes, and checksums. Do not remove unrelated release assets during reruns.

### REL-04

**Build inputs are not sufficiently reproducible or current.**  
Priority: P2. Evidence: S.

Runtime/build dependencies and actions are not consistently locked. Pillow is directly imported but relies on transitive installation; pytest is undeclared. Workflows use Python 3.10, whose upstream end of life was 2026-10-01. Mutable runners/actions and unconstrained tools make reproduction harder.

Evidence: [requirements.txt](../../../requirements.txt), [release.yml](../../../.github/workflows/release.yml), [build-pyinstaller.yml](../../../.github/workflows/build-pyinstaller.yml).

Recommendation: a tested supported Python baseline, explicit direct dependencies, locked build/runtime inputs, and controlled update review. No project-specific CVE claim is made because a vulnerability audit was not completed.

### REL-05

**Process survival is not a packaged feature smoke test.**  
Priority: P2. Evidence: S.

A short survival check can pass with deferred-tab failures, a hung UI, or exceptions that are logged rather than reflected in the process exit code. Source-mode native mounting performed in this audit does not verify the packaged executable.

Evidence: [build-pyinstaller.yml](../../../.github/workflows/build-pyinstaller.yml), [measure_packaged_startup.ps1](../../../tools/measure_packaged_startup.ps1).

Recommendation: an isolated packaged functional self-test covering tab construction, one calculation, a temporary save/export, error capture, and clean shutdown, with a decisive exit status.

### REL-06

**Installer identity and upgrade handling need platform-specific verification.**  
Priority: P2. Evidence: S/C.

The AppId's doubled-brace representation is used both in Inno Setup escaping and literal registry/Pascal contexts, producing an upgrade-lookup mismatch. Uninstall return handling is incomplete. 64-bit install mode is not equivalent to an explicit allowed-architecture contract.

Evidence: [HomeUnitCalculator.iss](../../../installer/HomeUnitCalculator.iss).

Recommendation: verify real install/upgrade/uninstall behavior on a clean Windows environment and preserve already-shipped identity compatibility. Prefer normal stable Inno upgrade mechanisms over custom removal logic where possible.

### REL-07

**Documentation and version metadata disagree with the current application.**  
Priority: P3. Evidence: S.

Launch/configuration/module documentation is stale in places. Version fallbacks differ across spec, installer, About, and changelog. No root license/copying document was found in the reviewed repository; PyQt/Fluent distribution obligations require review, but this absence alone does not establish a violation.

Evidence: [project README](../../../README.md), [HomeUnitCalculator.spec](../../../HomeUnitCalculator.spec), [HomeUnitCalculator.iss](../../../installer/HomeUnitCalculator.iss), [about_tab.py](../../../src/ui/tabs/about_tab.py).

Recommendation: one version source, current setup instructions, and a distribution/license checklist tied to actual dependencies and distribution terms.

### REL-08

**The successful local tests are not tracked as a repository safety net.**  
Priority: P2. Evidence: S and Git verification.

`tests/` is ignored, and `git ls-files -- tests` returned no tracked files. The local suite passed during the audit, but a clean checkout does not acquire those tests through Git. Many tests assert source strings, use mocks, or invoke worker `run()` directly; those do not validate real asynchronous ordering or deployed authorization.

Evidence: [.gitignore:11](../../../.gitignore#L11), [local tests directory](../../../tests).

Recommendation: explicitly version the intended test suite and declare test dependencies. Retain focused tests, but add behavior-level integration tests and separate live/environment-dependent verification.

### REL-09

**Tests can touch normal user resources or depend on execution order.**  
Priority: P2. Evidence: S; isolated harness results are recorded separately.

Some tests instantiate the default database location; temporary database use does not itself isolate keyring. Callback tests use fixed loopback ports and incomplete timeout/cleanup controls. QApplication setup has order-dependent cases. One audit test rejects exact dependency pins, conflicting with reproducibility goals.

Evidence: [tests/conftest.py](../../../tests/conftest.py), [local test suite](../../../tests).

Recommendation: default fixtures for temporary app directories, process-local keyring isolation, network policy, Qt application lifecycle, bounded callback servers, and deterministic cleanup. Correct tests that codify obsolete policy rather than behavior.

## Existing strengths to retain

- S256 PKCE and random OAuth state.
- Loopback callback binding, state rejection before token exchange, browser error escaping, and callback URL log suppression.
- Fernet-based encryption and encrypted stored credentials.
- Automatic anonymous-key selection rather than automatic service-role selection.
- Existing default-No overwrite confirmations.

These are useful controls, not proof that all surrounding lifecycle and authorization boundaries are sound.

## Verification boundary

The audit did not alter RLS, grants, bucket policies, OAuth settings, credentials, release assets, tags, workflows, or installer behavior. Backend security findings remain source-confirmed and deployment-conditional until read-only live inspection and authorized negative-access tests are possible. See [research sources and next gates](verification-and-roadmap.md#research-sources).
