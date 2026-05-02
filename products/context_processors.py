from django.core.cache import cache
from django.db.models import Count
from .models import Category

def categories_footer(request):
    """Cache categories with product counts for 1 hour"""
    categories = cache.get('footer_categories')
    if categories is None:
        categories = list(Category.objects.annotate(
            product_count=Count('products')
        ).order_by('name'))
        cache.set('footer_categories', categories, 3600)  # Cache for 1 hour
    return {'categories': categories}
