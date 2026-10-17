"""Explorer configuration and budget limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExplorerLevel = Literal[
    "monkey",
    "rules",
    "rules_probes",
    "rules_probes_goexplore",
    "full",
]

VALID_LEVELS: tuple[str, ...] = (
    "monkey",
    "rules",
    "rules_probes",
    "rules_probes_goexplore",
    "full",
)


@dataclass
class ExplorerConfig:
    """Configurable exploration policies and budget constraints."""

    level: ExplorerLevel = "rules"
    max_actions_per_run: int = 25
    budget_depth: int = 6
    budget_time_seconds: float = 60.0
    per_path_state_cap: int = 8
    per_page_probe_cap: int = 5
    per_probe_budget: int = 10
    archive_budget_fraction: float = 0.5
    global_visit_cap: int = 15

    def __post_init__(self) -> None:
        if self.level not in VALID_LEVELS:
            raise ValueError(f"Invalid explorer level: {self.level}. Must be one of {VALID_LEVELS}")
