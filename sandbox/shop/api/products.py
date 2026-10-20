from django.shortcuts import get_object_or_404
from ninja import Router

from shop.api.schemas import ProductIn, ProductOut
from shop.api.security import DevTokenAuth
from shop.models import Product

router = Router(tags=["products"])
bearer = DevTokenAuth()


@router.get("", response=list[ProductOut])
def list_products(request):
    """List all products."""
    return Product.objects.all()


@router.get("/{product_id}", response=ProductOut)
def get_product(request, product_id: int):
    """Fetch one product."""
    return get_object_or_404(Product, id=product_id)


@router.post("", response=ProductOut, auth=bearer)
def create_product(request, payload: ProductIn):
    """Create a product."""
    return Product.objects.create(**payload.dict())


@router.put("/{product_id}", response=ProductOut, auth=bearer)
def update_product(request, product_id: int, payload: ProductIn):
    """Replace a product."""
    product = get_object_or_404(Product, id=product_id)
    for field, value in payload.dict().items():
        setattr(product, field, value)
    product.save()
    return product


@router.delete("/{product_id}", auth=bearer)
def delete_product(request, product_id: int):
    """Delete a product."""
    get_object_or_404(Product, id=product_id).delete()
    return {"success": True}
