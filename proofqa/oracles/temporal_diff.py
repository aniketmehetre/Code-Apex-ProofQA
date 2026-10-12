"""Oracle Class E: Temporal differential replay between two builds/WorldSpecs."""

from __future__ import annotations

import hashlib

from proofqa.contracts import (
    Action,
    FailureSignature,
    Finding,
    OracleClass,
    Tier,
    WorldSpec,
    normalize_message,
)
from proofqa.proof.replay import replay


class TemporalDifferentialOracle:
    """Class E Oracle: Replays a saved tape on two builds (e.g. baseline and candidate/buggy)

    and detects behavioral divergence.
    """

    async def compare(
        self,
        trace: list[Action],
        baseline_spec: WorldSpec,
        candidate_spec: WorldSpec,
        replays: int = 1,
    ) -> Finding | None:
        """Run trace on baseline and candidate worlds; report behavioral divergence."""
        baseline_rep = await replay(trace, baseline_spec, n=replays)
        candidate_rep = await replay(trace, candidate_spec, n=replays)

        baseline_fails = baseline_rep.fail_count
        candidate_fails = candidate_rep.fail_count

        # Behavioral divergence: candidate failed while baseline passed
        if candidate_fails > 0 and baseline_fails == 0:
            sig = FailureSignature(
                kind="temporal_differential",
                first_party_endpoint="/api/cart",
                status=500,
                error_type="TemporalDifferentialDivergence",
                message_norm=normalize_message(
                    "TemporalDifferential: Candidate build exhibited failure not present in baseline build"
                ),
            )
            fid = f"finding_E_{hashlib.sha256(sig.message_norm.encode('utf-8')).hexdigest()[:8]}"
            return Finding(
                id=fid,
                oracle_class=OracleClass.E,
                tier=Tier.VERIFIED_VIOLATION,
                signature=sig,
                claim=f"Candidate build diverged from baseline: observed failure {sig.message_norm}",
                steps=trace,
                confidence=1.0,
                intent_confirmation_needed=True,
            )

        return None
