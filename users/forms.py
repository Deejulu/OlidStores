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

class SignupForm(forms.Form):
    """Single-step signup: name, password, and security questions. No email/OTP."""
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'First name',
            'autofocus': True
        })
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Last name / Surname'
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
    security_question_1 = forms.ChoiceField(
        choices=[],
        required=True,
        label='Security Question 1',
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    security_answer_1 = forms.CharField(
        max_length=255,
        required=True,
        label='Answer',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Your answer'
        })
    )
    security_question_2 = forms.ChoiceField(
        choices=[],
        required=True,
        label='Security Question 2',
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    security_answer_2 = forms.CharField(
        max_length=255,
        required=True,
        label='Answer',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Your answer'
        })
    )
    security_question_3 = forms.ChoiceField(
        choices=[],
        required=True,
        label='Security Question 3',
        widget=forms.Select(attrs={'class': 'form-control form-control-lg'})
    )
    security_answer_3 = forms.CharField(
        max_length=255,
        required=True,
        label='Answer',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Your answer'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SecurityQuestion
        questions = SecurityQuestion.objects.all().order_by('question_key')
        choices = [('', '--- Select a question ---')] + [(q.id, q.question_text) for q in questions]
        self.fields['security_question_1'].choices = choices
        self.fields['security_question_2'].choices = choices
        self.fields['security_question_3'].choices = choices
    
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
        
        # Ensure security questions are unique
        q1 = cleaned_data.get('security_question_1')
        q2 = cleaned_data.get('security_question_2')
        q3 = cleaned_data.get('security_question_3')
        if q1 and q2 and q3:
            if len({q1, q2, q3}) != 3:
                raise forms.ValidationError("Please select 3 different security questions.")
        
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





class AccountRecoveryForm(forms.Form):
    """Form for recovering account using security questions."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your username',
            'autofocus': True
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import SecurityQuestion
        questions = SecurityQuestion.objects.all().order_by('question_key')
        for q in questions:
            self.fields[f'answer_{q.id}'] = forms.CharField(
                label=q.question_text,
                max_length=255,
                required=False,
                widget=forms.TextInput(attrs={
                    'class': 'form-control form-control-lg',
                    'placeholder': 'Your answer',
                    'data-question-id': q.id
                })
            )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise forms.ValidationError("Please enter your username.")
        return username.strip()
    
    def clean(self):
        cleaned_data = super().clean()
        from .models import SecurityQuestion, SecurityAnswer, CustomUser
        
        username = cleaned_data.get('username')
        if not username:
            return cleaned_data
        
        try:
            user = CustomUser.objects.get(username__iexact=username)
            security_answers = SecurityAnswer.objects.filter(user=user)
            
            if not security_answers.exists():
                raise forms.ValidationError("No security questions found for this account.")
            
            answers = {}
            for sa in security_answers:
                answer_key = f'answer_{sa.question.id}'
                provided = self.data.get(answer_key, '').strip().lower()
                answers[answer_key] = provided
                if not provided:
                    raise forms.ValidationError("Please answer all security questions.")
            
            cleaned_data['answers'] = answers
            cleaned_data['user'] = user
        except CustomUser.DoesNotExist:
            pass
        
        return cleaned_data
