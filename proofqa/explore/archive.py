"""GoExploreArchive: novelty-directed cell archive and return-to-cell mechanism (Prompt 6)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from proofqa.contracts import Action


@dataclass
class ArchiveCell:
    """A cell in the Go-Explore archive representing a distinct semantic state."""

    state_key: str
    prefix: list[Action]
    visit_count: int = 1
    untried_actions: list[Action] = field(default_factory=list)
    novelty_score: float = 1.0
    is_stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_key": self.state_key,
            "prefix_len": len(self.prefix),
            "visit_count": self.visit_count,
            "untried_count": len(self.untried_actions),
            "novelty_score": self.novelty_score,
            "is_stale": self.is_stale,
        }


class GoExploreArchive:
    """Manages semantic state cells, novelty-weighted selection, and replay return."""

    def __init__(self, max_cell_visits: int = 15) -> None:
        self.cells: dict[str, ArchiveCell] = {}
        self.max_cell_visits = max_cell_visits

    def add_or_update(
        self,
        state_key: str,
        prefix: list[Action],
        grounded_controls: list[Action],
    ) -> tuple[ArchiveCell, bool]:
        """Registers a newly discovered semantic state or updates an existing cell with a shorter path."""
        if state_key not in self.cells:
            # New state discovered!
            novelty = 1.0 / (len(self.cells) + 1.0)
            cell = ArchiveCell(
                state_key=state_key,
                prefix=list(prefix),
                visit_count=1,
                untried_actions=list(grounded_controls),
                novelty_score=novelty,
            )
            self.cells[state_key] = cell
            return cell, True
        else:
            cell = self.cells[state_key]
            cell.visit_count += 1
            # If a strictly shorter trajectory reached this same semantic state, update prefix!
            if len(prefix) < len(cell.prefix):
                cell.prefix = list(prefix)
            # Add any newly visible controls
            known_ids = {a.id for a in cell.untried_actions}
            for ctrl in grounded_controls:
                if ctrl.id not in known_ids:
                    cell.untried_actions.append(ctrl)
            return cell, False

    def select_cell(self, rng: random.Random) -> ArchiveCell | None:
        """Selects a non-stale cell via seeded weighted choice favoring few visits and many untried controls."""
        candidates = [
            c for c in self.cells.values()
            if not c.is_stale and c.visit_count < self.max_cell_visits and len(c.untried_actions) > 0
        ]
        if not candidates:
            # Fallback: allow cells with 0 untried actions if not stale and not over visit limit
            candidates = [
                c for c in self.cells.values()
                if not c.is_stale and c.visit_count < self.max_cell_visits
            ]
        if not candidates:
            return None

        # Sort candidates by state_key for byte-for-byte deterministic tie-breaking
        candidates.sort(key=lambda c: c.state_key)

        weights = [
            ((len(c.untried_actions) + 1.0) / (c.visit_count + 1.0)) * c.novelty_score
            for c in candidates
        ]
        total_w = sum(weights)
        if total_w <= 0:
            return candidates[0]

        normalized_w = [w / total_w for w in weights]
        chosen = rng.choices(candidates, weights=normalized_w, k=1)[0]
        return chosen

    def mark_stale(self, state_key: str) -> None:
        """Marks a cell stale if trajectory replay diverges from the expected semantic state."""
        if state_key in self.cells:
            self.cells[state_key].is_stale = True

    def record_action_tried(self, state_key: str, action_id: str) -> None:
        """Removes a tried action from the cell's untried list."""
        if state_key in self.cells:
            cell = self.cells[state_key]
            cell.untried_actions = [a for a in cell.untried_actions if a.id != action_id]

    def count_active_cells(self) -> int:
        return sum(1 for c in self.cells.values() if not c.is_stale)
