from django.db.models import Sum
from .models import Cart, CartItem

def cart_count(request):
    """Get cart item count efficiently using database aggregation"""
    count = 0
    if request.user.is_authenticated:
        # Use aggregate to sum quantities in one query instead of fetching all items
        result = Cart.objects.filter(user=request.user).aggregate(
            total=Sum('items__quantity')
        )
        count = result['total'] or 0
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        result = Cart.objects.filter(session_key=session_key, user=None).aggregate(
            total=Sum('items__quantity')
        )
        count = result['total'] or 0
    return {'cart_count': count}
