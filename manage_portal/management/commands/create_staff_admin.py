import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from manage_portal.models import StaffUser


class Command(BaseCommand):
    """
    Creates (or resets the password of) the manage-portal StaffUser login,
    reading credentials from environment variables. Also keeps the Django
    Sites framework's domain in sync with the real site domain, so
    allauth-generated pages/emails show the actual domain instead of the
    default placeholder "example.com".

    Safe to run on every deploy — it's a no-op if STAFF_ADMIN_USERNAME isn't
    set, and it won't downgrade an existing admin's role.

    Usage (typically called from build.sh):
        python manage.py create_staff_admin
    """
    help = 'Create or update the manage-portal staff admin login from STAFF_ADMIN_USERNAME / STAFF_ADMIN_PASSWORD env vars, and sync the Sites framework domain.'

    def handle(self, *args, **options):
        # ── Fix the Sites framework domain (shown on allauth pages) ────────
        site_domain = (
            os.environ.get('SITE_DOMAIN', '').strip()
            or os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
        )
        if site_domain:
            Site.objects.update_or_create(
                id=1,
                defaults={'domain': site_domain, 'name': 'CraftX3D'},
            )
            self.stdout.write(self.style.SUCCESS(f'Site domain set to: {site_domain}'))
        else:
            self.stdout.write(self.style.WARNING(
                'SITE_DOMAIN / RENDER_EXTERNAL_HOSTNAME not set — Sites framework domain left as-is.'
            ))

        # ── Staff admin login ────────────────────────────────────────────
        username = os.environ.get('STAFF_ADMIN_USERNAME', '').strip()
        password = os.environ.get('STAFF_ADMIN_PASSWORD', '')

        if not username or not password:
            self.stdout.write(self.style.WARNING(
                'STAFF_ADMIN_USERNAME / STAFF_ADMIN_PASSWORD not set — skipping staff admin creation.'
            ))
            return

        staff = StaffUser.objects.filter(username__iexact=username).first()
        if staff:
            created = False
        else:
            staff = StaffUser(username=username, full_name='Admin', role='admin', is_active=True)
            created = True
        staff.set_password(password)
        staff.is_active = True
        staff.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created staff admin login: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated password for existing staff admin: {username}'))
