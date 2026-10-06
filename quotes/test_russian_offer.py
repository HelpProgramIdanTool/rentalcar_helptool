from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from suppliers.models import Supplier, VehicleGroup, VehicleComparisonClass
from .localization import translate_text
from .models import Quote, QuoteOption, QuoteTemplate
from .email_tools import load_email_template
from .services import ensure_quote_document_blocks


class TranslationTests(SimpleTestCase):
    def test_longest_phrase_and_quantity_use_configured_translation(self):
        config = {"translations": {"A": "B", "AA": "TEST-LONG", "B": "C"}}
        self.assertEqual(translate_text("AA × 2 — A", config), "TEST-LONG × 2 — B")


@override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}})
class RussianOfferTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username="russian-test"))
        pickup = timezone.now() + timedelta(days=5)
        self.quote = Quote.objects.create(
            customer=Customer.objects.create(first_name="Тест", email="test@example.com"),
            language="Russian", pickup_datetime=pickup, return_datetime=pickup + timedelta(days=3),
            pickup_city="Kraków", return_city="Kraków", pickup_service="AIRPORT", return_service="AIRPORT",
            extra_requests={"CHILD_SEAT": 2},
        )
        supplier = Supplier.objects.create(supplier_code="RU-TEST", supplier_name="Test supplier")
        group = VehicleGroup.objects.create(supplier=supplier, group_code="TEST", group_name="Test car")
        self.option = QuoteOption.objects.create(
            quote=self.quote, supplier=supplier, vehicle_group=group,
            comparison_class=VehicleComparisonClass.objects.first(), supplier_name_snapshot="Test supplier",
            vehicle_group_name_snapshot="Test car", total_price_gross=300,
            calculation_snapshot={"included_items": ["כיסא תינוק / בוסטר × 2"],
                                  "excluded_items": ["GPS / מערכת ניווט — 10 PLN ליום"],
                                  "fuel_type_label": "בנזין"},
        )

    def url(self, name):
        return reverse(f"quotes:{name}", args=[self.quote.quote_number])

    def test_russian_preview_copy_plain_text_and_email(self):
        preview = self.client.get(self.url("quote_preview"))
        self.assertContains(preview, '<html lang="ru" dir="ltr">')
        payload = self.client.get(self.url("copy_quote")).json()
        self.assertTrue(payload["subject"].startswith("Предложение "))
        for text in (payload["html"], payload["text"]):
            self.assertIn("Общая стоимость", text)
            self.assertIn("Здравствуйте", text)
            self.assertIn("6 месяцев", text)
            self.assertIn("Детское кресло / бустер × 2", text)
            self.assertIn("GPS / навигация — 10 PLN в день", text)
            self.assertIn("возраст, рост и вес", text)
            self.assertIn("Точный порядок получения", text)
            self.assertNotRegex(text, r"[\u0590-\u05ff]")
        self.assertEqual(self.client.post(self.url("send_quote")).status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Общая стоимость", mail.outbox[0].body)
        self.assertNotRegex(mail.outbox[0].alternatives[0].content, r"[\u0590-\u05ff]")

    def test_customer_labels_and_text_are_read_from_database(self):
        template = QuoteTemplate.objects.get(language="Russian", is_active=True)
        template.presentation["labels"]["total"] = "TEST-TOTAL-RU"
        template.presentation["translations"]["כיסא תינוק / בוסטר"] = "TEST-SEAT-RU"
        template.presentation["airport"]["UNKNOWN"] = "TEST-AIRPORT-RU"
        template.save()
        template.blocks.filter(block_key="IMPORTANT").update(content="TEST-IMPORTANT-RU")
        response = self.client.get(self.url("quote_preview"))
        for marker in ("TEST-TOTAL-RU", "TEST-SEAT-RU", "TEST-AIRPORT-RU", "TEST-IMPORTANT-RU"):
            self.assertContains(response, marker)

    def test_editor_translates_saved_vehicle_title(self):
        self.option.calculation_snapshot["hebrew_vehicle_class"] = "קבוצה C — סדאן, אוטומטי"
        self.option.save()
        response = self.client.get(self.url("email_editor"))
        self.assertContains(response, "Группа C — седан, автомат")
        self.assertNotContains(response, "קבוצה C")

    def test_language_change_updates_standard_blocks_preserves_manual_edits(self):
        self.quote.language = "Hebrew"
        self.quote.save()
        load_email_template(self.quote)
        self.quote.document_blocks.filter(block_key="PAYMENT").update(content="My custom payment note")
        self.quote.language = "Russian"
        self.quote.save()
        ensure_quote_document_blocks(self.quote)
        self.assertEqual(self.quote.document_blocks.get(block_key="GREETING").source_block.template.language, "Russian")
        self.assertEqual(self.quote.document_blocks.get(block_key="IMPORTANT").source_block.template.language, "Russian")
        self.assertEqual(self.quote.document_blocks.get(block_key="PAYMENT").content, "My custom payment note")
        page = self.client.get(self.url("email_editor"))
        for form in page.context["blocks"].forms:
            self.assertEqual(form.fields["content"].widget.attrs["dir"], "ltr")
