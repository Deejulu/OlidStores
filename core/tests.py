from django.test import TestCase, Client
from core.models import BannerImage
import json
import os
from unittest.mock import patch
from urllib.parse import quote


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


class ChatTier1MatchTests(TestCase):
    """Tier 1: keyword rule match should fire instantly and return 'tier1'."""

    def setUp(self):
        from core.models import ChatAutoReply, ChatConversation, ChatMessage
        # Ensure defaults are loaded
        from core.views import _ensure_default_auto_replies
        _ensure_default_auto_replies()
        self.conv = ChatConversation.objects.create(
            guest_name='Test User',
            guest_email='test@example.com',
            subject='Support',
            status='open',
        )

    def test_tier1_match_returns_tier1(self):
        from core.views import _try_auto_reply
        # "Where is my order?" is now an account-specific intent. For a guest
        # (no request / not authenticated) the bot asks them to sign in instead
        # of giving a generic scripted answer -- no crash, no data leak.
        tier = _try_auto_reply(self.conv, 'Where is my order?')
        self.assertEqual(tier, 'tier1')
        msgs = self.conv.messages.filter(sender_type='admin')
        self.assertEqual(msgs.count(), 1)
        self.assertIn('sign in', msgs.first().message.lower())

    def test_tier1_payment_methods_match(self):
        from core.views import _try_auto_reply
        tier = _try_auto_reply(self.conv, 'How do I pay? What payment methods do you accept?')
        self.assertEqual(tier, 'tier1')
        msgs = self.conv.messages.filter(sender_type='admin')
        self.assertEqual(msgs.count(), 1)
        self.assertIn('Paystack', msgs.first().message)

    def test_tier1_greeting_match(self):
        from core.views import _try_auto_reply
        tier = _try_auto_reply(self.conv, 'Hello there!')
        self.assertEqual(tier, 'tier1')
        msgs = self.conv.messages.filter(sender_type='admin')
        self.assertEqual(msgs.count(), 1)
        self.assertIn('Welcome', msgs.first().message)


class ChatTier2AIFallbackTests(TestCase):
    """Tier 2: AI fallback for unmatched questions."""

    def setUp(self):
        from core.models import ChatConversation
        self.conv = ChatConversation.objects.create(
            guest_name='AI User',
            guest_email='ai@example.com',
            subject='Support',
            status='open',
        )
        # Ensure no auto-replies match our test question
        from core.models import ChatAutoReply
        ChatAutoReply.objects.filter(is_active=True).update(is_active=False)
        # Set a dummy API key so the Anthropic client is instantiated (mocked in tests)
        import os
        os.environ['ANTHROPIC_API_KEY'] = 'sk-test-mock-key'

    def tearDown(self):
        # Do not leak the dummy key into other test classes (avoids real API calls).
        os.environ.pop('ANTHROPIC_API_KEY', None)

    def _mock_anthropic_response(self, text):
        from unittest.mock import MagicMock, patch
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text=text)]
        mock_client.messages.create.return_value = mock_msg
        return patch('anthropic.Anthropic', return_value=mock_client)

    def test_tier2_ai_reply_success(self):
        from core.ai_reply import get_ai_reply
        with self._mock_anthropic_response('We offer exchange within 7 days for different sizes.'):
            with self.settings(CHAT_AI_PER_CONV_CAP=5):
                reply, tier, info = get_ai_reply(self.conv.pk, 'Can I swap for a larger size?')
        self.assertEqual(tier, 'tier2')
        self.assertIsNotNone(reply)
        self.assertEqual(reply, 'We offer exchange within 7 days for different sizes.')

    def test_tier2_ai_cache_hit(self):
        from core.ai_reply import get_ai_reply
        from django.core.cache import cache
        cache.clear()
        with self._mock_anthropic_response('Cached answer'):
            with self.settings(CHAT_AI_PER_CONV_CAP=5):
                reply1, tier1, info1 = get_ai_reply(self.conv.pk, 'What is your return policy?')
        self.assertEqual(tier1, 'tier2')
        self.assertEqual(reply1, 'Cached answer')

        # Second call should hit cache, not API
        with self._mock_anthropic_response('Should not be called'):
            with self.settings(CHAT_AI_PER_CONV_CAP=5):
                reply2, tier2, info2 = get_ai_reply(self.conv.pk, 'What is your return policy?')
        self.assertEqual(tier2, 'tier2')
        self.assertEqual(reply2, 'Cached answer')
        self.assertEqual(info2.get('reason'), 'cache_hit')

    def test_tier2_account_specific_handoff(self):
        from core.ai_reply import get_ai_reply
        reply, tier, info = get_ai_reply(self.conv.pk, 'Where is my order #4521?')
        self.assertIsNone(reply)
        self.assertEqual(tier, 'tier3')
        self.assertEqual(info.get('reason'), 'account_specific_question')

    def test_tier2_per_conversation_cap(self):
        from core.ai_reply import get_ai_reply
        from django.core.cache import cache
        import os
        cache.clear()
        old_cap = os.environ.get('CHAT_AI_PER_CONV_CAP')
        os.environ['CHAT_AI_PER_CONV_CAP'] = '2'
        try:
            # Force reimport to pick up new env var
            import importlib
            import core.ai_reply
            importlib.reload(core.ai_reply)
            with self._mock_anthropic_response('Answer'):
                get_ai_reply(self.conv.pk, 'Question one?')
                get_ai_reply(self.conv.pk, 'Question two?')
                reply, tier, info = get_ai_reply(self.conv.pk, 'Question three?')
        finally:
            if old_cap is not None:
                os.environ['CHAT_AI_PER_CONV_CAP'] = old_cap
            else:
                os.environ.pop('CHAT_AI_PER_CONV_CAP', None)
            importlib.reload(core.ai_reply)
        self.assertIsNone(reply)
        self.assertEqual(tier, 'tier3')
        self.assertEqual(info.get('reason'), 'per_conversation_cap_reached')

    def test_tier2_ai_uncertain_handoff(self):
        from core.ai_reply import get_ai_reply
        uncertain_text = 'I am sorry, I cannot access order status. Please contact our support team.'
        with self._mock_anthropic_response(uncertain_text):
            with self.settings(CHAT_AI_PER_CONV_CAP=5):
                reply, tier, info = get_ai_reply(self.conv.pk, 'What is the status of my package?')
        self.assertIsNone(reply)
        self.assertEqual(tier, 'tier3')
        self.assertEqual(info.get('reason'), 'ai_uncertain')

    def test_tier2_api_error_handoff(self):
        from core.ai_reply import get_ai_reply
        from unittest.mock import MagicMock, patch
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception('Timeout')
        with patch('anthropic.Anthropic', return_value=mock_client):
            with self.settings(CHAT_AI_PER_CONV_CAP=5):
                reply, tier, info = get_ai_reply(self.conv.pk, 'Tell me about your products?')
        self.assertIsNone(reply)
        self.assertEqual(tier, 'tier3')
        self.assertIn('ai_api_error', info.get('reason', ''))


class ChatTier3HandoffTests(TestCase):
    """Tier 3: human handoff should leave conversation open with no bot reply."""

    def setUp(self):
        from core.models import ChatConversation, ChatAutoReply
        ChatAutoReply.objects.filter(is_active=True).update(is_active=False)
        self.conv = ChatConversation.objects.create(
            guest_name='Tier3 User',
            guest_email='t3@example.com',
            subject='Support',
            status='open',
        )

    def test_tier3_no_bot_reply_on_unmatched(self):
        from core.views import _try_auto_reply
        tier = _try_auto_reply(self.conv, 'Zyxwvutsrqponmlkjihgfedcba question')
        self.assertEqual(tier, 'tier3')
        msgs = self.conv.messages.filter(sender_type='admin')
        self.assertEqual(msgs.count(), 0)


class ChatAPIIntegrationTests(TestCase):
    """Integration tests for chat_start and chat_send with 3-tier routing."""

    def setUp(self):
        self.client = Client(HTTP_HOST='127.0.0.1')
        from core.models import ChatAutoReply
        ChatAutoReply.objects.filter(is_active=True).update(is_active=False)

    def test_chat_start_tier1_reply(self):
        from core.views import _ensure_default_auto_replies
        _ensure_default_auto_replies()
        payload = {
            'name': 'Alice',
            'email': 'alice@example.com',
            'subject': 'Help',
            'message': 'Hello!',
        }
        r = self.client.post('/chat/start/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data['success'])
        conv_id = data['conversation_id']
        from core.models import ChatConversation
        conv = ChatConversation.objects.get(pk=conv_id)
        # Welcome message + Tier 1 bot reply
        admin_msgs = conv.messages.filter(sender_type='admin')
        self.assertEqual(admin_msgs.count(), 2)
        self.assertIn('Welcome', admin_msgs.first().message)
        self.assertIn('Hello!', admin_msgs.last().message)

    def test_chat_start_tier3_handoff(self):
        payload = {
            'name': 'Bob',
            'email': 'bob@example.com',
            'subject': 'Help',
            'message': 'What is the meaning of life?',
        }
        r = self.client.post('/chat/start/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data['success'])
        conv_id = data['conversation_id']
        from core.models import ChatConversation
        conv = ChatConversation.objects.get(pk=conv_id)
        # Only welcome message, no bot reply (Tier 3)
        admin_msgs = conv.messages.filter(sender_type='admin')
        self.assertEqual(admin_msgs.count(), 1)
        self.assertIn('Welcome', admin_msgs.first().message)

    def test_chat_send_subsequent_tier3(self):
        from core.models import ChatConversation, ChatAutoReply
        ChatAutoReply.objects.filter(is_active=True).update(is_active=False)
        conv = ChatConversation.objects.create(
            guest_name='Subsequent',
            guest_email='sub@example.com',
            subject='Support',
            status='open',
        )
        payload = {
            'conversation_id': conv.pk,
            'message': 'Zyxwvutsrqponmlkjihgfedcba question',
        }
        r = self.client.post('/chat/send/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content)
        self.assertTrue(data['success'])
        conv.refresh_from_db()
        admin_msgs = conv.messages.filter(sender_type='admin')
        self.assertEqual(admin_msgs.count(), 0)


class AISystemPromptTests(TestCase):
    """Verify the AI system prompt contains correct store context."""

    def test_system_prompt_contains_store_info(self):
        from core.ai_reply import get_ai_system_prompt_text, _get_store_context
        prompt = get_ai_system_prompt_text()
        ctx = _get_store_context()
        self.assertIn(ctx['store_name'], prompt)
        self.assertIn('CRITICAL RULES', prompt)
        self.assertIn('NEVER invent order status', prompt)
        self.assertIn('tracking numbers', prompt)
        self.assertIn('stock levels', prompt)
        self.assertIn('contact support', prompt)


class ChatAccountDataSecurityTests(TestCase):
    """Verify a logged-in user cannot retrieve another user's order/payment data through chat."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from core.models import ChatConversation, ChatAutoReply

        self.User = get_user_model()
        self.user_a = self.User.objects.create_user(
            username='user_a', email='a@example.com', password='pass123'
        )
        self.user_b = self.User.objects.create_user(
            username='user_b', email='b@example.com', password='pass123'
        )

        self.conv_a = ChatConversation.objects.create(
            user=self.user_a,
            subject='My orders',
            status='open',
        )
        self.conv_b = ChatConversation.objects.create(
            user=self.user_b,
            subject='My orders',
            status='open',
        )

        ChatAutoReply.objects.filter(is_active=True).update(is_active=False)

        self.client_a = Client()
        self.client_b = Client()
        self.client_a.force_login(self.user_a)
        self.client_b.force_login(self.user_b)

    def test_user_a_cannot_access_user_b_conversation(self):
        payload = {
            'conversation_id': self.conv_b.pk,
            'message': 'Where is my order?',
        }
        r = self.client_a.post(
            '/chat/send/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_user_b_cannot_access_user_a_conversation(self):
        payload = {
            'conversation_id': self.conv_a.pk,
            'message': 'Where is my order?',
        }
        r = self.client_b.post(
            '/chat/send/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 404)

    def test_tier2_account_specific_handoff_blocks_data_leak(self):
        from core.ai_reply import get_ai_reply
        reply, tier, info = get_ai_reply(
            self.conv_a.pk, 'What is the status of my order ORD-B-001?'
        )
        self.assertIsNone(reply)
        self.assertEqual(tier, 'tier3')
        self.assertEqual(info.get('reason'), 'account_specific_question')


class ChatAccountIntentTests(TestCase):
    """Account-specific intents return real, user-scoped data; guests are prompted to log in."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from orders.models import Order, PaymentTransaction
        from core.models import ChatConversation, ChatAutoReply
        from core.views import _ensure_default_auto_replies

        self.User = get_user_model()
        self.alice = self.User.objects.create_user('alice', email='alice@example.com', password='pass123')
        self.bob = self.User.objects.create_user('bob', email='bob@example.com', password='pass123')

        self.alice_order = Order.objects.create(
            user=self.alice, full_name='Alice A', phone='08010000001',
            email='alice@example.com', delivery_address='1 Alice St',
            total=15000, status='Shipped', tracking_number='TRK-ALICE-0001',
        )
        self.bob_order = Order.objects.create(
            user=self.bob, full_name='Bob B', phone='08020000002',
            email='bob@example.com', delivery_address='2 Bob Ave',
            total=8000, status='Processing', tracking_number='TRK-BOB-0002',
        )

        self.alice_payment = PaymentTransaction.objects.create(
            order=self.alice_order, reference='ref_alice_1', amount=15000,
            currency='NGN', status='success', payment_method='card',
        )
        self.bob_payment = PaymentTransaction.objects.create(
            order=self.bob_order, reference='ref_bob_1', amount=8000,
            currency='NGN', status='failed', payment_method='bank',
        )

        # Disable generic keyword rules so only account intents are exercised.
        ChatAutoReply.objects.filter(is_active=True).update(is_active=False)
        _ensure_default_auto_replies()

    def _client_for(self, user):
        c = Client()
        c.force_login(user)
        return c

    def _send_and_get_bot_reply(self, message, conv_user=None):
        """POST /chat/send/ as `conv_user`, then fetch history and return bot reply text."""
        from core.models import ChatConversation
        if conv_user is None:
            conv_user = self.alice
        conv = ChatConversation.objects.create(user=conv_user, subject='Chat', status='open')
        client = self._client_for(conv_user)
        r = client.post('/chat/send/', data=json.dumps({'conversation_id': conv.pk, 'message': message}),
                        content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        h = client.get('/chat/history/%d/' % conv.pk)
        hist = json.loads(h.content)
        admin_msgs = [m['message'] for m in hist['messages'] if m['sender_type'] == 'admin']
        self.assertTrue(admin_msgs, 'expected a bot reply')
        return '\n'.join(admin_msgs)

    def test_order_status_returns_own_real_data(self):
        reply = self._send_and_get_bot_reply('Where are my orders?', conv_user=self.alice)
        self.assertIn(self.alice_order.number, reply)
        self.assertIn('Shipped', reply)

    def test_order_status_specific_number_resolves_own_order(self):
        reply = self._send_and_get_bot_reply('Where is my order %s?' % self.alice_order.number,
                                             conv_user=self.alice)
        self.assertIn(self.alice_order.number, reply)
        self.assertIn('Tracking: TRK-ALICE-0001', reply)

    def test_payment_status_returns_own_data(self):
        reply = self._send_and_get_bot_reply('When am I expecting my payment?', conv_user=self.alice)
        self.assertIn(self.alice_order.number, reply)
        self.assertIn('15000', reply)
        self.assertIn('card', reply)
        self.assertNotIn(self.bob_order.number, reply)
        self.assertNotIn('ref_bob_1', reply)

    def test_payment_history_returns_own_payments(self):
        reply = self._send_and_get_bot_reply('Where can I see my previous payment(s)?', conv_user=self.alice)
        self.assertIn('ref_alice_1', reply)
        self.assertIn(self.alice_order.number, reply)

    def test_user_cannot_see_other_users_order_data(self):
        # Alice asks about Bob's order number -- must only ever see her own data.
        reply = self._send_and_get_bot_reply('Where is my order %s?' % self.bob_order.number,
                                             conv_user=self.alice)
        self.assertIn(self.alice_order.number, reply)
        self.assertNotIn(self.bob_order.number, reply)
        self.assertNotIn('TRK-BOB-0002', reply)
        self.assertNotIn('ref_bob_1', reply)

    def test_user_cannot_see_other_users_payment_history(self):
        reply = self._send_and_get_bot_reply('Show me my payments', conv_user=self.alice)
        self.assertNotIn('ref_bob_1', reply)
        self.assertNotIn(self.bob_order.number, reply)

    def test_guest_account_question_prompts_login_not_error(self):
        c = Client()  # anonymous guest
        # Start with a greeting so no live AI call happens; then ask an account question.
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}):
            r = c.post('/chat/start/', data=json.dumps(
                {'name': 'Guest', 'email': 'g@x.com', 'subject': 'Support', 'message': 'Hi'}),
                content_type='application/json')
            conv_id = json.loads(r.content)['conversation_id']
        r2 = c.post('/chat/send/', data=json.dumps(
            {'conversation_id': conv_id, 'message': 'Where is my order #EST-2026-9999?'}),
            content_type='application/json')
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertTrue(json.loads(r2.content)['success'])
        h = c.get('/chat/history/%d/' % conv_id)
        hist = json.loads(h.content)
        admin_msgs = [m['message'] for m in hist['messages'] if m['sender_type'] == 'admin']
        self.assertTrue(admin_msgs)
        bot_reply = '\n'.join(admin_msgs)
        # Must prompt to log in and must NOT leak anyone's order data.
        self.assertIn('sign in', bot_reply.lower())
        self.assertNotIn('EST-2026-9999', bot_reply)

    def test_guest_payment_history_prompts_login(self):
        c = Client()
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''}):
            r = c.post('/chat/start/', data=json.dumps(
                {'name': 'Guest', 'email': 'g@x.com', 'subject': 'Support', 'message': 'Hi'}),
                content_type='application/json')
            conv_id = json.loads(r.content)['conversation_id']
        r2 = c.post('/chat/send/', data=json.dumps(
            {'conversation_id': conv_id, 'message': 'my payment history'}),
            content_type='application/json')
        self.assertEqual(r2.status_code, 200)
        h = c.get('/chat/history/%d/' % conv_id)
        bot_reply = '\n'.join(m['message'] for m in json.loads(h.content)['messages']
                              if m['sender_type'] == 'admin')
        self.assertIn('sign in', bot_reply.lower())


class ChatDuplicationTests(TestCase):
    """Rapid sends and overlapping polls must not duplicate messages."""

    def setUp(self):
        from core.views import _ensure_default_auto_replies
        _ensure_default_auto_replies()
        from core.models import ChatConversation
        self.conv = ChatConversation.objects.create(
            guest_name='Dup', guest_email='d@x.com', subject='Support', status='open')

    def test_rapid_sends_one_user_msg_and_one_bot_reply_each(self):
        from core.models import ChatMessage
        c = Client()
        n = 5
        for i in range(n):
            r = c.post('/chat/send/', data=json.dumps(
                {'conversation_id': self.conv.pk, 'message': 'hello'}),
                content_type='application/json')
            self.assertEqual(r.status_code, 200, r.content)
        customer = ChatMessage.objects.filter(conversation=self.conv, sender_type='customer').count()
        admin = ChatMessage.objects.filter(conversation=self.conv, sender_type='admin').count()
        # 1:1 -- each send produced exactly one customer message and one bot reply
        self.assertEqual(customer, n)
        self.assertEqual(admin, n)

    def test_overlapping_polls_dedup_contract(self):
        """Two polls with the same cursor return the same bot message; the frontend
        id-based dedup (mirroring appendMessage) must render each exactly once."""
        c = Client()
        r = c.post('/chat/send/', data=json.dumps(
            {'conversation_id': self.conv.pk, 'message': 'hello'}),
            content_type='application/json')
        after = json.loads(r.content)['created_at']

        url = '/chat/poll/%d/?after=%s' % (self.conv.pk, quote(after, safe=''))
        p1 = json.loads(c.get(url).content)['messages']
        p2 = json.loads(c.get(url).content)['messages']

        # Both polls return the same set of admin (bot) message ids
        ids1 = [m['id'] for m in p1 if m['sender_type'] == 'admin']
        ids2 = [m['id'] for m in p2 if m['sender_type'] == 'admin']
        self.assertEqual(ids1, ids2)
        self.assertGreater(len(ids1), 0)

        # Mirror the frontend appendMessage dedup algorithm (id + customer-text).
        rendered = []
        seen_ids = set()
        seen_cust_texts = set()
        for m in p1 + p2:
            if m['id'] and m['id'] in seen_ids:
                continue
            if m['sender_type'] == 'customer' and m['message'] in seen_cust_texts:
                continue
            if m['id']:
                seen_ids.add(m['id'])
            if m['sender_type'] == 'customer':
                seen_cust_texts.add(m['message'])
            rendered.append(m)
        # Each distinct message id rendered exactly once.
        all_ids = [m['id'] for m in (p1 + p2) if m['id']]
        self.assertEqual(len(rendered), len(set(all_ids)))
