from django.test import TestCase, Client
from products.models import Product, Category

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
        Category.objects.create(name='ExtraCat', slug='extracat')
        r = self.client.get('/shop/')
        # sidebar still renders the limited set (All Products + 11 categories)
        self.assertEqual(r.content.count(b'class="category-card'), 12)
        # mobile filter duplicates the same category links for small screens (includes "All Products")
        self.assertEqual(r.content.count(b'class="mobile-category-item'), 12)
        # total category links with query param should now be sidebar + mobile (11 + 11)
        self.assertEqual(r.content.count(b'/shop/?category='), 22)

    def test_shop_buttons_use_delegated_handler(self):
        # Buttons should not use inline onclick handlers — global delegated handler in base.html should cover them
        r = self.client.get('/shop/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'onclick="addToCart(', r.content)
        self.assertIn(b'btn-add-to-cart', r.content)

    def test_product_detail_variant_stock_handling(self):
        # Create a product with variants, one in stock and one out of stock
        from products.models import ProductVariant
        cat = Category.objects.create(name='VarCat', slug='varcat')
        prod = Product.objects.create(name='VarProd', slug='varprod', price=20.0, category=cat)
        variant1 = ProductVariant.objects.create(product=prod, name='Small', additional_price=0, stock=0)
        variant2 = ProductVariant.objects.create(product=prod, name='Large', additional_price=5, stock=3)
        r = self.client.get(f'/shop/{prod.slug}/')
        self.assertEqual(r.status_code, 200)
        # should show the form to select a variant because one variant is in stock
        self.assertIn(b'Choose a variant', r.content)
        # ensure out-of-stock variant is not listed
        self.assertNotIn(b'Small', r.content)
        # and in-stock variant appears
        self.assertIn(b'Large', r.content)

