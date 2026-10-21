from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from django.templatetags.static import static as static_url
from store import views as store_views

urlpatterns = [
    # Browsers, Google, and link-preview bots request /favicon.ico at the
    # domain root directly — redirect it to the real static file so the tab
    # icon and search-result icon always resolve.
    path('favicon.ico', RedirectView.as_view(url=static_url('img/favicon.ico'), permanent=True)),
    path('apple-touch-icon.png', RedirectView.as_view(url=static_url('img/apple-touch-icon.png'), permanent=True)),
    path('admin/', admin.site.urls),
    path('manage/', include('manage_portal.urls', namespace='manage')),
    # Google login handshake only (NOT the full allauth.urls, which would
    # collide with our own /accounts/login/ and /accounts/register/ views).
    path('accounts/', include('allauth.socialaccount.providers.google.urls')),
    path('accounts/', include('allauth.socialaccount.urls')),
    # Unnamespaced alias: allauth's internal flows fall back to
    # reverse('account_login') in a few edge cases (e.g. an expired/invalid
    # pending social signup). This must be registered OUTSIDE the 'store'
    # namespace, or the name silently becomes 'store:account_login' and
    # allauth's plain reverse('account_login') still 500s with NoReverseMatch.
    path('accounts/login/', store_views.login_view, name='account_login'),
    path('', include('store.urls', namespace='store')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
