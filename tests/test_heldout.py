"""Scripted request verification for held-out bugs H01-H05 and decoys D06-D10.

Rule: The explorer must NEVER be run on held-out bugs prior to final evaluation.
All checks here are strictly deterministic scripted HTTP client requests.
"""

from __future__ import annotations

import httpx
import pytest

from apps.shop_twin.backend.app import app


@pytest.fixture
def client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")


@pytest.mark.asyncio
async def test_h01_negative_quantity_scripted(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    # Off -> 400 (D08 bounds check) or 200
    monkeypatch.setenv("BUGS", "")
    res = await client.post("/api/cart", json={"product_id": 1, "quantity": -1})
    assert res.status_code == 400

    # On -> HTTP 500
    monkeypatch.setenv("BUGS", "H01")
    res = await client.post("/api/cart", json={"product_id": 1, "quantity": -1})
    assert res.status_code == 500
    assert "NegativeQuantityException" in res.json().get("detail", "")


@pytest.mark.asyncio
async def test_h02_search_injection_scripted(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    # Off -> 200
    monkeypatch.setenv("BUGS", "")
    res = await client.get("/api/products", params={"q": 'test"quote'})
    assert res.status_code == 200

    # On with quote -> HTTP 500
    monkeypatch.setenv("BUGS", "H02")
    res_q = await client.get("/api/products", params={"q": 'test"quote'})
    assert res_q.status_code == 500
    assert "DatabaseError" in res_q.json().get("detail", "")

    # On with percent -> HTTP 500
    res_p = await client.get("/api/products", params={"q": "100%"})
    assert res_p.status_code == 500

    # On with backslash -> HTTP 500
    res_b = await client.get("/api/products", params={"q": "slash\\test"})
    assert res_b.status_code == 500


@pytest.mark.asyncio
async def test_h03_sort_revert_scripted(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BUGS", "H03")
    # 1. Sort by name
    res1 = await client.get("/api/products", params={"sort": "name"})
    assert res1.status_code == 200
    names_sorted = [p["name"] for p in res1.json()["products"]]

    # 2. Revert to default sort with same session cookies -> H03 keeps name sort
    res2 = await client.get("/api/products", params={"sort": "default"}, cookies=res1.cookies)
    assert res2.status_code == 200
    names_reverted = [p["name"] for p in res2.json()["products"]]
    assert names_reverted == names_sorted


@pytest.mark.asyncio
async def test_h04_profile_persistence_scripted(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    # Register/login
    await client.post("/api/register", json={"email": "h04@test.local", "password": "Password123!", "name": "Agent H04"})
    login_res = await client.post("/api/login", json={"email": "h04@test.local", "password": "Password123!"})
    assert login_res.status_code == 200

    # When H04 is on
    monkeypatch.setenv("BUGS", "H04")
    put_res = await client.put("/api/account/profile", json={"display_name": "New Name"}, cookies=login_res.cookies)
    assert put_res.status_code == 200

    get_res = await client.get("/api/account/profile", cookies=login_res.cookies)
    assert get_res.status_code == 200
    # H04 loses the saved display_name
    assert get_res.json()["display_name"] is None


@pytest.mark.asyncio
async def test_h05_direct_coupon_checkout_scripted(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BUGS", "H05")
    # Add product
    add_res = await client.post("/api/cart", json={"product_id": 1, "quantity": 1})
    assert add_res.status_code == 200

    # Apply coupon
    coup_res = await client.post("/api/coupons/apply", json={"code": "SAVE10"})
    assert coup_res.status_code == 200

    # Direct checkout without item deletion -> HTTP 500
    checkout_res = await client.post("/api/checkout", json={"address": "123 Heldout Way"})
    assert checkout_res.status_code == 500
    assert "NullReferenceException" in checkout_res.json().get("detail", "")


@pytest.mark.asyncio
async def test_decoys_d06_to_d10_cause_no_5xx(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BUGS", "D06,D07,D08,D09,D10")

    # D06: equal price tie-break
    r_sort = await client.get("/api/products", params={"sort": "price_asc"})
    assert r_sort.status_code == 200

    # D07: preferences endpoint
    r_pref = await client.get("/api/preferences")
    assert r_pref.status_code == 200
    assert r_pref.json()["device_local_only"] is True

    # D08: out-of-range quantity returns 400 (not 5xx)
    r_d08 = await client.post("/api/cart", json={"product_id": 1, "quantity": 999})
    assert r_d08.status_code == 400

    # D10: rapid calls return 429 when threshold exceeded, never 5xx
    for _ in range(6):
        r_lim = await client.get("/api/rate-limit-check")
    assert r_lim.status_code in (200, 429)
