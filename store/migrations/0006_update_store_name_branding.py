from django.db import migrations


def update_store_name(apps, schema_editor):
    StoreSettings = apps.get_model('store', 'StoreSettings')
    StoreSettings.objects.filter(store_name='CraftX3D Studio').update(store_name='CraftX3D')


def revert_store_name(apps, schema_editor):
    StoreSettings = apps.get_model('store', 'StoreSettings')
    StoreSettings.objects.filter(store_name='CraftX3D').update(store_name='CraftX3D Studio')


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_contactinfo_privacypolicy_refundpolicy_and_more'),
    ]

    operations = [
        migrations.RunPython(update_store_name, revert_store_name),
    ]
