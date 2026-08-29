from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("quotes", "0002_quote_requested_vehicle_classes")]
    operations = [
        migrations.AddField(
            model_name="quote",
            name="extra_requests",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
