from django.db import migrations, models


REMOVED_SENTENCE = "אין להסתמך על סכום פיקדון אחיד לכל החברות או לכל קבוצות הרכב."


def remove_old_deposit_sentence(apps, schema_editor):
    for model_name in ("QuoteTemplateBlock", "QuoteDocumentBlock"):
        Model = apps.get_model("quotes", model_name)
        for block in Model.objects.filter(block_key="PAYMENT_DEPOSIT"):
            updated = block.content.replace(REMOVED_SENTENCE, "").strip()
            if updated != block.content:
                block.content = updated
                block.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0014_vehicle_group_deposit"),
        ("quotes", "0007_quote_templates"),
    ]
    operations = [
        migrations.AddField(
            model_name="quoteoption",
            name="deposit_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="quoteoption",
            name="deposit_currency",
            field=models.CharField(default="PLN", max_length=3),
        ),
        migrations.RunPython(remove_old_deposit_sentence, migrations.RunPython.noop),
    ]
