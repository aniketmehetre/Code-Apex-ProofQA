"""Unit tests for proofbench/reach.py reachability predicates."""

from proofbench.reach import REACH_SPECS, is_bug_reached


def test_b01_reach():
    pos_log = [
        {"method": "GET", "path": "/api/products"},
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 0}},
    ]
    neg_log = [
        {"method": "GET", "path": "/api/products"},
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
    ]
    assert is_bug_reached("B01", pos_log) is True
    assert is_bug_reached("B01", neg_log) is False


def test_b02_reach():
    pos_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "POST", "path": "/api/coupons/apply", "body": {"code": "SAVE10"}},
        {"method": "DELETE", "path": "/api/cart/1"},
        {"method": "POST", "path": "/api/checkout", "body": {"address": "123 Way"}},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "DELETE", "path": "/api/cart/1"},
        {"method": "POST", "path": "/api/checkout", "body": {"address": "123 Way"}},
    ]
    assert is_bug_reached("B02", pos_log) is True
    assert is_bug_reached("B02", neg_log) is False


def test_b03_reach():
    pos_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "DELETE", "path": "/api/cart/1"},
        {"method": "GET", "path": "/api/cart"},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "GET", "path": "/api/cart"},
    ]
    assert is_bug_reached("B03", pos_log) is True
    assert is_bug_reached("B03", neg_log) is False


def test_b04_reach():
    pos_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "POST", "path": "/api/coupons/apply", "body": {"code": "SAVE10"}},
        {"method": "GET", "path": "/api/cart"},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "GET", "path": "/api/cart"},
    ]
    assert is_bug_reached("B04", pos_log) is True
    assert is_bug_reached("B04", neg_log) is False


def test_b05_reach():
    pos_log = [
        {"method": "GET", "path": "/api/products", "query": {"sort": "price_asc"}},
        {"method": "GET", "path": "/api/products", "query": {"sort": ""}},
    ]
    neg_log = [
        {"method": "GET", "path": "/api/products", "query": {"sort": "price_asc"}},
        {"method": "GET", "path": "/api/products", "query": {"sort": "name"}},
    ]
    assert is_bug_reached("B05", pos_log) is True
    assert is_bug_reached("B05", neg_log) is False


def test_b06_reach():
    pos_log = [
        {"method": "GET", "path": "/api/products", "query": {"category": "Electronics", "page": "2"}},
    ]
    neg_log = [
        {"method": "GET", "path": "/api/products", "query": {"category": "Electronics", "page": "1"}},
    ]
    assert is_bug_reached("B06", pos_log) is True
    assert is_bug_reached("B06", neg_log) is False


def test_b07_reach():
    pos_log = [
        {"method": "POST", "path": "/api/register", "status": 200},
        {"method": "PUT", "path": "/api/account/address", "status": 200},
        {"method": "GET", "path": "/api/account/address"},
    ]
    neg_log = [
        {"method": "PUT", "path": "/api/account/address", "status": 200},
    ]
    assert is_bug_reached("B07", pos_log) is True
    assert is_bug_reached("B07", neg_log) is False


def test_b08_reach():
    pos_log = [
        {"method": "POST", "path": "/api/register", "body": {"email": "u@e.com", "password": "pass"}},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/register", "body": {"email": "u@e.com", "password": "Password123!"}},
    ]
    assert is_bug_reached("B08", pos_log) is True
    assert is_bug_reached("B08", neg_log) is False


def test_b09_reach():
    pos_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 2, "quantity": 1}},
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 3, "quantity": 1}},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
    ]
    assert is_bug_reached("B09", pos_log) is True
    assert is_bug_reached("B09", neg_log) is False


def test_b10_reach():
    pos_log = [
        {"method": "GET", "path": "/api/products", "query": {"q": "head'phone"}},
    ]
    neg_log = [
        {"method": "GET", "path": "/api/products", "query": {"q": "headphone"}},
    ]
    assert is_bug_reached("B10", pos_log) is True
    assert is_bug_reached("B10", neg_log) is False


def test_all_ten_specs_registered():
    for i in range(1, 11):
        bid = f"B{i:02d}"
        assert bid in REACH_SPECS
        assert REACH_SPECS[bid].bug_id == bid


def test_h01_reach():
    pos_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": -1}},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
    ]
    assert is_bug_reached("H01", pos_log) is True
    assert is_bug_reached("H01", neg_log) is False


def test_h02_reach():
    pos_quote = [{"method": "GET", "path": "/api/products", "query": {"q": 'test"quote'}}]
    pos_percent = [{"method": "GET", "path": "/api/products", "query": {"q": "100%"}}]
    pos_backslash = [{"method": "GET", "path": "/api/products", "query": {"q": "test\\escape"}}]
    neg = [{"method": "GET", "path": "/api/products", "query": {"q": "clean query"}}]
    assert is_bug_reached("H02", pos_quote) is True
    assert is_bug_reached("H02", pos_percent) is True
    assert is_bug_reached("H02", pos_backslash) is True
    assert is_bug_reached("H02", neg) is False


def test_h03_reach():
    pos_log = [
        {"method": "GET", "path": "/api/products", "query": {"sort": "name"}},
        {"method": "GET", "path": "/api/products", "query": {"sort": "default"}},
    ]
    neg_log = [
        {"method": "GET", "path": "/api/products", "query": {"sort": "name"}},
    ]
    assert is_bug_reached("H03", pos_log) is True
    assert is_bug_reached("H03", neg_log) is False


def test_h04_reach():
    pos_log = [
        {"method": "PUT", "path": "/api/account/profile", "body": {"phone": "555-1234"}},
        {"method": "GET", "path": "/api/account/profile"},
    ]
    neg_log = [
        {"method": "GET", "path": "/api/account/profile"},
    ]
    assert is_bug_reached("H04", pos_log) is True
    assert is_bug_reached("H04", neg_log) is False


def test_h05_reach():
    pos_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "POST", "path": "/api/coupons/apply", "body": {"code": "SAVE10"}},
        {"method": "POST", "path": "/api/checkout", "body": {"address": "123 Main"}},
    ]
    neg_log = [
        {"method": "POST", "path": "/api/cart", "body": {"product_id": 1, "quantity": 1}},
        {"method": "POST", "path": "/api/coupons/apply", "body": {"code": "SAVE10"}},
        {"method": "DELETE", "path": "/api/cart/1"},
        {"method": "POST", "path": "/api/checkout", "body": {"address": "123 Main"}},
    ]
    assert is_bug_reached("H05", pos_log) is True
    assert is_bug_reached("H05", neg_log) is False


def test_all_heldout_specs_registered():
    for i in range(1, 6):
        hid = f"H{i:02d}"
        assert hid in REACH_SPECS
        assert REACH_SPECS[hid].bug_id == hid
