from django.db import migrations


def seed(apps, schema_editor):
    Template = apps.get_model("quotes", "QuoteTemplate")
    wording = {
        "Hebrew": "מסירת הרכב או החזרתו בעיר מחוץ לפולין",
        "Russian": "Получение или возврат в зарубежном городе",
        "English": "Vehicle collection or return in a city outside Poland",
    }
    sources = [*wording.values(), "Delivery or return in selected foreign city"]
    for template in Template.objects.filter(language__in=wording):
        presentation = dict(template.presentation or {})
        translations = presentation.setdefault("translations", {})
        for source in sources:
            translations.setdefault(source, wording[template.language])
        template.presentation = presentation
        template.save(update_fields=["presentation"])


class Migration(migrations.Migration):
    dependencies = [("quotes", "0019_russian_offer_template")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
