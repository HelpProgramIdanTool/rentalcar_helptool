from django.db import migrations


def configure(apps, schema_editor):
    Template = apps.get_model('quotes', 'QuoteTemplate')
    for language, label in [('English', 'Young/new driver fee'),
                             ('Polish', 'Dopłata za młodego / nowego kierowcę'),
                             ('Russian', 'Доплата за молодого / нового водителя')]:
        for template in Template.objects.filter(language=language):
            presentation = dict(template.presentation or {})
            translations = dict(presentation.get('translations', {}))
            translations['תוספת נהג צעיר / חדש'] = label
            presentation['translations'] = translations
            template.presentation = presentation
            template.save(update_fields=['presentation'])


class Migration(migrations.Migration):
    dependencies = [('quotes', '0031_quote_driver_requirements')]
    operations = [migrations.RunPython(configure, migrations.RunPython.noop)]
