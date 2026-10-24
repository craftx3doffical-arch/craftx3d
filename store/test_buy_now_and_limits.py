"""Tests for: Buy Now (only that product), per-order quantity limit, free-parcel text."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from store.models import Cart, CartItem, Category, Order, Product

AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
KEYS = dict(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret')
ADDR = dict(full_name='A B', phone='9500000000', email='a@b.com', address='1 St',
            city='Salem', state='Tamil Nadu', pincode='635601')


class Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', 'u@x.com', 'pw')
        self.client.force_login(self.user)
        cat = Category.objects.create(name='Idols', slug='idols')
        self.a = Product.objects.create(name='Alpha', slug='alpha', category=cat,
                                        base_price=Decimal('500'), track_inventory=True, stock=50,
                                        max_order_quantity=10)
        self.b = Product.objects.create(name='Beta', slug='beta', category=cat,
                                        base_price=Decimal('300'), track_inventory=True, stock=50,
                                        max_order_quantity=10)

    def add(self, product, qty=1, buy_now=False):
        data = {'quantity': qty}
        if buy_now:
            data['buy_now'] = '1'
        return self.client.post(f'/cart/add/{product.pk}/', data, **AJAX)


class OrderLimitTests(Base):
    def test_cannot_add_more_than_the_limit_at_once(self):
        r = self.add(self.a, 11)
        self.assertFalse(r.json()['success'])
        self.assertFalse(CartItem.objects.exists())

    def test_limit_counts_what_is_already_in_the_cart(self):
        self.assertTrue(self.add(self.a, 10).json()['success'])
        self.assertFalse(self.add(self.a, 1).json()['success'])

    def test_plus_button_in_cart_stops_at_the_limit(self):
        self.add(self.a, 10)
        item = CartItem.objects.get()
        r = self.client.post(f'/cart/update/{item.pk}/', {'action': 'increase'}, **AJAX)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 10)
        self.assertTrue(r.json()['limit_message'])

    def test_zero_means_no_limit(self):
        Product.objects.filter(pk=self.a.pk).update(max_order_quantity=0)
        self.assertTrue(self.add(self.a, 25).json()['success'])

    def test_limit_is_capped_by_stock(self):
        Product.objects.filter(pk=self.a.pk).update(stock=3)
        self.a.refresh_from_db()
        self.assertEqual(self.a.max_per_order, 3)


class BuyNowTests(Base):
    def test_buy_now_never_enters_the_cart(self):
        self.add(self.a, 2)                                   # normal cart item
        r = self.add(self.b, 1, buy_now=True)
        data = r.json()
        self.assertTrue(data['success'])
        self.assertIn('?buy_now=', data['checkout_url'])
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.item_count, 1)                  # still only Alpha
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.all_items.count(), 2)

    def test_buy_now_checkout_shows_only_that_product(self):
        self.add(self.a, 2)
        url = self.add(self.b, 1, buy_now=True).json()['checkout_url']
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['cart'].subtotal, Decimal('300'))
        self.assertEqual(r.context['cart'].item_count, 1)

    @override_settings(**KEYS)
    def test_buy_now_order_has_only_that_product_and_leaves_cart_alone(self):
        self.add(self.a, 2)
        url = self.add(self.b, 3, buy_now=True).json()['checkout_url']
        r = self.client.post(url, ADDR)
        self.assertEqual(r.status_code, 302)
        order = Order.objects.get()
        self.assertTrue(order.is_buy_now)
        self.assertEqual([(i.product_id, i.quantity) for i in order.items.all()], [(self.b.pk, 3)])
        self.assertEqual(order.subtotal, Decimal('900'))
        cart_items = CartItem.objects.all()
        self.assertEqual([(i.product_id, i.quantity) for i in cart_items], [(self.a.pk, 2)])
        self.assertFalse(CartItem.all_items.filter(buy_now=True).exists())

    @override_settings(**KEYS)
    def test_cancelled_buy_now_order_does_not_land_in_the_cart(self):
        url = self.add(self.b, 1, buy_now=True).json()['checkout_url']
        self.client.post(url, ADDR)
        order = Order.objects.get()
        self.client.get(f'/payment/{order.order_id}/cancel/')
        self.assertEqual(Cart.objects.get(user=self.user).item_count, 0)

    def test_buy_now_ignores_what_is_in_the_cart_for_the_limit(self):
        self.add(self.a, 10)
        self.assertTrue(self.add(self.a, 4, buy_now=True).json()['success'])

    def test_stale_or_foreign_buy_now_id_is_refused(self):
        r = self.client.get('/checkout/?buy_now=99999')
        self.assertEqual(r.status_code, 302)

    def test_normal_checkout_still_uses_the_cart(self):
        self.add(self.a, 2)
        r = self.client.get('/checkout/')
        self.assertEqual(r.context['cart'].subtotal, Decimal('1000'))


class FreeParcelTextTests(Base):
    def test_free_parcel_text_is_shown_and_editable(self):
        Product.objects.filter(pk=self.a.pk).update(parcel_charge_free_label='Free Delivery Across India')
        r = self.client.get(f'/products/{self.a.slug}/')
        self.assertContains(r, 'Free Delivery Across India')

    def test_empty_text_hides_the_badge(self):
        Product.objects.filter(pk=self.a.pk).update(parcel_charge_free_label='')
        r = self.client.get(f'/products/{self.a.slug}/')
        self.assertNotContains(r, 'pd-ship-bar')


class LoggedOutBuyPriceTests(Base):
    def test_logged_out_buy_button_has_live_price_span(self):
        self.client.logout()
        r = self.client.get(f'/products/{self.a.slug}/')
        self.assertContains(r, 'id="buyPrice"')


class BuyNowAddressTests(Base):
    def _url(self):
        self.add(self.a, 2)                                   # something in the cart too
        return self.add(self.b, 1, buy_now=True).json()['checkout_url']

    def test_address_links_keep_the_buy_now_item(self):
        url = self._url()
        r = self.client.get(url)
        self.assertContains(r, 'next=%2Fcheckout%2F%3Fbuy_now%3D')

    def test_saving_an_address_returns_to_buy_now_checkout_not_the_cart(self):
        url = self._url()
        r = self.client.post('/addresses/add/', dict(
            full_name='A B', phone='9500000000', address_line1='1 St', city='Salem',
            state='Tamil Nadu', pincode='635601', next=url))
        self.assertRedirects(r, url, fetch_redirect_response=False)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_external_next_is_ignored(self):
        r = self.client.post('/addresses/add/', dict(
            full_name='A B', phone='9500000000', address_line1='1 St', city='Salem',
            state='Tamil Nadu', pincode='635601', next='//evil.example.com/'))
        self.assertEqual(r['Location'], '/addresses/')
