import os
import re
import hashlib
from django.core.cache import cache
from django.conf import settings
from core.models import SiteContent
from products.models import Category


AI_MODEL = os.getenv('CHAT_AI_MODEL', 'claude-sonnet-4-6')
AI_MAX_TOKENS = int(os.getenv('CHAT_AI_MAX_TOKENS', '300'))
AI_TIMEOUT = int(os.getenv('CHAT_AI_TIMEOUT', '15'))
AI_CACHE_TTL = int(os.getenv('CHAT_AI_CACHE_TTL', '3600'))


def _get_per_conv_cap():
    return int(os.getenv('CHAT_AI_PER_CONV_CAP', '5'))

_ACCOUNT_SPECIFIC_PATTERNS = [
    r'\border\s*#?\d+',
    r'\btracking\s*number\b',
    r'\bmy\s+order\b',
    r'\bwhere\s+is\s+my\s+(order|package|item)\b',
    r'\bstatus\s+of\s+my\s+order\b',
    r'\bdelivery\s+address\b',
    r'\bmy\s+account\b',
    r'\blogin\s+issue\b',
    r'\bpassword\s+reset\b',
    r'\bpayment\s+for\s+order\b',
    r'\brefund\s+for\s+order\b',
    r'\breturn\s+for\s+order\b',
    r'\bexchange\s+for\s+order\b',
    r'\border\s+status\b',
]


def _is_account_specific(text):
    lower = text.lower()
    for pattern in _ACCOUNT_SPECIFIC_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def _get_store_context():
    sc = {s.key: s for s in SiteContent.objects.all()}
    site = sc.get('site_settings') or sc.get('about') or sc.get('contact') or next(iter(sc.values()), None)

    from products.models import Category
    categories = list(Category.objects.values_list('name', flat=True))

    checkout = sc.get('checkout')
    payment_methods = []
    if checkout and checkout.bank_name:
        payment_methods.append(f"Bank Transfer ({checkout.bank_name}, Account: {checkout.account_name}, {checkout.account_number})")
    payment_methods.extend([
        "Paystack secure checkout (Visa, Mastercard, Verve)",
        "Pay on Delivery (available in select areas)",
    ])

    delivery_fee_24h = float(site.delivery_fee_24h) if site and site.delivery_fee_24h else 0.0
    delivery_fee_2d = float(site.delivery_fee_2d) if site and site.delivery_fee_2d else 0.0
    free_shipping = float(site.free_shipping_threshold) if site and site.free_shipping_threshold else 20000.0
    return_days = site.return_policy_days if site else 7

    phone = site.phone if site and site.phone else ''
    email = site.email if site and site.email else ''
    whatsapp = ''
    if site:
        if hasattr(site, 'whatsapp_number') and site.whatsapp_number:
            whatsapp = site.whatsapp_number
        elif hasattr(site, 'social') and isinstance(getattr(site, 'social', None), dict):
            whatsapp = site.social.get('whatsapp', '')

    hours = site.business_hours if site and site.business_hours else 'Monday to Friday: 8am to 6pm, Saturday: 9am to 3pm, Sunday: Closed'
    store_name = site.site_name if site and site.site_name else 'Olid Stores'
    store_address = site.store_address if site and site.store_address else ''

    return {
        'store_name': store_name,
        'phone': phone,
        'email': email,
        'whatsapp': whatsapp,
        'business_hours': hours,
        'free_shipping_threshold': free_shipping,
        'return_policy_days': return_days,
        'delivery_fee_24h': delivery_fee_24h,
        'delivery_fee_2d': delivery_fee_2d,
        'payment_methods': payment_methods,
        'categories': categories,
        'store_address': store_address,
    }


def build_system_prompt(context):
    categories_str = ', '.join(context['categories']) if context['categories'] else 'various consumer goods'
    payments_str = '; '.join(context['payment_methods'])

    prompt = (
        f"You are a customer support assistant for {context['store_name']} only. "
        f"Answer questions about our store, products, orders, delivery, payments, returns, and policies.\n\n"
        f"Store context (use ONLY this factual information):\n"
        f"- Store name: {context['store_name']}\n"
        f"- Categories: {categories_str}\n"
        f"- Payment methods: {payments_str}\n"
        f"- Delivery: 24-hour delivery available at checkout; standard delivery is 3-5 business days within Lagos "
        f"and 5-7 business days for other states. "
        f"FREE delivery on orders above {context['free_shipping_threshold']:,.0f}.\n"
        f"- Returns: {context['return_policy_days']}-day return policy. Items must be unused and in original packaging. "
        f"Some personal-care items may be non-returnable for hygiene reasons.\n"
        f"- Business hours: {context['business_hours']}\n"
        f"- Contact: Phone: {context['phone'] or 'see Contact page'}; "
        f"Email: {context['email'] or 'see Contact page'}; "
        f"WhatsApp: {context['whatsapp'] or 'see Contact page'}\n"
        f"- Address: {context['store_address'] or 'see Contact page'}\n\n"
        "CRITICAL RULES:\n"
        "1. NEVER invent order status, tracking numbers, prices, stock levels, or account-specific data. "
        "If the customer asks about a specific order, tracking, stock level, or account issue, "
        "politely say you cannot access that and offer to connect them with the support team.\n"
        "2. Keep answers short (2-4 sentences for simple questions). Friendly, plain, human tone.\n"
        "3. If you don't know the answer or the question is about account-specific data, say so and suggest they contact support directly.\n"
        "4. Do not make up policies, prices, or delivery times not stated above.\n"
        "5. Do not promise discounts, refunds, or exceptions not explicitly stated in store policy.\n"
        "6. If the customer uses Nigerian Pidgin or informal language, you may reply in plain English; do not invent slang."
    )
    return prompt


def _call_anthropic(system_prompt, user_message):
    try:
        import anthropic
    except ImportError:
        return None, "anthropic library not installed"

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return None, "ANTHROPIC_API_KEY not configured"

    client = anthropic.Anthropic(api_key=api_key, timeout=AI_TIMEOUT)

    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=AI_MAX_TOKENS,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ],
        )
        text = message.content[0].text.strip() if message.content else ""
        return text, None
    except Exception as e:
        return None, str(e)


_UNCERTAINTY_MARKERS = [
    "i don't know",
    "i'm not sure",
    "i cannot access",
    "i can't access",
    "i don't have access",
    "contact support",
    "contact our support team",
    "speak to our team",
    "wait for the team",
    "i am unable to",
    "i cannot provide",
    "i'm unable to",
    "i don't have that information",
    "i'm sorry, i cannot",
    "i'm sorry, i don't",
    "please reach out to",
    "you will need to contact",
    "best to contact",
    "human agent",
    "real person",
]


def _should_handoff(ai_response):
    if not ai_response:
        return True
    lower = ai_response.lower()
    return any(m in lower for m in _UNCERTAINTY_MARKERS)


def _conversation_ai_count_key(conv_id):
    return f'chat_ai_count_{conv_id}'


def _increment_conversation_ai_count(conv_id):
    key = _conversation_ai_count_key(conv_id)
    count = cache.get(key, 0)
    cache.set(key, count + 1, timeout=86400)
    return count + 1


def _cache_key_for_message(text):
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return f'chat_ai_reply_{hashlib.md5(normalized.encode()).hexdigest()}'


def get_ai_reply(conversation_id, customer_text):
    """
    Return (reply_text, tier, log_info).
    tier is one of: 'tier1', 'tier2', 'tier3'
    """
    cap = _get_per_conv_cap()
    current_count = cache.get(_conversation_ai_count_key(conversation_id), 0)
    if current_count >= cap:
        return None, 'tier3', {'reason': 'per_conversation_cap_reached', 'ai_count': current_count}

    cache_key = _cache_key_for_message(customer_text)
    cached = cache.get(cache_key)
    if cached:
        return cached, 'tier2', {'reason': 'cache_hit', 'ai_count': current_count}

    if _is_account_specific(customer_text):
        return None, 'tier3', {'reason': 'account_specific_question', 'ai_count': current_count}

    context = _get_store_context()
    system_prompt = build_system_prompt(context)

    ai_response, error = _call_anthropic(system_prompt, customer_text)

    if error:
        return None, 'tier3', {'reason': f'ai_api_error: {error}', 'ai_count': current_count}

    if not ai_response:
        return None, 'tier3', {'reason': 'ai_empty_response', 'ai_count': current_count}

    if _should_handoff(ai_response):
        return None, 'tier3', {'reason': 'ai_uncertain', 'ai_response': ai_response[:200], 'ai_count': current_count}

    new_count = _increment_conversation_ai_count(conversation_id)
    cache.set(cache_key, ai_response, timeout=AI_CACHE_TTL)
    return ai_response, 'tier2', {'reason': 'ai_success', 'ai_count': new_count}


def get_ai_system_prompt_text():
    return build_system_prompt(_get_store_context())
