from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_migrate_legacy_banner_images'),
    ]

    operations = [
        # Add is_secret to Coupon (new BooleanField — requires schema change)
        migrations.AddField(
            model_name='coupon',
            name='is_secret',
            field=models.BooleanField(
                default=False,
                help_text='Secret coupons work when typed but never appear in any public listing or suggestion UI.',
            ),
        ),
        # awaiting_payment is a new ORDER_STATUS choice — Django choices are app-level
        # only (no DB constraint), so this is a no-op at the schema level but we include
        # it to make the migration history reflect the model change clearly.
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('awaiting_payment', '💳 Awaiting Payment'),
                    ('pending', '⏳ Pending'),
                    ('printing', '🖨️ Printing'),
                    ('shipped', '🚚 Shipped'),
                    ('delivered', '✅ Delivered'),
                    ('cancelled', '❌ Cancelled'),
                ],
                default='awaiting_payment',
                max_length=20,
            ),
        ),
    ]
