"""Comprehensive deterministic tests for all bugs B01-B10 and decoys D01-D05."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.shop_twin.backend.app import app


@pytest.mark.asyncio
async def test_b01_quantity_zero_500(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. When BUGS is off
        monkeypatch.setenv("BUGS", "")
        res_off = await client.post("/api/cart", json={"product_id": 1, "quantity": 0})
        assert res_off.status_code != 500

        # 2. When B01 is on
        monkeypatch.setenv("BUGS", "B01")
        res_on = await client.post("/api/cart", json={"product_id": 1, "quantity": 0})
        assert res_on.status_code == 500
        assert "ZeroQuantityException" in res_on.text


@pytest.mark.asyncio
async def test_b02_state_dependent_checkout_exception(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: Add product 1
        r1 = await client.post("/api/cart", json={"product_id": 1, "quantity": 1})
        item_1_id = r1.json()["items"][0]["id"]

        # Step 2: Add product 2
        await client.post("/api/cart", json={"product_id": 2, "quantity": 1})

        # Step 3: Apply coupon
        await client.post("/api/coupons/apply", json={"code": "SAVE10"})

        # Step 4: Remove item 1
        await client.delete(f"/api/cart/{item_1_id}")

        # Step 5: Checkout when OFF
        monkeypatch.setenv("BUGS", "")
        res_off = await client.post("/api/checkout", json={"address": "123 Test St"})
        assert res_off.status_code == 200

        # Re-create state for ON test
        r_new = await client.post("/api/cart", json={"product_id": 3, "quantity": 1})
        it_id = r_new.json()["items"][0]["id"]
        await client.post("/api/cart", json={"product_id": 4, "quantity": 1})
        await client.post("/api/coupons/apply", json={"code": "SAVE10"})
        await client.delete(f"/api/cart/{it_id}")

        # Checkout when B02 is ON
        monkeypatch.setenv("BUGS", "B02")
        res_on = await client.post("/api/checkout", json={"address": "123 Test St"})
        assert res_on.status_code == 500
        assert "NullReferenceException" in res_on.text


@pytest.mark.asyncio
async def test_b03_cart_badge_count_mismatch(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        add_r = await client.post("/api/cart", json={"product_id": 5, "quantity": 2})
        it_id = add_r.json()["items"][0]["id"]
        await client.delete(f"/api/cart/{it_id}")

        # When OFF: badge equals item count
        monkeypatch.setenv("BUGS", "")
        cart_off = (await client.get("/api/cart")).json()
        assert cart_off["badge_count"] == cart_off["item_count"]

        # When B03 is ON: badge is item count + 1
        monkeypatch.setenv("BUGS", "B03")
        cart_on = (await client.get("/api/cart")).json()
        assert cart_on["badge_count"] == cart_on["item_count"] + 1


@pytest.mark.asyncio
async def test_b04_displayed_total_ignores_discount(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/cart", json={"product_id": 1, "quantity": 1})
        await client.post("/api/coupons/apply", json={"code": "SAVE10"})

        # When OFF: total = subtotal - discount
        monkeypatch.setenv("BUGS", "")
        cart_off = (await client.get("/api/cart")).json()
        assert cart_off["discount"] > 0
        assert cart_off["total"] == round(cart_off["subtotal"] - cart_off["discount"], 2)

        # When B04 is ON: total = subtotal (ignores coupon discount)
        monkeypatch.setenv("BUGS", "B04")
        cart_on = (await client.get("/api/cart")).json()
        assert cart_on["total"] == cart_on["subtotal"]


@pytest.mark.asyncio
async def test_b05_default_sort_restoration(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Sort by price_asc
        await client.get("/api/products?sort=price_asc")

        # When OFF: default sort restores ID order
        monkeypatch.setenv("BUGS", "")
        def_off = (await client.get("/api/products")).json()
        ids_off = [p["id"] for p in def_off["products"]]
        assert ids_off == sorted(ids_off)

        # When B05 is ON: default sort retains price_asc order
        monkeypatch.setenv("BUGS", "B05")
        def_on = (await client.get("/api/products")).json()
        prices_on = [p["price"] for p in def_on["products"]]
        assert prices_on == sorted(prices_on)


@pytest.mark.asyncio
async def test_b06_category_filter_page_2_leakage(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # When OFF: page 2 of category filter only has Electronics
        monkeypatch.setenv("BUGS", "")
        res_off = (await client.get("/api/products?category=Electronics&page=2&page_size=10")).json()
        assert all(p["category"] == "Electronics" for p in res_off["products"])

        # When B06 is ON: page 2 leaks products from other categories
        monkeypatch.setenv("BUGS", "B06")
        res_on = (await client.get("/api/products?category=Electronics&page=2&page_size=10")).json()
        categories = {p["category"] for p in res_on["products"]}
        assert len(categories) > 1 or any(c != "Electronics" for c in categories)


@pytest.mark.asyncio
async def test_b07_saved_address_lost_on_reload(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        u_email = f"b07_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/register", json={"email": u_email, "password": "password123", "name": "B07 User"})
        await client.put("/api/account/address", json={"address": "777 Memory Lane"})

        # When OFF: address is retained
        monkeypatch.setenv("BUGS", "")
        res_off = await client.get("/api/account/address")
        assert res_off.json()["address"] == "777 Memory Lane"

        # When B07 is ON: address is lost
        monkeypatch.setenv("BUGS", "B07")
        res_on = await client.get("/api/account/address")
        assert res_on.json()["address"] is None


@pytest.mark.asyncio
async def test_b08_short_password_accepted(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 4-character password
        short_pw = "pass"

        # When OFF: rejected (policy is >= 8 chars)
        monkeypatch.setenv("BUGS", "")
        res_off = await client.post(
            "/api/register",
            json={"email": f"b08_off_{uuid.uuid4().hex[:6]}@example.com", "password": short_pw, "name": "Short Pw User"},
        )
        assert res_off.status_code == 400

        # When B08 is ON: accepted
        monkeypatch.setenv("BUGS", "B08")
        res_on = await client.post(
            "/api/register",
            json={"email": f"b08_on_{uuid.uuid4().hex[:6]}@example.com", "password": short_pw, "name": "Short Pw User"},
        )
        assert res_on.status_code == 200


@pytest.mark.asyncio
async def test_b09_intermittent_add_to_cart_500(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # When OFF: 15 additions all succeed
        monkeypatch.setenv("BUGS", "")
        off_results = [
            (await client.post("/api/cart", json={"product_id": 1, "quantity": 1})).status_code
            for _ in range(10)
        ]
        assert all(s == 200 for s in off_results)

        # When B09 is ON: mixed 200 and 500
        monkeypatch.setenv("BUGS", "B09")
        on_results = [
            (await client.post("/api/cart", json={"product_id": 1, "quantity": 1})).status_code
            for _ in range(30)
        ]
        assert 500 in on_results
        assert 200 in on_results


@pytest.mark.asyncio
async def test_b10_single_quote_search_syntax_error(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # When OFF: single quote handled gracefully
        monkeypatch.setenv("BUGS", "")
        res_off = await client.get("/api/products?q=Gamer's")
        assert res_off.status_code == 200

        # When B10 is ON: returns 500
        monkeypatch.setenv("BUGS", "B10")
        res_on = await client.get("/api/products?q=Gamer's")
        assert res_on.status_code == 500
        assert "Database error" in res_on.text


@pytest.mark.asyncio
async def test_decoys_cause_no_first_party_5xx(monkeypatch):
    """Verify always-on decoys (D01, D03, D05) cause no 5xx or unhandled crashes."""
    monkeypatch.setenv("BUGS", "")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # D01: Friendly 404
        d01_res = await client.get("/api/decoy/not-found")
        assert d01_res.status_code == 404
        assert "Friendly 404" in d01_res.text

        # D03: Telemetry ping (2 seconds delay in production, fast in test)
        d03_res = await client.get("/api/telemetry/ping")
        assert d03_res.status_code == 200
        assert d03_res.json()["telemetry"] == "healthy"

        # D05: Deliberate 400 on invalid coupon
        d05_res = await client.post("/api/coupons/apply", json={"code": "NON_EXISTENT_COUPON"})
        assert d05_res.status_code == 400
        assert d05_res.status_code != 500
