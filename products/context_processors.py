from django.db.models import Count
from django.urls import reverse
from .models import Category


def categories_footer(request):
    categories = list(
        Category.objects.annotate(product_count=Count('products')).order_by('name')
    )
    return {'categories': categories}


def search_categories(request):
    return {
        'shop_url': reverse('products:shop'),
        'search_categories': list(Category.objects.order_by('name')),
    }
