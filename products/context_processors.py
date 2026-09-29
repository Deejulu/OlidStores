import os

from django.core.cache import cache
from django.db.models import Count
from django.urls import reverse

from .models import Category

CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))

# This key is already invalidated on every product/category create, edit,
# delete and toggle in admin_dashboard/views.py and populate_tasks.py, so
# admin edits still show up immediately.
CACHE_KEY = 'footer_categories'


def _footer_categories():
    """Footer category list with product counts, cached across requests.

    The footer renders on every page, so without this cache each navigation
    pays for a needless aggregate query. On a remote Postgres that is a full
    round-trip per page view.
    """
    return cache.get_or_set(
        CACHE_KEY,
        lambda: list(
            Category.objects.annotate(product_count=Count('products')).order_by('name')
        ),
        CACHE_TTL,
    )


def categories_footer(request):
    return {'categories': _footer_categories()}


def search_categories(request):
    # Deliberately NOT cached: the search dropdown is required to track live
    # categories, so it must always read current data.
    # See products.tests.SearchViewTests.test_main_search_dropdown_tracks_live_categories.
    return {
        'shop_url': reverse('products:shop'),
        'search_categories': list(Category.objects.order_by('name')),
    }
