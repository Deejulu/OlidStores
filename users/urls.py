
from django.urls import path
from .views import test_users, UserLoginView, UserLogoutView, signup, profile, customer_dashboard, order_history, wishlist_view, wishlist_add_view, wishlist_remove_view, activity_view, notifications_view, mark_notification_read, mark_all_notifications_read, feedback_view, CustomPasswordChangeView, addresses_view, address_edit_view, address_delete_view
from .views_verification import (
    signup, credentials_download, credentials_download_file,
    account_recovery, recovery_success
)
from django.shortcuts import render

app_name = 'users'

urlpatterns = [
	path('notifications/', notifications_view, name='notifications'),
	path('notifications/read/<int:pk>/', mark_notification_read, name='notification_mark_read'),
	path('notifications/read-all/', mark_all_notifications_read, name='mark_all_notifications_read'),
	path('test/', test_users, name='users_test'),
	path('login/', UserLoginView.as_view(), name='login'),
	path('logout/', UserLogoutView.as_view(), name='logout'),
	
	# Single-step signup (no email/OTP)
	path('signup/', signup, name='signup'),
	
	# Credentials download
	path('signup/credentials/', credentials_download, name='credentials_download'),
	path('signup/credentials/download/', credentials_download_file, name='credentials_download_file'),
	
	path('profile/', profile, name='profile'),
	path('dashboard/', customer_dashboard, name='dashboard'),
	path('orders/', order_history, name='order_history'),
	path('activity/', activity_view, name='activity'),
	path('help/', lambda request: render(request, 'users/help.html'), name='help'),
	path('feedback/', feedback_view, name='feedback'),
	path('wishlist/', wishlist_view, name='wishlist'),
	path('wishlist/add/', wishlist_add_view, name='wishlist_add'),
	path('wishlist/remove/', wishlist_remove_view, name='wishlist_remove'),
	path('password/change/', CustomPasswordChangeView.as_view(), name='password_change'),
	path('addresses/', addresses_view, name='addresses'),
	path('addresses/edit/<int:pk>/', address_edit_view, name='address_edit'),
	path('addresses/delete/<int:pk>/', address_delete_view, name='address_delete'),
	
	# Password Reset - Security Questions Only (no email)
	path('password-reset/', account_recovery, name='password_reset'),
	path('recovery/', account_recovery, name='account_recovery'),
	path('recovery/success/', recovery_success, name='recovery_success'),
]
