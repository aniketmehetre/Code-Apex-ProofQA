"""ProofQA Vertical Slice Pipeline (Milestone M1).

Coordinates:
Explore -> Detect -> Replay -> Shrink -> Certify
Emits typed async events across all stages for UI/SSE subscribers.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from proofqa.cert.build import build_certificate
from proofqa.contracts import (
    Finding,
    Tier,
    WorldSpec,
)
from proofqa.explore.explorer import RuleBasedExplorer
from proofqa.oracles.hard_signals import HardSignalsOracle
from proofqa.proof.replay import replay
from proofqa.proof.shrink import shrink
from proofqa.uncertainty import assign_tier, compute_confidence, deduplicate_findings
from proofqa.world.manager import World


class PipelineEventBus:
    """Async event bus dispatching typed pipeline lifecycle events."""

    def __init__(self) -> None:
        self.listeners: list[Callable[[dict[str, Any]], Any]] = []

    def subscribe(self, callback: Callable[[dict[str, Any]], Any]) -> None:
        self.listeners.append(callback)

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        payload = {"event": event_type, "timestamp": time.time(), "data": data}
        for listener in self.listeners:
            try:
                res = listener(payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass


class Pipeline:
    """ProofQA Vertical Slice Execution Engine."""

    def __init__(
        self,
        world_spec: WorldSpec,
        output_dir: Path | str = "results/certificates",
        session_db_path: Path | str = "results/session.db",
        event_bus: PipelineEventBus | None = None,
        level: str = "rules",
        explorer_config: Any = None,
    ) -> None:
        self.world_spec = world_spec
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session_db_path = Path(session_db_path)
        self.session_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.event_bus = event_bus or PipelineEventBus()
        self.level = level
        self.explorer_config = explorer_config
        self.last_request_log: list[dict[str, Any]] = []
        self.last_candidates: list[Finding] = []
        self.last_confirmed_findings: list[Finding] = []
        self._init_session_db()

    def _init_session_db(self) -> None:
        with sqlite3.connect(self.session_db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    oracle_class TEXT,
                    tier TEXT,
                    signature TEXT,
                    certificate_path TEXT,
                    created_at REAL
                )
                """
            )
            conn.commit()

    async def run(
        self,
        step_budget: int = 25,
        k_replays: int = 2,
        initial_candidates: list[Finding] | None = None,
    ) -> list[Path]:
        """Execute full pipeline: explore -> detect -> replay -> shrink -> certify."""
        await self.event_bus.emit("pipeline_started", {"world": self.world_spec.model_dump()})
        certificates: list[Path] = []
        self.last_candidates = []
        self.last_confirmed_findings = []
        self.last_request_log = []

        # 1. Start world and explore
        world = World(self.world_spec)
        with world:
            hard_signals = HardSignalsOracle(world_origin=world.url)

            explorer = RuleBasedExplorer(
                world=world,
                budget_steps=step_budget,
                seed=self.world_spec.seed,
                output_dir=self.output_dir / "explore",
                level=self.level,
                config=self.explorer_config,
            )
            explorer.add_oracle_hook(hard_signals.hook)

            await self.event_bus.emit("stage_explore_started", {"budget": step_budget})
            explore_result = await explorer.explore()
            discovered = list(hard_signals.candidates)
            candidates = list(initial_candidates or []) + discovered

            self.last_request_log = list(world.request_log)
            await self.event_bus.emit(
                "stage_explore_completed",
                {"candidates_found": len(candidates), "steps": explore_result.steps_executed},
            )

        # Deduplicate candidate findings before replay
        candidates = deduplicate_findings(candidates)
        self.last_candidates = list(candidates)

        # 2. For each discovered candidate: Replay, Shrink, and Certify
        for cand in candidates:
            await self.event_bus.emit("candidate_evaluation_started", {"finding_id": cand.id})

            # Check replay reproduction (k of k)
            rep_report = await replay(
                trace=cand.steps,
                world_spec=self.world_spec,
                n=k_replays,
                target_signature=cand.signature,
                concurrency=1,
            )

            # Compute uncertainty breakdown and tier
            breakdown = compute_confidence(
                finding=cand,
                successes=rep_report.fail_count,
                total_replays=k_replays,
            )
            assigned_tier, intent_needed, next_exp = assign_tier(
                finding=cand,
                successes=rep_report.fail_count,
                total_replays=k_replays,
                breakdown=breakdown,
            )

            if assigned_tier == Tier.INSUFFICIENT_EVIDENCE:
                await self.event_bus.emit(
                    "candidate_rejected",
                    {
                        "finding_id": cand.id,
                        "reason": f"Insufficient evidence (reproduced {rep_report.fail_count}/{k_replays})",
                        "suggested_experiment": next_exp,
                    },
                )
                continue

            # Candidate confirmed! Assign tier and confidence
            verified_cand = cand.model_copy(
                update={
                    "tier": assigned_tier,
                    "confidence": breakdown.composite_score,
                    "intent_confirmation_needed": intent_needed,
                }
            )
            self.last_confirmed_findings.append(verified_cand)

            await self.event_bus.emit("stage_shrink_started", {"finding_id": cand.id})
            shrink_res = await shrink(
                trace=cand.steps,
                world_spec=self.world_spec,
                target_signature=cand.signature,
                budget=15,
                enable_level3=True,
            )

            await self.event_bus.emit(
                "stage_shrink_completed",
                {
                    "finding_id": cand.id,
                    "original_steps": len(cand.steps),
                    "reduced_steps": len(shrink_res.reduced_trace),
                },
            )

            # Build Certificate
            cert_path = build_certificate(
                finding=verified_cand,
                world_spec=self.world_spec,
                shrink_result=shrink_res,
                replay_report=rep_report,
                output_dir=self.output_dir,
            )
            certificates.append(cert_path)

            # Record in session db
            with sqlite3.connect(self.session_db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO findings VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        verified_cand.id,
                        verified_cand.oracle_class.value,
                        verified_cand.tier.value,
                        json.dumps(verified_cand.signature.model_dump()),
                        str(cert_path),
                        time.time(),
                    ),
                )
                conn.commit()

            await self.event_bus.emit(
                "certificate_issued",
                {"finding_id": verified_cand.id, "certificate_path": str(cert_path)},
            )

        await self.event_bus.emit(
            "pipeline_completed",
            {"certificates_issued": len(certificates)},
        )
        return certificates
