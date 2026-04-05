from django import forms
from core.models import SiteContent


class SiteContentForm(forms.ModelForm):
    """Form for editing SiteContent records. Fields are shown/hidden based on the content key."""
    
    class Meta:
        model = SiteContent
        fields = [
            'title', 'content', 'announcement_text', 
            'announcement_bar_item1', 'announcement_bar_item2', 'announcement_bar_item3',
            'background_style', 'background_video',
            'phone', 'email', 'social_links',
            'delivery_fee_24h', 'delivery_fee_2d', 'bank_name', 'account_name', 'account_number',
            # New site settings fields
            'site_name', 'site_tagline', 'site_logo', 'favicon', 'footer_text',
            'store_address', 'business_hours',
            # Individual social fields
            'twitter_handle', 'instagram_handle', 'facebook_handle', 'whatsapp_number',
            'tiktok_handle', 'youtube_handle',
            # Shipping/policies
            'free_shipping_threshold', 'return_policy_days',
            # SEO
            'meta_description', 'meta_keywords',
        ]
        labels = {
            'title': 'Section Title',
            'content': 'Main Content',
            'announcement_text': 'Top Banner Announcement',
            'announcement_bar_item1': 'Announcement Item 1',
            'announcement_bar_item2': 'Announcement Item 2',
            'announcement_bar_item3': 'Announcement Item 3',
            'background_style': 'Background Style',
            'background_video': 'Background Video File',
            'phone': 'Contact Phone',
            'email': 'Contact Email',
            'social_links': 'Social Media Links',
            'delivery_fee_24h': '24-hour Delivery Fee',
            'delivery_fee_2d': '2-day Delivery Fee',
            'bank_name': 'Bank Name',
            'account_name': 'Account Holder Name',
            'account_number': 'Account Number',
            # Site settings
            'site_name': 'Site Name',
            'site_tagline': 'Tagline / Slogan',
            'site_logo': 'Site Logo',
            'favicon': 'Favicon',
            'footer_text': 'Footer Text',
            'store_address': 'Store Address',
            'business_hours': 'Business Hours',
            # Social
            'twitter_handle': 'Twitter',
            'instagram_handle': 'Instagram',
            'facebook_handle': 'Facebook',
            'whatsapp_number': 'WhatsApp',
            'tiktok_handle': 'TikTok',
            'youtube_handle': 'YouTube',
            # Shipping
            'free_shipping_threshold': 'Free Shipping Threshold',
            'return_policy_days': 'Return Policy (Days)',
            # SEO
            'meta_description': 'Meta Description',
            'meta_keywords': 'Meta Keywords',
        }
        help_texts = {
            'announcement_text': 'Text shown in the top banner across all pages (e.g. "Free shipping on orders over ₦15,000 | Use code DFLOW10 for 10% off")',
            'announcement_bar_item1': 'First rotating message (e.g. "Free shipping on orders over ₦15,000")',
            'announcement_bar_item2': 'Second rotating message (e.g. "Use code OLID10 for 10% off")',
            'announcement_bar_item3': 'Third rotating message (e.g. "Secure checkout guaranteed")',
            'background_style': 'Choose the background style for the homepage banner',
            'background_video': 'Upload a video file (MP4) for video background option',
            'bank_name': 'Bank name for manual transfer payments (e.g. GTBank, Access Bank)',
            'account_name': 'Account holder name shown to customers',
            'account_number': 'Account number customers will transfer money to',
            'site_name': 'Your store name (shown in header, emails, etc.)',
            'site_tagline': 'A short tagline or slogan',
            'site_logo': 'Your store logo (recommended: transparent PNG)',
            'favicon': 'Browser tab icon (32x32 or 64x64)',
            'footer_text': 'Custom text for the footer (copyright, legal info)',
            'store_address': 'Your physical address for contact page',
            'business_hours': 'e.g. Mon-Fri: 9AM-6PM, Sat: 10AM-4PM',
            'twitter_handle': 'e.g. @yourhandle or full URL',
            'instagram_handle': 'e.g. yourhandle or full URL',
            'facebook_handle': 'e.g. facebook.com/yourpage or just the page name',
            'whatsapp_number': 'e.g. +2348012345678',
            'tiktok_handle': 'e.g. @yourhandle or full URL',
            'youtube_handle': 'Full YouTube channel URL',
            'free_shipping_threshold': 'Orders above this amount get free shipping (0 = disabled)',
            'return_policy_days': 'How many days customers have to return items',
            'meta_description': 'SEO description (150-160 chars recommended)',
            'meta_keywords': 'Comma-separated keywords for SEO',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)
        key = None
        if instance:
            key = getattr(instance, 'key', None)
        elif 'initial' in kwargs:
            key = kwargs['initial'].get('key')

        # Fields to conditionally show/hide
        contact_fields = ['phone', 'email', 'social_links']
        checkout_fields = ['delivery_fee_24h', 'delivery_fee_2d', 'bank_name', 'account_name', 'account_number']
        banner_fields = ['background_style', 'background_video', 'announcement_text', 'announcement_bar_item1', 'announcement_bar_item2', 'announcement_bar_item3']
        site_settings_fields = ['site_name', 'site_tagline', 'site_logo', 'favicon', 'footer_text', 
                                'store_address', 'business_hours', 'free_shipping_threshold', 'return_policy_days']
        social_fields = ['twitter_handle', 'instagram_handle', 'facebook_handle', 'whatsapp_number', 'tiktok_handle', 'youtube_handle']
        seo_fields = ['meta_description', 'meta_keywords']
        
        # Remove fields not applicable to this section
        if key != 'checkout':
            for f in checkout_fields:
                self.fields.pop(f, None)
        
        if key != 'homepage_banner':
            for f in banner_fields:
                self.fields.pop(f, None)
        
        if key not in ['contact', 'site_settings']:
            for f in social_fields:
                self.fields.pop(f, None)
        
        if key != 'site_settings':
            for f in site_settings_fields:
                self.fields.pop(f, None)
            for f in seo_fields:
                self.fields.pop(f, None)
        
        # Section-specific configurations
        if key == 'contact':
            self.fields['title'].label = 'Contact Page Title'
            self.fields['content'].label = 'Contact Page Content'
            self.fields['content'].help_text = 'This text appears at the top of the Contact page.'
            # Keep phone, email, social fields visible for contact
            # Add social input fields from instance.social dict
            if instance and hasattr(instance, 'social') and instance.social:
                soc = instance.social if isinstance(instance.social, dict) else {}
                for field in social_fields:
                    platform = field.replace('_handle', '').replace('_number', '')
                    if field in self.fields:
                        self.fields[field].initial = soc.get(platform, '') or getattr(instance, field, '')
            
        elif key == 'about':
            self.fields['title'].label = 'About Page Title'
            self.fields['content'].label = 'About Page Content'
            self.fields['content'].help_text = 'This text appears on the About page.'
            for f in contact_fields:
                self.fields.pop(f, None)
                
        elif key == 'homepage_banner':
            self.fields['title'].label = 'Homepage Banner Title'
            self.fields['content'].label = 'Homepage Banner Content'
            self.fields['content'].help_text = 'This text appears in the banner on the homepage.'
            for f in contact_fields:
                self.fields.pop(f, None)
                
        elif key == 'checkout':
            self.fields['title'].label = 'Checkout Section Title'
            self.fields['title'].required = True
            self.fields['content'].label = 'Checkout Notes / Help Text'
            self.fields['content'].required = True
            self.fields['content'].help_text = 'Optional notice or instructions shown on the checkout page.'
            self.fields['delivery_fee_24h'].widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
            self.fields['delivery_fee_24h'].required = True
            self.fields['delivery_fee_2d'].widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
            self.fields['delivery_fee_2d'].required = True
            for f in contact_fields:
                self.fields.pop(f, None)
                
        elif key == 'site_settings':
            self.fields['title'].label = 'Site Settings'
            self.fields['title'].widget = forms.HiddenInput()
            self.fields['content'].widget = forms.HiddenInput()
            for f in contact_fields:
                self.fields.pop(f, None)
            # Configure widgets for site settings
            if 'free_shipping_threshold' in self.fields:
                self.fields['free_shipping_threshold'].widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
            if 'return_policy_days' in self.fields:
                self.fields['return_policy_days'].widget = forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
                
        elif key in ['faq', 'privacy', 'terms']:
            self.fields['title'].label = f'{key.upper() if key in ["faq"] else key.title()} Page Title'
            self.fields['content'].label = f'{key.upper() if key in ["faq"] else key.title()} Content'
            self.fields['content'].help_text = f'This content appears on the {key.upper() if key in ["faq"] else key.title()} page.'
            for f in contact_fields:
                self.fields.pop(f, None)
        else:
            # Default: hide contact fields
            for f in contact_fields:
                self.fields.pop(f, None)

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Sync individual social fields to the social JSON dict
        social_mapping = {
            'twitter_handle': 'twitter',
            'instagram_handle': 'instagram', 
            'facebook_handle': 'facebook',
            'whatsapp_number': 'whatsapp',
            'tiktok_handle': 'tiktok',
            'youtube_handle': 'youtube',
        }
        
        soc = instance.social if hasattr(instance, 'social') and isinstance(instance.social, dict) else {}
        for field_name, platform in social_mapping.items():
            val = self.cleaned_data.get(field_name) if hasattr(self, 'cleaned_data') else None
            if val:
                soc[platform] = val.strip()
            elif platform in soc:
                soc.pop(platform, None)
        
        try:
            instance.social = soc
        except Exception:
            instance.social = soc
            
        if commit:
            instance.save()
        return instance


# --- New contact form ---
class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=200, 
        min_length=2,
        widget=forms.TextInput(attrs={
            'class':'form-control',
            'placeholder': 'Enter your full name'
        }),
        error_messages={
            'required': 'Please enter your name',
            'min_length': 'Name must be at least 2 characters long'
        }
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class':'form-control',
            'placeholder': 'your.email@example.com'
        }),
        error_messages={
            'required': 'Please enter your email address',
            'invalid': 'Please enter a valid email address'
        }
    )
    subject = forms.CharField(
        max_length=200, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class':'form-control',
            'placeholder': 'What is your message about? (optional)'
        })
    )
    message = forms.CharField(
        min_length=10,
        widget=forms.Textarea(attrs={
            'class':'form-control', 
            'rows':5,
            'placeholder': 'Please write your message here. Be as detailed as possible...'
        }),
        error_messages={
            'required': 'Please enter your message',
            'min_length': 'Message must be at least 10 characters long'
        }
    )
    honeypot = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_honeypot(self):
        data = self.cleaned_data.get('honeypot')
        if data:
            raise forms.ValidationError('Spam detected')
        return data
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Please enter your name')
        # Check if name contains at least some letters
        if not any(c.isalpha() for c in name):
            raise forms.ValidationError('Please enter a valid name')
        # Prevent very short single-character names
        if len(name) < 2:
            raise forms.ValidationError('Name must be at least 2 characters')
        return name
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError('Please enter your message')
        # Minimum length check
        if len(message) < 10:
            raise forms.ValidationError('Message must be at least 10 characters long')
        # Check if message contains meaningful content (at least some letters)
        letter_count = sum(1 for c in message if c.isalpha())
        if letter_count < 5:
            raise forms.ValidationError('Please write a meaningful message')
        # Check for excessive repetition (spam pattern)
        if len(set(message.replace(' ', ''))) < 3:
            raise forms.ValidationError('Please write a meaningful message')
        return message


from django import forms as _forms
from core.models import BannerImage, HeroImage

class BannerImageForm(_forms.ModelForm):
    class Meta:
        model = BannerImage
        fields = ['title', 'image', 'alt_text', 'link', 'order', 'is_active']
        widgets = {
            'order': _forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:90px;'}),
            'title': _forms.TextInput(attrs={'class': 'form-control'}),
            'alt_text': _forms.TextInput(attrs={'class': 'form-control'}),
            'link': _forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': _forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance', None)
        key = None
        if instance:
            key = getattr(instance, 'key', None)
        elif 'initial' in kwargs:
            key = kwargs['initial'].get('key')

        contact_fields = ['phone', 'email', 'social_links']
        # Remove delivery fee fields from non-checkout sections to avoid validation issues
        # They will be present only for the 'checkout' section
        if key != 'checkout':
            self.fields.pop('delivery_fee_24h', None)
            self.fields.pop('delivery_fee_2d', None)
        # Show/hide fields and adjust help text based on section
        if key == 'contact':
            self.fields['title'].label = 'Contact Page Title'
            self.fields['content'].label = 'Contact Page Content'
            self.fields['content'].help_text = 'This text appears at the top of the Contact page.'
            # Remove map_embed from the form
            self.fields.pop('map_embed', None)
            # Add structured social fields for easier input (handles or full URLs)
            self.fields['twitter'] = forms.CharField(required=False, label='Twitter', help_text='Twitter handle (e.g. @yourhandle) or full URL')
            self.fields['instagram'] = forms.CharField(required=False, label='Instagram', help_text='Instagram handle (e.g. yourhandle) or full URL')
            self.fields['facebook'] = forms.CharField(required=False, label='Facebook', help_text='Facebook page/handle or full URL')
            self.fields['whatsapp'] = forms.CharField(required=False, label='WhatsApp', help_text='Phone number (e.g. +2348012345678) or wa.me link')
            # Set initial values from instance.social if available
            if instance and hasattr(instance, 'social') and instance.social:
                soc = instance.social if isinstance(instance.social, dict) else {}
                self.fields['twitter'].initial = soc.get('twitter', '')
                self.fields['instagram'].initial = soc.get('instagram', '')
                self.fields['facebook'].initial = soc.get('facebook', '')
                self.fields['whatsapp'].initial = soc.get('whatsapp', '')
        elif key == 'about':
            self.fields['title'].label = 'About Page Title'
            self.fields['content'].label = 'About Page Content'
            self.fields['content'].help_text = 'This text appears on the About page.'
            for field in contact_fields:
                self.fields[field].widget = forms.HiddenInput()
        elif key == 'homepage_banner':
            self.fields['title'].label = 'Homepage Banner Title'
            self.fields['content'].label = 'Homepage Banner Content'
            self.fields['content'].help_text = 'This text appears in the banner on the homepage.'
            for field in contact_fields:
                self.fields[field].widget = forms.HiddenInput()
        elif key == 'checkout':
            # Show checkout-specific fee fields
            self.fields['title'].label = 'Checkout Section Title'
            self.fields['content'].label = 'Checkout Notes / Help Text'
            self.fields['content'].help_text = 'Optional notice or instructions shown on the checkout page.'
            # Show delivery fee inputs, hide contact info
            self.fields['delivery_fee_24h'].widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
            self.fields['delivery_fee_2d'].widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
            for field in contact_fields:
                self.fields[field].widget = forms.HiddenInput()
        else:
            for field in contact_fields:
                self.fields[field].widget = forms.HiddenInput()

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Save structured social fields into instance.social (dict)
        social_keys = ['twitter', 'instagram', 'facebook', 'whatsapp']
        soc = instance.social if hasattr(instance, 'social') and isinstance(instance.social, dict) else {}
        for key in social_keys:
            val = self.cleaned_data.get(key) if hasattr(self, 'cleaned_data') else None
            if val:
                soc[key] = val.strip()
            else:
                if key in soc:
                    soc.pop(key, None)
        # Assign back
        try:
            instance.social = soc
        except Exception:
            # If social is a TextField fallback, serialize as string
            instance.social = soc
        if commit:
            instance.save()
        return instance


from django import forms as _forms
from core.models import BannerImage, HeroImage

class BannerImageForm(_forms.ModelForm):
    class Meta:
        model = BannerImage
        fields = ['title', 'image', 'alt_text', 'link', 'order', 'is_active']
        widgets = {
            'order': _forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:90px;'}),
            'title': _forms.TextInput(attrs={'class': 'form-control'}),
            'alt_text': _forms.TextInput(attrs={'class': 'form-control'}),
            'link': _forms.URLInput(attrs={'class': 'form-control'}),
            'is_active': _forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class HeroImageForm(_forms.ModelForm):
    class Meta:
        model = HeroImage
        fields = ['title', 'image', 'alt_text', 'order', 'is_active']
        widgets = {
            'order': _forms.NumberInput(attrs={'class': 'form-control', 'style': 'width:90px;'}),
            'title': _forms.TextInput(attrs={'class': 'form-control'}),
            'alt_text': _forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': _forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
