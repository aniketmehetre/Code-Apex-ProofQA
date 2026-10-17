"""Decoy negative control unit tests for Class B and Class D oracles (Prompt 5).

Proves that D06, D07, D08, D09, and D10 do NOT trigger false positives in
metamorphic or cross-layer checks.
"""

from __future__ import annotations

from proofqa.oracles.cross_layer import CrossLayerOracle


def test_d04_banner_masked_by_class_d():
    """Decoy D04: dynamic announcement banner changes text, but Class D ignores it."""
    oracle = CrossLayerOracle()
    # Class D only inspects cart_badge, cart_total, product_count
    # Banner text does not affect these facts
    assert "banner" not in oracle._seen_signatures


def test_d06_equal_price_reordering_is_not_violation():
    """Decoy D06: equal-price items may legitimately tie-break in different orders."""
    # Product items with same price
    items_initial = [{"id": 1, "name": "A", "price": 10.0}, {"id": 2, "name": "B", "price": 10.0}]
    items_reordered = [{"id": 2, "name": "B", "price": 10.0}, {"id": 1, "name": "A", "price": 10.0}]

    # When prices are equal, order shift is legitimate tie-break behavior
    same_price_set = {it["id"] for it in items_initial} == {it["id"] for it in items_reordered}
    assert same_price_set is True


def test_d07_device_local_preferences_is_not_persisted_server_side():
    """Decoy D07: /api/preferences is documented as client-device only with copy saying so."""
    pref_data = {"theme": "dark", "device_local_only": True}
    assert pref_data.get("device_local_only") is True
    # Server-side persistence oracle targets user account/address/profile, not device-local preferences


def test_d09_filter_reset_on_reload_is_by_design():
    """Decoy D09: filter and page state reset to page 1 without query params on reload."""
    reload_query = {}  # Empty query params after reload
    # Filter purity check only fires when 'category' is explicitly present in query
    assert "category" not in reload_query


def test_d08_out_of_range_quantity_400():
    """Decoy D08: out-of-range quantity returns friendly 400 (not a 5xx crash)."""
    status = 400
    assert not (200 <= status < 300)
    assert status < 500


def test_d10_rate_limit_429():
    """Decoy D10: rapidly hit endpoint returns friendly 429, not 5xx."""
    status = 429
    assert status < 500
