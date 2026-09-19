from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from customers.models import Customer
from suppliers.models import Supplier
from .models import Booking


@override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}})
class BookingWorkspaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operator")
        self.client.force_login(self.user)
        self.supplier = Supplier.objects.create(supplier_code="WORKSPACE", supplier_name="Test supplier", booking_email="supplier@example.com")
        customer = Customer.objects.create(first_name="Test", email="test@example.com")
        self.booking = Booking.objects.create(supplier=self.supplier, customer=customer,
            manual_vehicle_price_gross=Decimal("300"), manual_price_override_reason="Test")
        self.url = reverse("quotes:booking_detail", args=[self.booking.pk])

    def test_reservation_number_and_status_save_without_repricing(self):
        response = self.client.post(self.url, {"supplier_booking_number": "ABC-123", "status": "CONFIRMED"})
        self.assertRedirects(response, self.url)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.supplier_booking_number, "ABC-123")
        self.assertEqual(self.booking.status, "CONFIRMED")
        self.assertEqual(self.booking.total_price_gross, Decimal("300"))
        self.assertTrue(self.booking.history_events.filter(description="Reservation number/status updated").exists())

    def test_duplicate_supplier_number_is_rejected(self):
        Booking.objects.create(supplier=self.supplier, customer=self.booking.customer, supplier_booking_number="ABC-123")
        response = self.client.post(self.url, {"supplier_booking_number": " abc-123 ", "status": "CONFIRMED"})
        self.assertContains(response, "Проверьте дубликат")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.supplier_booking_number, "")

    def test_confirmation_requires_supplier_number(self):
        response = self.client.post(self.url, {"supplier_booking_number": "", "status": "CONFIRMED"})
        self.assertContains(response, "укажите номер резервации")

    def test_list_filters_by_reservation_and_status(self):
        self.client.post(self.url, {"supplier_booking_number": "ABC-123", "status": "CONFIRMED"})
        url = reverse("quotes:booking_list")
        self.assertContains(self.client.get(url, {"q": "ABC-123"}), self.booking.booking_number)
        self.assertNotContains(self.client.get(url, {"status": "CANCELLED"}), self.booking.booking_number)

    def test_supplier_draft_is_editable_and_does_not_send(self):
        response = self.client.get(reverse("quotes:supplier_message", args=[self.booking.pk]))
        self.assertContains(response, "supplier@example.com")
        self.assertContains(response, "supplier-body")
        self.assertContains(response, self.booking.booking_number)
        self.assertEqual(len(mail.outbox), 0)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "DRAFT")

    def test_workspace_requires_login(self):
        self.client.logout()
        for url in (self.url, reverse("quotes:booking_list"), reverse("quotes:supplier_message", args=[self.booking.pk])):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_supplier_message_draft_survives_reopening_without_sending(self):
        url = reverse("quotes:supplier_message", args=[self.booking.pk])
        response = self.client.post(url, {"recipient": "supplier@example.com", "subject": "Test request", "body": "Driver One // Driver Two\n5x100+50=550 // 120"})
        self.assertRedirects(response, url)
        response = self.client.get(url)
        self.assertEqual(response.context["body"], "Driver One // Driver Two\n5x100+50=550 // 120")
        self.assertEqual(len(mail.outbox), 0)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "DRAFT")
        self.assertEqual(self.booking.total_price_gross, Decimal("300"))

    def test_compact_message_includes_price_address_and_zero_deposit(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            customer_address_snapshot="Example street 10", source_quote_snapshot={"deposit": "0", "deposit_currency": "PLN"})
        response = self.client.get(reverse("quotes:supplier_message", args=[self.booking.pk]))
        body = response.context["body"]
        self.assertTrue(body.startswith("Test\n"))
        self.assertIn("300=300 PLN // Deposit: 0 PLN", body)
        self.assertIn("Example street 10", body)
        self.assertNotIn("border crossing", body)

    def test_cross_border_message_uses_eu_countries(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            source_quote_snapshot={"request": {"cross_border_requested": True}})
        response = self.client.get(reverse("quotes:supplier_message", args=[self.booking.pk]))
        self.assertIn("border crossing to EU countries", response.context["body"])
        self.assertNotIn("[specify countries]", response.context["body"])

    def send_data(self):
        url = reverse("quotes:supplier_message", args=[self.booking.pk])
        response = self.client.get(url)
        return url, {"recipient": "supplier@example.com", "subject": "Test reservation", "body": "Exact test message",
                     "action": "send", "send_token": response.context["send_token"]}

    def test_send_uses_edited_text_records_history_and_waits_for_confirmation(self):
        url, data = self.send_data()
        self.assertRedirects(self.client.post(url, data), url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body, "Exact test message")
        self.assertEqual(mail.outbox[0].to, ["supplier@example.com"])
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "WAITING_CONFIRMATION")
        self.assertEqual(self.booking.supplier_booking_number, "")
        self.assertEqual(self.booking.total_price_gross, 300)
        self.assertEqual(self.booking.supplier_deliveries.get().status, "SENT")
        self.client.post(url, data)
        self.assertEqual(len(mail.outbox), 1)

    def test_failed_send_preserves_draft_and_does_not_change_status(self):
        from unittest.mock import patch
        from smtplib import SMTPException
        url, data = self.send_data()
        with patch("bookings.workspace.EmailMultiAlternatives.send", side_effect=SMTPException("test failure")):
            response = self.client.post(url, data)
        self.assertContains(response, "Отправка не подтверждена")
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "DRAFT")
        self.assertEqual(self.booking.supplier_deliveries.get().status, "FAILED")
        self.assertEqual(self.client.get(url).context["body"], data["body"])

    def test_send_requires_recipient_and_valid_token(self):
        url, data = self.send_data()
        for changes in ({"recipient": ""}, {"send_token": "invalid"}):
            response = self.client.post(url, {**data, **changes})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(self.booking.supplier_deliveries.exists())

    def test_reservation_number_has_quick_link_from_list(self):
        response = self.client.get(reverse("quotes:booking_list"))
        self.assertContains(response, self.url + "#reservation-number")
        self.assertContains(response, "＋ Внести номер")
