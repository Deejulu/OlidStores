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
	'e_stores.middleware.MediaLoggingMiddleware',  # Log media file access
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

# Supabase-specific envs
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_STORAGE_BUCKET = os.getenv('SUPABASE_STORAGE_BUCKET')

# AWS / S3-compatible envs (for real AWS or other S3 providers)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME') or SUPABASE_STORAGE_BUCKET
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', None)
AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN', None)
AWS_QUERYSTRING_AUTH = os.getenv('AWS_QUERYSTRING_AUTH', 'False').lower() in ('1','true','yes')

# Determine storage backend and MEDIA_URL
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and SUPABASE_STORAGE_BUCKET:
	# Use custom Supabase storage backend
	STORAGE_BACKEND = 'e_stores.storage_backends.SupabaseStorage'
	MEDIA_URL = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/"
elif AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
	# Use S3-compatible storage
	STORAGE_BACKEND = 'storages.backends.s3boto3.S3Boto3Storage'
	AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', None)
	if AWS_S3_CUSTOM_DOMAIN:
		MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
	else:
		MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/'
else:
	# Local filesystem storage (development / fallback)
	STORAGE_BACKEND = 'django.core.files.storage.FileSystemStorage'
	MEDIA_URL = '/media/'

# Django 6+ STORAGES configuration (replaces deprecated DEFAULT_FILE_STORAGE)
STORAGES = {
	'default': {
		'BACKEND': STORAGE_BACKEND,
	},
	'staticfiles': {
		'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
	},
}

# Keep for backwards compatibility with older code
DEFAULT_FILE_STORAGE = STORAGE_BACKEND

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Paystack keys (IMPORTANT: Set via environment variables in production)
# Default test keys are provided for local development only
PAYSTACK_PUBLIC = os.getenv('PAYSTACK_PUBLIC_KEY', 'pk_test_ab035140620358b854be0559e4aad67b3a85877a')
PAYSTACK_SECRET = os.getenv('PAYSTACK_SECRET_KEY', 'sk_test_4791378c14596cb054f5eb4ce11e78fa55b55a23')

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

# Production Security Settings (only enabled when DEBUG=False)
if not DEBUG:
	# Force HTTPS
	SECURE_SSL_REDIRECT = True
	SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
	
	# HSTS (HTTP Strict Transport Security)
	SECURE_HSTS_SECONDS = 31536000  # 1 year
	SECURE_HSTS_INCLUDE_SUBDOMAINS = True
	SECURE_HSTS_PRELOAD = True
	
	# Secure Cookies
	SESSION_COOKIE_SECURE = True
	CSRF_COOKIE_SECURE = True
	SESSION_COOKIE_HTTPONLY = True
	CSRF_COOKIE_HTTPONLY = True
	
	# Browser Security Headers
	SECURE_BROWSER_XSS_FILTER = True
	SECURE_CONTENT_TYPE_NOSNIFF = True
	X_FRAME_OPTIONS = 'DENY'
	
	# Referrer Policy
	SECURE_REFERRER_POLICY = 'same-origin'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {module} {funcName}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
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
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.core.files.storage': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'storages': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'boto3': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'botocore': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        's3transfer': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

