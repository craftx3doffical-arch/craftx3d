"""Regression tests for: size/price in cart, cart removal, and unpaid orders."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from store.models import Cart, CartItem, Category, Coupon, Order, Product
from store.views import expire_stale_unpaid_orders

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
KEYS = dict(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret')
ADDR = dict(full_name='A B', phone='9500000000', email='a@b.com', address='1 St',
            city='Salem', state='Tamil Nadu', pincode='635601')

BUILDER = {
    'section_order': ['size_options'],
    'sections': {'size_options': {'enabled': True, 'title': 'Select Size', 'sizes': [
        {'label': '4 INCH', 'extra_price': 0},
        {'label': '6 INCH', 'extra_price': 799},
        {'label': '10 INCH', 'extra_price': 1999},
    ]}},
}


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@x.com', 'pw')
        self.client.force_login(self.user)
        cat = Category.objects.create(name='Idols', slug='idols')
        self.p = Product.objects.create(
            name='Peacock', slug='peacock', category=cat, base_price=Decimal('399'),
            customization_data=BUILDER, track_inventory=True, stock=10)

    def add(self, size, qty=1):
        return self.client.post(f'/cart/add/{self.p.pk}/', {'quantity': qty, 'custom_size': size}, **AJAX)


class SizePriceTests(Base):
    def test_each_size_is_priced_and_stored_correctly(self):
        for size, price in [('4 INCH', 399), ('6 INCH', 1198), ('10 INCH', 2398)]:
            self.assertEqual(self.add(size).status_code, 200)
            item = CartItem.objects.filter(product=self.p).latest('pk')
            self.assertEqual(item.unit_price, Decimal(price))
            self.assertEqual(item.customization_data['choices']['Select Size'], size)

    def test_missing_or_unknown_size_is_rejected(self):
        self.assertEqual(self.add('').status_code, 400)
        self.assertEqual(self.add('99 INCH').status_code, 400)
        self.assertFalse(CartItem.objects.exists())


class CartRemovalTests(Base):
    def test_minus_on_quantity_one_reports_removed(self):
        self.add('4 INCH')
        item = CartItem.objects.get()
        r = self.client.post(f'/cart/update/{item.pk}/', {'action': 'decrease'}, **AJAX).json()
        self.assertTrue(r['success'] and r['removed'])
        self.assertEqual(r['quantity'], 0)
        self.assertFalse(CartItem.objects.exists())

    def test_removing_an_already_removed_item_is_not_a_404(self):
        self.add('4 INCH')
        item = CartItem.objects.get()
        self.client.post(f'/cart/update/{item.pk}/', {'action': 'remove'}, **AJAX)
        r = self.client.post(f'/cart/update/{item.pk}/', {'action': 'remove'}, **AJAX)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['already_removed'])


@override_settings(**KEYS)
class UnpaidOrderTests(Base):
    def checkout(self):
        r = self.client.post('/checkout/', ADDR)
        self.assertEqual(r.status_code, 302)
        return Order.objects.latest('pk')

    def test_checkout_creates_draft_hidden_from_customer(self):
        self.add('10 INCH')
        order = self.checkout()
        self.assertEqual((order.status, order.payment_status), ('awaiting_payment', 'pending'))
        self.assertEqual(self.p.__class__.objects.get(pk=self.p.pk).stock, 9)
        self.assertNotIn(order.order_id, self.client.get('/my-orders/').content.decode())

    def test_customer_cancel_restores_stock_cart_size_and_price(self):
        self.add('10 INCH')
        order = self.checkout()
        self.client.get(f'/payment/{order.order_id}/cancel/')
        order.refresh_from_db()
        self.assertEqual((order.status, order.payment_status), ('cancelled', 'failed'))
        self.assertEqual(Product.objects.get(pk=self.p.pk).stock, 10)
        item = CartItem.objects.get()
        self.assertEqual(item.unit_price, Decimal('2398'))
        self.assertEqual(item.customization_data['choices']['Select Size'], '10 INCH')

    def test_abandoned_order_is_cancelled_after_timeout(self):
        self.add('6 INCH')
        order = self.checkout()
        # not old enough yet -> untouched
        expire_stale_unpaid_orders()
        order.refresh_from_db(); self.assertEqual(order.status, 'awaiting_payment')
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=30))
        self.assertEqual(expire_stale_unpaid_orders(), 1)
        order.refresh_from_db()
        self.assertEqual((order.status, order.payment_status), ('cancelled', 'failed'))
        self.assertEqual(Product.objects.get(pk=self.p.pk).stock, 10)

    def test_stale_order_is_confirmed_if_razorpay_says_it_was_paid(self):
        self.add('4 INCH')
        order = self.checkout()
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=30), razorpay_order_id='order_abc')
        fake = mock.Mock()
        fake.order.payments.return_value = {'items': [{'id': 'pay_1', 'status': 'captured'}]}
        with mock.patch('razorpay.Client', return_value=fake):
            expire_stale_unpaid_orders()
        order.refresh_from_db()
        self.assertEqual((order.status, order.payment_status, order.razorpay_payment_id),
                         ('pending', 'paid', 'pay_1'))

    def test_stale_order_is_left_alone_if_razorpay_cannot_be_reached(self):
        self.add('4 INCH')
        order = self.checkout()
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(minutes=30), razorpay_order_id='order_abc')
        with mock.patch('razorpay.Client', side_effect=RuntimeError('network')):
            expire_stale_unpaid_orders()
        order.refresh_from_db()
        self.assertEqual(order.status, 'awaiting_payment')   # never cancel a maybe-paid order blindly

    def test_coupon_use_is_given_back_on_cancel(self):
        c = Coupon.objects.create(code='SAVE', discount_type='fixed', discount_value=Decimal('10'),
                                  is_active=True) if hasattr(Coupon, 'discount_type') else None
        if c is None:
            self.skipTest('Coupon model shape differs')
        self.add('4 INCH')
        cart = Cart.objects.get(user=self.user); cart.coupon = c; cart.save()
        order = self.checkout()
        c.refresh_from_db(); used = c.used_count
        self.client.get(f'/payment/{order.order_id}/cancel/')
        c.refresh_from_db()
        self.assertEqual(c.used_count, used - 1)


@override_settings(RAZORPAY_KEY_ID='', RAZORPAY_KEY_SECRET='')
class PaymentNotConfiguredTests(Base):
    def test_no_order_is_created_when_payment_is_unavailable(self):
        self.add('4 INCH')
        r = self.client.post('/checkout/', ADDR)
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Order.objects.exists())
        self.assertTrue(CartItem.objects.exists())        # cart untouched
