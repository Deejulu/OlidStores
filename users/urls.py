
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
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
	
	# Password Reset URLs
	path('password-reset/', 
	     auth_views.PasswordResetView.as_view(
	         template_name='users/password_reset.html',
	         email_template_name='users/password_reset_email.txt',
	         subject_template_name='users/password_reset_subject.txt',
	         success_url=reverse_lazy('users:password_reset_done')
	     ),
	     name='password_reset'),
	path('password-reset/done/', 
	     auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
	     name='password_reset_done'),
	path('password-reset-confirm/<uidb64>/<token>/', 
	     auth_views.PasswordResetConfirmView.as_view(
	         template_name='users/password_reset_confirm.html',
	         success_url=reverse_lazy('users:password_reset_complete')
	     ),
	     name='password_reset_confirm'),
	path('password-reset-complete/', 
	     auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
	     name='password_reset_complete'),
	
	# Account Recovery with Security Questions
	path('recovery/', account_recovery, name='account_recovery'),
	path('recovery/success/', recovery_success, name='recovery_success'),
]
