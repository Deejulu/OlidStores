"""
Configure the Supabase Storage bucket used for media uploads.

Supabase Storage buckets can be locked to a whitelist of allowed MIME types.
When that whitelist does not include video types, any MP4 upload fails with a
415 ``invalid_mime_type`` error (see ``storage_backends.SupabaseStorage._save``).

This command ensures the bucket allows the common image and video types the
project needs, so background videos (and other media) upload successfully.

Run at deploy/build time via:
    python manage.py configure_storage_bucket
"""
import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

BUCKET_ALLOWED_TYPES = [
    # Images (JPEG/PNG/WebP/GIF/etc.)
    "image/*",
    # Video backgrounds / lookbooks (MP4/MOV/WebM/MKV)
    "video/*",
]


class Command(BaseCommand):
    help = "Ensure the Supabase media bucket allows image and video MIME types."

    def handle(self, *args, **options):
        supabase_url = getattr(settings, "SUPABASE_URL", "").rstrip("/")
        service_role_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
        bucket_name = getattr(settings, "SUPABASE_STORAGE_BUCKET", "media")

        # Skip on local dev where Supabase is not configured.
        if not supabase_url or not service_role_key:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping storage bucket configuration: "
                    "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set."
                )
            )
            return

        admin_url = f"{supabase_url}/storage/v1/buckets/{bucket_name}"
        headers = {
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        payload = {"allowed_mime_types": BUCKET_ALLOWED_TYPES}

        self.stdout.write(
            f"Configuring bucket '{bucket_name}' allowed MIME types: "
            f"{BUCKET_ALLOWED_TYPES}"
        )
        try:
            response = requests.patch(
                admin_url, headers=headers, json=payload, timeout=30
            )
        except requests.RequestException as exc:
            raise CommandError(f"Failed to configure storage bucket: {exc}")

        if response.status_code in (200, 204):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Bucket '{bucket_name}' now allows image and video MIME types."
                )
            )
        else:
            logger.error(
                "Failed to configure bucket %s: %s %s",
                bucket_name, response.status_code, response.text,
            )
            # Non-fatal: uploads may still work if the bucket is already permissive.
            self.stdout.write(
                self.style.WARNING(
                    f"Could not update bucket (HTTP {response.status_code}); "
                    "uploads of unsupported types may still fail."
                )
            )
