from .models import Cart, CartItem

def cart_count(request):
    count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key, user=None).first()
    if cart:
        count = sum(item.quantity for item in cart.items.all())
    return {'cart_count': count}
