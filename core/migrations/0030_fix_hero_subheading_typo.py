from django.db import migrations

# The homepage hero subheading was seeded correctly, but the live CMS record had
# been saved with a typo ("all in one storee."). This migration repairs any
# stored copy so the typo does not have to be fixed by hand in the admin.
TYPO_FIXES = [
    ("all in one storee.", "all in one store."),
    ("all in one storee", "all in one store"),
    ("storee.", "store."),
]


def fix_hero_subheading_typo(apps, schema_editor):
    SiteContent = apps.get_model("core", "SiteContent")
    banner = SiteContent.objects.filter(key="homepage_banner").first()
    if not banner:
        return

    changed_fields = []
    for field in ("content", "title", "announcement_text"):
        value = getattr(banner, field, "") or ""
        if not value:
            continue
        original = value
        for bad, good in TYPO_FIXES:
            value = value.replace(bad, good)
        if value != original:
            setattr(banner, field, value)
            changed_fields.append(field)

    if not changed_fields:
        return

    changed_fields.append("updated_at")
    banner.save(update_fields=changed_fields)


def noop(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0029_alter_sitecontent_delivery_fee_24h_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_hero_subheading_typo, noop),
    ]
