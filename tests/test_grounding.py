"""Unit tests for the action grounding choke point and input value sanitizer."""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind, Locator
from proofqa.explore.grounding import TELEMETRY, ground_action, sanitize_input_value


def test_sanitize_input_value():
    # Length cap
    huge = "a" * 15000
    res = sanitize_input_value(huge)
    assert len(res) == 10000

    # Control characters stripped, newlines preserved
    ctrl = "Hello\x00\x07World\nValid\tLine\x1fEnd"
    cleaned = sanitize_input_value(ctrl)
    assert cleaned == "HelloWorld\nValid\tLineEnd"


def test_ground_action_matches_existing_control():
    grounded = [
        Action(id="c1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart", testid="btn-add")),
        Action(id="c2", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", testid="qty-input")),
    ]

    # Valid click matching testid
    act1 = Action(id="a1", kind=ActionKind.CLICK, locator=Locator(testid="btn-add"))
    g1 = ground_action(act1, grounded)
    assert g1 is not None
    assert g1.locator.name == "Add to Cart"

    # Valid fill matching role and name
    act2 = Action(id="a2", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="quantity"), value="5\x00")
    g2 = ground_action(act2, grounded)
    assert g2 is not None
    assert g2.value == "5"


def test_ground_action_drops_ungrounded_action():
    grounded = [
        Action(id="c1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Submit")),
    ]

    # Action targeting non-existent element
    fake_act = Action(id="fake", kind=ActionKind.CLICK, locator=Locator(role="button", name="Phishing Button"))
    initial_dropped = TELEMETRY.dropped_count
    res = ground_action(fake_act, grounded)
    assert res is None
    assert TELEMETRY.dropped_count == initial_dropped + 1


def test_ground_action_passes_goto():
    grounded = []
    goto_act = Action(id="g", kind=ActionKind.GOTO, value="/about")
    res = ground_action(goto_act, grounded)
    assert res is not None
    assert res.value == "/about"
