"""
Signup Views - Single-step account creation with auto-generated username.
No email/OTP verification required.
"""
import secrets
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import make_password

from .models import CustomUser, SecurityQuestion, SecurityAnswer
from .forms import SignupForm, OTPVerifyForm, AccountRecoveryForm
from .username_utils import generate_unique_username_with_id


def signup(request):
    """
    Single-step signup: collect name, password, and security questions.
    Auto-generate username. No email/OTP required.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            raw_password = form.cleaned_data['password1']
            
            username, account_id = generate_unique_username_with_id(first_name, last_name)
            
            user = CustomUser.objects.create_user(
                username=username,
                password=raw_password,
                first_name=first_name,
                last_name=last_name,
                account_id=account_id,
                email_verified=True,
                phone_verified=True,
            )
            
            for i in range(1, 4):
                q_id = form.cleaned_data.get(f'security_question_{i}')
                answer = form.cleaned_data.get(f'security_answer_{i}')
                if q_id and answer:
                    try:
                        question = SecurityQuestion.objects.get(id=q_id)
                        SecurityAnswer.objects.create(
                            user=user,
                            question=question,
                            answer_hash=make_password(answer.strip().lower())
                        )
                    except SecurityQuestion.DoesNotExist:
                        pass
            
            request.session['credentials_username'] = user.username
            request.session['credentials_account_id'] = user.account_id
            request.session['credentials_password'] = raw_password
            
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('users:credentials_download')
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Signup form errors: {form.errors}")
    else:
        form = SignupForm()
    
    security_questions = SecurityQuestion.objects.all()
    
    return render(request, 'users/signup.html', {
        'form': form,
        'security_questions': security_questions,
    })





# ========== Existing User Verification ==========

def verify_existing_user(request):
    """
    Force existing users to verify their email/phone.
    Called when unverified user tries to access protected pages.
    """
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    user = request.user
    
    # Admin users are auto-verified
    if user.role == 'admin':
        user.email_verified = True
        user.phone_verified = True
        user.save()
        return redirect('admin_dashboard:dashboard_home')
    
    # If fully verified, redirect to dashboard
    if user.is_fully_verified:
        return redirect('users:dashboard')
    
    # Only email verification required (phone is optional, no OTP)
    needs_email = not user.email_verified
    
    return render(request, 'users/verify_existing_user.html', {
        'user': user,
        'needs_email': needs_email,
        'needs_phone': False  # Phone OTP disabled - phone is optional field only
    })


def send_existing_user_email_otp(request):
    """Send email OTP for existing user verification."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    user = request.user
    
    if user.email_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('users:verify_existing_user')
    
    # Create and send OTP
    otp = OTPVerification.create_otp(
        otp_type='email',
        email=user.email,
        user=user,
        expiry_minutes=settings.OTP_EXPIRY_MINUTES
    )
    
    sent, error_message = send_email_otp(user.email, otp.plaintext_code)
    if sent:
        request.session['existing_email_otp_id'] = otp.id
        messages.success(request, f"Verification code sent to {user.email}")
    else:
        error_text = "Failed to send verification code."
        if error_message and (settings.DEBUG or settings.OTP_DEBUG_MODE):
            error_text += f" ({error_message})"
        messages.error(request, error_text)
    
    return redirect('users:verify_existing_email')


def send_existing_user_phone_otp(request):
    """Send phone OTP for existing user verification."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    user = request.user
    
    if user.phone_verified:
        messages.info(request, "Your phone is already verified.")
        return redirect('users:verify_existing_user')
    
    if not user.phone:
        messages.warning(request, "Please update your phone number first.")
        return redirect('users:profile')
    
    # Create and send OTP
    otp = OTPVerification.create_otp(
        otp_type='phone',
        phone=user.phone,
        user=user,
        expiry_minutes=settings.OTP_EXPIRY_MINUTES
    )
    
    if send_sms_otp(user.phone, otp.plaintext_code):
        request.session['existing_phone_otp_id'] = otp.id
        messages.success(request, f"Verification code sent to {user.phone}")
    else:
        messages.error(request, "Failed to send verification code.")
    
    return redirect('users:verify_existing_phone')


def verify_existing_email(request):
    """Verify existing user's email."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    user = request.user
    otp_id = request.session.get('existing_email_otp_id')
    
    if user.email_verified:
        return redirect('users:dashboard')
    
    if not otp_id:
        return redirect('users:send_existing_user_email_otp')
    
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            try:
                otp = OTPVerification.objects.get(id=otp_id)
                success, message = otp.verify(form.cleaned_data['otp_code'])
                
                if success:
                    user.email_verified = True
                    user.phone_verified = True  # Phone always auto-verified (optional field, no OTP required)
                    user.save()
                    request.session.pop('existing_email_otp_id', None)
                    messages.success(request, "Email verified! Your account is now fully verified.")
                    return redirect('users:dashboard')
                else:
                    messages.error(request, message)
            except OTPVerification.DoesNotExist:
                messages.error(request, "Session expired. Please try again.")
                return redirect('users:send_existing_user_email_otp')
    else:
        form = OTPVerifyForm()
    
    return render(request, 'users/verify_otp.html', {
        'form': form,
        'verification_type': 'email',
        'target': user.email,
        'resend_url': 'users:send_existing_user_email_otp',
        'existing_user': True
    })


def verify_existing_phone(request):
    """Verify existing user's phone."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    user = request.user
    otp_id = request.session.get('existing_phone_otp_id')
    
    if user.phone_verified:
        return redirect('users:dashboard')
    
    if not user.phone:
        messages.warning(request, "Please add your phone number first.")
        return redirect('users:profile')
    
    if not otp_id:
        return redirect('users:send_existing_user_phone_otp')
    
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            try:
                otp = OTPVerification.objects.get(id=otp_id)
                success, message = otp.verify(form.cleaned_data['otp_code'])
                
                if success:
                    user.phone_verified = True
                    user.save()
                    request.session.pop('existing_phone_otp_id', None)
                    messages.success(request, "Phone verified! Your account is now fully verified.")
                    return redirect('users:dashboard')
                else:
                    messages.error(request, message)
            except OTPVerification.DoesNotExist:
                messages.error(request, "Session expired. Please try again.")
                return redirect('users:send_existing_user_phone_otp')
    else:
        form = OTPVerifyForm()
    
    return render(request, 'users/verify_otp.html', {
        'form': form,
        'verification_type': 'phone',
        'target': user.phone,
        'resend_url': 'users:send_existing_user_phone_otp',
        'existing_user': True
    })


def credentials_download(request):
    """One-time page showing account credentials after signup."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    username = request.session.get('credentials_username')
    account_id = request.session.get('credentials_account_id')
    password = request.session.get('credentials_password')
    
    if not username or not password:
        messages.error(request, "Credentials not available. Please complete signup.")
        return redirect('users:signup')
    
    # Get security questions for this user
    security_answers = SecurityAnswer.objects.filter(user=request.user).select_related('question')
    recovery_questions = [sa.question.question_text for sa in security_answers]
    
    response = render(request, 'users/credentials_download.html', {
        'username': username,
        'account_id': account_id,
        'password': password,
        'recovery_questions': recovery_questions,
    })
    
    # Prevent caching
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


def credentials_download_file(request):
    """Generate and download credentials as a text file."""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    username = request.session.get('credentials_username')
    account_id = request.session.get('credentials_account_id')
    password = request.session.get('credentials_password')
    
    if not username or not password:
        return redirect('users:signup')
    
    security_answers = SecurityAnswer.objects.filter(user=request.user).select_related('question')
    recovery_questions = [sa.question.question_text for sa in security_answers]
    
    content = f"""Olid Stores Account Credentials
============================
Username:      {username}
Account ID:    {account_id}
Password:      {password}

Account Recovery Questions:
"""
    for i, q in enumerate(recovery_questions, 1):
        content += f"{i}. {q}\n"
    
    content += """
============================
IMPORTANT: Keep this file secure and do not share it with anyone.
"""
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="credentials-{username}.txt"'
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    # Clear credentials from session after download
    for key in ['credentials_username', 'credentials_account_id', 'credentials_password']:
        request.session.pop(key, None)
    
    return response


def account_recovery(request):
	"""Recover account using username and security questions."""
	from .forms import AccountRecoveryForm

	if request.user.is_authenticated:
		return redirect('users:dashboard')

	if request.method == 'POST':
		form = AccountRecoveryForm(request.POST)
		if form.is_valid():
			username = form.cleaned_data['username']
			answers = form.cleaned_data['answers']

			try:
				user = CustomUser.objects.get(username__iexact=username)
				security_answers = SecurityAnswer.objects.filter(user=user).select_related('question')

				if not security_answers.exists():
					messages.error(request, "Account recovery is not set up for this account.")
					return redirect('users:account_recovery')

			except CustomUser.DoesNotExist:
				messages.error(request, "The information provided is incorrect. Please try again.")
				return redirect('users:account_recovery')

			# Check all answers
			all_correct = True
			for sa in security_answers:
				answer_key = f'answer_{sa.question.id}'
				provided = answers.get(answer_key, '').strip().lower()
				from django.contrib.auth.hashers import check_password
				if not check_password(provided, sa.answer_hash):
					all_correct = False
					break

			if all_correct:
				# Generate a temporary password and show it
				temp_password = secrets.token_urlsafe(12)
				user.set_password(temp_password)
				user.save()

				# Store temporary password in session for one-time display
				request.session['recovery_temp_password'] = temp_password
				request.session['recovery_username'] = user.username

				messages.success(request, "Account recovered successfully! Please log in with your temporary password.")
				return redirect('users:recovery_success')
			else:
				messages.error(request, "The information provided is incorrect. Please try again.")
	else:
		form = AccountRecoveryForm()

	return render(request, 'users/account_recovery.html', {
		'form': form,
	})


def recovery_success(request):
    """Show temporary password after successful recovery."""
    temp_password = request.session.pop('recovery_temp_password', None)
    username = request.session.pop('recovery_username', None)
    
    if not temp_password or not username:
        return redirect('users:login')
    
    response = render(request, 'users/recovery_success.html', {
        'username': username,
        'temp_password': temp_password,
    })
    
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response
