from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from store.models import Order
from store.views import _confirm_if_paid


class Command(BaseCommand):
    help = ('Ask Razorpay about recent orders that are not marked paid and confirm any that '
            'were actually paid (customer paid but the order never showed up).')

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=14)

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(days=opts['days'])
        qs = (Order.objects.filter(payment_status__in=['pending', 'failed'], created_at__gte=cutoff)
              .exclude(razorpay_order_id='').order_by('-created_at'))
        fixed = skipped = 0
        for order in qs:
            result = _confirm_if_paid(order)
            if result:
                fixed += 1
                self.stdout.write(self.style.SUCCESS(f'Recovered {order.order_id}'))
            elif result is None:
                skipped += 1
        self.stdout.write(f'Done. Recovered {fixed}; could not check {skipped}.')
