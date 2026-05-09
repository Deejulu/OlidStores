from django.db.models import Sum
from django.core.cache import cache
from .models import Cart, CartItem

def cart_count(request):
    """Get cart item count efficiently, cached per user/session for 30 seconds."""
    count = 0
    if request.user.is_authenticated:
        cache_key = f'cart_count_user_{request.user.pk}'
        count = cache.get(cache_key)
        if count is None:
            result = Cart.objects.filter(user=request.user).aggregate(
                total=Sum('items__quantity')
            )
            count = result['total'] or 0
            cache.set(cache_key, count, 30)
    else:
        # Only query if a session already exists — avoids creating unnecessary sessions
        # for anonymous visitors who never interact with the cart
        session_key = request.session.session_key
        if session_key:
            cache_key = f'cart_count_session_{session_key}'
            count = cache.get(cache_key)
            if count is None:
                result = Cart.objects.filter(session_key=session_key, user=None).aggregate(
                    total=Sum('items__quantity')
                )
                count = result['total'] or 0
                cache.set(cache_key, count, 30)
    return {'cart_count': count}
