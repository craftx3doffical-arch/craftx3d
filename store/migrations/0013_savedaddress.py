from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('store', '0012_coupon_is_secret_order_awaiting_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavedAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=120)),
                ('phone', models.CharField(max_length=15)),
                ('alternate_phone', models.CharField(blank=True, max_length=15)),
                ('address_line1', models.CharField(max_length=250, verbose_name='Flat / House no. / Building')),
                ('address_line2', models.CharField(blank=True, max_length=250, verbose_name='Area / Street / Village')),
                ('landmark', models.CharField(blank=True, max_length=200)),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=100)),
                ('pincode', models.CharField(max_length=10)),
                ('is_default', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='saved_addresses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-is_default', '-created_at']},
        ),
    ]
