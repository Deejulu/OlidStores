
import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load local environment variables from a .env file in the project root.
# This makes local development easier and avoids repeated manual shell export.
ENV_PATH = BASE_DIR / '.env'
if ENV_PATH.exists():
    with ENV_PATH.open() as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and not os.getenv(key):
                os.environ[key] = value

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-please-change-this-key')
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [host.strip() for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',') if host.strip()]

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'core',
	'products.apps.ProductsConfig',
	'orders.apps.OrdersConfig',
	'users',
	'admin_dashboard',
	'crispy_forms',
	'crispy_bootstrap5',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

AUTH_USER_MODEL = 'users.CustomUser'

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'whitenoise.middleware.WhiteNoiseMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'users.middleware.VerificationMiddleware',  # Enforce email/phone verification
]

ROOT_URLCONF = 'e_stores.urls'

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
				'products.context_processors.categories_footer',
                'core.context_processors.site_contact',
				'orders.context_processors.cart_count',
				'admin_dashboard.context_processors.admin_notifications',
			],
		},
	},
]

WSGI_APPLICATION = 'e_stores.wsgi.application'

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = f'sqlite:///{BASE_DIR / "db.sqlite3"}'

DATABASE_SSL_MODE = os.getenv('DATABASE_SSL_MODE', '').strip() or None
DATABASE_CONNECT_TIMEOUT = int(os.getenv('DATABASE_CONNECT_TIMEOUT', '10'))
DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=0,
        ssl_require=False,
    )
}

DATABASES['default'].setdefault('OPTIONS', {})
if DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    DATABASES['default']['OPTIONS']['connect_timeout'] = DATABASE_CONNECT_TIMEOUT

    if DATABASE_SSL_MODE:
        DATABASES['default']['OPTIONS']['sslmode'] = DATABASE_SSL_MODE
    elif not os.getenv('DJANGO_DEBUG', 'True').lower() in ('1', 'true', 'yes'):
        DATABASES['default']['OPTIONS']['sslmode'] = 'require'

CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
CACHES = {
    'default': {
        'BACKEND': os.getenv('DJANGO_CACHE_BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': os.getenv('DJANGO_CACHE_LOCATION', 'e-stores-cache'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Paystack keys (set via environment variables in production)
PAYSTACK_PUBLIC = 'pk_test_ab035140620358b854be0559e4aad67b3a85877a'
PAYSTACK_SECRET = 'sk_test_4791378c14596cb054f5eb4ce11e78fa55b55a23'

# Contact page settings
CONTACT_NOTIFY_EMAIL = os.getenv('CONTACT_NOTIFY_EMAIL', '')
CONTACT_RATE_LIMIT_PER_HOUR = int(os.getenv('CONTACT_RATE_LIMIT_PER_HOUR', '6'))

# Email Configuration
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
backend_name = EMAIL_BACKEND.lower()
if backend_name == 'sendgrid':
    EMAIL_BACKEND = 'e_stores.email_backends.SendGridEmailBackend'
elif backend_name == 'brevo':
    EMAIL_BACKEND = 'e_stores.email_backends.BrevoEmailBackend'
elif backend_name == 'resend':
    EMAIL_BACKEND = 'e_stores.email_backends.ResendEmailBackend'

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('1', 'true', 'yes')

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
SENDGRID_SENDER_EMAIL = os.getenv('SENDGRID_SENDER_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')
SENDGRID_SENDER_NAME = os.getenv('SENDGRID_SENDER_NAME', 'E-Stores')
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_SENDER_EMAIL = os.getenv('BREVO_SENDER_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')
BREVO_SENDER_NAME = os.getenv('BREVO_SENDER_NAME', 'E-Stores')
RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')
RESEND_SENDER_EMAIL = os.getenv('RESEND_SENDER_EMAIL', EMAIL_HOST_USER or 'webmaster@localhost')
RESEND_SENDER_NAME = os.getenv('RESEND_SENDER_NAME', 'E-Stores')
EMAIL_SEND_TIMEOUT = int(os.getenv('EMAIL_SEND_TIMEOUT', '10'))

# Default from email
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    SENDGRID_SENDER_EMAIL or BREVO_SENDER_EMAIL or RESEND_SENDER_EMAIL or EMAIL_HOST_USER or 'webmaster@localhost'
)
EMAIL_SUBJECT_PREFIX = os.getenv('EMAIL_SUBJECT_PREFIX', '[E-Stores] ')

# Twilio SMS Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')  # e.g., '+1234567890'

# OTP Verification Settings
OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', '10'))
OTP_MAX_ATTEMPTS = 5
# Set to True to print OTP codes instead of sending real emails
OTP_DEBUG_MODE = os.getenv('OTP_DEBUG_MODE', 'False').lower() in ('1', 'true', 'yes')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s] %(asctime)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        '': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}
