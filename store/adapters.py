from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    DefaultAccountAdapter.save_user() sets user.username from the signup
    form's 'username' field — but our social signup form has no such field
    (ACCOUNT_USERNAME_REQUIRED=False), so it would otherwise save a BLANK
    username. Force it to the email address here instead, consistent with
    how the site's own registration view creates accounts.
    """

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        email = (user.email or '').strip()
        if email:
            user.username = email
        if commit:
            user.save()
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Makes Google sign-in behave exactly like the site's own registration
    flow: the account's username is set to their email address, so no
    separate "choose a username" form is ever shown to the customer.
    """

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = data.get('email') or (user.email or '')
        if email:
            user.username = email
            user.email = email
        return user

    def pre_social_login(self, request, sociallogin):
        """
        If someone already has an account with this email (e.g. they signed
        up the normal way first), connect their Google login to that same
        account instead of erroring out with "email already in use" or
        creating a confusing duplicate. This is what makes "I already have
        an account, I just want to sign in with Google" work seamlessly.
        """
        if sociallogin.is_existing:
            return  # already linked to a social account, nothing to do

        email = (sociallogin.user.email or '').strip()
        if not email:
            return

        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return
        except User.MultipleObjectsReturned:
            return

        sociallogin.connect(request, existing_user)
