"""FastAPI backend for the shop twin target application."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, col, create_engine, select

from apps.shop_twin.backend.models import (
    CartItem,
    Coupon,
    Order,
    Product,
    SQLModel,
    User,
    UserSession,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIST = REPO_ROOT / "apps" / "shop_twin" / "frontend" / "dist"

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "seed.db"
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    shop_db_path = os.environ.get("SHOP_DB_PATH", str(DEFAULT_DB_PATH))
    db_url = f"sqlite:///{shop_db_path}"

engine = create_engine(db_url, connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(engine)


def get_db():
    with Session(engine) as session:
        yield session


def hash_password(password: str) -> str:
    return "sha256:" + hashlib.sha256(password.encode("utf-8")).hexdigest()


# Request & Response Schemas
class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class CartAddRequest(BaseModel):
    product_id: int
    quantity: int = 1


class CartUpdateRequest(BaseModel):
    quantity: int


class CouponRequest(BaseModel):
    code: str


class AddressRequest(BaseModel):
    address: str


class CheckoutRequest(BaseModel):
    address: str


app = FastAPI(title="Shop Twin Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_session_id(request: Request, response: Response, db: Session) -> str:
    session_id = request.cookies.get("session_id")
    if session_id:
        existing = db.get(UserSession, session_id)
        if existing:
            return session_id

    # Create new session
    new_id = str(uuid.uuid4())
    user_session = UserSession(id=new_id, created_at=time.time())
    db.add(user_session)
    db.commit()
    response.set_cookie(key="session_id", value=new_id, httponly=True, samesite="lax")
    return new_id


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "shop_twin", "version": "1.0.0"}


@app.post("/api/register")
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    existing = db.exec(select(User).where(User.email == data.email.lower())).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        name=data.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session_id = get_or_create_session_id(request, response, db)
    sess = db.get(UserSession, session_id)
    if sess:
        sess.user_id = user.id
        db.add(sess)
        db.commit()

    return {"status": "registered", "user": {"id": user.id, "email": user.email, "name": user.name}}


@app.post("/api/login")
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.exec(select(User).where(User.email == data.email.lower())).first()
    if not user or user.password_hash != hash_password(data.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_id = get_or_create_session_id(request, response, db)
    sess = db.get(UserSession, session_id)
    if sess:
        sess.user_id = user.id
        db.add(sess)
        db.commit()

    return {"status": "logged_in", "user": {"id": user.id, "email": user.email, "name": user.name}}


@app.post("/api/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = request.cookies.get("session_id")
    if session_id:
        sess = db.get(UserSession, session_id)
        if sess:
            sess.user_id = None
            db.add(sess)
            db.commit()
    response.delete_cookie("session_id")
    return {"status": "logged_out"}


@app.get("/api/products")
def get_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
):
    statement = select(Product)
    if category:
        statement = statement.where(Product.category == category)
    if q:
        query_pattern = f"%{q}%"
        statement = statement.where(
            col(Product.name).ilike(query_pattern) | col(Product.description).ilike(query_pattern)
        )

    # Count total matching products
    all_matching = db.exec(statement).all()
    total_count = len(all_matching)

    # Sort
    if sort == "price_asc":
        statement = statement.order_by(col(Product.price).asc())
    elif sort == "price_desc":
        statement = statement.order_by(col(Product.price).desc())
    elif sort == "name":
        statement = statement.order_by(col(Product.name).asc())
    else:
        statement = statement.order_by(col(Product.id).asc())

    # Pagination
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size)
    items = db.exec(statement).all()

    total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

    return {
        "products": [p.model_dump() for p in items],
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@app.get("/api/cart")
def get_cart(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    sess = db.get(UserSession, session_id)
    items = db.exec(select(CartItem).where(CartItem.session_id == session_id)).all()

    cart_items = []
    subtotal = 0.0
    item_count = 0
    for item in items:
        product = db.get(Product, item.product_id)
        if product:
            line_total = round(product.price * item.quantity, 2)
            subtotal += line_total
            item_count += item.quantity
            cart_items.append({
                "id": item.id,
                "product_id": product.id,
                "name": product.name,
                "price": product.price,
                "quantity": item.quantity,
                "line_total": line_total,
                "category": product.category,
            })

    subtotal = round(subtotal, 2)
    discount = 0.0
    applied_coupon = sess.applied_coupon if sess else None
    if applied_coupon:
        coupon = db.exec(select(Coupon).where(Coupon.code == applied_coupon, Coupon.active)).first()
        if coupon:
            discount = round(subtotal * (coupon.discount_percent / 100.0), 2)

    total = round(max(0.0, subtotal - discount), 2)

    return {
        "items": cart_items,
        "item_count": item_count,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "applied_coupon": applied_coupon,
    }


@app.post("/api/cart")
def add_to_cart(
    data: CartAddRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    product = db.get(Product, data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    existing_item = db.exec(
        select(CartItem).where(
            CartItem.session_id == session_id,
            CartItem.product_id == data.product_id,
        )
    ).first()

    if existing_item:
        existing_item.quantity += data.quantity
        db.add(existing_item)
    else:
        new_item = CartItem(
            session_id=session_id,
            product_id=data.product_id,
            quantity=data.quantity,
        )
        db.add(new_item)

    db.commit()
    return get_cart(request, response, db)


@app.patch("/api/cart/{item_id}")
def update_cart_item(
    item_id: int,
    data: CartUpdateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    item = db.get(CartItem, item_id)
    if not item or item.session_id != session_id:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if data.quantity <= 0:
        db.delete(item)
    else:
        item.quantity = data.quantity
        db.add(item)
    db.commit()

    return get_cart(request, response, db)


@app.delete("/api/cart/{item_id}")
def remove_cart_item(
    item_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    item = db.get(CartItem, item_id)
    if not item or item.session_id != session_id:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()
    return get_cart(request, response, db)


@app.post("/api/coupons/apply")
def apply_coupon(
    data: CouponRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    code_upper = data.code.strip().upper()
    coupon = db.exec(select(Coupon).where(Coupon.code == code_upper, Coupon.active)).first()
    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon code")

    sess = db.get(UserSession, session_id)
    if sess:
        sess.applied_coupon = coupon.code
        db.add(sess)
        db.commit()

    return {"status": "applied", "coupon": coupon.code, "discount_percent": coupon.discount_percent}


@app.post("/api/checkout")
def checkout(
    data: CheckoutRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    cart = get_cart(request, response, db)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cannot checkout an empty cart")

    sess = db.get(UserSession, session_id)
    user_id = sess.user_id if sess else None

    order = Order(
        session_id=session_id,
        user_id=user_id,
        items_json=json.dumps(cart["items"]),
        subtotal=cart["subtotal"],
        discount=cart["discount"],
        total=cart["total"],
        shipping_address=data.address,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(order)

    # Clear cart items and coupon
    items = db.exec(select(CartItem).where(CartItem.session_id == session_id)).all()
    for it in items:
        db.delete(it)
    if sess:
        sess.applied_coupon = None
        db.add(sess)

    db.commit()
    db.refresh(order)

    return {
        "status": "success",
        "order": {
            "id": order.id,
            "total": order.total,
            "address": order.shipping_address,
            "created_at": order.created_at,
            "items": cart["items"],
        },
    }


@app.get("/api/account/address")
def get_address(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    sess = db.get(UserSession, session_id)
    if not sess or not sess.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.get(User, sess.user_id)
    return {"address": user.address if user else None}


@app.put("/api/account/address")
def update_address(
    data: AddressRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    sess = db.get(UserSession, session_id)
    if not sess or not sess.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.get(User, sess.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.address = data.address
    db.add(user)
    db.commit()
    return {"status": "updated", "address": user.address}


@app.get("/api/orders")
def get_orders(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)
    sess = db.get(UserSession, session_id)
    if sess and sess.user_id:
        orders = db.exec(select(Order).where(Order.user_id == sess.user_id)).all()
    else:
        orders = db.exec(select(Order).where(Order.session_id == session_id)).all()

    return [
        {
            "id": o.id,
            "total": o.total,
            "subtotal": o.subtotal,
            "discount": o.discount,
            "address": o.shipping_address,
            "created_at": o.created_at,
            "items": json.loads(o.items_json),
        }
        for o in orders
    ]


# ============================================================================
# Frontend Static Serving Fallback
# ============================================================================

if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def index_stub():
        return """<!DOCTYPE html>
<html>
<head><title>ProofQA Shop Twin</title></head>
<body>
  <h1>ProofQA Shop Twin Target Application</h1>
  <p>Backend API running on <code>/api</code>. Frontend build available in Phase 1.2.</p>
</body>
</html>"""
