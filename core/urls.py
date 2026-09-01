from django.urls import path
from .views import HomeView, AboutView, ContactPageView, GalleryView, FAQView, PrivacyPolicyView, TermsConditionsView, ShippingPolicyView, ReturnsPolicyView
from . import views as core_views
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string

urlpatterns = [
	path('', HomeView.as_view(), name='home'),
	path('about/', AboutView.as_view(), name='about'),
	path('contact/', ContactPageView.as_view(), name='contact'),
	path('gallery/', GalleryView.as_view(), name='gallery'),
	path('test-base/', lambda request: HttpResponse(render_to_string('base.html'))),
	path('faq/', FAQView.as_view(), name='faq'),
	path('help/', lambda request: HttpResponseRedirect('/accounts/help/')),
	path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
	path('terms-conditions/', TermsConditionsView.as_view(), name='terms_conditions'),
	path('shipping/', ShippingPolicyView.as_view(), name='shipping_policy'),
	path('returns/', ReturnsPolicyView.as_view(), name='returns_policy'),
	# Chat AJAX endpoints
	path('chat/start/', core_views.chat_start, name='chat_start'),
	path('chat/send/', core_views.chat_send, name='chat_send'),
	path('chat/poll/<int:conv_id>/', core_views.chat_poll, name='chat_poll'),
	path('chat/history/<int:conv_id>/', core_views.chat_history, name='chat_history'),
	# Newsletter subscription
	path('newsletter/subscribe/', core_views.newsletter_subscribe, name='newsletter_subscribe'),
]
