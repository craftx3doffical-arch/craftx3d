from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg, Count, Q
from django.core.cache import cache   # used for simple rate limiting
from django.utils import timezone
from datetime import timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)

# ─── Simple rate-limiter using Django's cache backend ────────────────────────
# Usage: rate_limit(request, key, max_calls, period_seconds) → True if allowed
def _rate_limit(request, key_suffix, max_calls, period):
    """Return True if the request is within the rate limit, False if exceeded."""
    uid  = request.user.pk if request.user.is_authenticated else request.META.get('REMOTE_ADDR', 'anon')
    key  = f'rl:{key_suffix}:{uid}'
    count = cache.get(key, 0)
    if count >= max_calls:
        return False
    cache.set(key, count + 1, timeout=period)
    return True

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 MB
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif'}
ALLOWED_IMAGE_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic', 'image/heif'}


def _validate_uploaded_image(f):
    """Returns (is_valid, error_message). Guards customization photo uploads
    against oversized files and non-image content disguised with an image
    extension."""
    if f.size > MAX_UPLOAD_SIZE:
        return False, f'"{f.name}" is too large (max 8 MB).'
    ext = os.path.splitext(f.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f'"{f.name}" isn\'t a supported image type.'
    content_type = getattr(f, 'content_type', '') or ''
    if content_type and content_type.lower() not in ALLOWED_IMAGE_CONTENT_TYPES:
        return False, f'"{f.name}" isn\'t a supported image type.'
    return True, ''

from .models import (
    Product, Category, Review, Cart, CartItem, Order, OrderItem,
    OrderItemImage, HelpFAQ, Enquiry, Banner, AboutPageContent,
    StoreSettings, UserProfile, Coupon, PackagingType, ProductImage, Favorite,
    SavedAddress, INDIAN_STATES,
)
from .forms import CustomerRegistrationForm, ReviewForm, EnquiryForm, CustomEnquiryForm, CheckoutForm, normalize_phone


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
        return cart


# ─── HOME ────────────────────────────────────────────────────────────────────
def home(request):
    banners = Banner.objects.filter(is_active=True).order_by('display_order')
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    categories = Category.objects.filter(is_active=True).prefetch_related('images').distinct()
    all_products = Product.objects.filter(is_active=True).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__status=Review.STATUS_APPROVED)),
        rating_count=Count('reviews', filter=Q(reviews__status=Review.STATUS_APPROVED)),
    )[:12]
    best_reviews = Review.objects.filter(
        status=Review.STATUS_APPROVED, featured_on_home=True
    ).select_related('product').order_by('-created_at')[:8]
    # Store-wide aggregate rating shown in the "Loved by our customers" header
    approved_reviews = Review.objects.filter(status=Review.STATUS_APPROVED)
    reviews_summary = approved_reviews.aggregate(avg=Avg('rating'), total=Count('id'))
    # Flatten all banner images into a single swipeable list
    banner_slides = []
    for b in banners:
        for img in b.all_images:
            banner_slides.append({
                'url': img.url if hasattr(img, 'url') else str(img),
                'link': b.effective_link,
                'cta_text': b.cta_text or 'Shop Now',
            })
    context = {
        'banners': banners,
        'banner_slides': banner_slides,
        'featured_products': featured_products,
        'categories': categories,
        'all_products': all_products,
        'best_reviews': best_reviews,
        'reviews_avg': round(reviews_summary['avg'] or 0, 2),
        'reviews_total': reviews_summary['total'] or 0,
    }
    return render(request, 'store/home.html', context)


# ─── PRODUCTS ────────────────────────────────────────────────────────────────
def products(request):
    qs = Product.objects.filter(is_active=True).prefetch_related('images')
    category_slug = request.GET.get('category')
    search = request.GET.get('q', '')
    # "SORT BY" default is staff-configurable from the manage portal
    # (Settings → Products page default sort) — customers can still change
    # it, but the dropdown opens on whatever the staff picked.
    try:
        store_settings = StoreSettings.objects.first()
        default_sort = store_settings.default_sort if store_settings else 'newest'
    except Exception:
        # DB not migrated yet for the default_sort column, or no row exists —
        # never let this take the whole products page down.
        default_sort = 'newest'
    sort = request.GET.get('sort') or default_sort
    bestseller = request.GET.get('bestseller')

    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if bestseller:
        qs = qs.filter(is_bestseller=True)
    if search:
        qs = qs.filter(name__icontains=search)

    # Star rating + review count, used by the product card badge on every listing
    qs = qs.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__status=Review.STATUS_APPROVED)),
        rating_count=Count('reviews', filter=Q(reviews__status=Review.STATUS_APPROVED)),
    )

    if sort == 'price_low':
        qs = qs.order_by('base_price')
    elif sort == 'price_high':
        qs = qs.order_by('-base_price')
    elif sort == 'popular':
        qs = qs.order_by('-rating_count', '-avg_rating')
    else:
        qs = qs.order_by('-created_at')

    categories = Category.objects.filter(is_active=True)
    context = {
        'products': qs,
        'categories': categories,
        'selected_category': category_slug,
        'search': search,
        'sort': sort,
        'bestseller_filter': bool(bestseller),
    }
    return render(request, 'store/products.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    reviews = product.reviews.filter(status=Review.STATUS_APPROVED)
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    rating_counts = {i: reviews.filter(rating=i).count() for i in range(1, 6)}
    related = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk).annotate(
        r_avg=Avg('reviews__rating', filter=Q(reviews__status=Review.STATUS_APPROVED)),
        r_count=Count('reviews', filter=Q(reviews__status=Review.STATUS_APPROVED)),
    )[:4]
    context = {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'rating_counts': rating_counts,
        'related': related,
        'images': product.images.all(),
        'can_review': _can_review(request.user, product),
        'already_reviewed': _already_reviewed(request.user, product),
    }
    return render(request, 'store/product_detail.html', context)


# ─── REVIEWS ─────────────────────────────────────────────────────────────────
# A customer can review a product once their order has shipped or been delivered.
REVIEWABLE_ORDER_STATUSES = ("shipped", "delivered")


def _reviewable_products(user):
    """Products from this customer's shipped/delivered orders that they have not
    reviewed yet — only real buyers can review."""
    if not user.is_authenticated:
        return Product.objects.none()
    bought = OrderItem.objects.filter(
        order__user=user, order__status__in=REVIEWABLE_ORDER_STATUSES, product__isnull=False
    ).values_list('product_id', flat=True)
    reviewed = Review.objects.filter(user=user, product__isnull=False).values_list('product_id', flat=True)
    return Product.objects.filter(pk__in=list(bought)).exclude(pk__in=list(reviewed))


def _can_review(user, product):
    return _reviewable_products(user).filter(pk=product.pk).exists()


def _already_reviewed(user, product):
    return user.is_authenticated and Review.objects.filter(user=user, product=product).exists()


def reviews_page(request):
    reviews = Review.objects.filter(status=Review.STATUS_APPROVED).order_by('-created_at')
    sort = request.GET.get('sort', 'newest')
    if sort == 'highest':
        reviews = reviews.order_by('-rating', '-created_at')
    elif sort == 'lowest':
        reviews = reviews.order_by('rating', '-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    rating_counts = {i: reviews.filter(rating=i).count() for i in range(1, 6)}
    total = reviews.count()
    context = {
        'reviews': reviews,
        'avg_rating': avg_rating,
        'rating_counts': rating_counts,
        'total_reviews': total,
        'sort': sort,
    }
    return render(request, 'store/reviews.html', context)


@login_required
def write_review(request):
    """Only customers who RECEIVED a product can review it (one review per
    product). Reached from My Orders → order → "Write a review"."""
    products = _reviewable_products(request.user)
    if not products.exists():
        messages.info(request, 'You can review a product once your order has shipped. Check My Orders after you place an order.')
        return redirect('store:my_orders')

    def _render(form):
        return render(request, 'store/write_review.html', {'form': form, 'products': products})

    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product_id_int = int(request.POST.get('product', '').strip())
            except (ValueError, TypeError):
                product_id_int = 0
            if not products.filter(pk=product_id_int).exists():
                messages.error(request, 'Please choose a product from your orders.')
                return _render(form)

            rating = form.cleaned_data.get('rating')
            if not isinstance(rating, int) or not (1 <= rating <= 5):
                messages.error(request, 'Rating must be between 1 and 5 stars.')
                return _render(form)

            if len(form.cleaned_data.get('body', '')) > 2000:
                messages.error(request, 'Review text must be 2000 characters or fewer.')
                return _render(form)

            review = form.save(commit=False)
            review.user = request.user
            review.status = Review.STATUS_PENDING
            review.product_id = product_id_int
            try:
                review.save()
            except Exception as e:
                logger.exception('Review save failed (product=%s, has_photo=%s)', product_id_int, bool(request.FILES.get('photo')))
                messages.error(
                    request,
                    "We couldn't publish your review just now — this usually "
                    "means the photo upload failed. Please try again, or "
                    "submit without a photo."
                )
                return _render(form)
            messages.success(request, 'Thanks for your feedback! Your review will appear once our team has reviewed it.')
            return redirect('store:my_orders')
        return _render(form)

    initial = {'reviewer_name': request.user.get_full_name() or ''}
    return _render(ReviewForm(initial=initial))


# ─── ABOUT ───────────────────────────────────────────────────────────────────
def about(request):
    content = AboutPageContent.objects.first()
    if not content:
        content = AboutPageContent()
    return render(request, 'store/about.html', {'content': content})


# ─── HELP ────────────────────────────────────────────────────────────────────
def help_support(request):
    faqs = HelpFAQ.objects.filter(is_active=True)
    if request.method == 'POST':
        form = EnquiryForm(request.POST, request.FILES)
        if form.is_valid():
            enquiry = form.save()
            messages.success(request, "Your message has been sent! We'll respond within 24 hours.")
            return redirect('store:help')
    else:
        form = EnquiryForm()
        if request.user.is_authenticated:
            form.initial = {
                'full_name': request.user.get_full_name(),
                'email': request.user.email,
                'phone': getattr(request.user, 'profile', None) and request.user.profile.phone or '',
            }
    return render(request, 'store/help.html', {'form': form, 'faqs': faqs})


# ─── CUSTOMIZATION ENQUIRY ───────────────────────────────────────────────────
def custom_enquiry(request):
    """Public form: ask for a customised version of a product (or a custom idea)."""
    if request.method == 'POST':
        form = CustomEnquiryForm(request.POST, request.FILES)
        if not _rate_limit(request, 'custom_enquiry', 5, 600):
            messages.error(request, 'Too many requests. Please try again in a few minutes.')
        elif form.is_valid():
            form.save()
            messages.success(request, "Thanks! Your customization request has been sent. We'll contact you within 24 hours.")
            return redirect('store:custom_enquiry')
    else:
        initial = {}
        pid = request.GET.get('product', '')
        if pid.isdigit():
            initial['product'] = int(pid)
        if request.user.is_authenticated:
            initial['full_name'] = request.user.get_full_name()
            initial['email'] = request.user.email
            try:
                initial['phone'] = request.user.profile.phone
            except Exception:
                pass
        form = CustomEnquiryForm(initial=initial)
    return render(request, 'store/custom_enquiry.html', {'form': form})


# ─── CART ────────────────────────────────────────────────────────────────────
def cart(request):
    cart = get_or_create_cart(request)
    store_s = StoreSettings.objects.first()
    context = {
        'cart': cart,
        'cart_items': cart.items.select_related(
            'product', 'selected_packaging'
        ).prefetch_related('product__images').all(),
        'store_settings': store_s,
    }
    return render(request, 'store/cart.html', context)


def cart_drawer_refresh(request):
    """Re-renders just the mini-cart drawer's inner content. Used after Add
    to Cart so the drawer can be opened with fresh data via AJAX instead of
    reloading the whole page (a full reload was racing with — and silently
    breaking — the drawer if the customer tapped the cart icon right after)."""
    return render(request, 'store/_cart_drawer_content.html', {})


@require_POST
def add_to_cart(request, product_id):
    # Handle auth manually so AJAX gets JSON not a redirect
    if not request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'need_login': True, 'redirect': f'/accounts/login/?next={request.path}'}, status=401)
        return redirect(f'/accounts/login/?next={request.path}')

    # Rate limit: 30 add-to-cart actions per minute per user
    if not _rate_limit(request, 'add_cart', 30, 60):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'rate_limited', 'message': 'Too many requests. Please slow down.'}, status=429)
        messages.error(request, 'Too many requests. Please wait a moment.')
        return redirect('store:products')

    # Validate product_id is a positive integer
    try:
        product_id = int(product_id)
        if product_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Invalid product.'}, status=400)

    product = get_object_or_404(Product, pk=product_id, is_active=True)

    # Out of stock check
    if not product.is_in_stock:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'out_of_stock', 'message': 'This product is currently out of stock.'})
        messages.error(request, 'Sorry, this product is currently out of stock.')
        return redirect('store:product_detail', slug=product.slug)

    cart = get_or_create_cart(request)
    quantity = max(1, int(request.POST.get('quantity', 1) or 1))

    # Enforce stock limit — reject instead of silently capping. Skipped
    # entirely for products with inventory tracking turned off.
    existing_qty = sum(
        item.quantity for item in cart.items.filter(product=product)
    )
    if product.track_inventory:
        available = product.available_stock - existing_qty
        if available <= 0:
            msg = f'Only {product.stock} in stock and you already have {existing_qty} in your cart.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'out_of_stock', 'message': msg})
            messages.warning(request, msg)
            return redirect('store:product_detail', slug=product.slug)

        if quantity > available:
            msg = f'Only {available} more available (you have {existing_qty} in cart, stock is {product.stock}).'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'insufficient_stock', 'message': msg})
            messages.warning(request, msg)
            return redirect('store:product_detail', slug=product.slug)

    # Older non-JSON customization types: both require an uploaded photo.
    if product.customization_type in ('miniature', 'photo') and not request.FILES.get('custom_photo'):
        message = 'Please upload a photo to continue.' if product.customization_type == 'photo' else 'Please upload a reference photo to continue.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': message}, status=400)
        messages.error(request, message)
        return redirect('store:product_detail', slug=product.slug)

    # Read builder config from PRODUCT DB (not POST — customer form has no hidden builder input)
    builder_config = product.customization_data or {}

    # ── Server-side enforcement of required customization fields ───────────
    # The storefront JS already blocks/highlights missing required fields, but
    # that is client-side only. Re-validate here so a request that skips the
    # JS (disabled JS, direct POST, etc.) can never add an incomplete
    # customization to the cart.
    if builder_config and isinstance(builder_config, dict):
        sections = builder_config.get('sections', {})
        section_order = builder_config.get('section_order', list(sections.keys()))
        missing = []

        for key in section_order:
            sec = sections.get(key, {})
            if not isinstance(sec, dict) or not sec.get('enabled'):
                continue

            if key == 'photo':
                for i, slot in enumerate(sec.get('slots', [])):
                    if slot.get('required') and not request.FILES.get(f'custom_photo_{i}'):
                        missing.append(slot.get('label') or f'Photo {i + 1}')

            elif key == 'text_fields':
                for i, field in enumerate(sec.get('fields', [])):
                    if field.get('required') and not request.POST.get(f'custom_field_{i}', '').strip():
                        missing.append(field.get('label') or f'Field {i + 1}')

            elif key == 'select_model':
                options = sec.get('options') or []
                if len(options) > 0 and not request.POST.get('custom_model', '').strip():
                    missing.append(sec.get('title') or 'Model selection')

            elif key == 'personalisation':
                if request.POST.get('personalisation', 'no') == 'yes':
                    if not request.POST.get('pers_line_0', '').strip():
                        missing.append((sec.get('title') or 'Personalisation') + ' text')

        if missing:
            message = 'Please complete: ' + ', '.join(missing)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': message, 'missing_fields': missing}, status=400)
            messages.error(request, message)
            return redirect('store:product_detail', slug=product.slug)

    # Build clean human-readable choices from customer's submitted values
    customer_choices = {}
    builder_size_extra = 0
    if builder_config and isinstance(builder_config, dict):
        sections = builder_config.get('sections', {})
        section_order = builder_config.get('section_order', list(sections.keys()))

        for key in section_order:
            sec = sections.get(key, {})
            if not isinstance(sec, dict) or not sec.get('enabled'):
                continue

            if key == 'text_fields':
                for i, field in enumerate(sec.get('fields', [])):
                    val = request.POST.get(f'custom_field_{i}', '').strip()
                    if val:
                        customer_choices[field.get('label') or f'Field {i+1}'] = val

            elif key == 'colour_combos':
                val = request.POST.get('custom_colour_combo', '').strip()
                if val:
                    customer_choices[sec.get('title') or 'Colour'] = val

            elif key == 'text_colours':
                for i, slot in enumerate(sec.get('slots', [])):
                    val = request.POST.get(f'custom_tc_{i}', '').strip()
                    if val:
                        customer_choices[slot.get('title') or f'Text Colour {i+1}'] = val

            elif key == 'size_options':
                val = request.POST.get('custom_size', '').strip()
                _valid_sizes = [sz.get('label') for sz in sec.get('sizes', []) if sz.get('label')]
                if _valid_sizes and val not in _valid_sizes:
                    _msg = 'Please select a size.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'message': _msg}, status=400)
                    messages.error(request, _msg)
                    return redirect('store:product_detail', slug=product.slug)
                if val:
                    customer_choices[sec.get('title') or 'Size'] = val
                    # This is the JSON-builder size selector (distinct from the
                    # older separate ProductSize model below) — its extra price
                    # lives inline in the builder JSON, keyed by label.
                    for sz in sec.get('sizes', []):
                        if sz.get('label') == val:
                            try:
                                from decimal import Decimal, InvalidOperation
                                builder_size_extra = Decimal(str(sz.get('extra_price') or 0))
                            except (TypeError, ValueError, InvalidOperation):
                                builder_size_extra = 0
                            break

            elif key == 'pack_options':
                val = request.POST.get('custom_pack', '').strip()
                if val:
                    customer_choices['Pack Size'] = val

            elif key == 'select_model':
                val = request.POST.get('custom_model', '').strip()
                if val:
                    customer_choices[sec.get('title') or 'Model'] = val

            elif key == 'suggestion_box':
                val = request.POST.get('custom_suggestion', '').strip()
                if val:
                    customer_choices[sec.get('title') or 'Special Instructions'] = val

            elif key == 'photo':
                # NOTE: actual file saving + the single choices entry for each photo
                # happens later in the saved_photos block below (using request.FILES).
                # Do NOT write anything here — doing so previously caused each photo
                # to appear twice in the invoice under two different label formats.
                pass

            elif key == 'personalisation':
                pers = request.POST.get('personalisation', 'no')
                if pers == 'yes':
                    pers_type = request.POST.get('pers_type', 'text')
                    if pers_type != 'logo':
                        lines = []
                        for i in range(sec.get('max_lines', 3)):
                            line = request.POST.get(f'pers_line_{i}', '').strip()
                            if line:
                                lines.append(line)
                        if lines:
                            customer_choices[sec.get('title') or 'Personalisation'] = ' | '.join(lines)
                        font = request.POST.get('pers_font', '').strip()
                        if font:
                            customer_choices['Font'] = font
                        font_size = request.POST.get('pers_size', '').strip()
                        if font_size:
                            customer_choices['Font Size'] = font_size
                    # Logo file itself is handled by the saved_photos block below
                    # (matches 'pers_logo' in request.FILES) — not duplicated here.

    customization_data = {'choices': customer_choices}

    unit_price = product.base_price + builder_size_extra
    size_label = request.POST.get('selected_size', '')
    if size_label:
        size_opt = product.sizes.filter(label=size_label).first()
        if size_opt:
            unit_price += size_opt.extra_price

    cart_item = CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=quantity,
        unit_price=unit_price,
        customization_data=customization_data,
        selected_size=size_label,
        parcel_charge=product.parcel_charge_price if product.show_parcel_charge else 0,
    )

    # Save any uploaded customization photos/logo files to disk.
    # These become OrderItemImage records at checkout (the single source of truth
    # for displaying uploaded files on the invoice) — they are NOT duplicated into
    # the 'choices' text dict.
    from django.core.files.storage import default_storage
    import os as _os

    # Build a map of form field name → human-readable label, using the admin's
    # configured labels wherever available (falls back to a sensible default).
    field_labels = {}
    if builder_config and isinstance(builder_config, dict):
        sections = builder_config.get('sections', {})
        photo_sec = sections.get('photo', {})
        if photo_sec.get('enabled'):
            for i, slot in enumerate(photo_sec.get('slots', [])):
                field_labels[f'custom_photo_{i}'] = slot.get('label') or f'Photo {i+1}'
        pers_sec = sections.get('personalisation', {})
        if pers_sec.get('enabled'):
            field_labels['pers_logo'] = (pers_sec.get('title') or 'Personalisation') + ' Logo'
    field_labels.setdefault('custom_logo', 'Logo')

    saved_photos = {}
    for file_key, upload_file in request.FILES.items():
        if file_key.startswith('custom_photo') or file_key in ('custom_logo', 'pers_logo'):
            valid, err = _validate_uploaded_image(upload_file)
            if not valid:
                cart_item.delete()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': err}, status=400)
                messages.error(request, err)
                return redirect('store:product_detail', slug=product.slug)
            try:
                # Sanitize the filename: strip any path components and non-
                # alphanumeric characters so it can't be used for path
                # traversal or to overwrite unrelated files.
                base_name = os.path.basename(upload_file.name).replace(' ', '_')
                safe_name = ''.join(c for c in base_name if c.isalnum() or c in ('.', '_', '-')) or 'photo'
                file_path = default_storage.save(
                    f'cart_custom/item_{cart_item.pk}/{file_key}_{safe_name}',
                    upload_file
                )
                label = field_labels.get(file_key) or file_key.replace('custom_photo_', 'Photo ').replace('_', ' ').title()
                saved_photos[file_key] = {
                    'path': file_path,
                    'url': default_storage.url(file_path),
                    'name': upload_file.name,
                    'label': label,
                }
            except Exception:
                pass
    if saved_photos:
        customization_data['uploaded_photos'] = saved_photos
        cart_item.customization_data = customization_data
        cart_item.save()
    elif customization_data:
        cart_item.customization_data = customization_data
        cart_item.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.item_count,
            'checkout_url': reverse('store:checkout'),
            'product_name': product.name,
            'product_price': float(unit_price),
            'cart_subtotal': float(cart.subtotal),
            'cart_parcel_charge': float(cart.parcel_charge_total),
            'cart_total': float(cart.total),
            'image_url': product.main_image.image.url if product.main_image else '',
        })
    messages.success(request, f'✅ {product.name} added to cart!')
    return redirect('store:product_detail', slug=product.slug)


@require_POST
def update_cart(request, item_id):
    cart = get_or_create_cart(request)
    action = request.POST.get('action')
    item = CartItem.objects.filter(pk=item_id, cart=cart).first()
    if item is None:
        # Already removed (double tap, stale drawer, another tab). Treat as
        # success and return the real cart so the page re-syncs instead of
        # failing silently with a 404.
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            cart.refresh_from_db()
            return JsonResponse({
                'success': True, 'already_removed': True, 'quantity': 0, 'item_total': 0,
                'cart_subtotal': float(cart.subtotal),
                'cart_parcel_charge': float(cart.parcel_charge_total),
                'cart_total': float(cart.total), 'cart_count': cart.item_count,
            })
        return redirect('store:cart')
    removed = False
    if action == 'increase':
        item.quantity += 1
        item.save()
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()      # "−" on quantity 1 removes the line
            removed = True
    elif action == 'remove':
        item.delete()
        removed = True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart.refresh_from_db()
        return JsonResponse({
            'success': True,
            'removed': removed,
            'quantity': 0 if removed else item.quantity,
            'item_total': 0 if removed else float(item.total_price),
            'cart_subtotal': float(cart.subtotal),
            'cart_parcel_charge': float(cart.parcel_charge_total),
            'cart_total': float(cart.total),
            'cart_count': cart.item_count,
        })
    return redirect('store:cart')


@require_POST
def apply_coupon(request):
    cart = get_or_create_cart(request)
    code = request.POST.get('coupon_code', '').strip().upper()
    try:
        coupon = Coupon.objects.get(code=code)
        valid, msg = coupon.is_valid()
        if valid:
            if cart.subtotal >= coupon.min_order_value:
                cart.coupon = coupon
                cart.save()
                discount = coupon.get_discount_amount(cart.subtotal)
                display_code = '🔒 Secret' if coupon.is_secret else coupon.code
                return JsonResponse({
                    'success': True,
                    'message': f'🎉 Coupon applied! You save ₹{discount:.0f}',
                    'code': display_code,
                    'discount': float(discount),
                    'discount_amount': float(discount),
                    'subtotal': float(cart.subtotal),
                    'total': float(cart.total),
                })
            else:
                return JsonResponse({'success': False, 'message': f'Min order ₹{coupon.min_order_value:.0f} required'})
        else:
            return JsonResponse({'success': False, 'message': msg})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid coupon code'})


@require_POST
def remove_coupon(request):
    cart = get_or_create_cart(request)
    cart.coupon = None
    cart.save()
    return JsonResponse({
        'success': True,
        'subtotal': float(cart.subtotal),
        'total': float(cart.total),
    })


@require_POST
def save_notes(request):
    cart = get_or_create_cart(request)
    cart.notes = request.POST.get('notes', '')
    cart.save()
    return JsonResponse({'success': True})


@require_POST
def toggle_gift_wrap(request):
    cart = get_or_create_cart(request)
    cart.gift_wrap = not cart.gift_wrap
    cart.save()
    return JsonResponse({'success': True, 'gift_wrap': cart.gift_wrap, 'total': float(cart.total), 'gift_wrap_price': float(cart.gift_wrap_price)})


# ─── SAVED ADDRESS VIEWS ─────────────────────────────────────────────────────
@login_required
def manage_addresses(request):
    """List all saved delivery addresses for the logged-in user."""
    addresses = request.user.saved_addresses.all()
    return render(request, 'store/addresses.html', {
        'addresses': addresses,
        'indian_states': INDIAN_STATES,
    })


@login_required
def add_address(request):
    """Add a new saved delivery address."""
    if request.method == 'POST':
        addr = SavedAddress(
            user=request.user,
            full_name=request.POST.get('full_name', '').strip(),
            phone=request.POST.get('phone', '').strip(),
            alternate_phone=request.POST.get('alternate_phone', '').strip(),
            address_line1=request.POST.get('address_line1', '').strip(),
            address_line2=request.POST.get('address_line2', '').strip(),
            landmark=request.POST.get('landmark', '').strip(),
            city=request.POST.get('city', '').strip(),
            state=request.POST.get('state', '').strip(),
            pincode=request.POST.get('pincode', '').strip(),
            is_default=request.POST.get('is_default') == 'on',
        )
        addr.save()
        next_url = request.POST.get('next') or request.GET.get('next') or ''
        messages.success(request, 'Address saved!')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('store:manage_addresses')

    try:
        initial_phone = request.user.profile.phone
    except Exception:
        initial_phone = ''

    return render(request, 'store/address_form.html', {
        'action': 'add',
        'initial_name': request.user.get_full_name(),
        'initial_phone': initial_phone,
        'initial_email': request.user.email,
        'indian_states': INDIAN_STATES,
        'next': request.GET.get('next', ''),
    })


@login_required
def edit_address(request, address_id):
    """Edit an existing saved address."""
    address = get_object_or_404(SavedAddress, id=address_id, user=request.user)
    if request.method == 'POST':
        address.full_name = request.POST.get('full_name', '').strip()
        address.phone = request.POST.get('phone', '').strip()
        address.alternate_phone = request.POST.get('alternate_phone', '').strip()
        address.address_line1 = request.POST.get('address_line1', '').strip()
        address.address_line2 = request.POST.get('address_line2', '').strip()
        address.landmark = request.POST.get('landmark', '').strip()
        address.city = request.POST.get('city', '').strip()
        address.state = request.POST.get('state', '').strip()
        address.pincode = request.POST.get('pincode', '').strip()
        address.is_default = request.POST.get('is_default') == 'on'
        address.save()
        next_url = request.POST.get('next') or request.GET.get('next') or ''
        messages.success(request, 'Address updated!')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect('store:manage_addresses')

    return render(request, 'store/address_form.html', {
        'action': 'edit',
        'address': address,
        'indian_states': INDIAN_STATES,
        'next': request.GET.get('next', ''),
    })


@login_required
def delete_address(request, address_id):
    """Delete a saved address (POST only)."""
    address = get_object_or_404(SavedAddress, id=address_id, user=request.user)
    if request.method == 'POST':
        address.delete()
        return JsonResponse({'success': True})
    return redirect('store:manage_addresses')


@login_required
def set_default_address(request, address_id):
    """Mark a saved address as default."""
    address = get_object_or_404(SavedAddress, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    return JsonResponse({'success': True})


def pincode_lookup(request, pincode):
    """Look up Indian city/state from a 6-digit pincode via the free postal API."""
    import urllib.request as _req
    import json as _json
    try:
        url = f'https://api.postalpincode.in/pincode/{pincode}'
        with _req.urlopen(url, timeout=4) as resp:
            data = _json.loads(resp.read())
        if data and data[0].get('Status') == 'Success':
            offices = data[0].get('PostOffice', [])
            if offices:
                po = offices[0]
                return JsonResponse({
                    'success': True,
                    'city': po.get('District') or po.get('Block') or '',
                    'state': po.get('State', ''),
                    'district': po.get('District', ''),
                })
    except Exception:
        pass
    return JsonResponse({'success': False, 'city': '', 'state': ''})


# ─── CHECKOUT ────────────────────────────────────────────────────────────────
@login_required
def checkout(request):
    # Release anything this customer left unpaid earlier (closed tab, etc.)
    # so stock and their cart are back before we look at the cart.
    expire_stale_unpaid_orders(request=request, user=request.user)
    cart = get_or_create_cart(request)
    if cart.item_count == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')
    store_s = StoreSettings.objects.first()
    saved_addresses = request.user.saved_addresses.all()

    if request.method == 'POST':
        # Never create an order we cannot collect payment for.
        if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
            messages.error(request, 'Online payment is temporarily unavailable, so your order was not placed. Please try again shortly or contact support.')
            return redirect('store:checkout')
        # ── Option A: customer picked a saved address ──
        selected_id = request.POST.get('selected_address_id', '').strip()
        if selected_id:
            try:
                addr = SavedAddress.objects.get(id=selected_id, user=request.user)
                combined = addr.address_line1
                if addr.address_line2:
                    combined += ', ' + addr.address_line2
                if addr.landmark:
                    combined += ', Near ' + addr.landmark
                cleaned = {
                    'full_name': addr.full_name,
                    'phone': addr.phone,
                    'alternate_phone': addr.alternate_phone,
                    'email': request.user.email or '',
                    'address': combined,
                    'city': addr.city,
                    'state': addr.state,
                    'pincode': addr.pincode,
                }
            except SavedAddress.DoesNotExist:
                messages.error(request, 'Selected address not found. Please try again.')
                return redirect('store:checkout')
        else:
            # ── Option B: customer filled in the address form ──
            form = CheckoutForm(request.POST)
            if not form.is_valid():
                context = {
                    'cart': cart, 'form': form, 'store_settings': store_s,
                    'saved_addresses': saved_addresses, 'indian_states': INDIAN_STATES,
                    'payment_configured': bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
                }
                return render(request, 'store/checkout.html', context)
            cleaned = form.cleaned_data
            # Optionally save this address for future
            if request.POST.get('save_address') == 'on':
                SavedAddress.objects.create(
                    user=request.user,
                    full_name=cleaned['full_name'],
                    phone=cleaned['phone'],
                    alternate_phone=cleaned.get('alternate_phone', ''),
                    address_line1=cleaned['address_line1'],
                    address_line2=cleaned.get('address_line2', ''),
                    landmark=cleaned.get('landmark', ''),
                    city=cleaned['city'],
                    state=cleaned['state'],
                    pincode=cleaned['pincode'],
                    is_default=not saved_addresses.exists(),
                )

        # ── Stock check ──────────────────────────────────────────────────────
        from django.db import transaction
        from django.db.models import F
        out_of_stock = []
        for item in cart.items.select_related('product').all():
            if item.product.track_inventory and item.quantity > item.product.stock:
                out_of_stock.append((item.product.name, item.product.stock))
        if out_of_stock:
            for name, available in out_of_stock:
                if available <= 0:
                    messages.error(request, f'"{name}" just went out of stock.')
                else:
                    messages.error(request, f'Only {available} left of "{name}".')
            return redirect('store:cart')

        # ── Create order ─────────────────────────────────────────────────────
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                full_name=cleaned['full_name'],
                phone=cleaned['phone'],
                alternate_phone=cleaned.get('alternate_phone', ''),
                email=cleaned.get('email') or request.user.email or '',
                address=cleaned['address'],
                city=cleaned['city'],
                state=cleaned['state'],
                pincode=cleaned['pincode'],
                payment_method='online',
                status='awaiting_payment',
                payment_status='pending',
                subtotal=cart.subtotal,
                discount_amount=cart.discount_amount,
                gift_wrap=cart.gift_wrap,
                gift_wrap_price=cart.gift_wrap_price if cart.gift_wrap else 0,
                parcel_charge_total=cart.parcel_charge_total,
                total=cart.total,
                coupon_code=cart.coupon.code if cart.coupon else '',
                notes=cart.notes,
            )
            for item in cart.items.all():
                cust_data = dict(item.customization_data or {})
                if hasattr(item, 'selected_size') and item.selected_size:
                    cust_data['selected_size'] = item.selected_size
                order_item = OrderItem.objects.create(
                    order=order, product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity, unit_price=item.unit_price,
                    parcel_charge=item.parcel_charge,
                    customization_data=cust_data,
                )
                if item.product.track_inventory:
                    Product.objects.filter(pk=item.product_id).update(stock=F('stock') - item.quantity)
                from django.core.files.storage import default_storage
                from django.core.files.base import File
                import os as _os
                uploaded_photos = item.customization_data.get('uploaded_photos', {})
                for slot_key, photo_info in uploaded_photos.items():
                    file_path = photo_info.get('path', '')
                    if file_path and default_storage.exists(file_path):
                        try:
                            with default_storage.open(file_path, 'rb') as f:
                                fname = _os.path.basename(file_path)
                                OrderItemImage.objects.create(
                                    order_item=order_item,
                                    image=File(f, name=fname),
                                    slot_label=photo_info.get('label') or slot_key,
                                )
                        except Exception:
                            pass
            if cart.coupon:
                cart.coupon.used_count += 1
                cart.coupon.save()
            cart.items.all().delete()
            cart.coupon = None
            cart.gift_wrap = False
            cart.notes = ''
            cart.save()
        return redirect('store:payment', order_id=order.order_id)

    # ── GET ──────────────────────────────────────────────────────────────────
    initial = {'full_name': request.user.get_full_name(), 'email': request.user.email}
    try:
        initial['phone'] = request.user.profile.phone
    except Exception:
        pass
    form = CheckoutForm(initial=initial)
    context = {
        'cart': cart,
        'form': form,
        'store_settings': store_s,
        'saved_addresses': saved_addresses,
        'indian_states': INDIAN_STATES,
        'payment_configured': bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
    }
    return render(request, 'store/checkout.html', context)


@login_required
def _old_checkout_unused(request):
    cart = get_or_create_cart(request)
    if cart.item_count == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('store:cart')
    store_s = StoreSettings.objects.first()
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Re-validate stock at the moment of purchase — a product's stock can
            # change between "add to cart" and checkout (other customers buying,
            # admin adjusting stock, etc.), so we check again right before charging.
            from django.db import transaction
            from django.db.models import F

            out_of_stock = []
            for item in cart.items.select_related('product').all():
                if item.product.track_inventory and item.quantity > item.product.stock:
                    out_of_stock.append((item.product.name, item.product.stock))

            if out_of_stock:
                for name, available in out_of_stock:
                    if available <= 0:
                        messages.error(request, f'"{name}" just went out of stock. Please remove it from your cart to continue.')
                    else:
                        messages.error(request, f'Only {available} left of "{name}". Please update the quantity in your cart.')
                return redirect('store:cart')

            data = form.cleaned_data
            with transaction.atomic():
                # Order is created now (so stock can be reserved), but payment
                # is NOT complete yet — payment_status stays 'pending' until
                # Razorpay confirms the payment in payment_verify(). If payment
                # fails or is abandoned, stock is restored via order.restore_stock().
                order = Order.objects.create(
                    user=request.user,
                    full_name=data['full_name'],
                    phone=data['phone'],
                    alternate_phone=data.get('alternate_phone', ''),
                    email=data['email'],
                    address=data['address'],
                    city=data['city'],
                    state=data['state'],
                    pincode=data['pincode'],
                    payment_method='online',
                    status='awaiting_payment',
                    payment_status='pending',
                    subtotal=cart.subtotal,
                    discount_amount=cart.discount_amount,
                    gift_wrap=cart.gift_wrap,
                    gift_wrap_price=cart.gift_wrap_price if cart.gift_wrap else 0,
                    total=cart.total,
                    coupon_code=cart.coupon.code if cart.coupon else '',
                    notes=cart.notes,
                )
                for item in cart.items.all():
                    # Merge selected_size into customization_data for storage
                    cust_data = dict(item.customization_data or {})
                    if hasattr(item, 'selected_size') and item.selected_size:
                        cust_data['selected_size'] = item.selected_size

                    order_item = OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        customization_data=cust_data,
                    )
                    # Atomically decrement stock — F() avoids a read-then-write race
                    # between two customers checking out the same product at once.
                    # Skipped for made-to-order items with tracking turned off.
                    if item.product.track_inventory:
                        Product.objects.filter(pk=item.product_id).update(
                            stock=F('stock') - item.quantity
                        )
                    # Transfer uploaded customization photos to OrderItemImage
                    from django.core.files.storage import default_storage
                    from django.core.files.base import File
                    import os as _os
                    uploaded_photos = item.customization_data.get('uploaded_photos', {})
                    for slot_key, photo_info in uploaded_photos.items():
                        file_path = photo_info.get('path', '')
                        if file_path and default_storage.exists(file_path):
                            try:
                                with default_storage.open(file_path, 'rb') as f:
                                    fname = _os.path.basename(file_path)
                                    OrderItemImage.objects.create(
                                        order_item=order_item,
                                        image=File(f, name=fname),
                                        slot_label=photo_info.get('label') or slot_key,
                                    )
                            except Exception:
                                pass
                if cart.coupon:
                    cart.coupon.used_count += 1
                    cart.coupon.save()
                cart.items.all().delete()
                cart.coupon = None
                cart.gift_wrap = False
                cart.notes = ''
                cart.save()
            return redirect('store:payment', order_id=order.order_id)
    else:
        initial = {
            'full_name': request.user.get_full_name(),
            'email': request.user.email,
        }
        try:
            initial['phone'] = request.user.profile.phone
        except:
            pass
        form = CheckoutForm(initial=initial)
    context = {
        'cart': cart,
        'form': form,
        'store_settings': store_s,
        'payment_configured': bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
    }
    return render(request, 'store/checkout.html', context)


# ─── UNPAID ORDER HANDLING ───────────────────────────────────────────────────
# An order only counts as "placed" once payment is verified. Anything else
# (customer closes the tab, network drops, payment fails, card declined…) is
# cancelled automatically, stock + coupon are given back, and the items return
# to the customer's cart. Nothing is ever left sitting in "Awaiting Payment".
UNPAID_ORDER_TTL_MINUTES = 20


def _restore_order_to_cart(order, cart, only_if_empty=False):
    """Put an unpaid order's items back into the cart, keeping size and
    customisation, and merging only into an identical line."""
    if only_if_empty and cart.items.exists():
        return
    for item in order.items.select_related('product').all():
        if item.product is None:
            continue
        cust = dict(item.customization_data or {})
        size = cust.pop('selected_size', '') or ''
        existing = None
        for ci in CartItem.objects.filter(cart=cart, product=item.product, selected_size=size):
            if (ci.customization_data or {}) == cust:
                existing = ci
                break
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=['quantity'])
        else:
            CartItem.objects.create(
                cart=cart,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.unit_price,
                customization_data=cust,
                selected_size=size,
                parcel_charge=item.parcel_charge,
            )


def _cancel_unpaid_order(order, cart=None, only_if_cart_empty=False):
    """Cancel an order that was never paid. Safe to call more than once."""
    from django.db import transaction
    from django.db.models import F
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=order.pk)
        if o.payment_status == 'paid' or o.status == 'cancelled':
            return False
        o.payment_status = 'failed'
        o.status = 'cancelled'
        o.save(update_fields=['payment_status', 'status', 'updated_at'])
        o.restore_stock()
        if o.coupon_code:
            Coupon.objects.filter(code=o.coupon_code, used_count__gt=0).update(used_count=F('used_count') - 1)
    if cart is not None:
        _restore_order_to_cart(o, cart, only_if_empty=only_if_cart_empty)
    return True


def _mark_order_paid(order, payment_id='', signature='', request=None):
    """Finalize a verified payment. Idempotent. Returns True if it changed."""
    from django.db import transaction
    from django.db.models import F
    with transaction.atomic():
        o = Order.objects.select_for_update().get(pk=order.pk)
        if o.payment_status == 'paid':
            return False
        was_cancelled = (o.status == 'cancelled')
        o.payment_status = 'paid'
        o.status = 'pending'          # officially placed — visible in manage portal
        if payment_id:
            o.razorpay_payment_id = payment_id
        if signature:
            o.razorpay_signature = signature
        o.save(update_fields=['payment_status', 'status', 'razorpay_payment_id', 'razorpay_signature', 'updated_at'])
        if was_cancelled:
            # Paid after we had already released the stock (very late payment) — take it again.
            for it in o.items.select_related('product').all():
                if it.product_id and it.product.track_inventory:
                    Product.objects.filter(pk=it.product_id).update(stock=F('stock') - it.quantity)
            if o.coupon_code:
                Coupon.objects.filter(code=o.coupon_code).update(used_count=F('used_count') + 1)
    try:
        from .emails import send_order_confirmation_email
        send_order_confirmation_email(o, request=request)
    except Exception:
        logger.exception('Order confirmation email failed for order %s', o.order_id)
    return True


def expire_stale_unpaid_orders(request=None, user=None, minutes=UNPAID_ORDER_TTL_MINUTES):
    """Cancel unpaid orders older than `minutes`. Before cancelling, ask Razorpay
    whether the customer actually paid (e.g. paid, then closed the browser before
    we heard back) — if so the order is confirmed instead. If Razorpay can't be
    reached the order is left alone and re-checked next time, so a paid order is
    never cancelled by mistake."""
    cutoff = timezone.now() - timedelta(minutes=minutes)
    qs = Order.objects.filter(status='awaiting_payment', payment_status='pending', created_at__lt=cutoff)
    if user is not None:
        qs = qs.filter(user=user)
    keys_ok = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    client = None
    done = 0
    for order in list(qs[:50]):
        try:
            if keys_ok and order.razorpay_order_id:
                try:
                    import razorpay
                    if client is None:
                        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    pays = client.order.payments(order.razorpay_order_id).get('items', [])
                    ok = next((p for p in pays if p.get('status') in ('captured', 'authorized')), None)
                except Exception:
                    logger.exception('Could not check Razorpay for order %s; will retry later', order.order_id)
                    continue
                if ok:
                    _mark_order_paid(order, payment_id=ok.get('id', ''), request=request)
                    done += 1
                    continue
            cart = None
            if request is not None and request.user.is_authenticated and order.user_id == request.user.pk:
                cart = get_or_create_cart(request)
            if _cancel_unpaid_order(order, cart=cart, only_if_cart_empty=True):
                done += 1
        except Exception:
            logger.exception('Failed to expire unpaid order %s', order.order_id)
    return done


@login_required
def payment_page(request, order_id):
    """Creates a Razorpay Order for this store Order and renders the Razorpay
    Checkout widget. GET only — the order itself was already created (as
    'pending') by checkout(); this step is purely about collecting payment."""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if order.payment_status == 'paid':
        return redirect('store:order_placed', order_id=order.order_id)

    if order.status == 'cancelled':
        messages.info(request, 'That payment session expired. Your items are back in your cart.')
        return redirect('store:cart')

    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        # Can't take payment, so don't leave a dead order behind — cancel it
        # and hand the items back to the cart.
        _cancel_unpaid_order(order, cart=get_or_create_cart(request))
        return render(request, 'store/payment.html', {
            'order': order,
            'razorpay_key_id': '',
            'payment_not_configured': True,
        })

    # Reuse the existing Razorpay order if we already created one for this
    # order (e.g. customer refreshed the payment page) instead of creating
    # duplicates on every reload.
    if not order.razorpay_order_id:
        try:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            amount_paise = int(round(float(order.total) * 100))
            rp_order = client.order.create({
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': order.order_id,
                'notes': {'order_id': order.order_id},
            })
            order.razorpay_order_id = rp_order['id']
            order.save(update_fields=['razorpay_order_id'])
        except Exception as e:
            logger.exception('Razorpay order creation failed (order_id=%s)', order.order_id)
            error_code = f"{type(e).__name__}: {str(e)[:180]}"
            messages.error(request, 'Could not start the payment right now. Please try again in a moment.')
            messages.error(request, f"Diagnostic code (copy this if it keeps happening): {error_code}")
            return render(request, 'store/payment.html', {
                'order': order,
                'razorpay_key_id': '',
            })

    return render(request, 'store/payment.html', {
        'order': order,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'amount_paise': int(round(float(order.total) * 100)),
    })


@require_POST
@login_required
def payment_verify(request, order_id):
    """Verifies the Razorpay payment signature and finalizes the order."""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        return JsonResponse({'success': False, 'message': 'Online payment is not configured.'}, status=400)

    # Rate limit: 10 verify attempts per minute per user
    if not _rate_limit(request, 'pay_verify', 10, 60):
        logger.warning('Payment verify rate limit exceeded for user %s order %s', request.user.pk, order_id)
        return JsonResponse({'success': False, 'message': 'Too many requests. Please wait before retrying.'}, status=429)

    # Input validation — all three fields must be non-empty strings
    razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
    razorpay_order_id   = request.POST.get('razorpay_order_id', '').strip()
    razorpay_signature  = request.POST.get('razorpay_signature', '').strip()

    if not (razorpay_payment_id and razorpay_order_id and razorpay_signature):
        logger.warning('Payment verify called with missing fields for order %s', order_id)
        return JsonResponse({'success': False, 'message': 'Invalid payment data received.'}, status=400)

    # Validate that the razorpay_order_id matches what we stored
    if order.razorpay_order_id and order.razorpay_order_id != razorpay_order_id:
        logger.warning('razorpay_order_id mismatch for order %s', order_id)
        return JsonResponse({'success': False, 'message': 'Payment order ID mismatch.'}, status=400)

    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
        valid = True
    except razorpay.errors.SignatureVerificationError:
        valid = False
    except Exception as e:
        logger.exception('Unexpected error during payment signature verification for order %s', order_id)
        return JsonResponse({'success': False, 'message': 'Verification error. Please contact support.'}, status=500)

    if valid:
        _mark_order_paid(order, payment_id=razorpay_payment_id, signature=razorpay_signature, request=request)
        return JsonResponse({'success': True, 'redirect': reverse('store:order_placed', args=[order.order_id])})

    logger.warning('Payment signature verification failed for order %s payment %s', order_id, razorpay_payment_id)
    return JsonResponse({'success': False, 'message': 'Payment verification failed. Please try again.'}, status=400)


def cancel_payment(request, order_id):
    """Customer cancelled before paying — restore cart then go to home."""
    if not request.user.is_authenticated:
        return redirect('store:home')

    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        return redirect('store:home')

    if order.payment_status != 'paid':
        _cancel_unpaid_order(order, cart=get_or_create_cart(request))

    return redirect('store:home')


def payment_failed(request, order_id):
    """Hard payment failure (card declined, bank error).
    Restores stock + cart items, then renders the failure page.
    No @login_required for same reason as cancel_payment.
    """
    if not request.user.is_authenticated:
        return redirect('store:cart')

    try:
        order = Order.objects.get(order_id=order_id, user=request.user)
    except Order.DoesNotExist:
        return redirect('store:cart')

    reason = request.GET.get('reason', 'failed')
    cart_restored = False

    if order.payment_status != 'paid':
        _cancel_unpaid_order(order, cart=get_or_create_cart(request))
        cart_restored = True

    return render(request, 'store/payment_failed.html', {
        'order': order,
        'reason': reason,
        'cart_restored': cart_restored,
    })


@login_required
def order_placed(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    return render(request, 'store/order_placed.html', {'order': order})




# ─── MY ORDERS ───────────────────────────────────────────────────────────────
@login_required
def my_orders(request):
    expire_stale_unpaid_orders(request=request, user=request.user)
    # Show all real orders: paid (active, shipped, delivered, admin-cancelled)
    # AND payment-failed cancellations so customer can see what happened.
    # Only hide 'awaiting_payment' drafts (incomplete checkout, no payment attempted).
    orders = Order.objects.filter(user=request.user).exclude(
        status='awaiting_payment'
    ).order_by('-created_at')
    return render(request, 'store/my_orders.html', {'orders': orders})


def _normalize_order_item_customization(item):
    """
    Turns an OrderItem's raw customization_data (which may contain a nested
    'choices' dict, an 'uploaded_photos' dict, etc.) into a clean, flat list
    of {'label','icon','value','kind'} entries safe to render in any template
    without dumping raw Python dict/repr text onto the page.

    Used by both the order detail page and the customer invoice so the two
    pages always show identical, correctly-formatted customization info.
    """
    import json as _json

    BLOCKED_SUBSTRINGS = ('password', 'pwd', 'token', 'csrf', 'session',
                           'secret', 'email', 'username', 'login', 'signup',
                           'account', 'user_id', 'auth', 'cookie')

    raw = {}
    if hasattr(item, 'customization_data') and item.customization_data:
        r = item.customization_data
        raw = _json.loads(r) if isinstance(r, str) else (r or {})
    if 'choices' in raw and isinstance(raw.get('choices'), dict):
        raw = raw['choices']

    choices = []
    handled = set()

    def _add(label, icon, value, kind='text'):
        if value and str(value).strip():
            choices.append({'label': label, 'icon': icon,
                            'value': str(value).strip(), 'kind': kind})

    TEXT_KEYS  = ['text', 'personalisation', 'Personalisation', 'custom_text', 'Text', 'message', 'Message']
    FONT_KEYS  = ['Font', 'font', 'custom_font']
    COLOR_KEYS = ['Color', 'color', 'colour', 'Colour', 'custom_color']
    SIZE_KEYS  = ['Size', 'size']
    NOTE_KEYS  = ['instructions', 'notes', 'special_instructions', 'suggestion', 'Notes', 'note']

    for key in TEXT_KEYS:
        if key in raw and raw[key] and key not in handled:
            _add('Text', '📝', raw[key], 'text'); handled.add(key); break
    for key in FONT_KEYS:
        if key in raw and raw[key] and key not in handled:
            _add('Font', '🔤', raw[key], 'font'); handled.add(key); break
    for key in COLOR_KEYS:
        if key in raw and raw[key] and key not in handled:
            _add('Colour', '🎨', raw[key], 'color'); handled.add(key); break
    for key in SIZE_KEYS:
        if key in raw and raw[key] and key not in handled:
            _add('Size', '📐', raw[key], 'text'); handled.add(key); break
    for key in NOTE_KEYS:
        if key in raw and raw[key] and key not in handled:
            _add('Notes', '📋', raw[key], 'text'); handled.add(key); break

    # All remaining entries — photo/image/logo keys intentionally skipped here;
    # uploaded files are represented once, via OrderItemImage, never as text.
    for key, val in raw.items():
        if not val or key in handled:
            continue
        lk = key.lower()
        if 'photo' in lk or 'image' in lk or 'pic' in lk or 'logo' in lk:
            continue
        if any(b in lk for b in BLOCKED_SUBSTRINGS):
            continue
        choices.append({'label': key, 'icon': '•', 'value': str(val), 'kind': 'text'})
        handled.add(key)

    order_images = list(item.images.all()) if hasattr(item, 'images') else []
    return choices, order_images


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    ORDER_STEPS = [
        ('pending',   'Pending'),
        ('printing',  'Printing'),
        ('shipped',   'Shipped'),
        ('delivered', 'Delivered'),
    ]
    step_keys = [s[0] for s in ORDER_STEPS]
    current_idx = step_keys.index(order.status) if order.status in step_keys else -1
    passed_steps = set(step_keys[:current_idx])

    items_data = []
    for item in order.items.all():
        choices, order_images = _normalize_order_item_customization(item)
        can_rev = bool(order.status in REVIEWABLE_ORDER_STATUSES and item.product_id and _can_review(request.user, item.product))
        reviewed = bool(item.product_id and Review.objects.filter(user=request.user, product_id=item.product_id).exists())
        items_data.append({'item': item, 'choices': choices, 'order_images': order_images,
                           'can_review': can_rev, 'reviewed': reviewed})

    return render(request, 'store/order_detail.html', {
        'order': order,
        'items_data': items_data,
        'steps': ORDER_STEPS,
        'passed_steps': passed_steps,
    })


@login_required
def customer_invoice(request, order_id):
    """Customer-facing professional invoice — only accessible by the order owner."""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    items_data = []

    for item in order.items.all():
        choices, order_images = _normalize_order_item_customization(item)
        items_data.append({
            'item':         item,
            'choices':      choices,
            'order_images': order_images,
        })

    ORDER_STEPS = [('pending','Pending'),('printing','Printing'),('shipped','Shipped'),('delivered','Delivered')]
    step_keys   = [k for k, _ in ORDER_STEPS]
    current_idx = step_keys.index(order.status) if order.status in step_keys else 0
    passed_steps = set(step_keys[:current_idx])

    store_settings = StoreSettings.objects.first()

    return render(request, 'store/order_invoice.html', {
        'order':        order,
        'items_data':   items_data,
        'steps':        ORDER_STEPS,
        'passed_steps': passed_steps,
        'store_settings': store_settings,
    })


@login_required
def download_invoice(request, order_id):
    """Generate a plain-text/HTML invoice and return as downloadable file."""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    from django.http import HttpResponse
    lines = []
    lines.append("=" * 56)
    lines.append(f"{'CRAFTX3D STUDIO — TAX INVOICE':^56}")
    lines.append("=" * 56)
    lines.append(f"Invoice No : {order.order_id}")
    lines.append(f"Date       : {order.created_at.strftime('%d %b %Y, %I:%M %p')}")
    lines.append(f"Order ID   : {order.order_id}")
    lines.append("-" * 56)
    lines.append(f"BILL TO:")
    lines.append(f"  {order.full_name}")
    lines.append(f"  {order.phone}")
    if order.email: lines.append(f"  {order.email}")
    lines.append(f"  {order.address}, {order.city}")
    lines.append(f"  {order.state} - {order.pincode}")
    lines.append("-" * 56)
    lines.append(f"{'ITEM':<30} {'QTY':>4} {'PRICE':>10} {'TOTAL':>10}")
    lines.append("-" * 56)
    for item in order.items.all():
        name = item.product_name[:28]
        lines.append(f"{name:<30} {item.quantity:>4} ₹{item.unit_price:>8.2f} ₹{item.total_price:>8.2f}")
    lines.append("-" * 56)
    lines.append(f"{'Subtotal':>44}: ₹{order.subtotal:>8.2f}")
    if order.discount_amount:
        lines.append(f"{'Discount (' + (order.coupon_code or '') + ')':>44}: -₹{order.discount_amount:>7.2f}")
    if order.gift_wrap:
        lines.append(f"{'Gift Wrap':>44}: ₹{order.gift_wrap_price:>8.2f}")
    lines.append(f"{'TOTAL':>44}: ₹{order.total:>8.2f}")
    lines.append("-" * 56)
    lines.append(f"Payment Method: {order.payment_method.upper()}")
    lines.append("=" * 56)
    lines.append("Thank you for shopping with CraftX3D!")
    lines.append("www.craftx3dstudio.com")
    lines.append("=" * 56)
    content = "\n".join(lines)
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_id}.txt"'
    return response


# ─── AUTH ────────────────────────────────────────────────────────────────────
def register(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        agreed_terms = 'agree_terms' in request.POST
        if form.is_valid() and not agreed_terms:
            messages.error(request, 'Please agree to the Terms & Conditions to create an account.')
        elif form.is_valid():
            data = form.cleaned_data
            names = data['full_name'].split(' ', 1)
            # Phone number is the login (username); email is optional.
            user = User.objects.create_user(
                username=data['phone'],
                email=data.get('email', ''),
                password=data['password'],
                first_name=names[0],
                last_name=names[1] if len(names) > 1 else '',
            )
            # The post_save signal on User already created a blank UserProfile;
            # just fill in the phone number they gave us.
            UserProfile.objects.update_or_create(user=user, defaults={'phone': data['phone']})
            user = authenticate(request, username=data['phone'], password=data['password'])
            login(request, user)
            messages.success(request, f"Welcome to CraftiX 3D, {user.first_name}!")
            return redirect('store:home')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'store/register.html', {'form': form})


def _find_users_by_identifier(identifier):
    """Login id can be a 10-digit phone number (new) or an email (accounts
    created before phone login existed). Returns candidate User objects."""
    identifier = (identifier or '').strip()
    if '@' in identifier:
        return list(User.objects.filter(email__iexact=identifier, is_active=True)[:5])
    phone = normalize_phone(identifier)
    if len(phone) != 10:
        return []
    ids = set(User.objects.filter(username=phone, is_active=True).values_list('pk', flat=True))
    ids |= set(UserProfile.objects.filter(phone__endswith=phone, user__is_active=True).values_list('user_id', flat=True))
    return list(User.objects.filter(pk__in=ids)[:5])


def _safe_next(request, default='store:home'):
    from django.utils.http import url_has_allowed_host_and_scheme
    nxt = request.GET.get('next') or request.POST.get('next') or ''
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return nxt
    return default


def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    if request.method == 'POST':
        identifier = (request.POST.get('phone') or request.POST.get('email') or '').strip()
        password = request.POST.get('password', '')

        from django.core.cache import cache
        lockout_key = f'customer_login_fail:{identifier.lower()}'
        fail_count = cache.get(lockout_key, 0)
        if fail_count >= 8:
            messages.error(request, 'Too many failed attempts. Please try again in 15 minutes.')
            return render(request, 'store/login.html')

        user = None
        for candidate in _find_users_by_identifier(identifier):
            user = authenticate(request, username=candidate.username, password=password)
            if user:
                break
        if user:
            cache.delete(lockout_key)
            login(request, user)
            return redirect(_safe_next(request))
        else:
            cache.set(lockout_key, fail_count + 1, 900)
            messages.error(request, 'Invalid phone number or password.')
    return render(request, 'store/login.html')


def logout_view(request):
    logout(request)
    return redirect('store:home')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        from django.core.cache import cache
        lockout_key = f'forgot_password_fail:{email.lower()}'
        fail_count = cache.get(lockout_key, 0)
        if fail_count >= 5:
            messages.error(request, 'Too many requests. Please try again in 15 minutes.')
            return render(request, 'store/forgot_password.html')
        cache.set(lockout_key, fail_count + 1, 900)

        # Always show the same message regardless of whether the account exists
        # — this prevents anyone from using this form to discover who has one.
        if email:
            user = next((u for u in _find_users_by_identifier(email) if u.email), None)
            if user:
                from django.contrib.auth.tokens import default_token_generator
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from .emails import send_password_reset_email

                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse('store:reset_password_confirm', args=[uidb64, token])
                )
                send_password_reset_email(user, reset_url)

        messages.success(request, "If an account exists with that phone number or email and has an email on file, we've sent a password reset link. No email on your account? Contact support.")
        return redirect('store:login')

    return render(request, 'store/forgot_password.html')


def reset_password_confirm(request, uidb64, token):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    token_valid = user is not None and default_token_generator.check_token(user, token)

    if not token_valid:
        return render(request, 'store/reset_password_confirm.html', {'token_valid': False})

    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'store/reset_password_confirm.html', {'token_valid': True})
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'store/reset_password_confirm.html', {'token_valid': True})

        user.set_password(password)
        user.save()
        messages.success(request, 'Your password has been reset. You can now sign in.')
        return redirect('store:login')

    return render(request, 'store/reset_password_confirm.html', {'token_valid': True})


def terms_page(request):
    from .models import TermsCondition
    terms = TermsCondition.objects.filter(is_active=True)
    return render(request, 'store/terms.html', {'terms': terms})


def privacy_page(request):
    from .models import PrivacyPolicy
    terms = PrivacyPolicy.objects.filter(is_active=True)
    return render(request, 'store/privacy.html', {'terms': terms})


def refund_page(request):
    from .models import RefundPolicy
    terms = RefundPolicy.objects.filter(is_active=True)
    return render(request, 'store/refund.html', {'terms': terms})


def shipping_page(request):
    from .models import ShippingPolicy
    terms = ShippingPolicy.objects.filter(is_active=True)
    return render(request, 'store/shipping.html', {'terms': terms})


def custom_order_policy_page(request):
    from .models import CustomOrderPolicy
    terms = CustomOrderPolicy.objects.filter(is_active=True)
    return render(request, 'store/custom_order_policy.html', {'terms': terms})


def product_disclaimer_page(request):
    from .models import ProductDisclaimer
    terms = ProductDisclaimer.objects.filter(is_active=True)
    return render(request, 'store/product_disclaimer.html', {'terms': terms})


def contact_page(request):
    from .models import ContactInfo
    info = ContactInfo.objects.first()
    return render(request, 'store/contact.html', {'info': info})


@login_required
def profile(request):
    user = request.user
    profile_obj, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            user.save(update_fields=['first_name', 'last_name'])
        new_phone = normalize_phone(request.POST.get('phone', profile_obj.phone))
        if new_phone and new_phone != normalize_phone(profile_obj.phone) and (
            UserProfile.objects.filter(phone__endswith=new_phone).exclude(user=user).exists()
            or User.objects.filter(username=new_phone).exclude(pk=user.pk).exists()
        ):
            messages.error(request, 'That phone number is already used by another account.')
            return redirect('store:profile')
        profile_obj.phone = new_phone or profile_obj.phone
        profile_obj.city = request.POST.get('city', profile_obj.city).strip()
        profile_obj.save()
        messages.success(request, 'Your profile has been updated.')
        return redirect('store:profile')

    expire_stale_unpaid_orders(request=request, user=user)
    orders = Order.objects.filter(user=user).exclude(status='awaiting_payment')
    context = {
        'profile': profile_obj,
        'order_count': orders.count(),
        'delivered_count': orders.filter(status='delivered').count(),
        'recent_orders': orders.order_by('-created_at')[:3],
    }
    return render(request, 'store/profile.html', context)


@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    favorite = Favorite.objects.filter(user=request.user, product=product).first()
    if favorite:
        favorite.delete()
        is_favorited = False
    else:
        Favorite.objects.create(user=request.user, product=product)
        is_favorited = True

    favorite_count = Favorite.objects.filter(user=request.user).count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_favorited': is_favorited, 'favorite_count': favorite_count})
    return redirect(request.META.get('HTTP_REFERER', 'store:home'))


@login_required
def my_favorites(request):
    favorites_qs = Favorite.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    products = [f.product for f in favorites_qs if f.product and f.product.is_active]
    return render(request, 'store/my_favorites.html', {'products': products})
