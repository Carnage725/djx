from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=32, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")

    def __str__(self):
        return self.name


class ActiveProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class ActiveProduct(Product):
    objects = ActiveProductManager()

    class Meta:
        proxy = True


class Customer(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.user.get_username()


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    placed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Order {self.pk}"


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
