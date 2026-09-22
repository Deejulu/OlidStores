from django.test import TestCase, Client
from django.core.cache import cache
from django.db.models import Count
from products.models import Product, Category, ProductImage
import re

class SearchViewTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST='127.0.0.1')
        self.cat = Category.objects.create(name='TestCat', slug='testcat')
        self.p1 = Product.objects.create(name='Test Shoe', slug='shoe', price=1000, category=self.cat, stock=5)
        self.p2 = Product.objects.create(name='Other Item', slug='other', price=500, category=self.cat, stock=0)

    def test_search_returns_results(self):
        r = self.client.get('/search/?q=shoe')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Test Shoe', r.content)

    def test_search_filters_stock(self):
        r = self.client.get('/search/?q=test&stock=in')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Test Shoe', r.content)
        self.assertNotIn(b'Other Item', r.content)

    def test_shop_category_filter(self):
        # Create a category and a product, then visit shop filtered by that category
        from products.models import Category, Product
        cat = Category.objects.create(name='FilterCat', slug='filtercat')
        prod = Product.objects.create(name='FilterProd', slug='fprod', price=10.0, category=cat, stock=1)
        r = self.client.get('/shop/?category=filtercat')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'FilterProd', r.content)

    def test_shop_category_count_uses_current_products_when_cache_is_stale(self):
        cat = Category.objects.create(name='SixProductCat', slug='six-product-cat')
        products = [
            Product.objects.create(
                name=f'Six Product {index}',
                slug=f'six-product-{index}',
                price=index,
                category=cat,
                stock=1,
            )
            for index in range(1, 7)
        ]
        cached_categories = list(Category.objects.annotate(product_count=Count('products')).all())
        next(c for c in cached_categories if c.slug == cat.slug).product_count = 5
        cache.set('shop_sidebar_categories', cached_categories, 3600)

        response = self.client.get('/shop/?category=six-product-cat')

        self.assertEqual(response.context['total_products'], 6)
        displayed_category = next(
            c for c in response.context['categories'] if c.slug == cat.slug
        )
        self.assertEqual(displayed_category.product_count, 6)
        for product in products:
            self.assertContains(response, product.name)

    def test_shop_nonexistent_category_no_404(self):
        # Visiting shop with a category slug that doesn't exist should not 404
        from products.models import Category
        cat = Category.objects.create(name='FilterCat', slug='filtercat')
        r = self.client.get('/shop/?category=nonexistent')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'No products found', r.content)

    def search_dropdown_category_slugs(self):
        response = self.client.get('/search/')
        self.assertEqual(response.status_code, 200)
        dropdown = re.search(
            r'<div class="search-suggestions" id="searchSuggestions">(.*?)</form>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(dropdown)
        return sorted(re.findall(
            r'href="[^"]*\?category=([^"]+)"',
            dropdown.group(1),
        ))

    def search_dropdown_category_href(self, slug):
        response = self.client.get('/search/')
        self.assertEqual(response.status_code, 200)
        dropdown = re.search(
            r'<div class="search-suggestions" id="searchSuggestions">(.*?)</form>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(dropdown)
        href = re.search(
            rf'href="([^"]*\?category={re.escape(slug)}[^"]*)"',
            dropdown.group(1),
        )
        self.assertIsNotNone(href)
        return href.group(1)

    def test_search_dropdown_category_click_opens_filtered_shop(self):
        first = Category.objects.create(name='First Category', slug='first-category')
        first_product = Product.objects.create(
            name='First Category Product',
            slug='first-category-product',
            price=10.0,
            category=first,
            stock=1,
        )
        second = Category.objects.create(name='Second Category', slug='second-category')
        second_product = Product.objects.create(
            name='Second Category Product',
            slug='second-category-product',
            price=20.0,
            category=second,
            stock=1,
        )

        for category, product, other_product in (
            (first, first_product, second_product),
            (second, second_product, first_product),
        ):
            href = self.search_dropdown_category_href(category.slug)
            response = self.client.get(href, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.request['PATH_INFO'], '/shop/')
            self.assertContains(response, product.name)
            self.assertNotContains(response, other_product.name)

    def test_main_search_dropdown_tracks_live_categories(self):
        self.assertEqual(self.search_dropdown_category_slugs(), ['testcat'])

        added = Category.objects.create(name='New Category', slug='new-category')
        self.assertEqual(
            self.search_dropdown_category_slugs(),
            ['new-category', 'testcat'],
        )

        added.name = 'Renamed Category'
        added.slug = 'renamed-category'
        added.save()
        renamed_response = self.client.get('/search/')
        self.assertEqual(
            self.search_dropdown_category_slugs(),
            ['renamed-category', 'testcat'],
        )
        self.assertContains(renamed_response, '>Renamed Category</span>')
        self.assertNotContains(renamed_response, '>New Category</span>')

        added.delete()
        self.assertEqual(self.search_dropdown_category_slugs(), ['testcat'])

    def test_product_image_limit(self):
        from products.models import ProductImage
        # create product
        from products.models import Product, Category
        cat = Category.objects.create(name='ImgCat')
        p = Product.objects.create(name='PicProd', slug='picprod', price=10.0, category=cat)
        # add three images
        for i in range(3):
            ProductImage.objects.create(product=p, image='products/sample.jpg')
        # adding a 4th should raise ValidationError on save
        with self.assertRaises(Exception):
            ProductImage.objects.create(product=p, image='products/too_many.jpg')

    def test_ajax_filter_returns_partial(self):
        # Create several products and call ajax filter
        from products.models import Product, Category
        cat = Category.objects.create(name='AjaxCat', slug='ajaxcat')
        for i in range(5):
            Product.objects.create(name=f'AJX{i}', slug=f'ajx{i}', price=10+i, category=cat, stock=1)
        r = self.client.get('/shop/?category=ajaxcat', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'AJX0', r.content)

    def test_category_list_limited(self):
        # Create 15 categories and ensure only 11 render in the shop list
        from products.models import Category
        for i in range(15):
            Category.objects.create(name=f'C{i}', slug=f'c{i}')
        r = self.client.get('/shop/')
        # count occurrences of category-card anchors (sidebar only)
        # match HTML attributes only (avoid CSS selector occurrences in the <style> block)
        # includes the "All Products" anchor + 11 limited categories
        self.assertEqual(r.content.count(b'class="category-card'), 12)

    def test_no_extra_category_links(self):
        # Ensure category links appear only in the intended locations (sidebar + mobile filter)
        from products.models import Category
        # setUp already created 1 (TestCat); create 10 more to reach the 11-category display limit
        for i in range(10):
            Category.objects.create(name=f'Cat{i}', slug=f'cat{i}')
        # Add one extra beyond the 11-limit to verify it doesn't create extra links
        Category.objects.create(name='ExtraCat', slug='extracat')
        r = self.client.get('/shop/')
        # sidebar still renders the limited set (All Products + 11 categories)
        self.assertEqual(r.content.count(b'class="category-card'), 12)
        # mobile filter duplicates the same category links for small screens (includes "All Products")
        self.assertEqual(r.content.count(b'class="mobile-category-item'), 12)

    def test_shop_buttons_use_delegated_handler(self):
        # Buttons should not use inline onclick handlers — global delegated handler in base.html should cover them
        r = self.client.get('/shop/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'onclick="addToCart(', r.content)
        self.assertIn(b'btn-add-to-cart', r.content)

    def test_quick_view_returns_html_for_complete_product(self):
        response = self.client.get(f'/shop/{self.p1.id}/quick-view/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.name)
        self.assertContains(response, 'View Full Details')

    def test_quick_view_ignores_incomplete_image_records(self):
        ProductImage.objects.create(product=self.p1, image='')

        response = self.client.get(f'/shop/{self.p1.id}/quick-view/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.name)

    def test_quick_view_legacy_products_route_is_supported(self):
        response = self.client.get(f'/products/{self.p1.id}/quick-view/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.p1.name)

    def test_quick_view_gallery_supports_thumbnail_selection(self):
        image_urls = [
            'products/gallery-one.jpg',
            'products/gallery-two.jpg',
            'products/gallery-three.jpg',
        ]
        for image_url in image_urls:
            ProductImage.objects.create(product=self.p1, image=image_url)

        response = self.client.get(
            f'/shop/{self.p1.id}/quick-view/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        html = response.json()['html']
        thumbnails = re.findall(
            r'<img[^>]+class="quick-view-thumb[^"]*"[^>]*>',
            html,
        )
        self.assertEqual(len(thumbnails), len(image_urls))
        self.assertIn('id="quickViewMainImage"', html)
        self.assertIn('class="quick-view-thumb active"', html)
        self.assertIn('aria-pressed="true"', html)
        self.assertIn('data-quick-view-close', html)
        for thumbnail in thumbnails:
            self.assertIn('data-full=', thumbnail)
            self.assertIn('role="button"', thumbnail)
            self.assertIn('tabindex="0"', thumbnail)
        for image_url in image_urls:
            self.assertIn(f'data-full="/media/{image_url}"', html)

        shop_html = self.client.get('/shop/').content.decode()
        self.assertIn('function selectQuickViewImage', shop_html)
        self.assertIn('mainImage.src = source', shop_html)
        self.assertIn("item.classList.toggle('active', isSelected)", shop_html)
        self.assertIn("event.key === 'Escape'", shop_html)
        self.assertIn('visibility: hidden', shop_html)
        self.assertIn('pointer-events: none', shop_html)
        self.assertIn('transform: translateY(100%)', shop_html)
        self.assertIn('quick-view-loading', shop_html)
        self.assertNotIn('thumbnail.scrollIntoView', shop_html)

    def test_product_detail_variant_stock_handling(self):
        # Create a product with variants, one in stock and one out of stock
        from products.models import ProductVariant
        cat = Category.objects.create(name='VarCat', slug='varcat')
        prod = Product.objects.create(name='VarProd', slug='varprod', price=20.0, category=cat)
        variant1 = ProductVariant.objects.create(product=prod, name='Small', additional_price=0, stock=0)
        variant2 = ProductVariant.objects.create(product=prod, name='Large', additional_price=5, stock=3)
        r = self.client.get(f'/shop/{prod.slug}/')
        self.assertEqual(r.status_code, 200)
        # should show the variant select form because at least one variant is in stock
        self.assertIn(b'name="variant"', r.content)
        # ensure out-of-stock variant option is not listed (option text format: ">Name - ₦")
        self.assertNotIn(b'>Small -', r.content)
        # and in-stock variant appears as an option
        self.assertIn(b'>Large -', r.content)


class ProductFilterTests(TestCase):
	"""Tests for advanced product filtering."""

	def setUp(self):
		self.client = Client(HTTP_HOST='127.0.0.1')
		self.cat = Category.objects.create(name='FilterCat', slug='filtercat')
		self.p1 = Product.objects.create(name='Cheap Shoe', slug='cheap', price=500, category=self.cat, stock=5)
		self.p2 = Product.objects.create(name='Expensive Shoe', slug='expensive', price=5000, category=self.cat, stock=3)
		self.p3 = Product.objects.create(name='Mid Range', slug='mid', price=2000, category=self.cat, stock=0)

	def test_price_range_filter_min(self):
		"""Filter products with minimum price."""
		r = self.client.get('/shop/?min_price=1000', HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 200)
		self.assertIn(b'Expensive Shoe', r.content)
		self.assertIn(b'Mid Range', r.content)
		self.assertNotIn(b'Cheap Shoe', r.content)

	def test_price_range_filter_max(self):
		"""Filter products with maximum price."""
		r = self.client.get('/shop/?max_price=2000', HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 200)
		self.assertIn(b'Cheap Shoe', r.content)
		self.assertIn(b'Mid Range', r.content)
		self.assertNotIn(b'Expensive Shoe', r.content)

	def test_price_range_filter_both(self):
		"""Filter products within price range."""
		r = self.client.get('/shop/?min_price=1000&max_price=3000', HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 200)
		self.assertIn(b'Mid Range', r.content)
		self.assertNotIn(b'Cheap Shoe', r.content)
		self.assertNotIn(b'Expensive Shoe', r.content)

	def test_price_range_filter_no_results(self):
		"""Price range with no matching products."""
		r = self.client.get('/shop/?min_price=10000', HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 200)
		self.assertNotIn(b'Cheap Shoe', r.content)
		self.assertNotIn(b'Expensive Shoe', r.content)
		self.assertNotIn(b'Mid Range', r.content)

	def test_invalid_price_filter_ignored(self):
		"""Invalid price values should be ignored."""
		r = self.client.get('/shop/?min_price=invalid&max_price=also_invalid', HTTP_X_FORWARDED_PROTO='https')
		self.assertEqual(r.status_code, 200)
		# All products should still be shown
		self.assertIn(b'Cheap Shoe', r.content)
		self.assertIn(b'Expensive Shoe', r.content)
		self.assertIn(b'Mid Range', r.content)
