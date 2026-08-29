from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("quotes", "0003_quote_extra_requests")]
    operations = [
        migrations.AddField(model_name="quote", name="pickup_city", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="quote", name="pickup_service", field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name="quote", name="pickup_address", field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name="quote", name="return_city", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="quote", name="return_service", field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name="quote", name="return_address", field=models.CharField(blank=True, max_length=300)),
    ]
