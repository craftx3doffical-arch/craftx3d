from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0022_storesettings_footer_logo_alter_banner_cta_text_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
    ]
  
