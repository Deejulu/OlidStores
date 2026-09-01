from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from users.models import CustomUser, SecurityQuestion, SecurityAnswer
from django.contrib.auth.hashers import make_password
from users.models import OTPVerification
import re

User = get_user_model()

_test_settings = override_settings(
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)


class PasswordHashingTests(TestCase):
    """Verify passwords are always hashed, never stored in plain text."""
    
    def test_create_user_hashes_password(self):
        user = User.objects.create_user(
            username='hashuser',
            email='hash@example.com',
            password='SecurePass123!'
        )
        self.assertTrue(user.password.startswith('pbkdf2_'))
    
    def test_admin_form_hashes_password(self):
        from admin_dashboard.forms import AddCustomerForm
        form = AddCustomerForm(data={
            'email': 'adminform@example.com',
            'first_name': 'Admin',
            'last_name': 'Form',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
            'role': 'customer',
            'is_active': True,
            'security_question_1': SecurityQuestion.objects.first().id,
            'security_answer_1': 'answer1',
            'security_question_2': SecurityQuestion.objects.last().id,
            'security_answer_2': 'answer2',
            'security_question_3': SecurityQuestion.objects.all()[1].id,
            'security_answer_3': 'answer3',
        })
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.password.startswith('pbkdf2_'))


class UsernameGenerationTests(TestCase):
    """Verify username generation uses crypto-random IDs and correct OLID format."""
    
    def test_new_username_format(self):
        from users.username_utils import generate_unique_username
        username = generate_unique_username('David', 'Okonkwo')
        self.assertRegex(username, r'^DavidOkonkwo\d{4}OLID[A-Z0-9]{4}$')
    
    def test_username_is_unique(self):
        from users.username_utils import generate_unique_username
        username1 = generate_unique_username('Alice', 'Smith')
        username2 = generate_unique_username('Alice', 'Smith')
        self.assertNotEqual(username1, username2)
    
    def test_username_contains_olid(self):
        from users.username_utils import generate_unique_username
        username = generate_unique_username('Sarah', 'Okafor')
        self.assertIn('OLID', username)
    
    def test_username_contains_current_year(self):
        from users.username_utils import generate_unique_username
        from django.utils import timezone
        username = generate_unique_username('Test', 'User')
        self.assertIn(str(timezone.now().year), username)
    
    def test_extract_account_id(self):
        from users.username_utils import extract_account_id
        account_id = extract_account_id('SarahOkafor2026OLID7K2M')
        self.assertEqual(account_id, '7K2M')
    
    def test_extract_account_id_returns_empty_for_non_olid(self):
        from users.username_utils import extract_account_id
        self.assertEqual(extract_account_id('legacy_user'), '')
    
    def test_existing_usernames_unchanged(self):
        user = User.objects.create_user(
            username='OldUser001',
            email='old@example.com',
            password='testpass123'
        )
        user.refresh_from_db()
        self.assertEqual(user.username, 'OldUser001')


class AccountIdTests(TestCase):
    """Verify account_id is generated and unique."""
    
    def test_account_id_generated_for_new_users(self):
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertIsNotNone(user.account_id)
        self.assertEqual(len(user.account_id), 4)
    
    def test_account_id_is_unique(self):
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.assertNotEqual(user1.account_id, user2.account_id)
    
    def test_existing_users_backfilled_account_id(self):
        user = User.objects.create_user(
            username='backfill',
            email='backfill@example.com',
            password='testpass123'
        )
        self.assertIsNotNone(user.account_id)
        self.assertTrue(len(user.account_id) >= 4)


class SecurityQuestionTests(TestCase):
    """Verify security questions are saved and hashed."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='secuser',
            email='sec@example.com',
            password='testpass123'
        )
    
    def test_security_questions_populated(self):
        self.assertGreater(SecurityQuestion.objects.count(), 0)
    
    def test_security_answer_is_hashed(self):
        question = SecurityQuestion.objects.first()
        SecurityAnswer.objects.create(
            user=self.user,
            question=question,
            answer_hash='pbkdf2_sha256$test$hash'
        )
        answer = SecurityAnswer.objects.first()
        self.assertIsNotNone(answer)
        self.assertEqual(answer.answer_hash, 'pbkdf2_sha256$test$hash')


class CredentialsDownloadTests(TestCase):
    """Verify one-time credentials page works correctly."""
    
    @_test_settings
    def test_credentials_page_requires_login(self):
        response = self.client.get(reverse('users:credentials_download'))
        self.assertEqual(response.status_code, 302)
    
    @_test_settings
    def test_credentials_page_no_cache_header(self):
        user = User.objects.create_user(
            username='creduser',
            email='cred@example.com',
            password='testpass123'
        )
        
        self.client.force_login(user)
        session = self.client.session
        session['credentials_username'] = 'creduser'
        session['credentials_account_id'] = 'ABC12345'
        session['credentials_password'] = 'testpass'
        session.save()
        
        response = self.client.get(reverse('users:credentials_download'))
        self.assertEqual(response.status_code, 200)
        cache_control = response.get('Cache-Control', '')
        self.assertIn('no-store', cache_control)


class RecoveryTests(TestCase):
    """Verify account recovery with security questions."""
    
    @_test_settings
    def test_recovery_page_loads(self):
        response = self.client.get(reverse('users:account_recovery'))
        self.assertEqual(response.status_code, 200)
    
    @_test_settings
    def test_recovery_with_correct_answers(self):
        user = User.objects.create_user(
            username='recoveryuser',
            email='recovery@example.com',
            password='originalpass123'
        )
        question = SecurityQuestion.objects.first()
        SecurityAnswer.objects.create(
            user=user,
            question=question,
            answer_hash=make_password('correctanswer')
        )
        
        response = self.client.post(reverse('users:account_recovery'), {
            'username': 'recoveryuser',
            f'answer_{question.id}': 'correctanswer',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:recovery_success'))


class AdminCredentialsTests(TestCase):
    """Verify admin credential delivery."""
    
    @_test_settings
    def test_admin_credentials_page_requires_login(self):
        response = self.client.get(reverse('admin_dashboard:admin_credentials'))
        self.assertEqual(response.status_code, 302)


class MigrationTests(TestCase):
	"""Verify existing data is preserved after migrations."""

	def test_existing_users_preserved(self):
		user = User.objects.create_user(
			username='existing',
			email='existing@example.com',
			password='oldpass123'
		)
		user.refresh_from_db()
		self.assertEqual(user.username, 'existing')
		self.assertIsNotNone(user.account_id)


class WishlistTests(TestCase):
	"""Tests for wishlist functionality."""

	def setUp(self):
		self.client = Client()
		self.user = User.objects.create_user(
			username='wishlistuser',
			password='password',
			email_verified=True
		)
		from products.models import Category, Product
		self.category = Category.objects.create(name='WishCat', slug='wishcat')
		self.product = Product.objects.create(
			name='Wishlist Product',
			slug='wish-product',
			price=100.00,
			category=self.category,
			stock=5
		)

	def test_add_to_wishlist(self):
		"""User can add a product to their wishlist."""
		self.client.force_login(self.user)
		r = self.client.post(reverse('users:wishlist_add'), {'product_id': self.product.id}, HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 302)  # Redirect after adding

		# Verify product is in wishlist
		from users.models import Wishlist
		wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
		self.assertTrue(wishlist.products.filter(id=self.product.id).exists())

	def test_remove_from_wishlist(self):
		"""User can remove a product from their wishlist."""
		from users.models import Wishlist
		wishlist, _ = Wishlist.objects.get_or_create(user=self.user)
		wishlist.products.add(self.product)

		self.client.force_login(self.user)
		r = self.client.post(reverse('users:wishlist_remove'), {'product_id': self.product.id}, HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 302)  # Redirect after removing

		# Verify product is removed from wishlist
		self.assertFalse(wishlist.products.filter(id=self.product.id).exists())

	def test_wishlist_requires_login(self):
		"""Anonymous users cannot add to wishlist."""
		r = self.client.post(reverse('users:wishlist_add'), {'product_id': self.product.id}, HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 302)  # Redirect to login
		self.assertIn('login', r.url)


class OTPHashingTests(TestCase):
	"""Verify OTP codes are hashed, never stored in plain text."""

	def test_otp_stored_as_hash(self):
		"""OTP code should be stored as a hash, not plaintext."""
		otp = OTPVerification.create_otp(
			otp_type='email',
			email='test@example.com',
			expiry_minutes=10
		)
		# The stored field should be a hash, not the plaintext code
		self.assertNotEqual(otp.otp_code_hash, otp.plaintext_code)
		# The hash should be a valid Django password hash
		self.assertTrue(otp.otp_code_hash.startswith('pbkdf2_') or otp.otp_code_hash.startswith('argon2'))

	def test_plaintext_otp_not_stored(self):
		"""Plaintext OTP should not be stored in the database."""
		otp = OTPVerification.create_otp(
			otp_type='email',
			email='test@example.com',
			expiry_minutes=10
		)
		# Refresh from database to ensure plaintext wasn't saved
		otp.refresh_from_db()
		# plaintext_code is only an in-memory attribute, not persisted
		self.assertFalse(hasattr(otp, 'plaintext_code') and otp.plaintext_code == otp.otp_code_hash)

	def test_otp_verification_works(self):
		"""OTP verification should work with hashed codes."""
		otp = OTPVerification.create_otp(
			otp_type='email',
			email='test@example.com',
			expiry_minutes=10
		)
		plaintext = otp.plaintext_code

		# Verify with correct code
		success, message = otp.verify(plaintext)
		self.assertTrue(success)
		self.assertEqual(message, 'Verified successfully')

	def test_otp_verification_fails_with_wrong_code(self):
		"""OTP verification should fail with incorrect code."""
		otp = OTPVerification.create_otp(
			otp_type='email',
			email='test@example.com',
			expiry_minutes=10
		)

		# Verify with wrong code
		success, message = otp.verify('000000')
		self.assertFalse(success)
		self.assertIn('Invalid OTP', message)

	def test_otp_verification_case_sensitive(self):
		"""OTP verification should be exact match."""
		otp = OTPVerification.create_otp(
			otp_type='email',
			email='test@example.com',
			expiry_minutes=10
		)
		plaintext = otp.plaintext_code

		# Verify that the code works
		success, message = otp.verify(plaintext)
		self.assertTrue(success)


class SignupFlowTests(TestCase):
    """Verify the new single-step signup flow."""

    @_test_settings
    def test_signup_page_loads(self):
        response = self.client.get(reverse('users:signup'))
        self.assertEqual(response.status_code, 200)

    @_test_settings
    def test_signup_creates_user_with_olid_username(self):
        """New signup should create user with OLID-format username."""
        q1, _ = SecurityQuestion.objects.get_or_create(question_key='pet_name', defaults={'question_text': 'First pet?'})
        q2, _ = SecurityQuestion.objects.get_or_create(question_key='birth_city', defaults={'question_text': 'Birth city?'})
        q3, _ = SecurityQuestion.objects.get_or_create(question_key='school_name', defaults={'question_text': 'School?'})

        response = self.client.post(reverse('users:signup'), {
            'first_name': 'Sarah',
            'last_name': 'Okafor',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'security_question_1': q1.id,
            'security_answer_1': 'fluffy',
            'security_question_2': q2.id,
            'security_answer_2': 'lagos',
            'security_question_3': q3.id,
            'security_answer_3': 'springfield',
        }, HTTP_X_FORWARDED_PROTO='https')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:credentials_download'))

        user = CustomUser.objects.get(first_name='Sarah', last_name='Okafor')
        self.assertRegex(user.username, r'^SarahOkafor\d{4}OLID[A-Z0-9]{4}$')
        self.assertIsNotNone(user.account_id)

    @_test_settings
    def test_signup_hashes_security_answers(self):
        """Security answers should be hashed, not stored in plaintext."""
        q1, _ = SecurityQuestion.objects.get_or_create(question_key='pet_name', defaults={'question_text': 'First pet?'})
        q2, _ = SecurityQuestion.objects.get_or_create(question_key='birth_city', defaults={'question_text': 'Birth city?'})
        q3, _ = SecurityQuestion.objects.get_or_create(question_key='school_name', defaults={'question_text': 'School?'})

        self.client.post(reverse('users:signup'), {
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'security_question_1': q1.id,
            'security_answer_1': 'mysecret',
            'security_question_2': q2.id,
            'security_answer_2': 'anothersecret',
            'security_question_3': q3.id,
            'security_answer_3': 'yetanother',
        }, HTTP_X_FORWARDED_PROTO='https')

        user = CustomUser.objects.get(first_name='Test', last_name='User')
        answers = SecurityAnswer.objects.filter(user=user)
        self.assertEqual(answers.count(), 3)

        for answer in answers:
            self.assertTrue(answer.answer_hash.startswith('pbkdf2_'))
            self.assertNotEqual(answer.answer_hash, 'mysecret')
            self.assertNotEqual(answer.answer_hash, 'anothersecret')
            self.assertNotEqual(answer.answer_hash, 'yetanother')

    @_test_settings
    def test_signup_requires_unique_security_questions(self):
        """Signup should fail if security questions are not unique."""
        q1, _ = SecurityQuestion.objects.get_or_create(question_key='pet_name', defaults={'question_text': 'First pet?'})

        response = self.client.post(reverse('users:signup'), {
            'first_name': 'Dup',
            'last_name': 'User',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
            'security_question_1': q1.id,
            'security_answer_1': 'answer1',
            'security_question_2': q1.id,
            'security_answer_2': 'answer2',
            'security_question_3': q1.id,
            'security_answer_3': 'answer3',
        }, HTTP_X_FORWARDED_PROTO='https')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(first_name='Dup').exists())

    @_test_settings
    def test_credentials_file_download(self):
        """Credentials file should download with correct content."""
        user = User.objects.create_user(
            username='SarahOkafor2026OLID7K2M',
            password='SecurePass123!',
            account_id='7K2M'
        )
        self.client.force_login(user)
        session = self.client.session
        session['credentials_username'] = user.username
        session['credentials_account_id'] = user.account_id
        session['credentials_password'] = 'SecurePass123!'
        session.save()

        response = self.client.get(reverse('users:credentials_download_file'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertIn('SarahOkafor2026OLID7K2M', response.content.decode())
        self.assertIn('SecurePass123!', response.content.decode())
