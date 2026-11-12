# Card Hover Recursion Implementation Plan

**Goal:** Resolve audit RUN-01 without changing the existing dark color palette or adding another event wrapper.

**Architecture:** Keep the current color helper overrides, but leave Fluent's native enter/leave handlers untouched. Regression tests use real Qt/Fluent cards and restore all class attributes modified by the palette function so tests do not contaminate one another.

**Tech Stack:** Python 3.12, PyQt5, PyQt-Fluent-Widgets, pytest.

**Authorization:** The user requested handling the audit findings one by one and maintaining the Markdown documentation. No commits, deployment, live cloud operations, or billing-policy changes are included.

---

## Files

- Modify [HomeUnitCalculator.py](../../../src/core/HomeUnitCalculator.py), `_patch_cardwidget_dark_style`, initially at lines 995-1165.
- Extend [test_startup_smoke.py](../../../tests/test_startup_smoke.py) with isolated real-card regressions.
- Update [RUN-01](../../audits/2026-11-12/ui-and-runtime.md#run-01), the audit index, state/design inventories, and verification record after actual verification.
- Test tracking is a separate open finding, REL-08: the existing tests directory is ignored. Do not pretend these test edits are versioned until that finding is addressed.

## Task 1: Reproduce and guard the defect

- [x] Add `pytest` and `QEvent` imports to the existing startup test module.
- [x] Add the following fixture and tests. The fixture snapshots owned class attributes, including inherited-vs-owned distinctions, and restores them in `finally`.

```python
@pytest.fixture
def dark_style_cards(qapp):
    from qfluentwidgets import CardWidget, SimpleCardWidget, ElevatedCardWidget
    from src.core.HomeUnitCalculator import MeterCalculationApp

    card_types = (CardWidget, SimpleCardWidget, ElevatedCardWidget)
    attributes = (
        "_normalBackgroundColor", "_hoverBackgroundColor", "_pressedBackgroundColor",
        "enterEvent", "leaveEvent", "_original_enterEvent", "_original_leaveEvent",
        "__hmc_dark_patched__",
    )
    missing = object()
    original = {
        cls: {name: cls.__dict__.get(name, missing) for name in attributes}
        for cls in card_types
    }
    handlers = {cls: (cls.enterEvent, cls.leaveEvent) for cls in card_types}
    try:
        for cls in card_types:
            if "__hmc_dark_patched__" in cls.__dict__:
                delattr(cls, "__hmc_dark_patched__")
        MeterCalculationApp._patch_cardwidget_dark_style(None)
        MeterCalculationApp._patch_cardwidget_dark_style(None)
        yield card_types, handlers
    finally:
        for cls, values in original.items():
            for name, value in values.items():
                if value is missing:
                    if name in cls.__dict__:
                        delattr(cls, name)
                else:
                    setattr(cls, name, value)


@pytest.mark.parametrize("card_index", range(3))
def test_card_dark_style_preserves_native_hover(dark_style_cards, card_index):
    card_types, handlers = dark_style_cards
    cls = card_types[card_index]
    card = cls()
    try:
        for _ in range(3):
            card.enterEvent(QEvent(QEvent.Enter))
            assert card.isHover is True
            card.leaveEvent(QEvent(QEvent.Leave))
            assert card.isHover is False
        assert (cls.enterEvent, cls.leaveEvent) == handlers[cls]
        assert not hasattr(card, "_hover_animation")
    finally:
        card.deleteLater()


def test_card_dark_style_keeps_existing_palette(dark_style_cards):
    card_types, _ = dark_style_cards
    cases = (
        ("", (43, 43, 43, 255), (54, 54, 54, 255), (37, 37, 37, 255)),
        ("billing_meter_container", (43, 43, 43, 255), (43, 43, 43, 255), (37, 37, 37, 255)),
        ("billing_period_box", (255, 255, 255, 72), (255, 255, 255, 72), (255, 255, 255, 72)),
        ("reading_pairs_box", (255, 255, 255, 72), (255, 255, 255, 72), (255, 255, 255, 72)),
        ("additional_amount_box", (255, 255, 255, 72), (255, 255, 255, 72), (255, 255, 255, 72)),
    )
    for cls in card_types:
        card = cls()
        try:
            for name, normal, hover, pressed in cases:
                card.setObjectName(name)
                assert card._normalBackgroundColor().getRgb() == normal
                assert card._hoverBackgroundColor().getRgb() == hover
                assert card._pressedBackgroundColor().getRgb() == pressed
        finally:
            card.deleteLater()
```

- [x] Run `python -B -m pytest tests/test_startup_smoke.py -k card_dark_style -q -p no:cacheprovider --tb=short` with the established temporary-directory/keyring/network audit harness. Expected before the fix: native-handler assertion failure for CardWidget and recursion for the inherited card paths; the palette test passes.

## Task 2: Remove the unsafe wrappers

- [x] Remove the local `QPropertyAnimation`, `QEasingCurve`, and `pyqtProperty` import, which becomes unused.
- [x] Delete the `_enhanced_enter_event` and `_enhanced_leave_event` nested functions.
- [x] Remove `_original_enterEvent`/`_original_leaveEvent` capture and `enterEvent`/`leaveEvent` assignment from the class loop. The complete resulting loop is:

```python
            for _cls in (CardWidget, SimpleCardWidget, ElevatedCardWidget):
                _cls._normalBackgroundColor = _normal
                _cls._hoverBackgroundColor = _hover
                _cls._pressedBackgroundColor = _pressed
                _cls.__hmc_dark_patched__ = True
```

- [x] Keep `_normal`, `_hover`, `_pressed`, the double-patch guard, and existing error handling unchanged. Update the existing method documentation to stop promising added hover animations.
- [x] Rerun the targeted tests; expected four passing cases.

## Task 3: Verify integration and update the audit

- [x] Run the complete isolated test suite and record the exact outcome; do not bypass existing failures without diagnosis.
- [x] Launch the actual native application in a temporary local-only profile, mount all seven tabs, and exercise repeated enter/leave on CardWidget, SimpleCardWidget, and ElevatedCardWidget. Capture exceptions, palette values, screenshot, and exit status.
- [x] Inspect the resulting screenshot and ensure tab mounting and the existing palette remain intact. This native application has no web development server; test it through Qt rather than claiming a browser test.
- [x] Review the actual diff; no unrelated source changes, new event wrappers, or third-party package edits should be present.
- [x] Record RUN-01 as locally verified only after those checks pass. Retain the separate color-helper coupling concern and the open test-tracking issue.
- [x] Update affected audit line references and record the next sequential finding. Do not claim that all findings are fixed or that a cloud test ran.

## Review refinement: preserve static containers

Independent review found that the removed wrappers also suppressed room and Rental-tab hover effects. Preserve that established appearance locally rather than restoring any global handler replacement:

- [x] Add `StaticRoomCard(CardWidget)` in [main_tab.py](../../../src/ui/tabs/main_tab.py) and use it for room cards.
- [x] Add `StaticHeaderCardWidget(HeaderCardWidget)` in [rental_info_tab.py](../../../src/ui/tabs/rental_info_tab.py) and use it for the three rental header cards. Keep the existing rental static table card unchanged.

Each new subclass implements only:

```python
    def enterEvent(self, event):
        return

    def leaveEvent(self, event):
        return
```

- [x] Extend the startup regression with parameterized cases for both new classes and the existing rental static class; assert repeated enter/leave keeps `isHover` false and the background unchanged, and child button clicks still emit.
- [x] Verify actual room-card and rental-header construction in the native application, not only detached subclass instances. Type into a room input and remove/undo a room to check child interaction.

## Execution status

Plan recorded before implementation. The original regression produced three failures and one pass before the wrapper removal, then four passes afterward. Added static-container regressions initially failed for the two not-yet-created subclasses while the existing static class passed. Native integration now passes with all seven tabs mounted, 11 room cards and four rental cards checked, native handlers retained for all three Fluent card types, child input/remove/undo exercised, zero captured exceptions, and exit 0. Screenshots were inspected. Final isolated suite: 164 passed, one third-party warning. Audit statuses and 64 shifted source citations were updated. The native harness first rejected a legitimate temporary key-file write because short and long Windows paths were compared inconsistently; resolving the sandbox path fixed the harness without weakening its write restriction or changing key management.

No commit will be created unless the user requests it.
