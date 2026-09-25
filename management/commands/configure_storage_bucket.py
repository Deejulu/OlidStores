"""
Configure the Supabase Storage bucket used for media uploads.

Supabase Storage buckets can be locked to a whitelist of allowed MIME types.
When that whitelist does not include ``video/mp4``, any MP4 upload fails with a
415 ``invalid_mime_type`` error (see ``storage_backends.SupabaseStorage._save``).

This command updates the bucket's ``allowed_mime_types`` via the Supabase Storage
Admin API so that image **and** video uploads succeed.

Run at deploy/build time via:
    python manage.py configure_storage_bucket
"""
import logging

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

# Explicit MIME types (Supabase Storage does not accept wildcards in
# allowed_mime_types; use null to allow everything, which we fall back to).
ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/bmp",
    "image/tiff",
]
ALLOWED_VIDEO_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/x-matroska",
]
ALLOWED_MIME_TYPES = ALLOWED_IMAGE_TYPES + ALLOWED_VIDEO_TYPES


class Command(BaseCommand):
    help = "Ensure the Supabase media bucket allows image and video MIME types."

    def _patch_bucket(self, admin_url, headers, payload):
        # The Supabase Storage Admin API uses PUT /bucket/{bucketId} to update a
        # bucket's configuration (allowed_mime_types, file_size_limit, public).
        return requests.put(admin_url, headers=headers, json=payload, timeout=30)

    def handle(self, *args, **options):
        supabase_url = getattr(settings, "SUPABASE_URL", "").rstrip("/")
        service_role_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
        bucket_name = getattr(settings, "SUPABASE_STORAGE_BUCKET", "media")
        max_memory_size = getattr(settings, "DATA_UPLOAD_MAX_MEMORY_SIZE", 50 * 1024 * 1024)

        # Skip on local dev where Supabase is configured.
        if not supabase_url or not service_role_key:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping storage bucket configuration: "
                    "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set."
                )
            )
            return

        admin_url = f"{supabase_url}/storage/v1/bucket/{bucket_name}"
        headers = {
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

        self.stdout.write(
            f"Configuring bucket '{bucket_name}' allowed MIME types: "
            f"{ALLOWED_MIME_TYPES}"
        )

        # Attempt 1: set an explicit allow-list (incl. video types) and a sane
        # file-size limit (the Django form already caps uploads at 50 MB).
        payload = {
            "allowed_mime_types": ALLOWED_MIME_TYPES,
            "public": True,
            "file_size_limit": DATA_UPLOAD_MAX_MEMORY_SIZE,
        }
        try:
            response = self._patch_bucket(admin_url, headers, payload)
        except requests.RequestException as exc:
            raise CommandError(f"Failed to contact Supabase Storage API: {exc}")

        if response.status_code in (200, 201, 204):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Bucket '{bucket_name}' now allows image and video MIME types."
                )
            )
            return

        # Attempt 2: if the explicit allow-list is rejected (e.g. unknown type),
        # open the bucket to all types by setting allowed_mime_types to null.
        status, text = response.status_code, response.text
        logger.warning(
            "Explicit allowed_mime_types rejected for %s (%s %s); "
            "falling back to permissive bucket.",
            bucket_name, status, text,
        )
        fallback_payload = {
            "allowed_mime_types": None,
            "public": True,
            "file_size_limit": max_memory_size,
        }
        try:
            response = self._patch_bucket(admin_url, headers, fallback_payload)
        except requests.RequestException as exc:
            raise CommandError(f"Failed to contact Supabase Storage API: {exc}")

        if response.status_code in (200, 201, 204):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Bucket '{bucket_name}' is now permissive (all MIME types)."
                )
            )
        else:
            logger.error(
                "Failed to configure bucket %s: %s %s",
                bucket_name, response.status_code, response.text,
            )
            # Non-fatal: the bucket may already allow these types.
            self.stdout.write(
                self.style.WARNING(
                    f"Could not update bucket (HTTP {response.status_code}); "
                    "uploads of unsupported types may still fail. "
                    "Update the bucket in the Supabase dashboard manually."
                )
            )
