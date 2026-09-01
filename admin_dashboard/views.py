from users.models import Feedback
from users.models_notification import Notification
from .forms_notification import NotificationForm
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from functools import wraps
import logging
from .models import DailyMetric
from products.models import Product
from products.forms import ProductForm
from products.models import Category
from orders.models import Order
from django.contrib.auth import get_user_model
from .forms import CategoryForm, OrderUpdateForm, CustomerForm
from core.models import SiteContent, ChatAutoReply, ChatMessage
from core.forms import SiteContentForm
from django.contrib import messages
from django.db.models import Sum, Count, Q

User = get_user_model()

# Security logger for admin access
security_logger = logging.getLogger('security')

def admin_role_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if getattr(request.user, 'role', None) == 'admin':
            return view_func(request, *args, **kwargs)
        # Log unauthorized access attempt
        security_logger.warning(
            'Unauthorized admin access attempt: user=%s, role=%s, ip=%s, path=%s',
            request.user.username if request.user.is_authenticated else 'anonymous',
            getattr(request.user, 'role', 'none'),
            request.META.get('REMOTE_ADDR', 'unknown'),
            request.path
        )
        return redirect('core:home')
    return _wrapped_view
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
        ChatMessage.objects.filter(sender_type='customer', is_read=False).update(is_read=True)
        Feedback.objects.filter(is_resolved=False).update(is_resolved=True)
        # Clear admin notification cache so counts update immediately
        if request.user.is_authenticated:
            cache.delete(f'admin_notifications_{request.user.pk}')
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

# ...existing code...


def test_admin_dashboard(request):
	return HttpResponse('Admin Dashboard app is working!')

@admin_role_required
def dashboard_home(request):
    from products.models import Product
    from orders.models import Order
    from django.conf import settings
    total_customers = User.objects.filter(role='customer').count()
    total_products  = Product.objects.count()
    total_orders    = Order.objects.count()
    pending_orders  = Order.objects.filter(status='Pending').count()
    return render(request, 'admin_dashboard/dashboard_home.html', {
        'total_customers': total_customers,
        'total_products':  total_products,
        'total_orders':    total_orders,
        'pending_orders':  pending_orders,
        'debug':           settings.DEBUG,
    })

@admin_role_required
def admin_profile(request):
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

    unread_feedback   = Feedback.objects.filter(is_resolved=False).count()

    # Single aggregate query instead of N+1 loop with unread_admin_count property
    from core.models import ChatConversation
    unread_chats = ChatMessage.objects.filter(
        conversation__status='open',
        sender_type='customer',
        is_read=False
    ).count()

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
    from django.conf import settings
    from django.http import HttpResponseForbidden

    # Only allow in development/debug mode
    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

    if request.method != 'POST':
        return redirect('admin_dashboard:product_list')
    try:
        with transaction.atomic():
            call_command('populate_sample')
        messages.success(request, 'Sample categories and products created successfully.')
    except Exception as e:
        messages.error(request, f'Failed to populate sample products: {e}')
    return redirect('admin_dashboard:product_list')

@admin_role_required
def product_remove_sample(request):
    from products.models import Product
    from django.conf import settings
    from django.http import HttpResponseForbidden

    # Only allow in development/debug mode
    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

    if request.method != 'POST':
        return redirect('admin_dashboard:product_list')
    try:
        # Only delete sample products, never real products
        deleted_count, _ = Product.objects.filter(is_sample=True).delete()
        messages.success(request, f'Removed {deleted_count} sample products.')
    except Exception as e:
        messages.error(request, f'Failed to remove sample products: {e}')
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
def product_bulk_create(request):
    """Create up to 10 products at once under a chosen category."""
    from products.forms import BulkProductForm
    from django.forms import formset_factory

    BulkFormSet = formset_factory(BulkProductForm, extra=0, min_num=0, max_num=100, validate_min=False)

    categories = Category.objects.all().order_by('name')
    category_id = request.POST.get('category') or request.GET.get('category')
    selected_category = None
    if category_id:
        selected_category = get_object_or_404(Category, pk=category_id)

    if request.method == 'POST':
        formset = BulkFormSet(request.POST, request.FILES)
        if not selected_category:
            messages.error(request, 'Please select a category first.')
        elif formset.is_valid():
            saved, skipped = 0, 0
            for form in formset:
                name = form.cleaned_data.get('name', '').strip()
                if not name:
                    skipped += 1
                    continue
                product = Product(
                    name=name,
                    description=form.cleaned_data.get('description', ''),
                    price=form.cleaned_data['price'],
                    stock=form.cleaned_data.get('stock') or 0,
                    reorder_level=form.cleaned_data.get('reorder_level') or 5,
                    category=selected_category,
                    image=form.cleaned_data.get('image') or None,
                )
                product.save()
                saved += 1
            if saved:
                messages.success(
                    request,
                    f'{saved} product{"s" if saved != 1 else ""} added to "{selected_category.name}" successfully.'
                    + (f' ({skipped} empty row{"s" if skipped != 1 else ""} skipped.)' if skipped else '')
                )
                return redirect('admin_dashboard:product_list')
            else:
                messages.error(request, 'No products were saved. Please fill in at least one row.')
        else:
            messages.error(request, 'Please fix the errors highlighted below.')
    else:
        formset = BulkFormSet()

    return render(request, 'admin_dashboard/products/product_bulk_create.html', {
        'formset': formset,
        'categories': categories,
        'selected_category': selected_category,
    })


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
            messages.success(request, f'"{product.name}" has been updated successfully.')
            return redirect('admin_dashboard:product_edit', pk=product.pk)
        else:
            messages.error(request, 'Please fix the errors below before saving.')
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
def category_populate_sample(request):
    from django.core.management import call_command
    from django.db import transaction
    from django.conf import settings
    from django.http import HttpResponseForbidden

    # Only allow in development/debug mode
    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

    if request.method != 'POST':
        return redirect('admin_dashboard:category_list')
    try:
        with transaction.atomic():
            call_command('populate_sample')
        messages.success(request, 'Sample categories and products created successfully.')
    except Exception as e:
        messages.error(request, f'Failed to populate sample categories: {e}')
    return redirect('admin_dashboard:category_list')


@admin_role_required
def category_remove_sample(request):
    from django.conf import settings
    from django.http import HttpResponseForbidden

    # Only allow in development/debug mode
    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

    if request.method != 'POST':
        return redirect('admin_dashboard:category_list')
    try:
        # Only delete sample categories (those created by sample data tool)
        from products.models import Category, Product
        # First delete sample products, then sample categories
        Product.objects.filter(is_sample=True).delete()
        # Only delete categories that have no remaining products (all their products were samples)
        deleted_count, _ = Category.objects.filter(products__isnull=True).delete()
        messages.success(request, f'Removed sample data. Categories with real products were preserved.')
    except Exception as e:
        messages.error(request, f'Failed to remove sample categories: {e}')
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
                # Soft delete orders instead of hard delete (preserves audit trail and allows stock reversal)
                for order in modifiable_orders:
                    order.soft_delete()
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
        old_status = order.status
        old_notes = order.notes
        old_delivery_fee = str(order.delivery_fee)
        form = OrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            # --- Audit trail ---
            from .models import AdminAuditLog
            changes = {}
            if order.status != old_status:
                changes['status'] = [old_status, order.status]
            if order.notes != old_notes:
                changes['notes'] = [old_notes, order.notes]
            if str(order.delivery_fee) != old_delivery_fee:
                changes['delivery_fee'] = [old_delivery_fee, str(order.delivery_fee)]
            if changes:
                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                AdminAuditLog.objects.create(
                    admin_user=request.user,
                    action=AdminAuditLog.ACTION_UPDATE,
                    model_name='Order',
                    object_id=str(order.pk),
                    object_repr=str(order),
                    changes=changes,
                    ip_address=ip or None,
                )
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

    from .models import AdminAuditLog
    audit_logs = AdminAuditLog.objects.filter(model_name='Order', object_id=str(pk)).select_related('admin_user')[:20]
    return render(request, 'admin_dashboard/orders/order_detail.html', {
        'order': order,
        'form': form,
        'paystack_payment': paystack_payment,
        'payment_method': payment_method,
        'audit_logs': audit_logs,
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
    from users.models import OTPVerification
    from users.otp_utils import send_email_otp
    
    if request.method == 'POST':
        form = AddCustomerForm(request.POST)
        if form.is_valid():
            user = form.save()
            raw_password = form.cleaned_data['password']
            
            # Create and send OTP for email verification
            try:
                otp = OTPVerification.create_otp(
                    otp_type='email',
                    email=user.email,
                    user=user,
                    expiry_minutes=30
                )
                
                # Send OTP via email (or show in console if DEBUG mode)
                success, error_msg = send_email_otp(user.email, otp.otp_code, purpose='email_verification')
                
                if not success:
                    messages.error(
                        request,
                        f'Failed to send verification code: {error_msg}. '
                        f'Please check email configuration or enable DEBUG mode.'
                    )
                    return redirect('admin_dashboard:customer_list')
                
                # Store user ID in session for OTP verification
                request.session['pending_customer_id'] = user.id
                request.session['pending_customer_email'] = user.email
                
                # Store credentials in session for admin to download
                request.session['admin_credentials_username'] = user.username
                request.session['admin_credentials_account_id'] = user.account_id
                request.session['admin_credentials_password'] = raw_password
                request.session['admin_credentials_email'] = user.email
                
                messages.info(
                    request, 
                    f'Customer "{user.username}" created! OTP sent to {user.email}. Please verify to complete setup.'
                )
                return redirect('admin_dashboard:admin_credentials')
            except Exception as e:
                # Still create the customer even if OTP sending fails
                messages.warning(
                    request,
                    f'Customer "{user.username}" created, but OTP email failed to send. '
                    f'Error: {str(e)}'
                )
                return redirect('admin_dashboard:customer_list')
    else:
        form = AddCustomerForm(initial={'is_active': True, 'role': 'customer'})
    
    return render(request, 'admin_dashboard/customers/add_customer.html', {'form': form})


@admin_role_required
def admin_credentials(request):
    """One-time page for admin to download customer credentials after creation."""
    username = request.session.get('admin_credentials_username')
    account_id = request.session.get('admin_credentials_account_id')
    password = request.session.get('admin_credentials_password')
    email = request.session.get('admin_credentials_email')
    
    if not username or not password:
        messages.error(request, "No pending credentials found.")
        return redirect('admin_dashboard:customer_list')
    
    # Get security questions for this user
    from users.models import SecurityAnswer
    security_answers = SecurityAnswer.objects.filter(user__username=username).select_related('question')
    recovery_questions = [sa.question.question_text for sa in security_answers]
    
    response = render(request, 'admin_dashboard/customers/admin_credentials.html', {
        'username': username,
        'account_id': account_id,
        'password': password,
        'email': email,
        'recovery_questions': recovery_questions,
    })
    
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@admin_role_required
def admin_credentials_download(request):
    """Download customer credentials as a text file."""
    username = request.session.get('admin_credentials_username')
    account_id = request.session.get('admin_credentials_account_id')
    password = request.session.get('admin_credentials_password')
    email = request.session.get('admin_credentials_email')
    
    if not username or not password:
        return redirect('admin_dashboard:customer_list')
    
    from users.models import SecurityAnswer
    security_answers = SecurityAnswer.objects.filter(user__username=username).select_related('question')
    recovery_questions = [sa.question.question_text for sa in security_answers]
    
    content = f"""Olid Stores Customer Credentials
============================
Username:      {username}
Account ID:    {account_id}
Email:         {email}
Password:      {password}

Account Recovery Questions:
"""
    for i, q in enumerate(recovery_questions, 1):
        content += f"{i}. {q}\n"
    
    content += """
============================
IMPORTANT: Keep this file secure and do not share it with anyone.
"""
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="credentials-{username}.txt"'
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    # Clear credentials from session after download
    for key in ['admin_credentials_username', 'admin_credentials_account_id', 
                'admin_credentials_password', 'admin_credentials_email']:
        request.session.pop(key, None)
    
    return response


@admin_role_required
def verify_customer_otp(request):
    """Admin verifies the OTP for newly created customer"""
    from users.models import OTPVerification
    from users.otp_utils import send_email_otp
    from django.utils import timezone
    
    # Get customer info from session
    customer_id = request.session.get('pending_customer_id')
    customer_email = request.session.get('pending_customer_email')
    
    if not customer_id or not customer_email:
        messages.error(request, 'No pending customer verification found.')
        return redirect('admin_dashboard:customer_list')
    
    try:
        customer = User.objects.get(id=customer_id)
    except User.DoesNotExist:
        messages.error(request, 'Customer not found.')
        del request.session['pending_customer_id']
        del request.session['pending_customer_email']
        return redirect('admin_dashboard:customer_list')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle resend OTP
        if action == 'resend':
            try:
                otp = OTPVerification.create_otp(
                    otp_type='email',
                    email=customer.email,
                    user=customer,
                    expiry_minutes=30
                )
                
                # Send OTP via email (or show in console if DEBUG mode)
                success, error_msg = send_email_otp(customer.email, otp.otp_code, purpose='email_verification')
                
                if not success:
                    messages.error(request, f'Failed to resend OTP: {error_msg}')
                    return redirect('admin_dashboard:verify_customer_otp')
                
                messages.success(request, f'New OTP sent to {customer.email}')
            except Exception as e:
                messages.error(request, f'Failed to resend OTP: {str(e)}')
            return redirect('admin_dashboard:verify_customer_otp')
        
        # Handle OTP verification
        else:
            otp_code = request.POST.get('otp_code', '').strip()
            
            if not otp_code:
                messages.error(request, 'Please enter the OTP code.')
                return redirect('admin_dashboard:verify_customer_otp')
            
            try:
                # Find the OTP
                otp = OTPVerification.objects.filter(
                    email=customer.email,
                    otp_type='email',
                    is_verified=False
                ).order_by('-created_at').first()
                
                if not otp:
                    messages.error(request, 'No OTP found. Please request a new one.')
                    return redirect('admin_dashboard:verify_customer_otp')
                
                # Check if expired
                if otp.expires_at < timezone.now():
                    messages.error(request, 'OTP has expired. Please request a new one.')
                    return redirect('admin_dashboard:verify_customer_otp')
                
                # Verify OTP - CRITICAL: verify() returns (bool, message) tuple
                is_valid, verify_message = otp.verify(otp_code)
                
                if is_valid:
                    # Mark email as verified
                    customer.email_verified = True
                    customer.save()
                    
                    messages.success(
                        request, 
                        f'✓ Customer "{customer.username}" verified successfully! '
                        f'They can now log in with full access.'
                    )
                    
                    # Clear session
                    del request.session['pending_customer_id']
                    del request.session['pending_customer_email']
                    
                    return redirect('admin_dashboard:customer_list')
                else:
                    messages.error(request, f'Invalid OTP: {verify_message}')
                    return redirect('admin_dashboard:verify_customer_otp')
                    
            except Exception as e:
                messages.error(request, f'Verification failed: {str(e)}')
                return redirect('admin_dashboard:verify_customer_otp')
    
    # GET request - show verification form
    context = {
        'customer': customer,
        'customer_email': customer_email,
    }
    return render(request, 'admin_dashboard/customers/verify_otp.html', context)


@admin_role_required
def customer_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    from orders.models import Order, Cart
    from users.models import Address, Profile, Wishlist
    from products.models import Product
    orders = Order.objects.filter(user=user).order_by('-created_at')
    carts = Cart.objects.filter(user=user)
    addresses = Address.objects.filter(user=user)
    profile = Profile.objects.filter(user=user).first()
    wishlist = Wishlist.objects.filter(user=user).first()
    wishlist_products = wishlist.products.select_related('category').prefetch_related('images', 'variants') if wishlist else []
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
    from django.db.models import Sum, Count, F, Q
    from orders.models import Order, OrderItem
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from admin_dashboard.models import DailyMetric
    from datetime import timedelta, datetime
    from django.http import HttpResponse
    from django.db.models import DecimalField, ExpressionWrapper
    from products.models import Product, Category
    User = get_user_model()

    # Date range handling (GET params: start, end) - default last 90 days
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
            start_date = end_date - timedelta(days=89)
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

    # Compute all aggregations in a single query for completed orders
    completed_aggs = completed_orders_qs.aggregate(
        total_sales=Sum('total'),
        order_count=Count('id'),
        total_items=Sum('items__quantity'),
    )
    total_sales = completed_aggs['total_sales'] or 0
    completed_order_count = completed_aggs['order_count'] or 0
    total_items_sum = completed_aggs['total_items'] or 0

    # Order count (all statuses)
    order_count = orders_qs.count()

    # Average order value and items per order (reuse computed values)
    avg_order_value = float(total_sales) / completed_order_count if completed_order_count else 0
    avg_items_per_order = float(total_items_sum) / completed_order_count if completed_order_count else 0

    # User analytics - combine into fewer queries
    user_count = User.objects.count()
    new_users = User.objects.filter(date_joined__range=(start_dt, end_dt)).count()

    # Top products by quantity and by revenue in range
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

    # Buyers in range (for conversion rate)
    buyers_in_range = User.objects.filter(order__in=completed_orders_qs).distinct().count()
    conversion_rate = round((float(buyers_in_range) / user_count) * 100, 2) if user_count else None

    # Repeat customer rate and CLV - combine queries using lifetime aggregates
    lifetime_aggs = Order.objects.filter(
        status__in=['Processing', 'Delivered', 'Shipped']
    ).aggregate(
        total_revenue=Sum('total'),
        total_buyers=Count('user', distinct=True),
    )
    total_all_time_revenue = lifetime_aggs['total_revenue'] or 0
    total_buyers_count = lifetime_aggs['total_buyers'] or 0

    # Repeat customers: users with more than 1 completed order
    repeat_customers_count = User.objects.annotate(
        c=Count('order', filter=Q(order__status__in=['Processing', 'Completed', 'Shipped', 'Delivered']))
    ).filter(c__gt=1).count()
    users_ever_ordered = total_buyers_count
    repeat_rate = round((float(repeat_customers_count) / users_ever_ordered) * 100, 2) if users_ever_ordered else None

    # Customer Lifetime Value (CLV)
    clv = round(float(total_all_time_revenue) / total_buyers_count, 2) if total_buyers_count else 0

    # Cart Abandonment: carts with items but no corresponding order
    from orders.models import Cart
    carts_with_items = Cart.objects.filter(items__isnull=False).distinct().count()
    total_completed_orders = total_buyers_count  # Use already computed value
    abandonment_rate = None
    if carts_with_items + total_completed_orders > 0:
        abandonment_rate = round((float(carts_with_items) / (carts_with_items + total_completed_orders)) * 100, 2)

    # Orders by status
    orders_by_status = orders_qs.values('status').annotate(count=Count('id')).order_by('-count')

    # Sales & Orders trend - optimized with single GROUP BY query
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
        # Optimized: Use single GROUP BY query instead of looping per day
        from django.db.models.functions import TruncDate
        trend_data = (
            Order.objects.filter(created_at__range=(start_dt, end_dt))
            .filter(status__in=['Processing', 'Completed', 'Shipped', 'Delivered'])
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                daily_sales=Sum('total'),
                daily_orders=Count('id'),
            )
            .order_by('day')
        )
        # Build a lookup dict for O(1) access
        trend_lookup = {item['day']: item for item in trend_data}
        
        for i in range(delta, -1, -1):
            day = end_dt - timedelta(days=i)
            day_date = day.date()
            labels.append(day_date.strftime('%Y-%m-%d'))
            day_data = trend_lookup.get(day_date)
            sales_trend.append(float(day_data['daily_sales']) if day_data else 0)
            orders_trend.append(day_data['daily_orders'] if day_data else 0)

    # Percentage change vs previous period
    prev_start = start_dt - (end_dt - start_dt) - timedelta(days=1)
    prev_end = start_dt - timedelta(days=1)
    sales_change = None
    
    # If filters are applied, use live calculation for comparison
    if category_id or status_filter:
        prev_orders = Order.objects.filter(created_at__range=(prev_start, prev_end), status__in=['Processing', 'Completed', 'Shipped', 'Delivered'])
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
            prev_orders = Order.objects.filter(created_at__range=(prev_start, prev_end), status__in=['Processing', 'Completed', 'Shipped', 'Delivered'])
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
    from django.conf import settings
    from django.http import HttpResponseForbidden

    # Only allow in development/debug mode
    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

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
    body += f"Total sales: ₦{float(total_sales):,.2f}\nOrders: {order_count} (Completed: {completed_order_count})\n"

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

            # Immediately clear cached site content so changes show on the live site right away
            from django.core.cache import cache
            for _cache_key in ['about', 'contact', 'homepage_banner', 'checkout', 'site_settings', 'faq', 'privacy', 'terms']:
                cache.delete(f'site_content_{_cache_key}')
            cache.delete('site_content_announcement')
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


@admin_role_required
def payment_detail_view(request, reference):
    """View detailed information about a specific payment transaction"""
    from orders.models import PaymentTransaction
    from django.shortcuts import get_object_or_404
    
    transaction = get_object_or_404(PaymentTransaction, reference=reference)
    
    # Get related order details if available
    order = transaction.order
    
    context = {
        'transaction': transaction,
        'order': order,
        'page_title': f'Payment Details - {reference}',
    }
    
    return render(request, 'admin_dashboard/payments/payment_detail.html', context)


@admin_role_required
def payment_print_slip(request, reference):
    """Generate printable payment slip"""
    from orders.models import PaymentTransaction
    from django.shortcuts import get_object_or_404
    
    transaction = get_object_or_404(PaymentTransaction, reference=reference)
    order = transaction.order
    
    context = {
        'transaction': transaction,
        'order': order,
    }
    
    return render(request, 'admin_dashboard/payments/payment_slip.html', context)


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


@admin_role_required
def populate_sample_data_full(request):
    """Unified sample data population: categories, products, customers, orders, payments."""
    import random
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.conf import settings
    from django.http import HttpResponseForbidden
    from orders.models import Order, OrderItem, PaymentTransaction

    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

    if request.method != 'POST':
        return redirect('admin_dashboard:dashboard_home')

    User = get_user_model()
    summary = {}

    try:
        with transaction.atomic():
            # 1. Categories and Products (inline the management command logic)
            from products.models import Category, Product
            from django.utils.text import slugify as _slugify

            CATALOG = {
                'Electronics': [
                    ('Wireless Earbuds', 'True wireless earbuds with active noise cancellation and 24-hour battery life.', 35, 150),
                    ('Bluetooth Speaker', 'Portable waterproof speaker with 360° rich bass sound.', 45, 120),
                    ('USB-C Hub', '7-in-1 USB-C hub with HDMI, SD card, and 3 USB-A ports.', 28, 80),
                    ('Mechanical Keyboard', 'Compact tenkeyless keyboard with RGB backlight and tactile switches.', 75, 60),
                    ('Webcam HD', '1080p webcam with built-in noise-cancelling microphone for video calls.', 55, 90),
                    ('Laptop Stand', 'Adjustable aluminium laptop stand for ergonomic desk use.', 32, 100),
                    ('Solar Charger', '20W foldable solar panel charger compatible with all USB devices.', 48, 70),
                    ('Smart Plug', 'Wi-Fi enabled smart plug with energy monitoring and voice control.', 18, 150),
                    ('Rechargeable Fan', 'Portable desk fan with 5000mAh rechargeable battery and 3 speeds.', 25, 110),
                    ('LED Desk Lamp', 'Touch-controlled LED lamp with 5 colour temperatures and USB charging port.', 38, 95),
                    ('Portable Power Bank', '20000mAh power bank with dual USB-C fast charging output.', 42, 130),
                    ('Wireless Mouse', 'Ergonomic silent wireless mouse with 2.4GHz nano receiver.', 22, 140),
                    ('Smart Watch', 'Fitness smartwatch with heart rate monitor, GPS, and 7-day battery.', 89, 75),
                    ('Action Camera', '4K action camera with waterproof case, wide-angle lens, and image stabilisation.', 65, 70),
                    ('Portable Projector', 'Mini LED projector with 200-lumen output, HDMI and USB inputs.', 95, 55),
                ],
                'Fashion': [
                    ('Classic White T-Shirt', 'Premium 100% cotton crew-neck tee, perfect for everyday wear.', 12, 200),
                    ('Slim-Fit Denim Jeans', 'Modern slim-fit jeans crafted from stretch denim for all-day comfort.', 38, 150),
                    ('Leather Sneakers', 'Minimalist leather sneakers with cushioned insole and rubber sole.', 65, 100),
                    ('Canvas Backpack', 'Durable canvas backpack with laptop sleeve and multiple pockets.', 45, 120),
                    ('Sunglasses UV400', 'Polarised sunglasses with full UV400 protection and lightweight frame.', 28, 180),
                    ('Summer Floral Dress', 'Lightweight floral wrap dress, ideal for warm weather occasions.', 35, 130),
                    ('Leather Belt', 'Genuine leather reversible belt available in black and brown.', 22, 160),
                    ('Knit Beanie', 'Soft ribbed-knit beanie hat, one size fits all.', 14, 200),
                    ('Chinos Trouser', 'Smart casual stretch chinos available in multiple colours.', 42, 140),
                    ('Puffer Jacket', 'Lightweight water-resistant puffer jacket with packable design.', 78, 90),
                    ('Polo Shirt', 'Classic polo shirt made from breathable piqué cotton.', 24, 170),
                    ('Ankle Boots', 'Chelsea-style ankle boots with elastic side panels and block heel.', 72, 85),
                    ('Hoodie Sweatshirt', 'Fleece-lined pullover hoodie with kangaroo pocket.', 34, 160),
                    ('Crossbody Bag', 'Compact vegan leather crossbody bag with adjustable strap.', 39, 110),
                ],
                'Home Appliances': [
                    ('Air Fryer', '4-litre digital air fryer with 8 preset cooking modes and timer.', 85, 70),
                    ('Electric Kettle', '1.7L stainless steel cordless kettle with rapid-boil technology.', 32, 110),
                    ('Stand Blender', '1000W high-speed blender with 6-blade assembly and 1.5L jug.', 58, 80),
                    ('Rice Cooker', '1.8L digital rice cooker with steamer basket and keep-warm function.', 44, 95),
                    ('Microwave Oven', '20L solo microwave with 5 power levels and defrost setting.', 95, 55),
                    ('Sandwich Toaster', 'Non-stick sandwich maker with cool-touch handle and indicator light.', 26, 120),
                    ('Handheld Vacuum', 'Cordless handheld vacuum with HEPA filter and 20-minute runtime.', 48, 85),
                    ('Iron Box', '2200W steam iron with self-cleaning function and anti-drip system.', 36, 100),
                    ('Electric Kettle Mini', '0.5L travel-size kettle with dual voltage support (110V/220V).', 22, 130),
                    ('Dish Drying Rack', 'Stainless steel two-tier dish drying rack with drip tray.', 28, 140),
                    ('Ceiling Fan Remote', 'Universal ceiling fan remote control kit with timer function.', 18, 160),
                    ('Water Purifier Jug', '3.5L pitcher with activated carbon filter, removes 99% of chlorine.', 35, 110),
                    ('Electric Can Opener', 'Cordless automatic electric can opener, safe edge technology.', 20, 120),
                ],
                'Cosmetics': [
                    ('Vitamin C Serum', 'Brightening 20% vitamin C face serum with hyaluronic acid.', 24, 150),
                    ('Moisturising Sunscreen SPF50', 'Lightweight SPF50 daily sunscreen with moisturising formula.', 18, 180),
                    ('Matte Lipstick', 'Long-wear matte lipstick in 12 rich shades, hydrating formula.', 12, 200),
                    ('Face Wash Gel', 'Gentle foaming gel cleanser for oily and combination skin.', 14, 190),
                    ('Eyeshadow Palette', '18-shade neutral eyeshadow palette with matte and shimmer finishes.', 28, 140),
                    ('Hair Growth Oil', 'Castor and argan oil blend for scalp treatment and hair growth.', 20, 165),
                    ('Collagen Face Mask', 'Pack of 5 hydrogel collagen sheet masks for intensive hydration.', 16, 210),
                    ('BB Cream', 'Tinted moisturiser with SPF30 and buildable medium coverage.', 22, 170),
                    ('Nail Polish Set', 'Set of 10 chip-resistant nail polishes in trending seasonal colours.', 18, 155),
                    ('Under Eye Patches', '60-piece gold collagen under-eye patches to reduce puffiness.', 15, 180),
                    ('Setting Spray', 'Long-lasting makeup setting spray for up to 16-hour wear.', 17, 160),
                    ('Beard Balm', 'Natural conditioning beard balm with shea butter and cedarwood oil.', 14, 130),
                    ('Body Scrub', 'Coffee and coconut exfoliating body scrub for smooth, glowing skin.', 16, 145),
                ],
                'Books': [
                    ('Atomic Habits', "James Clear's guide to building good habits and breaking bad ones.", 14, 100),
                    ('Rich Dad Poor Dad', "Robert Kiyosaki's personal finance classic on building wealth.", 12, 120),
                    ('The Alchemist', "Paulo Coelho's beloved novel about following your personal legend.", 11, 130),
                    ('Think and Grow Rich', "Napoleon Hill's timeless principles of success and achievement.", 11, 115),
                    ('Ikigai', 'Japanese concept guide to finding purpose and living a longer life.', 13, 110),
                    ('The 48 Laws of Power', "Robert Greene's definitive guide to power, strategy and influence.", 15, 95),
                    ('Sapiens', "Yuval Noah Harari's sweeping history of humankind.", 16, 90),
                    ('Mindset', "Carol Dweck's research on the power of believing you can improve.", 13, 105),
                    ('Deep Work', "Cal Newport's rules for focused success in a distracted world.", 14, 100),
                    ('The Psychology of Money', "Morgan Housel's timeless lessons on wealth, greed, and happiness.", 13, 110),
                    ("Can't Hurt Me", "David Goggins' memoir about overcoming adversity and self-discipline.", 15, 95),
                    ('Start With Why', "Simon Sinek's exploration of what makes great leaders inspire action.", 13, 105),
                    ('Zero to One', "Peter Thiel's notes on startups and building the future.", 14, 90),
                ],
                'Sports': [
                    ('Yoga Mat', 'Non-slip 6mm thick TPE yoga mat with carry strap and alignment lines.', 28, 110),
                    ('Resistance Bands Set', 'Set of 5 latex resistance bands ranging from 5lb to 50lb.', 22, 130),
                    ('Jump Rope Speed', 'Ball-bearing speed jump rope with adjustable cable and foam handles.', 14, 160),
                    ('Gym Gloves', 'Padded weightlifting gloves with wrist support and anti-slip grip.', 18, 150),
                    ('Running Shoes', 'Lightweight mesh running shoes with responsive foam sole.', 58, 90),
                    ('Cycling Helmet', 'Aerodynamic road cycling helmet with 18 ventilation channels.', 45, 75),
                    ('Football', 'FIFA-quality match football, size 5, durable PU leather casing.', 28, 120),
                    ('Swimming Goggles', 'Anti-fog UV-protected swimming goggles with adjustable strap.', 16, 140),
                    ('Dumbbell Pair 5kg', 'Pair of rubber hex dumbbells, 5kg each, non-roll design.', 35, 100),
                    ('Sports Bottle 1L', 'BPA-free 1-litre sports water bottle with flip-cap and carry loop.', 12, 200),
                    ('Foam Roller', '33cm high-density EVA foam roller for muscle recovery and massage.', 20, 135),
                    ('Tennis Racket', 'Aluminium frame beginner tennis racket with grip tape included.', 38, 80),
                    ('Skipping Board', 'Wooden balance board for core training and coordination exercises.', 32, 90),
                ],
                'Toys': [
                    ('LEGO Classic Brick Set', '500-piece classic LEGO brick set for creative free-building play.', 38, 85),
                    ('Remote Control Car', 'High-speed 1:16 scale RC car with 2.4GHz control and 30-min battery.', 45, 75),
                    ('Kids Art Set', '120-piece art and craft kit including crayons, paints, and brushes.', 22, 100),
                    ('Stuffed Teddy Bear', 'Soft plush teddy bear, 45cm, hypoallergenic filling, machine washable.', 16, 150),
                    ('Wooden Puzzle 100pc', '100-piece jigsaw puzzle with vibrant wildlife illustration for ages 5+.', 14, 120),
                    ('Play Kitchen Set', 'Realistic pretend-play kitchen set with 25 accessories included.', 55, 60),
                    ('Magnetic Drawing Board', 'Mess-free magnetic drawing and writing tablet for ages 3+.', 18, 130),
                    ('Bubble Machine', 'Automatic electric bubble machine producing 500+ bubbles per minute.', 24, 110),
                    ('Building Blocks 60pc', 'Soft foam building blocks in 6 shapes and 8 colours for toddlers.', 20, 125),
                    ('Kids Walkie Talkies', 'Pair of durable walkie talkies with 3km range and torch function.', 28, 90),
                    ('Play-Doh Modelling Set', '10-can modelling compound set with tools and activity cards.', 18, 140),
                    ('Toy Doctor Kit', '20-piece toy doctor playset with stethoscope and carry case.', 22, 100),
                    ('Dinosaur Figure Set', 'Set of 12 realistically painted dinosaur figurines, ages 3+.', 26, 105),
                ],
                'Furniture': [
                    ('Ergonomic Office Chair', 'Adjustable lumbar support office chair with breathable mesh back.', 120, 40),
                    ('Folding Study Desk', 'Space-saving folding desk with cable management and storage shelf.', 95, 50),
                    ('Bedside Table', 'Minimalist bedside table with drawer and open shelf, easy assembly.', 65, 60),
                    ('Bookshelf 5-Tier', 'Freestanding 5-tier open bookshelf in rustic brown finish.', 85, 45),
                    ('TV Console Unit', 'Modern floating TV unit with two drawers for cable organisation.', 110, 35),
                    ('Dining Chair Set x2', 'Set of 2 padded dining chairs in linen fabric with wooden legs.', 88, 50),
                    ('Plastic Storage Cabinet', '4-drawer plastic storage cabinet for office or bedroom use.', 48, 75),
                    ('Wardrobe 2-Door', 'Sliding 2-door wardrobe with hanging rail and 2 shelves.', 145, 30),
                    ('Coffee Table', 'Round glass-top coffee table with chrome base, 90cm diameter.', 98, 40),
                    ('Wall Floating Shelf', 'Set of 3 floating wall shelves in oak veneer finish.', 32, 95),
                    ('Shoe Rack 4-Tier', 'Metal 4-tier shoe rack holding up to 20 pairs, rust-resistant.', 28, 110),
                    ('Bean Bag Chair', 'Extra-large indoor bean bag with EPS filling and waterproof cover.', 55, 65),
                    ('Standing Desk Converter', 'Height-adjustable desk converter, converts any desk to standing.', 78, 45),
                ],
                'Gaming': [
                    ('Gaming Headset', '7.1 surround sound gaming headset with noise-cancelling microphone.', 55, 80),
                    ('Gaming Controller', 'Wired USB gamepad compatible with PC, PS3, and Android devices.', 32, 100),
                    ('Gaming Mouse Pad XL', 'Extended 90×40cm mouse pad with non-slip rubber base.', 18, 150),
                    ('Gaming Chair', 'Racing-style gaming chair with lumbar pillow and reclining backrest.', 130, 35),
                    ('Capture Card', 'USB 3.0 game capture card for HD 1080p60 streaming and recording.', 48, 70),
                    ('PC Gaming Fan', '120mm ARGB case fan with PWM control and daisy-chain connector.', 14, 120),
                    ('LED Strip Lights', '5-metre smart RGB LED strip with app control and music sync mode.', 22, 140),
                    ('Gaming Desk', 'Carbon fibre-texture gaming desk with cup holder and monitor stand.', 115, 40),
                    ('Steering Wheel', 'USB racing steering wheel with foot pedals for PC and consoles.', 72, 55),
                    ('VR Headset', 'Standalone VR headset with 6DoF tracking and built-in speakers.', 95, 45),
                    ('Mechanical Gaming Keyboard', 'Full-size mechanical keyboard with RGB per-key lighting and blue switches.', 68, 70),
                    ('Gaming Router', 'Wi-Fi 6 gaming router with QoS, low latency, and MU-MIMO support.', 89, 50),
                    ('Memory Card 256GB', 'High-speed 256GB microSDXC UHS-I card for game storage and transfers.', 28, 130),
                ],
            }

            # Ensure all categories exist (marked as sample)
            cat_names = list(CATALOG.keys())
            existing_cats = set(Category.objects.filter(name__in=cat_names).values_list('name', flat=True))
            new_cats = [Category(name=n, slug=_slugify(n), is_sample=True) for n in cat_names if n not in existing_cats]
            if new_cats:
                Category.objects.bulk_create(new_cats)
            # Mark all catalog categories as sample
            Category.objects.filter(name__in=cat_names, is_sample=False).update(is_sample=True)

            cat_objects = {c.name: c for c in Category.objects.filter(name__in=cat_names)}

            # Only delete existing sample products, never real products
            Product.objects.filter(is_sample=True).delete()

            # Build products
            to_create = []
            seen_slugs = set()
            for cat_name, products in CATALOG.items():
                category = cat_objects[cat_name]
                for name, description, base_price, base_stock in products:
                    price = round(base_price * random.uniform(0.9, 1.1), 2)
                    stock = random.randint(max(1, base_stock - 20), base_stock + 20)
                    base_slug = _slugify(name)
                    slug = base_slug
                    i = 1
                    while slug in seen_slugs:
                        slug = f'{base_slug}-{i}'
                        i += 1
                    seen_slugs.add(slug)
                    to_create.append(Product(
                        name=name, description=description, price=price,
                        stock=stock, category=category, slug=slug, is_sample=True,
                    ))
            Product.objects.bulk_create(to_create)

            cat_count = Category.objects.filter(is_sample=True).count()
            prod_count = Product.objects.filter(is_sample=True).count()
            summary['categories'] = cat_count
            summary['products'] = prod_count

            # 2. Sample Customers
            sample_customers = []
            customer_names = [
                ('Adaobi Nwosu', 'adaobi.sample@example.com'),
                ('Chukwuemeka Okafor', 'emeka.sample@example.com'),
                ('Fatima Bello', 'fatima.sample@example.com'),
                ('Tunde Bakare', 'tunde.sample@example.com'),
                ('Ngozi Eze', 'ngozi.sample@example.com'),
                ('Ibrahim Musa', 'ibrahim.sample@example.com'),
                ('Funke Adeyemi', 'funke.sample@example.com'),
                ('Chioma Okonkwo', 'chioma.sample@example.com'),
                ('Emeka Ibrahim', 'emeka.i.sample@example.com'),
                ('Aisha Mohammed', 'aisha.sample@example.com'),
                ('Oluwaseun Adebayo', 'seun.sample@example.com'),
                ('Amina Yusuf', 'amina.sample@example.com'),
                ('Chinedu Eze', 'chinedu.sample@example.com'),
                ('Halima Abubakar', 'halima.sample@example.com'),
                ('Yemi Oladipo', 'yemi.sample@example.com'),
            ]
            for name, email in customer_names:
                username = email.split('@')[0]
                first_name = name.split()[0]
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'role': 'customer',
                        'is_sample': True,
                    }
                )
                if created:
                    user.set_password('samplepass123')
                    user.is_sample = True
                    user.save()
                else:
                    if not user.is_sample:
                        user.is_sample = True
                        user.save()
                sample_customers.append(user)
            summary['customers'] = len(sample_customers)

            # 3. Sample Orders with OrderItems and PaymentTransactions
            products = list(Product.objects.filter(is_sample=True))
            if not products:
                products = list(Product.objects.all()[:10])

            statuses = ['Completed', 'Completed', 'Completed', 'Completed', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
            payment_methods = ['paystack', 'paystack', 'pay_on_delivery', 'manual']

            order_count = 0
            payment_count = 0
            item_count = 0

            # Collect orders to create (bulk_create for performance)
            orders_to_create = []
            order_items_to_create = []
            payments_to_create = []

            # Get starting order number
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f"EST-{year}-"
            last_order = Order.objects.filter(number__startswith=prefix).order_by('-number').first()
            if last_order and last_order.number:
                try:
                    seq = int(last_order.number.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1

            for user in sample_customers:
                # Skip if user already has sample orders (don't duplicate)
                existing_sample_orders = Order.objects.filter(user=user, is_sample=True).count()
                if existing_sample_orders > 0:
                    order_count += existing_sample_orders
                    item_count += OrderItem.objects.filter(order__user=user, is_sample=True).count()
                    payment_count += PaymentTransaction.objects.filter(order__user=user, is_sample=True).count()
                    continue

                num_orders = random.randint(4, 12)
                for _ in range(num_orders):
                    # Weighted random: 60% of orders in last 30 days, 40% spread over 180 days
                    if random.random() < 0.6:
                        days_ago = random.randint(0, 30)
                    else:
                        days_ago = random.randint(31, 180)
                    created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
                    status = random.choice(statuses)
                    payment_method = random.choice(payment_methods)

                    order = Order(
                        user=user,
                        full_name=user.get_full_name() or user.username,
                        phone=f'080{random.randint(10000000, 99999999)}',
                        email=user.email,
                        delivery_address=f'{random.randint(1, 99)} Sample Street, Lagos',
                        delivery_fee=random.choice([0, 1500, 2000, 2500]),
                        total=0,
                        status=status,
                        payment_method=payment_method,
                        is_sample=True,
                        created_at=created_at,
                        updated_at=created_at,
                        number=f"{prefix}{seq:04d}",
                    )
                    orders_to_create.append(order)
                    seq += 1
                    order_count += 1

            # Bulk create orders
            Order.objects.bulk_create(orders_to_create)

            # Now create order items and payments for the created orders
            for order in orders_to_create:
                num_items = random.randint(1, 5)
                order_total = 0
                for _ in range(num_items):
                    product = random.choice(products)
                    qty = random.randint(1, 3)
                    price = product.price
                    order_items_to_create.append(OrderItem(
                        order=order,
                        product=product,
                        quantity=qty,
                        price=price,
                        is_sample=True,
                    ))
                    order_total += float(price) * qty
                    item_count += 1

                order.total = round(order_total, 2)

                # Create payment transaction for most orders
                if order.payment_method == 'paystack' or random.random() < 0.7:
                    payments_to_create.append(PaymentTransaction(
                        reference=f'SMP-{timezone.now().strftime("%Y%m%d")}-{order.id}-{random.randint(100000, 999999)}',
                        order=order,
                        amount=order.total + order.delivery_fee,
                        currency='NGN',
                        status='success' if order.status != 'Cancelled' else 'failed',
                        payment_method=order.payment_method,
                        raw_response={'sample': True},
                        is_sample=True,
                    ))
                    payment_count += 1

            # Bulk create order items and payments
            OrderItem.objects.bulk_create(order_items_to_create)
            PaymentTransaction.objects.bulk_create(payments_to_create)

            # Update order totals
            for order in orders_to_create:
                Order.objects.filter(pk=order.pk).update(total=order.total)

            summary['orders'] = order_count
            summary['payments'] = payment_count
            summary['order_items'] = item_count

        msg_parts = [f'{v} {k}' for k, v in summary.items()]
        messages.success(
            request,
            f'Sample data created: {", ".join(msg_parts)}.'
        )
    except Exception as e:
        messages.error(request, f'Failed to populate sample data: {e}')

    return redirect('admin_dashboard:dashboard_home')


@admin_role_required
def delete_sample_data_full(request):
    """Unified sample data deletion: removes all sample-flagged records across all models."""
    from django.conf import settings
    from django.http import HttpResponseForbidden

    if not settings.DEBUG:
        return HttpResponseForbidden("This action is not available in production.")

    if request.method != 'POST':
        return redirect('admin_dashboard:dashboard_home')

    summary = {}
    try:
        # Delete in correct order to respect FK relationships
        # 1. PaymentTransactions (reference Orders)
        from orders.models import PaymentTransaction, OrderItem, Order
        from products.models import Product, Category
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Delete payment transactions first
        payment_count, _ = PaymentTransaction.objects.filter(is_sample=True).delete()
        summary['payments'] = payment_count

        # Delete order items
        item_count, _ = OrderItem.objects.filter(is_sample=True).delete()
        summary['order_items'] = item_count

        # Delete orders
        order_count, _ = Order.objects.filter(is_sample=True).delete()
        summary['orders'] = order_count

        # Delete sample users (customers only)
        user_count, _ = User.objects.filter(is_sample=True, role='customer').delete()
        summary['customers'] = user_count

        # Delete sample products
        product_count, _ = Product.objects.filter(is_sample=True).delete()
        summary['products'] = product_count

        # Delete sample categories (only those with no remaining products)
        category_count, _ = Category.objects.filter(is_sample=True, products__isnull=True).delete()
        summary['categories'] = category_count

        msg_parts = [f'{v} {k}' for k, v in summary.items() if v > 0]
        if msg_parts:
            messages.success(
                request,
                f'Sample data removed: {", ".join(msg_parts)}. Real data was not affected.'
            )
        else:
            messages.info(request, 'No sample data found to remove.')
    except Exception as e:
        messages.error(request, f'Failed to remove sample data: {e}')

    return redirect('admin_dashboard:dashboard_home')
