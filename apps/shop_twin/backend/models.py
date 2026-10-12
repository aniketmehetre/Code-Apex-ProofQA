"""SQLModel database models for the shop twin."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Field, SQLModel


class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str = Field(index=True)
    price: float
    description: str = ""
    stock: int = 100
    rating: float = 4.5
    image_url: str = ""


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    address: Optional[str] = None


class UserSession(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    applied_coupon: Optional[str] = None
    created_at: float = 0.0
    last_sort: Optional[str] = None
    removed_item: bool = False


class CartItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    product_id: int = Field(foreign_key="product.id")
    quantity: int = 1


class Coupon(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    discount_percent: float
    active: bool = True


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    user_id: Optional[int] = None
    items_json: str
    subtotal: float
    discount: float
    total: float
    shipping_address: str
    created_at: str
