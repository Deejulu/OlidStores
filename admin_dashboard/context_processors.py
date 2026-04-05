from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from core.models import ContactMessage, ChatConversation
from users.models import Feedback
from orders.models import Order


def admin_notifications(request):
    """
    Context processor to provide notification counts for admin users.
    Returns counts of:
    - Unread contact messages
    - Unresolved feedback
    - Pending/untouched orders
    """
    # Check if user is authenticated and is admin (or superuser)
    if not request.user.is_authenticated:
        return {
            'admin_unread_messages': 0,
            'admin_unread_chats': 0,
            'admin_unresolved_feedback': 0,
            'admin_pending_orders': 0,
            'admin_total_notifications': 0,
            'admin_order_alerts': [],
            'admin_order_alerts_count': 0,
        }
    
    # Check if user is admin or superuser
    is_admin = (
        request.user.is_superuser or 
        (hasattr(request.user, 'role') and request.user.role == 'admin')
    )
    
    if not is_admin:
        return {
            'admin_unread_messages': 0,
            'admin_unread_chats': 0,
            'admin_unresolved_feedback': 0,
            'admin_pending_orders': 0,
            'admin_total_notifications': 0,
            'admin_order_alerts': [],
            'admin_order_alerts_count': 0,
        }
    
    try:
        # Count unread contact messages
        unread_messages = ContactMessage.objects.filter(is_read=False).count()

        # Count unread live chat messages
        all_chats = list(ChatConversation.objects.prefetch_related('messages').all())
        unread_chats = sum(c.unread_admin_count for c in all_chats)
        
        # Count unresolved feedback
        unresolved_feedback = Feedback.objects.filter(is_resolved=False).count()
        
        # Count pending/processing orders (untouched = pending)
        pending_orders = Order.objects.filter(
            Q(status='Pending') | Q(status='Processing')
        ).count()
        
        # --- Order alerts ---
        now = timezone.now()
        order_alerts = []

        # 1. Pending orders that haven't been moved to Processing
        #    Alert if pending for more than 2 hours
        stale_pending = Order.objects.filter(
            status='Pending',
            created_at__lte=now - timedelta(hours=2)
        ).order_by('created_at')
        for o in stale_pending[:10]:
            hours_ago = (now - o.created_at).total_seconds() / 3600
            order_alerts.append({
                'type': 'pending',
                'severity': 'danger' if hours_ago > 12 else 'warning',
                'icon': 'bi-hourglass-split',
                'message': f'Order #{o.id} ({o.full_name}) has been Pending for {int(hours_ago)}h',
                'order_id': o.id,
            })

        # 2. Shipped orders at risk of late delivery
        #    delivery_option: '24h' = 24 hours, '2d' = 48 hours
        shipped_orders = Order.objects.filter(
            status='Shipped',
            shipped_at__isnull=False,
        ).order_by('shipped_at')
        for o in shipped_orders:
            if o.delivery_option == '24h':
                deadline = o.shipped_at + timedelta(hours=24)
            else:
                deadline = o.shipped_at + timedelta(hours=48)
            
            time_left = deadline - now
            hours_left = time_left.total_seconds() / 3600

            if hours_left < 0:
                # Overdue
                overdue_h = abs(int(hours_left))
                order_alerts.append({
                    'type': 'overdue',
                    'severity': 'danger',
                    'icon': 'bi-exclamation-triangle-fill',
                    'message': f'Order #{o.id} ({o.full_name}) is OVERDUE by {overdue_h}h — was promised {o.get_delivery_option_display()}',
                    'order_id': o.id,
                })
            elif hours_left < 6:
                # Running out of time
                order_alerts.append({
                    'type': 'at_risk',
                    'severity': 'warning',
                    'icon': 'bi-clock-history',
                    'message': f'Order #{o.id} ({o.full_name}) — only {int(hours_left)}h left to deliver ({o.get_delivery_option_display()})',
                    'order_id': o.id,
                })

        order_alerts_count = len(order_alerts)
        total_notifications = unread_messages + unread_chats + pending_orders + order_alerts_count

        return {
            'admin_unread_messages': unread_messages,
            'admin_unread_chats': unread_chats,
            'admin_unresolved_feedback': unresolved_feedback,
            'admin_pending_orders': pending_orders,
            'admin_total_notifications': total_notifications,
            'admin_order_alerts': order_alerts,
            'admin_order_alerts_count': order_alerts_count,
        }
    except Exception as e:
        # If any error occurs, return zeros
        print(f"Error in admin_notifications context processor: {e}")
        return {
            'admin_unread_messages': 0,
            'admin_unresolved_feedback': 0,
            'admin_pending_orders': 0,
            'admin_total_notifications': 0,
            'admin_order_alerts': [],
            'admin_order_alerts_count': 0,
        }

