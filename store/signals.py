from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """
    Every customer needs a UserProfile to show up in the manage portal's
    customer list (manage_portal.views.customers_list filters on it). The
    site's own registration view already creates one explicitly, but any
    other signup path — Google OAuth being the main one — doesn't. This
    signal is the single place that guarantees it always exists, no matter
    how the account was created.
    """
    if instance.is_staff:
        return
    UserProfile.objects.get_or_create(user=instance)
