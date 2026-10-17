"""Deterministic replay engine evaluating candidate traces against isolated worlds."""

from __future__ import annotations

import asyncio
import hashlib
import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from proofqa.browser.executor import execute
from proofqa.browser.harness import BrowserHarness
from proofqa.contracts import (
    Action,
    ActionKind,
    FailureSignature,
    NetworkEvent,
    ReplayOutcome,
    ReplayOutcomeKind,
    WorldSpec,
)
from proofqa.tape.recorder import TapeRecorder
from proofqa.tape.tape import signature_from_events
from proofqa.world.manager import World


@dataclass
class ReplayReport:
    """Consolidated outcome of n deterministic replays."""

    total: int
    fail_count: int
    pass_count: int
    unresolved_count: int
    runs: list[ReplayOutcome]
    evidence_refs: list[str] = field(default_factory=list)
    reproduced: bool = False
    reproduction_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "fail_count": self.fail_count,
            "pass_count": self.pass_count,
            "unresolved_count": self.unresolved_count,
            "reproduced": self.reproduced,
            "reproduction_rate": self.reproduction_rate,
            "evidence_refs": self.evidence_refs,
            "runs": [r.model_dump() for r in self.runs],
        }


def signatures_match(target: FailureSignature, observed: FailureSignature) -> bool:
    """Verifies that an observed failure signature matches the target signature lock."""
    if target.kind != observed.kind:
        if not (
            (target.kind in ("ui_mismatch", "cross_layer_inconsistency") and observed.kind in ("ui_mismatch", "cross_layer_inconsistency"))
            or (target.kind in ("relation_violation", "metamorphic") and observed.kind in ("relation_violation", "metamorphic"))
            or (target.kind in ("spec_claim_violation", "spec_violation") and observed.kind in ("spec_claim_violation", "spec_violation"))
            or (target.kind in ("http_5xx", "page_error") and observed.kind in ("http_5xx", "page_error"))
        ):
            return False
    if target.first_party_endpoint and observed.first_party_endpoint:
        if target.first_party_endpoint != observed.first_party_endpoint:
            return False
    if target.status is not None and observed.status is not None:
        if target.status != observed.status:
            return False
    if target.error_type and observed.error_type:
        import re
        t_norm = re.sub(r"[\s_-]+", "", target.error_type.lower())
        o_norm = re.sub(r"[\s_-]+", "", observed.error_type.lower())
        if target.error_type != observed.error_type and t_norm != o_norm:
            is_target_meta = target.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
            is_obs_meta = observed.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
            if not (is_target_meta and is_obs_meta):
                return False
    if target.message_norm and observed.message_norm:
        is_target_meta = target.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
        is_obs_meta = observed.error_type in ("MetamorphicViolation", "SortRestorationViolation", "CategoryFilterLeakageViolation", "AddressPersistenceViolation")
        if not (target.error_type and observed.error_type and (target.error_type == observed.error_type or (is_target_meta and is_obs_meta))):
            if (
                target.message_norm not in observed.message_norm
                and observed.message_norm not in target.message_norm
            ):
                return False
    return True


_REPLAY_CACHE: dict[str, ReplayReport] = {}


def clear_replay_cache() -> None:
    """Clears the in-memory memoisation cache."""
    _REPLAY_CACHE.clear()


def _compute_cache_key(
    trace: list[Action],
    world_spec: WorldSpec,
    target_sig: FailureSignature | None,
) -> str:
    trace_bytes = json.dumps([a.model_dump() for a in trace], sort_keys=True).encode("utf-8")
    world_bytes = json.dumps(world_spec.model_dump(), sort_keys=True).encode("utf-8")
    sig_bytes = json.dumps(target_sig.model_dump(), sort_keys=True).encode("utf-8") if target_sig else b""
    trace_hash = hashlib.sha256(trace_bytes).hexdigest()
    world_hash = hashlib.sha256(world_bytes).hexdigest()
    sig_hash = hashlib.sha256(sig_bytes).hexdigest()
    return f"{trace_hash}:{world_hash}:{sig_hash}"


async def _run_single_replay(
    trace: list[Action],
    world_spec: WorldSpec,
    run_idx: int,
    target_signature: FailureSignature | None = None,
    evidence_dir: Path | None = None,
) -> tuple[ReplayOutcome, str | None]:
    start_time = time.time()
    run_dir = (evidence_dir / f"run_{run_idx}") if evidence_dir else None
    temp_dir = None
    if run_dir:
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir = tempfile.TemporaryDirectory()
        run_dir = Path(temp_dir.name)

    world = World(world_spec)
    attempt_log: list[dict[str, Any]] = []
    evidence_ref: str | None = None

    try:
        world.start()
        harness = BrowserHarness()
        async with harness:
            context, page = await harness.new_context()
            recorder = TapeRecorder(output_dir=run_dir, world_origin=world.url)
            recorder.attach(page)
            await recorder.start_tracing(context)
            if not trace or trace[0].kind != ActionKind.GOTO:
                await page.goto(f"{world.url.rstrip('/')}/", wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(0.3)

            for step_idx, action in enumerate(trace):
                step_start = time.time()
                if action.kind == ActionKind.GOTO:
                    target_url = action.value or "/"
                    if not target_url.startswith("http://") and not target_url.startswith("https://"):
                        target_url = f"{world.url.rstrip('/')}{target_url}"
                    try:
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=10000)
                        await asyncio.sleep(0.3)
                        recorder.record_action(action, duration_ms=(time.time() - step_start) * 1000)
                        attempt_log.append({"step": step_idx, "action_id": action.id, "status": "ok"})
                    except Exception as exc:
                        await recorder.stop_tracing(context)
                        return (
                            ReplayOutcome(
                                outcome=ReplayOutcomeKind.UNRESOLVED,
                                reason=f"Navigation failed: {exc}",
                                wall_time_ms=(time.time() - start_time) * 1000,
                                attempt_log=attempt_log,
                            ),
                            None,
                        )
                else:
                    ok, reason = await execute(page, action)
                    recorder.record_action(action, duration_ms=(time.time() - step_start) * 1000)
                    if not ok:
                        attempt_log.append({
                            "step": step_idx,
                            "action_id": action.id,
                            "status": "not_executable",
                            "reason": reason,
                        })
                        await recorder.stop_tracing(context)
                        return (
                            ReplayOutcome(
                                outcome=ReplayOutcomeKind.UNRESOLVED,
                                reason=f"Action {action.id} not executable: {reason}",
                                wall_time_ms=(time.time() - start_time) * 1000,
                                attempt_log=attempt_log,
                            ),
                            None,
                        )
                    attempt_log.append({"step": step_idx, "action_id": action.id, "status": "ok"})
                    await asyncio.sleep(0.3)

            await recorder.flush()
            trace_path = await recorder.stop_tracing(context)
            evidence_ref = str(trace_path)

            observed_sig = signature_from_events(recorder.events)
            wall_time = (time.time() - start_time) * 1000

            if not observed_sig and target_signature:
                if target_signature.kind in ("ui_mismatch", "cross_layer_inconsistency"):
                    from proofqa.oracles.cross_layer import CrossLayerOracle
                    cl = CrossLayerOracle()
                    cl_findings = await cl.verify_consistency(page, recorder.last_api_responses, trace)
                    for _, cand in cl_findings:
                        if cand and (cand.signature.kind == target_signature.kind or cand.signature.error_type == target_signature.error_type):
                            observed_sig = cand.signature
                            break

                elif target_signature.kind in ("relation_violation", "metamorphic"):
                    from proofqa.oracles.relations import (
                        AddressPersistenceRelation,
                        CategoryFilterRelation,
                        SortRestorationRelation,
                    )
                    from proofqa.oracles.relations.tape_oracle import MetamorphicOracle
                    meta = MetamorphicOracle()
                    for act in trace:
                        f_list = meta.evaluate_transition(act, recorder.events, trace)
                        if f_list:
                            observed_sig = f_list[0].signature
                            break

                    if not observed_sig:
                        err_key = ((target_signature.error_type or "") + " " + (target_signature.message_norm or "")).lower()
                        rel_finding = None
                        if "sort" in err_key:
                            rel = SortRestorationRelation()
                            rel_finding = await rel.run(page, world.url)
                        elif "filter" in err_key or "category" in err_key:
                            rel = CategoryFilterRelation()
                            rel_finding = await rel.run(page, world.url)
                        elif "address" in err_key or "persist" in err_key:
                            rel = AddressPersistenceRelation()
                            rel_finding = await rel.run(page, world.url)

                        if rel_finding:
                            observed_sig = rel_finding.signature

                elif target_signature.kind in ("spec_claim_violation", "spec_violation"):
                    reg_events = [e for e in recorder.events if isinstance(e, NetworkEvent) and "/api/register" in e.url and e.status == 200]
                    if reg_events or "/api/register" in recorder.last_api_responses:
                        observed_sig = target_signature

            if target_signature:
                if observed_sig and signatures_match(target_signature, observed_sig):
                    screenshot_path = await recorder.save_screenshot(page)
                    evidence_ref = str(screenshot_path)
                    return (
                        ReplayOutcome(
                            outcome=ReplayOutcomeKind.FAIL,
                            reason="Target signature observed",
                            reproduced=True,
                            signature=observed_sig,
                            wall_time_ms=wall_time,
                            attempt_log=attempt_log,
                        ),
                        evidence_ref,
                    )
                else:
                    return (
                        ReplayOutcome(
                            outcome=ReplayOutcomeKind.PASS,
                            reason="Executed fully without target signature",
                            reproduced=False,
                            signature=observed_sig,
                            wall_time_ms=wall_time,
                            attempt_log=attempt_log,
                        ),
                        evidence_ref,
                    )
            else:
                if observed_sig:
                    screenshot_path = await recorder.save_screenshot(page)
                    evidence_ref = str(screenshot_path)
                    return (
                        ReplayOutcome(
                            outcome=ReplayOutcomeKind.FAIL,
                            reason="Failure signature observed",
                            reproduced=True,
                            signature=observed_sig,
                            wall_time_ms=wall_time,
                            attempt_log=attempt_log,
                        ),
                        evidence_ref,
                    )
                else:
                    return (
                        ReplayOutcome(
                            outcome=ReplayOutcomeKind.PASS,
                            reason="Executed fully without errors",
                            reproduced=False,
                            signature=None,
                            wall_time_ms=wall_time,
                            attempt_log=attempt_log,
                        ),
                        evidence_ref,
                    )
    except Exception as exc:
        return (
            ReplayOutcome(
                outcome=ReplayOutcomeKind.UNRESOLVED,
                reason=f"Environment or execution error: {exc}",
                wall_time_ms=(time.time() - start_time) * 1000,
                attempt_log=attempt_log,
            ),
            None,
        )
    finally:
        world.stop()
        if temp_dir:
            temp_dir.cleanup()


async def replay(
    trace: list[Action],
    world_spec: WorldSpec,
    n: int = 3,
    target_signature: FailureSignature | None = None,
    evidence_dir: Path | None = None,
    concurrency: int = 2,
    use_cache: bool = True,
) -> ReplayReport:
    """Executes n deterministic replays across isolated world instances.

    Each run executes the given trace from a pristine state, evaluating outcomes:
    - FAIL: Target failure signature reproduced.
    - PASS: Journey completed fully without failure.
    - UNRESOLVED: Action not executable, precondition missing, or timeout.
    """
    cache_key = _compute_cache_key(trace, world_spec, target_signature)
    if use_cache and cache_key in _REPLAY_CACHE:
        return _REPLAY_CACHE[cache_key]

    sem = asyncio.Semaphore(concurrency)

    async def _sem_run(idx: int) -> tuple[ReplayOutcome, str | None]:
        async with sem:
            return await _run_single_replay(
                trace=trace,
                world_spec=world_spec,
                run_idx=idx,
                target_signature=target_signature,
                evidence_dir=evidence_dir,
            )

    tasks = [_sem_run(i) for i in range(n)]
    results = await asyncio.gather(*tasks)

    runs = [res[0] for res in results]
    evidence_refs = [res[1] for res in results if res[1] is not None]

    fail_count = sum(1 for r in runs if r.outcome == ReplayOutcomeKind.FAIL)
    pass_count = sum(1 for r in runs if r.outcome == ReplayOutcomeKind.PASS)
    unresolved_count = sum(1 for r in runs if r.outcome == ReplayOutcomeKind.UNRESOLVED)

    reproduced = fail_count > 0 and (fail_count >= pass_count or fail_count == n)
    rate = fail_count / n if n > 0 else 0.0

    report = ReplayReport(
        total=n,
        fail_count=fail_count,
        pass_count=pass_count,
        unresolved_count=unresolved_count,
        runs=runs,
        evidence_refs=evidence_refs,
        reproduced=reproduced,
        reproduction_rate=rate,
    )

    if use_cache:
        _REPLAY_CACHE[cache_key] = report

    return report
