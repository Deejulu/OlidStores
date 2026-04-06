from core.models import ContactMessage
from users.models import Feedback
from users.models_notification import Notification
from .forms_notification import NotificationForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from functools import wraps
from .models import DailyMetric
from products.models import Product
from products.forms import ProductForm
from products.models import Category
from orders.models import Order
from django.contrib.auth import get_user_model
from .forms import CategoryForm, OrderUpdateForm, CustomerForm
from core.models import SiteContent, ChatAutoReply
from core.forms import SiteContentForm
from django.contrib import messages

User = get_user_model()

def admin_role_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if getattr(request.user, 'role', None) == 'admin':
            return view_func(request, *args, **kwargs)
        return redirect('core:home')
    return _wrapped_view

# Admin view for contact messages
@admin_role_required
def contact_message_list(request):
    from django.utils import timezone
    from django.urls import reverse
    from core.models import ChatConversation

    # ── Handle POST actions ───────────────────────────────────────────────────
    if request.method == 'POST':
        action    = request.POST.get('action')
        msg_id    = request.POST.get('msg_id')
        open_param = request.POST.get('open', '')
        msg = ContactMessage.objects.filter(id=msg_id).first() if msg_id else None

        if action == 'mark_read' and msg:
            msg.is_read = True
            msg.save()
            messages.success(request, 'Message marked as read.')
        elif action == 'mark_unread' and msg:
            msg.is_read = False
            msg.save()
            messages.info(request, 'Message marked as unread.')
        elif action == 'mark_all_read':
            ContactMessage.objects.filter(is_read=False).update(is_read=True)
            messages.success(request, 'All messages marked as read.')
        elif action == 'delete' and msg:
            msg.delete()
            open_param = ''
            messages.success(request, 'Message deleted.')
        elif action == 'reply' and msg:
            reply_text = request.POST.get('reply_text', '').strip()
            if reply_text:
                msg.admin_reply = reply_text
                msg.replied_at = timezone.now()
                msg.is_read = True
                msg.save()
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    send_mail(
                        subject=f'Re: {msg.subject or "Your message"}',
                        message=f'Hi {msg.name},\n\n{reply_text}\n\n— Support Team',
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                        recipient_list=[msg.email],
                        fail_silently=True,
                    )
                    messages.success(request, f'Reply sent to {msg.email}.')
                except Exception:
                    messages.success(request, 'Reply saved.')
            else:
                messages.error(request, 'Reply cannot be empty.')

        redirect_url = reverse('admin_dashboard:contact_message_list')
        if open_param:
            redirect_url += f'?open={open_param}'
        return redirect(redirect_url)

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ── Fetch base data ───────────────────────────────────────────────────────
    contact_qs = ContactMessage.objects.select_related('user').all()
    all_chats  = list(ChatConversation.objects.prefetch_related('messages').all())

    # ── Stats (always full, unfiltered) ──────────────────────────────────────
    contact_total  = contact_qs.count()
    contact_unread = contact_qs.filter(is_read=False).count()
    contact_today  = contact_qs.filter(created_at__gte=today_start).count()
    chat_total     = len(all_chats)
    chat_unread    = sum(c.unread_admin_count for c in all_chats)
    chat_today     = ChatConversation.objects.filter(created_at__gte=today_start).count()
    total_count    = contact_total + chat_total
    unread_count   = contact_unread + chat_unread
    today_count    = contact_today + chat_today

    # ── Build unified conversation list ──────────────────────────────────────
    tab          = request.GET.get('tab', 'all')
    search_query = request.GET.get('search', '').strip()

    unified = []

    for msg in contact_qs:
        if search_query:
            sq = search_query.lower()
            if not (sq in msg.name.lower() or sq in msg.email.lower()
                    or sq in (msg.subject or '').lower() or sq in msg.message.lower()):
                continue
        last_activity = msg.replied_at or msg.created_at
        unified.append({
            'type': 'contact',
            'pk': msg.pk,
            'name': msg.name,
            'email': msg.email,
            'subject': msg.subject or '',
            'preview': (msg.admin_reply or msg.message)[:100],
            'timestamp': last_activity,
            'is_unread': not msg.is_read,
            'unread_count': 0 if msg.is_read else 1,
            'is_replied': bool(msg.admin_reply),
        })

    for conv in all_chats:
        if search_query:
            sq = search_query.lower()
            if not (sq in conv.display_name.lower()
                    or sq in (conv.display_email or '').lower()
                    or sq in (conv.subject or '').lower()):
                continue
        last_msg      = conv.messages.last()
        last_activity = last_msg.created_at if last_msg else conv.created_at
        preview       = last_msg.message[:100] if last_msg else '(no messages yet)'
        unified.append({
            'type': 'chat',
            'pk': conv.pk,
            'name': conv.display_name,
            'email': conv.display_email or '',
            'subject': conv.subject or '',
            'preview': preview,
            'timestamp': last_activity,
            'is_unread': conv.unread_admin_count > 0,
            'unread_count': conv.unread_admin_count,
            'is_replied': conv.status == 'closed',
        })

    # ── Tab filter ────────────────────────────────────────────────────────────
    if tab == 'unread':
        unified = [u for u in unified if u['is_unread']]
    elif tab == 'today':
        unified = [u for u in unified if u['timestamp'] >= today_start]
    elif tab == 'chat':
        unified = [u for u in unified if u['type'] == 'chat']
    elif tab == 'contact':
        unified = [u for u in unified if u['type'] == 'contact']
    # 'all' → no filter

    # Sort by most recent activity
    unified.sort(key=lambda x: x['timestamp'], reverse=True)

    # ── Selected contact message (right pane) ─────────────────────────────────
    open_param       = request.GET.get('open', '')
    selected_contact = None
    if open_param.startswith('contact-'):
        contact_pk = open_param.split('-', 1)[1]
        selected_contact = ContactMessage.objects.filter(pk=contact_pk).first()
        if selected_contact and not selected_contact.is_read:
            selected_contact.is_read = True
            selected_contact.save()

    context = {
        'unified_conversations': unified,
        'selected_contact': selected_contact,
        'open_param': open_param,
        'search_query': search_query,
        'tab': tab,
        'total_count': total_count,
        'unread_count': unread_count,
        'today_count': today_count,
        'chat_total': chat_total,
        'chat_unread': chat_unread,
    }
    return render(request, 'admin_dashboard/contact_message_list.html', context)


@admin_role_required
def feedback_list(request):
    if request.method == 'POST':
        if 'resolve_id' in request.POST:
            fb_id = request.POST.get('resolve_id')
            fb = Feedback.objects.filter(id=fb_id).first()
            if fb and not fb.is_resolved:
                fb.is_resolved = True
                fb.save()
                messages.success(request, 'Feedback marked as resolved.')
            return redirect('admin_dashboard:feedback_list')
        elif 'unresolve_id' in request.POST:
            fb_id = request.POST.get('unresolve_id')
            fb = Feedback.objects.filter(id=fb_id).first()
            if fb and fb.is_resolved:
                fb.is_resolved = False
                fb.save()
                messages.info(request, 'Feedback marked as open.')
            return redirect('admin_dashboard:feedback_list')
        elif 'resolve_all' in request.POST:
            Feedback.objects.filter(is_resolved=False).update(is_resolved=True)
            messages.success(request, 'All feedback marked as resolved.')
            return redirect('admin_dashboard:feedback_list')
    
    feedbacks = Feedback.objects.select_related('user').all()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        feedbacks = feedbacks.filter(
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    return render(request, 'admin_dashboard/feedback_list.html', {'feedbacks': feedbacks, 'search_query': search_query})

@admin_role_required
def mark_all_notifications_read(request):
    """Quick action to mark all notifications as read/resolved"""
    if request.method == 'POST':
        ContactMessage.objects.filter(is_read=False).update(is_read=True)
        Feedback.objects.filter(is_resolved=False).update(is_resolved=True)
        messages.success(request, 'All notifications cleared!')
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard:dashboard_home'))

@admin_role_required
def notification_list(request):
    notifications = Notification.objects.select_related('user').all()
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notif = form.save(commit=False)
            if not notif.user:
                notif.user = None
            notif.save()
            # Optionally: send notification to all customers if user is None
            return redirect('admin_dashboard:notification_list')
    else:
        form = NotificationForm()
    return render(request, 'admin_dashboard/notification_list.html', {'notifications': notifications, 'form': form})
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from functools import wraps
from products.models import Product
from products.forms import ProductForm
from products.models import Category
from orders.models import Order
from django.contrib.auth import get_user_model
from .forms import CategoryForm, OrderUpdateForm, CustomerForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from functools import wraps
from products.models import Product
from products.forms import ProductForm
from products.models import Category
from orders.models import Order
from django.contrib.auth import get_user_model
from .forms import CategoryForm, OrderUpdateForm, CustomerForm
from core.models import SiteContent
from core.forms import SiteContentForm
from django.contrib import messages

from core.models import SiteContent
from core.forms import SiteContentForm
from django.contrib import messages

User = get_user_model()

def admin_role_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if getattr(request.user, 'role', None) == 'admin':
            return view_func(request, *args, **kwargs)
        return redirect('core:home')
    return _wrapped_view

# ...existing code...


def test_admin_dashboard(request):
	return HttpResponse('Admin Dashboard app is working!')

@admin_role_required
def dashboard_home(request):
    from products.models import Product
    from orders.models import Order
    total_customers = User.objects.filter(role='customer').count()
    total_products  = Product.objects.count()
    total_orders    = Order.objects.count()
    pending_orders  = Order.objects.filter(status='Pending').count()
    return render(request, 'admin_dashboard/dashboard_home.html', {
        'total_customers': total_customers,
        'total_products':  total_products,
        'total_orders':    total_orders,
        'pending_orders':  pending_orders,
    })

@admin_role_required
def admin_profile(request):
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # Site-wide stats
    total_customers = User.objects.filter(role='customer').count()
    total_products  = Product.objects.count()
    active_products = Product.objects.filter(is_editable=True).count()
    low_stock       = Product.objects.filter(stock__lte=5, stock__gt=0).count()
    out_of_stock    = Product.objects.filter(stock=0).count()
    total_orders    = Order.objects.count()
    pending_orders  = Order.objects.filter(status='Pending').count()
    recent_orders   = Order.objects.order_by('-created_at')[:5]

    total_revenue = Order.objects.filter(
        status__in=['Delivered', 'Shipped', 'Processing']
    ).aggregate(total=Sum('total'))['total'] or 0

    revenue_30d = Order.objects.filter(
        status__in=['Delivered', 'Shipped', 'Processing'],
        created_at__date__gte=thirty_days_ago,
    ).aggregate(total=Sum('total'))['total'] or 0

    new_customers_30d = User.objects.filter(
        role='customer', date_joined__date__gte=thirty_days_ago
    ).count()

    orders_30d = Order.objects.filter(created_at__date__gte=thirty_days_ago).count()

    unread_messages   = ContactMessage.objects.filter(is_read=False).count()
    unread_feedback   = Feedback.objects.filter(is_resolved=False).count()

    from core.models import ChatConversation
    open_chats   = ChatConversation.objects.filter(status='open').prefetch_related('messages')
    unread_chats = sum(c.unread_admin_count for c in open_chats)

    return render(request, 'admin_dashboard/admin_profile.html', {
        'total_customers':   total_customers,
        'total_products':    total_products,
        'active_products':   active_products,
        'low_stock':         low_stock,
        'out_of_stock':      out_of_stock,
        'total_orders':      total_orders,
        'pending_orders':    pending_orders,
        'recent_orders':     recent_orders,
        'total_revenue':     total_revenue,
        'revenue_30d':       revenue_30d,
        'new_customers_30d': new_customers_30d,
        'orders_30d':        orders_30d,
        'unread_messages':   unread_messages,
        'unread_feedback':   unread_feedback,
        'unread_chats':      unread_chats,
    })

@admin_role_required
def product_list(request):
    products = Product.objects.all()
    
    # Handle bulk actions
    if request.method == 'POST' and 'bulk_action' in request.POST:
        product_ids = request.POST.getlist('product_ids')
        action = request.POST.get('bulk_action')
        
        if product_ids:
            selected_products = Product.objects.filter(id__in=product_ids)
            
            if action == 'delete':
                count = selected_products.count()
                selected_products.delete()
                messages.success(request, f'Successfully deleted {count} products.')
            
            elif action == 'activate':
                count = selected_products.update(is_editable=True)
                messages.success(request, f'Activated {count} products.')
            
            elif action == 'deactivate':
                count = selected_products.update(is_editable=False)
                messages.success(request, f'Deactivated {count} products.')
            
            elif action == 'stock_zero':
                count = selected_products.update(stock=0)
                messages.success(request, f'Set stock to 0 for {count} products.')

            elif action == 'restock_default':
                # Restock selected products to a sensible default: use reorder_level*2 if available, otherwise 20
                count = 0
                for p in selected_products:
                    if getattr(p, 'reorder_level', None) and p.reorder_level > 0:
                        p.stock = p.reorder_level * 2
                    else:
                        p.stock = 20
                    p.save()
                    count += 1
                messages.success(request, f'Restocked {count} products to default levels.')

            elif action == 'restock_all_zero':
                zero_qs = Product.objects.filter(stock=0)
                count = 0
                for p in zero_qs:
                    if getattr(p, 'reorder_level', None) and p.reorder_level > 0:
                        p.stock = p.reorder_level * 2
                    else:
                        p.stock = 20
                    p.save()
                    count += 1
                messages.success(request, f'Restocked {count} zero-stock products to default levels.')
            
            elif action == 'price_increase':
                try:
                    percentage = float(request.POST.get('price_percentage', 10))
                    for product in selected_products:
                        product.price = product.price * (1 + percentage / 100)
                        product.save()
                    messages.success(request, f'Increased prices by {percentage}% for {selected_products.count()} products.')
                except ValueError:
                    messages.error(request, 'Invalid percentage value.')
            
            elif action == 'price_decrease':
                try:
                    percentage = float(request.POST.get('price_percentage', 10))
                    for product in selected_products:
                        product.price = product.price * (1 - percentage / 100)
                        product.save()
                    messages.success(request, f'Decreased prices by {percentage}% for {selected_products.count()} products.')
                except ValueError:
                    messages.error(request, 'Invalid percentage value.')
        
        return redirect('admin_dashboard:product_list')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    return render(request, 'admin_dashboard/products/product_list.html', {'products': products, 'search_query': search_query})

@admin_role_required
def product_populate_sample(request):
    from django.core.management import call_command
    from django.db import transaction

    try:
        with transaction.atomic():
            call_command('populate_sample')
        messages.success(request, 'Sample categories and products created successfully.')
    except Exception as e:
        messages.error(request, f'Failed to populate sample products: {e}')
    return redirect('admin_dashboard:product_list')

@admin_role_required
def product_create(request):
    from products.models import ProductImage
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            for field in ['image1', 'image2', 'image3']:
                img = form.cleaned_data.get(field)
                if img:
                    ProductImage.objects.create(product=product, image=img)
            return redirect('admin_dashboard:product_list')
    else:
        form = ProductForm()
    return render(request, 'admin_dashboard/products/product_form.html', {'form': form})

@admin_role_required
def product_edit(request, pk):
    from products.models import ProductImage
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            # Remove old images if any new are uploaded
            new_images = [form.cleaned_data.get(f) for f in ['image1', 'image2', 'image3'] if form.cleaned_data.get(f)]
            if new_images:
                ProductImage.objects.filter(product=product).delete()
                for img in new_images:
                    ProductImage.objects.create(product=product, image=img)
            return redirect('admin_dashboard:product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'admin_dashboard/products/product_form.html', {'form': form, 'product': product})

@admin_role_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        return redirect('admin_dashboard:product_list')
    return render(request, 'admin_dashboard/products/product_confirm_delete.html', {'product': product})


@admin_role_required
def product_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_editable = not product.is_editable
        product.save()
    return redirect('admin_dashboard:product_list')


@admin_role_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'admin_dashboard/categories/category_list.html', {'categories': categories})


@admin_role_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard:category_list')
    else:
        form = CategoryForm()
    return render(request, 'admin_dashboard/categories/category_form.html', {'form': form})


@admin_role_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'admin_dashboard/categories/category_form.html', {'form': form})


@admin_role_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('admin_dashboard:category_list')
    return render(request, 'admin_dashboard/categories/category_confirm_delete.html', {'category': category})


@admin_role_required
def category_toggle(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.is_editable = not category.is_editable
        category.save()
    return redirect('admin_dashboard:category_list')


@admin_role_required
def order_list(request):
    all_orders = Order.objects.all()
    
    # Calculate stats from all orders (before filtering)
    total_count = all_orders.count()
    pending_count = all_orders.filter(status='Pending').count()
    processing_count = all_orders.filter(status='Processing').count()
    shipped_count = all_orders.filter(status='Shipped').count()
    delivered_count = all_orders.filter(status='Delivered').count()
    cancelled_count = all_orders.filter(status='Cancelled').count()
    attention_count = pending_count + processing_count
    
    # Handle bulk actions
    if request.method == 'POST' and 'bulk_action' in request.POST:
        order_ids = request.POST.getlist('order_ids')
        action = request.POST.get('bulk_action')
        
        if order_ids:
            from orders.models import PaymentTransaction
            selected_orders = Order.objects.filter(id__in=order_ids)
            
            # Get orders with successful payments (should be protected)
            orders_with_payment = selected_orders.filter(
                paymenttransaction__status='success'
            ).distinct()
            
            # Get orders that can be modified (no successful payment)
            modifiable_orders = selected_orders.exclude(
                paymenttransaction__status='success'
            )
            
            if action == 'mark_processing':
                count = selected_orders.update(status='Processing')
                messages.success(request, f'Marked {count} orders as Processing.')
            
            elif action == 'mark_shipped':
                # set shipped_at timestamp for records being shipped
                from django.utils import timezone as _tz
                count = selected_orders.update(status='Shipped', shipped_at=_tz.now())
                messages.success(request, f'Marked {count} orders as Shipped.')
            
            elif action == 'mark_delivered':
                # set delivered_at timestamp for records being delivered
                from django.utils import timezone as _tz
                count = selected_orders.update(status='Delivered', delivered_at=_tz.now())
                messages.success(request, f'Marked {count} orders as Delivered.')
            
            elif action == 'mark_cancelled':
                # Only cancel orders without successful payment
                protected_count = orders_with_payment.count()
                count = modifiable_orders.update(status='Cancelled')
                messages.success(request, f'Cancelled {count} orders.')
                if protected_count > 0:
                    messages.warning(request, f'{protected_count} orders with confirmed payments cannot be cancelled.')
            
            elif action == 'delete':
                # Only delete orders without successful payment
                protected_count = orders_with_payment.count()
                count = modifiable_orders.count()
                modifiable_orders.delete()
                messages.success(request, f'Deleted {count} orders.')
                if protected_count > 0:
                    messages.warning(request, f'{protected_count} orders with confirmed payments cannot be deleted.')
        
        return redirect('admin_dashboard:order_list')
    
    # Start with all orders for display
    orders = all_orders
    
    # Status filter
    status_filter = request.GET.get('status', '')
    current_filter = status_filter
    
    if status_filter == 'attention':
        orders = orders.filter(status__in=['Pending', 'Processing'])
    elif status_filter in ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']:
        orders = orders.filter(status=status_filter)
    
    # Search filter
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(full_name__icontains=search_query) |
            Q(status__icontains=search_query)
        )

    # Date filter (supports "placed" -> created_at, and "shipped" -> updated_at for shipped/delivered orders)
    from django.utils.dateparse import parse_date
    date_filter = request.GET.get('date', '')
    date_type = request.GET.get('date_type', 'placed')
    if date_filter:
        parsed = parse_date(date_filter)
        if parsed:
            if date_type == 'shipped':
                # Filter by explicit shipped/delivered timestamps (if present)
                from django.db.models import Q
                orders = orders.filter(
                    Q(shipped_at__date=parsed) | Q(delivered_at__date=parsed)
                )
            else:
                orders = orders.filter(created_at__date=parsed)

    # Sort by date (newest/oldest) — defaults to newest
    sort_order = request.GET.get('sort', 'newest')
    if date_type == 'shipped' and sort_order == 'oldest':
        orders = orders.order_by('shipped_at', 'delivered_at', 'created_at')
    elif date_type == 'shipped':
        orders = orders.order_by('-shipped_at', '-delivered_at', '-created_at')
    elif sort_order == 'oldest':
        orders = orders.order_by('created_at')
    else:
        orders = orders.order_by('-created_at')

    context = {
        'orders': orders,
        'search_query': search_query,
        'current_filter': current_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,
        'cancelled_count': cancelled_count,
        'attention_count': attention_count,
        'date_filter': date_filter,
        'date_type': date_type,
        'sort_order': sort_order,
    }
    return render(request, 'admin_dashboard/orders/order_list.html', context)


@admin_role_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    # Check payment method: Paystack or Manual Receipt
    from orders.models import PaymentTransaction
    paystack_payment = PaymentTransaction.objects.filter(
        order=order,
        status='success'
    ).first()
    
    # Determine payment method
    payment_method = None
    if paystack_payment:
        payment_method = 'paystack'
    elif order.receipt:
        payment_method = 'manual'
    
    if request.method == 'POST':
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, 'Order updated successfully.')
            return redirect('admin_dashboard:order_list')
        else:
            # Always redirect after POST to prevent resubmission on Back
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
            return redirect('admin_dashboard:order_detail', pk=pk)
    else:
        form = OrderUpdateForm(instance=order)
    
    return render(request, 'admin_dashboard/orders/order_detail.html', {
        'order': order,
        'form': form,
        'paystack_payment': paystack_payment,
        'payment_method': payment_method,
    })


@admin_role_required
def customer_list(request):
    users = User.objects.all()
    
    # Handle bulk actions
    if request.method == 'POST' and 'bulk_action' in request.POST:
        user_ids = request.POST.getlist('user_ids')
        action = request.POST.get('bulk_action')
        
        if user_ids:
            selected_users = User.objects.filter(id__in=user_ids)
            
            if action == 'suspend':
                count = selected_users.update(is_active=False)
                messages.success(request, f'Suspended {count} user(s).')
            elif action == 'activate':
                count = selected_users.update(is_active=True)
                messages.success(request, f'Activated {count} user(s).')
            elif action == 'delete':
                # Don't delete current admin user
                selected_users = selected_users.exclude(id=request.user.id)
                count = selected_users.count()
                selected_users.delete()
                messages.success(request, f'Deleted {count} user(s).')
        
        return redirect('admin_dashboard:customer_list')
    
    # Filter users
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    return render(request, 'admin_dashboard/customers/customer_list.html', {'users': users, 'search_query': search_query})


@admin_role_required
def add_customer(request):
    from admin_dashboard.forms import AddCustomerForm
    
    if request.method == 'POST':
        form = AddCustomerForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Customer "{user.username}" added successfully!')
            return redirect('admin_dashboard:customer_list')
    else:
        form = AddCustomerForm(initial={'is_active': True, 'role': 'customer'})
    
    return render(request, 'admin_dashboard/customers/add_customer.html', {'form': form})


@admin_role_required
def customer_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    from orders.models import Order, Cart
    from users.models import Address, Profile, Wishlist
    from products.models import Product
    orders = Order.objects.filter(user=user)
    carts = Cart.objects.filter(user=user)
    addresses = Address.objects.filter(user=user)
    profile = Profile.objects.filter(user=user).first()
    wishlist = Wishlist.objects.filter(user=user).first()
    wishlist_products = wishlist.products.all() if wishlist else []
    total_orders = orders.count()
    total_spent = sum([o.total for o in orders])
    last_order = orders.first().created_at if orders.exists() else None
    reg_date = user.date_joined
    last_login = user.last_login
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard:customer_list')
    else:
        form = CustomerForm(instance=user)
    return render(request, 'admin_dashboard/customers/customer_detail.html', {
        'user_obj': user,
        'form': form,
        'orders': orders,
        'carts': carts,
        'addresses': addresses,
        'profile': profile,
        'wishlist_products': wishlist_products,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'last_order': last_order,
        'reg_date': reg_date,
        'last_login': last_login,
    })


@admin_role_required
def analytics_dashboard(request):
    import csv
    from django.db.models import Sum, Count, F
    from orders.models import Order, OrderItem
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from admin_dashboard.models import DailyMetric
    from datetime import timedelta, datetime
    from django.http import HttpResponse
    User = get_user_model()

    # Date range handling (GET params: start, end) - default last 30 days
    try:
        end_date_str = request.GET.get('end')
        start_date_str = request.GET.get('start')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = timezone.now()
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            start_date = end_date - timedelta(days=29)
        # Normalize to day boundaries
        start_dt = timezone.make_aware(datetime.combine(start_date.date(), datetime.min.time())) if hasattr(timezone, 'make_aware') else datetime.combine(start_date.date(), datetime.min.time())
        end_dt = timezone.make_aware(datetime.combine(end_date.date(), datetime.max.time())) if hasattr(timezone, 'make_aware') else datetime.combine(end_date.date(), datetime.max.time())
    except Exception:
        end_dt = timezone.now()
        start_dt = end_dt - timedelta(days=29)

    # Base queryset for completed/processing orders in range
    orders_qs = Order.objects.filter(created_at__range=(start_dt, end_dt))
    completed_orders_qs = orders_qs.filter(status__in=['Processing', 'Shipped', 'Delivered'])

    # Segmentation filters from GET params - APPLY EARLY BEFORE CALCULATIONS
    category_id = request.GET.get('category')
    status_filter = request.GET.get('status')
    cat = None
    if category_id:
        try:
            cat = Category.objects.get(pk=int(category_id))
            orders_qs = orders_qs.filter(items__product__category=cat).distinct()
            completed_orders_qs = completed_orders_qs.filter(items__product__category=cat).distinct()
        except Exception:
            pass
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)
        completed_orders_qs = completed_orders_qs.filter(status=status_filter)

    # High-level metrics
    total_sales = completed_orders_qs.aggregate(total=Sum('total'))['total'] or 0
    order_count = orders_qs.count()
    completed_order_count = completed_orders_qs.count()

    # User analytics
    user_count = User.objects.count()
    new_users = User.objects.filter(date_joined__range=(start_dt, end_dt)).count()

    # Average order value, average items per order
    # Average order value computed safely
    avg_order_value = 0
    if completed_orders_qs.exists():
        total_sales_period = completed_orders_qs.aggregate(total=Sum('total'))['total'] or 0
        avg_order_value = float(total_sales_period) / completed_orders_qs.count() if completed_orders_qs.count() else 0

    # Items per order (use OrderItem)
    avg_items_per_order = 0
    if completed_orders_qs.exists():
        total_items = OrderItem.objects.filter(order__in=completed_orders_qs).aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
        avg_items_per_order = float(total_items) / completed_orders_qs.count() if completed_orders_qs.count() else 0

    # Top products by quantity and by revenue in range
    from products.models import Product, Category
    from django.db.models import DecimalField, ExpressionWrapper
    revenue_expr = ExpressionWrapper(F('orderitem__quantity') * F('orderitem__price'), output_field=DecimalField())
    top_products_qty = (
        Product.objects.filter(orderitem__order__in=completed_orders_qs)
        .annotate(total_qty=Sum('orderitem__quantity'))
        .order_by('-total_qty')[:10]
    )
    top_products_revenue = (
        Product.objects.filter(orderitem__order__in=completed_orders_qs)
        .annotate(revenue=Sum(revenue_expr))
        .order_by('-revenue')[:10]
    )

    # Revenue by category
    cat_revenue_expr = ExpressionWrapper(F('products__orderitem__quantity') * F('products__orderitem__price'), output_field=DecimalField())
    revenue_by_category = (
        Category.objects.filter(products__orderitem__order__in=completed_orders_qs)
        .annotate(revenue=Sum(cat_revenue_expr))
        .order_by('-revenue')
    )

    # Top customers by spend
    top_customers = (
        User.objects.filter(order__in=completed_orders_qs)
        .annotate(spent=Sum('order__total'))
        .order_by('-spent')[:10]
    )

    # Repeat customer rate (lifetime) among users who have ever ordered
    from django.db.models import Q
    users_ever_ordered = User.objects.filter(order__status__in=['Processing', 'Completed']).distinct().count()
    repeat_customers_count = User.objects.annotate(c=Count('order', filter=Q(order__status__in=['Processing', 'Completed']))).filter(c__gt=1).count()
    repeat_rate = round((float(repeat_customers_count) / users_ever_ordered) * 100, 2) if users_ever_ordered else None

    # Conversion: buyers in selected range / total users (proxy)
    buyers_in_range = User.objects.filter(order__in=completed_orders_qs).distinct().count()
    conversion_rate = round((float(buyers_in_range) / user_count) * 100, 2) if user_count else None

    # Cart Abandonment: carts with items but no corresponding order
    from orders.models import Cart
    carts_with_items = Cart.objects.filter(items__isnull=False).distinct().count()
    total_completed_orders = Order.objects.filter(status__in=['Processing', 'Delivered', 'Shipped']).count()
    abandonment_rate = None
    if carts_with_items + total_completed_orders > 0:
        abandonment_rate = round((float(carts_with_items) / (carts_with_items + total_completed_orders)) * 100, 2)

    # Customer Lifetime Value (CLV): Average total spent per customer who has ever ordered
    customers_with_orders = User.objects.filter(order__status__in=['Processing', 'Delivered', 'Shipped']).distinct()
    if customers_with_orders.exists():
        total_all_time_revenue = Order.objects.filter(
            status__in=['Processing', 'Delivered', 'Shipped']
        ).aggregate(total=Sum('total'))['total'] or 0
        clv = round(float(total_all_time_revenue) / customers_with_orders.count(), 2) if customers_with_orders.count() else 0
    else:
        clv = 0

    # Orders by status
    from django.db.models import Count
    orders_by_status = orders_qs.values('status').annotate(count=Count('id')).order_by('-count')

    # Sales & Orders trend based on days in range
    delta = (end_dt.date() - start_dt.date()).days
    sales_trend = []
    orders_trend = []
    labels = []

    # If filters are applied, we must use live calculation
    use_live_calc = bool(category_id or status_filter)
    
    # Try to use precomputed DailyMetric data for the range (only if no filters)
    if not use_live_calc:
        metrics_qs = DailyMetric.objects.filter(date__range=(start_dt.date(), end_dt.date())).order_by('date')
        if metrics_qs.exists() and metrics_qs.count() == delta + 1:
            for m in metrics_qs:
                sales_trend.append(float(m.total_sales))
                orders_trend.append(m.order_count)
                labels.append(m.date.strftime('%Y-%m-%d'))
            use_live_calc = False
        else:
            use_live_calc = True
    
    if use_live_calc:
        # Fallback to live calculation with filters applied
        for i in range(delta, -1, -1):
            day = end_dt - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            day_orders = Order.objects.filter(created_at__range=(day_start, day_end), status__in=['Processing', 'Completed'])
            # Apply category filter if present
            if category_id and cat:
                day_orders = day_orders.filter(items__product__category=cat).distinct()
            # Apply status filter if present
            if status_filter:
                day_orders = day_orders.filter(status=status_filter)
            day_sales = day_orders.aggregate(total=Sum('total'))['total'] or 0
            sales_trend.append(float(day_sales))
            orders_trend.append(day_orders.count())
            labels.append(day.strftime('%Y-%m-%d'))

    # Percentage change vs previous period
    prev_start = start_dt - (end_dt - start_dt) - timedelta(days=1)
    prev_end = start_dt - timedelta(days=1)
    sales_change = None
    
    # If filters are applied, use live calculation for comparison
    if category_id or status_filter:
        prev_orders = Order.objects.filter(created_at__range=(prev_start, prev_end), status__in=['Processing', 'Completed'])
        if category_id and cat:
            prev_orders = prev_orders.filter(items__product__category=cat).distinct()
        if status_filter:
            prev_orders = prev_orders.filter(status=status_filter)
        prev_sales = prev_orders.aggregate(total=Sum('total'))['total'] or 0
    else:
        # Try to get previous period totals from DailyMetric if available for performance
        try:
            prev_metrics = DailyMetric.objects.filter(date__range=(prev_start.date(), prev_end.date())).aggregate(total=Sum('total_sales'))
            prev_sales = prev_metrics['total'] or 0
        except Exception:
            prev_orders = Order.objects.filter(created_at__range=(prev_start, prev_end), status__in=['Processing', 'Completed'])
            prev_sales = prev_orders.aggregate(total=Sum('total'))['total'] or 0
    
    if prev_sales:
        sales_change = round(((float(total_sales) - float(prev_sales)) / float(prev_sales)) * 100, 2)

    # CSV export support
    export = request.GET.get('export')
    if export == 'orders':
        # export orders in range to CSV
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="orders_{start_dt.date()}_{end_dt.date()}.csv"'
        writer = csv.writer(resp)
        writer.writerow(['Order ID', 'User', 'Status', 'Total', 'Created At'])
        for o in orders_qs.order_by('-created_at'):
            writer.writerow([o.id, o.user.username if o.user else 'Guest', o.status, float(o.total), o.created_at])
        return resp
    if export == 'top_products':
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="top_products_{start_dt.date()}_{end_dt.date()}.csv"'
        writer = csv.writer(resp)
        writer.writerow(['Product ID', 'Name', 'Qty Sold', 'Revenue'])
        for p in top_products_revenue:
            writer.writerow([p.id, p.name, getattr(p, 'total_qty', 0), getattr(p, 'revenue', 0)])
        return resp


    context = {
        'total_sales': total_sales,
        'order_count': order_count,
        'completed_order_count': completed_order_count,
        'user_count': user_count,
        'new_users': new_users,
        'avg_order_value': avg_order_value,
        'avg_items_per_order': round(avg_items_per_order, 2),
        'top_products_qty': top_products_qty,
        'top_products_revenue': top_products_revenue,
        'revenue_by_category': revenue_by_category,
        'top_customers': top_customers,
        'orders_by_status': list(orders_by_status),
        'sales_trend': sales_trend,
        'orders_trend': orders_trend,
        'trend_labels': labels,
        'sales_change': sales_change,
        'start_date': start_dt.date(),
        'end_date': end_dt.date(),
        # Quick range helpers
        'quick_start_7': (end_dt - timedelta(days=6)).date(),
        'quick_start_30': (end_dt - timedelta(days=29)).date(),
        'quick_start_90': (end_dt - timedelta(days=89)).date(),
        'today': end_dt.date(),
        'repeat_rate': repeat_rate,
        'buyers_in_range': buyers_in_range,
        'conversion_rate': conversion_rate,
        'abandonment_rate': abandonment_rate,
        'customer_lifetime_value': clv,
        'carts_with_items': carts_with_items,
        # segmentation helpers
        'categories_list': Category.objects.all(),
        'status_choices': [c[0] for c in Order.STATUS_CHOICES],
        'applied_category': cat if category_id else None,
        'applied_status': status_filter,
    }
    return render(request, 'admin_dashboard/analytics.html', context)


@admin_role_required
def compute_daily_metrics_view(request):
    # Trigger the management command to compute daily metrics for last 90 days
    from django.core.management import call_command
    try:
        call_command('compute_daily_metrics', days=90)
        messages.success(request, 'Daily metrics recomputed for last 90 days.')
    except Exception as e:
        messages.error(request, f'Failed to recompute daily metrics: {e}')
    return redirect('admin_dashboard:analytics_dashboard')


@admin_role_required
def generate_sample_data(request):
    """Generate realistic sample orders, customers, and products for analytics testing."""
    import random
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    from orders.models import OrderItem as _OrderItem
    User = get_user_model()
    # Ensure categories and products exist
    if not Category.objects.exists():
        cat_names = ['Clothing', 'Accessories', 'Shoes', 'Sale']
        for n in cat_names:
            Category.objects.create(name=n)
    if not Product.objects.exists():
        cats = list(Category.objects.all())
        for i in range(8):
            Product.objects.create(
                name=f"Sample Product {i+1}",
                description="Sample product for analytics",
                price=round(10 + i * 5, 2),
                stock=20 + i * 5,
                category=random.choice(cats)
            )
    products = list(Product.objects.all())
    # Create sample customers
    for i in range(5):
        username = f"sample_user_{i+1}"
        email = f"{username}@example.com"
        # Ensure sample users are customers (not admin)
        user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'role': 'customer'})
        if created:
            user.set_password('password')
            user.role = 'customer'
            user.save()
        else:
            # If a sample user exists with wrong role, fix it
            if getattr(user, 'role', None) != 'customer':
                user.role = 'customer'
                user.is_staff = False
                user.is_superuser = False
                user.save()
        # Create 1-4 orders for each user across last 60 days
        for oidx in range(random.randint(1, 4)):
            days_ago = random.randint(0, 60)
            created_at = timezone.now() - timedelta(days=days_ago)
            status = random.choices(['Completed', 'Processing', 'Shipped', 'Cancelled'], weights=[50,30,10,10])[0]
            order = Order.objects.create(
                user=user,
                full_name=user.username,
                phone='08000000000',
                email=user.email,
                delivery_address='Sample address',
                delivery_fee=0.00,
                total=0.00,
                status=status,
            )
            # Adjust created_at for older orders
            if days_ago:
                order.created_at = created_at
                order.updated_at = created_at
                order.save()
            # Add 1-3 items
            total = 0
            for ii in range(random.randint(1,3)):
                p = random.choice(products)
                qty = random.randint(1,4)
                price = p.price
                _OrderItem.objects.create(order=order, product=p, quantity=qty, price=price)
                total += float(price) * qty
            order.total = round(total, 2)
            order.save()
    messages.success(request, 'Sample analytics data generated successfully!')
    return redirect('admin_dashboard:analytics_dashboard')


@admin_role_required
def send_analytics_report(request):
    """Send a summary analytics report via email (immediate, for testing)."""
    import io, csv
    from django.core.mail import EmailMessage
    from django.conf import settings
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import F, DecimalField, ExpressionWrapper, Sum

    # Use last 30 days by default
    end_dt = timezone.now()
    start_dt = end_dt - timedelta(days=29)
    orders_qs = Order.objects.filter(created_at__range=(start_dt, end_dt))
    completed_orders_qs = orders_qs.filter(status__in=['Processing', 'Completed'])
    total_sales = completed_orders_qs.aggregate(total=Sum('total'))['total'] or 0
    order_count = orders_qs.count()
    completed_order_count = completed_orders_qs.count()

    body = f"Analytics report for {start_dt.date()} to {end_dt.date()}\n\n"
    body += f"Total sales: ${float(total_sales):.2f}\nOrders: {order_count} (Completed: {completed_order_count})\n"

    # Attach CSV of top products (recompute for range)
    revenue_expr = ExpressionWrapper(F('orderitem__quantity') * F('orderitem__price'), output_field=DecimalField())
    top_products_revenue_local = (
        Product.objects.filter(orderitem__order__in=completed_orders_qs)
        .annotate(revenue=Sum(revenue_expr))
        .order_by('-revenue')[:20]
    )
    top_products_csv = io.StringIO()
    writer = csv.writer(top_products_csv)
    writer.writerow(['Product ID', 'Name', 'Qty Sold', 'Revenue'])
    for p in top_products_revenue_local:
        writer.writerow([p.id, p.name, getattr(p, 'total_qty', 0), getattr(p, 'revenue', 0)])
    top_products_csv.seek(0)

    # Attach orders CSV
    orders_csv = io.StringIO()
    writer = csv.writer(orders_csv)
    writer.writerow(['Order ID', 'User', 'Status', 'Total', 'Created At'])
    for o in orders_qs.order_by('-created_at'):
        writer.writerow([o.id, o.user.username if o.user else 'Guest', o.status, float(o.total), o.created_at])
    orders_csv.seek(0)

    # Recipients: ADMINS or current user
    recipients = [email for name, email in getattr(settings, 'ADMINS', [])]
    if not recipients:
        recipients = [request.user.email]

    email = EmailMessage(subject=f"Analytics Report {start_dt.date()} - {end_dt.date()}", body=body, to=recipients)
    email.attach(f'top_products_{start_dt.date()}_{end_dt.date()}.csv', top_products_csv.getvalue(), 'text/csv')
    email.attach(f'orders_{start_dt.date()}_{end_dt.date()}.csv', orders_csv.getvalue(), 'text/csv')
    email.send(fail_silently=True)
    messages.success(request, 'Analytics report sent (check email or console).')
    return redirect('admin_dashboard:analytics_dashboard')


@admin_role_required
def content_manage(request):
    # Get or create content objects for each section
    from django.forms import modelformset_factory
    from core.models import BannerImage, HeroImage
    from core.forms import BannerImageForm, HeroImageForm
    BannerImageFormSet = modelformset_factory(BannerImage, form=BannerImageForm, extra=0, can_delete=True)
    HeroImageFormSet = modelformset_factory(HeroImage, form=HeroImageForm, extra=0, can_delete=True)

    about, _ = SiteContent.objects.get_or_create(key='about')
    contact, _ = SiteContent.objects.get_or_create(key='contact')
    banner, _ = SiteContent.objects.get_or_create(key='homepage_banner')
    checkout, _ = SiteContent.objects.get_or_create(key='checkout')
    # New sections
    site_settings, _ = SiteContent.objects.get_or_create(key='site_settings')
    faq, _ = SiteContent.objects.get_or_create(key='faq')
    privacy, _ = SiteContent.objects.get_or_create(key='privacy')
    terms, _ = SiteContent.objects.get_or_create(key='terms')
    
    banner_qs = BannerImage.objects.all().order_by('order', '-created_at')
    hero_qs = HeroImage.objects.all().order_by('order', '-created_at')

    if request.method == 'POST':
        from django.http import JsonResponse
        about_form = SiteContentForm(request.POST, prefix='about', instance=about)
        contact_form = SiteContentForm(request.POST, prefix='contact', instance=contact)
        banner_form = SiteContentForm(request.POST, prefix='banner', instance=banner)
        checkout_form = SiteContentForm(request.POST, prefix='checkout', instance=checkout)
        site_settings_form = SiteContentForm(request.POST, request.FILES, prefix='site_settings', instance=site_settings)
        faq_form = SiteContentForm(request.POST, prefix='faq', instance=faq)
        privacy_form = SiteContentForm(request.POST, prefix='privacy', instance=privacy)
        terms_form = SiteContentForm(request.POST, prefix='terms', instance=terms)
        formset = BannerImageFormSet(request.POST, request.FILES, queryset=banner_qs, prefix='bimgs')
        hero_formset = HeroImageFormSet(request.POST, request.FILES, queryset=hero_qs, prefix='heros')
        # New images upload (multiple)
        new_files = request.FILES.getlist('new_banner_images')
        new_hero_files = request.FILES.getlist('new_hero_images')
        # Dynamic validation: validate only forms present in POST
        prefixes = list(request.POST.keys())
        present_about = any(k.startswith('about-') for k in prefixes)
        present_contact = any(k.startswith('contact-') for k in prefixes)
        present_banner = any(k.startswith('banner-') for k in prefixes)
        present_checkout = any(k.startswith('checkout-') for k in prefixes)
        present_site_settings = any(k.startswith('site_settings-') for k in prefixes)
        present_faq = any(k.startswith('faq-') for k in prefixes)
        present_privacy = any(k.startswith('privacy-') for k in prefixes)
        present_terms = any(k.startswith('terms-') for k in prefixes)
        present_bimgs = any(k.startswith('bimgs-') for k in prefixes)
        present_heros = any(k.startswith('heros-') for k in prefixes)

        # Validate only present forms/formsets (default to True if not present)
        valid = True
        validation_errors = {}
        if present_about and not about_form.is_valid():
            valid = False
            validation_errors['about'] = about_form.errors
        if present_contact and not contact_form.is_valid():
            valid = False
            validation_errors['contact'] = contact_form.errors
        if present_banner and not banner_form.is_valid():
            valid = False
            validation_errors['banner'] = banner_form.errors
        if present_checkout and not checkout_form.is_valid():
            valid = False
            validation_errors['checkout'] = checkout_form.errors
        if present_site_settings and not site_settings_form.is_valid():
            valid = False
            validation_errors['site_settings'] = site_settings_form.errors
        if present_faq and not faq_form.is_valid():
            valid = False
            validation_errors['faq'] = faq_form.errors
        if present_privacy and not privacy_form.is_valid():
            valid = False
            validation_errors['privacy'] = privacy_form.errors
        if present_terms and not terms_form.is_valid():
            valid = False
            validation_errors['terms'] = terms_form.errors
        if present_bimgs and not formset.is_valid():
            valid = False
            validation_errors['bimgs'] = formset.errors
        if present_heros and not hero_formset.is_valid():
            valid = False
            validation_errors['heros'] = hero_formset.errors

        import logging
        logger = logging.getLogger(__name__)

        if valid:
            if present_about:
                about_form.save()
            if present_contact:
                contact_form.save()
            if present_banner:
                banner_form.save()
            if present_checkout:
                checkout_form.save()
            if present_site_settings:
                site_settings_form.save()
            if present_faq:
                faq_form.save()
            if present_privacy:
                privacy_form.save()
            if present_terms:
                terms_form.save()
            # Process formsets (updates/deletes)
            saved_banners = formset.save()
            saved_heros = hero_formset.save()
            # Add new banner files
            created_banners = []
            for idx, f in enumerate(new_files):
                b = BannerImage.objects.create(image=f, title=f.name, order=999)
                created_banners.append({'id': b.id, 'order': b.order})
            # Add new hero files
            created_heros = []
            for idx, f in enumerate(new_hero_files):
                h = HeroImage.objects.create(image=f, title=f.name, order=999)
                created_heros.append({'id': h.id, 'order': h.order})

            # Fallback: ensure numeric checkout fields are persisted when present in POST
            try:
                from decimal import Decimal
                if request.POST.get('checkout-delivery_fee_24h') is not None:
                    checkout.delivery_fee_24h = Decimal(request.POST.get('checkout-delivery_fee_24h') or '0')
                if request.POST.get('checkout-delivery_fee_2d') is not None:
                    checkout.delivery_fee_2d = Decimal(request.POST.get('checkout-delivery_fee_2d') or '0')
                # Only save if any value changed or instance is new
                checkout.save()
            except Exception:
                # non-fatal: rely on standard form save above
                pass

            messages.success(request, 'Site content, banner images and hero images updated successfully!')

            # If AJAX request, return JSON with details to update UI
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                banners_out = [{'index': i, 'id': obj.id, 'order': obj.order} for i, obj in enumerate(saved_banners)]
                heros_out = [{'index': i, 'id': obj.id, 'order': obj.order} for i, obj in enumerate(saved_heros)]
                # append created ones at the end
                for cb in created_banners:
                    banners_out.append({'index': None, 'id': cb['id'], 'order': cb['order']})
                for ch in created_heros:
                    heros_out.append({'index': None, 'id': ch['id'], 'order': ch['order']})
                return JsonResponse({'success': True, 'message': 'Saved successfully', 'banners': banners_out, 'heros': heros_out})

            return redirect('admin_dashboard:content_manage')
        else:
            logger.warning('Content manage validation failed: %s', validation_errors)
            # If AJAX and forms invalid, return structured errors for UI
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': validation_errors}, status=400)
            # Non-AJAX: surface errors to user
            messages.error(request, 'One or more sections failed validation. Please check the highlighted errors.')
    else:
        about_form = SiteContentForm(prefix='about', instance=about)
        contact_form = SiteContentForm(prefix='contact', instance=contact)
        banner_form = SiteContentForm(prefix='banner', instance=banner)
        checkout_form = SiteContentForm(prefix='checkout', instance=checkout)
        site_settings_form = SiteContentForm(prefix='site_settings', instance=site_settings)
        faq_form = SiteContentForm(prefix='faq', instance=faq)
        privacy_form = SiteContentForm(prefix='privacy', instance=privacy)
        terms_form = SiteContentForm(prefix='terms', instance=terms)
        formset = BannerImageFormSet(queryset=banner_qs, prefix='bimgs')
        hero_formset = HeroImageFormSet(queryset=hero_qs, prefix='heros')

    return render(request, 'admin_dashboard/content_manage.html', {
        'about_form': about_form,
        'contact_form': contact_form,
        'banner_form': banner_form,
        'checkout_form': checkout_form,
        'site_settings_form': site_settings_form,
        'faq_form': faq_form,
        'privacy_form': privacy_form,
        'terms_form': terms_form,
        'banner_formset': formset,
        'hero_formset': hero_formset,
    })


@admin_role_required
def pending_orders_view(request):
    """Dedicated page for managing orders that need attention - Pending and Processing status"""
    from orders.models import Order
    from django.db.models import Q
    
    # Get all orders that need attention
    pending_orders = Order.objects.filter(
        Q(status='Pending') | Q(status='Processing')
    ).select_related('user').prefetch_related('items__product', 'items__variant').order_by('created_at')
    
    # Calculate urgency (orders older than 24 hours are urgent)
    from django.utils import timezone
    from datetime import timedelta
    urgent_threshold = timezone.now() - timedelta(hours=24)
    
    urgent_orders = pending_orders.filter(created_at__lt=urgent_threshold)
    recent_orders = pending_orders.filter(created_at__gte=urgent_threshold)
    
    # Statistics
    total_pending = pending_orders.count()
    urgent_count = urgent_orders.count()
    pending_payment_count = pending_orders.filter(status='Pending').count()
    processing_count = pending_orders.filter(status='Processing').count()
    
    # Handle bulk actions
    if request.method == 'POST':
        action = request.POST.get('action')
        order_ids = request.POST.getlist('order_ids')
        
        if order_ids and action:
            from orders.models import PaymentTransaction
            orders_to_update = Order.objects.filter(id__in=order_ids)
            
            # Get orders with successful payments (should be protected from cancellation)
            orders_with_payment = orders_to_update.filter(
                paymenttransaction__status='success'
            ).distinct()
            
            # Get orders that can be modified (no successful payment)
            modifiable_orders = orders_to_update.exclude(
                paymenttransaction__status='success'
            )
            
            if action == 'mark_processing':
                count = orders_to_update.update(status='Processing')
                messages.success(request, f'{count} order(s) marked as Processing.')
            elif action == 'mark_shipped':
                count = orders_to_update.update(status='Shipped')
                messages.success(request, f'{count} order(s) marked as Shipped.')
            elif action == 'mark_delivered':
                count = orders_to_update.update(status='Delivered')
                messages.success(request, f'{count} order(s) marked as Delivered.')
            elif action == 'mark_cancelled':
                # Only cancel orders without successful payment
                protected_count = orders_with_payment.count()
                count = modifiable_orders.update(status='Cancelled')
                if count > 0:
                    messages.warning(request, f'{count} order(s) cancelled.')
                if protected_count > 0:
                    messages.error(request, f'{protected_count} order(s) with confirmed payments cannot be cancelled.')
            
            return redirect('admin_dashboard:pending_orders')
    
    context = {
        'urgent_orders': urgent_orders,
        'recent_orders': recent_orders,
        'total_pending': total_pending,
        'urgent_count': urgent_count,
        'pending_payment_count': pending_payment_count,
        'processing_count': processing_count,
        'urgent_threshold_hours': 24,
    }
    
    return render(request, 'admin_dashboard/orders/pending_orders.html', context)


@admin_role_required
def payments_dashboard_view(request):
    """Dashboard for viewing all Paystack payment transactions"""
    from orders.models import PaymentTransaction, Order
    from django.db.models import Sum, Count, Q
    from django.utils import timezone
    from datetime import timedelta
    
    # Get all payment transactions
    transactions = PaymentTransaction.objects.select_related('order').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        transactions = transactions.filter(status__icontains=status_filter)
    
    # Search by reference, order ID, or customer name
    search_query = request.GET.get('search', '')
    if search_query:
        transactions = transactions.filter(
            Q(reference__icontains=search_query) |
            Q(order__id__icontains=search_query) |
            Q(order__full_name__icontains=search_query) |
            Q(order__email__icontains=search_query) |
            Q(order__phone__icontains=search_query)
        )
    
    # Date range filter
    date_filter = request.GET.get('date_range', '30')  # Default 30 days
    if date_filter == '7':
        start_date = timezone.now() - timedelta(days=7)
        transactions = transactions.filter(created_at__gte=start_date)
    elif date_filter == '30':
        start_date = timezone.now() - timedelta(days=30)
        transactions = transactions.filter(created_at__gte=start_date)
    elif date_filter == '90':
        start_date = timezone.now() - timedelta(days=90)
        transactions = transactions.filter(created_at__gte=start_date)
    
    # Statistics
    total_transactions = transactions.count()
    successful_transactions = transactions.filter(status='success').count()
    failed_transactions = transactions.exclude(status='success').count()
    total_amount = transactions.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent activity (last 24 hours)
    last_24h = timezone.now() - timedelta(hours=24)
    recent_count = transactions.filter(created_at__gte=last_24h).count()
    recent_amount = transactions.filter(created_at__gte=last_24h, status='success').aggregate(total=Sum('amount'))['total'] or 0
    
    # Get unreconciled payments (payments without orders or orders still pending)
    unreconciled = transactions.filter(
        Q(order__isnull=True) | Q(order__status='Pending')
    ).filter(status='success')
    
    context = {
        'transactions': transactions[:100],  # Limit to 100 for performance
        'total_transactions': total_transactions,
        'successful_transactions': successful_transactions,
        'failed_transactions': failed_transactions,
        'total_amount': total_amount,
        'recent_count': recent_count,
        'recent_amount': recent_amount,
        'unreconciled_count': unreconciled.count(),
        'unreconciled': unreconciled[:20],
        'status_filter': status_filter,
        'search_query': search_query,
        'date_filter': date_filter,
    }
    
    return render(request, 'admin_dashboard/payments/payments_dashboard.html', context)


# ── Admin live chat management ────────────────────────────────────────────────

@admin_role_required
def chat_conversation_list(request):
    """Admin view: list all chat conversations."""
    from core.models import ChatConversation
    from django.db.models import Count, Q

    convs = ChatConversation.objects.prefetch_related('messages').all()

    status_filter = request.GET.get('status', '')
    if status_filter in ('open', 'closed'):
        convs = convs.filter(status=status_filter)

    open_count   = ChatConversation.objects.filter(status='open').count()
    closed_count = ChatConversation.objects.filter(status='closed').count()
    # Total unread customer messages across all conversations
    total_unread = sum(c.unread_admin_count for c in ChatConversation.objects.prefetch_related('messages'))

    context = {
        'conversations': convs,
        'status_filter': status_filter,
        'open_count': open_count,
        'closed_count': closed_count,
        'total_unread': total_unread,
    }
    return render(request, 'admin_dashboard/chat_list.html', context)


def _get_chat_suggestion(message_text):
    """
    Return (response_text, question_label) for the best-matching active ChatAutoReply rule,
    or (None, None) if nothing matches well enough.
    """
    lower_text = message_text.lower()
    rules = ChatAutoReply.objects.filter(is_active=True).order_by('-priority')
    best_rule = None
    best_score = 0
    for rule in rules:
        score = sum(len(kw.split()) for kw in rule.keyword_list() if kw in lower_text)
        if score > best_score:
            best_score = score
            best_rule = rule
    if best_rule and best_score >= 1:
        return best_rule.response, best_rule.question
    return None, None


@admin_role_required
def chat_conversation_detail(request, pk):
    """Admin view: view a conversation and post a reply."""
    from core.models import ChatConversation, ChatMessage
    from django.http import JsonResponse

    conv = get_object_or_404(ChatConversation, pk=pk)

    # Mark all customer messages as read when admin opens conversation
    conv.messages.filter(sender_type='customer', is_read=False).update(is_read=True)

    if request.method == 'POST':
        if 'reply_text' in request.POST:
            reply_text = request.POST.get('reply_text', '').strip()
            if reply_text:
                ChatMessage.objects.create(
                    conversation=conv,
                    sender_type='admin',
                    sender_name='Support Team',
                    message=reply_text,
                )
                conv.save()
                messages.success(request, 'Reply sent.')
        elif 'close_conv' in request.POST:
            conv.status = 'closed'
            conv.save()
            messages.info(request, 'Conversation closed.')
        elif 'reopen_conv' in request.POST:
            conv.status = 'open'
            conv.save()
            messages.success(request, 'Conversation reopened.')
        return redirect('admin_dashboard:chat_detail', pk=pk)

    # Suggest an auto-reply only when the last message is from the customer (unanswered)
    last_msg = conv.messages.last()
    suggested_reply = None
    suggested_question = None
    if last_msg and last_msg.sender_type == 'customer':
        suggested_reply, suggested_question = _get_chat_suggestion(last_msg.message)

    context = {
        'conversation': conv,
        'chat_messages': conv.messages.all(),
        'suggested_reply': suggested_reply,
        'suggested_question': suggested_question,
    }
    return render(request, 'admin_dashboard/chat_detail.html', context)


@admin_role_required
def chat_admin_poll(request, pk):
    """Admin AJAX polling endpoint to get new messages since ?after=<ISO>."""
    from core.models import ChatConversation
    from django.http import JsonResponse

    conv = get_object_or_404(ChatConversation, pk=pk)

    after = request.GET.get('after', '')
    msgs_qs = conv.messages.all()
    if after:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(after)
        if dt:
            msgs_qs = msgs_qs.filter(created_at__gt=dt)

    conv.messages.filter(sender_type='customer', is_read=False).update(is_read=True)

    # Provide a suggestion for the latest unanswered customer message
    suggested_reply = None
    suggested_question = None
    new_msgs = list(msgs_qs)
    if new_msgs and any(m.sender_type == 'customer' for m in new_msgs):
        last_customer = conv.messages.filter(sender_type='customer').last()
        last_overall  = conv.messages.last()
        if last_customer and last_overall and last_customer.pk == last_overall.pk:
            suggested_reply, suggested_question = _get_chat_suggestion(last_customer.message)

    return JsonResponse({
        'success': True,
        'status': conv.status,
        'suggested_reply': suggested_reply,
        'suggested_question': suggested_question,
        'messages': [
            {
                'id': m.pk,
                'sender_type': m.sender_type,
                'sender_name': m.sender_name,
                'message': m.message,
                'created_at': m.created_at.isoformat(),
            }
            for m in new_msgs
        ],
    })


# ── Auto-reply FAQ management ─────────────────────────────────────────────────

def _seed_auto_replies():
    """Pre-populate the ChatAutoReply table with common e-commerce FAQ rules."""
    samples = [
        # Orders
        {
            'category': 'orders', 'priority': 20,
            'question': 'Where is my order?',
            'keywords': 'track,where is my order,order status,delivery status,when will it arrive,where my order',
            'response': (
                'You can track your order by visiting My Account → Orders. '
                'If your order was placed recently, please allow 24 hours for tracking to update. '
                'Need further help? Please share your order number!'
            ),
        },
        {
            'category': 'orders', 'priority': 15,
            'question': 'How long does delivery take?',
            'keywords': 'how long,delivery time,shipping time,when will i receive,estimated delivery,how many days',
            'response': (
                'Standard delivery takes 2–5 business days. Express (24h) is available at checkout. '
                'You will receive a tracking notification once your order is dispatched!'
            ),
        },
        {
            'category': 'orders', 'priority': 15,
            'question': 'Can I cancel my order?',
            'keywords': 'cancel order,cancel my order,stop my order',
            'response': (
                'Orders can be cancelled within 1 hour of placing them. After that, the order may already be processing. '
                'Please contact us immediately with your order number and we will do our best to help!'
            ),
        },
        # Payment
        {
            'category': 'payment', 'priority': 20,
            'question': 'What payment methods are accepted?',
            'keywords': 'payment,pay,card,visa,mastercard,paypal,how to pay,payment method',
            'response': (
                'We accept Visa, Mastercard, PayPal, and bank transfer. All payments are secured with SSL encryption. '
                'If you are having trouble at checkout, try a different browser or contact your bank.'
            ),
        },
        {
            'category': 'payment', 'priority': 25,
            'question': 'Payment failed / error at checkout',
            'keywords': 'payment failed,payment error,checkout error,card declined,transaction failed',
            'response': (
                "Sorry to hear that! Common causes: incorrect card details, insufficient funds, or bank restrictions on online payments. "
                "Please double-check your details or try a different card. If the issue persists, contact us and we will assist you directly."
            ),
        },
        # Returns
        {
            'category': 'returns', 'priority': 20,
            'question': 'How do I return an item?',
            'keywords': 'return,refund,send back,exchange,wrong item,damaged item',
            'response': (
                'We have a 14-day return policy. To start a return: go to My Account → Orders → Return Item. '
                'Items must be unused and in original packaging. Refunds are processed within 3–5 business days of receiving the return.'
            ),
        },
        {
            'category': 'returns', 'priority': 15,
            'question': 'When will I get my refund?',
            'keywords': 'refund,money back,when refund,refund status',
            'response': (
                'Refunds are processed within 3–5 business days after we receive your return. '
                'The money will appear in your account within 5–10 business days depending on your bank. '
                'If it has been longer, please contact us with your order number!'
            ),
        },
        # Products
        {
            'category': 'products', 'priority': 15,
            'question': 'Is this product in stock?',
            'keywords': 'in stock,available,out of stock,stock,do you have',
            'response': (
                'You can check product availability directly on the product page. '
                'If an item is out of stock, you can join the waitlist using the "Notify Me" button. '
                'We restock popular items regularly!'
            ),
        },
        {
            'category': 'products', 'priority': 15,
            'question': 'What size should I order?',
            'keywords': 'size,sizing,what size,size guide,measurements,fit',
            'response': (
                'Please check our Size Guide (available on each product page) for detailed measurements. '
                'If you are between sizes, we generally recommend sizing up. '
                'Feel free to share your measurements and I can help you choose!'
            ),
        },
        # Account
        {
            'category': 'account', 'priority': 20,
            'question': 'I forgot my password',
            'keywords': 'forgot password,reset password,cant login,cannot login,password reset',
            'response': (
                'No problem! Click "Forgot Password" on the login page and we will send a reset link to your email. '
                'Check your spam folder if you do not see it within a few minutes.'
            ),
        },
        # General
        {
            'category': 'general', 'priority': 5,
            'question': 'How can I contact support?',
            'keywords': 'contact,speak to someone,human,agent,support,help',
            'response': (
                'You are chatting with us right now! \U0001f60a You can also reach us by email at support@olidstores.com. '
                'We typically respond within a few hours during business hours (Mon\u2013Fri, 9am\u20136pm).'
            ),
        },
        {
            'category': 'general', 'priority': 5,
            'question': 'Opening hours',
            'keywords': 'hours,open,business hours,when are you open,working hours',
            'response': (
                'Our team is available Monday to Friday, 9am\u20136pm. '
                'We also monitor messages on weekends and will get back to you as soon as possible!'
            ),
        },
    ]
    for s in samples:
        ChatAutoReply.objects.get_or_create(question=s['question'], defaults=s)


@admin_role_required
def auto_reply_manage(request):
    """Admin CRUD page for managing FAQ auto-reply rules."""
    if request.method == 'POST':
        action  = request.POST.get('action')
        rule_id = request.POST.get('rule_id')

        if action == 'delete' and rule_id:
            ChatAutoReply.objects.filter(pk=rule_id).delete()
            messages.success(request, 'Rule deleted.')

        elif action == 'toggle' and rule_id:
            rule = ChatAutoReply.objects.filter(pk=rule_id).first()
            if rule:
                rule.is_active = not rule.is_active
                rule.save()

        elif action in ('add', 'edit'):
            pk   = request.POST.get('rule_id') if action == 'edit' else None
            rule = ChatAutoReply.objects.filter(pk=pk).first() if pk else ChatAutoReply()
            rule.category = request.POST.get('category', 'general')
            rule.question = request.POST.get('question', '').strip()
            rule.keywords = request.POST.get('keywords', '').strip()
            rule.response = request.POST.get('response', '').strip()
            try:
                rule.priority = int(request.POST.get('priority', 10))
            except (ValueError, TypeError):
                rule.priority = 10
            if action == 'add':
                rule.is_active = True
            if rule.question and rule.keywords and rule.response:
                rule.save()
                messages.success(request, 'Rule saved.')
            else:
                messages.error(request, 'Question, keywords, and response are all required.')

        return redirect('admin_dashboard:auto_reply_manage')

    rules = ChatAutoReply.objects.all()
    if not rules.exists():
        _seed_auto_replies()
        rules = ChatAutoReply.objects.all()

    context = {
        'rules': rules,
        'categories': ChatAutoReply.CATEGORY_CHOICES,
    }
    return render(request, 'admin_dashboard/auto_reply_manage.html', context)
