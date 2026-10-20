import csv

from django.core.management.base import BaseCommand

from shop.models import Order


class Command(BaseCommand):
    help = "Export all orders as CSV to stdout."

    def handle(self, *args, **options):
        writer = csv.writer(self.stdout)
        writer.writerow(["id", "customer_id", "status", "total", "placed_at"])
        for order in Order.objects.all():
            writer.writerow([order.id, order.customer_id, order.status, order.total, order.placed_at])
