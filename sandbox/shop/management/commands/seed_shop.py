import random
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from shop.models import Category, Customer, Order, OrderItem, Product


class Command(BaseCommand):
    help = "Seed the shop with categories, products, customers and orders."

    def handle(self, *args, **options):
        rng = random.Random(42)
        categories = [
            Category.objects.get_or_create(slug=f"cat-{i}", defaults={"name": f"Category {i}"})[0]
            for i in range(10)
        ]
        products = [
            Product.objects.get_or_create(
                sku=f"SKU-{i:04d}",
                defaults={
                    "name": f"Product {i}",
                    "price": Decimal(rng.randint(500, 20000)) / 100,
                    "stock": rng.randint(0, 100),
                    "is_active": i % 8 != 0,
                    "category": rng.choice(categories),
                },
            )[0]
            for i in range(40)
        ]
        User = get_user_model()
        customers = []
        for i in range(15):
            user, _ = User.objects.get_or_create(username=f"customer{i}")
            customer, _ = Customer.objects.get_or_create(user=user, defaults={"phone": f"555-01{i:02d}"})
            customers.append(customer)
        if not Order.objects.exists():
            for _ in range(30):
                order = Order.objects.create(
                    customer=rng.choice(customers),
                    status=rng.choice(Order.Status.values),
                )
                total = Decimal(0)
                for product in rng.sample(products, rng.randint(1, 4)):
                    quantity = rng.randint(1, 3)
                    OrderItem.objects.create(
                        order=order, product=product, quantity=quantity, unit_price=product.price
                    )
                    total += product.price * quantity
                order.total = total
                order.save()
        self.stdout.write(
            f"categories={Category.objects.count()} products={Product.objects.count()} "
            f"customers={Customer.objects.count()} orders={Order.objects.count()}"
        )
