from django.db import migrations


def forwards_func(apps, schema_editor):
    SiteContent = apps.get_model('core', 'SiteContent')
    try:
        CheckoutSettings = apps.get_model('orders', 'CheckoutSettings')
    except LookupError:
        CheckoutSettings = None
    cs = None
    if CheckoutSettings:
        cs = CheckoutSettings.objects.first()
    sc, created = SiteContent.objects.get_or_create(key='checkout', defaults={'title': 'Checkout'})
    if cs:
        changed = False
        if getattr(sc, 'delivery_fee_24h', None) in [None, 0] and getattr(cs, 'delivery_fee_24h', None) is not None:
            sc.delivery_fee_24h = cs.delivery_fee_24h
            changed = True
        if getattr(sc, 'delivery_fee_2d', None) in [None, 0] and getattr(cs, 'delivery_fee_2d', None) is not None:
            sc.delivery_fee_2d = cs.delivery_fee_2d
            changed = True
        if changed:
            sc.save()


def reverse_func(apps, schema_editor):
    # no-op
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_sitecontent_delivery_fee_24h_and_more'),
        ('orders', '0007_checkoutsettings'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
