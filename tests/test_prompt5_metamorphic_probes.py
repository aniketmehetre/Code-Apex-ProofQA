"""Unit tests for Prompt 5 metamorphic probes and tape oracle."""

from __future__ import annotations

from proofqa.contracts import Action, ActionKind, Locator
from proofqa.explore.probes.base import ProbeContext
from proofqa.explore.probes.inverse import InversePairProbe
from proofqa.explore.probes.pairwise import PairwiseProbe
from proofqa.explore.probes.reload import ReloadProbe
from proofqa.explore.probes.revert import RevertProbe
from proofqa.oracles.relations.tape_oracle import MetamorphicOracle


def test_revert_probe_planning():
    ctrl = Action(
        id="act_sort",
        kind=ActionKind.SELECT,
        locator=Locator(role="combobox", name="Sort products", label="Sort products"),
        value="",
    )
    ctx = ProbeContext(grounded_controls=[ctrl], semantic_state_key="/:hash1")
    probe = RevertProbe()

    assert probe.applies(ctx) is True
    plan = probe.plan(ctx)
    assert len(plan) == 2
    assert plan[0].value == "price_asc"
    assert plan[1].value == ""
    assert plan[1].params.get("restoring") is True


def test_reload_probe_planning():
    ctx = ProbeContext(grounded_controls=[], semantic_state_key="/cart:hash2")
    probe = ReloadProbe()

    assert probe.applies(ctx) is True
    plan = probe.plan(ctx)
    assert len(plan) == 1
    assert plan[0].kind == ActionKind.GOTO
    assert plan[0].value == "/cart"


def test_inverse_pair_probe_planning():
    add_act = Action(
        id="act_add",
        kind=ActionKind.CLICK,
        locator=Locator(role="button", name="Add to Cart"),
    )
    del_act = Action(
        id="act_remove",
        kind=ActionKind.CLICK,
        locator=Locator(role="button", name="Remove item"),
    )
    ctx = ProbeContext(grounded_controls=[add_act, del_act], semantic_state_key="/cart:hash3")
    probe = InversePairProbe()

    assert probe.applies(ctx) is True
    plan = probe.plan(ctx)
    assert len(plan) == 2
    assert plan[0].id == "act_add"
    assert plan[1].id == "act_remove"


def test_pairwise_probe_planning():
    filter_ctrl = Action(
        id="act_filter",
        kind=ActionKind.SELECT,
        locator=Locator(role="combobox", name="Filter by Category", label="Filter by Category"),
        value="",
    )
    page_ctrl = Action(
        id="act_page2",
        kind=ActionKind.CLICK,
        locator=Locator(role="button", name="Page 2", label="Go to page 2"),
    )
    ctx = ProbeContext(grounded_controls=[filter_ctrl, page_ctrl], semantic_state_key="/:hash4")
    probe = PairwiseProbe()

    assert probe.applies(ctx) is True
    plan = probe.plan(ctx)
    assert len(plan) == 2
    assert plan[0].kind == ActionKind.SELECT
    assert plan[0].value == "Electronics"
    assert plan[1].kind == ActionKind.CLICK


def test_metamorphic_oracle_filter_purity():
    import json
    from pathlib import Path

    oracle = MetamorphicOracle()
    act = Action(id="a1", kind=ActionKind.CLICK)

    # Directly verify evaluate_transition with leakage
    oracle._seen_signatures.clear()

    class DummyEventWithBody:
        url = "http://localhost:8000/api/products?category=Electronics&page=2"
        method = "GET"
        status = 200
        response_blob_ref = "test_blob.json"

    # Write temporary blob for test
    blob_dir = Path("results/explore/blobs")
    blob_dir.mkdir(parents=True, exist_ok=True)
    (blob_dir / "test_blob.json").write_text(
        json.dumps({"items": [{"id": 1, "category": "Books"}, {"id": 2, "category": "Electronics"}]}),
        encoding="utf-8",
    )

    findings = oracle.evaluate_transition(act, [DummyEventWithBody()], [])
    assert len(findings) == 1
    assert findings[0].signature.first_party_endpoint == "/api/products"
    assert findings[0].signature.error_type == "MetamorphicViolation"
