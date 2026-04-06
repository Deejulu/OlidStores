from django.db import migrations, models


def set_empty_phone_to_null(apps, schema_editor):
    CustomUser = apps.get_model('users', 'CustomUser')
    CustomUser.objects.filter(phone='').update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_change_phone_verified_default'),
    ]

    operations = [
        migrations.RunPython(set_empty_phone_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='customuser',
            name='phone',
            field=models.CharField(
                max_length=20,
                unique=True,
                null=True,
                blank=True,
                default=None,
                help_text='Phone number for delivery updates',
            ),
        ),
    ]
