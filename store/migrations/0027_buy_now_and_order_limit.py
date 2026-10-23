from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0026_product_sale_timer'),
    ]

    operations = [
        migrations.AddField(model_name='product', name='max_order_quantity',
            field=models.PositiveIntegerField(default=10, help_text='Most units one customer can order at a time (per order / in the cart). 0 = no limit.')),
        migrations.AddField(model_name='cartitem', name='buy_now',
            field=models.BooleanField(default=False)),
        migrations.AddField(model_name='order', name='is_buy_now',
            field=models.BooleanField(default=False)),
    ]
