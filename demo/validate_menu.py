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
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Cart")),
        Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove Item")),
    ]),
    ("B03", "Cart badge count UI vs network divergence", "D", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="button", name="Add to Cart")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Cart")),
        Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Remove Item")),
    ]),
    ("B05", "Sort restoration metamorphic violation", "B", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="combobox", name="Sort")),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="combobox", name="Sort")),
    ]),
    ("B07", "Saved address loss upon page reload", "B", [
        Action(id="s0", kind=ActionKind.GOTO, value="/account"),
        Action(id="s1", kind=ActionKind.FILL, locator=Locator(role="textbox", name="Street"), value="123 Verification St"),
        Action(id="s2", kind=ActionKind.CLICK, locator=Locator(role="button", name="Save Address")),
    ]),
    ("B10", "Unescaped single quote SQL injection in search", "A", [
        Action(id="s0", kind=ActionKind.GOTO, value="/"),
        Action(id="s1", kind=ActionKind.FILL, locator=Locator(role="searchbox", name="Search", testid="search-input"), value="'"),
    ]),
]


async def validate_flag(flag: str, desc: str, o_class: str, steps: list[Action], output_root: Path) -> bool:
    print("\n=======================================================")
    print(f"[*] Validating Judge's-Choice Flag: {flag} - {desc}")
    print("=======================================================")

    spec = WorldSpec(app_id="shop_twin", bugs=[flag])
    out_dir = output_root / f"cert_{flag}"
    pipeline = Pipeline(
        world_spec=spec,
        output_dir=out_dir,
        session_db_path=output_root / f"session_{flag}.db",
    )

    endpoint = (
        "/api/cart" if "cart" in desc.lower()
        else "/api/products" if "search" in desc.lower() or "sort" in desc.lower()
        else "/api/account/address"
    )
    sig = FailureSignature(
        kind="http_5xx" if o_class == "A" else "cross_layer_inconsistency" if o_class == "D" else "relation_violation",
        first_party_endpoint=endpoint,
        status=500 if o_class == "A" else None,
        message_norm=f"HTTP <NUM> on {endpoint}" if o_class == "A" else desc,
    )

    candidate = Finding(
        id=f"menu_{flag}",
        oracle_class=OracleClass(o_class),
        tier=Tier.VERIFIED,
        signature=sig,
        claim=desc,
        steps=steps,
        confidence=1.0,
    )

    certs = await pipeline.run(step_budget=6, k_replays=1, initial_candidates=[candidate])
    if not certs:
        print(f"[-] FAILED: No certificate issued for flag {flag}")
        return False

    cert_path = certs[0]
    print(f"[+] Certificate generated: {cert_path}")

    # Verify independently (Rule 3)
    verdict = await verify_certificate(cert_path, replay_count=1, verbose=False)
    print(f"[+] Independent Verifier Verdict: {verdict.verdict.value}")

    if verdict.verdict != VerifyVerdictKind.VALID:
        print(f"[-] FAILED: Certificate rejected by verifier ({verdict.verdict.value})")
        return False

    # Adjudicate against ground truth
    adjudicator = Adjudicator()
    status, bid = adjudicator.adjudicate(candidate, set())
    print(f"[+] Ground-Truth Adjudication: status={status}, bug_id={bid}")

    print(f"[SUCCESS] Flag {flag} passed end-to-end certification and verification.")
    return True


async def main() -> int:
    output_root = Path("results/validate_menu")
    output_root.mkdir(parents=True, exist_ok=True)

    target_flags = sys.argv[1:] if len(sys.argv) > 1 else [m[0] for m in MENU_FLAGS]

    passed = 0
    total = 0

    for flag, desc, o_class, steps in MENU_FLAGS:
        if flag in target_flags or "all" in [t.lower() for t in target_flags]:
            total += 1
            ok = await validate_flag(flag, desc, o_class, steps, output_root)
            if ok:
                passed += 1

    print("\n" + "=" * 55)
    print(f"[*] VALIDATE-MENU SUMMARY: {passed} of {total} flags passed.")
    print("=" * 55)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
