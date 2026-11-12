# Implicit design-system inventory

[Audit index](README.md)  
Last updated: 2026-11-12  
Status: inventory and recommendations; not an implemented replacement design system.

## Assessment

HomeUnitCalculator already contains substantial design-system material. It is distributed across application-wide styling, shared widgets, local theme classes, repeated card implementations, table helpers, per-screen overrides, and dormant infrastructure.

The most consequential gap is not an absent color palette. It is the lack of shared behavioral contracts for validity, selection, saving, loading, missing data, connectivity, recovery, and cancellation.

This inventory distinguishes application-owned components from third-party Qt/Fluent primitives and from nonvisual resource machinery. A helper being defined or imported does not establish production use.

## Foundations and primitives

| ID | Existing material and evidence | Classification and recommendation |
| --- | --- | --- |
| DS-01 Global visual foundation | Dark theme, application fonts, navigation/status styles, tooltips, and message-box behavior. [HomeUnitCalculator.py:139](../../../src/core/HomeUnitCalculator.py#L139), [HomeUnitCalculator.py:784](../../../src/core/HomeUnitCalculator.py#L784). | Global card event replacement was removed and locally verified under RUN-01; color callbacks and separate message/dialog patches remain. Continue separating supported appearance configuration from event/message behavior. |
| DS-02 Calculator tokens | `CalculatorTheme` and helpers for cards, inputs, buttons, headers, captions, dividers, and results. [custom_widgets.py:1697](../../../src/ui/custom_widgets.py#L1697), [custom_widgets.py:1747](../../../src/ui/custom_widgets.py#L1747). | Reusable token/style material, not yet the sole source. Consolidate semantic names rather than only literal values. |
| DS-03 Dashboard tokens | `DashboardTheme` duplicates semantic palette and sizing choices. [dashboard_tab.py:92](../../../src/ui/tabs/dashboard_tab.py#L92). | Calculator/card and dashboard radii differ; input/global radii differ too. Differences are not inherently defects, but should be intentional component variants rather than accidental divergence. |
| DS-04 Surface/card primitive | `StaticCardWidget` appears in Dashboard, History, Rental, Archive, and RentalRecordDialog. [dashboard_tab.py:65](../../../src/ui/tabs/dashboard_tab.py#L65), [history_tab.py:51](../../../src/ui/tabs/history_tab.py#L51), [rental_info_tab.py:105](../../../src/ui/tabs/rental_info_tab.py#L105), [archived_info_tab.py:65](../../../src/ui/tabs/archived_info_tab.py#L65), [rental_record_dialog.py:73](../../../src/ui/rental_record_dialog.py#L73). | Repeated app-owned wrappers around third-party cards. RUN-01 removed global hover-event replacement; local StaticRoomCard and StaticHeaderCardWidget preserve static room/rental appearance. Extract only matching semantics; no shared-card redesign was introduced. |
| DS-05 Input primitive and reading pair | `CustomLineEdit` and `ReadingPairWidget`. [custom_widgets.py:60](../../../src/ui/custom_widgets.py#L60), [main_tab.py:83](../../../src/ui/tabs/main_tab.py#L83). | Standardize units, accessible labels, focus, validation, read-only/disabled behavior, and boundary parsing. The pair is a domain composite, not just two generic text fields. |
| DS-06 Action primitives | `LeftIconButton`, `CustomNavButton`, and `AddPairButton`. [custom_widgets.py:180](../../../src/ui/custom_widgets.py#L180), [custom_widgets.py:467](../../../src/ui/custom_widgets.py#L467), [main_tab.py:273](../../../src/ui/tabs/main_tab.py#L273). | Define primary, secondary, destructive, and icon-only variants with equivalent mouse and keyboard behavior. Back them with shared actions where appropriate. |
| DS-07 Table cell roles | Identifier/numeric/date/special-value item factories and `NumericTableWidgetItem`. [rental_info_tab.py:132](../../../src/ui/tabs/rental_info_tab.py#L132), [archived_info_tab.py:575](../../../src/ui/tabs/archived_info_tab.py#L575). | Cell semantic roles belong in a shared contract. Display text, numeric sorting, stable identity, and accessibility must remain separate. |

## Composites and workflow patterns

| ID | Existing material and evidence | Classification and recommendation |
| --- | --- | --- |
| DS-08 Financial result cards | `ResultCard`, `FinalAmountCard`. [main_tab.py:347](../../../src/ui/tabs/main_tab.py#L347), [main_tab.py:523](../../../src/ui/tabs/main_tab.py#L523). | Share numeric/unit/freshness semantics, not necessarily identical visual hierarchy. A prominent result must never conceal stale or partial calculation state. |
| DS-09 Dashboard metric family | `InfoResultCard`, `SummaryKpiCard`, `KpiChipBar`. [dashboard_tab.py:198](../../../src/ui/tabs/dashboard_tab.py#L198), [custom_widgets.py:1121](../../../src/ui/custom_widgets.py#L1121), [custom_widgets.py:1591](../../../src/ui/custom_widgets.py#L1591). | Unify value, unit, period, comparison, missing-data, and trend-direction contracts before merging implementations. |
| DS-10 Tables | `SmoothTableWidget`, table styling/alignment/width helpers, `EnhancedTableMixin`, and per-tab overrides. [custom_widgets.py:509](../../../src/ui/custom_widgets.py#L509), [custom_widgets.py:653](../../../src/ui/custom_widgets.py#L653), [custom_widgets.py:850](../../../src/ui/custom_widgets.py#L850), [enhanced_table_mixin.py:16](../../../src/ui/components/enhanced_table_mixin.py#L16). | Standardize population/sorting safety, identity, selection restoration, row actions, empty/loading/error states, and width policy. Pilot Model/View on one screen rather than converting all tables speculatively. |
| DS-11 Charts | `SimpleLineChartWidget`, `SimpleBarChartWidget`, QtChart-backed paths, and tooltip styling. [dashboard_tab.py:263](../../../src/ui/tabs/dashboard_tab.py#L263), [custom_widgets.py:1318](../../../src/ui/custom_widgets.py#L1318). | Multiple renderers need common unit/period/missing-data/hover semantics and a tabular equivalent. Correct data meaning before animation or renderer consolidation. |
| DS-12 Dialog foundation | `ResponsiveDialog`, `SaveDialog`, and `ConfirmDialog`. [responsive_components.py:100](../../../src/ui/responsive_components.py#L100), [save_dialog.py:19](../../../src/ui/save_dialog.py#L19), [rental_record_dialog.py:83](../../../src/ui/rental_record_dialog.py#L83). | Define initial focus, focus return, Escape, default/destructive action, sizing, and outcome. Dialog dismissal and operation cancellation are different states. |
| DS-13 Record detail/edit composites | `RentalRecordDialog` and History `EditRecordDialog`. [rental_record_dialog.py:288](../../../src/ui/rental_record_dialog.py#L288), [history_tab.py:99](../../../src/ui/tabs/history_tab.py#L99). | Share behavioral contracts while retaining distinct domain forms. Consider a list/inspector layout before building a universal form framework. |
| DS-14 Document presentation | `ResponsiveImageLabel`, `ResponsiveImagePreviewGrid`, and upload/preview controls. [responsive_image.py:15](../../../src/ui/responsive_image.py#L15), [responsive_image.py:152](../../../src/ui/responsive_image.py#L152), [rental_info_tab.py:2860](../../../src/ui/tabs/rental_info_tab.py#L2860). | Distinguish no document, loading, unavailable, unauthorized, invalid, and displayed. Include explicit replace/remove outcomes and correct logical-pixel scaling. |
| DS-15 Progress and connection cards | `FluentProgressDialog`, `_StatusCard`, `_ProgressCard`. [custom_widgets.py:739](../../../src/ui/custom_widgets.py#L739), [cloud_connect_tab.py:110](../../../src/ui/tabs/cloud_connect_tab.py#L110), [cloud_connect_tab.py:237](../../../src/ui/tabs/cloud_connect_tab.py#L237). | Present actual operation stage, cancellation capability, and completion evidence. Stored credentials, data access, and sync health need separate status vocabulary. |
| DS-16 Notifications and recovery | QMessageBox-to-InfoBar replacement, normal InfoBars, and room-removal undo. [HomeUnitCalculator.py:72](../../../src/core/HomeUnitCalculator.py#L72), [main_tab.py:2128](../../../src/ui/tabs/main_tab.py#L2128). | Transient messages suit transient facts. Failed/partial saves need persistent recoverable receipts, not only a disappearing toast. Preserve the useful undo token guards. |
| DS-17 Disclosure | `CollapsibleSection` and calculator Actions grouping. [custom_widgets.py:1498](../../../src/ui/custom_widgets.py#L1498). | Keyboard-operable headers, visible expanded state, meaningful accessible names, and predictable focus. Do not hide the only route to a critical operation without clear discoverability. |
| DS-18 Empty/loading/motion helpers | `EmptyStateWidget`, `ShimmerPlaceholder`, `AnimatedNumberLabel`. [custom_widgets.py:1199](../../../src/ui/custom_widgets.py#L1199), [custom_widgets.py:1232](../../../src/ui/custom_widgets.py#L1232), [custom_widgets.py:1281](../../../src/ui/custom_widgets.py#L1281). | Defined helpers; some have no demonstrated production construction calls. Do not count them as implemented loading/empty states. Wire intentionally or remove confirmed unused code later. |

## Layout, navigation, and infrastructure

| ID | Existing material and evidence | Classification and recommendation |
| --- | --- | --- |
| DS-19 Layout and scrolling | `FlowLayout`, `AutoScrollArea`, per-screen resize handlers. [flow_layout.py:5](../../../src/ui/flow_layout.py#L5), [custom_widgets.py:281](../../../src/ui/custom_widgets.py#L281). | Shared layout behavior should honor margins, logical pixels, content minima, wheel intent, and narrow-window fallbacks. Desktop responsiveness is not a web breakpoint system. |
| DS-20 Application navigation/actions | Fluent shell and `KeyboardNavigationManager`. [HomeUnitCalculator.py:1295](../../../src/core/HomeUnitCalculator.py#L1295), [keyboard_navigation.py:22](../../../src/ui/keyboard_navigation.py#L22). | Navigation is a third-party foundation with app-specific routing. The shortcut contract is currently broken; centralize actual actions rather than maintaining parallel dispatch logic. |
| DS-21 Responsive registry/testing | `ResponsiveConfig`, `ComponentRegistry`, `LayoutValidator`, and responsive test helpers. [responsive_components.py:15](../../../src/ui/responsive_components.py#L15), [responsive_components.py:26](../../../src/ui/responsive_components.py#L26), [responsive_components.py:146](../../../src/ui/responsive_components.py#L146), [responsive_testing.py:35](../../../src/ui/responsive_testing.py#L35). | Infrastructure, not proof of consistent responsiveness. Correct mutation/coordinate/DPI assumptions before relying on its certification. |
| DS-22 Optimization integration | Batch, cache, width, debounce, and safe-mode managers. [table_optimization.py:1023](../../../src/ui/components/table_optimization.py#L1023). | Nonvisual machinery affecting visual behavior, not design components themselves. Distinguish effective, shadowed, disabled, and dormant paths before extraction. |

## Missing shared behavioral contracts

| Contract | Required distinctions | Current weakness |
| --- | --- | --- |
| Calculation result | Uncalculated, invalid, current, stale, partial | Numeric labels can outlive their inputs. |
| Data availability | Loading, complete, empty, missing, partial, failed | Several paths render zero for multiple different meanings. |
| Freshness | Displayed snapshot age, in-flight refresh, latest successful scoped refresh | Shared timestamps can misdescribe independently selected periods. |
| Connectivity | Unconfigured, authorizing, configured, data-ready, denied, offline, recovered | Stored credentials and runtime access are conflated. |
| Draft | New, clean persisted, dirty, replacing, saving, conflicted | Modal lifetime does not cover persistent form editing. |
| Selection | None, main record, room record, stable selected identity | Enabled actions can use a different target than apparent selection. |
| Save outcome | Not requested, pending, succeeded with receipt, failed with retry | Unrequested destinations are treated as successful. |
| Document | Missing, local, fetching, accessible, unauthorized, invalid, removed/replaced | Paths, slots, and fetch state are distributed across widgets/maps. |
| Cancellation | Available, requested, acknowledged, completed, no longer publishable | Stop requests and short waits are treated too much like completion. |
| Destructive action | Specific target/scope, confirmation, in progress, complete/failed | Cross-source identity and file ownership are not sufficiently explicit. |
| Input accessibility | Focusable, disabled, invalid, described, keyboard-operable | NoFocus/mouse-only paths and shortcut conflicts remain. |

## Recommended extraction order

1. Correct dangerous behavior first: identity, sorting, stale results, global event monkeypatches, and action targets.
2. Define semantic tokens and type/number/unit roles using supported Qt APIs.
3. Establish shared actions and input/validation contracts.
4. Pilot one table or list/inspector slice with complete selection/loading/error behavior.
5. Consolidate result/metric/document/status components only when their semantics match.
6. Remove shadowed or unused helpers after runtime ownership is verified.
7. Expand with native keyboard, high-DPI, multi-monitor, assistive-technology, and empty/error/stale-state tests.

## Proposed visual direction

Use a restrained Fluent foundation, fewer competing accents, strong numerical alignment, tabular numerals for financial comparisons, and semantic state colors. Preserve hierarchy differences between the main total, intermediate values, contextual metrics, and destructive operations.

Motion should communicate a meaningful state change, not imply progress or correctness that has not been established. Chart-to-table access and clear status language matter more than additional animation. See [architecture and UX](architecture-and-ux.md#creative-ui-direction).

## Maintenance

When a component is consolidated, record which old definitions were removed and which behavior tests establish equivalence. Do not mark a contract implemented merely because a class or style helper now exists. Keep third-party primitives, application composites, infrastructure, and dormant code distinct.
