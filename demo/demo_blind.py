"""ProofQA 2.0: Blind Discovery Live Demo (Prompt 10).

Explores Shop Twin with all dev bugs enabled and zero hints.
Streams discovery events in real-time, certifies findings, and runs the independent verifier.
Caches event streams in results/demo_blind_cache/ with --replay-recorded fallback support.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

from proofqa.cert.verify import verify_certificate
from proofqa.contracts import VerifyVerdictKind, WorldSpec
from proofqa.pipeline import Pipeline

DEV_BUGS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10"]


async def run_blind_demo(replay_recorded: bool = False, budget: int = 25) -> int:
    cache_dir = Path("results/demo_blind_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    events_cache_file = cache_dir / "events.json"

    print("=" * 70)
    print("  PROOFQA 2.0: BLIND AUTONOMOUS DISCOVERY DEMO")
    print("=" * 70)

    if replay_recorded and events_cache_file.exists():
        print("[!] Running in RECORDED FALLBACK mode (--replay-recorded)")
        print(f"[*] Replaying event stream from {events_cache_file}...\n")
        cached_events = json.loads(events_cache_file.read_text(encoding="utf-8"))
        for ev in cached_events:
            print(f"[RECORDED RUN] {ev.get('timestamp', '')} | {ev.get('event', '')}: {ev.get('data', '')}")
            await asyncio.sleep(0.05)
        print("\n[+] Recorded run replay completed successfully.")
        return 0

    start_time = time.time()
    spec = WorldSpec(app_id="shop_twin", bugs=DEV_BUGS, seed=1)
    output_dir = Path("results/demo_blind_certs")
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline(
        world_spec=spec,
        output_dir=output_dir,
        session_db_path="results/demo_blind.db",
        level="rules_probes_goexplore",
    )

    recorded_events: list[dict] = []

    def on_event(ev: dict) -> None:
        event_name = ev.get("event")
        data = ev.get("data", {})
        ev_record = {
            "timestamp": time.strftime("%H:%M:%S"),
            "event": event_name,
            "data": str(data),
        }
        recorded_events.append(ev_record)

        if event_name == "stage_explore_started":
            print(f"[*] Step Budget: {data.get('step_budget')} | Exploration started...")
        elif event_name == "candidate_found":
            print(f"  [?] DISCOVERED CANDIDATE DEFECT: {data.get('signature', {}).get('message_norm', '')}")
        elif event_name == "certificate_issued":
            print(f"  [+] CERTIFICATE ISSUED: {data.get('certificate_path')}")

    pipeline.event_bus.subscribe(on_event)

    print(f"[*] Launching autonomous exploration on Shop Twin (dev bugs {len(DEV_BUGS)} enabled)...")
    certs = await pipeline.run(step_budget=budget, k_replays=1)

    # Save event stream to cache
    events_cache_file.write_text(json.dumps(recorded_events, indent=2), encoding="utf-8")

    elapsed = time.time() - start_time
    print(f"\n[*] Exploration completed in {elapsed:.2f}s. Total certificates issued: {len(certs)}")

    # Step 2: Run independent verifier on each issued certificate
    print("\n" + "=" * 70)
    print("  INDEPENDENT VERIFICATION OF ISSUED CERTIFICATES (RULE 3)")
    print("=" * 70)

    valid_count = 0
    for cert_path in certs:
        print(f"[*] Verifying certificate at {cert_path}...")
        verdict = await verify_certificate(cert_path, replay_count=1, verbose=False)
        if verdict.verdict in (VerifyVerdictKind.VALID, VerifyVerdictKind.VALID_INTERMITTENT):
            print(f"  [VERDICT] {verdict.verdict.value} (Signature verified independently)")
            valid_count += 1
        else:
            print(f"  [VERDICT] {verdict.verdict.value} ({verdict.reason})")

    print("\n" + "=" * 70)
    print(f"  DEMO COMPLETE: {valid_count}/{len(certs)} certificates verified independently.")
    print(f"  Total Runtime: {elapsed:.1f}s (Budget: {budget} steps)")
    print("=" * 70)

    return 0 if valid_count > 0 else 1


def main() -> None:
    replay = "--replay-recorded" in sys.argv
    budget = 25
    for arg in sys.argv[1:]:
        if arg.isdigit():
            budget = int(arg)
    exit_code = asyncio.run(run_blind_demo(replay_recorded=replay, budget=budget))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
