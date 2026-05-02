from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_product_product_created_desc_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_sample',
            field=models.BooleanField(default=False, help_text='Marks products created by the sample data tool'),
        ),
    ]
