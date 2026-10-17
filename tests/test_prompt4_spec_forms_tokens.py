"""Unit tests for Prompt 4: SpecFacts, forms, boundary probes, tokens, auth, and Class C."""

from __future__ import annotations

from pathlib import Path

from proofqa.contracts import Action, ActionKind, Locator, NetworkEvent, OracleClass
from proofqa.explore.auth import AuthBootstrap
from proofqa.explore.forms import FormPlan
from proofqa.explore.probes.base import ProbeContext
from proofqa.explore.probes.boundary import BoundaryProbe
from proofqa.explore.tokens import TokenPool
from proofqa.oracles.spec_claims import SpecClaimsOracle
from proofqa.spec.facts import SpecFact, SpecFactStore


def test_spec_fact_store_html_attributes():
    store = SpecFactStore()
    attrs = {
        "minlength": "8",
        "maxlength": "64",
        "min": "1",
        "max": "99",
        "required": True,
        "pattern": r"^[0-9]+$",
    }
    facts = store.extract_from_html_attributes(attrs, subject="quantity", page="/cart")
    assert len(facts) == 6
    assert store.get_fact_value("quantity", "min") == 1.0
    assert store.get_fact_value("quantity", "max") == 99.0
    assert store.get_fact_value("quantity", "required") is True


def test_spec_fact_store_page_copy_regex():
    store = SpecFactStore()
    page_text = """
    Welcome to ApexShop.
    Security Notice: Password must be at least 8 characters long.
    Shopping Policy: Quantity must be between 1 and 99 items per order.
    """
    facts = store.extract_from_page_copy(page_text, page="/about")
    assert len(facts) >= 3

    assert store.get_fact_value("password", "min_len") == 8
    assert store.get_fact_value("quantity", "min") == 1
    assert store.get_fact_value("quantity", "max") == 99


def test_form_plan_baseline_and_boundary_variants():
    fact_store = SpecFactStore()
    fact_store.add_fact(
        SpecFact(
            subject="password",
            kind="min_len",
            value=8,
            source="copy",
            evidence_text="at least 8 characters",
            page="/register",
        )
    )
    fact_store.add_fact(
        SpecFact(
            subject="quantity",
            kind="min",
            value=1,
            source="copy",
            evidence_text="minimum 1",
            page="/product",
        )
    )

    f_pw = Action(id="f1", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Password", label="Password"))
    f_qty = Action(id="f2", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"))
    submit_btn = Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Register"))

    plan = FormPlan(fields=[f_pw, f_qty], submit_control=submit_btn)
    baselines = plan.baseline_values(seed=42, fact_store=fact_store)

    assert len(baselines[f_pw.id]) >= 12
    assert baselines[f_qty.id] == "1"

    # Boundary variants for quantity
    qty_variants = plan.boundary_variants_for_field(f_qty, fact_store=fact_store)
    assert "0" in qty_variants
    assert "-1" in qty_variants
    assert "⚡🚀Ω≈ç√∫˜µ" in qty_variants

    # Boundary variants for password
    pw_variants = plan.boundary_variants_for_field(f_pw, fact_store=fact_store)
    assert "pass" in pw_variants
    assert "a" * 7 in pw_variants


def test_boundary_probe_generation():
    ctrl1 = Action(id="c1", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Password"))
    btn = Action(id="b1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Register"))

    probe = BoundaryProbe()
    ctx = ProbeContext(
        grounded_controls=[ctrl1, btn],
        semantic_state_key="/register:hash",
    )

    assert probe.applies(ctx) is True
    actions = probe.plan(ctx)
    assert len(actions) >= 2
    # Last action must be the submit button click
    assert actions[-1].kind == ActionKind.CLICK
    assert actions[-1].locator.name == "Register"


def test_token_pool_harvesting_and_fixtures(tmp_path: Path):
    # Fixtures file
    fixtures_file = tmp_path / "test_fixtures.yaml"
    fixtures_file.write_text("promo_codes:\n  - DISK50\n  - CODE99\n", encoding="utf-8")

    pool = TokenPool(fixtures_path=fixtures_file)
    assert "DISK50" in pool.get_tokens()
    assert "CODE99" in pool.get_tokens()

    # Harvest from DOM text near promo keywords
    text = "Get 20% off with promo code SAVE20 at checkout!"
    harvested = pool.harvest_from_text(text)
    assert "SAVE20" in harvested
    assert "SAVE20" in pool.get_tokens()

    # Harvest from placeholder
    input_act = Action(id="i1", kind=ActionKind.FILL, locator=Locator(label="Enter promo code WELCOME10"))
    h2 = pool.harvest_from_placeholders([input_act])
    assert "WELCOME10" in h2
    assert "WELCOME10" in pool.get_tokens()


def test_auth_bootstrap_wall_detection_and_planning():
    events = [
        NetworkEvent(method="GET", url="/api/orders", status=401, first_party=True)
    ]
    controls = [
        Action(id="c1", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Email")),
        Action(id="c2", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Password")),
        Action(id="c3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Login")),
    ]

    is_wall = AuthBootstrap.is_auth_wall(url_path="/account", recent_events=events, grounded_controls=controls)
    assert is_wall is True

    actions = AuthBootstrap.plan_login_or_register(controls, fixtures={"accounts": {"test_user": {"email": "fix@test.com", "password": "fix_password"}}})
    assert len(actions) == 3
    assert any(a.value == "fix@test.com" for a in actions)
    assert any(a.value == "fix_password" for a in actions)
    assert actions[-1].kind == ActionKind.CLICK


def test_class_c_with_spec_fact_store_detects_violation_and_ignores_decoy_d08():
    fact_store = SpecFactStore()
    fact_store.add_fact(
        SpecFact(
            subject="quantity",
            kind="min",
            value=1,
            source="copy",
            evidence_text="Quantity must be at least 1",
            page="/product",
        )
    )

    oracle = SpecClaimsOracle(offline=True, fact_store=fact_store)

    action = Action(
        id="act_qty",
        kind=ActionKind.FILL,
        locator=Locator(name="Quantity", role="spinbutton"),
        value="0",
    )

    # Case 1: Server accepts invalid qty 0 with 200 OK -> Violation!
    ev_200 = [
        NetworkEvent(method="POST", url="http://test/api/cart", status=200, first_party=True)
    ]
    finding = oracle.evaluate_transition(fact_store, action, ev_200, action_prefix=[])
    assert finding is not None
    assert finding.oracle_class == OracleClass.C
    assert "Quantity must be at least 1" in finding.claim

    # Case 2: Decoy D08 returns friendly 400 Bad Request on invalid qty -> NO Violation! D08 stays clean!
    ev_400 = [
        NetworkEvent(method="POST", url="http://test/api/cart", status=400, first_party=True)
    ]
    finding_d08 = oracle.evaluate_transition(fact_store, action, ev_400, action_prefix=[])
    assert finding_d08 is None, "Decoy D08 returning 400 must NOT be flagged by Class C!"
