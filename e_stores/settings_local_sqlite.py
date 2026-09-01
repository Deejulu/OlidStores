# Local SQLite sandbox settings.
# This module is used ONLY for safe local browser testing. It does NOT touch the
# production Olid Stores Supabase database. Activate with:
#   manage.py runserver --settings=e_stores.settings_local_sqlite
import os
from .settings import *  # noqa: F401,F403  (inherit everything, then override below)

print("\n" + "=" * 72)
print("  LOCAL SQLITE SANDBOX  ->  Django is using db.sqlite3 (local file)")
print("  NOT connected to Supabase / Olid Stores production database")
print("=" * 72 + "\n")

# Override the database to a local SQLite file (production DATABASE_URL is ignored).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }
}

# Use local filesystem storage so nothing is written to Supabase Storage.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Do not send real emails during local testing.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
