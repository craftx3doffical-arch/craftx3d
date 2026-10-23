from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0025_enquiry_customization'),
    ]

    operations = [
        migrations.AddField(model_name='product', name='show_sale_timer',
            field=models.BooleanField(default=False, help_text='Show a sale countdown on the product page until the end time')),
        migrations.AddField(model_name='product', name='sale_timer_label',
            field=models.CharField(blank=True, default='Sale ends in:', max_length=60)),
        migrations.AddField(model_name='product', name='sale_timer_ends_at',
            field=models.DateTimeField(blank=True, null=True, help_text='When the sale ends. The countdown hides itself after this time.')),
        migrations.AddField(model_name='product', name='show_sale_stock',
            field=models.BooleanField(default=False, help_text='Show "Only N left at this price!" using the real stock count')),
        migrations.AddField(model_name='product', name='sale_stock_text',
            field=models.CharField(blank=True, default='Only {n} left at this price!', help_text='Use {n} where the stock number should appear', max_length=120)),
    ]
