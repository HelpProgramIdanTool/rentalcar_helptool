from django.db import migrations


def configure_translations(apps, schema_editor):
    templates = apps.get_model('quotes', 'QuoteTemplate')
    seasonal = set()
    for template in templates.objects.filter(language='Hebrew'):
        for rule in (template.presentation or {}).get('seasonal_included_items', []):
            if rule.get('code') == 'winter_tyres' and rule.get('text'):
                seasonal.add(rule['text'])
    wording = {
        'English': ('All-season / winter tyres, in accordance with applicable law and European standards', 'Cross-border travel'),
        'Russian': ('Всесезонные / зимние шины в соответствии с законом и европейскими стандартами', 'Выезд за границу'),
        'Polish': ('Opony całoroczne / zimowe zgodne z przepisami i normami europejskimi', 'Wyjazd za granicę'),
    }
    for language, (tyres, cross_border) in wording.items():
        for template in templates.objects.filter(language=language):
            presentation = dict(template.presentation or {})
            translations = dict(presentation.get('translations', {}))
            for source in seasonal:
                translations.setdefault(source, tyres)
            for source in ('יציאה לחו״ל', 'יציאה לחו"ל', "יציאה לחו''ל", 'יציאה לחול'):
                translations.setdefault(source, cross_border)
            presentation['translations'] = translations
            template.presentation = presentation
            template.save(update_fields=['presentation'])


class Migration(migrations.Migration):
    dependencies = [('quotes', '0025_seasonal_included_tyres')]
    operations = [migrations.RunPython(configure_translations, migrations.RunPython.noop)]
