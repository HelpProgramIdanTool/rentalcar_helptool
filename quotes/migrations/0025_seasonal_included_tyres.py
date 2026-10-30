from django.db import migrations


def configure_seasonal_tyres(apps, schema_editor):
    templates = apps.get_model('quotes', 'QuoteTemplate')
    for template in templates.objects.filter(language='Hebrew', is_active=True):
        presentation = dict(template.presentation or {})
        rules = list(presentation.get('seasonal_included_items', []))
        if not any(rule.get('code') == 'winter_tyres' for rule in rules):
            rules.append({'code': 'winter_tyres', 'start_month': 11, 'start_day': 1,
                          'end_month': 4, 'end_day': 30,
                          'text': r'ציגים רב עונתיים\חורף, בהתאם לחוק ותקן אירופאי'})
        presentation['seasonal_included_items'] = rules
        template.presentation = presentation
        template.save(update_fields=['presentation'])


class Migration(migrations.Migration):
    dependencies = [('quotes', '0024_required_offer_insurance')]
    operations = [migrations.RunPython(configure_seasonal_tyres, migrations.RunPython.noop)]
