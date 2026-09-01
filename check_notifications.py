import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.models import ChatConversation
from users.models import Feedback
from orders.models import Order

unread_chats = sum(c.unread_admin_count for c in ChatConversation.objects.all())
unresolved_feedback = Feedback.objects.filter(is_resolved=False).count()
pending_orders = Order.objects.filter(status__in=['Pending', 'Processing']).count()

print(f'Unread chat messages: {unread_chats}')
print(f'Unresolved feedback: {unresolved_feedback}')
print(f'Pending orders: {pending_orders}')
print(f'Total: {unread_chats + unresolved_feedback + pending_orders}')

if unread_chats + unresolved_feedback + pending_orders == 0:
    print('\nNo notifications! The bell icon should still be visible, just without a badge.')
    print('Check if the bell icon is visible on the admin dashboard.')
