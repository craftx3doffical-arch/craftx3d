from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0023_alter_slug_max_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='show_mega_deal',
            field=models.BooleanField(default=False, help_text='Show the red deal badge and "-X% price / M.R.P." block on the product page'),
        ),
        migrations.AddField(
            model_name='product',
            name='mega_deal_label',
            field=models.CharField(blank=True, default='Mega Festival Deal', help_text='Text on the red badge', max_length=60),
        ),
    ]
