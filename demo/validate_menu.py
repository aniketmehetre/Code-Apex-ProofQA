"""Judge's-choice menu validator proving bug flags end-to-end (Prompt 13.1).

Validates that each bug flag in the catalogue can be injected, triggered,
certified, and verified independently with VALID verdict.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from proofbench.adjudicate import Adjudicator
from proofqa.cert.verify import verify_certificate
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    VerifyVerdictKind,
    WorldSpec,
)
from proofqa.pipeline import Pipeline

MENU_FLAGS = [
    ("B01", "Zero quantity cart addition returns 500", "A", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones")),
        Action(id="s2", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"), value="0"),
        Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart")),
    ]),
    ("B02", "Coupon dereference crash after item deletion", "A", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(testid="add-to-cart-1")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(testid="add-to-cart-2")),
        Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="View Shopping Cart")),
        Action(id="s4", kind=ActionKind.FILL, locator=Locator(role="textbox", label="Coupon Code"), value="SAVE10"),
        Action(id="s5", kind=ActionKind.CLICK, locator=Locator(role="button", name="Apply")),
        Action(id="s6", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove")),
        Action(id="s7", kind=ActionKind.CLICK, locator=Locator(role="button", name="Proceed to Checkout")),
        Action(id="s8", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Shipping Address"), value="123 Test St"),
        Action(id="s9", kind=ActionKind.CLICK, locator=Locator(role="button", name="Place Order")),
    ]),
    ("B03", "Cart badge count UI vs network divergence", "D", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(testid="add-to-cart-1")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="View Shopping Cart")),
        Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove")),
    ]),
    ("B04", "Cart summary total ignores discount", "D", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(testid="add-to-cart-1")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="View Shopping Cart")),
        Action(id="s3", kind=ActionKind.FILL, locator=Locator(role="textbox", label="Coupon Code"), value="SAVE10"),
        Action(id="s4", kind=ActionKind.CLICK, locator=Locator(role="button", name="Apply")),
    ]),
    ("B05", "Sort restoration metamorphic violation", "B", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Sort products"), value="price_asc"),
        Action(id="s2", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Sort products"), value=""),
    ]),
    ("B06", "Filter category fails on page 2", "B", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.SELECT, locator=Locator(role="combobox", name="Filter by Category"), value="Electronics"),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Page 2")),
    ]),
    ("B07", "Saved address loss upon page reload", "B", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
    ]),
    ("B08", "Weak password allowed during registration", "C", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Sign In")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Sign up here")),
        Action(id="s3", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Full Name"), value="Weak User"),
        Action(id="s4", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Email Address"), value="weak_test@example.com"),
        Action(id="s5", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Password"), value="1234"),
        Action(id="s6", kind=ActionKind.CLICK, locator=Locator(role="button", name="Register")),
    ]),
    ("B09", "Transient concurrency lock timeout during cart insertion", "A", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart", testid="add-to-cart-1"), burst=5),
    ]),
    ("B10", "Unescaped single quote SQL injection in search", "A", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.FILL, locator=Locator(role="searchbox", name="Search products"), value="'"),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Submit Search")),
    ]),
]


async def validate_flag(
    flag: str,
    desc: str,
    o_class: str,
    steps: list[Action],
    output_root: Path,
    blind: bool = False,
) -> bool:
    mode_str = "BLIND DISCOVERY" if blind else "SCRIPTED DETERMINISTIC"
    print("\n=======================================================")
    print(f"[*] Validating Flag: {flag} - {desc} ({mode_str})")
    print("=======================================================")

    spec = WorldSpec(app_id="shop_twin", bugs=[flag])
    out_dir = output_root / f"cert_{flag}"
    pipeline = Pipeline(
        world_spec=spec,
        output_dir=out_dir,
        session_db_path=output_root / f"session_{flag}.db",
        level="rules_probes_goexplore" if blind else "rules",
    )

    if blind:
        # Autonomous blind discovery: no seeded candidate
        certs = await pipeline.run(step_budget=20, k_replays=1)
    else:
        # Scripted deterministic execution
        endpoint = (
            "/api/checkout" if flag == "B02"
            else "/api/cart" if "cart" in desc.lower() or flag in ("B01", "B03", "B04", "B09")
            else "/api/products" if "search" in desc.lower() or "sort" in desc.lower() or flag in ("B05", "B06", "B10")
            else "/api/register" if flag == "B08"
            else "/api/account/address"
        )
        error_type = (
            "ZeroQuantityException" if flag == "B01"
            else "NullReferenceException" if flag == "B02"
            else "CrossLayerMismatch" if flag in ("B03", "B04")
            else "MetamorphicViolation" if flag in ("B05", "B06", "B07")
            else "SpecViolation" if flag == "B08"
            else "LockTimeoutException" if flag == "B09"
            else "DatabaseError" if flag == "B10"
            else None
        )
        sig = FailureSignature(
            kind="http_5xx" if o_class == "A" else "cross_layer_inconsistency" if o_class == "D" else "spec_claim_violation" if o_class == "C" else "relation_violation",
            first_party_endpoint=endpoint,
            status=500 if o_class == "A" else 200 if o_class == "C" else None,
            error_type=error_type,
            message_norm=f"HTTP <NUM> on {endpoint}" if o_class == "A" else desc,
        )

        candidate = Finding(
            id=f"menu_{flag}",
            oracle_class=OracleClass(o_class),
            tier=Tier.INTERMITTENT if flag == "B09" else Tier.VERIFIED,
            signature=sig,
            claim=desc,
            steps=steps,
            confidence=1.0,
        )
        certs = await pipeline.run(step_budget=0, k_replays=1, initial_candidates=[candidate])

    if not certs:
        print(f"[-] FAILED: No certificate issued for flag {flag}")
        return False

    cert_path = certs[0]
    print(f"[+] Certificate generated: {cert_path}")

    # Verify independently (Rule 3)
    verdict = await verify_certificate(cert_path, replay_count=1, verbose=False)
    print(f"[+] Independent Verifier Verdict: {verdict.verdict.value}")

    if verdict.verdict not in (VerifyVerdictKind.VALID, VerifyVerdictKind.VALID_INTERMITTENT):
        print(f"[-] FAILED: Certificate rejected by verifier ({verdict.verdict.value})")
        return False

    # Adjudicate against ground truth
    adjudicator = Adjudicator()
    target_finding = pipeline.last_confirmed_findings[0] if pipeline.last_confirmed_findings else None
    if target_finding:
        status, bid = adjudicator.adjudicate(target_finding, set())
        print(f"[+] Ground-Truth Adjudication: status={status}, bug_id={bid}")

    print(f"[SUCCESS] Flag {flag} passed end-to-end certification and verification.")
    return True


async def main() -> int:
    output_root = Path("results/validate_menu")
    output_root.mkdir(parents=True, exist_ok=True)

    args = sys.argv[1:]
    blind = "--blind" in args
    filtered_args = [a for a in args if not a.startswith("--")]

    target_flags = filtered_args if filtered_args else [m[0] for m in MENU_FLAGS]

    passed = 0
    total = 0

    for flag, desc, o_class, steps in MENU_FLAGS:
        if flag in target_flags or "all" in [t.lower() for t in target_flags]:
            total += 1
            ok = await validate_flag(flag, desc, o_class, steps, output_root, blind=blind)
            if ok:
                passed += 1

    print("\n" + "=" * 55)
    print(f"[*] VALIDATE-MENU SUMMARY: {passed} of {total} flags passed.")
    print("=" * 55)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
