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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if order has successful PAYSTACK payment (not manual receipt)
        if self.instance and self.instance.pk:
            from orders.models import PaymentTransaction
            has_paystack_payment = PaymentTransaction.objects.filter(
                order=self.instance,
                status='success'
            ).exists()
            
            # Only protect orders with Paystack payments
            # Manual receipt payments can be freely modified
            if has_paystack_payment:
                self.fields['status'].help_text = '⚠️ Status locked - Paystack payment confirmed'
                # Only allow forward progression (cannot go back to Pending)
                current_status = self.instance.status
                if current_status in ['Processing', 'Shipped', 'Delivered']:
                    status_choices = list(Order.STATUS_CHOICES)
                    # Remove 'Pending' option
                    status_choices = [choice for choice in status_choices if choice[0] != 'Pending']
                    self.fields['status'].choices = status_choices
            elif self.instance.receipt:
                # Manual payment - show help text
                self.fields['status'].help_text = '📄 Manual payment receipt uploaded - verify before updating'
    
    def clean_status(self):
        status = self.cleaned_data.get('status')
        
        # Additional server-side validation
        if self.instance and self.instance.pk:
            from orders.models import PaymentTransaction
            has_paystack_payment = PaymentTransaction.objects.filter(
                order=self.instance,
                status='success'
            ).exists()
            
            # Only restrict Paystack payments, not manual receipts
            if has_paystack_payment:
                # Cannot change status back to Pending if Paystack payment is successful
                if status == 'Pending' and self.instance.status != 'Pending':
                    raise forms.ValidationError(
                        'Cannot change order back to Pending - Paystack payment confirmed.'
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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
