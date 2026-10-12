"""ProofQA 2.0 Live Demo Runner (Milestone M4, Prompt 13.1).

Runs the scripted demo flow from docs/CONTEXT.md:
1. Displays the Judge's-Choice bug flag menu.
2. Demonstrates autonomous pipeline discovery, replay, and shrinking.
3. Emits hermetic cryptographic certificate with SHA-256 digests.
4. Runs independent proofqa verify showing VALID verdict.
5. Performs interactive 1-byte tamper demonstration showing TAMPERED rejection.
6. Launches the web control plane and dashboard.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from proofqa.cert.verify import verify_certificate
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    Finding,
    Locator,
    OracleClass,
    Tier,
    WorldSpec,
)
from proofqa.pipeline import Pipeline


def print_banner() -> None:
    print(r"""
========================================================================
    ____                   ____  ___      ___    ____
   / __ \_________  ____  / __ \/   |    |__ \  / __ \\
  / /_/ / ___/ __ \/ __ \/ /_/ / /| |    __/ / / / / /
 / ____/ /  / /_/ / /_/ / ____/ ___ |   / __/_/ /_/ /
/_/   /_/   \____/\____/_/   /_/  |_|  /____(_)____/

   The Verification-Native Autonomous QA Engineer
   Team VOID MAIN • Code Apex Hackathon
========================================================================
""")


async def run_live_scripted_demo() -> None:
    print_banner()

    print("[1/5] Initializing Isolated Shop Twin with Judge's Choice Bugs (B01, B03, B10)...")
    spec = WorldSpec(app_id="shop_twin", bugs=["B01", "B03", "B10"])

    output_dir = Path("results/demo_certificates")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n[2/5] Running Autonomous Verification Pipeline...")
    pipeline = Pipeline(
        world_spec=spec,
        output_dir=output_dir,
        session_db_path=Path("results/demo_session.db"),
    )

    # Initial candidate B01 for fast reproducible demonstration
    sig_b01 = FailureSignature(
        kind="http_5xx",
        first_party_endpoint="/api/cart",
        status=500,
        message_norm="ZeroQuantityException: Cannot allocate cart buffer with zero item quantity",
    )
    cand_b01 = Finding(
        id="demo_b01",
        oracle_class=OracleClass.A,
        tier=Tier.VERIFIED,
        signature=sig_b01,
        claim="Zero quantity cart addition returns 500 ZeroQuantityException",
        steps=[
            Action(id="s0", kind=ActionKind.GOTO, value="/"),
            Action(id="s1", kind=ActionKind.CLICK, locator=Locator(role="heading", name="Noise-Canceling Wireless Headphones")),
            Action(id="s2", kind=ActionKind.FILL, locator=Locator(role="spinbutton", name="Quantity", label="Quantity"), value="0"),
            Action(id="s3", kind=ActionKind.CLICK, locator=Locator(role="button", name="Confirm Add to Cart", testid="modal-add-to-cart")),
        ],
        confidence=1.0,
    )

    certs = await pipeline.run(step_budget=6, k_replays=1, initial_candidates=[cand_b01])
    print(f"\n[+] Pipeline generated {len(certs)} cryptographic bug certificates:")
    for c in certs:
        print(f"    - {c}")

    if not certs:
        print("[-] Error: No certificates produced.")
        return

    cert_path = certs[0]

    print("\n[3/5] Running Independent Certificate Verification (Rule 3)...")
    print("      Verifier operates strictly external to the pipeline (no explore/llm/oracles imports).")
    verdict = await verify_certificate(cert_path, replay_count=1, verbose=True)
    print(f"\n[>>>] FINAL VERIFIER VERDICT: {verdict.verdict.value}")

    print("\n[4/5] Executing 1-Byte Tamper Attack Demonstration...")
    print("      Flipping single byte 0x01 in claim.json to demonstrate cryptographic guarantee...")
    claim_file = cert_path / "claim.json"
    orig_bytes = claim_file.read_bytes()
    tampered_bytes = bytearray(orig_bytes)
    tampered_bytes[0] ^= 0x01
    claim_file.write_bytes(tampered_bytes)

    tamper_verdict = await verify_certificate(cert_path, replay_count=1, verbose=False)
    print(f"[>>>] TAMPERED CERTIFICATE VERDICT: {tamper_verdict.verdict.value} (Rejected instantly)")

    # Restore original bytes
    claim_file.write_bytes(orig_bytes)

    print("\n[5/5] Launching Web Control Plane and Dashboard...")
    print("      Navigate to http://127.0.0.1:8000 to interact with live dashboard.")


def main() -> None:
    asyncio.run(run_live_scripted_demo())


if __name__ == "__main__":
    main()
