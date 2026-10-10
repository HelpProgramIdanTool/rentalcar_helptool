from django.db import migrations


def seed(apps, schema_editor):
    from quotes.email_content_pl import PRESENTATION, BLOCKS
    Template = apps.get_model('quotes', 'QuoteTemplate')
    Block = apps.get_model('quotes', 'QuoteTemplateBlock')
    template = Template.objects.create(name='Polska oferta wynajmu', language='Polish', is_active=True, presentation=PRESENTATION)
    for order, key, title, content in BLOCKS:
        Block.objects.create(template=template, block_key=key, title=title, content=content, display_order=order, is_active=True)


class Migration(migrations.Migration):
    dependencies = [('quotes', '0022_default_hebrew_subject')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
