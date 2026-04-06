from django import forms
from .models import Feedback

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Your feedback...'}),
        }

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

# Allow login with email or username
class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        UserModel = get_user_model()
        if username and password:
            try:
                user = UserModel.objects.get(email__iexact=username)
                username = user.username
            except UserModel.DoesNotExist:
                pass
            self.cleaned_data['username'] = username
        return super().clean()
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email


class ProfileEditForm(forms.Form):
    first_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    phone = forms.CharField(
        max_length=20, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +2348012345678'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Delivery address'})
    )
    avatar = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'd-none', 'accept': 'image/*', 'id': 'avatar-upload-input'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # Will validate uniqueness in the view (need to exclude current user)
        return email


class AddressForm(forms.ModelForm):
    class Meta:
        from .models import Address
        model = Address
        fields = ['full_name', 'phone', 'address_line', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Full name for delivery'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. +2348012345678'
            }),
            'address_line': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Street address, city, state'
            }),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ============ OTP Verification Forms ============

import re

class SignupStep1Form(forms.Form):
    """Step 1: Collect email and phone for OTP verification."""
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'example@email.com',
            'autofocus': True
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=False,  # Phone is optional, but one contact method is required
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '+234 801 234 5678'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return ''
        # Check proper email format
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise forms.ValidationError("Please enter a valid email (e.g., name@example.com)")
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email.lower()
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not phone:
            return ''  # Allow empty phone
        
        # Remove spaces, dashes, and brackets
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Accept Nigerian formats: +234..., 234..., 0...
        # Must be 10-14 digits after cleaning
        if cleaned.startswith('+'):
            cleaned_digits = cleaned[1:]
        else:
            cleaned_digits = cleaned
        
        if not cleaned_digits.isdigit():
            raise forms.ValidationError("Phone number can only contain digits, +, spaces, or dashes.")
        
        if len(cleaned_digits) < 10 or len(cleaned_digits) > 14:
            raise forms.ValidationError("Please enter a valid phone number (e.g., +234 801 234 5678 or 0801 234 5678)")
        
        from .otp_utils import normalize_phone_number
        normalized = normalize_phone_number(phone)
        if normalized and CustomUser.objects.filter(phone=normalized).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return normalized or None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        if not email and not phone:
            raise forms.ValidationError("Please provide either an email address or a phone number.")
        return cleaned_data


class OTPVerifyForm(forms.Form):
    """Form to enter OTP code."""
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center letter-spacing-wide',
            'placeholder': '000000',
            'maxlength': '6',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'autocomplete': 'one-time-code',
            'style': 'font-size: 1.5rem; letter-spacing: 0.5rem;'
        })
    )
    
    def clean_otp_code(self):
        code = self.cleaned_data.get('otp_code')
        if not code.isdigit():
            raise forms.ValidationError("OTP must contain only numbers.")
        return code


class SignupStep2Form(forms.Form):
    """Step 2: Complete registration after OTP verification."""
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Last name / Surname'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=False,  # Generated by system
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Auto-generated',
            'readonly': 'readonly',
            'style': 'background-color: #f3f4f6; cursor: not-allowed;'
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Create a password'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm password'
        })
    )
    
    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name or len(first_name.strip()) < 2:
            raise forms.ValidationError("Please enter your first name (at least 2 characters).")
        if not first_name.replace(' ', '').replace('-', '').isalpha():
            raise forms.ValidationError("First name should only contain letters.")
        return first_name.strip().title()
    
    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name or len(last_name.strip()) < 2:
            raise forms.ValidationError("Please enter your last name / surname (at least 2 characters).")
        if not last_name.replace(' ', '').replace('-', '').isalpha():
            raise forms.ValidationError("Last name should only contain letters.")
        return last_name.strip().title()
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("Passwords don't match.")
            if len(password1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters.")
        
        return cleaned_data
