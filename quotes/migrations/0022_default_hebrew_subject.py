from django.db import migrations


def seed(apps, schema_editor):
    Template = apps.get_model("quotes", "QuoteTemplate")
    for template in Template.objects.filter(language="Hebrew"):
        presentation = dict(template.presentation or {})
        presentation["default_subject"] = "הצעת מחיר לרכב בבפולין"
        template.presentation = presentation
        template.save(update_fields=["presentation"])


class Migration(migrations.Migration):
    dependencies = [("quotes", "0021_english_vehicle_details")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
