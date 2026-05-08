from django import forms
from products.models import Category
from orders.models import Order
from django.contrib.auth import get_user_model

User = get_user_model()

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_editable']

class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status', 'notes', 'delivery_fee']

    # Valid status transitions: which statuses can follow the current one
    VALID_TRANSITIONS = {
        'Pending':     ['Processing', 'Cancelled'],
        'Processing':  ['Shipped', 'Cancelled'],
        'Shipped':     ['Delivered', 'Cancelled'],
        'Delivered':   ['Completed'],
        'Completed':   [],
        'Cancelled':   [],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show contextual help text and restrict choices to valid next statuses
        if self.instance and self.instance.pk:
            current = self.instance.status
            allowed = self.VALID_TRANSITIONS.get(current, [])
            # Build choices: keep current status + allowed next statuses
            valid_values = set([current] + allowed)
            self.fields['status'].choices = [
                choice for choice in Order.STATUS_CHOICES if choice[0] in valid_values
            ]
            from orders.models import PaymentTransaction
            if PaymentTransaction.objects.filter(order=self.instance, status='success').exists():
                self.fields['status'].help_text = '⚠️ Paystack payment confirmed — only forward transitions allowed'
            elif self.instance.receipt:
                self.fields['status'].help_text = '📄 Manual payment receipt uploaded — verify before updating'

    def clean_status(self):
        status = self.cleaned_data.get('status')

        if self.instance and self.instance.pk:
            current = self.instance.status
            if status != current:
                allowed = self.VALID_TRANSITIONS.get(current, [])
                if status not in allowed:
                    allowed_str = ', '.join(allowed) if allowed else 'none'
                    raise forms.ValidationError(
                        f'Cannot change status from "{current}" to "{status}". '
                        f'Allowed next statuses: {allowed_str}.'
                    )

            from orders.models import PaymentTransaction
            has_paystack_payment = PaymentTransaction.objects.filter(
                order=self.instance,
                status='success'
            ).exists()
            if has_paystack_payment and status == 'Pending':
                raise forms.ValidationError(
                    'Cannot change order back to Pending — Paystack payment confirmed.'
                )

        return status

    def save(self, commit=True):
        order = super().save(commit=False)
        # set fulfillment timestamps when status transitions occur
        from django.utils import timezone
        if order.status == 'Shipped' and not order.shipped_at:
            order.shipped_at = timezone.now()
        if order.status in ('Delivered', 'Completed') and not order.delivered_at:
            order.delivered_at = timezone.now()
        if commit:
            order.save()
        return order

class CustomerForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active', 'role']

class AddCustomerForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        help_text='Minimum 8 characters'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match')
        return password_confirm
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long')
        return password
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Validate that email is not a disposable/temporary email
            disposable_domains = {
                'tempmail.com', 'temp-mail.org', 'guerrillamail.com', 'mailinator.com',
                '10minutemail.com', 'throwaway.email', 'yopmail.com', 'trashmail.com',
                'fake-mail.com', 'tempemail.com', 'maildrop.cc', 'temp-mail.io',
                'tmail.com', 'fakeinbox.com', 'minutemail.com', 'sharklasers.com',
            }
            
            domain = email.split('@')[1].lower() if '@' in email else ''
            if domain in disposable_domains:
                raise forms.ValidationError(
                    f'"{domain}" is a temporary/disposable email provider. '
                    'Please use a real email address.'
                )
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError('This email is already registered.')
        
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
