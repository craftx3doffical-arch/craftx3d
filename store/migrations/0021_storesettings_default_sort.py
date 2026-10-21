from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0020_is_bestseller'),
    ]

    operations = [
        migrations.AddField(
            model_name='storesettings',
            name='default_sort',
            field=models.CharField(
                choices=[('newest', 'Newest First'), ('popular', 'Best Selling'), ('price_low', 'Price: Low to High'), ('price_high', 'Price: High to Low')],
                default='newest',
                help_text='Sort order shown on /products/ when a customer hasn\'t picked one — the "Sort by" dropdown opens on this option.',
                max_length=20,
            ),
        ),
    ]
