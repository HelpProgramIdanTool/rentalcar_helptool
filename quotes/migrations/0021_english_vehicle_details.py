from django.db import migrations


def seed(apps, schema_editor):
    Template = apps.get_model("quotes", "QuoteTemplate")
    translations = {
        "כתובת המלון שלכם": "Your hotel address",
        "כתובת המלון": "Hotel address",
        "מזוודות גדולות": "large suitcases",
        "מזוודות קטנות": "small suitcases",
        "נפח תא מטען משוער: לפחות": "Estimated luggage capacity: at least",
        "קיבולת תא מטען משוערת:": "Estimated luggage capacity:",
        "ליטר": "litres",
        "בנזין": "Petrol",
        "דיזל": "Diesel",
        "היברידי": "Hybrid",
        "חשמלי": "Electric",
    }
    for template in Template.objects.filter(language="English"):
        presentation = dict(template.presentation or {})
        wording = presentation.setdefault("translations", {})
        for source, target in translations.items():
            wording.setdefault(source, target)
        template.presentation = presentation
        template.save(update_fields=["presentation"])


class Migration(migrations.Migration):
    dependencies = [("quotes", "0020_foreign_delivery_translations")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
