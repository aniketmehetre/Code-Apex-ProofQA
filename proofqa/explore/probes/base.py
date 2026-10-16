"""Probe protocol and execution context for active state-space exploration."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from proofqa.contracts import Action


@dataclass
class ProbeContext:
    """Carries grounded controls, semantic state keys, and resources needed by probes."""

    grounded_controls: list[Action]
    semantic_state_key: str
    spec_facts: Any = None
    token_pool: list[str] = field(default_factory=list)
    fixtures: dict[str, Any] = field(default_factory=dict)
    budget_left: int = 25
    rng: random.Random = field(default_factory=lambda: random.Random(42))


class Probe(ABC):
    """Abstract base class for all systematic invariant and metamorphic probes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this probe family (e.g. 'boundary', 'revert', 'reload')."""
        ...

    @abstractmethod
    def applies(self, ctx: ProbeContext) -> bool:
        """Evaluates whether this probe is applicable to the current state and controls."""
        ...

    @abstractmethod
    def plan(self, ctx: ProbeContext) -> list[Action]:
        """Plans a deterministic sequence of actions executing the probe hypothesis."""
        ...
