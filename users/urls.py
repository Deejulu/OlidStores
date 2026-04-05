
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import test_users, UserLoginView, UserLogoutView, signup, profile, customer_dashboard, order_history, wishlist_view, wishlist_add_view, wishlist_remove_view, activity_view, notifications_view, mark_notification_read, feedback_view, CustomPasswordChangeView, addresses_view, address_edit_view, address_delete_view
from .views_verification import (
    signup_step1, signup_verify_email, signup_verify_phone, signup_complete,
    resend_email_otp, resend_phone_otp,
    verify_existing_user, send_existing_user_email_otp, send_existing_user_phone_otp,
    verify_existing_email, verify_existing_phone
)
from django.shortcuts import render

app_name = 'users'

urlpatterns = [
	path('notifications/read/<int:pk>/', mark_notification_read, name='notification_mark_read'),
	path('test/', test_users, name='users_test'),
	path('login/', UserLoginView.as_view(), name='login'),
	path('logout/', UserLogoutView.as_view(), name='logout'),
	
	# New multi-step signup with OTP verification
	path('signup/', signup_step1, name='signup'),
	path('signup/verify-email/', signup_verify_email, name='signup_verify_email'),
	path('signup/verify-phone/', signup_verify_phone, name='signup_verify_phone'),
	path('signup/complete/', signup_complete, name='signup_complete'),
	path('signup/resend-email/', resend_email_otp, name='resend_email_otp'),
	path('signup/resend-phone/', resend_phone_otp, name='resend_phone_otp'),
	
	# Existing user verification (for users who registered before OTP was required)
	path('verify/', verify_existing_user, name='verify_existing_user'),
	path('verify/send-email-otp/', send_existing_user_email_otp, name='send_existing_user_email_otp'),
	path('verify/send-phone-otp/', send_existing_user_phone_otp, name='send_existing_user_phone_otp'),
	path('verify/email/', verify_existing_email, name='verify_existing_email'),
	path('verify/phone/', verify_existing_phone, name='verify_existing_phone'),
	
	path('profile/', profile, name='profile'),
	path('dashboard/', customer_dashboard, name='dashboard'),
	path('orders/', order_history, name='order_history'),
	path('activity/', activity_view, name='activity'),
	path('help/', lambda request: render(request, 'users/help.html'), name='help'),
	path('feedback/', feedback_view, name='feedback'),
	path('notifications/', notifications_view, name='notifications'),
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
]
