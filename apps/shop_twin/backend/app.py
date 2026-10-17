"""FastAPI backend for the shop twin target application."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, col, create_engine, select

from apps.shop_twin.backend import bugs
from apps.shop_twin.backend.models import (
    CartItem,
    Coupon,
    Order,
    Product,
    SQLModel,
    User,
    UserSession,
)
from proofqa.world.heldout import (
    check_d08_cart_quantity_bounds,
    check_h01_cart_quantity,
    check_h02_search_query,
    is_heldout_on,
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


class ProfileRequest(BaseModel):
    phone: Optional[str] = None
    display_name: Optional[str] = None


app = FastAPI(title="Shop Twin Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    req_log_path = os.environ.get("SHOP_TWIN_REQUEST_LOG")
    body_data = None
    if req_log_path and request.method in ("POST", "PUT", "PATCH"):
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    body_data = json.loads(body_bytes.decode("utf-8"))
                except Exception:
                    body_data = {"_raw": body_bytes.decode("utf-8", errors="ignore")[:500]}
        except Exception:
            pass

    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except HTTPException as he:
        status_code = he.status_code
        raise
    except Exception:
        status_code = 500
        raise
    finally:
        if req_log_path:
            try:
                log_entry = {
                    "timestamp": time.time(),
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    "status": status_code,
                    "body": body_data,
                }
                with open(req_log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception:
                pass


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


@app.post("/api/reset")
def reset_database():
    """Reset database to pristine seed.db without process restart."""
    engine.dispose()
    runtime_path = Path(db_url.replace("sqlite:///", ""))
    if DEFAULT_DB_PATH.exists() and runtime_path.exists():
        shutil.copyfile(DEFAULT_DB_PATH, runtime_path)
    return {"status": "reset", "db": str(runtime_path)}


@app.post("/api/register")
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    # Password validation: minimum 8 characters unless B08 is active (which accepts 4)
    min_pw_len = 4 if bugs.is_on("B08") else 8
    if len(data.password) < min_pw_len:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {min_pw_len} characters in length",
        )

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
    request: Request,
    response: Response,
    q: Optional[str] = None,
    category: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = 1,
    page_size: int = 12,
    db: Session = Depends(get_db),
):
    session_id = get_or_create_session_id(request, response, db)

    # B10: searching with a single quote returns 500
    if bugs.is_on("B10") and q and "'" in q:
        raise HTTPException(
            status_code=500,
            detail="Database error: syntax error near ''' - unescaped query parameter",
        )

    # H02: search containing double quote, percent sign, or backslash returns 500
    check_h02_search_query(q)

    statement = select(Product)

    # B06: category filter on page 2 returns items from other categories
    if category and not (bugs.is_on("B06") and page == 2):
        statement = statement.where(Product.category == category)

    if q:
        query_pattern = f"%{q}%"
        statement = statement.where(
            col(Product.name).ilike(query_pattern) | col(Product.description).ilike(query_pattern)
        )

    # Count total matching products
    all_matching = db.exec(statement).all()
    total_count = len(all_matching)

    # B05: sorting by price and then returning to default order retains price sort
    sess = db.get(UserSession, session_id) if session_id else None
    if bugs.is_on("B05") and sess and (not sort or sort in ("", "default")):
        if getattr(sess, "last_sort", None) == "price_asc":
            sort = "price_asc"

    # H03: sorting by name and then returning to default order retains name sort
    if is_heldout_on("H03") and sess and (not sort or sort in ("", "default")):
        if getattr(sess, "last_sort", None) == "name":
            sort = "name"

    # Sort
    if sort == "price_asc":
        # D06: equal-price items tie-break in reverse order
        if is_heldout_on("D06"):
            statement = statement.order_by(col(Product.price).asc(), col(Product.id).desc())
        else:
            statement = statement.order_by(col(Product.price).asc())
        if sess:
            sess.last_sort = "price_asc"
            db.add(sess)
            db.commit()
    elif sort == "price_desc":
        statement = statement.order_by(col(Product.price).desc())
    elif sort == "name":
        statement = statement.order_by(col(Product.name).asc())
        if sess:
            sess.last_sort = "name"
            db.add(sess)
            db.commit()
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
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    if not session_id:
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

    # B04: displayed total ignores the coupon discount
    if bugs.is_on("B04"):
        total = subtotal
    else:
        total = round(max(0.0, subtotal - discount), 2)

    # B03: cart badge shows one more than the API count after a removal
    badge_count = item_count
    if bugs.is_on("B03") and sess and getattr(sess, "removed_item", False):
        badge_count = item_count + 1

    return {
        "items": cart_items,
        "item_count": item_count,
        "badge_count": badge_count,
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
    # B01: POST cart with quantity 0 returns 500
    if bugs.is_on("B01") and data.quantity == 0:
        raise HTTPException(
            status_code=500,
            detail="ZeroQuantityException: Cannot allocate cart buffer with zero item quantity",
        )

    # H01: POST cart with negative quantity returns 500
    check_h01_cart_quantity(data.quantity)

    # D08: Out-of-bounds quantity returns friendly 400
    check_d08_cart_quantity_bounds(data.quantity)

    # B09: add to cart returns 500 about one request in three (seeded random)
    if bugs.is_on("B09"):
        import random
        if random.random() < 0.34:
            raise HTTPException(
                status_code=500,
                detail="LockTimeoutException: Transient concurrency lock timeout during cart insertion",
            )

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
    return get_cart(request, response, session_id=session_id, db=db)


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

    return get_cart(request, response, session_id=session_id, db=db)


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

    # Track item removal in session for B02 and B03
    sess = db.get(UserSession, session_id)
    if sess:
        sess.removed_item = True
        db.add(sess)

    db.delete(item)
    db.commit()
    return get_cart(request, response, session_id=session_id, db=db)


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
    # D05: deliberate 400 on invalid coupon
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
    sess = db.get(UserSession, session_id)

    # B02: state-dependent exception when checking out after removing an item with a coupon applied
    if bugs.is_on("B02") and sess and sess.applied_coupon and getattr(sess, "removed_item", False):
        raise HTTPException(
            status_code=500,
            detail="NullReferenceException: Coupon item binding dereference failed after line item deletion",
        )

    # H05: state-dependent exception when checking out under coupon without line item modification
    if is_heldout_on("H05") and sess and sess.applied_coupon and not getattr(sess, "removed_item", False):
        raise HTTPException(
            status_code=500,
            detail="NullReferenceException: Direct coupon checkout without line item verification failed",
        )

    cart = get_cart(request, response, session_id=session_id, db=db)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cannot checkout an empty cart")

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
        sess.removed_item = False
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

    # B07: saved address is lost after reload
    if bugs.is_on("B07"):
        return {"address": None}

    user = db.get(User, sess.user_id)
    return {"address": user.address if user else None}


@app.put("/api/account/profile")
def update_profile(
    data: ProfileRequest,
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

    # H04: profile display_name is not persisted
    if not is_heldout_on("H04"):
        if data.display_name is not None:
            user.name = data.display_name
        db.add(user)
        db.commit()

    return {"status": "success", "display_name": data.display_name}


@app.get("/api/account/profile")
def get_profile(
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

    # H04: saved profile fields are lost on retrieval
    if is_heldout_on("H04"):
        return {"display_name": None}

    return {"display_name": user.name}


# ============================================================================
# Decoys (Always On) & Adversarial Traps
# ============================================================================

_recent_calls: list[float] = []


@app.get("/api/preferences")
def get_device_preferences():
    """D07: UI preference stored on this device only."""
    return {
        "theme": "dark",
        "device_local_only": True,
        "copy": "Preferences stored on this device only. Cloud synchronization disabled by design.",
    }


@app.get("/api/rate-limit-check")
def check_rate_limiting():
    """D10: A rapidly-hit endpoint returns friendly 429, never 5xx."""
    now = time.time()
    _recent_calls.append(now)
    recent = [t for t in _recent_calls if now - t < 1.0]
    _recent_calls[:] = recent
    if is_heldout_on("D10") and len(recent) >= 5:
        raise HTTPException(
            status_code=429,
            detail="TooManyRequests: Friendly rate limit exceeded. Please retry in 1s.",
        )
    return {"status": "ok", "recent_requests": len(recent)}

@app.get("/api/decoy/not-found", response_class=HTMLResponse)
def decoy_404():
    """D01: Friendly 404 page."""
    return HTMLResponse(
        content="<html><body><h1>Friendly 404</h1><p>The page was not found, but system is healthy.</p></body></html>",
        status_code=404,
    )


@app.get("/api/telemetry/ping")
def decoy_slow_ping():
    """D03: Deliberate 2-second telemetry endpoint."""
    time.sleep(2.0)
    return {"status": "ok", "latency_ms": 2000, "telemetry": "healthy"}


@app.get("/trap/infinite-scroll", response_class=HTMLResponse)
def trap_infinite_scroll():
    """Adversarial trap: page that generates infinite content on scroll."""
    return HTMLResponse(
        content="""<html><head><title>Infinite Scroll Trap</title></head>
<body>
  <h1>Infinite Catalog</h1>
  <div id="content"></div>
  <script>
    let c = 0;
    function add() {
      for(let i=0; i<20; i++){
        c++;
        const d = document.createElement('div');
        d.innerText = 'Item ' + c;
        document.getElementById('content').appendChild(d);
      }
    }
    add();
    window.onscroll = function(){ if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 100) { add(); } };
  </script>
</body></html>"""
    )


@app.get("/trap/circular-a", response_class=HTMLResponse)
def trap_circular_a():
    """Adversarial trap: Circular link loop A."""
    return HTMLResponse(
        content="<html><body><h1>Circular Node A</h1><a href='/trap/circular-b'>Go to Node B</a></body></html>"
    )


@app.get("/trap/circular-b", response_class=HTMLResponse)
def trap_circular_b():
    """Adversarial trap: Circular link loop B."""
    return HTMLResponse(
        content="<html><body><h1>Circular Node B</h1><a href='/trap/circular-a'>Go to Node A</a></body></html>"
    )


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
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_spa(full_path: str):
        target = FRONTEND_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return HTMLResponse("<h1>Not Found</h1>", status_code=404)
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

