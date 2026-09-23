from django.db import migrations


def seed_english_template(apps, schema_editor):
    from quotes.email_content_en import BLOCKS
    Template = apps.get_model("quotes", "QuoteTemplate")
    Block = apps.get_model("quotes", "QuoteTemplateBlock")
    Template.objects.filter(language="English").update(is_active=False)
    template = Template.objects.create(
        name="Approved customer offer", language="English", is_active=True,
    )
    for order, key, title, content in BLOCKS:
        Block.objects.create(
            template=template, block_key=key, title=title, content=content,
            display_order=order, is_active=True,
        )


class Migration(migrations.Migration):
    dependencies = [("quotes", "0016_quoteoption_manual_adjustment_amount_and_more")]
    operations = [migrations.RunPython(seed_english_template, migrations.RunPython.noop)]
