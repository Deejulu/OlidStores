# Generated manually for performance optimization
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_product_is_sample'),
    ]

    operations = [
        # Add indexes to Product model for faster queries
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['-created_at'], name='product_created_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['price'], name='product_price_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['stock'], name='product_stock_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['category', '-created_at'], name='product_cat_date_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_sample'], name='product_sample_idx'),
        ),
        
        # Add indexes to Category model
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['slug'], name='category_slug_idx'),
        ),
        
        # Add indexes to ProductReview model
        migrations.AddIndex(
            model_name='productreview',
            index=models.Index(fields=['product', '-created_at'], name='review_prod_date_idx'),
        ),
        migrations.AddIndex(
            model_name='productreview',
            index=models.Index(fields=['rating'], name='review_rating_idx'),
        ),
    ]
