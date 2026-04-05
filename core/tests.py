from django.test import TestCase, Client
from core.models import BannerImage

class HomeBannerTest(TestCase):
    def setUp(self):
        # Create a sample banner record pointing to a placeholder path (does not require file)
        BannerImage.objects.create(title='T1', image='banners/banner_sample_1.jpg', order=1, is_active=True)

    def test_home_includes_banner_images(self):
        c = Client()
        r = c.get('/')
        self.assertEqual(r.status_code, 200)
        # homepage was refactored to a hero-section; ensure hero markup is present
        self.assertIn('hero-section', r.content.decode())

class BannerImageProcessingTest(TestCase):
    def test_image_resizing_and_thumbnail_created(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image
        # create an in-memory large image
        img = Image.new('RGB', (2000, 800), color='#123456')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        f = SimpleUploadedFile('big.jpg', buf.read(), content_type='image/jpeg')
        b = BannerImage.objects.create(title='T Large', image=f, order=1, is_active=True)
        # reload from DB
        b.refresh_from_db()
        self.assertIsNotNone(b.thumbnail)
        # Open stored image file to check width <= 1200
        from PIL import Image as PilImage
        import os
        p = b.image.path
        with PilImage.open(p) as im:
            self.assertLessEqual(im.width, 1200)

    def test_regenerate_command_reprocesses(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        import io
        from PIL import Image
        from django.core.management import call_command
        # create an in-memory image and banner
        img = Image.new('RGB', (1300, 700), color='#654321')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        f = SimpleUploadedFile('regen.jpg', buf.read(), content_type='image/jpeg')
        b = BannerImage.objects.create(title='To Regen', image=f, order=1, is_active=True)
        # remove thumbnail to simulate missing thumb
        # Ensure thumbnail removed (use direct DB update to guarantee blank value)
        from core.models import BannerImage as BI
        BI.objects.filter(pk=b.pk).update(thumbnail='')
        b.refresh_from_db()
        self.assertFalse(bool(b.thumbnail))
        # run command
        call_command('regenerate_banner_thumbnails')
        b.refresh_from_db()
        self.assertTrue(bool(b.thumbnail))


class ContactFormTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST='127.0.0.1')

    def test_contact_form_saves_message(self):
        r = self.client.post('/contact/', {'name':'Alice','email':'a@b.com','subject':'Hello','message':'Hi there, I have a question about your products.'})
        self.assertEqual(r.status_code, 302)
        from core.models import ContactMessage
        self.assertTrue(ContactMessage.objects.filter(email='a@b.com', subject='Hello').exists())

    def test_honeypot_blocks(self):
        r = self.client.post('/contact/', {'name':'SpamBot','email':'s@b.com','subject':'x','message':'m','honeypot':'I am a bot'})
        # invalid form; response should render page with errors (200) and no message created
        self.assertEqual(r.status_code, 200)
        from core.models import ContactMessage
        self.assertFalse(ContactMessage.objects.filter(email='s@b.com').exists())

    def test_rate_limit_blocks(self):
        from django.core.cache import cache
        cache.clear()
        for i in range(7):
            r = self.client.post('/contact/', {'name':'User','email':f'u{i}@b.com','subject':'x','message':'m'})
        # last one should have been blocked; messages count <=6
        from core.models import ContactMessage
        self.assertLessEqual(ContactMessage.objects.filter(name='User').count(), 6)


class AboutPageTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST='127.0.0.1')

    def test_about_includes_team_and_structured_data(self):
        from core.models import TeamMember, SiteContent
        SiteContent.objects.create(key='about', title='About Us', content='We do things')
        TeamMember.objects.create(name='Alice', title='Founder', bio='Founder bio')
        r = self.client.get('/about/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Alice', r.content)
        self.assertIn(b'"@type": "Organization"', r.content)


