from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('quotes', '0030_quote_local_rental_branch')]
    operations = [migrations.AddField(model_name='quote', name='driver_requirements',
        field=models.JSONField(default=dict, blank=True))]
