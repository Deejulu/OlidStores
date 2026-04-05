from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

class SampleDataTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='adm', email='adm@example.com', password='pass')
        # ensure role is admin so admin_role_required decorator allows access
        self.admin.role = 'admin'
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.client = Client()
        self.client.force_login(self.admin)

    def test_generate_sample_users_are_customers(self):
        resp = self.client.get(reverse('admin_dashboard:generate_sample_data'))
        self.assertEqual(resp.status_code, 302)  # redirect to analytics
        User = get_user_model()
        samples = User.objects.filter(username__startswith='sample_user_')
        self.assertTrue(samples.exists())
        for u in samples:
            self.assertEqual(u.role, 'customer')
            self.assertFalse(u.is_staff)
            self.assertFalse(u.is_superuser)

class CustomUserDefaultsTest(TestCase):
    def test_default_role_is_customer(self):
        User = get_user_model()
        u = User.objects.create_user(username='newuser', email='new@example.com', password='x')
        self.assertEqual(u.role, 'customer')

class ContentManageImagesTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='adm2', email='adm2@example.com', password='pass')
        self.admin.role='admin'
        self.admin.is_staff=True
        self.admin.is_superuser=True
        self.admin.save()
        self.client = Client()
        self.client.force_login(self.admin)

    def test_content_manage_banner_section(self):
        resp = self.client.get(reverse('admin_dashboard:content_manage'))
        self.assertEqual(resp.status_code, 200)
        # updated template — ensure banner section and quick-link are present
        self.assertIn('banner-section', resp.content.decode())
        self.assertIn('Homepage Banner', resp.content.decode())

    def test_ajax_save_content_returns_json(self):
        # Test that AJAX POST returns JSON success
        resp = self.client.post(reverse('admin_dashboard:content_manage'), {
            'about-title': 'AJAX',
            'about-content': 'ajax test content',
            'about-key': 'about',
            'contact-key': 'contact',
            'banner-key': 'homepage_banner',
            'banner-background_style': 'gradient_blue',
            # management form fields minimal
            'bimgs-TOTAL_FORMS': '0',
            'bimgs-INITIAL_FORMS': '0',
            'heros-TOTAL_FORMS': '0',
            'heros-INITIAL_FORMS': '0',
        }, **{'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'})
        import json
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get('success'))

    def test_update_checkout_fees_via_content_manage(self):
        # POST to content manage to update checkout fees
        # Use non-AJAX POST (redirect on success) to avoid JS-only behavior in tests
        resp = self.client.post(reverse('admin_dashboard:content_manage'), {
            'about-title': 'About',
            'about-content': 'About',
            'about-key': 'about',
            'contact-key': 'contact',
            'banner-key': 'homepage_banner',
            'banner-background_style': 'gradient_blue',
            'checkout-key': 'checkout',
            'checkout-title': 'Checkout',
            'checkout-content': 'Checkout info',
            'checkout-delivery_fee_24h': '33.50',
            'checkout-delivery_fee_2d': '12.00',
            # minimal management form fields
            'bimgs-TOTAL_FORMS': '0',
            'bimgs-INITIAL_FORMS': '0',
            'heros-TOTAL_FORMS': '0',
            'heros-INITIAL_FORMS': '0',
        })
        # Non-AJAX POST should redirect on success
        self.assertIn(resp.status_code, (302, 200))
        # verify site content updated
        from core.models import SiteContent
        sc = SiteContent.objects.filter(key='checkout').first()
        self.assertIsNotNone(sc)
        self.assertEqual(float(sc.delivery_fee_24h), 33.50)
        self.assertEqual(float(sc.delivery_fee_2d), 12.00)

    def test_bulk_mark_shipped_sets_shipped_at(self):
        # create a sample order and use bulk action to mark shipped
        from orders.models import Order
        order = Order.objects.create(full_name='Test', phone='123', email='t@t.com', delivery_address='X', total=10.0, status='Processing')
        resp = self.client.post(reverse('admin_dashboard:order_list'), {
            'bulk_action': 'mark_shipped',
            'order_ids': [str(order.id)]
        })
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Shipped')
        self.assertIsNotNone(order.shipped_at)

    def test_bulk_mark_delivered_sets_delivered_at(self):
        from orders.models import Order
        order = Order.objects.create(full_name='Test', phone='123', email='t@t.com', delivery_address='X', total=10.0, status='Shipped')
        resp = self.client.post(reverse('admin_dashboard:order_list'), {
            'bulk_action': 'mark_delivered',
            'order_ids': [str(order.id)]
        })
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, 'Delivered')
        self.assertIsNotNone(order.delivered_at)
