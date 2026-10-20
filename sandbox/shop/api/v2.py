from decimal import Decimal

from ninja import Router, Schema

from shop.models import Product

router = Router(tags=["v2"])


class ProductV2Out(Schema):
    id: int
    name: str
    price: Decimal


@router.get("/products", response=list[ProductV2Out])
def list_products_v2(request):
    """List products (v2 shape)."""
    return Product.objects.filter(is_active=True)


@router.get("/ping")
def ping(request):
    return {"ping": "pong"}
