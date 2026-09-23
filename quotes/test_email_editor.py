from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from customers.models import Customer
from suppliers.models import Supplier, VehicleGroup, VehicleComparisonClass
from .models import Quote, QuoteOption, QuoteTemplate
from .services import ensure_quote_document_blocks
from .email_tools import seat_guides, child_seat_text, load_email_template


@override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}})
class EmailEditorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor", password="test-pass")
        self.client.force_login(self.user)
        customer = Customer.objects.create(first_name="Test", email="test@example.com")
        pickup = timezone.now() + timedelta(days=10)
        self.quote = Quote.objects.create(customer=customer, language="Hebrew", pickup_datetime=pickup, return_datetime=pickup+timedelta(days=3), extra_requests={})
        self.option = self.add_option("01")
        ensure_quote_document_blocks(self.quote)
        self.url = reverse("quotes:email_editor", args=[self.quote.quote_number])

    def add_option(self, code):
        supplier, _ = Supplier.objects.get_or_create(supplier_code=code, defaults={"supplier_name": code})
        group = VehicleGroup.objects.create(supplier=supplier, group_code="EDITOR", group_name="Test")
        return QuoteOption.objects.create(quote=self.quote, supplier=supplier, vehicle_group=group,
            comparison_class=VehicleComparisonClass.objects.first(), supplier_name_snapshot=supplier.supplier_name,
            vehicle_group_name_snapshot="Test", total_price_gross=100, calculation_snapshot={})

    def payload(self):
        response = self.client.get(self.url)
        data = {"email_subject": "Custom offer", "action": "save"}
        for prefix in ("blocks", "options"):
            formset = response.context[prefix]
            data.update({f"{prefix}-TOTAL_FORMS": str(len(formset.forms)), f"{prefix}-INITIAL_FORMS": str(len(formset.forms))})
            for form in formset:
                for name in form.fields:
                    value = form[name].value()
                    if value is not None and value is not False:
                        data[form.add_prefix(name)] = value
        return data

    def test_editor_saves_only_quote_not_shared_template(self):
        template = QuoteTemplate.objects.get(is_active=True, language="Hebrew")
        original = list(template.blocks.values_list("content", flat=True))
        data = self.payload()
        data["blocks-0-content"] = "שלום חדש <script>alert(1)</script>"
        data["options-0-customer_comment"] = "הערה ללקוח"
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.email_subject, "Custom offer")
        self.assertEqual(list(template.blocks.values_list("content", flat=True)), original)
        preview = self.client.get(reverse("quotes:quote_preview", args=[self.quote.quote_number]))
        self.assertContains(preview, "הערה ללקוח")
        self.assertContains(preview, "&lt;script&gt;")

    def test_english_quote_uses_english_template_and_labels(self):
        self.quote.language = "English"
        self.quote.save(update_fields=["language"])
        load_email_template(self.quote, replace=True)

        preview = self.client.get(
            reverse("quotes:quote_preview", args=[self.quote.quote_number])
        )
        customer_html = self.client.get(
            reverse("quotes:copy_quote", args=[self.quote.quote_number])
        ).json()["html"]

        self.assertEqual(
            set(self.quote.document_blocks.values_list("source_block__template__language", flat=True)),
            {"English"},
        )
        self.assertContains(preview, "Rental details")
        self.assertContains(preview, "Vehicle options")
        self.assertContains(preview, "Total price")
        self.assertNotIn("פרטי ההשכרה", customer_html)

    def test_mandatory_not_disabled_and_options_independent_of_deposit_block(self):
        self.quote.document_blocks.filter(block_key__in=["CROSS_BORDER", "PAYMENT_DEPOSIT"]).update(is_enabled=False)
        response = self.client.get(reverse("quotes:quote_preview", args=[self.quote.quote_number]))
        self.assertContains(response, "חובה להודיע מראש על כוונה")
        self.assertContains(response, "100.00")

    def test_suppliers_switch_only_changes_newly_loaded_introduction(self):
        Supplier.objects.filter(supplier_code="01").update(show_in_introduction=True)
        load_email_template(self.quote, replace=True)
        greeting = self.quote.document_blocks.get(block_key="GREETING").content
        Supplier.objects.filter(supplier_code="01").update(show_in_introduction=False)
        self.assertEqual(self.quote.document_blocks.get(block_key="GREETING").content, greeting)
        load_email_template(self.quote, replace=True)
        self.assertNotEqual(self.quote.document_blocks.get(block_key="GREETING").content, greeting)

    def test_guides_depend_on_seats_and_selected_suppliers(self):
        self.assertEqual(seat_guides(self.quote), [])
        self.quote.extra_requests = {"CHILD_SEAT": 2}
        self.assertEqual([g["code"] for g in seat_guides(self.quote)], ["01"])
        one = self.add_option("02")
        guides = seat_guides(self.quote)
        self.assertEqual(len(guides), 2)
        self.assertIn("1–5", child_seat_text(self.quote, guides))
        self.assertIn("הגובה", child_seat_text(self.quote, guides))
        one.is_included = False
        one.save()
        self.option.is_included = False
        self.option.save()
        self.add_option("03")
        self.assertEqual(seat_guides(self.quote), [])
        self.assertNotIn("המצורפים", child_seat_text(self.quote, []))

    def test_email_attachments_and_sent_history_survive_draft_edits(self):
        self.quote.extra_requests = {"CHILD_SEAT": 1}
        self.quote.save()
        self.client.post(reverse("quotes:send_quote", args=[self.quote.quote_number]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(".workflow", mail.outbox[0].body)
        self.assertIn("פיקדון", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].attachments[0].filename, "Kaizen-child-seats.pdf")
        delivery = self.quote.email_deliveries.get()
        self.assertEqual(delivery.html, mail.outbox[0].alternatives[0].content)
        saved = delivery.html
        self.client.post(self.url, {"action": "reset"})
        delivery.refresh_from_db()
        self.assertEqual(delivery.html, saved)
        self.assertTrue(delivery.attachments[0]["data"])

    def test_missing_attachment_blocks_send(self):
        self.quote.extra_requests = {"CHILD_SEAT": 1}
        self.quote.save()
        with patch("pathlib.Path.read_bytes", side_effect=FileNotFoundError):
            response = self.client.post(reverse("quotes:send_quote", args=[self.quote.quote_number]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(self.quote.email_deliveries.exists())

    def test_foreign_block_cannot_be_edited_and_subject_rejects_newline(self):
        other = Quote.objects.create(customer=self.quote.customer, language="Hebrew", pickup_datetime=self.quote.pickup_datetime, return_datetime=self.quote.return_datetime)
        ensure_quote_document_blocks(other)
        data = self.payload()
        foreign = other.document_blocks.first()
        original = foreign.content
        data["blocks-0-id"] = foreign.pk
        data["blocks-0-content"] = "Intrusion"
        self.assertEqual(self.client.post(self.url, data).status_code, 200)
        foreign.refresh_from_db()
        self.assertEqual(foreign.content, original)
        data = self.payload()
        data["email_subject"] = "Subject\r\nBcc: wrong@example.com"
        self.assertEqual(self.client.post(self.url, data).status_code, 200)

    def test_editor_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_add_block_preserves_edits_and_renders_custom_text(self):
        template_count = QuoteTemplate.objects.get(is_active=True, language="Hebrew").blocks.count()
        data = self.payload()
        data["blocks-0-content"] = "Saved greeting"
        data["action"] = "add_block"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        block = self.quote.document_blocks.get(block_key__startswith="CUSTOM_")
        self.assertIn(f"#block-{block.pk}", response.url)
        self.assertEqual(self.quote.document_blocks.get(block_key="GREETING").content, "Saved greeting")
        self.assertEqual(QuoteTemplate.objects.get(is_active=True, language="Hebrew").blocks.count(), template_count)
        data = self.payload()
        for key, value in list(data.items()):
            if key.startswith("blocks-") and key.endswith("-id") and str(value) == str(block.pk):
                prefix = key[:-2]
                data[prefix + "title"] = "מידע נוסף"
                data[prefix + "content"] = "Custom useful information"
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        preview = self.client.get(reverse("quotes:quote_preview", args=[self.quote.quote_number]))
        self.assertContains(preview, "Custom useful information")

    def test_legacy_signature_upgrades_without_overwriting_custom_text(self):
        old = QuoteTemplate.objects.filter(is_active=False, language="Hebrew").first().blocks.get(block_key="SIGNATURE")
        signature = self.quote.document_blocks.get(block_key="SIGNATURE")
        signature.source_block = old
        signature.content = old.content.replace("\n", "\r\n")
        signature.save()
        self.quote.document_blocks.filter(block_key="GREETING").update(content="Personal greeting")
        self.client.get(self.url)
        signature.refresh_from_db()
        for item in ("idanrentacar@gmail.com", "idan.caliber@gmail.com", "+48 533 100 636", "https://poland-rent-car.com/", "https://trip2poland.co.il/", "https://travel-time.co.il/"):
            self.assertIn(item, signature.content)
        self.assertEqual(self.quote.document_blocks.get(block_key="GREETING").content, "Personal greeting")
        signature.content = "Custom signature"
        signature.save()
        self.client.get(self.url)
        signature.refresh_from_db()
        self.assertEqual(signature.content, "Custom signature")
