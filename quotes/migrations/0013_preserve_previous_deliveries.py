from django.db import migrations


def preserve(apps, schema_editor):
    Quote = apps.get_model("quotes", "Quote")
    Delivery = apps.get_model("quotes", "QuoteEmailDelivery")
    for quote in Quote.objects.exclude(sent_html_snapshot="").iterator():
        if not Delivery.objects.filter(quote=quote).exists():
            delivery = Delivery.objects.create(quote=quote, recipient=quote.sent_to_email,
                subject=quote.sent_subject, html=quote.sent_html_snapshot, attachments=[])
            if quote.sent_at:
                Delivery.objects.filter(pk=delivery.pk).update(sent_at=quote.sent_at)


class Migration(migrations.Migration):
    dependencies = [("quotes", "0012_approved_email_template")]
    operations = [migrations.RunPython(preserve, migrations.RunPython.noop)]
