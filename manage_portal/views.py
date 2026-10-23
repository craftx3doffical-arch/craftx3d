from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings as django_settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.contrib import messages
import json, csv, io
from datetime import timedelta
from .decorators import staff_required
from .models import StaffUser
from store.models import (
    Product, Category, CategoryImage, ProductImage, ProductFAQ,
    Review, Order, OrderItem, Coupon, HelpFAQ, Enquiry, Banner, BannerImage,
    AboutPageContent, StoreSettings, UserProfile, PackagingType,
    SizeOption, PackSizeOption, TermsCondition, PrivacyPolicy,
    RefundPolicy, ShippingPolicy, ContactInfo, CustomOrderPolicy, ProductDisclaimer
)
from django.contrib.auth.models import User


# ─── AUTH ────────────────────────────────────────────────────────────────────
def manage_login(request):
    if request.session.get('staff_logged_in'):
        return redirect('manage:dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Basic brute-force protection: lock out further attempts for this
        # username after 5 failed tries within 15 minutes.
        from django.core.cache import cache
        lockout_key = f'staff_login_fail:{username.lower()}'
        fail_count = cache.get(lockout_key, 0)
        if fail_count >= 5:
            return render(request, 'manage/login.html', {
                'error': 'Too many failed attempts. Please try again in 15 minutes.'
            })

        try:
            staff = StaffUser.objects.get(username__iexact=username, is_active=True)
            if staff.check_password(password):
                cache.delete(lockout_key)
                request.session['staff_logged_in'] = True
                request.session['staff_id'] = staff.pk
                request.session['staff_username'] = staff.username
                request.session['staff_role'] = staff.role
                staff.total_logins += 1
                staff.last_login = timezone.now()
                staff.save()
                return redirect('manage:dashboard')
            else:
                cache.set(lockout_key, fail_count + 1, 900)  # 15 minutes
                error = "Invalid credentials"
        except StaffUser.DoesNotExist:
            cache.set(lockout_key, fail_count + 1, 900)
            error = "Invalid credentials"
        except StaffUser.MultipleObjectsReturned:
            error = "Invalid credentials"
    return render(request, 'manage/login.html', {'error': error})


def manage_logout(request):
    for key in ['staff_logged_in', 'staff_id', 'staff_username', 'staff_role']:
        request.session.pop(key, None)
    return redirect('manage:login')


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@staff_required
def dashboard(request):
    try:
        from store.views import expire_stale_unpaid_orders
        expire_stale_unpaid_orders(request=None)
    except Exception:
        pass
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    stats = {
        'total_revenue': Order.objects.filter(payment_status='paid', status='delivered').aggregate(s=Sum('total'))['s'] or 0,
        'active_orders': Order.objects.filter(payment_status='paid', status__in=['pending', 'printing', 'shipped']).count(),
        'total_products': Product.objects.filter(is_active=True).count(),
        'total_customers': User.objects.filter(is_staff=False).count(),
        'new_today': Order.objects.filter(payment_status='paid', created_at__date=today).count(),
        'pending_orders': Order.objects.filter(payment_status='paid', status='pending').count(),
        'pending_reviews': Review.objects.filter(status=Review.STATUS_PENDING).count(),
        'new_enquiries': Enquiry.objects.filter(status=Enquiry.STATUS_NEW, enquiry_type=Enquiry.TYPE_GENERAL).count(),
        'new_custom_enquiries': Enquiry.objects.filter(status=Enquiry.STATUS_NEW, enquiry_type=Enquiry.TYPE_CUSTOMIZATION).count(),
    }
    # Last 7 days revenue chart
    revenue_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        rev = Order.objects.filter(payment_status='paid', created_at__date=day).aggregate(s=Sum('total'))['s'] or 0
        revenue_data.append({'date': day.strftime('%a'), 'revenue': float(rev)})
    recent_orders = Order.objects.filter(payment_status='paid').select_related('user').order_by('-created_at')[:10]
    top_products = Product.objects.annotate(order_count=Count('orderitem')).order_by('-order_count')[:5]
    context = {
        'stats': stats,
        'revenue_data': json.dumps(revenue_data),
        'recent_orders': recent_orders,
        'top_products': top_products,
    }
    return render(request, 'manage/dashboard.html', context)


# ─── PRODUCTS ────────────────────────────────────────────────────────────────
@staff_required
def products_list(request):
    qs = Product.objects.select_related('category').prefetch_related('images')
    category_id = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('q', '')
    if category_id:
        qs = qs.filter(category_id=category_id)
    if status == 'active':
        qs = qs.filter(is_active=True)
    elif status == 'inactive':
        qs = qs.filter(is_active=False)
    if search:
        qs = qs.filter(name__icontains=search)
    categories = Category.objects.all()
    return render(request, 'manage/products.html', {
        'products': qs,
        'categories': categories,
        'selected_cat': category_id,
        'status_filter': status,
        'search': search,
        'view_mode': request.GET.get('view', 'table'),
    })


@staff_required
def product_add(request):
    categories = Category.objects.filter(is_active=True)
    packaging_types = PackagingType.objects.filter(is_active=True)
    if request.method == 'POST':
        product = _save_product(request, None)
        if product:
            messages.success(request, f'Product "{product.name}" added successfully.')
            return redirect('manage:products')
    from store.models import CUSTOMIZATION_TYPE_CHOICES
    return render(request, 'manage/product_form.html', {
        'categories': categories,
        'packaging_types': packaging_types,
        'product': None,
        'customization_types': CUSTOMIZATION_TYPE_CHOICES,
    })


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.filter(is_active=True)
    packaging_types = PackagingType.objects.filter(is_active=True)
    if request.method == 'POST':
        product = _save_product(request, product)
        if product:
            messages.success(request, f'Product "{product.name}" updated.')
            return redirect('manage:products')
    from store.models import CUSTOMIZATION_TYPE_CHOICES
    # Properly serialize customization_data to valid JSON for the builder
    customization_data_json = json.dumps(product.customization_data or {})
    return render(request, 'manage/product_form.html', {
        'categories': categories,
        'packaging_types': packaging_types,
        'product': product,
        'customization_types': CUSTOMIZATION_TYPE_CHOICES,
        'customization_data_json': customization_data_json,
    })


def _save_product(request, product=None):
    data = request.POST
    files = request.FILES
    if not product:
        product = Product()
    product.name = data.get('name', '')
    cat_id = data.get('category')
    if cat_id:
        try:
            product.category = Category.objects.get(pk=cat_id)
        except Category.DoesNotExist:
            pass
    product.base_price = data.get('base_price', 0) or 0
    cp = data.get('compare_price', '')
    product.compare_price = float(cp) if cp else None
    if files.get('video'):
        product.video = files['video']
    product.show_mega_deal = 'show_mega_deal' in data
    product.mega_deal_label = data.get('mega_deal_label', '').strip() or 'Mega Festival Deal'
    product.show_parcel_charge = 'show_parcel_charge' in data
    product.parcel_charge_title = data.get('parcel_charge_title', '').strip() or 'Parcel & Packaging Fee'
    pc = data.get('parcel_charge_price', '')
    product.parcel_charge_price = float(pc) if pc else 0
    product.parcel_charge_free_label = data.get('parcel_charge_free_label', '').strip() or 'Free Parcel & Packaging'
    product.customization_type = data.get('customization_type', 'none')
    product.description = data.get('description', '')
    product.description_title = data.get('description_title', '').strip() or 'Product Description'
    product.materials = data.get('materials', '')
    product.materials_title = data.get('materials_title', '').strip() or 'Materials & Specifications'
    product.dimensions = data.get('dimensions', '')
    product.production_info = data.get('production_info', '')
    product.production_info_title = data.get('production_info_title', '').strip() or 'Production & Shipping'
    for i in range(1, 6):
        setattr(product, f'extra_title_{i}', data.get(f'extra_title_{i}', '').strip())
        setattr(product, f'extra_content_{i}', data.get(f'extra_content_{i}', '').strip())
        if files.get(f'extra_image_{i}'):
            setattr(product, f'extra_image_{i}', files[f'extra_image_{i}'])
    product.standard_delivery_days = int(data.get('standard_delivery_days', 7) or 7)
    product.standard_delivery_title = data.get('standard_delivery_title', '').strip() or 'Standard Delivery'
    product.express_delivery_days = int(data.get('express_delivery_days', 3) or 3)
    product.express_delivery_title = data.get('express_delivery_title', '').strip() or 'Express Delivery'
    product.show_production_time = 'show_production_time' in data
    product.production_time_title = data.get('production_time_title', '').strip() or 'Production Time'
    product.production_time_days = int(data.get('production_time_days', 2) or 2)
    product.show_delivery_estimate = 'show_delivery_estimate' in data

    product.show_feature_ticks = 'show_feature_ticks' in data
    product.feature_tick_1 = data.get('feature_tick_1', '').strip()
    product.feature_tick_2 = data.get('feature_tick_2', '').strip()
    product.feature_tick_3 = data.get('feature_tick_3', '').strip()

    product.show_short_description = 'show_short_description' in data
    product.short_description = data.get('short_description', '').strip()

    product.show_trust_badges = 'show_trust_badges' in data
    product.trust_badge_1 = data.get('trust_badge_1', '').strip()
    product.trust_badge_2 = data.get('trust_badge_2', '').strip()
    product.trust_badge_3 = data.get('trust_badge_3', '').strip()
    product.trust_badge_4 = data.get('trust_badge_4', '').strip()

    product.show_materials_table = 'show_materials_table' in data
    row_labels = data.getlist('materials_row_label[]')
    row_values = data.getlist('materials_row_value[]')
    rows = []
    for label, value in zip(row_labels, row_values):
        label, value = label.strip(), value.strip()
        if label and value:
            rows.append({'label': label, 'value': value})
    product.materials_table_rows = rows

    product.show_about_craft = 'show_about_craft' in data
    product.about_craft_title = data.get('about_craft_title', '').strip() or 'About Our Craft'
    product.about_craft_text = data.get('about_craft_text', '').strip()
    # BUGFIX: stock was not being saved from form
    try:
        product.stock = int(data.get('stock', 0) or 0)
    except (ValueError, TypeError):
        product.stock = 0
    product.track_inventory = 'track_inventory' in data
    product.show_standard_delivery = 'show_standard_delivery' in data
    product.show_express_delivery = 'show_express_delivery' in data
    product.is_active = 'is_active' in data
    product.is_featured = 'is_featured' in data
    product.is_bestseller = 'is_bestseller' in data
    product.photo_upload_enabled = 'photo_upload_enabled' in data
    # Customization JSON — only preserve builder data for 'field' type
    if product.customization_type == 'field':
        try:
            product.customization_data = json.loads(data.get('customization_data', '{}'))
        except:
            product.customization_data = {}
    else:
        product.customization_data = {}
    try:
        product.section_order = json.loads(data.get('section_order', '[]'))
    except:
        product.section_order = []
    product.save()
    # Handle product images — accept both 'images' (multiple) and 'image_N' (individual)
    existing_main = data.get('existing_main_image')
    has_existing = product.images.exists()
    img_order = product.images.aggregate(mx=__import__('django.db.models', fromlist=['Max']).Max('display_order'))['mx'] or 0
    image_upload_failed = False
    # Multiple files upload (from product_form)
    multi_imgs = files.getlist('images')
    for i, img_file in enumerate(multi_imgs):
        is_main = (i == 0 and not has_existing)
        try:
            ProductImage.objects.create(product=product, image=img_file, is_main=is_main, display_order=img_order + i + 1)
        except Exception:
            image_upload_failed = True
    # Individual image_N fields (legacy / slots)
    if not multi_imgs:
        for i in range(10):
            img_file = files.get(f'image_{i}')
            if img_file:
                is_main = (str(i) == data.get('main_image_index', '0')) and not has_existing
                try:
                    ProductImage.objects.create(product=product, image=img_file, is_main=is_main, display_order=img_order + i + 1)
                except Exception:
                    image_upload_failed = True
    if image_upload_failed:
        messages.warning(request, f'"{product.name}" was saved, but one or more photos failed to upload — please try re-uploading them.')
    return product


@staff_required
@require_POST
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f'Product "{name}" deleted.')
    return redirect('manage:products')


@staff_required
@require_POST
def product_toggle_status(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save()
    return JsonResponse({'success': True, 'is_active': product.is_active})


@staff_required
@require_POST
def delete_product_image(request, pk):
    img = get_object_or_404(ProductImage, pk=pk)
    img.image.delete()
    img.delete()
    return JsonResponse({'success': True})


# ─── CATEGORIES ──────────────────────────────────────────────────────────────
@staff_required
def categories_list(request):
    cats = Category.objects.prefetch_related('images').annotate(product_count=Count('products'))
    return render(request, 'manage/categories.html', {'categories': cats})


@staff_required
def category_add(request):
    if request.method == 'POST':
        cat = Category()
        cat.name = request.POST.get('name', '').strip()
        if not cat.name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Name is required'})
            messages.error(request, 'Category name is required.')
            return redirect('manage:categories')
        cat.description = request.POST.get('description', '')
        cat.display_order = int(request.POST.get('display_order', 0) or 0)
        cat.is_active = 'is_active' in request.POST
        cat.save()
        # Handle images — wrapped in try/except so a Cloudinary/upload error
        # doesn't cause a 500 after the category has already been saved
        try:
            for i, img_file in enumerate(request.FILES.getlist('images')):
                CategoryImage.objects.create(category=cat, image=img_file, display_order=i)
        except Exception:
            pass  # category saved; image upload failed silently
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'id': cat.pk, 'name': cat.name})
        messages.success(request, f'Category "{cat.name}" added successfully.')
        return redirect('manage:categories')
    # GET — render the add form directly (same template as edit)
    return render(request, 'manage/category_form.html', {'category': None})


@staff_required
def category_edit(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.name = request.POST.get('name', cat.name).strip()
        cat.description = request.POST.get('description', cat.description)
        cat.display_order = int(request.POST.get('display_order', cat.display_order) or cat.display_order)
        cat.is_active = 'is_active' in request.POST
        cat.save()
        for i, img_file in enumerate(request.FILES.getlist('images')):
            CategoryImage.objects.create(category=cat, image=img_file, display_order=i)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, f'Category "{cat.name}" updated.')
        return redirect('manage:categories')
    # GET — return category data as JSON (for edit modal if needed)
    data = {
        'id': cat.pk, 'name': cat.name, 'description': cat.description,
        'display_order': cat.display_order, 'is_active': cat.is_active,
        'images': [{'id': img.pk, 'url': img.image.url} for img in cat.images.all()],
    }
    return render(request, 'manage/category_form.html', {'category': cat})


@staff_required
@require_POST
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, f'Category deleted.')
        return redirect('manage:categories')
    # GET — redirect (don't delete on GET)
    return redirect('manage:categories')


@staff_required
@require_POST
def delete_category_image(request, pk):
    img = get_object_or_404(CategoryImage, pk=pk)
    img.image.delete()
    img.delete()
    return JsonResponse({'success': True})


# ─── INVENTORY ───────────────────────────────────────────────────────────────
@staff_required
def inventory(request):
    products = Product.objects.select_related('category').all()
    return render(request, 'manage/inventory.html', {'products': products})


@staff_required
@require_POST
def inventory_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.stock = int(request.POST.get('stock', product.stock))
    product.base_price = request.POST.get('price', product.base_price)
    product.save()
    return JsonResponse({'success': True})


@staff_required
@require_POST
def inventory_toggle_tracking(request, pk):
    product = get_object_or_404(Product, pk=pk)
    product.track_inventory = request.POST.get('track_inventory', 'true').lower() == 'true'
    product.save(update_fields=['track_inventory'])
    return JsonResponse({'success': True, 'track_inventory': product.track_inventory})


@staff_required
def export_inventory(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Product', 'Category', 'Price', 'Stock', 'Status'])
    for p in Product.objects.select_related('category').all():
        writer.writerow([p.name, p.category.name if p.category else '', p.base_price, p.stock, 'Active' if p.is_active else 'Inactive'])
    return response


# ─── ORDERS ──────────────────────────────────────────────────────────────────
@staff_required
def orders_list(request):
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')
    qs = Order.objects.filter(payment_status='paid').select_related('user').prefetch_related('items').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(Q(order_id__icontains=search) | Q(full_name__icontains=search) | Q(phone__icontains=search))
    order_statuses = Order._meta.get_field('status').choices
    return render(request, 'manage/orders.html', {
        'orders': qs,
        'status_filter': status_filter,
        'search': search,
        'order_statuses': order_statuses,
    })


@staff_required
def order_detail_manage(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    ORDER_STEPS = [
        ('pending',   'Pending'),
        ('printing',  'Printing'),
        ('shipped',   'Shipped'),
        ('delivered', 'Delivered'),
    ]
    step_keys = [s[0] for s in ORDER_STEPS]
    current_idx = step_keys.index(order.status) if order.status in step_keys else -1
    passed_steps = set(step_keys[:current_idx])
    order_statuses = Order._meta.get_field('status').choices
    return render(request, 'manage/order_detail.html', {
        'order': order,
        'steps': ORDER_STEPS,
        'passed_steps': passed_steps,
        'order_statuses': order_statuses,
    })


@staff_required
@require_POST
def resend_order_email(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    from store.emails import send_order_confirmation_email
    sent, error_detail = send_order_confirmation_email(order, request=request)
    if sent:
        messages.success(request, f'Confirmation email resent to {order.email}.')
    else:
        messages.error(request, 'Could not send the email right now.')
        if error_detail:
            messages.error(request, f'Diagnostic code (copy this if it keeps happening): {error_detail}')
    return redirect('manage:order_detail', order_id=order.order_id)


@staff_required
def order_invoice(request, order_id):
    """Professional HTML invoice with all customization details and image downloads."""
    order = get_object_or_404(Order, order_id=order_id)
    store_settings = StoreSettings.objects.first()
    return render(request, 'manage/order_invoice.html', {'order': order, 'store_settings': store_settings})


@staff_required
def printing_invoice(request, order_id):
    """Compact 4x6in, 1-up courier-style tax invoice — the kind couriers/
    3rd-party marketplaces (Amazon, Flipkart) stick on the package: Sold By
    block, Order/Invoice No & Date, a line-item tax table (taxable value +
    GST split out of the tax-inclusive selling price), billing/shipping
    address boxes, amount in words, and a scan barcode. Meant to be printed
    directly at 4x6in (e.g. a label printer or a cut sheet), separate from
    the full-page 'Invoice' used for customer-facing/record-keeping copies.
    """
    from decimal import Decimal, ROUND_HALF_UP
    from .utils import amount_in_words_inr

    order = get_object_or_404(Order, order_id=order_id)
    store_settings = StoreSettings.objects.first()

    # Only split out a GST line if the store has actually configured GST —
    # otherwise this renders as a plain Bill of Supply (0% tax column),
    # rather than inventing a tax rate/GSTIN the store never gave us.
    show_gst = bool(store_settings and store_settings.show_gst_on_invoice and store_settings.gst_number)
    gst_rate = Decimal('18') if show_gst else Decimal('0')
    divisor = (Decimal('100') + gst_rate) / Decimal('100')

    items_data = []
    total_taxable = Decimal('0')
    total_tax = Decimal('0')
    for idx, item in enumerate(order.items.select_related('product').all(), start=1):
        net_amount = item.total_price
        if gst_rate:
            taxable_amount = (net_amount / divisor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            taxable_amount = net_amount
        tax_amount = (net_amount - taxable_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_taxable += taxable_amount
        total_tax += tax_amount
        items_data.append({
            'sno': idx,
            'item': item,
            'net_amount': net_amount,
            'taxable_amount': taxable_amount,
            'tax_amount': tax_amount,
        })

    return render(request, 'manage/printing_invoice.html', {
        'order': order,
        'items_data': items_data,
        'store_settings': store_settings,
        'show_gst': show_gst,
        'gst_rate': gst_rate,
        'total_taxable': total_taxable,
        'total_tax': total_tax,
        'amount_in_words': amount_in_words_inr(order.total),
        'printed_at': timezone.now(),
    })


@staff_required
@require_POST
def order_update_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    new_status = request.POST.get('status')
    if new_status in dict(Order._meta.get_field('status').choices):
        was_cancelled = (order.status == 'cancelled')
        order.status = new_status
        if new_status == 'delivered':
            order.delivered_at = timezone.now()
        tracking = request.POST.get('tracking_number', '')
        courier = request.POST.get('courier', '')
        if tracking:
            order.tracking_number = tracking
        if courier:
            order.courier = courier
        staff_note = request.POST.get('staff_note', '')
        if staff_note:
            order.staff_note = staff_note
        order.save()
        # Restore stock when an order is newly cancelled; don't double-restore
        # if it's already cancelled and gets re-saved.
        if new_status == 'cancelled' and not was_cancelled:
            order.restore_stock()
        # AJAX (status dropdown) → JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': order.status})
        # Regular form submit (tracking form) → redirect back
        messages.success(request, f'Order #{order_id} updated.')
        return redirect('manage:order_detail', order_id=order_id)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid status'})
    messages.error(request, 'Invalid status.')
    return redirect('manage:order_detail', order_id=order_id)


@staff_required
def export_orders(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Date', 'Customer', 'Phone', 'City', 'State', 'Items', 'Total', 'Status', 'Payment Status', 'Razorpay Payment ID'])
    for o in Order.objects.filter(payment_status='paid'):
        writer.writerow([o.order_id, o.created_at.strftime('%d/%m/%Y'), o.full_name, o.phone, o.city, o.state, o.items.count(), o.total, o.status, o.get_payment_status_display(), o.razorpay_payment_id])
    return response


@staff_required
def delivered_orders(request):
    orders = Order.objects.filter(status='delivered').order_by('-delivered_at')
    return render(request, 'manage/delivered_orders.html', {'orders': orders})


@staff_required
def cancelled_orders(request):
    orders = Order.objects.filter(payment_status='paid', status='cancelled').order_by('-updated_at')
    return render(request, 'manage/cancelled_orders.html', {'orders': orders})


@staff_required
def export_delivered(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="delivered_orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Date', 'Customer', 'Phone', 'Address', 'Payment', 'Items', 'Total', 'Tracking', 'Courier'])
    for o in Order.objects.filter(status='delivered'):
        writer.writerow([o.order_id, o.created_at.strftime('%d/%m/%Y'), o.full_name, o.phone, f"{o.address}, {o.city}, {o.state} - {o.pincode}", o.payment_method, o.items.count(), o.total, o.tracking_number, o.courier])
    return response


@staff_required
def export_cancelled(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="cancelled_orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Date', 'Customer', 'Phone', 'Address', 'Payment', 'Items', 'Total', 'Staff Note'])
    for o in Order.objects.filter(payment_status='paid', status='cancelled'):
        writer.writerow([o.order_id, o.created_at.strftime('%d/%m/%Y'), o.full_name, o.phone, f"{o.address}, {o.city}", o.payment_method, o.items.count(), o.total, o.staff_note])
    return response


# ─── COUPONS ─────────────────────────────────────────────────────────────────
@staff_required
def coupons_list(request):
    coupons = Coupon.objects.all().order_by('-created_at')
    return render(request, 'manage/coupons.html', {'coupons': coupons})


@staff_required
def coupon_add(request):
    if request.method == 'POST':
        from datetime import datetime
        coupon = Coupon()
        coupon.code = request.POST.get('code', '').upper().strip()
        if not coupon.code:
            messages.error(request, 'Coupon code is required.')
            return redirect('manage:coupons')
        coupon.discount_type = request.POST.get('discount_type', 'percent')
        coupon.discount_value = request.POST.get('discount_value', 0)
        coupon.min_order_value = request.POST.get('min_order_value', 0) or 0
        coupon.max_uses = int(request.POST.get('max_uses', 0) or 0)
        coupon.is_active = 'is_active' in request.POST
        coupon.is_secret = 'is_secret' in request.POST
        coupon.description = request.POST.get('description', '')
        vf = request.POST.get('valid_from')
        vu = request.POST.get('valid_until')
        if vf:
            coupon.valid_from = datetime.fromisoformat(vf)
        if vu:
            coupon.valid_until = datetime.fromisoformat(vu)
        coupon.save()
        # AJAX → JSON, regular form → redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'id': coupon.pk})
        messages.success(request, f'Coupon "{coupon.code}" created successfully.')
        return redirect('manage:coupons')
    return redirect('manage:coupons')


@staff_required
@require_POST
def coupon_delete(request, pk):
    coupon = get_object_or_404(Coupon, pk=pk)
    coupon.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Coupon deleted.')
    return redirect('manage:coupons')


# ─── CUSTOMERS ───────────────────────────────────────────────────────────────
@staff_required
def customers_list(request):
    search = request.GET.get('q', '')
    # Work with UserProfile objects (template uses c.user.* and c.phone etc.)
    profiles = UserProfile.objects.select_related('user').filter(user__is_staff=False)
    if search:
        profiles = profiles.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search) |
            Q(phone__icontains=search)
        )
    return render(request, 'manage/customers.html', {'customers': profiles, 'search': search})


@staff_required
@require_POST
def customer_block(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_blocked = not profile.is_blocked
    profile.save()
    # AJAX callers get JSON; plain form/browser requests go back to the list
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'success': True, 'blocked': profile.is_blocked})
    messages.success(request, f"{user.get_full_name() or user.email} is now {'blocked' if profile.is_blocked else 'active'}.")
    return redirect('manage:customers')


@staff_required
def export_customers(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Phone', 'City', 'Orders', 'Total Spent', 'Joined', 'Status'])
    for u in User.objects.filter(is_staff=False).select_related('profile'):
        profile = getattr(u, 'profile', None)
        writer.writerow([u.get_full_name(), u.email, profile.phone if profile else '', profile.city if profile else '', u.orders.count(), u.orders.aggregate(s=Sum('total'))['s'] or 0, u.date_joined.strftime('%d %b %Y'), 'Blocked' if (profile and profile.is_blocked) else 'Active'])
    return response


# ─── REVIEWS ─────────────────────────────────────────────────────────────────
@staff_required
def reviews_list(request):
    product_filter = request.GET.get('product')
    status_filter = request.GET.get('status', 'all')
    qs = Review.objects.select_related('product', 'user').order_by('-created_at')
    if product_filter:
        qs = qs.filter(product_id=product_filter)
    if status_filter != 'all':
        qs = qs.filter(status=status_filter)
    products = Product.objects.all()
    return render(request, 'manage/reviews.html', {'reviews': qs, 'products': products, 'product_filter': product_filter, 'status_filter': status_filter})


@staff_required
def review_add(request):
    """Staff add a review by hand — e.g. feedback a real customer sent on
    WhatsApp / Instagram / in person. Saved as approved so it shows straight away."""
    products = Product.objects.order_by('name')
    errors = []
    form = {}
    if request.method == 'POST':
        form = request.POST
        name = form.get('reviewer_name', '').strip()
        body = form.get('body', '').strip()
        title = form.get('title', '').strip()
        product_id = form.get('product', '').strip()
        try:
            rating = int(form.get('rating', 5))
        except (TypeError, ValueError):
            rating = 0
        if not name:
            errors.append('Customer name is required.')
        if not body:
            errors.append('Review text is required.')
        if rating < 1 or rating > 5:
            errors.append('Rating must be between 1 and 5.')
        product = None
        if product_id:
            product = Product.objects.filter(pk=product_id).first()
            if not product:
                errors.append('Please choose a valid product.')
        photo = request.FILES.get('photo')
        if photo:
            from store.views import _validate_uploaded_image
            ok, msg = _validate_uploaded_image(photo)
            if not ok:
                errors.append(msg)
        if not errors:
            status = Review.STATUS_APPROVED if form.get('status', 'approved') == 'approved' else Review.STATUS_PENDING
            review = Review.objects.create(
                product=product,
                user=None,
                reviewer_name=name,
                rating=rating,
                title=title or body[:60],
                body=body,
                photo=photo,
                status=status,
                staff_reply=form.get('staff_reply', '').strip(),
                featured_on_home=bool(form.get('featured_on_home')) and status == Review.STATUS_APPROVED,
            )
            messages.success(request, f'Review by {review.reviewer_name} added.')
            return redirect('manage:reviews')
    return render(request, 'manage/review_form.html', {'products': products, 'errors': errors, 'form': form})


@staff_required
@require_POST
def review_approve(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.status = Review.STATUS_APPROVED
    reply = request.POST.get('reply', '')
    if reply:
        review.staff_reply = reply
    review.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Review approved.')
    return redirect('manage:reviews')


@staff_required
@require_POST
def review_reject(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.status = Review.STATUS_REJECTED
    review.save()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Review rejected.')
    return redirect('manage:reviews')


@staff_required
@require_POST
def review_delete(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Review deleted.')
    return redirect('manage:reviews')


@staff_required
@require_POST
def review_toggle_feature(request, pk):
    review = get_object_or_404(Review, pk=pk)
    if review.status != Review.STATUS_APPROVED:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Only approved reviews can be featured on the home page.'}, status=400)
        messages.error(request, 'Only approved reviews can be featured on the home page.')
        return redirect('manage:reviews')

    review.featured_on_home = not review.featured_on_home
    review.save(update_fields=['featured_on_home'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'featured_on_home': review.featured_on_home})
    messages.success(request, 'Updated.')
    return redirect('manage:reviews')


# ─── FAQS ────────────────────────────────────────────────────────────────────
@staff_required
def faqs_list(request):
    faqs = HelpFAQ.objects.all()
    return render(request, 'manage/faqs.html', {'faqs': faqs})


@staff_required
def faq_add(request):
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        answer = request.POST.get('answer', '').strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not question or not answer:
            if is_ajax:
                return JsonResponse({'success': False, 'message': 'Question and answer are required.'}, status=400)
            messages.error(request, 'Question and answer are required.')
            return redirect('manage:faqs')

        faq = HelpFAQ()
        faq.question = question
        faq.answer = answer
        faq.display_order = int(request.POST.get('display_order', 0) or 0)
        faq.is_active = 'is_active' in request.POST
        faq.save()

        if is_ajax:
            return JsonResponse({'success': True, 'id': faq.pk, 'question': faq.question})
        messages.success(request, 'FAQ added.')
        return redirect('manage:faqs')

    return redirect('manage:faqs')


@staff_required
def faq_edit(request, pk):
    faq = get_object_or_404(HelpFAQ, pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        faq.question = request.POST.get('question', faq.question)
        faq.answer = request.POST.get('answer', faq.answer)
        faq.display_order = int(request.POST.get('display_order', faq.display_order) or faq.display_order)
        faq.is_active = 'is_active' in request.POST
        faq.save()
        if is_ajax:
            return JsonResponse({'success': True})
        messages.success(request, 'FAQ updated.')
        return redirect('manage:faqs')
    if is_ajax:
        return JsonResponse({'id': faq.pk, 'question': faq.question, 'answer': faq.answer, 'display_order': faq.display_order, 'is_active': faq.is_active})
    return redirect('manage:faqs')


@staff_required
@require_POST
def faq_delete(request, pk):
    get_object_or_404(HelpFAQ, pk=pk).delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'FAQ deleted.')
    return redirect('manage:faqs')


# ─── TERMS & CONDITIONS ──────────────────────────────────────────────────────
@staff_required
def terms_list(request):
    terms = TermsCondition.objects.all()
    return render(request, 'manage/terms.html', {'terms': terms})


@staff_required
@require_POST
def terms_add(request):
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    if not title or not content:
        messages.error(request, 'Title and content are required.')
        return redirect('manage:terms')
    t = TermsCondition()
    t.title = title
    t.content = content
    t.display_order = int(request.POST.get('display_order', 0) or 0)
    t.is_active = 'is_active' in request.POST
    t.save()
    messages.success(request, 'Terms section added.')
    return redirect('manage:terms')


@staff_required
@require_POST
def terms_edit(request, pk):
    t = get_object_or_404(TermsCondition, pk=pk)
    t.title = request.POST.get('title', t.title).strip()
    t.content = request.POST.get('content', t.content).strip()
    t.display_order = int(request.POST.get('display_order', t.display_order) or t.display_order)
    t.is_active = 'is_active' in request.POST
    t.save()
    messages.success(request, 'Terms section updated.')
    return redirect('manage:terms')


@staff_required
@require_POST
def terms_delete(request, pk):
    get_object_or_404(TermsCondition, pk=pk).delete()
    messages.success(request, 'Terms section deleted.')
    return redirect('manage:terms')


# ─── Generic policy-section CRUD (used by Privacy/Refund/Shipping below) ────
def _policy_list(request, model, template):
    items = model.objects.all()
    return render(request, template, {'terms': items})


def _policy_add(request, model, redirect_name):
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    if not title or not content:
        messages.error(request, 'Title and content are required.')
        return redirect(redirect_name)
    obj = model()
    obj.title = title
    obj.content = content
    obj.display_order = int(request.POST.get('display_order', 0) or 0)
    obj.is_active = 'is_active' in request.POST
    obj.save()
    messages.success(request, 'Section added.')
    return redirect(redirect_name)


def _policy_edit(request, model, pk, redirect_name):
    obj = get_object_or_404(model, pk=pk)
    obj.title = request.POST.get('title', obj.title).strip()
    obj.content = request.POST.get('content', obj.content).strip()
    obj.display_order = int(request.POST.get('display_order', obj.display_order) or obj.display_order)
    obj.is_active = 'is_active' in request.POST
    obj.save()
    messages.success(request, 'Section updated.')
    return redirect(redirect_name)


def _policy_delete(request, model, pk, redirect_name):
    get_object_or_404(model, pk=pk).delete()
    messages.success(request, 'Section deleted.')
    return redirect(redirect_name)


# ─── PRIVACY POLICY ──────────────────────────────────────────────────────────
@staff_required
def privacy_list(request):
    return _policy_list(request, PrivacyPolicy, 'manage/privacy.html')


@staff_required
@require_POST
def privacy_add(request):
    return _policy_add(request, PrivacyPolicy, 'manage:privacy')


@staff_required
@require_POST
def privacy_edit(request, pk):
    return _policy_edit(request, PrivacyPolicy, pk, 'manage:privacy')


@staff_required
@require_POST
def privacy_delete(request, pk):
    return _policy_delete(request, PrivacyPolicy, pk, 'manage:privacy')


# ─── REFUND POLICY ───────────────────────────────────────────────────────────
@staff_required
def refund_list(request):
    return _policy_list(request, RefundPolicy, 'manage/refund.html')


@staff_required
@require_POST
def refund_add(request):
    return _policy_add(request, RefundPolicy, 'manage:refund')


@staff_required
@require_POST
def refund_edit(request, pk):
    return _policy_edit(request, RefundPolicy, pk, 'manage:refund')


@staff_required
@require_POST
def refund_delete(request, pk):
    return _policy_delete(request, RefundPolicy, pk, 'manage:refund')


# ─── SHIPPING POLICY ─────────────────────────────────────────────────────────
@staff_required
def shipping_list(request):
    return _policy_list(request, ShippingPolicy, 'manage/shipping.html')


@staff_required
@require_POST
def shipping_add(request):
    return _policy_add(request, ShippingPolicy, 'manage:shipping')


@staff_required
@require_POST
def shipping_edit(request, pk):
    return _policy_edit(request, ShippingPolicy, pk, 'manage:shipping')


@staff_required
@require_POST
def shipping_delete(request, pk):
    return _policy_delete(request, ShippingPolicy, pk, 'manage:shipping')


# ─── CUSTOM ORDER POLICY ─────────────────────────────────────────────────────
@staff_required
def custom_order_policy_list(request):
    return _policy_list(request, CustomOrderPolicy, 'manage/custom_order_policy.html')


@staff_required
@require_POST
def custom_order_policy_add(request):
    return _policy_add(request, CustomOrderPolicy, 'manage:custom_order_policy')


@staff_required
@require_POST
def custom_order_policy_edit(request, pk):
    return _policy_edit(request, CustomOrderPolicy, pk, 'manage:custom_order_policy')


@staff_required
@require_POST
def custom_order_policy_delete(request, pk):
    return _policy_delete(request, CustomOrderPolicy, pk, 'manage:custom_order_policy')


# ─── PRODUCT DISCLAIMER ───────────────────────────────────────────────────────
@staff_required
def product_disclaimer_list(request):
    return _policy_list(request, ProductDisclaimer, 'manage/product_disclaimer.html')


@staff_required
@require_POST
def product_disclaimer_add(request):
    return _policy_add(request, ProductDisclaimer, 'manage:product_disclaimer')


@staff_required
@require_POST
def product_disclaimer_edit(request, pk):
    return _policy_edit(request, ProductDisclaimer, pk, 'manage:product_disclaimer')


@staff_required
@require_POST
def product_disclaimer_delete(request, pk):
    return _policy_delete(request, ProductDisclaimer, pk, 'manage:product_disclaimer')


# ─── CONTACT INFO ────────────────────────────────────────────────────────────
@staff_required
def contact_info_edit(request):
    info, _ = ContactInfo.objects.get_or_create(pk=1)
    if request.method == 'POST':
        info.email = request.POST.get('email', info.email).strip()
        info.phone = request.POST.get('phone', '').strip()
        info.whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        info.address_line = request.POST.get('address_line', '').strip()
        info.business_hours = request.POST.get('business_hours', info.business_hours).strip()
        info.map_embed_url = request.POST.get('map_embed_url', '').strip()
        info.save()
        messages.success(request, 'Contact info updated.')
        return redirect('manage:contact_info')
    return render(request, 'manage/contact_info.html', {'info': info})


# ─── ENQUIRIES ───────────────────────────────────────────────────────────────
@staff_required
def enquiries_list(request):
    status_filter = request.GET.get('status', 'all')
    qs = Enquiry.objects.filter(enquiry_type=Enquiry.TYPE_GENERAL)
    if status_filter != 'all':
        qs = qs.filter(status=status_filter)
    return render(request, 'manage/enquiries.html', {'enquiries': qs, 'status_filter': status_filter})


@staff_required
def custom_enquiries_list(request):
    status_filter = request.GET.get('status', 'all')
    search = request.GET.get('q', '').strip()
    base = Enquiry.objects.filter(enquiry_type=Enquiry.TYPE_CUSTOMIZATION).select_related('product')
    counts = {
        'all': base.count(),
        'new': base.filter(status='new').count(),
        'in_progress': base.filter(status='in_progress').count(),
        'resolved': base.filter(status='resolved').count(),
    }
    qs = base
    if status_filter in ('new', 'in_progress', 'resolved'):
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(Q(full_name__icontains=search) | Q(phone__icontains=search) | Q(message__icontains=search) | Q(product__name__icontains=search))
    return render(request, 'manage/custom_enquiries.html', {
        'enquiries': qs, 'status_filter': status_filter, 'counts': counts, 'search': search,
    })


@staff_required
def export_custom_enquiries(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customization_enquiries.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Phone', 'Email', 'Product', 'Quantity', 'Budget', 'Request', 'Status', 'Staff note', 'Date'])
    def safe(v):
        v = '' if v is None else str(v)
        return "'" + v if v[:1] in ('=', '+', '-', '@') else v
    for e in Enquiry.objects.filter(enquiry_type=Enquiry.TYPE_CUSTOMIZATION).select_related('product'):
        writer.writerow([safe(e.full_name), safe(e.phone), safe(e.email), safe(e.product.name if e.product else ''),
                         e.quantity or '', safe(e.budget), safe(e.message), e.status, safe(e.staff_note),
                         e.created_at.strftime('%d/%m/%Y %H:%M')])
    return response


@staff_required
@require_POST
def enquiry_update_status(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    enquiry.status = request.POST.get('status', enquiry.status)
    note = request.POST.get('note', '')
    if note:
        enquiry.staff_note = note
    enquiry.save()
    return JsonResponse({'success': True})


@staff_required
@require_POST
def enquiry_delete(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    was_custom = enquiry.enquiry_type == Enquiry.TYPE_CUSTOMIZATION
    enquiry.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Enquiry deleted.')
    return redirect('manage:custom_enquiries' if was_custom else 'manage:enquiries')


@staff_required
def export_enquiries(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="enquiries.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Phone', 'Email', 'Subject', 'Message', 'Status', 'Date'])
    for e in Enquiry.objects.filter(enquiry_type=Enquiry.TYPE_GENERAL):
        writer.writerow([e.full_name, e.phone, e.email, e.subject, e.message, e.status, e.created_at.strftime('%d/%m/%Y %H:%M')])
    return response


# ─── BANNERS ─────────────────────────────────────────────────────────────────
@staff_required
def banners_list(request):
    banners = Banner.objects.all()
    return render(request, 'manage/banners.html', {'banners': banners})


@staff_required
def banner_add(request):
    if request.method == 'POST':
        banner = Banner()
        banner.title = request.POST.get('title', '')
        banner.cta_text = request.POST.get('cta_text', 'Shop Now')
        # cta_url comes from either the product picker auto-fill OR manual entry
        banner.cta_url = request.POST.get('cta_url', '/products/') or '/products/'
        banner.display_order = int(request.POST.get('display_order', 0) or 0)
        banner.is_active = 'is_active' in request.POST
        banner.save()
        for order, img in enumerate(request.FILES.getlist('images')):
            BannerImage.objects.create(banner=banner, image=img, display_order=order)
        messages.success(request, 'Banner added successfully.')
        return redirect('manage:banners')
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'manage/banner_form.html', {'banner': None, 'products': products})


@staff_required
def banner_edit(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    if request.method == 'POST':
        banner.title = request.POST.get('title', banner.title)
        banner.cta_text = request.POST.get('cta_text', banner.cta_text)
        banner.cta_url = request.POST.get('cta_url', banner.cta_url) or '/products/'
        banner.display_order = int(request.POST.get('display_order', banner.display_order) or banner.display_order)
        banner.is_active = 'is_active' in request.POST
        banner.save()
        existing_max = banner.gallery_images.count()
        for i, img in enumerate(request.FILES.getlist('images')):
            BannerImage.objects.create(banner=banner, image=img, display_order=existing_max + i)
        messages.success(request, 'Banner updated successfully.')
        return redirect('manage:banners')
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'manage/banner_form.html', {'banner': banner, 'products': products})


@staff_required
@require_POST
def banner_image_delete(request, pk):
    img = get_object_or_404(BannerImage, pk=pk)
    img.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Image removed.')
    return redirect('manage:banners')


@staff_required
@require_POST
def banner_delete(request, pk):
    get_object_or_404(Banner, pk=pk).delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    messages.success(request, 'Banner deleted.')
    return redirect('manage:banners')


@staff_required
@require_POST
def banner_toggle(request, pk):
    banner = get_object_or_404(Banner, pk=pk)
    banner.is_active = not banner.is_active
    banner.save()
    return JsonResponse({'success': True, 'is_active': banner.is_active})


# ─── ABOUT PAGE ──────────────────────────────────────────────────────────────
@staff_required
def about_page(request):
    content = AboutPageContent.objects.first()
    if not content:
        content = AboutPageContent()
        content.save()
    if request.method == 'POST':
        content.hero_heading = request.POST.get('hero_heading', content.hero_heading)
        content.hero_subheading = request.POST.get('hero_subheading', content.hero_subheading)
        content.story_title = request.POST.get('story_title', content.story_title)
        content.story_content = request.POST.get('story_content', content.story_content)
        content.mission_statement = request.POST.get('mission_statement', content.mission_statement)
        content.team_section_title = request.POST.get('team_section_title', content.team_section_title)
        content.team_subtitle = request.POST.get('team_subtitle', content.team_subtitle)
        content.team_quote = request.POST.get('team_quote', content.team_quote)
        content.save()
        messages.success(request, 'About page updated successfully.')
        return redirect('manage:about_page')
    return render(request, 'manage/about_page.html', {'content': content})


# ─── MANAGE LOGIN ────────────────────────────────────────────────────────────
@staff_required
def manage_logins(request):
    if request.session.get('staff_role') != 'admin':
        messages.error(request, 'Admin access required.')
        return redirect('manage:dashboard')
    staff_users = StaffUser.objects.all().order_by('-created_at')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            username = request.POST.get('username', '').strip()
            full_name = request.POST.get('full_name', '')
            role = request.POST.get('role', 'staff')
            password = request.POST.get('password', '')
            if username and password:
                staff = StaffUser(username=username, full_name=full_name, role=role)
                staff.set_password(password)
                staff.save()
                return JsonResponse({'success': True, 'id': staff.pk})
            return JsonResponse({'success': False, 'error': 'Username and password required'})
    return render(request, 'manage/manage_logins.html', {'staff_users': staff_users})


@staff_required
@require_POST
def staff_delete(request, pk):
    staff = get_object_or_404(StaffUser, pk=pk)
    if staff.role == 'admin':
        admin_count = StaffUser.objects.filter(role='admin', is_active=True).count()
        if admin_count <= 1:
            return JsonResponse({'success': False, 'error': 'Cannot delete the last admin'})
    staff.delete()
    return JsonResponse({'success': True})


# ─── SETTINGS ────────────────────────────────────────────────────────────────
@staff_required
def store_settings_view(request):
    settings = StoreSettings.objects.first()
    if not settings:
        settings = StoreSettings()
        settings.save()
    if request.method == 'POST':
        settings.store_name = request.POST.get('store_name', settings.store_name)
        def _autocrop_transparent(django_file):
            """Trim transparent margins from uploaded logos so they render at
            full size in the navbar/footer instead of shrinking inside their
            own empty padding. Always leaves the original upload rewound so
            it can still be sent to storage (Cloudinary) untouched."""
            def _original():
                try:
                    django_file.seek(0)
                except Exception:
                    pass
                return django_file
            try:
                from PIL import Image
                from io import BytesIO
                from django.core.files.base import ContentFile
                django_file.seek(0)
                img = Image.open(django_file).convert('RGBA')
                alpha = img.getchannel('A').point(lambda a: 255 if a > 60 else 0)
                bbox = alpha.getbbox()
                if not bbox:
                    return _original()
                l, t, r, b = bbox
                pad = max(4, int(0.02 * max(img.size)))
                l = max(0, l - pad); t = max(0, t - pad)
                r = min(img.width, r + pad); b = min(img.height, b + pad)
                if (r - l) >= img.width - 8 and (b - t) >= img.height - 8:
                    return _original()  # nothing meaningful to trim
                out = BytesIO()
                img.crop((l, t, r, b)).save(out, 'PNG')
                base = django_file.name.rsplit('.', 1)[0] or 'logo'
                return ContentFile(out.getvalue(), name=base + '.png')
            except Exception:
                return _original()

        if request.FILES.get('logo'):
            settings.logo = _autocrop_transparent(request.FILES['logo'])
        if request.FILES.get('footer_logo'):
            settings.footer_logo = _autocrop_transparent(request.FILES['footer_logo'])
        settings.announcement_bar_enabled = 'announcement_bar_enabled' in request.POST
        settings.announcement_bar_text = request.POST.get('announcement_bar_text', settings.announcement_bar_text).strip()
        settings.instagram_url = request.POST.get('instagram_url', settings.instagram_url).strip()
        settings.free_delivery_above = request.POST.get('free_delivery_above', settings.free_delivery_above) or 0
        settings.free_gift_above = request.POST.get('free_gift_above', settings.free_gift_above) or 0
        settings.gift_wrap_enabled = 'gift_wrap_enabled' in request.POST
        settings.gift_wrap_price = request.POST.get('gift_wrap_price', settings.gift_wrap_price) or 99
        default_sort = request.POST.get('default_sort', settings.default_sort)
        if default_sort in dict(StoreSettings.DEFAULT_SORT_CHOICES):
            settings.default_sort = default_sort
        settings.standard_delivery_days = int(request.POST.get('standard_delivery_days', settings.standard_delivery_days) or 7)
        settings.express_delivery_days = int(request.POST.get('express_delivery_days', settings.express_delivery_days) or 3)
        settings.new_order_alerts = 'new_order_alerts' in request.POST
        settings.review_notifications = 'review_notifications' in request.POST
        settings.low_stock_alerts = 'low_stock_alerts' in request.POST
        settings.invoice_enabled = 'invoice_enabled' in request.POST
        settings.company_legal_name = request.POST.get('company_legal_name', settings.company_legal_name).strip()
        settings.company_address = request.POST.get('company_address', settings.company_address).strip()
        settings.company_phone = request.POST.get('company_phone', settings.company_phone).strip()
        settings.company_email = request.POST.get('company_email', settings.company_email).strip()
        settings.gst_number = request.POST.get('gst_number', settings.gst_number).strip()
        settings.show_gst_on_invoice = 'show_gst_on_invoice' in request.POST
        settings.invoice_footer_note = request.POST.get('invoice_footer_note', settings.invoice_footer_note).strip()
        try:
            settings.save()
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception('Settings save failed')
            messages.error(request, f'Could not save settings (logo upload problem?): {e}')
            return redirect('manage:settings')
        messages.success(request, 'Settings saved.')
        return redirect('manage:settings')
    razorpay_configured = bool(getattr(django_settings, 'RAZORPAY_KEY_ID', '') and getattr(django_settings, 'RAZORPAY_KEY_SECRET', ''))
    return render(request, 'manage/settings.html', {'settings': settings, 'razorpay_configured': razorpay_configured})
