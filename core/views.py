import logging
import os
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.db.models import Count, Prefetch, Avg
from django.core.cache import cache
import threading
from products.models import Product
from core.models import SiteContent

logger = logging.getLogger('core.chat')


CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))


def _get_sitecontent(key):
    return cache.get_or_set(f'site_content_{key}', lambda: SiteContent.objects.filter(key=key).first(), CACHE_TTL)


def _async_send_mail(subject, message, from_email, recipient_list):
    try:
        from django.core.mail import send_mail
        send_mail(subject, message, from_email, recipient_list)
    except Exception:
        pass


class FAQView(TemplateView):
    template_name = 'faq.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faq = _get_sitecontent('faq')
        context['faq_title'] = faq.title if faq else 'Frequently Asked Questions'
        context['faq_content'] = faq.content if faq else ''
        context['faq_updated'] = faq.updated_at if faq else None
        return context


class PrivacyPolicyView(TemplateView):
    template_name = 'privacy_policy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        privacy = _get_sitecontent('privacy')
        context['privacy_title'] = privacy.title if privacy else 'Privacy Policy'
        context['privacy_content'] = privacy.content if privacy else ''
        context['privacy_updated'] = privacy.updated_at if privacy else None
        return context


class TermsConditionsView(TemplateView):
    template_name = 'terms_conditions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        terms = _get_sitecontent('terms')
        context['terms_title'] = terms.title if terms else 'Terms & Conditions'
        context['terms_content'] = terms.content if terms else ''
        context['terms_updated'] = terms.updated_at if terms else None
        return context

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cache featured products for 10 minutes
        featured_products = cache.get('homepage_featured_products')
        if featured_products is None:
            featured_products = list(Product.objects.select_related('category').prefetch_related('images', 'variants').annotate(
                avg_rating=Avg('reviews__rating'),
                review_count=Count('reviews', distinct=True)
            ).order_by('-created_at')[:8])
            cache.set('homepage_featured_products', featured_products, 600)
        context['featured_products'] = featured_products
        
        # Add homepage banner content and banner images
        from core.models import BannerImage
        banner = _get_sitecontent('homepage_banner')
        context['homepage_banner_title'] = banner.title if banner else 'Homepage Banner'
        context['homepage_banner_content'] = banner.content if banner else ''
        context['banner_background_style'] = banner.background_style if banner else 'gradient_blue'
        context['banner_background_video'] = banner.background_video if banner else None
        
        # Cache banner images for 30 minutes
        banner_images = cache.get('homepage_banner_images')
        if banner_images is None:
            banner_images = list(BannerImage.objects.filter(is_active=True).order_by('order', '-created_at'))
            cache.set('homepage_banner_images', banner_images, 1800)
        context['banner_images'] = banner_images
        
        # hero images for floating product mockups - cache for 30 minutes
        from core.models import HeroImage
        hero_images = cache.get('homepage_hero_images')
        if hero_images is None:
            hero_images = list(HeroImage.objects.filter(is_active=True).order_by('order', '-created_at'))
            cache.set('homepage_hero_images', hero_images, 1800)
        context['hero_images'] = hero_images
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
        context['page_title'] = "Welcome to Olid Stores - Quality at Great Prices"
        return context


class AboutView(TemplateView):
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        about = _get_sitecontent('about')
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
            'name': getattr(settings, 'SITE_NAME', 'Olid Stores'),
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


class ContactPageView(TemplateView):
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = _get_sitecontent('contact')
        context['contact_content'] = contact.content if contact else ''
        context['contact_title'] = contact.title if contact else 'Contact Us'
        context['contact_phone'] = contact.phone if contact else ''
        context['contact_email'] = contact.email if contact else ''

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

class GalleryView(TemplateView):
    template_name = 'core/gallery.html'

    def get_context_data(self, **kwargs):
        from products.models import Product, ProductImage
        context = super().get_context_data(**kwargs)
        product_images = ProductImage.objects.select_related('product').all()
        if product_images.exists():
            context['gallery_images'] = list(product_images)
        else:
            # Fallback: only products that actually have an image
            context['gallery_products'] = Product.objects.exclude(image='').exclude(image__isnull=True)
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

    customer_msg = ChatMessage.objects.create(
        conversation=conv,
        sender_type='customer',
        sender_name=conv.display_name,
        message=message_text,
    )

    # ── Welcome message from bot ──────────────────────────────────────────────
    _send_welcome_message(conv)

    # ── Auto-reply bot ────────────────────────────────────────────────────────
    tier = _try_auto_reply(conv, message_text, request)
    logger.info('chat_start conv=%s tier=%s', conv.pk, tier)

    return JsonResponse({
        'success': True,
        'conversation_id': conv.pk,
        'display_name': conv.display_name,
        'message_created_at': customer_msg.created_at.isoformat(),
    })


@require_POST
def chat_send(request):
    """Send a subsequent message inside an existing conversation (customer side)."""
    from core.models import ChatConversation, ChatMessage

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
    tier = _try_auto_reply(conv, message_text, request)
    logger.info('chat_send conv=%s tier=%s', conv.pk, tier)

    return JsonResponse({
        'success': True,
        'message_id': msg.pk,
        'created_at': msg.created_at.isoformat(),
    })


def _ensure_default_auto_replies():
    """Create a trimmed baseline set of ~28 high-value auto-reply rules when none exist."""
    from core.models import ChatAutoReply

    if ChatAutoReply.objects.filter(is_active=True).exists():
        return

    defaults = [
        {
            'category': 'general', 'priority': 10, 'is_active': True,
            'question': 'Greeting - Hello',
            'keywords': 'hello, hi, hey, good morning, good afternoon, good evening',
            'response': 'Hello! Welcome to our store. How can I help you today?',
        },
        {
            'category': 'general', 'priority': 10, 'is_active': True,
            'question': 'How Are You',
            'keywords': 'how are you, how are u, how r you, how r u, how you doing, how u doing, how far',
            'response': 'I am doing great, thank you for asking! I am here and ready to help you. What can I do for you today?',
        },
        {
            'category': 'general', 'priority': 10, 'is_active': True,
            'question': 'Farewell - Bye Goodbye',
            'keywords': 'bye, goodbye, see you, take care, later, good night',
            'response': 'Goodbye! Thank you for chatting with us. Have a wonderful day!',
        },
        {
            'category': 'general', 'priority': 10, 'is_active': True,
            'question': 'Thank You',
            'keywords': 'thank you, thanks, thank u, thankyou, thx, ty, much appreciated, appreciate it',
            'response': 'You are very welcome! It is our pleasure to assist you. Is there anything else I can help you with?',
        },
        {
            'category': 'orders', 'priority': 20, 'is_active': True,
            'question': 'Where Is My Order / Order Tracking',
            'keywords': (
                'where is my order, track my order, order tracking, where is my package, '
                'order status, check my order, track order, my order, order update, '
                'has my order shipped, did my order ship, when will my order arrive, '
                'order not arrived, order not delivered, where my order, '
                'i have not received my order, order taking too long'
            ),
            'response': (
                'To track your order, go to your account and click My Orders to see the latest status. '
                'If you have your order number handy, share it here and our team will look it up for you right away!'
            ),
        },
        {
            'category': 'orders', 'priority': 17, 'is_active': True,
            'question': 'How Long Does Delivery Take',
            'keywords': (
                'delivery time, how long delivery, when will it arrive, how long does shipping take, '
                'delivery days, how many days delivery, how long will it take, when will i receive, '
                'when will i get my order, estimated delivery, expected delivery, delivery duration, '
                'how long shipping, delivery how long, fast delivery, quick delivery'
            ),
            'response': (
                'Standard delivery typically takes 3 to 5 business days within Lagos '
                'and 5 to 7 business days for other states. '
                'You will receive a tracking number via email once your order ships. '
                'Express delivery is also available at checkout!'
            ),
        },
        {
            'category': 'orders', 'priority': 16, 'is_active': True,
            'question': 'Cancel My Order',
            'keywords': (
                'cancel order, cancel my order, i want to cancel, how to cancel, '
                'order cancellation, stop my order, undo order, reverse order, '
                'cancel purchase, how do i cancel, i need to cancel, please cancel my order'
            ),
            'response': (
                'You can cancel your order within 1 hour of placing it. '
                'Go to My Orders in your account and click Cancel Order. '
                'After 1 hour the order may already be in processing — '
                'contact us immediately and we will do our best to help you!'
            ),
        },
        {
            'category': 'orders', 'priority': 16, 'is_active': True,
            'question': 'Modify or Change Order',
            'keywords': (
                'change order, modify order, edit order, update order, ordered wrong item, '
                'wrong size, wrong colour, wrong color, wrong address, change delivery address, '
                'update address, change my order, i made a mistake on my order'
            ),
            'response': (
                'To modify your order, please contact us as soon as possible since orders are processed quickly. '
                'If your order has not shipped yet, we can make changes for you. '
                'Share your order number and we will sort it out!'
            ),
        },
        {
            'category': 'orders', 'priority': 22, 'is_active': True,
            'question': 'Received Wrong Item',
            'keywords': (
                'wrong item, received wrong, wrong product, not what i ordered, '
                'different from what i ordered, got wrong item, sent wrong item, '
                'incorrect item, wrong thing, they sent me wrong, this is not what i ordered'
            ),
            'response': (
                'We sincerely apologise for sending the wrong item! '
                'Please take a photo of what you received and contact our support team. '
                'We will arrange a free exchange and correct delivery right away at no extra cost to you.'
            ),
        },
        {
            'category': 'orders', 'priority': 22, 'is_active': True,
            'question': 'Damaged or Defective Item',
            'keywords': (
                'damaged order, broken item, item damaged, damaged product, package damaged, '
                'arrived broken, came broken, defective, not working, faulty, '
                'item not working, product broken, received damaged, item is damaged'
            ),
            'response': (
                'We are so sorry your item arrived damaged! '
                'Please take clear photos of the damage and send them to our support. '
                'We will replace it or issue a full refund immediately. Your satisfaction is our priority!'
            ),
        },
        {
            'category': 'orders', 'priority': 13, 'is_active': True,
            'question': 'How To Place An Order',
            'keywords': (
                'how to order, how to buy, how do i order, how to place order, ordering process, '
                'steps to order, how do i buy, how to purchase, place an order, how do i purchase, '
                'buying process, i want to buy'
            ),
            'response': (
                'Placing an order is simple! '
                '1. Browse our products and click Add to Cart '
                '2. Review your cart and click Checkout '
                '3. Enter your delivery address '
                '4. Choose your payment method and complete payment '
                '5. You will receive an order confirmation email instantly! '
                'Need help? We are here every step of the way.'
            ),
        },
        {
            'category': 'payment', 'priority': 15, 'is_active': True,
            'question': 'Payment Methods Accepted',
            'keywords': (
                'payment methods, how to pay, ways to pay, accepted payment, do you accept card, '
                'can i pay with, payment options, how can i pay, bank transfer, card payment, '
                'pay online, paystack, pay on delivery, cash on delivery, what payment, which payment'
            ),
            'response': (
                'We accept the following payment methods: '
                '- Debit/Credit Cards (Visa, Mastercard, Verve) '
                '- Bank Transfer '
                '- Paystack secure online checkout '
                '- Pay on Delivery (available in select areas). '
                'All online payments are 100% secure and encrypted.'
            ),
        },
        {
            'category': 'payment', 'priority': 20, 'is_active': True,
            'question': 'Payment Failed',
            'keywords': (
                'payment failed, payment not successful, transaction failed, payment declined, '
                'card declined, my payment failed, payment error, unable to pay, payment issue, '
                'payment unsuccessful, payment not going through, payment problem, '
                'transaction not successful, cant pay'
            ),
            'response': (
                'Sorry about that! If your payment failed, please try: '
                '1. Double-check your card details '
                '2. Ensure your card is enabled for online transactions '
                '3. Try a different payment method '
                '4. Contact your bank if the error persists. '
                'If you were charged but got no order confirmation, contact us immediately with your transaction reference!'
            ),
        },
        {
            'category': 'payment', 'priority': 25, 'is_active': True,
            'question': 'Charged But No Order Confirmation',
            'keywords': (
                'charged but no order, money deducted no order, payment taken but no order, '
                'debited but no order, money gone but no order, paid but order not placed, '
                'charged twice, double charge, duplicate charge, money left account no order, '
                'i was charged but no order'
            ),
            'response': (
                'Please do not panic! If you were charged but did not receive an order confirmation, '
                'it usually reverses automatically within 24 to 48 hours. '
                'However, please contact us immediately with your transaction reference and '
                'we will investigate and resolve it as a top priority.'
            ),
        },
        {
            'category': 'payment', 'priority': 12, 'is_active': True,
            'question': 'Is Payment Secure',
            'keywords': (
                'is payment safe, is it safe to pay, safe to enter card, secure payment, '
                'is the website safe, is my card safe, payment security, is this site safe, '
                'can i trust this site, is it legit'
            ),
            'response': (
                'Absolutely! All payments are processed through Paystack, '
                'a fully PCI-DSS compliant payment gateway. '
                'Your card details are never stored on our servers. '
                'Shopping with us is 100% safe and secure.'
            ),
        },
        {
            'category': 'returns', 'priority': 18, 'is_active': True,
            'question': 'Return Policy',
            'keywords': (
                'return policy, return item, how to return, can i return, return product, '
                'returns, send back, i want to return, return process, return request, '
                'returning an item, how do i return, what is your return policy'
            ),
            'response': (
                'We have a 7-day return policy. '
                'To return an item: '
                '1. Contact us within 7 days of delivery '
                '2. Item must be unused and in original packaging '
                '3. We will arrange a pickup from your address. '
                'Note: Some items (e.g. personal care products) are non-returnable for hygiene reasons.'
            ),
        },
        {
            'category': 'returns', 'priority': 18, 'is_active': True,
            'question': 'Refund - When and How',
            'keywords': (
                'refund, get my money back, money back, when will i get refund, refund policy, '
                'how long refund, refund time, refund status, when will i be refunded, '
                'when is my refund coming, want a refund, i want my money back'
            ),
            'response': (
                'Refunds are processed within 3 to 7 business days after we receive and inspect your returned item. '
                'The money will be returned to your original payment method. '
                'You will receive an email confirmation once your refund is processed.'
            ),
        },
        {
            'category': 'returns', 'priority': 15, 'is_active': True,
            'question': 'Exchange Item',
            'keywords': (
                'exchange, swap, change product, exchange item, change size, exchange size, '
                'swap product, different size, want different color, change color, '
                'want to swap, exchange for another'
            ),
            'response': (
                'Yes, we offer exchanges! You can exchange an item within 7 days of delivery '
                'for a different size, colour, or product (subject to availability). '
                'Contact us with your order number and we will guide you through the exchange process.'
            ),
        },
        {
            'category': 'products', 'priority': 14, 'is_active': True,
            'question': 'Product Availability / In Stock',
            'keywords': (
                'in stock, available, is it available, do you have, out of stock, '
                'when will it be back, back in stock, restock, restocking, product available, '
                'when available, will it come back, sold out, is this available, is it in stock'
            ),
            'response': (
                'You can check real-time stock availability on the product page. '
                'If an item shows Out of Stock: '
                '- Contact us to be notified when it is back in stock '
                '- Check back in a few days as we restock regularly '
                '- Browse similar items in the same category'
            ),
        },
        {
            'category': 'products', 'priority': 13, 'is_active': True,
            'question': 'What Sizes Are Available',
            'keywords': (
                'sizes available, what sizes, size guide, which sizes, size chart, '
                'do you have my size, size options, available sizes, size range, what size, sizing'
            ),
            'response': (
                'Available sizes are listed on each product page. We typically stock sizes XS to 3XL. '
                'If you are unsure about sizing, check our Size Guide on the product page '
                'or contact us — we are happy to help you pick the right fit!'
            ),
        },
        {
            'category': 'products', 'priority': 14, 'is_active': True,
            'question': 'Product Quality / Authenticity',
            'keywords': (
                'is it original, is it authentic, product quality, is it fake, '
                'are products genuine, original products, quality of products, '
                'real or fake, is it real, are they original'
            ),
            'response': (
                'All our products are 100% genuine and authentic. '
                'We source directly from verified manufacturers and trusted suppliers. '
                'Customer satisfaction and product quality are our top priorities.'
            ),
        },
        {
            'category': 'account', 'priority': 15, 'is_active': True,
            'question': 'Forgot Password / Reset Password',
            'keywords': (
                'forgot password, reset password, cant login, cannot login, lost password, '
                'password reset, change password, update password, i forgot my password, '
                'how to reset password, password help, login problem, cant log in'
            ),
            'response': (
                'To reset your password: '
                '1. Click Forgot Password on the login page '
                '2. Enter your email address '
                '3. Check your email for a reset link (also check your spam folder) '
                '4. Click the link and create a new password. '
                'If you still have issues, contact us and we will help you get back in!'
            ),
        },
        {
            'category': 'account', 'priority': 13, 'is_active': True,
            'question': 'How To Create An Account',
            'keywords': (
                'create account, register, sign up, make account, how to register, '
                'open account, new account, how do i sign up, how to create, registration, '
                'how to make account'
            ),
            'response': (
                'Creating an account is easy and free! '
                '1. Click Sign Up at the top of the page '
                '2. Fill in your name, email, and password '
                '3. Verify your email address '
                '4. You are ready to shop! '
                'Having an account lets you track orders, save wishlist items, and checkout faster.'
            ),
        },
        {
            'category': 'general', 'priority': 30, 'is_active': True,
            'question': 'Contact Support / Speak To Human',
            'keywords': (
                'contact support, speak to agent, speak to human, speak to someone, contact us, '
                'talk to someone, real person, human agent, customer service, customer care, '
                'support team, speak with agent, connect me to agent, i want to speak, '
                'talk to a person, i need help from a person'
            ),
            'response': (
                'You would like to speak with our team — we would love to help! '
                'Our support team is available: '
                '- Monday to Friday: 8am to 6pm '
                '- Saturday: 9am to 3pm. '
                'You can also send a message via the Contact Us page and we will respond within a few hours. '
                'What is your concern? We are listening!'
            ),
        },
        {
            'category': 'general', 'priority': 10, 'is_active': True,
            'question': 'Store Opening Hours',
            'keywords': (
                'opening hours, business hours, working hours, when are you open, '
                'what time do you open, what time do you close, are you open, store hours, '
                'shop hours, hours of operation, when do you work, when can i reach you'
            ),
            'response': (
                'Our support team is available: '
                '- Monday to Friday: 8am to 6pm '
                '- Saturday: 9am to 3pm '
                '- Sunday: Closed. '
                'You can still browse and place orders 24/7 on our website!'
            ),
        },
        {
            'category': 'general', 'priority': 12, 'is_active': True,
            'question': 'Complaint or Bad Experience',
            'keywords': (
                'complaint, complain, not happy, unhappy, disappointed, bad service, '
                'bad experience, terrible, awful, very bad, this is bad, frustrated, angry, '
                'upset, not satisfied, not good, this is rubbish, this is terrible, poor service'
            ),
            'response': (
                'We are genuinely sorry to hear about your experience and we sincerely apologise. '
                'Your satisfaction is our top priority. Please tell us exactly what happened and '
                'a senior member of our team will personally attend to your issue and make it right. '
                'We truly value you as our customer.'
            ),
        },
        {
            'category': 'general', 'priority': 12, 'is_active': True,
            'question': 'Discount Coupon Promo Code',
            'keywords': (
                'coupon, discount code, promo code, voucher, discount, promo, have a code, '
                'use code, apply code, any discount, any promo, any coupon, sale, offers, '
                'how to get discount, is there a discount, any deals'
            ),
            'response': (
                'We regularly run promotions and discounts! '
                '- Subscribe to our newsletter for exclusive offers '
                '- Follow us on social media for flash sales '
                '- Check the homepage banners for active promotions. '
                'If you have a promo code, enter it at checkout in the Coupon Code field.'
            ),
        },
        {
            'category': 'general', 'priority': 14, 'is_active': True,
            'question': 'Delivery Fee / Free Shipping',
            'keywords': (
                'free delivery, free shipping, minimum order, how much for free delivery, '
                'delivery fee, shipping fee, how much is delivery, delivery cost, shipping cost, '
                'how much to deliver, cost of delivery, what is delivery fee, is delivery free'
            ),
            'response': (
                'Delivery fees vary by location: '
                '- Lagos: starts from 1,500 '
                '- Other States: 2,500 to 4,000. '
                'Enjoy FREE delivery on orders above 20,000 within Lagos! '
                'Your exact delivery fee is shown clearly at checkout.'
            ),
        },
    ]

    for rule in defaults:
        ChatAutoReply.objects.update_or_create(question=rule['question'], defaults=rule)


def _send_welcome_message(conv):
    """Send an instant welcome/acknowledgment message at the start of every new conversation."""
    from core.models import ChatMessage

    name = conv.display_name
    greeting = f"Hi {name}! 👋 Welcome to our store. Thanks for reaching out — I'm the support bot and I'm here to help right away."
    tips = (
        "\n\nYou can ask me about:\n"
        "• Order tracking & delivery\n"
        "• Payments & refunds\n"
        "• Products & stock\n"
        "• Returns & complaints\n\n"
        "A human agent will also check your message and follow up if needed. What can I help you with?"
    )
    ChatMessage.objects.create(
        conversation=conv,
        sender_type='admin',
        sender_name='Support Bot',
        message=greeting + tips,
        is_read=True,
    )


# ── Account-specific intents (real data, scoped to the logged-in user) ─────────

_ACCOUNT_LOGIN_PROMPT = (
    "To check your orders and payments I need you to be logged in first. "
    "Please sign in at the top right of any page (or tap the account icon on mobile), "
    "then come back and ask me again — I'll pull up your real order and payment details."
)

# Ordered: order-status first, then payment timing/status, then payment history.
_ACCOUNT_ORDER_PATTERNS = [
    r'\bwhere\s+is\s+my\s+order\b', r'\bwhere\s+are\s+my\s+orders?\b',
    r'\bwhere\s+my\s+order\b', r'\bwhere\s+is\s+my\s+package\b',
    r'\bmy\s+order\b', r'\bmy\s+orders\b', r'\border\s+status\b',
    r'\btrack\s+(my\s+)?order\b', r'\border\s+tracking\b',
    r'\bhas\s+my\s+order\s+shipped\b', r'\bdid\s+my\s+order\s+ship\b',
    r'\bis\s+my\s+order\s+shipped\b', r'\bmy\s+order.*shipped\b',
    r'\bmy\s+order.*delivered\b', r'\border.*shipped\b', r'\border.*delivered\b',
    r'\border\s+not\s+received\b', r'\border\s+taking\s+too\s+long\b',
    r'\bwhen\s+will\s+(my\s+)?order\b', r'\bwhen\s+will\s+(my\s+)?package\s+arrive\b',
    r'\border\s+#?\d+\b', r'\border\s+number\b', r'\border\s+update\b',
    r'\border\s+history\b', r'\border.*status\b',
]
_ACCOUNT_PAYMENT_STATUS_PATTERNS = [
    r'\bwhen\s+am\s+i\s+expecting\s+my\s+payment\b',
    r'\bwhen\s+will\s+(my\s+)?payment\b',
    r'\bwhen\s+will\s+i\s+get\s+(my\s+)?payment\b',
    r'\bwhen\s+will\s+i\s+be\s+(refunded|paid)\b',
    r'\bpayment\s+timing\b', r'\bpayment\s+status\b',
    r'\bpayment\s+for\s+order\b',
    r'\bwhen\s+is\s+(my\s+)?payment\b', r'\bwhen\s+is\s+(my\s+)?refund\b',
    r'\brefund\s+status\b', r'\bwhen\s+will\s+(the\s+)?refund\b',
    r'\bpayment\s+processed\b',
    r'\bis\s+(my\s+)?payment\s+(done|confirmed|successful|complete)\b',
]
_ACCOUNT_PAYMENT_HISTORY_PATTERNS = [
    r'\bwhere\s+can\s+i\s+see\s+my\s+previous\s+payment',
    r'\bwhere\s+can\s+i\s+see\s+my\s+(payment|payments)\b',
    r'\bpayment\s+history\b', r'\bprevious\s+payment\b',
    r'\bmy\s+payment\s+history\b', r'\bmy\s+payments\b',
    r'\bpast\s+(payment|payments)\b',
    r'\bshow\s+me\s+my\s+(payment|payments)\b',
    r'\blist\s+my\s+(payment|payments)\b',
    r'\bview\s+my\s+(payment|payments)\b',
    r'\bmy\s+payment\s+receipt\b', r'\bmy\s+payment\s+records\b',
]


def _classify_account_intent(text):
    """Return 'order_status', 'payment_status', 'payment_history' or None."""
    import re
    t = (text or '').lower().strip()
    if not t:
        return None
    for p in _ACCOUNT_ORDER_PATTERNS:
        if re.search(p, t):
            return 'order_status'
    for p in _ACCOUNT_PAYMENT_STATUS_PATTERNS:
        if re.search(p, t):
            return 'payment_status'
    for p in _ACCOUNT_PAYMENT_HISTORY_PATTERNS:
        if re.search(p, t):
            return 'payment_history'
    return None


def _latest_transaction(order):
    from orders.models import PaymentTransaction
    try:
        return PaymentTransaction.objects.filter(order=order).order_by('-created_at').first()
    except Exception:
        return None


def _format_order_line(order):
    placed = order.created_at.strftime('%b %d, %Y')
    parts = ["\u2022 Order #%s \u2014 %s (placed %s)" % (order.number, order.get_status_display(), placed)]
    if order.tracking_number:
        parts.append("  Tracking: %s" % order.tracking_number)
    pt = _latest_transaction(order)
    if pt:
        method = pt.payment_method or 'bank'
        parts.append("  Payment: %s %s via %s \u2014 status %s"
                     % (pt.amount, pt.currency, method, pt.status or 'pending'))
    elif order.payment_method == 'pay_on_delivery':
        parts.append("  Payment: Pay on Delivery (cash on delivery) \u2014 awaiting fulfillment")
    elif order.payment_method == 'manual':
        parts.append("  Payment: Bank transfer \u2014 awaiting confirmation")
    elif order.payment_method:
        parts.append("  Payment: %s \u2014 status pending" % order.payment_method)
    return '\n'.join(parts)


def _format_account_answer(user, intent, customer_text):
    """Build a real-data reply for an account intent. Never reads another user's data."""
    import re
    from orders.models import Order, PaymentTransaction

    # IMPORTANT: always scoped to `user` — never a guest, never another customer.
    recent = list(Order.objects.filter(user=user, is_deleted=False).order_by('-created_at')[:10])

    if intent == 'order_status':
        if not recent:
            return ("I don't see any orders under your account yet. Once you place one, "
                    "come back and ask me and I'll tell you its exact status and tracking!")
        token = None
        m = re.search(r'order\s+#?([A-Za-z0-9\-]+)', customer_text, re.IGNORECASE)
        if m:
            token = m.group(1)
        specific = None
        if token:
            for o in recent:
                if o.number and (token.lower() == o.number.lower()
                                 or token.lower() in o.number.lower()):
                    specific = o
                    break
        if specific:
            return (_format_order_line(specific)
                    + "\n\nWant to see your full order history? Just ask 'where are my orders'.")
        lines = ["Here are your %d most recent order(s):" % len(recent)]
        for o in recent:
            lines.append(_format_order_line(o))
        lines.append("\nReply with the order number (e.g. #EST-2026-0001) and I'll show tracking details.")
        return '\n'.join(lines)

    if intent == 'payment_status':
        if not recent:
            return "I don't see any orders or payments under your account yet."
        lines = ["Here's the payment status for your recent order(s):"]
        for o in recent:
            line = "  \u2022 Order #%s: " % o.number
            pt = _latest_transaction(o)
            if pt:
                line += "%s %s via %s \u2014 %s" % (
                    pt.amount, pt.currency, pt.payment_method or 'bank', pt.status or 'pending')
            elif o.payment_method == 'pay_on_delivery':
                line += "Pay on Delivery (cash on delivery) \u2014 no online payment recorded yet"
            elif o.payment_method == 'manual':
                line += "Bank transfer \u2014 awaiting confirmation"
            else:
                line += "payment method: %s \u2014 status pending" % (o.payment_method or 'unknown')
            lines.append(line)
        lines.append("\nRefunds (if any) are processed within 3-7 business days to your original "
                     "payment method. Need details on a specific order? Share the order number.")
        return '\n'.join(lines)

    if intent == 'payment_history':
        payments = list(PaymentTransaction.objects.filter(order__user=user).order_by('-created_at')[:10])
        if not payments:
            return ("I don't see any recorded payments under your account yet. "
                    "Payments appear here once an order is paid. Need help? Ask 'payment status'.")
        lines = ["You have %d payment record(s):" % len(payments)]
        for pt in payments:
            onum = pt.order.number if pt.order_id else 'N/A'
            amt = ("%s %s" % (pt.amount, pt.currency)) if pt.amount else 'N/A'
            when = pt.created_at.strftime('%b %d, %Y')
            lines.append("\u2022 %s \u2014 %s via %s \u2014 status %s (ref %s, order #%s)"
                         % (when, amt, pt.payment_method or 'bank', pt.status or 'pending', pt.reference, onum))
        return '\n'.join(lines)

    return None


def _handle_account_query(conv, customer_text, request):
    """Account-specific intent handler. Returns a bot reply string or None.

    Runs BEFORE the generic Tier-1 keyword rules so real, account-scoped data
    wins over scripted answers. Only the logged-in user's own orders/payments
    are ever read; a guest is asked to log in instead of erroring out.
    """
    intent = _classify_account_intent(customer_text)
    if intent is None:
        return None
    try:
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated):
            return _ACCOUNT_LOGIN_PROMPT
        return _format_account_answer(user, intent, customer_text)
    except Exception:
        logger.exception('account_query_failed conv=%s intent=%s', conv.pk, intent)
        return None


def _try_auto_reply(conv, customer_text, request=None):
    """
    3-tier response system:
      Tier 1 — instant replies (account-specific real data + keyword rule match)
      Tier 2 — AI-powered fallback via Anthropic (grounded, scoped)
      Tier 3 — human handoff (no bot reply; admin sees it in inbox)

    Returns the tier that answered, or None if Tier 3 (silent handoff).
    """
    from core.models import ChatAutoReply, ChatMessage
    from core.ai_reply import get_ai_reply
    import re
    from difflib import SequenceMatcher

    # Tier 1 (a) — account-specific intents with real, user-scoped data
    account_reply = _handle_account_query(conv, customer_text, request)
    if account_reply is not None:
        ChatMessage.objects.create(
            conversation=conv,
            sender_type='admin',
            sender_name='Olid Stores bot',
            message=account_reply,
            is_read=True,
        )
        logger.info('chat_tier=1 account conv=%s intent=%s',
                    conv.pk, _classify_account_intent(customer_text))
        return 'tier1'

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
        return 'tier3'
    customer_tokens = tokenize(customer_lower)

    _ensure_default_auto_replies()
    rules = ChatAutoReply.objects.filter(is_active=True).order_by('-priority')

    best_rule = None
    best_score = 0.0

    for rule in rules:
        total = sum(score_keyword(customer_lower, customer_tokens, kw) for kw in rule.keyword_list())
        weighted = total + rule.priority * 0.01
        if weighted > best_score:
            best_score = weighted
            best_rule = rule

    if best_rule and best_score >= 2.0:
        ChatMessage.objects.create(
            conversation=conv,
            sender_type='admin',
            sender_name='Olid Stores bot',
            message=best_rule.response,
            is_read=True,
        )
        logger.info(
            'chat_tier=1 conv=%s rule="%s" score=%.1f',
            conv.pk, best_rule.question, best_score
        )
        return 'tier1'

    # Tier 2 — AI fallback
    ai_reply, tier, log_info = get_ai_reply(conv.pk, customer_text)
    logger.info(
        'chat_tier=%s conv=%s reason=%s ai_count=%s',
        tier, conv.pk, log_info.get('reason', ''), log_info.get('ai_count', 0)
    )
    if tier == 'tier2' and ai_reply:
        ChatMessage.objects.create(
            conversation=conv,
            sender_type='admin',
            sender_name='Olid Stores bot',
            message=ai_reply,
            is_read=True,
        )
        return 'tier2'

    # Tier 3 — human handoff (silent)
    return 'tier3'


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


from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone

@require_http_methods(['POST'])
def newsletter_subscribe(request):
    """Handle newsletter subscription via AJAX."""
    from core.models import Newsletter
    import json
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required.'}, status=400)
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email address.'}, status=400)
        
        # Check if email already exists
        existing = Newsletter.objects.filter(email=email).first()
        if existing:
            if existing.is_active:
                return JsonResponse({'success': False, 'error': 'This email is already subscribed.'}, status=400)
            else:
                # Reactivate subscription
                existing.is_active = True
                existing.unsubscribed_at = None
                existing.save()
                return JsonResponse({'success': True, 'message': 'Welcome back! Your subscription has been reactivated.'})
        
        # Create new subscription
        Newsletter.objects.create(email=email)
        return JsonResponse({'success': True, 'message': 'Thank you for subscribing! You\'ll receive our latest updates.'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'An error occurred. Please try again.'}, status=500)


class ShippingPolicyView(TemplateView):
    template_name = 'shipping_policy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shipping = _get_sitecontent('shipping')
        context['shipping_title'] = shipping.title if shipping else 'Shipping & Delivery Policy'
        context['shipping_content'] = shipping.content if shipping else ''
        context['shipping_updated'] = shipping.updated_at if shipping else None
        return context


class ReturnsPolicyView(TemplateView):
    template_name = 'returns_policy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        returns = _get_sitecontent('returns')
        context['returns_title'] = returns.title if returns else 'Returns & Refunds Policy'
        context['returns_content'] = returns.content if returns else ''
        context['returns_updated'] = returns.updated_at if returns else None
        return context
