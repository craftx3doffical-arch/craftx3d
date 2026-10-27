"""Customization enquiry: customer form -> saved -> visible/editable in the staff portal."""
from django.core.cache import cache
from django.test import TestCase

from manage_portal.models import StaffUser
from store.models import Category, Enquiry, Product

GOOD = dict(full_name='Ravi', phone='+91 95002 95991', email='', quantity='10',
            budget='Rs 500', message='Name on the base please')


class CustomEnquiryTests(TestCase):
    def setUp(self):
        cache.clear()
        cat = Category.objects.create(name='Idols', slug='idols')
        self.p = Product.objects.create(name='Peacock Vel', slug='peacock-vel', category=cat, base_price=599)

    def test_customer_can_send_a_request_without_email(self):
        r = self.client.post('/custom-enquiry/', dict(GOOD, product=self.p.pk))
        self.assertEqual(r.status_code, 302)
        e = Enquiry.objects.get()
        self.assertEqual(e.enquiry_type, Enquiry.TYPE_CUSTOMIZATION)
        self.assertEqual(e.phone, '9500295991')
        self.assertEqual(e.product, self.p)

    def test_bad_phone_is_rejected_and_does_not_use_up_the_allowance(self):
        for _ in range(12):
            self.client.post('/custom-enquiry/', dict(GOOD, phone='123'))
        self.assertEqual(Enquiry.objects.count(), 0)
        r = self.client.post('/custom-enquiry/', GOOD)
        self.assertEqual(r.status_code, 302)           # still allowed
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_visitors_behind_the_proxy_do_not_share_one_limit(self):
        # Same REMOTE_ADDR (the proxy), different real visitors in X-Forwarded-For.
        for i in range(12):
            r = self.client.post('/custom-enquiry/', GOOD, REMOTE_ADDR='10.0.0.1',
                                 HTTP_X_FORWARDED_FOR=f'203.0.113.{i}')
            self.assertEqual(r.status_code, 302)
        self.assertEqual(Enquiry.objects.count(), 12)

    def test_one_visitor_is_still_limited(self):
        codes = [self.client.post('/custom-enquiry/', GOOD, HTTP_X_FORWARDED_FOR='203.0.113.9').status_code
                 for _ in range(12)]
        self.assertEqual(codes.count(302), 10)
        self.assertEqual(Enquiry.objects.count(), 10)


class StaffPortalEnquiryTests(TestCase):
    def setUp(self):
        self.staff = StaffUser.objects.create(username='boss', role='admin')
        self.staff.set_password('x'); self.staff.save()
        s = self.client.session
        s['staff_logged_in'] = True; s['staff_id'] = self.staff.pk; s['staff_role'] = 'admin'
        s.save()
        self.e = Enquiry.objects.create(full_name='Ravi', phone='9500295991', email='', subject='Customization: x',
                                        message='hello', enquiry_type=Enquiry.TYPE_CUSTOMIZATION)

    def test_list_shows_the_enquiry(self):
        r = self.client.get('/manage/customization-enquiries/')
        self.assertContains(r, 'Ravi')

    def test_status_and_note_can_be_saved(self):
        r = self.client.post(f'/manage/enquiries/{self.e.pk}/status/', {'status': 'in_progress'})
        self.assertTrue(r.json()['success'])
        r = self.client.post(f'/manage/enquiries/{self.e.pk}/status/', {'note': 'Quoted Rs 700'})
        self.e.refresh_from_db()
        self.assertEqual((self.e.status, self.e.staff_note), ('in_progress', 'Quoted Rs 700'))

    def test_invalid_status_is_refused(self):
        r = self.client.post(f'/manage/enquiries/{self.e.pk}/status/', {'status': 'bogus'})
        self.assertEqual(r.status_code, 400)
        self.e.refresh_from_db()
        self.assertEqual(self.e.status, 'new')


class MultiProductEnquiryTests(TestCase):
    def setUp(self):
        cache.clear()
        cat = Category.objects.create(name='Idols', slug='idols')
        self.a = Product.objects.create(name='Peacock Vel', slug='peacock-vel', category=cat, base_price=599)
        self.b = Product.objects.create(name='Moon Lamp', slug='moon-lamp', category=cat, base_price=799)
        self.c = Product.objects.create(name='Twist Vase', slug='twist-vase', category=cat, base_price=399)
        self.staff = StaffUser.objects.create(username='boss', role='admin')
        self.staff.set_password('x'); self.staff.save()
        s = self.client.session
        s['staff_logged_in'] = True; s['staff_id'] = self.staff.pk; s['staff_role'] = 'admin'
        s.save()

    def test_several_products_are_saved_and_shown_in_the_portal(self):
        r = self.client.post('/custom-enquiry/', dict(GOOD, products=[self.a.pk, self.b.pk, self.c.pk]))
        self.assertEqual(r.status_code, 302)
        e = Enquiry.objects.get()
        self.assertEqual({p.pk for p in e.products.all()}, {self.a.pk, self.b.pk, self.c.pk})
        self.assertIn(e.product, (self.a, self.b, self.c))   # first pick kept for older code
        for name in ('Peacock Vel', 'Moon Lamp', 'Twist Vase'):
            self.assertIn(name, e.subject)
        page = self.client.get('/manage/customization-enquiries/')
        for name in ('Peacock Vel', 'Moon Lamp', 'Twist Vase'):
            self.assertContains(page, name)
        self.assertContains(page, '3 products')

    def test_portal_search_finds_a_request_by_any_of_its_products(self):
        self.client.post('/custom-enquiry/', dict(GOOD, products=[self.a.pk, self.b.pk]))
        r = self.client.get('/manage/customization-enquiries/?q=Moon')
        self.assertContains(r, 'Ravi')

    def test_no_product_still_works(self):
        r = self.client.post('/custom-enquiry/', GOOD)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Enquiry.objects.get().all_products, [])

    def test_form_page_preselects_product_from_link(self):
        r = self.client.get(f'/custom-enquiry/?product={self.b.pk}')
        self.assertContains(r, f'value="{self.b.pk}" checked')

    def test_csv_export_lists_all_products(self):
        self.client.post('/custom-enquiry/', dict(GOOD, products=[self.a.pk, self.b.pk]))
        r = self.client.get('/manage/export/customization-enquiries/')
        body = r.content.decode()
        self.assertIn('Peacock Vel', body)
        self.assertIn('Moon Lamp', body)
