import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


def _parse_from_email(default_from_email):
    """DEFAULT_FROM_EMAIL is normally formatted like 'CraftX3D <foo@bar.com>' —
    split it into (name, email) for Brevo's API, which wants them separately."""
    if '<' in default_from_email and '>' in default_from_email:
        name, email = default_from_email.rsplit('<', 1)
        return name.strip().strip('"'), email.strip('> ').strip()
    return 'CraftX3D', default_from_email.strip()


def _send_via_brevo(to_email, to_name, subject, html_body, log_ref):
    """
    Shared low-level sender used by every email in the site. Sends via
    Brevo's HTTPS API (not SMTP — Render's free tier blocks outbound SMTP
    ports 25/465/587 entirely, but regular HTTPS traffic works fine).

    Never raises — any failure (bad API key, rate limit, network issue, etc.)
    is logged and swallowed by the caller's try/except pattern. Returns
    (success, error_detail).
    """
    if not settings.BREVO_API_KEY:
        return False, 'Email sending is not configured (BREVO_API_KEY missing).'

    text_body = strip_tags(html_body)
    sender_name, sender_email = _parse_from_email(settings.DEFAULT_FROM_EMAIL)

    response = requests.post(
        BREVO_API_URL,
        headers={
            'accept': 'application/json',
            'api-key': settings.BREVO_API_KEY,
            'content-type': 'application/json',
        },
        json={
            'sender': {'name': sender_name, 'email': sender_email},
            'to': [{'email': to_email, 'name': to_name or to_email}],
            'subject': subject,
            'htmlContent': html_body,
            'textContent': text_body,
        },
        timeout=10,
    )

    if response.status_code in (200, 201):
        return True, None

    # Brevo returns a JSON body describing what went wrong (bad key,
    # unverified sender, rate limit, etc.) — surface that directly.
    try:
        detail = response.json().get('message', response.text[:200])
    except ValueError:
        detail = response.text[:200]
    logger.error('Brevo API returned %s for %s: %s', response.status_code, log_ref, detail)
    return False, f'Brevo API error {response.status_code}: {detail}'


def send_order_confirmation_email(order, request=None):
    """
    Sends the order confirmation/invoice email to the customer.

    Never raises — any failure (bad API key, rate limit, network issue, etc.)
    is logged and swallowed, so a failed email can never break the checkout
    flow or leave an order in a broken state. The order and its on-site
    invoice are always available regardless of whether this email goes out.

    Returns (success, error_detail) — error_detail is None on success, or a
    short diagnostic string on failure (safe to show to staff, not customers).
    """
    if not order.email:
        return False, 'This order has no email address on file.'

    try:
        if request is not None:
            order_url = request.build_absolute_uri(f'/my-orders/{order.order_id}/')
        else:
            scheme = 'http' if settings.DEBUG else 'https'
            domain = getattr(settings, 'RENDER_EXTERNAL_HOSTNAME', None) or 'localhost:8000'
            order_url = f'{scheme}://{domain}/my-orders/{order.order_id}/'

        html_body = render_to_string('emails/order_confirmation.html', {
            'order': order,
            'order_url': order_url,
        })
        return _send_via_brevo(
            to_email=order.email,
            to_name=order.full_name,
            subject=f'Order Confirmed — #{order.order_id} — CraftX3D',
            html_body=html_body,
            log_ref=f'order {order.order_id}',
        )
    except Exception as e:
        # Order confirmation email is a convenience, not a requirement — the
        # customer can always see their invoice on the site. Log it so staff
        # can notice a pattern (e.g. daily send-limit reached) without it
        # ever affecting the order itself.
        logger.exception('Order confirmation email failed to send (order_id=%s)', order.order_id)
        return False, f"{type(e).__name__}: {str(e)[:200]}"


def send_password_reset_email(user, reset_url):
    """
    Sends the "reset your password" email. Never raises — logs and swallows
    any failure. Returns (success, error_detail).
    """
    try:
        html_body = render_to_string('emails/password_reset.html', {
            'user': user,
            'reset_url': reset_url,
        })
        return _send_via_brevo(
            to_email=user.email,
            to_name=user.get_full_name() or user.email,
            subject='Reset your password — CraftX3D',
            html_body=html_body,
            log_ref=f'password reset for user {user.pk}',
        )
    except Exception as e:
        logger.exception('Password reset email failed to send (user_id=%s)', user.pk)
        return False, f"{type(e).__name__}: {str(e)[:200]}"

