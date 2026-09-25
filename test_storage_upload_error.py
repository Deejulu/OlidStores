"""
Test that a storage upload failure is handled gracefully by the CMS content
manage view: it must NOT return a raw 500 error page.

When the configured file storage raises an OSError/IOError while saving an
uploaded file (e.g. a Supabase 415 / storage rejection), the view should catch
it, surface a clear message, and re-render the page with the user's data intact.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.models import SiteContent


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
)
class ContentUploadErrorHandlingTest(TestCase):
    """Ensure storage failures never produce a raw 500 error page."""

    @classmethod
    def setUpTestData(cls):
        SiteContent.objects.get_or_create(key="homepage_banner")

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="pw12345"
        )
        # Bypass django-axes (it requires a request in authenticate()) during tests.
        self.client.force_login(
            self.user, backend="django.contrib.auth.backends.ModelBackend"
        )

    def _patch_save_to_fail(self):
        """
        Patch ``SiteContentForm.save`` so it raises an IOError, mirroring the
        storage rejection (``SupabaseStorage._save`` -> 415) raised on
        production. This exercises the view's ``_safe_save`` error handling.
        """
        from core.forms import SiteContentForm

        def _failing_save(self, commit=True):
            raise IOError("Failed to upload file to Supabase: 415 invalid_mime_type")

        return mock.patch.object(SiteContentForm, "save", _failing_save)

    def test_upload_failure_returns_clean_response_not_500(self):
        """A storage failure during save should not crash as a 500."""
        fake_video = SimpleUploadedFile(
            name="stars.mp4",
            content=b"%PDF-1.4 fake video bytes",
            content_type="video/mp4",
        )

        with self._patch_save_to_fail():
            response = self.client.post(
                "/admin-dashboard/content/",
                data={"banner-background_style": "video"},
                files={"banner-background_video": fake_video},
            )

        self.assertNotEqual(response.status_code, 500)
        self.assertIn(response.status_code, (200, 302))

    def test_upload_failure_shows_friendly_message(self):
        """On a non-AJAX request a 200 is returned with a friendly message."""
        fake_video = SimpleUploadedFile(
            name="stars.mp4",
            content=b"%PDF-1.4 fake video bytes",
            content_type="video/mp4",
        )

        with self._patch_save_to_fail():
            response = self.client.post(
                "/admin-dashboard/content/",
                data={"banner-background_style": "video"},
                files={"banner-background_video": fake_video},
            )

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8", errors="replace")
        self.assertIn("file upload to", content)
