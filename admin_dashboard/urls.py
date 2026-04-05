from django.urls import path


from .views import (
    test_admin_dashboard, dashboard_home, admin_profile,
    product_list, product_create, product_edit, product_delete, product_toggle, product_populate_sample,
    category_list, category_create, category_edit, category_delete, category_toggle,
    order_list, order_detail,
    customer_list, customer_detail, add_customer,
    analytics_dashboard, generate_sample_data, send_analytics_report, compute_daily_metrics_view,
    content_manage,
    feedback_list, notification_list, contact_message_list, mark_all_notifications_read,
    pending_orders_view, payments_dashboard_view,
    chat_conversation_list, chat_conversation_detail, chat_admin_poll,
    auto_reply_manage,
)


app_name = 'admin_dashboard'

urlpatterns = [
    path('test/', test_admin_dashboard, name='admin_dashboard_test'),
    path('', dashboard_home, name='dashboard_home'),
    path('profile/', admin_profile, name='admin_profile'),
    path('products/', product_list, name='product_list'),
    path('products/add/', product_create, name='product_create'),
    path('products/<int:pk>/edit/', product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', product_delete, name='product_delete'),
    path('products/<int:pk>/toggle/', product_toggle, name='product_toggle'),
    path('products/populate-sample/', product_populate_sample, name='product_populate_sample'),
    # Categories
    path('categories/', category_list, name='category_list'),
    path('categories/add/', category_create, name='category_create'),
    path('categories/<int:pk>/edit/', category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', category_delete, name='category_delete'),
    path('categories/<int:pk>/toggle/', category_toggle, name='category_toggle'),
    # Orders
    path('orders/', order_list, name='order_list'),
    path('orders/<int:pk>/', order_detail, name='order_detail'),
    path('orders/pending/', pending_orders_view, name='pending_orders'),
    # Payments
    path('payments/', payments_dashboard_view, name='payments_dashboard'),
    # Customers
    path('customers/', customer_list, name='customer_list'),
    path('customers/add/', add_customer, name='add_customer'),
    path('customers/<int:pk>/', customer_detail, name='customer_detail'),
    # Analytics
    path('analytics/', analytics_dashboard, name='analytics_dashboard'),
    path('analytics/generate-sample/', generate_sample_data, name='generate_sample_data'),
    path('analytics/send-report/', send_analytics_report, name='send_analytics_report'),
    path('analytics/recompute/', compute_daily_metrics_view, name='compute_daily_metrics'),
    # Site Content Management
    path('content/', content_manage, name='content_manage'),
    path('feedback/', feedback_list, name='feedback_list'),
    path('notifications-admin/', notification_list, name='notification_list'),
    path('contact-messages/', contact_message_list, name='contact_message_list'),
    path('notifications/clear-all/', mark_all_notifications_read, name='mark_all_notifications_read'),
    # Live Chat
    path('chat/', chat_conversation_list, name='chat_list'),
    path('chat/<int:pk>/', chat_conversation_detail, name='chat_detail'),
    path('chat/<int:pk>/poll/', chat_admin_poll, name='chat_poll'),
    path('chat/auto-replies/', auto_reply_manage, name='auto_reply_manage'),
]
