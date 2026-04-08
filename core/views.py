from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.db.models import Count, Prefetch
from products.models import Product
from core.models import SiteContent


class FAQView(TemplateView):
    template_name = 'faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faq = SiteContent.objects.filter(key='faq').first()
        context['faq_title'] = faq.title if faq else 'Frequently Asked Questions'
        context['faq_content'] = faq.content if faq else ''
        context['faq_updated'] = faq.updated_at if faq else None
        return context


class PrivacyPolicyView(TemplateView):
    template_name = 'privacy_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        privacy = SiteContent.objects.filter(key='privacy').first()
        context['privacy_title'] = privacy.title if privacy else 'Privacy Policy'
        context['privacy_content'] = privacy.content if privacy else ''
        context['privacy_updated'] = privacy.updated_at if privacy else None
        return context


class TermsConditionsView(TemplateView):
    template_name = 'terms_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        terms = SiteContent.objects.filter(key='terms').first()
        context['terms_title'] = terms.title if terms else 'Terms & Conditions'
        context['terms_content'] = terms.content if terms else ''
        context['terms_updated'] = terms.updated_at if terms else None
        return context

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_products'] = Product.objects.select_related('category').prefetch_related('images', 'variants').order_by('-created_at')[:8]
        # Add homepage banner content and banner images
        from core.models import SiteContent, BannerImage
        content_map = {item.key: item for item in SiteContent.objects.filter(key='homepage_banner')}
        banner = content_map.get('homepage_banner')
        context['homepage_banner_title'] = banner.title if banner else 'Homepage Banner'
        context['homepage_banner_content'] = banner.content if banner else ''
        context['banner_background_style'] = banner.background_style if banner else 'gradient_blue'
        context['banner_background_video'] = banner.background_video if banner else None
        context['banner_images'] = BannerImage.objects.filter(is_active=True).order_by('order', '-created_at')
        # hero images for floating product mockups
        from core.models import HeroImage
        context['hero_images'] = HeroImage.objects.filter(is_active=True).order_by('order', '-created_at')
        # Category previews: try to show first product image per category for the home cards
        from products.models import Category
        slugs = ['electronics', 'cosmetics', 'fashion', 'home']
        previews = {}
        categories = Category.objects.filter(slug__in=slugs).prefetch_related(
            Prefetch('products', queryset=Product.objects.filter(image__isnull=False).only('id', 'image'), to_attr='image_products')
        ).annotate(product_count=Count('products'))
        category_map = {cat.slug: cat for cat in categories}
        for s in slugs:
            cat = category_map.get(s)
            if cat:
                prod = cat.image_products[0] if getattr(cat, 'image_products', None) else None
                img_url = prod.image.url if prod and prod.image else None
                previews[s] = {'category': cat, 'image_url': img_url, 'count': getattr(cat, 'product_count', 0)}
            else:
                previews[s] = {'category': None, 'image_url': None, 'count': 0}
        context['categories_preview'] = previews
        # data URI placeholder (neutral SVG)
        placeholder_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='400'><rect width='100%' height='100%' fill='%23f0f0f0'/><text x='50%' y='50%' fill='%23999' font-size='24' text-anchor='middle' dy='.3em'>No image</text></svg>"
        context['placeholder_data_uri'] = placeholder_svg
        context['page_title'] = "Welcome to E-Stores - Quality at Great Prices"
        return context


class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        about = SiteContent.objects.filter(key='about').first()
        context['about_content'] = about.content if about else ''
        context['about_title'] = about.title if about else 'About Us'
        # Team members
        from core.models import TeamMember
        context['team_members'] = TeamMember.objects.filter(is_active=True).order_by('order')[:12]
        # Basic company structured data
        from django.conf import settings
        org = {
            '@context': 'http://schema.org',
            '@type': 'Organization',
            'name': getattr(settings, 'SITE_NAME', 'E-Stores'),
            'url': getattr(settings, 'SITE_URL', ''),
            'contactPoint': [{
                '@type': 'ContactPoint',
                'contactType': 'customer support',
                'telephone': about.phone if about and about.phone else '',
                'email': about.email if about and about.email else ''
            }]
        }
        import json
        context['about_structured_data'] = org
        context['about_structured_data_json'] = json.dumps(org)
        return context


class ContactView(TemplateView):
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = SiteContent.objects.filter(key='contact').first()
        context['contact_content'] = contact.content if contact else ''
        context['contact_title'] = contact.title if contact else 'Contact Us'
        context['contact_phone'] = contact.phone if contact else ''
        context['contact_email'] = contact.email if contact else ''
        # Contact form
        from core.forms import ContactForm
        context['contact_form'] = ContactForm()

        def _normalize(platform, val):
            if not val:
                return None
            v = val.strip()
            if v.startswith('http') or v.startswith('wa.me'):
                return v
            # Remove leading @ from handles
            if v.startswith('@'):
                v = v[1:]
            # Build URLs based on platform
            if platform == 'twitter':
                return f'https://twitter.com/{v}'
            if platform == 'instagram':
                return f'https://instagram.com/{v}'
            if platform == 'facebook':
                return f'https://facebook.com/{v}'
            if platform == 'whatsapp':
                # Normalize phone number: remove non-digits and ensure it starts with country code
                digits = ''.join(ch for ch in v if ch.isdigit())
                if digits:
                    return f'https://wa.me/{digits}'
                return v
            # Default: return raw value or assume it's a URL
            return v

        # Prefer structured social dict if present
        social_items = []
        if contact and hasattr(contact, 'social') and contact.social:
            soc = contact.social if isinstance(contact.social, dict) else {}
            for platform, val in soc.items():
                url = _normalize(platform, val)
                if url:
                    social_items.append({'platform': platform, 'url': url})
        elif contact and contact.social_links:
            # Fallback to legacy comma-separated URLs
            for l in [l.strip() for l in contact.social_links.split(',') if l.strip()]:
                # Try to guess platform from URL
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

        context['contact_social_list'] = social_items
        # WhatsApp
        whatsapp_item = next((s for s in social_items if s['platform'] == 'whatsapp'), None)
        context['contact_whatsapp'] = whatsapp_item['url'] if whatsapp_item else None
        context['contact_map'] = ''  # Map is now fixed in template
        return context

    def post(self, request, *args, **kwargs):
        from core.forms import ContactForm
        from core.models import ContactMessage
        from django.contrib import messages
        from django.core.cache import cache
        from django.conf import settings
        form = ContactForm(request.POST)
        if not form.is_valid():
            # Build a more helpful error message
            error_fields = []
            if form.errors:
                for field, errors in form.errors.items():
                    if field != 'honeypot':  # Don't mention honeypot field
                        field_name = field.replace('_', ' ').title()
                        error_fields.append(field_name)
            
            if error_fields:
                messages.error(request, f'Please check the following fields: {", ".join(error_fields)}')
            else:
                messages.error(request, 'There was a problem with your submission. Please try again.')
            
            context = self.get_context_data()
            context['contact_form'] = form
            return render(request, self.template_name, context)
        # rate limit per IP (simple): 6 per hour
        ip = request.META.get('REMOTE_ADDR', '')
        key = f'contact_rate_{ip}'
        count = cache.get(key, 0)
        if count >= getattr(settings, 'CONTACT_RATE_LIMIT_PER_HOUR', 6):
            messages.error(request, 'You have reached the contact submission limit. Please try later.')
            return redirect('core:contact')
        # Save message
        cm = ContactMessage.objects.create(
            name=form.cleaned_data['name'],
            email=form.cleaned_data['email'],
            subject=form.cleaned_data.get('subject', ''),
            message=form.cleaned_data['message'],
            ip_address=ip,
            user=request.user if request.user.is_authenticated else None,
        )
        cache.set(key, count + 1, 3600)
        # Optional email notification
        try:
            from django.core.mail import send_mail
            notify_to = getattr(settings, 'CONTACT_NOTIFY_EMAIL', None)
            if notify_to:
                send_mail(f'New contact: {cm.subject or "(no subject)"}', cm.message, settings.DEFAULT_FROM_EMAIL, [notify_to])
        except Exception:
            pass
        messages.success(request, 'Thank you — your message has been received. We will get back to you soon.')
        return redirect('core:contact')

class GalleryView(TemplateView):
    template_name = 'core/gallery.html'

    def get_context_data(self, **kwargs):
        from products.models import Product, ProductImage
        context = super().get_context_data(**kwargs)
        # Get all product images, or fallback to products if none exist
        product_images = ProductImage.objects.select_related('product').all()
        if product_images.exists():
            context['gallery_images'] = list(product_images)
        else:
            # fallback: show all products (even if no image)
            context['gallery_products'] = Product.objects.all()
        return context


# ── Chat AJAX views ───────────────────────────────────────────────────────────

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
import json


def _json_body(request):
    """Parse JSON body, fall back to POST dict."""
    try:
        return json.loads(request.body)
    except Exception:
        return request.POST


@require_POST
def chat_start(request):
    """Start a new chat conversation and post the first customer message."""
    from core.models import ChatConversation, ChatMessage

    data = _json_body(request)
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    subject = (data.get('subject') or 'Support Request').strip()
    message_text = (data.get('message') or '').strip()

    if not message_text:
        return JsonResponse({'success': False, 'error': 'Message is required.'}, status=400)

    # Ensure session exists so guests can be tracked
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key or ''

    if request.user.is_authenticated:
        conv = ChatConversation.objects.create(
            user=request.user,
            subject=subject,
            status='open',
        )
    else:
        if not name:
            return JsonResponse({'success': False, 'error': 'Name is required.'}, status=400)
        conv = ChatConversation.objects.create(
            guest_name=name,
            guest_email=email,
            subject=subject,
            session_key=session_key,
            status='open',
        )

    ChatMessage.objects.create(
        conversation=conv,
        sender_type='customer',
        sender_name=conv.display_name,
        message=message_text,
    )

    # ── Auto-reply bot ────────────────────────────────────────────────────────
    _try_auto_reply(conv, message_text)

    return JsonResponse({
        'success': True,
        'conversation_id': conv.pk,
        'display_name': conv.display_name,
    })


@require_POST
def chat_send(request):
    """Send a subsequent message inside an existing conversation (customer side)."""
    from core.models import ChatConversation, ChatMessage, ChatAutoReply

    data = _json_body(request)
    conv_id = data.get('conversation_id')
    message_text = (data.get('message') or '').strip()

    if not message_text:
        return JsonResponse({'success': False, 'error': 'Message is required.'}, status=400)

    if not conv_id:
        return JsonResponse({'success': False, 'error': 'conversation_id required.'}, status=400)

    qs = ChatConversation.objects.filter(pk=conv_id)
    if request.user.is_authenticated:
        conv = qs.filter(user=request.user).first()
    else:
        session_key = request.session.session_key or ''
        conv = qs.filter(session_key=session_key).first()

    if not conv:
        return JsonResponse({'success': False, 'error': 'Conversation not found.'}, status=404)

    if conv.status == 'closed':
        return JsonResponse({'success': False, 'error': 'This conversation is closed.'}, status=400)

    msg = ChatMessage.objects.create(
        conversation=conv,
        sender_type='customer',
        sender_name=conv.display_name,
        message=message_text,
    )
    conv.save()  # refresh updated_at

    # ── Auto-reply bot ────────────────────────────────────────────────────────
    _try_auto_reply(conv, message_text)

    return JsonResponse({
        'success': True,
        'message_id': msg.pk,
        'created_at': msg.created_at.isoformat(),
    })


def _try_auto_reply(conv, customer_text):
    """
    Match customer_text against active ChatAutoReply rules using three-level similarity:
      Level 1 — exact phrase/substring match (highest weight, 4 pts per word)
      Level 2 — direct word overlap (>=60% of keyword words found in message)
      Level 3 — fuzzy word similarity via difflib (handles typos, short-forms, alternate phrasing)
    The highest-scoring rule fires its response as a Dave (Support Bot) message.
    """
    from core.models import ChatAutoReply, ChatMessage
    import re
    from difflib import SequenceMatcher

    def tokenize(text):
        return set(re.findall(r'\b[a-z]+\b', text.lower()))

    def score_keyword(cust_lower, cust_tokens, kw):
        kw_lower = kw.lower().strip()
        if not kw_lower:
            return 0

        # Level 1 — exact phrase present in message
        if kw_lower in cust_lower:
            return len(kw_lower.split()) * 4

        kw_tokens = re.findall(r'\b[a-z]+\b', kw_lower)
        if not kw_tokens:
            return 0

        # Level 2 — direct word overlap
        direct_hits = sum(1 for w in kw_tokens if w in cust_tokens)
        direct_ratio = direct_hits / len(kw_tokens)
        if direct_ratio >= 1.0:
            return len(kw_tokens) * 3
        if direct_ratio >= 0.6:
            return direct_hits * 2

        # Level 3 — fuzzy word similarity (handles typos, "r"/"are", "u"/"you", etc.)
        fuzzy_hits = 0
        for kw_word in kw_tokens:
            best_sim = max(
                (SequenceMatcher(None, kw_word, cw).ratio()
                 for cw in cust_tokens if abs(len(cw) - len(kw_word)) <= 3),
                default=0,
            )
            if best_sim >= 0.78:
                fuzzy_hits += 1
        if len(kw_tokens) > 0 and fuzzy_hits / len(kw_tokens) >= 0.6:
            return fuzzy_hits

        return 0

    customer_lower = customer_text.lower().strip()
    if not customer_lower:
        return
    customer_tokens = tokenize(customer_lower)

    rules = ChatAutoReply.objects.filter(is_active=True).order_by('-priority')

    best_rule = None
    best_score = 0.0

    for rule in rules:
        total = sum(score_keyword(customer_lower, customer_tokens, kw) for kw in rule.keyword_list())
        # Use priority as a tiebreaker only (tiny fractional boost)
        weighted = total + rule.priority * 0.01
        if weighted > best_score:
            best_score = weighted
            best_rule = rule

    if best_rule and best_score >= 2.0:
        ChatMessage.objects.create(
            conversation=conv,
            sender_type='admin',
            sender_name='Olid bot',
            message=best_rule.response,
            is_read=True,  # bot replies don't count as unread for admin
        )


@require_http_methods(['GET'])
def chat_poll(request, conv_id):
    """Return new messages since `?after=<ISO timestamp>` (customer polling)."""
    from core.models import ChatConversation

    qs = ChatConversation.objects.filter(pk=conv_id)
    if request.user.is_authenticated:
        conv = qs.filter(user=request.user).first()
    else:
        session_key = request.session.session_key or ''
        conv = qs.filter(session_key=session_key).first()

    if not conv:
        return JsonResponse({'success': False, 'error': 'Not found.'}, status=404)

    after = request.GET.get('after', '')
    msgs_qs = conv.messages.all()
    if after:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(after)
        if dt:
            msgs_qs = msgs_qs.filter(created_at__gt=dt)

    # Mark admin messages as read by the customer
    conv.messages.filter(sender_type='admin', is_read=False).update(is_read=True)

    return JsonResponse({
        'success': True,
        'status': conv.status,
        'messages': [
            {
                'id': m.pk,
                'sender_type': m.sender_type,
                'sender_name': m.sender_name,
                'message': m.message,
                'created_at': m.created_at.isoformat(),
            }
            for m in msgs_qs
        ],
    })


@require_http_methods(['GET'])
def chat_history(request, conv_id):
    """Return the full message history for a conversation (initial load)."""
    from core.models import ChatConversation

    qs = ChatConversation.objects.filter(pk=conv_id)
    if request.user.is_authenticated:
        conv = qs.filter(user=request.user).first()
    else:
        session_key = request.session.session_key or ''
        conv = qs.filter(session_key=session_key).first()

    if not conv:
        return JsonResponse({'success': False, 'error': 'Not found.'}, status=404)

    # Mark admin messages as read
    conv.messages.filter(sender_type='admin', is_read=False).update(is_read=True)

    return JsonResponse({
        'success': True,
        'status': conv.status,
        'subject': conv.subject,
        'display_name': conv.display_name,
        'messages': [
            {
                'id': m.pk,
                'sender_type': m.sender_type,
                'sender_name': m.sender_name,
                'message': m.message,
                'created_at': m.created_at.isoformat(),
            }
            for m in conv.messages.all()
        ],
    })
