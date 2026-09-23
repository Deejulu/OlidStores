from django.db import migrations, models


HERO_TITLE = "Everything You Need, All in One Place"
HERO_CONTENT = (
    "From electronics to fashion, beauty to everyday essentials — quality products "
    "across every category, all in one store."
)


def seed_homepage_content(apps, schema_editor):
    SiteContent = apps.get_model("core", "SiteContent")
    banner = SiteContent.objects.filter(key="homepage_banner").first()
    if not banner:
        return

    if not banner.title or banner.title in {"Premium Collection", "Elevate Your Style"}:
        banner.title = HERO_TITLE
    if not banner.content or "timeless elegance" in banner.content.lower() or "contemporary design" in banner.content.lower():
        banner.content = HERO_CONTENT
    if not banner.homepage_stat1_label:
        banner.homepage_stat1_label = "Categories"
    if not banner.homepage_stat2_value:
        banner.homepage_stat2_value = "500+"
    if not banner.homepage_stat2_label:
        banner.homepage_stat2_label = "Premium Products"
    if not banner.homepage_stat3_value:
        banner.homepage_stat3_value = "24/7"
    if not banner.homepage_stat3_label:
        banner.homepage_stat3_label = "Customer Support"
    if not banner.homepage_stat4_value:
        banner.homepage_stat4_value = "100%"
    if not banner.homepage_stat4_label:
        banner.homepage_stat4_label = "Quality Guarantee"
    banner.save(update_fields=[
        "title", "content", "homepage_stat1_label",
        "homepage_stat2_value", "homepage_stat2_label",
        "homepage_stat3_value", "homepage_stat3_label",
        "homepage_stat4_value", "homepage_stat4_label", "updated_at",
    ])


class Migration(migrations.Migration):
    dependencies = [("core", "0027_chatconversation_chatconv_status_updated_and_more")]

    operations = [
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat1_label",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat2_label",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat2_value",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat3_label",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat3_value",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat4_label",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sitecontent",
            name="homepage_stat4_value",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.RunPython(seed_homepage_content, migrations.RunPython.noop),
    ]
