"""
Signals for orders app - handles notifications for order events
"""
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models
from .models import Order, OrderAuditLog, CartItem
from users.models_notification import Notification

User = get_user_model()


def _invalidate_cart_cache(cart_item):
    """Remove the cached cart count for the user/session owning this cart item."""
    try:
        cart = cart_item.cart
        if cart.user_id:
            cache.delete(f'cart_count_user_{cart.user_id}')
        elif cart.session_key:
            cache.delete(f'cart_count_session_{cart.session_key}')
    except Exception:
        pass


@receiver(post_save, sender=CartItem)
def bust_cart_count_on_save(sender, instance, **kwargs):
    _invalidate_cart_cache(instance)


@receiver(post_delete, sender=CartItem)
def bust_cart_count_on_delete(sender, instance, **kwargs):
    _invalidate_cart_cache(instance)





@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """
    Track the previous status before save to detect status changes.
    This runs before the order is saved.
    """
    if instance.pk:
        try:
            instance._old_status = Order.objects.get(pk=instance.pk).status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Order)
def notify_order_events(sender, instance, created, **kwargs):
    """
    Send notifications for order events:
    1. New order placed - notify customer and admin
    2. Order status changes - notify customer
    3. Order cancelled - reverse stock
    """
    if created:
        # New order created
        notify_new_order(instance)
    else:
        # Order updated - check for status change
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            notify_order_status_change(instance, old_status, instance.status)
            
            # Reverse stock if order is being cancelled
            if instance.status == 'Cancelled' and old_status != 'Cancelled':
                reverse_stock_for_cancelled_order(instance)


def notify_new_order(order):
    """
    Send notifications when a new order is placed.
    - Customer gets confirmation
    - Admin gets alert
    """
    # Notify customer
    if order.user:
        Notification.objects.create(
            user=order.user,
            notification_type=Notification.TYPE_ORDER,
            title="Order Placed Successfully!",
            message=f"Your order #{order.id} for ₦{order.grand_total():,.2f} has been placed and is being processed.",
            order_id=order.id,
            action_url=f"/users/order-history/",
            is_important=True
        )
    
    # Notify all admin users
    admin_users = User.objects.filter(
        models.Q(role='admin') | models.Q(is_superuser=True),
        is_active=True
    ).distinct()
    
    customer_name = order.full_name or "Guest"
    
    # Get payment method - handle if field has no choices or is empty
    payment_info = order.payment_method or 'Pending'
    
    for admin in admin_users:
        Notification.objects.create(
            user=admin,
            notification_type=Notification.TYPE_ORDER,
            title=f"New Order #{order.id} from {customer_name}",
            message=f"Order total: ₦{order.grand_total():,.2f} | Payment: {payment_info}",
            order_id=order.id,
            action_url=f"/admin-dashboard/orders/{order.id}/",
            is_important=True
        )


def notify_order_status_change(order, old_status, new_status):
    """
    Send notification to customer when order status changes.
    """
    if not order.user:
        return  # Can't notify guest orders
    
    # Status change messages
    status_messages = {
        'Pending': {
            'title': "Order Pending",
            'message': f"Your order #{order.id} is pending payment confirmation.",
            'important': False
        },
        'Processing': {
            'title': "Order is Being Processed!",
            'message': f"Great news! Your order #{order.id} is now being prepared for shipment.",
            'important': True
        },
        'Shipped': {
            'title': "Order Shipped! 📦",
            'message': f"Your order #{order.id} has been shipped and is on its way! Expected delivery: {order.get_delivery_option_display()}",
            'important': True
        },
        'Delivered': {
            'title': "Order Delivered! ✅",
            'message': f"Your order #{order.id} has been delivered successfully. Thank you for shopping with us!",
            'important': True
        },
        'Cancelled': {
            'title': "Order Cancelled",
            'message': f"Your order #{order.id} has been cancelled. If you didn't request this, please contact support.",
            'important': True
        },
    }
    
    notification_data = status_messages.get(new_status)
    if notification_data:
        Notification.objects.create(
            user=order.user,
            notification_type=Notification.TYPE_ORDER,
            title=notification_data['title'],
            message=notification_data['message'],
            order_id=order.id,
            action_url=f"/users/order-history/",
            is_important=notification_data['important']
        )

@receiver(pre_delete, sender=Order)
def reverse_stock_on_order_delete(sender, instance, **kwargs):
    """
    Reverse stock when an order is deleted (hard delete).
    This ensures inventory is restored even if order is permanently removed.
    """
    reverse_stock_for_cancelled_order(instance)


def reverse_stock_for_cancelled_order(order):
    """
    Reverse stock for a cancelled or deleted order.
    Calls the utility function and logs the result.
    """
    from .utils import reverse_order_stock
    
    result = reverse_order_stock(order)
    
    if result['success']:
        # Log success in audit trail
        OrderAuditLog.objects.create(
            order=order,
            action='stock_reversal',
            changes={
                'reversed': True,
                'item_count': len(result['reversed_items']),
                'message': result['message']
            }
        )
    else:
        # Log failure in audit trail
        OrderAuditLog.objects.create(
            order=order,
            action='stock_reversal',
            changes={
                'reversed': False,
                'error': result['message']
            }
        )