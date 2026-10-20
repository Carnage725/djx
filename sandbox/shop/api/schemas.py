from datetime import datetime
from decimal import Decimal

from ninja import Schema


class ProductIn(Schema):
    name: str
    sku: str
    price: Decimal
    stock: int = 0
    is_active: bool = True
    category_id: int


class ProductOut(Schema):
    id: int
    name: str
    sku: str
    price: Decimal
    stock: int
    is_active: bool
    category_id: int


class OrderItemIn(Schema):
    product_id: int
    quantity: int = 1


class OrderIn(Schema):
    customer_id: int
    items: list[OrderItemIn]


class OrderOut(Schema):
    id: int
    customer_id: int
    status: str
    total: Decimal
    placed_at: datetime


class LoginIn(Schema):
    username: str
    password: str


class TokenOut(Schema):
    token: str


class UserOut(Schema):
    id: int
    username: str
