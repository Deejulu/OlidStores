from core.models import SiteContent


def site_contact(request):
    contact = SiteContent.objects.filter(key='contact').first()
    contact_email = contact.email if contact else ''

    def _normalize(platform, val):
        if not val:
            return None
        v = val.strip()
        # If already a complete URL, return it
        if v.startswith('http://') or v.startswith('https://'):
            return v
        # Handle wa.me links without protocol
        if v.startswith('wa.me'):
            return f'https://{v}'
        # Remove @ prefix
        if v.startswith('@'):
            v = v[1:]
        if platform == 'twitter':
            return f'https://twitter.com/{v}'
        if platform == 'instagram':
            return f'https://instagram.com/{v}'
        if platform == 'facebook':
            return f'https://facebook.com/{v}'
        if platform == 'whatsapp':
            # Extract only digits from the phone number
            digits = ''.join(ch for ch in v if ch.isdigit())
            if digits:
                # If number starts with 0, assume Nigerian number and add country code 234
                if digits.startswith('0'):
                    digits = '234' + digits[1:]
                return f'https://wa.me/{digits}'
            # If no digits found, return None to skip this entry
            return None
        return v

    social_items = []
    if contact and hasattr(contact, 'social') and contact.social:
        soc = contact.social if isinstance(contact.social, dict) else {}
        for platform, val in soc.items():
            url = _normalize(platform, val)
            if url:
                social_items.append({'platform': platform, 'url': url})
    elif contact and contact.social_links:
        for l in [l.strip() for l in contact.social_links.split(',') if l.strip()]:
            platform = 'link'
            if 'twitter.com' in l:
                platform = 'twitter'
            elif 'instagram.com' in l:
                platform = 'instagram'
            elif 'facebook.com' in l:
                platform = 'facebook'
            elif 'wa.me' in l or 'whatsapp' in l:
                platform = 'whatsapp'
            social_items.append({'platform': platform, 'url': l})

    whatsapp_item = next((s for s in social_items if s['platform'] == 'whatsapp'), None)
    contact_whatsapp = whatsapp_item['url'] if whatsapp_item else None
    
    # Add email to social items if available
    if contact_email:
        social_items.append({'platform': 'email', 'url': f'mailto:{contact_email}'})
    
    # Get announcement text from any SiteContent that has it (typically homepage_banner)
    announcement_text = ''
    content_with_announcement = SiteContent.objects.filter(announcement_text__isnull=False).exclude(announcement_text='').first()
    if content_with_announcement:
        announcement_text = content_with_announcement.announcement_text

    # Get background style for global theming
    homepage_banner = SiteContent.objects.filter(key='homepage_banner').first()
    background_style = homepage_banner.background_style if homepage_banner else 'gradient_blue'
    
    # Get announcement bar items (from homepage_banner)
    announcement_bar_item1 = homepage_banner.announcement_bar_item1 if homepage_banner and homepage_banner.announcement_bar_item1 else "Free shipping on orders over ₦15,000"
    announcement_bar_item2 = homepage_banner.announcement_bar_item2 if homepage_banner and homepage_banner.announcement_bar_item2 else "Use code OLID10 for 10% off"
    announcement_bar_item3 = homepage_banner.announcement_bar_item3 if homepage_banner and homepage_banner.announcement_bar_item3 else "Secure checkout guaranteed"
    
    # Theme color mapping
    theme_colors = {
        'gradient_blue': {
            'primary': '#1e3a8a',
            'primary_light': '#3b82f6',
            'primary_dark': '#1e40af',
            'accent': '#60a5fa',
            'accent_light': '#93c5fd',
        },
        'gradient_purple': {
            'primary': '#581c87',
            'primary_light': '#a855f7',
            'primary_dark': '#7e22ce',
            'accent': '#c084fc',
            'accent_light': '#e9d5ff',
        },
        'gradient_orange': {
            'primary': '#ea580c',
            'primary_light': '#fb923c',
            'primary_dark': '#c2410c',
            'accent': '#fdba74',
            'accent_light': '#fed7aa',
        },
        'gradient_green': {
            'primary': '#166534',
            'primary_light': '#22c55e',
            'primary_dark': '#15803d',
            'accent': '#4ade80',
            'accent_light': '#86efac',
        },
        'animated_gradient': {
            'primary': '#e73c7e',
            'primary_light': '#ee7752',
            'primary_dark': '#23a6d5',
            'accent': '#23d5ab',
            'accent_light': '#93c5fd',
        },
        'particles': {
            'primary': '#8B7355',
            'primary_light': '#A8916D',
            'primary_dark': '#6B5A45',
            'accent': '#D4AF37',
            'accent_light': '#E5C76B',
        },
        'waves': {
            'primary': '#1e3a8a',
            'primary_light': '#3b82f6',
            'primary_dark': '#1e40af',
            'accent': '#60a5fa',
            'accent_light': '#93c5fd',
        },
		'sunset_blur': {
			'primary': '#ff5f6d',
			'primary_light': '#ff9966',
			'primary_dark': '#e23e57',
			'accent': '#ffd6a5',
			'accent_light': '#ffe8d6',
		},
		'neon_pulse': {
			'primary': '#00f5a0',
			'primary_light': '#7CFFCB',
			'primary_dark': '#00c27a',
			'accent': '#7C3AED',
			'accent_light': '#A78BFA',
		},
		'stellar_night': {
			'primary': '#0b1020',
			'primary_light': '#1f2a44',
			'primary_dark': '#050618',
			'accent': '#9be3ff',
			'accent_light': '#cfeeff',
		},
    }
    
    active_theme = theme_colors.get(background_style, theme_colors['particles'])

    # Get site settings for global use across all templates
    site_settings = SiteContent.objects.filter(key='site_settings').first()
    site_name = site_settings.site_name if site_settings and site_settings.site_name else 'E-Stores'
    site_tagline = site_settings.site_tagline if site_settings and site_settings.site_tagline else ''
    site_logo = site_settings.site_logo if site_settings and site_settings.site_logo else None
    favicon = site_settings.favicon if site_settings and site_settings.favicon else None
    footer_text = site_settings.footer_text if site_settings and site_settings.footer_text else ''
    store_address = site_settings.store_address if site_settings and site_settings.store_address else ''
    business_hours = site_settings.business_hours if site_settings and site_settings.business_hours else ''
    free_shipping_threshold = site_settings.free_shipping_threshold if site_settings else 0
    return_policy_days = site_settings.return_policy_days if site_settings else 7
    
    # Get contact phone from contact SiteContent
    contact_phone = contact.phone if contact and contact.phone else ''
    
    # Build comprehensive social links from both site_settings and contact
    all_social = {}
    if site_settings:
        if site_settings.twitter_handle:
            all_social['twitter'] = _normalize('twitter', site_settings.twitter_handle)
        if site_settings.instagram_handle:
            all_social['instagram'] = _normalize('instagram', site_settings.instagram_handle)
        if site_settings.facebook_handle:
            all_social['facebook'] = _normalize('facebook', site_settings.facebook_handle)
        if site_settings.whatsapp_number:
            all_social['whatsapp'] = _normalize('whatsapp', site_settings.whatsapp_number)
        if site_settings.tiktok_handle:
            all_social['tiktok'] = _normalize('tiktok', site_settings.tiktok_handle) if site_settings.tiktok_handle.startswith('http') else f'https://tiktok.com/@{site_settings.tiktok_handle.strip("@")}'
        if site_settings.youtube_handle:
            all_social['youtube'] = site_settings.youtube_handle if site_settings.youtube_handle.startswith('http') else f'https://youtube.com/{site_settings.youtube_handle}'

    return {
        'contact_email': contact_email,
        'contact_phone': contact_phone,
        'contact_whatsapp': contact_whatsapp,
        'contact_social_list': social_items,
        'announcement_text': announcement_text,
        'announcement_bar_item1': announcement_bar_item1,
        'announcement_bar_item2': announcement_bar_item2,
        'announcement_bar_item3': announcement_bar_item3,
        'site_theme': background_style,
        'theme_colors': active_theme,
        # Site settings
        'site_name': site_name,
        'site_tagline': site_tagline,
        'site_logo': site_logo,
        'favicon': favicon,
        'footer_text': footer_text,
        'store_address': store_address,
        'business_hours': business_hours,
        'free_shipping_threshold': free_shipping_threshold,
        'return_policy_days': return_policy_days,
        'all_social_links': all_social,
    }