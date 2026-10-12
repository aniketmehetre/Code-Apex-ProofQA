"""Validation gate and execution runner for Class B Metamorphic Relations."""

from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page

from proofqa.contracts import Finding, WorldSpec
from proofqa.oracles.relations.base import Relation, WidgetClassifier
from proofqa.oracles.relations.filter import CategoryFilterRelation
from proofqa.oracles.relations.persistence import AddressPersistenceRelation
from proofqa.oracles.relations.sort import SortRestorationRelation

logger = logging.getLogger("proofqa.oracles.relations")


class RelationRunner:
    """Manages the lifecycle, clean-world validation gate, and execution of metamorphic relations."""

    def __init__(self, relations: list[Relation] | None = None) -> None:
        self.relations = relations or [
            SortRestorationRelation(),
            CategoryFilterRelation(),
            AddressPersistenceRelation(),
        ]
        self._validated_relations: set[str] = set()

    async def validate_all(self, world_spec: WorldSpec) -> dict[str, bool]:
        """Runs the validation gate across all registered relations on a clean reference world."""
        results: dict[str, bool] = {}
        for rel in self.relations:
            is_valid = await rel.validate(world_spec)
            results[rel.name] = is_valid
            if is_valid:
                self._validated_relations.add(rel.name)
            else:
                logger.warning("Relation %s failed validation and was discarded.", rel.name)
        return results

    async def run_applicable(
        self,
        page: Page,
        world_url: str,
        widgets: dict[str, Any] | None = None,
    ) -> list[Finding]:
        """Executes validated and applicable relations against the current page."""
        if widgets is None:
            widgets = await WidgetClassifier.classify(page)

        findings: list[Finding] = []
        for rel in self.relations:
            # Gate 1: Must have passed clean-world validation
            if rel.name not in self._validated_relations:
                continue

            # Gate 2: Must apply to the detected page widgets
            if not rel.applies(widgets):
                continue

            violation = await rel.run(page, world_url)
            if violation is not None:
                findings.append(violation)

        return findings
