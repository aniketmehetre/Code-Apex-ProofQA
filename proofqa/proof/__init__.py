"""Deterministic proof engine, replay, and shrinking."""

from __future__ import annotations

from proofqa.proof.ddmin import ddmin
from proofqa.proof.replay import (
    ReplayReport,
    clear_replay_cache,
    replay,
    signatures_match,
)
from proofqa.proof.shrink import ShrinkResult, shrink

__all__ = [
    "ReplayReport",
    "ShrinkResult",
    "clear_replay_cache",
    "ddmin",
    "replay",
    "shrink",
    "signatures_match",
]
