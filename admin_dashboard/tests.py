from django.test import TestCase, Client, override_settings, TransactionTestCase
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

    @override_settings(DEBUG=True)
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


class MarkAllReadTest(TestCase):
    """Verify the admin 'clear all' action marks unread chat messages read + feedback resolved."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='admin_test', email='admin@test.com', password='testpass123')
        self.admin.role = 'admin'
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.client = Client()
        self.client.force_login(self.admin)

    def _make_unread_chat(self):
        from core.models import ChatConversation, ChatMessage
        conv = ChatConversation.objects.create(subject='Support')
        ChatMessage.objects.create(
            conversation=conv, sender_type='customer', message='Hello?', is_read=False
        )
        return conv

    def test_mark_all_read_clears_unread_chats(self):
        from core.models import ChatMessage
        from users.models import Feedback
        self._make_unread_chat()
        self._make_unread_chat()
        Feedback.objects.create(user=self.admin, message='Great!', is_resolved=False)

        self.assertEqual(ChatMessage.objects.filter(sender_type='customer', is_read=False).count(), 2)
        self.assertEqual(Feedback.objects.filter(is_resolved=False).count(), 1)

        resp = self.client.post(reverse('admin_dashboard:mark_all_notifications_read'))
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(ChatMessage.objects.filter(sender_type='customer', is_read=False).count(), 0)
        self.assertEqual(Feedback.objects.filter(is_resolved=False).count(), 0)

    def test_mark_all_read_clears_cache(self):
        from django.core.cache import cache
        from django.test import RequestFactory
        self._make_unread_chat()

        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.admin

        from admin_dashboard.context_processors import admin_notifications
        result = admin_notifications(request)
        self.assertGreater(result['admin_unread_chats'], 0)

        resp = self.client.post(reverse('admin_dashboard:mark_all_notifications_read'))
        self.assertEqual(resp.status_code, 302)

        result = admin_notifications(request)
        self.assertEqual(result['admin_unread_chats'], 0)

    def test_mark_all_notifications_read_updates_chat_and_feedback(self):
        from core.models import ChatMessage
        from users.models import Feedback
        self._make_unread_chat()
        Feedback.objects.create(user=self.admin, message='Great service!', is_resolved=False)

        self.assertEqual(ChatMessage.objects.filter(sender_type='customer', is_read=False).count(), 1)
        self.assertEqual(Feedback.objects.filter(is_resolved=False).count(), 1)

        resp = self.client.post(reverse('admin_dashboard:mark_all_notifications_read'))
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(ChatMessage.objects.filter(sender_type='customer', is_read=False).count(), 0)
        self.assertEqual(Feedback.objects.filter(is_resolved=False).count(), 0)


class ContactPageTests(TestCase):
    """The contact page must show info + a Start Chat button and contain NO form fields."""

    def setUp(self):
        self.client = Client(HTTP_HOST='127.0.0.1')

    def test_contact_page_get_has_start_chat_and_no_form_fields(self):
        resp = self.client.get('/contact/')
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # No contact-form fields should remain
        self.assertNotIn('name="name"', content)
        self.assertNotIn('name="email"', content)
        self.assertNotIn('name="message"', content)
        self.assertNotIn('name="subject"', content)
        self.assertNotIn('name="honeypot"', content)
        # Start Chat button must trigger the floating widget
        self.assertIn('startChatBtn', content)
        self.assertIn("getElementById('fcFabIcon').click()", content)


class AdminChatInboxTest(TestCase):
    """The admin inbox must return only chat conversations (no contact-message type)."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='admchat', email='admchat@example.com', password='pass')
        self.admin.role = 'admin'
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.client = Client()
        self.client.force_login(self.admin)
        from core.models import ChatConversation, ChatMessage
        self.conv = ChatConversation.objects.create(subject='Help')
        ChatMessage.objects.create(conversation=self.conv, sender_type='customer', message='Hi', is_read=False)

    def test_chat_list_shows_conversations_only(self):
        resp = self.client.get(reverse('admin_dashboard:chat_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.conv, resp.context['conversations'])


class UnifiedSampleDataTest(TransactionTestCase):
    """Tests for the unified Populate Sample Data / Delete Sample Data buttons."""
    reset_sequences = True

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(username='adm_unified', email='adm_unified@example.com', password='pass')
        self.admin.role = 'admin'
        self.admin.is_staff = True
        self.admin.is_superuser = True
        self.admin.save()
        self.client = Client()
        self.client.force_login(self.admin)
        self.sample_post_data = {'confirmation': 'CONFIRM'}

    @override_settings(DEBUG=True)
    def test_populate_creates_sample_data_across_all_models(self):
        """Full populate creates expected record counts across every model, all flagged is_sample=True."""
        from products.models import Category, Product
        from orders.models import Order, OrderItem, PaymentTransaction

        resp = self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)  # redirect to dashboard

        # Categories
        sample_cats = Category.objects.filter(is_sample=True)
        self.assertGreaterEqual(sample_cats.count(), 9)

        # Products
        sample_products = Product.objects.filter(is_sample=True)
        self.assertGreaterEqual(sample_products.count(), 120)

        # Customers
        User = get_user_model()
        sample_users = User.objects.filter(is_sample=True, role='customer')
        self.assertGreaterEqual(sample_users.count(), 5)

        # Orders
        sample_orders = Order.objects.filter(is_sample=True)
        self.assertGreater(sample_orders.count(), 0)

        # OrderItems
        sample_items = OrderItem.objects.filter(is_sample=True)
        self.assertGreater(sample_items.count(), 0)

        # PaymentTransactions
        sample_payments = PaymentTransaction.objects.filter(is_sample=True)
        self.assertGreater(sample_payments.count(), 0)

    @override_settings(DEBUG=True)
    def test_populate_twice_does_not_destroy_data(self):
        """Running populate a second time does not duplicate real-looking data or destroy anything."""
        from products.models import Category, Product
        from orders.models import Order, OrderItem, PaymentTransaction

        # First populate
        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        first_product_count = Product.objects.filter(is_sample=True).count()
        first_order_count = Order.objects.filter(is_sample=True).count()

        # Second populate
        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        second_product_count = Product.objects.filter(is_sample=True).count()
        second_order_count = Order.objects.filter(is_sample=True).count()

        # Product count should be the same (120 samples, not 240)
        self.assertEqual(first_product_count, second_product_count)
        # Orders may vary due to randomness, but should be in similar range
        self.assertAlmostEqual(first_order_count, second_order_count, delta=10)

    @override_settings(DEBUG=True)
    def test_real_data_survives_populate_and_delete(self):
        """Real (non-sample) records created before populate are untouched after both populate and delete-sample."""
        from products.models import Category, Product
        from orders.models import Order, OrderItem, PaymentTransaction

        # Create REAL data before populate
        real_cat = Category.objects.create(name='Real Category', slug='real-category')
        real_product = Product.objects.create(
            name='Real Product',
            description='A real product',
            price=99.99,
            stock=10,
            category=real_cat,
            slug='real-product',
        )
        User = get_user_model()
        real_user = User.objects.create_user(
            username='real_customer',
            email='real@example.com',
            password='realpass123',
            role='customer',
        )
        real_order = Order.objects.create(
            user=real_user,
            full_name='Real Customer',
            phone='08012345678',
            email='real@example.com',
            delivery_address='123 Real Street',
            total=150.00,
            status='Processing',
        )
        real_item = OrderItem.objects.create(
            order=real_order,
            product=real_product,
            quantity=1,
            price=99.99,
        )
        real_payment = PaymentTransaction.objects.create(
            reference='REAL-PAYMENT-001',
            order=real_order,
            amount=150.00,
            currency='NGN',
            status='success',
        )

        # Run populate
        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)

        # Verify real data still exists
        self.assertTrue(Category.objects.filter(pk=real_cat.pk).exists())
        self.assertTrue(Product.objects.filter(pk=real_product.pk).exists())
        self.assertTrue(User.objects.filter(pk=real_user.pk).exists())
        self.assertTrue(Order.objects.filter(pk=real_order.pk).exists())
        self.assertTrue(OrderItem.objects.filter(pk=real_item.pk).exists())
        self.assertTrue(PaymentTransaction.objects.filter(pk=real_payment.pk).exists())

        # Verify real data is NOT flagged as sample
        real_cat.refresh_from_db()
        self.assertFalse(real_cat.is_sample)
        real_product.refresh_from_db()
        self.assertFalse(real_product.is_sample)
        real_user.refresh_from_db()
        self.assertFalse(real_user.is_sample)
        real_order.refresh_from_db()
        self.assertFalse(real_order.is_sample)

        # Run delete-sample
        self.client.post(reverse('admin_dashboard:delete_sample_data_full'), data=self.sample_post_data)

        # Verify real data STILL exists after delete
        self.assertTrue(Category.objects.filter(pk=real_cat.pk).exists())
        self.assertTrue(Product.objects.filter(pk=real_product.pk).exists())
        self.assertTrue(User.objects.filter(pk=real_user.pk).exists())
        self.assertTrue(Order.objects.filter(pk=real_order.pk).exists())
        self.assertTrue(OrderItem.objects.filter(pk=real_item.pk).exists())
        self.assertTrue(PaymentTransaction.objects.filter(pk=real_payment.pk).exists())

    @override_settings(DEBUG=True)
    def test_delete_removes_all_sample_data(self):
        """Delete removes all sample-flagged records across all models, in correct order."""
        from products.models import Category, Product
        from orders.models import Order, OrderItem, PaymentTransaction

        # First populate
        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        self.assertGreater(Product.objects.filter(is_sample=True).count(), 0)
        self.assertGreater(Order.objects.filter(is_sample=True).count(), 0)

        # Delete sample data
        resp = self.client.post(reverse('admin_dashboard:delete_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

        # Verify all sample data is gone
        self.assertEqual(Product.objects.filter(is_sample=True).count(), 0)
        self.assertEqual(Order.objects.filter(is_sample=True).count(), 0)
        self.assertEqual(OrderItem.objects.filter(is_sample=True).count(), 0)
        self.assertEqual(PaymentTransaction.objects.filter(is_sample=True).count(), 0)

        User = get_user_model()
        self.assertEqual(User.objects.filter(is_sample=True, role='customer').count(), 0)

    @override_settings(DEBUG=False)
    def test_populate_works_when_debug_false(self):
        """Populate view is accessible to admin even when DEBUG=False (admin gating, not DEBUG gating)."""
        resp = self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

    @override_settings(DEBUG=False)
    def test_delete_works_when_debug_false(self):
        """Delete view is accessible to admin even when DEBUG=False (admin gating, not DEBUG gating)."""
        resp = self.client.post(reverse('admin_dashboard:delete_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

    def test_populate_requires_admin(self):
        """Non-admin and anonymous users are redirected away from populate."""
        User = get_user_model()
        # Non-admin user
        non_admin = User.objects.create_user(
            username='regular', email='reg@example.com', password='pass', role='customer'
        )
        client2 = Client()
        client2.force_login(non_admin)
        resp = client2.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

        # Anonymous (not logged in)
        client3 = Client()
        resp = client3.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

    def test_delete_requires_admin(self):
        """Non-admin and anonymous users are redirected away from delete."""
        User = get_user_model()
        non_admin = User.objects.create_user(
            username='regular2', email='reg2@example.com', password='pass', role='customer'
        )
        client2 = Client()
        client2.force_login(non_admin)
        resp = client2.post(reverse('admin_dashboard:delete_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

        # Anonymous
        client3 = Client()
        resp = client3.post(reverse('admin_dashboard:delete_sample_data_full'), data=self.sample_post_data)
        self.assertEqual(resp.status_code, 302)

    def test_populate_requires_confirmation(self):
        """POST without confirmation='CONFIRM' is rejected and creates no data."""
        resp = self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data={})
        self.assertEqual(resp.status_code, 302)
        from products.models import Product
        self.assertEqual(Product.objects.filter(is_sample=True).count(), 0)

    def test_delete_requires_confirmation(self):
        """POST without confirmation='CONFIRM' is rejected and leaves sample data intact."""
        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)
        from products.models import Product
        self.assertGreater(Product.objects.filter(is_sample=True).count(), 0)

        resp = self.client.post(reverse('admin_dashboard:delete_sample_data_full'), data={})
        self.assertEqual(resp.status_code, 302)
        self.assertGreater(Product.objects.filter(is_sample=True).count(), 0)

    def test_real_user_not_marked_sample_on_populate(self):
        """An existing real user whose username matches a sample username is NOT converted to sample."""
        from products.models import Category
        User = get_user_model()
        # Create a real user whose username matches one of the sample usernames
        real_user = User.objects.create_user(
            username='adaobi.sample',
            email='adaobi.real@example.com',
            password='realpass123',
            role='customer',
        )
        self.assertFalse(real_user.is_sample)

        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)

        real_user.refresh_from_db()
        self.assertFalse(real_user.is_sample)

    def test_real_category_not_marked_sample_on_populate(self):
        """An existing real category sharing a sample-category name is NOT converted to sample."""
        from products.models import Category
        # Create a real category with the same name as a sample category
        real_cat = Category.objects.create(name='Electronics', slug='electronics-real', is_sample=False)
        self.assertFalse(real_cat.is_sample)

        self.client.post(reverse('admin_dashboard:populate_sample_data_full'), data=self.sample_post_data)

        real_cat.refresh_from_db()
        self.assertFalse(real_cat.is_sample)

    def test_buttons_render_in_template_for_admin(self):
        """Sample Data section renders in dashboard template for admin users."""
        resp = self.client.get(reverse('admin_dashboard:dashboard_home'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Sample Data', content)
        self.assertIn('Populate Sample Data', content)
        self.assertIn('Delete Sample Data', content)

    @override_settings(DEBUG=False)
    def test_buttons_render_in_template_when_debug_false(self):
        """Sample Data section renders for admin even when DEBUG=False."""
        resp = self.client.get(reverse('admin_dashboard:dashboard_home'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Sample Data', content)
        self.assertIn('Populate Sample Data', content)
        self.assertIn('Delete Sample Data', content)

    def test_buttons_do_not_render_for_non_admin(self):
        """Sample Data section does NOT render for non-admin users (redirected away)."""
        User = get_user_model()
        non_admin = User.objects.create_user(
            username='regular3', email='reg3@example.com', password='pass', role='customer'
        )
        client2 = Client()
        client2.force_login(non_admin)
        resp = client2.get(reverse('admin_dashboard:dashboard_home'))
        self.assertEqual(resp.status_code, 302)  # non-admin redirected away from dashboard

    @override_settings(DEBUG=True)
    def test_populate_requires_post(self):
        """Populate view only accepts POST requests."""
        resp = self.client.get(reverse('admin_dashboard:populate_sample_data_full'))
        self.assertEqual(resp.status_code, 302)  # redirect

    @override_settings(DEBUG=True)
    def test_delete_requires_post(self):
        """Delete view only accepts POST requests."""
        resp = self.client.get(reverse('admin_dashboard:delete_sample_data_full'))
        self.assertEqual(resp.status_code, 302)  # redirect

