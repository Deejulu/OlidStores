from django import forms
from users.models_notification import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=User.objects.filter(role='customer'), required=False, empty_label='All Customers')
    class Meta:
        model = Notification
        fields = ['user', 'title', 'message', 'is_important']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_important': forms.CheckboxInput(),
        }
