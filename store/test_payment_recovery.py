"""A customer who really paid must always end up with a confirmed order."""
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from manage_portal.models import StaffUser
from store.models import Order
from store.test_buy_now_and_limits import ADDR, Base, KEYS


def razorpay_says(items=None, error=None):
    client = mock.MagicMock()
    if error:
        client.order.payments.side_effect = error
    else:
        client.order.payments.return_value = {'items': items or []}
    return mock.patch('razorpay.Client', return_value=client), client


PAID = [{'id': 'pay_1', 'status': 'captured'}]


@override_settings(**KEYS)
class PaymentRecoveryTests(Base):
    def setUp(self):
        super().setUp()
        cache.clear()
        url = self.add(self.b, 1, buy_now=True).json()['checkout_url']
        self.client.post(url, ADDR)
        self.order = Order.objects.get()
        Order.objects.filter(pk=self.order.pk).update(razorpay_order_id='order_X')
        self.order.refresh_from_db()

    def test_closing_the_window_after_paying_does_not_cancel_the_order(self):
        patcher, _ = razorpay_says(PAID)
        with patcher:
            r = self.client.get(f'/payment/{self.order.order_id}/cancel/')
        self.assertRedirects(r, reverse('store:order_placed', args=[self.order.order_id]),
                             fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual((self.order.payment_status, self.order.status), ('paid', 'pending'))

    def test_really_unpaid_order_is_still_cancelled(self):
        patcher, _ = razorpay_says([])
        with patcher:
            self.client.get(f'/payment/{self.order.order_id}/cancel/')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')

    def test_razorpay_down_never_cancels(self):
        patcher, _ = razorpay_says(error=RuntimeError('network'))
        with patcher:
            self.client.get(f'/payment/{self.order.order_id}/cancel/')
            self.client.get(f'/payment/{self.order.order_id}/failed/?reason=error')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'awaiting_payment')

    def test_failed_page_confirms_a_paid_order(self):
        patcher, _ = razorpay_says(PAID)
        with patcher:
            r = self.client.get(f'/payment/{self.order.order_id}/failed/?reason=error')
        self.assertEqual(r.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')

    def test_my_orders_recovers_an_already_cancelled_but_paid_order(self):
        Order.objects.filter(pk=self.order.pk).update(status='cancelled', payment_status='failed')
        patcher, _ = razorpay_says(PAID)
        with patcher:
            r = self.client.get('/my-orders/')
        self.assertEqual(r.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual((self.order.payment_status, self.order.status), ('paid', 'pending'))

    def test_phone_callback_with_valid_signature_confirms_without_a_login_cookie(self):
        self.client.logout()
        patcher, client = razorpay_says()
        with patcher:
            r = self.client.post(f'/payment/{self.order.order_id}/callback/', {
                'razorpay_payment_id': 'pay_1', 'razorpay_order_id': 'order_X',
                'razorpay_signature': 'sig'})
        client.utility.verify_payment_signature.assert_called_once()
        self.assertRedirects(r, reverse('store:order_placed', args=[self.order.order_id]),
                             fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')

    def test_phone_callback_with_bad_signature_does_not_confirm(self):
        patcher, client = razorpay_says()
        client.utility.verify_payment_signature.side_effect = Exception('bad')
        with patcher:
            self.client.post(f'/payment/{self.order.order_id}/callback/', {
                'razorpay_payment_id': 'pay_1', 'razorpay_order_id': 'order_X',
                'razorpay_signature': 'forged'})
        self.order.refresh_from_db()
        self.assertNotEqual(self.order.payment_status, 'paid')

    def test_callback_with_someone_elses_razorpay_order_id_is_refused(self):
        patcher, client = razorpay_says()
        with patcher:
            self.client.post(f'/payment/{self.order.order_id}/callback/', {
                'razorpay_payment_id': 'pay_1', 'razorpay_order_id': 'order_OTHER',
                'razorpay_signature': 'sig'})
        client.utility.verify_payment_signature.assert_not_called()


@override_settings(**KEYS)
class StaffSyncTests(Base):
    def test_sync_button_recovers_paid_orders_so_they_show_in_manage(self):
        url = self.add(self.b, 1, buy_now=True).json()['checkout_url']
        self.client.post(url, ADDR)
        Order.objects.update(razorpay_order_id='order_X', status='cancelled', payment_status='failed')

        staff = StaffUser.objects.create(username='boss', role='admin'); staff.set_password('x'); staff.save()
        s = self.client.session
        s['staff_logged_in'] = True; s['staff_id'] = staff.pk; s['staff_role'] = 'admin'; s.save()

        patcher, _ = razorpay_says(PAID)
        with patcher:
            self.client.post('/manage/orders/sync-payments/')
        self.assertEqual(Order.objects.get().payment_status, 'paid')
        self.assertContains(self.client.get('/manage/orders/'), Order.objects.get().order_id)
