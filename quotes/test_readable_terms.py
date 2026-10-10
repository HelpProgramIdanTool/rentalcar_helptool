from django.test import SimpleTestCase

from .localization import readable_terms, signature_display


class ReadableTermsTests(SimpleTestCase):
    def test_signature_keeps_contact_targets_and_custom_text(self):
        rows = signature_display("Regards,\nTest Name\nPhone: +48 123 456 789\nEmail preferred\na@example.com\nhttps://example.com/path/\nCustom closing")
        self.assertEqual(rows[1], {"kind": "name", "text": "Test Name"})
        self.assertEqual(rows[2]["href"], "tel:+48123456789")
        self.assertEqual(rows[2]["label"], "Phone:")
        self.assertEqual(rows[4]["href"], "mailto:a@example.com")
        self.assertEqual(rows[5]["href"], "https://example.com/path/")
        self.assertEqual(rows[5]["text"], "example.com/path")
        self.assertEqual(rows[6]["text"], "Custom closing")

    def test_sentences_preserve_words_numbers_and_punctuation(self):
        text = "Pay 100.50 PLN by card. No cash payments.\nKeep your voucher."
        self.assertEqual(readable_terms(text), [
            "Pay 100.50 PLN by card.", "No cash payments.", "Keep your voucher.",
        ])

    def test_hebrew_and_russian_sentences(self):
        for text in ("הפיקדון נשאר. הביטוח אינו מבטל אותו.", "Депозит остаётся. Страховка его не отменяет."):
            points = readable_terms(text)
            self.assertEqual(len(points), 2)
            self.assertEqual(" ".join(points), text)

    def test_links_and_empty_text(self):
        self.assertEqual(readable_terms("https://example.com/a.b"), ["https://example.com/a.b"])
        self.assertEqual(readable_terms(""), [])
