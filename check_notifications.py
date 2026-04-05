import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.models import ContactMessage
from users.models import Feedback
from orders.models import Order

unread_messages = ContactMessage.objects.filter(is_read=False).count()
unresolved_feedback = Feedback.objects.filter(is_resolved=False).count()
pending_orders = Order.objects.filter(status__in=['Pending', 'Processing']).count()

print(f'Unread messages: {unread_messages}')
print(f'Unresolved feedback: {unresolved_feedback}')
print(f'Pending orders: {pending_orders}')
print(f'Total: {unread_messages + unresolved_feedback + pending_orders}')

if unread_messages + unresolved_feedback + pending_orders == 0:
    print('\nNo notifications! The bell icon should still be visible, just without a badge.')
    print('Check if the bell icon is visible on the admin dashboard.')
