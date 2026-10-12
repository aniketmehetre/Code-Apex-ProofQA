"""Acceptance tests for the ProofQA World hermetic execution manager."""

import uuid

import httpx

from proofqa.contracts import WorldSpec
from proofqa.world import World


def test_three_worlds_isolation():
    """Verify three worlds running concurrently with different bug sets maintain complete isolation."""
    spec_clean = WorldSpec(app="shop_twin", bugs=[], seed=101)
    spec_b01 = WorldSpec(app="shop_twin", bugs=["B01"], seed=102)
    spec_b10 = WorldSpec(app="shop_twin", bugs=["B10"], seed=103)

    world_clean = World(spec_clean)
    world_b01 = World(spec_b01)
    world_b10 = World(spec_b10)

    try:
        world_clean.start()
        world_b01.start()
        world_b10.start()

        # Check different ports assigned
        ports = {world_clean.port, world_b01.port, world_b10.port}
        assert len(ports) == 3, f"Expected 3 distinct ports, got {ports}"

        # Log startup times
        print(f"\n[World Startup Times] Clean: {world_clean.startup_time_ms:.1f}ms | B01: {world_b01.startup_time_ms:.1f}ms | B10: {world_b10.startup_time_ms:.1f}ms")
        assert world_clean.startup_time_ms > 0
        assert world_b01.startup_time_ms > 0
        assert world_b10.startup_time_ms > 0

        # World Clean checks: neither B01 nor B10 active
        r1 = httpx.post(f"{world_clean.url}/api/cart", json={"product_id": 1, "quantity": 0})
        assert r1.status_code != 500
        r2 = httpx.get(f"{world_clean.url}/api/products?q=test'")
        assert r2.status_code == 200

        # World B01 checks: B01 active (500), B10 inactive (200)
        r3 = httpx.post(f"{world_b01.url}/api/cart", json={"product_id": 1, "quantity": 0})
        assert r3.status_code == 500
        r4 = httpx.get(f"{world_b01.url}/api/products?q=test'")
        assert r4.status_code == 200

        # World B10 checks: B01 inactive (!=500), B10 active (500)
        r5 = httpx.post(f"{world_b10.url}/api/cart", json={"product_id": 1, "quantity": 0})
        assert r5.status_code != 500
        r6 = httpx.get(f"{world_b10.url}/api/products?q=test'")
        assert r6.status_code == 500

    finally:
        world_clean.stop()
        world_b01.stop()
        world_b10.stop()


def test_world_reset_clears_state():
    """Verify reset() restores pristine seed database without restarting process."""
    spec = WorldSpec(app="shop_twin", bugs=[], seed=999)

    with World(spec) as world:
        email = f"reset_test_{uuid.uuid4().hex[:6]}@example.com"
        password = "password123"

        # 1. Register a user
        reg_res = httpx.post(
            f"{world.url}/api/register",
            json={"email": email, "password": password, "name": "Ephemeral User"},
        )
        assert reg_res.status_code == 200

        # 2. Login to verify user exists
        login_res1 = httpx.post(
            f"{world.url}/api/login",
            json={"email": email, "password": password},
        )
        assert login_res1.status_code == 200

        # 3. Call reset()
        world.reset()

        # 4. Attempt login again -> user must be gone (401)
        login_res2 = httpx.post(
            f"{world.url}/api/login",
            json={"email": email, "password": password},
        )
        assert login_res2.status_code == 401

        # 5. Pristine default test user still exists
        seed_login = httpx.post(
            f"{world.url}/api/login",
            json={"email": "test@example.com", "password": "password123"},
        )
        assert seed_login.status_code == 200
