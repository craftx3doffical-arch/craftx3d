from django.db import migrations


def migrate_banner_images(apps, schema_editor):
    Banner = apps.get_model('store', 'Banner')
    BannerImage = apps.get_model('store', 'BannerImage')
    for banner in Banner.objects.all():
        order = 0
        for field_name in ['image1', 'image2', 'image3', 'image4']:
            field = getattr(banner, field_name)
            if field:
                BannerImage.objects.create(banner=banner, image=field.name, display_order=order)
                order += 1


def reverse_migrate_banner_images(apps, schema_editor):
    # No safe reverse — legacy fields are left untouched either way, so
    # nothing needs to be undone.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0010_bannerimage'),
    ]

    operations = [
        migrations.RunPython(migrate_banner_images, reverse_migrate_banner_images),
    ]
