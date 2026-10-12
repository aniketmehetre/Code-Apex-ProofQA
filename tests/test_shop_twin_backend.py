import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from apps.shop_twin.backend.app import app
from apps.shop_twin.backend.seed import DEFAULT_SEED_DB_PATH, seed_database


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    """Ensure seed database exists before running backend tests."""
    if not DEFAULT_SEED_DB_PATH.exists():
        seed_database(DEFAULT_SEED_DB_PATH)


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["app"] == "shop_twin"


@pytest.mark.asyncio
async def test_products_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Default listing
        res = await client.get("/api/products")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 60
        assert len(data["products"]) == 12
        assert data["total_pages"] == 5

        # Category filter
        res_cat = await client.get("/api/products?category=Electronics")
        assert res_cat.status_code == 200
        cat_data = res_cat.json()
        assert cat_data["total"] == 15
        assert all(p["category"] == "Electronics" for p in cat_data["products"])

        # Search query
        res_q = await client.get("/api/products?q=Headphones")
        assert res_q.status_code == 200
        q_data = res_q.json()
        assert q_data["total"] >= 1
        assert "Headphones" in q_data["products"][0]["name"]

        # Sort price asc
        res_sort = await client.get("/api/products?sort=price_asc&page_size=60")
        assert res_sort.status_code == 200
        products = res_sort.json()["products"]
        prices = [p["price"] for p in products]
        assert prices == sorted(prices)

        # Sort price desc
        res_desc = await client.get("/api/products?sort=price_desc&page_size=60")
        assert res_desc.status_code == 200
        products_desc = res_desc.json()["products"]
        prices_desc = [p["price"] for p in products_desc]
        assert prices_desc == sorted(prices_desc, reverse=True)


@pytest.mark.asyncio
async def test_auth_workflow_and_address():
    test_email = f"alice_{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register new user
        reg_res = await client.post(
            "/api/register",
            json={"email": test_email, "password": "password123", "name": "Alice"},
        )
        assert reg_res.status_code == 200
        assert reg_res.json()["status"] == "registered"

        # Update address
        addr_res = await client.put(
            "/api/account/address",
            json={"address": "456 Silicon Alley"},
        )
        assert addr_res.status_code == 200
        assert addr_res.json()["address"] == "456 Silicon Alley"

        # Get address
        get_addr_res = await client.get("/api/account/address")
        assert get_addr_res.status_code == 200
        assert get_addr_res.json()["address"] == "456 Silicon Alley"

        # Logout
        logout_res = await client.post("/api/logout")
        assert logout_res.status_code == 200

        # Login again
        login_res = await client.post(
            "/api/login",
            json={"email": test_email, "password": "password123"},
        )
        assert login_res.status_code == 200
        assert login_res.json()["status"] == "logged_in"


@pytest.mark.asyncio
async def test_cart_and_coupon_and_checkout():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Initial empty cart
        cart_res = await client.get("/api/cart")
        assert cart_res.status_code == 200
        assert cart_res.json()["item_count"] == 0

        # Add item to cart (product_id = 1)
        add_res = await client.post("/api/cart", json={"product_id": 1, "quantity": 2})
        assert add_res.status_code == 200
        cart_data = add_res.json()
        assert cart_data["item_count"] == 2
        item_id = cart_data["items"][0]["id"]
        subtotal_before = cart_data["subtotal"]
        assert subtotal_before > 0

        # Update quantity
        patch_res = await client.patch(f"/api/cart/{item_id}", json={"quantity": 3})
        assert patch_res.status_code == 200
        assert patch_res.json()["item_count"] == 3

        # Apply invalid coupon
        inv_coupon = await client.post("/api/coupons/apply", json={"code": "INVALID99"})
        assert inv_coupon.status_code == 400

        # Apply valid coupon SAVE10 (10% off)
        val_coupon = await client.post("/api/coupons/apply", json={"code": "SAVE10"})
        assert val_coupon.status_code == 200
        assert val_coupon.json()["coupon"] == "SAVE10"

        # Check cart reflects coupon discount
        cart_after_coupon = (await client.get("/api/cart")).json()
        assert cart_after_coupon["applied_coupon"] == "SAVE10"
        assert cart_after_coupon["discount"] > 0
        expected_total = round(cart_after_coupon["subtotal"] - cart_after_coupon["discount"], 2)
        assert cart_after_coupon["total"] == expected_total

        # Checkout
        checkout_res = await client.post(
            "/api/checkout",
            json={"address": "789 Benchmark Way, Cityville"},
        )
        assert checkout_res.status_code == 200
        order_data = checkout_res.json()
        assert order_data["status"] == "success"
        order_id = order_data["order"]["id"]

        # Cart should now be empty
        empty_cart = (await client.get("/api/cart")).json()
        assert empty_cart["item_count"] == 0
        assert empty_cart["items"] == []

        # Get orders
        orders_res = await client.get("/api/orders")
        assert orders_res.status_code == 200
        orders_list = orders_res.json()
        assert any(o["id"] == order_id for o in orders_list)
