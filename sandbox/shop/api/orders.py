from django.db import transaction
from django.shortcuts import aget_object_or_404, get_object_or_404
from ninja import Router

from shop.api.schemas import OrderIn, OrderOut
from shop.models import Order, OrderItem, Product

router = Router(tags=["orders"])


@router.get("", response=list[OrderOut])
def list_orders(request):
    """List all orders."""
    return Order.objects.all()


@router.post("", response=OrderOut)
def create_order(request, payload: OrderIn):
    """Create an order with items."""
    with transaction.atomic():
        order = Order.objects.create(customer_id=payload.customer_id)
        total = 0
        for item in payload.items:
            product = get_object_or_404(Product, id=item.product_id)
            OrderItem.objects.create(
                order=order, product=product, quantity=item.quantity, unit_price=product.price
            )
            total += product.price * item.quantity
        order.total = total
        order.save()
    return order


@router.get("/{order_id}", response=OrderOut)
def get_order(request, order_id: int):
    """Fetch one order."""
    return get_object_or_404(Order, id=order_id)


@router.post("/{order_id}/cancel", response=OrderOut)
async def cancel_order(request, order_id: int):
    """Cancel an order (async view)."""
    order = await aget_object_or_404(Order, id=order_id)
    order.status = Order.Status.CANCELLED
    await order.asave(update_fields=["status", "updated_at"])
    return order
