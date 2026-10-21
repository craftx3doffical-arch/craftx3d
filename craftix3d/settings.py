import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — using environment variables or defaults


# ── Python 3.14 Django Admin compatibility patch ──────────
import sys as _sys
if _sys.version_info >= (3, 13):
    try:
        import django.template.context as _ctx
        def _py314_copy(self):
            cls = type(self)
            dup = cls.__new__(cls)
            dup.__dict__.update(self.__dict__)
            dup.dicts = self.dicts[:]
            return dup
        _ctx.BaseContext.__copy__ = _py314_copy
    except Exception:
        pass
# ─────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-craftix3d-dev-key-change-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Render.com sets this automatically for the app's own domain — add it so the
# site works at https://<your-app>.onrender.com without extra config.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Needed behind Render's/most PaaS reverse proxies so Django knows the
# original request was HTTPS (otherwise CSRF/redirects can misbehave).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# Production hardening — skipped when DEBUG=True so local dev over plain
# http:// still works without redirect loops.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Django's CSRF JS helpers read this cookie by design
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # required by allauth

    # Google login
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'store',
    'manage_portal',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'craftix3d.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_count',
                'store.context_processors.store_settings',
                'store.context_processors.favorites',
                'store.context_processors.nav_categories',
                'manage_portal.context_processors.manage_sidebar_counts',
            ],
        },
    },
]

WSGI_APPLICATION = 'craftix3d.wsgi.application'

# ── Database ────────────────────────────────────────────────────────────────
# Supports SQLite (local dev) or PostgreSQL via DATABASE_URL (Railway, Render,
# Heroku-style connection strings all use this same format).
USE_SQLITE = os.environ.get('USE_SQLITE', 'True') == 'True'
DB_URL = os.environ.get('DATABASE_URL', '')

if USE_SQLITE and not DB_URL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DB_URL:
    import urllib.parse
    urllib.parse.uses_netloc.append('postgres')
    urllib.parse.uses_netloc.append('postgresql')
    # Railway/Heroku-style URLs sometimes use the old 'postgres://' scheme,
    # which Python's urlparse handles fine, but be explicit just in case.
    result = urllib.parse.urlparse(DB_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': result.path.lstrip('/'),
            'USER': urllib.parse.unquote(result.username or ''),
            'PASSWORD': urllib.parse.unquote(result.password or ''),
            'HOST': result.hostname,
            'PORT': result.port or 5432,
            'CONN_MAX_AGE': 600,
            'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'require')},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'craftix3d'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'password'),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# ── Media storage ───────────────────────────────────────────────────────────
# Render's filesystem is ephemeral (wiped on every redeploy), so uploaded
# product photos, customization photos, etc. must live somewhere persistent.
# If Cloudinary credentials are present, use Cloudinary; otherwise fall back
# to local disk storage (fine for local development only).
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '').strip()
if not CLOUDINARY_URL:
    # Some setups/tutorials use three separate variables instead of the
    # single combined CLOUDINARY_URL — support both so this can't silently
    # disable Cloudinary just because a different naming convention was used.
    _cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    _api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    _api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()
    if _cloud_name and _api_key and _api_secret:
        CLOUDINARY_URL = f'cloudinary://{_api_key}:{_api_secret}@{_cloud_name}'
        os.environ['CLOUDINARY_URL'] = CLOUDINARY_URL  # cloudinary SDK reads this env var directly
USE_CLOUDINARY = bool(CLOUDINARY_URL)

if USE_CLOUDINARY:
    INSTALLED_APPS += ['cloudinary_storage', 'cloudinary']
    MEDIA_URL = '/media/'
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Django 4.2+ unified storage config — STATICFILES_STORAGE and STORAGES are
# mutually exclusive, so this single dict handles both static files (always
# whitenoise) and media/uploads (Cloudinary when configured, else local disk).
STORAGES = {
    'default': {
        'BACKEND': (
            'cloudinary_storage.storage.MediaCloudinaryStorage'
            if USE_CLOUDINARY else
            'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Ensure caught exceptions we explicitly log (e.g. a failed photo upload)
# reliably show up in Render's Logs tab, rather than depending on Django's
# default logging setup.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}


LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ── Google login (django-allauth) ───────────────────────────────────────────
# Set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET as environment variables — get
# these from Google Cloud Console → APIs & Services → Credentials.
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
SOCIALACCOUNT_AUTO_SIGNUP = False  # brand-new Google sign-ups confirm name + agree to Terms first
SOCIALACCOUNT_LOGIN_ON_GET = True  # skip allauth's intermediate confirmation page
SOCIALACCOUNT_FORMS = {'signup': 'store.forms.CustomSocialSignupForm'}
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True

# Auto-generate the account from Google's data (email/name) with zero extra
# form — the site's own registration already uses email as the username, so
# this keeps Google sign-in consistent with that and fully seamless.
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
SOCIALACCOUNT_ADAPTER = 'store.adapters.CustomSocialAccountAdapter'
ACCOUNT_ADAPTER = 'store.adapters.CustomAccountAdapter'

# ── Razorpay (online payments) ──────────────────────────────────────────────
# Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET as environment variables — get
# these from the Razorpay Dashboard → Settings → API Keys.
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# ── Order confirmation emails (Brevo HTTPS API) ─────────────────────────────
# Uses Brevo's REST API over HTTPS rather than SMTP — Render's free tier
# blocks outbound SMTP ports (25/465/587) entirely, but regular HTTPS traffic
# is unaffected, so this works on the free tier without needing to upgrade.
# Get your API key from Brevo → Settings (gear icon) → SMTP & API → API Keys tab
# (a different key from the SMTP key — look specifically for "API Keys").
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'CraftX3D <supportcraftx3dstudio@gmail.com>')
EMAIL_SENDING_ENABLED = bool(BREVO_API_KEY)

# Session settings
SESSION_COOKIE_AGE = 86400 * 30  # 30 days

# Message storage
MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
