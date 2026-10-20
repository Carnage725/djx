from django.contrib import admin

from shop.models import ActiveProduct, Category, Customer, Order, OrderItem, Product

for model in (Category, Product, ActiveProduct, Customer, Order, OrderItem):
    admin.site.register(model)
