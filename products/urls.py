from django.urls import path
from .views import ShopListView, ProductDetailView, submit_review, mark_review_helpful, quick_view_product

app_name = 'products'

urlpatterns = [
	path('', ShopListView.as_view(), name='shop'),
	path('<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
	path('<slug:slug>/review/', submit_review, name='submit_review'),
	path('review/<int:review_id>/helpful/', mark_review_helpful, name='mark_review_helpful'),
	path('<int:pk>/quick-view/', quick_view_product, name='quick_view'),
]
