"""Acceptance tests for Class B Metamorphic Relations detecting B05, B06, B07 and validation gate."""

from __future__ import annotations

import pytest

from proofqa.contracts import OracleClass, WorldSpec
from proofqa.oracles.relations import (
    AddressPersistenceRelation,
    CategoryFilterRelation,
    DeliberatelyFalseRelation,
    RelationRunner,
    SortRestorationRelation,
)
from proofqa.world import World


@pytest.mark.asyncio
async def test_deliberately_false_relation_is_discarded_by_validation() -> None:
    false_rel = DeliberatelyFalseRelation()
    clean_spec = WorldSpec(app_id="shop_twin", bugs=[])

    # Acceptance: A deliberately false relation is discarded by validation
    is_valid = await false_rel.validate(clean_spec)
    assert is_valid is False

    runner = RelationRunner(relations=[false_rel])
    results = await runner.validate_all(clean_spec)
    assert results[false_rel.name] is False
    assert false_rel.name not in runner._validated_relations


@pytest.mark.asyncio
async def test_relations_detect_b05_sort_restoration() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=["B05"])
    world = World(spec)

    with world:
        from proofqa.browser.harness import BrowserHarness
        h = BrowserHarness()
        async with h:
            context, page = await h.new_context()
            await page.goto(f"{world.url}/", wait_until="networkidle")

            rel = SortRestorationRelation()
            finding = await rel.run(page, world.url)

            # Acceptance: Detects B05
            assert finding is not None
            assert finding.oracle_class == OracleClass.B
            assert finding.intent_confirmation_needed is True
            assert "SortRestorationViolation" in finding.signature.message_norm


@pytest.mark.asyncio
async def test_relations_detect_b06_category_filter_leakage() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=["B06"])
    world = World(spec)

    with world:
        from proofqa.browser.harness import BrowserHarness
        h = BrowserHarness()
        async with h:
            context, page = await h.new_context()
            await page.goto(f"{world.url}/", wait_until="networkidle")

            rel = CategoryFilterRelation()
            finding = await rel.run(page, world.url)

            # Acceptance: Detects B06
            assert finding is not None
            assert finding.oracle_class == OracleClass.B
            assert "CategoryFilterLeakageViolation" in finding.signature.message_norm


@pytest.mark.asyncio
async def test_relations_detect_b07_saved_address_loss() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=["B07"])
    world = World(spec)

    with world:
        from proofqa.browser.harness import BrowserHarness
        h = BrowserHarness()
        async with h:
            context, page = await h.new_context()
            rel = AddressPersistenceRelation()
            finding = await rel.run(page, world.url)

            # Acceptance: Detects B07
            assert finding is not None
            assert finding.oracle_class == OracleClass.B
            assert "AddressPersistenceViolation" in finding.signature.message_norm


@pytest.mark.asyncio
async def test_zero_findings_on_clean_twin() -> None:
    spec = WorldSpec(app_id="shop_twin", bugs=[])
    world = World(spec)

    with world:
        from proofqa.browser.harness import BrowserHarness
        h = BrowserHarness()
        async with h:
            context, page = await h.new_context()
            await page.goto(f"{world.url}/", wait_until="networkidle")

            # Run sort relation on clean world
            sort_rel = SortRestorationRelation()
            assert await sort_rel.run(page, world.url) is None

            # Run category filter relation on clean world
            filter_rel = CategoryFilterRelation()
            assert await filter_rel.run(page, world.url) is None
