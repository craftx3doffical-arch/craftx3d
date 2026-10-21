from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    is_blocked = models.BooleanField(default=False)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = 'Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:250]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CategoryImage(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='categories/')
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']


class PackagingType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ImageField(upload_to='packaging/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.name


class ColorOption(models.Model):
    name = models.CharField(max_length=100)
    hex_code = models.CharField(max_length=7, default='#000000')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


CUSTOMIZATION_TYPE_CHOICES = [
    ('none', 'None — Normal Product'),
    ('photo', '📸 Photography Accessories'),
    ('miniature', '🧍 3D Miniatures'),
    ('field', '🧩 Field Customization'),
]


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='MRP / strikethrough price')

    video = models.FileField(upload_to='product_videos/', blank=True, null=True, help_text='Optional short product video — plays in the gallery when tapped')

    # Parcel / packaging charge — a flat per-unit fee shown separately from
    # the product price (Amazon-style "+ ₹X packaging"), added into the
    # cart/order total as its own line rather than folded into the price.
    show_parcel_charge = models.BooleanField(default=False, help_text='Charge a separate parcel/packaging fee for this product')
    parcel_charge_title = models.CharField(max_length=100, default='Parcel & Packaging Fee', blank=True, help_text='Label shown next to the fee, e.g. "Parcel & Packaging Fee"')
    parcel_charge_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, blank=True, help_text='Flat fee per unit, e.g. 100.00')
    parcel_charge_free_label = models.CharField(max_length=100, default='Free Parcel & Packaging', blank=True, help_text='Badge text shown on the product page when the fee is off')

    customization_type = models.CharField(max_length=20, choices=CUSTOMIZATION_TYPE_CHOICES, default='none')
    description = models.TextField(blank=True)
    description_title = models.CharField(max_length=100, default='Product Description', blank=True)
    materials = models.TextField(blank=True)
    materials_title = models.CharField(max_length=100, default='Materials & Specifications', blank=True)
    dimensions = models.TextField(blank=True)
    production_info = models.TextField(blank=True)
    production_info_title = models.CharField(max_length=100, default='Production & Shipping', blank=True)

    # Extra custom info sections (title + content), same style as
    # Description/Materials/Production — shown only when both filled in.
    # Each can optionally include a photo (e.g. "How it's made" steps).
    extra_title_1 = models.CharField(max_length=100, blank=True)
    extra_content_1 = models.TextField(blank=True)
    extra_image_1 = models.ImageField(upload_to='product_extra/', blank=True, null=True)
    extra_title_2 = models.CharField(max_length=100, blank=True)
    extra_content_2 = models.TextField(blank=True)
    extra_image_2 = models.ImageField(upload_to='product_extra/', blank=True, null=True)
    extra_title_3 = models.CharField(max_length=100, blank=True)
    extra_content_3 = models.TextField(blank=True)
    extra_image_3 = models.ImageField(upload_to='product_extra/', blank=True, null=True)
    extra_title_4 = models.CharField(max_length=100, blank=True)
    extra_content_4 = models.TextField(blank=True)
    extra_image_4 = models.ImageField(upload_to='product_extra/', blank=True, null=True)
    extra_title_5 = models.CharField(max_length=100, blank=True)
    extra_content_5 = models.TextField(blank=True)
    extra_image_5 = models.ImageField(upload_to='product_extra/', blank=True, null=True)

    # Delivery settings
    show_standard_delivery = models.BooleanField(default=True)
    standard_delivery_title = models.CharField(max_length=100, default='Standard Delivery', blank=True)
    standard_delivery_days = models.IntegerField(default=7)
    show_express_delivery = models.BooleanField(default=True)
    express_delivery_title = models.CharField(max_length=100, default='Express Delivery', blank=True)
    express_delivery_days = models.IntegerField(default=3)
    show_production_time = models.BooleanField(default=False, help_text='Show a separate Production Time card on the product page')
    production_time_title = models.CharField(max_length=100, default='Production Time', blank=True)
    production_time_days = models.IntegerField(default=2)
    show_free_delivery = models.BooleanField(default=False)
    free_delivery_above = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    show_cod = models.BooleanField(default=False)
    cod_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    show_delivery_estimate = models.BooleanField(default=False, help_text='Show "Order today — estimated delivery: [date range]" on the product page')

    # Feature tick list (e.g. "3D-printed to order", "Eco-friendly material")
    show_feature_ticks = models.BooleanField(default=False)
    feature_tick_1 = models.CharField(max_length=150, blank=True, default='3D-printed to order in premium PLA')
    feature_tick_2 = models.CharField(max_length=150, blank=True, default='Eco-friendly, plant-based material')
    feature_tick_3 = models.CharField(max_length=150, blank=True, default='Designed & handcrafted in India')

    # Short intro paragraph shown directly on the page (separate from the
    # full Description accordion tab)
    show_short_description = models.BooleanField(default=False)
    short_description = models.TextField(blank=True, help_text='A short intro paragraph shown directly on the page, above the accordion tabs')

    # Trust badges row (Free shipping / COD / Returns / Material, etc.) —
    # leave any text field blank to hide that one slot.
    show_trust_badges = models.BooleanField(default=False)
    trust_badge_1 = models.CharField(max_length=100, blank=True, default='Free shipping PAN India')
    trust_badge_2 = models.CharField(max_length=100, blank=True, default='Cash on Delivery')
    trust_badge_3 = models.CharField(max_length=100, blank=True, default='Easy 7-day returns')
    trust_badge_4 = models.CharField(max_length=100, blank=True, default='')

    # Materials/specs details table
    show_materials_table = models.BooleanField(default=False)
    materials_table_rows = models.JSONField(default=list, blank=True, help_text='List of {label, value} rows, freely add/edit/delete from the product form')

    # "About Our Craft" callout block
    show_about_craft = models.BooleanField(default=False)
    about_craft_title = models.CharField(max_length=100, blank=True, default='About Our Craft')
    about_craft_text = models.TextField(blank=True)
    
    # Stock
    stock = models.IntegerField(default=100)
    track_inventory = models.BooleanField(default=True, help_text='Turn off for made-to-order items with no fixed stock count — always shown as available.')
    low_stock_threshold = models.IntegerField(default=10)
    
    # Flags
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False, help_text='Shows in the "Bestsellers" nav link/page')
    photo_upload_enabled = models.BooleanField(default=False)
    
    # Customization JSON data (stores all complex customization fields)
    customization_data = models.JSONField(default=dict, blank=True)
    
    # Section order for customization display
    section_order = models.JSONField(default=list, blank=True)
    
    # Packaging
    available_packaging = models.ManyToManyField(PackagingType, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)[:240] or 'product'
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def discount_percent(self):
        if self.compare_price and self.compare_price > self.base_price:
            return round(((self.compare_price - self.base_price) / self.compare_price) * 100)
        return 0

    @property
    def is_new(self):
        """True for products added in the last 30 days — drives the '✦ New' chip."""
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at >= timezone.now() - timedelta(days=30)

    @property
    def extra_info_sections(self):
        """Returns the extra custom info sections that have both a title and
        content filled in, as a list of {'title', 'content', 'image'} dicts."""
        sections = []
        for i in range(1, 6):
            title = getattr(self, f'extra_title_{i}', '').strip()
            content = getattr(self, f'extra_content_{i}', '').strip()
            image = getattr(self, f'extra_image_{i}', None)
            if title and content:
                sections.append({'title': title, 'content': content, 'image': image})
        return sections

    @property
    def delivery_estimate_dates(self):
        """(start_date, end_date) for 'Order today — estimated delivery: ...',
        computed from this product's express/standard delivery day settings."""
        from datetime import timedelta
        from django.utils import timezone
        today = timezone.localdate()
        low = self.express_delivery_days if self.show_express_delivery else self.standard_delivery_days
        high = self.standard_delivery_days
        if high < low:
            low, high = high, low
        return today + timedelta(days=low), today + timedelta(days=high)

    @property
    def is_in_stock(self):
        """True if this product can be ordered right now. Products with
        inventory tracking turned off are always considered in stock —
        useful for made-to-order items with no fixed stock count."""
        if not self.track_inventory:
            return True
        return self.stock > 0

    @property
    def available_stock(self):
        """Effective stock count for quantity limits. A very high number
        when tracking is off, so quantity selectors/limits don't
        artificially cap made-to-order items."""
        if not self.track_inventory:
            return 999999
        return self.stock

    @property
    def main_image(self):
        img = self.images.filter(is_main=True).first()
        if not img:
            img = self.images.first()
        return img


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    is_main = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['-is_main', 'display_order']


class ProductFAQ(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=300)
    answer = models.TextField()
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']


class SizeOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    label = models.CharField(max_length=50)
    extra_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']


class PackSizeOption(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pack_sizes')
    label = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    min_qty = models.IntegerField(default=1)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']


class Favorite(models.Model):
    """A customer's saved/wishlisted product — the heart icon on product
    cards and the product detail page."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} ♥ {self.product}"


class Review(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    reviewer_name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    body = models.TextField()
    photo = models.ImageField(upload_to='reviews/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    staff_reply = models.TextField(blank=True)
    featured_on_home = models.BooleanField(default=False, help_text='Hand-picked by staff to show in the "What Customers Say" section on the home page.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reviewer_name} - {self.rating}★"


class Coupon(models.Model):
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_FLAT = 'flat'
    DISCOUNT_TYPE_CHOICES = [
        (DISCOUNT_PERCENT, 'Percentage (%)'),
        (DISCOUNT_FLAT, 'Flat Amount (₹)'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.IntegerField(default=0)
    used_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_secret = models.BooleanField(
        default=False,
        help_text='Secret coupons work when typed but never appear in any public listing or suggestion UI.',
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is not active"
        if self.valid_from and now < self.valid_from:
            return False, "Coupon is not yet valid"
        if self.valid_until and now > self.valid_until:
            return False, "Coupon has expired"
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False, "Coupon usage limit reached"
        return True, "Valid"

    def get_discount_amount(self, subtotal):
        if self.discount_type == self.DISCOUNT_PERCENT:
            return (subtotal * self.discount_value) / 100
        return min(self.discount_value, subtotal)



INDIAN_STATES = [
    'Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa',
    'Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala',
    'Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland',
    'Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura',
    'Uttar Pradesh','Uttarakhand','West Bengal',
    'Andaman and Nicobar Islands','Chandigarh',
    'Dadra and Nagar Haveli and Daman and Diu','Delhi',
    'Jammu and Kashmir','Ladakh','Lakshadweep','Puducherry',
]


class SavedAddress(models.Model):
    """Customer's saved delivery address — supports multiple addresses per user."""
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_addresses')
    full_name     = models.CharField(max_length=120)
    phone         = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True)
    address_line1 = models.CharField(max_length=250, verbose_name='Flat / House no. / Building')
    address_line2 = models.CharField(max_length=250, blank=True, verbose_name='Area / Street / Village')
    landmark      = models.CharField(max_length=200, blank=True)
    city          = models.CharField(max_length=100)
    state         = models.CharField(max_length=100)
    pincode       = models.CharField(max_length=10)
    is_default    = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.full_name} — {self.city} {self.pincode}'

    def save(self, *args, **kwargs):
        if self.is_default:
            SavedAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def combined_address(self):
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        if self.landmark:
            parts.append(f'Near {self.landmark}')
        return ', '.join(parts)

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    gift_wrap = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user or self.session_key}"

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def parcel_charge_total(self):
        """Sum of every item's parcel/packaging fee — shown as its own
        line in the cart/checkout/invoice, same pattern as gift wrap."""
        return sum(item.parcel_charge_total for item in self.items.all())

    @property
    def gift_wrap_price(self):
        try:
            settings = StoreSettings.objects.first()
            if settings and self.gift_wrap:
                return settings.gift_wrap_price
        except:
            pass
        return 99

    @property
    def discount_amount(self):
        if self.coupon:
            valid, _ = self.coupon.is_valid()
            if valid and self.subtotal >= self.coupon.min_order_value:
                return self.coupon.get_discount_amount(self.subtotal)
        return 0

    @property
    def total(self):
        t = self.subtotal - self.discount_amount + self.parcel_charge_total
        if self.gift_wrap:
            t += self.gift_wrap_price
        return max(t, 0)

    @property
    def item_count(self):
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    customization_data = models.JSONField(default=dict, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    selected_size = models.CharField(max_length=50, blank=True)
    selected_pack = models.CharField(max_length=100, blank=True)
    selected_packaging = models.ForeignKey(PackagingType, on_delete=models.SET_NULL, null=True, blank=True)
    # Snapshot of the product's parcel/packaging fee at the time it was added
    # to the cart, so a later price change in the manage portal doesn't
    # silently change what's sitting in someone's cart.
    parcel_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def total_price(self):
        packaging_price = self.selected_packaging.price if self.selected_packaging else 0
        return (self.unit_price + packaging_price) * self.quantity

    @property
    def parcel_charge_total(self):
        return self.parcel_charge * self.quantity


ORDER_STATUS_CHOICES = [
    ('awaiting_payment', '💳 Awaiting Payment'),
    ('pending', '⏳ Pending'),
    ('printing', '🖨️ Printing'),
    ('shipped', '🚚 Shipped'),
    ('delivered', '✅ Delivered'),
    ('cancelled', '❌ Cancelled'),
]

PAYMENT_METHOD_CHOICES = [
    ('online', 'Online Payment'),
]


class Order(models.Model):
    order_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Contact
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    
    # Address
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    # Order details
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='awaiting_payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='online')

    # Online payment (Razorpay) tracking
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gift_wrap = models.BooleanField(default=False)
    gift_wrap_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    parcel_charge_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Coupon
    coupon_code = models.CharField(max_length=50, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    staff_note = models.TextField(blank=True)
    
    # Tracking
    tracking_number = models.CharField(max_length=100, blank=True)
    courier = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_id:
            import random
            self.order_id = f"CX{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)

    def restore_stock(self):
        """Add each ordered item's quantity back to product stock. Used when
        an order is cancelled or when online payment fails/expires, so stock
        reserved at order-creation time isn't lost. Skipped for products with
        inventory tracking off, since their stock was never decremented."""
        from django.db.models import F
        for item in self.items.all():
            if item.product_id and item.product.track_inventory:
                Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)

    def __str__(self):
        return f"Order #{self.order_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot of the per-unit parcel/packaging fee at order time — shown
    # as its own line on invoices, same as unit_price is snapshotted.
    parcel_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    customization_data = models.JSONField(default=dict, blank=True)
    
    # For uploaded images in customization
    uploaded_images = models.JSONField(default=list, blank=True)
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity

    @property
    def parcel_charge_total(self):
        return self.parcel_charge * self.quantity


class OrderItemImage(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='order_items/')
    slot_label = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class HelpFAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.question


class TermsCondition(models.Model):
    """A single editable Terms & Conditions section, shown to customers at
    signup and on the /terms page, and managed from the staff portal."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return self.title


class PrivacyPolicy(models.Model):
    """A single editable Privacy Policy section, shown on the /privacy page
    and managed from the staff portal. Separate table from TermsCondition."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name_plural = 'Privacy Policy Sections'

    def __str__(self):
        return self.title


class RefundPolicy(models.Model):
    """A single editable Refund Policy section, shown on the /refund-policy
    page and managed from the staff portal. Separate table from the others."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name_plural = 'Refund Policy Sections'

    def __str__(self):
        return self.title


class ShippingPolicy(models.Model):
    """A single editable Shipping Policy section, shown on the
    /shipping-policy page and managed from the staff portal."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name_plural = 'Shipping Policy Sections'


class CustomOrderPolicy(models.Model):
    """A single editable Custom Order Policy section, shown on the
    /custom-order-policy page and managed from the staff portal."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name_plural = 'Custom Order Policy Sections'


class ProductDisclaimer(models.Model):
    """A single editable Product Disclaimer section, shown on the
    /product-disclaimer page and managed from the staff portal."""
    title = models.CharField(max_length=300)
    content = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'id']
        verbose_name_plural = 'Product Disclaimer Sections'

    def __str__(self):
        return self.title


class ContactInfo(models.Model):
    """Contact details shown on the /contact page and in the footer.
    Singleton-style, like StoreSettings — one row holds the current info."""
    email = models.EmailField(default='supportcraftx3dstudio@gmail.com')
    phone = models.CharField(max_length=20, blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, help_text='Digits only with country code, e.g. 919500295991')
    address_line = models.TextField(blank=True)
    business_hours = models.CharField(max_length=200, default='Mon\u2013Sat, 9 AM \u2013 7 PM')
    map_embed_url = models.URLField(blank=True, help_text='Optional Google Maps embed URL')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Contact Info'

    def __str__(self):
        return 'Contact Info'


class Enquiry(models.Model):
    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (STATUS_NEW, '🔴 New'),
        (STATUS_IN_PROGRESS, '🟡 In Progress'),
        (STATUS_RESOLVED, '🟢 Resolved'),
    ]

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    image = models.ImageField(upload_to='enquiries/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiries'

    def __str__(self):
        return f"{self.full_name} - {self.subject}"


class Banner(models.Model):
    title = models.CharField(max_length=200, blank=True)   # internal label, not shown to visitors
    cta_text = models.CharField(max_length=100, default='Shop Now')
    cta_url = models.CharField(max_length=200, default='/products/')  # product URL set via product picker
    subtitle = models.CharField(max_length=300, blank=True)
    promo_code = models.CharField(max_length=50, blank=True)
    offer_text = models.CharField(max_length=200, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    image1 = models.ImageField(upload_to='banners/', blank=True, null=True)
    image2 = models.ImageField(upload_to='banners/', blank=True, null=True)
    image3 = models.ImageField(upload_to='banners/', blank=True, null=True)
    image4 = models.ImageField(upload_to='banners/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.title

    @property
    def all_images(self):
        """Images for this banner in order — BannerImage gallery, then legacy fields."""
        images = list(self.gallery_images.all())
        if images:
            return [img.image for img in images]
        legacy = [self.image1, self.image2, self.image3, self.image4]
        return [img for img in legacy if img]

    @property
    def effective_link(self):
        """URL to navigate to when banner is clicked — cta_url (set via product picker or manually)."""
        return self.cta_url or '/products/'


class BannerImage(models.Model):
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='banners/')
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['display_order']


class AboutPageContent(models.Model):
    hero_heading = models.CharField(max_length=200, default='We Are CraftiX 3D')
    hero_subheading = models.CharField(max_length=300, default='A creative 3D printing brand born from passion, innovation, and the belief that every idea deserves its own shape.')
    story_title = models.CharField(max_length=200, default='Our Story')
    story_content = models.TextField(default='CraftX3D was started by four young minds with a shared passion for innovation, customization, and turning bold ideas into reality.')
    mission_statement = models.TextField(default='Where imagination meets precision. Every piece crafted with care, creativity, and cutting-edge 3D printing technology.')
    team_section_title = models.CharField(max_length=200, default='The Team Behind CraftX3D')
    team_subtitle = models.CharField(max_length=300, default='Four young minds. One shared vision.')
    team_quote = models.TextField(default='We started CraftX3D because we believed the world needed more personalized, creative products — things that truly reflect who you are. — The CraftX3D Team')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "About Page Content"


class StoreSettings(models.Model):
    store_name = models.CharField(max_length=200, default='CraftX3D')

    # ── Branding ─────────────────────────────────────────────────────────
    logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Shown in the navbar, footer, and staff portal. Leave blank to use the text wordmark.')
    footer_logo = models.ImageField(upload_to='branding/', blank=True, null=True, help_text='Light/white version of the logo for the dark footer. Falls back to the built-in light wordmark if blank.')

    # ── Announcement bar ─────────────────────────────────────────────────
    announcement_bar_enabled = models.BooleanField(default=False)
    announcement_bar_text = models.CharField(max_length=255, blank=True, default='', help_text='e.g. "Flat 15% off on all prepaid orders"')

    # ── Social ───────────────────────────────────────────────────────────
    instagram_url = models.URLField(blank=True, help_text='Full profile URL, e.g. https://instagram.com/craftx3d')

    # ── Products page default sort ──────────────────────────────────────
    SORT_NEWEST = 'newest'
    SORT_BEST_SELLING = 'popular'
    SORT_PRICE_LOW = 'price_low'
    SORT_PRICE_HIGH = 'price_high'
    DEFAULT_SORT_CHOICES = [
        (SORT_NEWEST, 'Newest First'),
        (SORT_BEST_SELLING, 'Best Selling'),
        (SORT_PRICE_LOW, 'Price: Low to High'),
        (SORT_PRICE_HIGH, 'Price: High to Low'),
    ]
    default_sort = models.CharField(
        max_length=20, choices=DEFAULT_SORT_CHOICES, default=SORT_NEWEST,
        help_text='Sort order shown on /products/ when a customer hasn\'t picked one — the "Sort by" dropdown opens on this option.',
    )

    cod_available = models.BooleanField(default=True)
    free_delivery_above = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    free_gift_above = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gift_wrap_enabled = models.BooleanField(default=True)
    gift_wrap_price = models.DecimalField(max_digits=10, decimal_places=2, default=99)
    standard_delivery_days = models.IntegerField(default=7)
    express_delivery_days = models.IntegerField(default=3)
    prepaid_cod_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_order_alerts = models.BooleanField(default=True)
    review_notifications = models.BooleanField(default=True)
    low_stock_alerts = models.BooleanField(default=True)

    # ── Invoice / Company details ───────────────────────────────────────────
    invoice_enabled = models.BooleanField(default=True)
    company_legal_name = models.CharField(max_length=200, blank=True)
    company_address = models.TextField(blank=True)
    company_phone = models.CharField(max_length=30, blank=True)
    company_email = models.EmailField(blank=True)
    gst_number = models.CharField(max_length=30, blank=True)
    show_gst_on_invoice = models.BooleanField(default=False)
    invoice_footer_note = models.CharField(max_length=255, blank=True, default='Thank you for shopping with us!')

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Store Settings"
