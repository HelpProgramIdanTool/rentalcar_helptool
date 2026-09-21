from django.db import migrations


def add_ai_note(apps, schema_editor):
    templates = apps.get_model("quotes", "QuoteTemplate")
    blocks = apps.get_model("quotes", "QuoteTemplateBlock")
    for template in templates.objects.filter(language="Hebrew", is_active=True):
        blocks.objects.get_or_create(
            template=template,
            block_key="AI_NOTE",
            defaults={
                "display_order": 95,
                "title": "מילה קטנה מאיתנו",
                "content": (
                    "ההצעה הזו הוכנה בעזרת בינה מלאכותית, אבל ההגה עדיין בידיים שלנו. "
                    "אם יש שאלה, תיקון או פרט שצריך לדייק, פשוט השיבו למייל הזה — "
                    "אחד מאיתנו יענה לכם אישית."
                ),
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("quotes", "0014_quote_sent_by_user_quoteemaildelivery_sent_by_user")]

    operations = [migrations.RunPython(add_ai_note, migrations.RunPython.noop)]
