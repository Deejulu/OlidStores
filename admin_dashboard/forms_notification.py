from django import forms
from users.models_notification import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationForm(forms.ModelForm):
    """Form for creating and sending notifications from admin dashboard."""
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(role='customer'), 
        required=False, 
        empty_label='All Customers',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Notification
        fields = ['user', 'notification_type', 'title', 'message', 'action_url', 'is_important']
        widgets = {
            'notification_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Notification title'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Notification message'
            }),
            'action_url': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '/path/to/page/ (optional)'
            }),
            'is_important': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'notification_type': 'Type',
            'action_url': 'Action URL (optional)',
            'is_important': 'Mark as Important'
        }
        help_texts = {
            'user': 'Leave blank to send to all customers',
            'action_url': 'URL to navigate when notification is clicked (e.g., /shop/)',
        }
