from .models import StoreSettings
from django.db.models import Q


def cart_count(request):
    count = 0
    cart_items = []
    cart = None
    available_coupons = []
    try:
        from .models import Cart, Coupon
        from django.utils import timezone
        if request.user.is_authenticated:
            cart = getattr(request.user, 'cart', None)
        else:
            session_key = request.session.session_key
            if session_key:
                cart = Cart.objects.filter(session_key=session_key).first()
        if cart:
            count = cart.item_count
            cart_items = list(cart.items.select_related('product').prefetch_related('product__images').all())
        # Active coupons — use Q() to avoid .union() which breaks on SQLite
        now = timezone.now()
        available_coupons = list(
            Coupon.objects.filter(is_active=True, is_secret=False).filter(
                Q(valid_until__isnull=True) | Q(valid_until__gte=now)
            ).order_by('code')[:5]
        )
    except Exception:
        pass
    return {
        'cart_count': count,
        'cart_items': cart_items,
        'cart': cart,
        'available_coupons': available_coupons,
    }


def store_settings(request):
    try:
        settings = StoreSettings.objects.first()
    except Exception:
        # Never let a StoreSettings query (e.g. a column added by a migration
        # that hasn't been applied to this DB yet) take down every page on
        # the site — fall back to defaults instead of a 500.
        settings = None
    if not settings:
        settings = StoreSettings()
    return {'store_settings': settings}


def favorites(request):
    favorite_product_ids = set()
    favorite_count = 0
    try:
        if request.user.is_authenticated:
            from .models import Favorite
            favorite_product_ids = set(
                Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
            )
            favorite_count = len(favorite_product_ids)
    except Exception:
        pass
    return {
        'favorite_product_ids': favorite_product_ids,
        'favorite_count': favorite_count,
    }


def nav_categories(request):
    """Active categories for the mobile nav drawer's category list."""
    try:
        from .models import Category
        categories = list(Category.objects.filter(is_active=True).order_by('display_order', 'name')[:8])
    except Exception:
        categories = []
    return {'nav_categories': categories}
