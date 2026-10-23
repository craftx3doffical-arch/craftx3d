from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0024_product_mega_deal'),
    ]

    operations = [
        migrations.AddField(
            model_name='enquiry',
            name='enquiry_type',
            field=models.CharField(choices=[('general', 'General'), ('customization', 'Customization')], db_index=True, default='general', max_length=20),
        ),
        migrations.AddField(
            model_name='enquiry',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='enquiries', to='store.product'),
        ),
        migrations.AddField(
            model_name='enquiry',
            name='quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='enquiry',
            name='budget',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
