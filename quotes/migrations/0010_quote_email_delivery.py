from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("quotes", "0009_quote_requested_vehicle_groups")]

    operations = [
        migrations.AddField(
            model_name="quote", name="sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="quote", name="sent_to_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name="quote", name="sent_subject",
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name="quote", name="sent_html_snapshot",
            field=models.TextField(blank=True),
        ),
    ]
