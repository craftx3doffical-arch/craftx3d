from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase


class EmailAuthTests(TestCase):
    def setUp(self):
        cache.clear()

    def _reg(self, **kw):
        data = dict(full_name='Ravi Kumar', phone='9500295991', email='Ravi@Example.com',
                    password='secret123', confirm_password='secret123', agree_terms='on')
        data.update(kw)
        return self.client.post('/accounts/register/', data)

    def test_email_is_required_on_signup(self):
        r = self._reg(email='')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.exists())
        self.assertContains(r, 'Email address is required')

    def test_signup_uses_email_as_username_and_logs_in(self):
        r = self._reg()
        self.assertEqual(r.status_code, 302)
        u = User.objects.get()
        self.assertEqual(u.username, 'ravi@example.com')
        self.assertEqual(u.email, 'ravi@example.com')

    def test_duplicate_email_rejected_case_insensitive(self):
        self._reg()
        self.client.logout()
        r = self._reg(phone='9500295992', email='RAVI@example.com')
        self.assertEqual(User.objects.count(), 1)
        self.assertContains(r, 'already exists')

    def test_login_with_email_and_password(self):
        self._reg(); self.client.logout()
        r = self.client.post('/accounts/login/', dict(email='RAVI@example.com', password='secret123'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_wrong_password_rejected(self):
        self._reg(); self.client.logout()
        r = self.client.post('/accounts/login/', dict(email='ravi@example.com', password='nope'))
        self.assertContains(r, 'Invalid email or password')
