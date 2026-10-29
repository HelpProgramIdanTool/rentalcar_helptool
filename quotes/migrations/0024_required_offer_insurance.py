from django.db import migrations


def configure_required_insurance(apps, schema_editor):
    template_model = apps.get_model('quotes', 'QuoteTemplate')
    wording = 'ביטוח מלא עם ביטול השתתפות עצמית'
    for template in template_model.objects.filter(language='Hebrew', is_active=True):
        presentation = dict(template.presentation or {})
        required = list(presentation.get('required_included_items', []))
        if wording not in required:
            required.append(wording)
        presentation['required_included_items'] = required
        template.presentation = presentation
        template.save(update_fields=['presentation'])


class Migration(migrations.Migration):
    dependencies = [('quotes', '0023_polish_offer')]
    operations = [migrations.RunPython(configure_required_insurance, migrations.RunPython.noop)]
