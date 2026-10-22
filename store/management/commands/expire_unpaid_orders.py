from django.core.management.base import BaseCommand

from store.views import expire_stale_unpaid_orders, UNPAID_ORDER_TTL_MINUTES


class Command(BaseCommand):
    help = (
        "Cancel orders that were never paid (customer closed the tab, payment "
        "failed, etc.). Confirms the order instead if Razorpay shows it was paid."
    )

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=UNPAID_ORDER_TTL_MINUTES)

    def handle(self, *args, **opts):
        n = expire_stale_unpaid_orders(minutes=opts['minutes'])
        self.stdout.write(self.style.SUCCESS(f'Processed {n} unpaid order(s).'))
