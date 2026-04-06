"""
OTP Verification Views - Email Only
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings

from .models import OTPVerification, CustomUser
from .forms import SignupStep1Form, OTPVerifyForm, SignupStep2Form
from .otp_utils import send_email_otp, send_sms_otp


def signup_step1(request):
    """
    Step 1: Collect email and/or phone, send OTP via email or phone.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = SignupStep1Form(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email', '')
            phone = form.cleaned_data.get('phone', '')
            
            # Determine OTP delivery method
            if email:
                otp = OTPVerification.create_otp(
                    otp_type='email',
                    email=email,
                    expiry_minutes=settings.OTP_EXPIRY_MINUTES
                )
                sent = send_email_otp(email, otp.otp_code)
                method = 'email'
                session_key = 'email_otp_id'
                redirect_url = 'users:signup_verify_email'
                message_text = 'Verification code sent to your email!'
            else:
                otp = OTPVerification.create_otp(
                    otp_type='phone',
                    phone=phone,
                    expiry_minutes=settings.OTP_EXPIRY_MINUTES
                )
                sent = send_sms_otp(phone, otp.otp_code)
                method = 'phone'
                session_key = 'phone_otp_id'
                redirect_url = 'users:signup_verify_phone'
                message_text = 'Verification code sent to your phone!'
            
            if not sent:
                messages.error(request, "Failed to send verification code. Please try again.")
                return render(request, 'users/signup_step1.html', {'form': form})
            
            request.session['signup_email'] = email
            request.session['signup_phone'] = phone
            request.session[session_key] = otp.id
            request.session['signup_method'] = method
            request.session['email_verified'] = False
            request.session['phone_verified'] = False
            
            messages.success(request, message_text)
            return redirect(redirect_url)
    else:
        form = SignupStep1Form()
    
    return render(request, 'users/signup_step1.html', {'form': form})


def signup_verify_email(request):
    """
    Step 2: Verify email OTP, then go to account creation.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    email = request.session.get('signup_email')
    email_otp_id = request.session.get('email_otp_id')
    
    if not email or not email_otp_id:
        messages.error(request, "Session expired. Please start over.")
        return redirect('users:signup')
    
    if request.session.get('email_verified'):
        return redirect('users:signup_complete')
    
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['otp_code']
            
            try:
                otp = OTPVerification.objects.get(id=email_otp_id)
                success, message = otp.verify(code)
                
                if success:
                    request.session['email_verified'] = True
                    messages.success(request, "Email verified successfully!")
                    return redirect('users:signup_complete')
                else:
                    messages.error(request, message)
            except OTPVerification.DoesNotExist:
                messages.error(request, "Invalid verification session.")
                return redirect('users:signup')
    else:
        form = OTPVerifyForm()
    
    return render(request, 'users/verify_otp.html', {
        'form': form,
        'verification_type': 'email',
        'target': email,
        'resend_url': 'users:resend_email_otp'
    })


def signup_verify_phone(request):
    """
    Step 2: Verify phone OTP, then go to account creation.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    phone = request.session.get('signup_phone')
    phone_otp_id = request.session.get('phone_otp_id')
    
    if not phone or not phone_otp_id:
        messages.error(request, "Session expired. Please start over.")
        return redirect('users:signup')
    
    if request.session.get('phone_verified'):
        return redirect('users:signup_complete')
    
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['otp_code']
            
            try:
                otp = OTPVerification.objects.get(id=phone_otp_id)
                success, message = otp.verify(code)
                
                if success:
                    request.session['phone_verified'] = True
                    messages.success(request, "Phone verified successfully!")
                    return redirect('users:signup_complete')
                else:
                    messages.error(request, message)
            except OTPVerification.DoesNotExist:
                messages.error(request, "Invalid verification session.")
                return redirect('users:signup')
    else:
        form = OTPVerifyForm()
    
    return render(request, 'users/verify_otp.html', {
        'form': form,
        'verification_type': 'phone',
        'target': phone,
        'resend_url': 'users:resend_phone_otp'
    })


def generate_username(first_name, last_name):
    """Generate a unique username from first name + last name + customer ID."""
    import re
    # Clean names - only letters
    first = re.sub(r'[^a-zA-Z]', '', first_name)
    last = re.sub(r'[^a-zA-Z]', '', last_name)
    
    # Get current user count for ID
    user_count = CustomUser.objects.count() + 1
    
    # Format: FirstLast + 3-digit ID (e.g., JimOkonkwo001)
    base_username = f"{first}{last}{str(user_count).zfill(3)}"
    
    # Ensure uniqueness
    username = base_username
    counter = 1
    while CustomUser.objects.filter(username__iexact=username).exists():
        username = f"{first}{last}{str(user_count + counter).zfill(3)}"
        counter += 1
    
    return username


def signup_complete(request):
    """
    Step 3: Complete registration with username and password.
    """
    if request.user.is_authenticated:
        return redirect('core:home')
    
    email = request.session.get('signup_email', '')
    phone = request.session.get('signup_phone', '')
    email_verified = request.session.get('email_verified', False)
    phone_verified = request.session.get('phone_verified', False)
    
    if not email and not phone:
        messages.error(request, "Session expired. Please start over.")
        return redirect('users:signup')
    
    if not email_verified and not phone_verified:
        messages.error(request, "Please verify your contact method first.")
        return redirect('users:signup')
    
    if request.method == 'POST':
        form = SignupStep2Form(request.POST)
        if form.is_valid():
            username = generate_username(
                form.cleaned_data['first_name'],
                form.cleaned_data['last_name']
            )
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=form.cleaned_data['password1'],
                phone=phone,
                email_verified=email_verified,
                phone_verified=phone_verified,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )
            
            for key in ['signup_email', 'signup_phone', 'email_otp_id', 'phone_otp_id', 'email_verified', 'phone_verified', 'signup_method']:
                request.session.pop(key, None)
            
            login(request, user)
            messages.success(request, f"Welcome to E-Stores! Your username is: {user.username}")
            return redirect('core:home')
    else:
        form = SignupStep2Form()
    
    next_user_id = CustomUser.objects.count() + 1
    
    return render(request, 'users/signup_complete.html', {
        'form': form,
        'email': email,
        'phone': phone,
        'next_user_id': next_user_id
    })


@require_http_methods(["POST"])
def resend_email_otp(request):
    """Resend email OTP."""
    email = request.session.get('signup_email')
    
    if not email:
        return JsonResponse({'success': False, 'message': 'Session expired.'})
    
    # Create new OTP
    otp = OTPVerification.create_otp(
        otp_type='email',
        email=email,
        expiry_minutes=settings.OTP_EXPIRY_MINUTES
    )
    request.session['email_otp_id'] = otp.id
    
    # Send OTP
    if send_email_otp(email, otp.otp_code):
        return JsonResponse({'success': True, 'message': 'New code sent to your email.'})
    else:
        return JsonResponse({'success': False, 'message': 'Failed to send code.'})


@require_http_methods(["POST"])
def resend_phone_otp(request):
    """Resend phone OTP."""
    phone = request.session.get('signup_phone')
    
    if not phone:
        return JsonResponse({'success': False, 'message': 'Session expired.'})
    
    # Create new OTP
    otp = OTPVerification.create_otp(
        otp_type='phone',
        phone=phone,
        expiry_minutes=settings.OTP_EXPIRY_MINUTES
    )
    request.session['phone_otp_id'] = otp.id
    
    # Send OTP
    if send_sms_otp(phone, otp.otp_code):
        return JsonResponse({'success': True, 'message': 'New code sent to your phone.'})
    else:
        return JsonResponse({'success': False, 'message': 'Failed to send code.'})


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
    
    # Determine what needs verification
    needs_email = not user.email_verified
    needs_phone = not user.phone_verified and user.phone
    
    return render(request, 'users/verify_existing_user.html', {
        'user': user,
        'needs_email': needs_email,
        'needs_phone': needs_phone
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
    
    if send_email_otp(user.email, otp.otp_code):
        request.session['existing_email_otp_id'] = otp.id
        messages.success(request, f"Verification code sent to {user.email}")
    else:
        messages.error(request, "Failed to send verification code.")
    
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
    
    if send_sms_otp(user.phone, otp.otp_code):
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
                    user.phone_verified = True  # Auto-verify phone since we skip it
                    user.save()
                    request.session.pop('existing_email_otp_id', None)
                    messages.success(request, "Email verified! Your account is now verified.")
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
