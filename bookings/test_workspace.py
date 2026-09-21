from decimal import Decimal
from types import SimpleNamespace

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from customers.models import Customer
from suppliers.models import Supplier
from .models import Booking, BookingHistoryEvent, BookingVoucher


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

    def test_voucher_versions_are_private_and_do_not_change_booking(self):
        with override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}):
            upload_url = reverse("quotes:upload_voucher", args=[self.booking.pk])
            for filename, content in (("first.pdf", b"%PDF-1.4 first"), ("second.pdf", b"%PDF-1.4 second")):
                response = self.client.post(upload_url, {"file": SimpleUploadedFile(filename, content, content_type="application/pdf")})
                self.assertRedirects(response, self.url)
            self.assertEqual(BookingVoucher.objects.filter(booking=self.booking).count(), 2)
            first = BookingVoucher.objects.get(original_filename="first.pdf")
            self.assertNotIn("first.pdf", first.file.name)
            self.assertContains(self.client.get(self.url), "first.pdf")
            download_url = reverse("quotes:download_voucher", args=[self.booking.pk, first.pk])
            response = self.client.get(download_url)
            self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 first")
            self.assertIn("private", response["Cache-Control"])
            self.assertIn("no-store", response["Cache-Control"])
            self.client.logout()
            self.assertEqual(self.client.get(download_url).status_code, 302)
            self.client.force_login(self.user)
            other = Booking.objects.create(supplier=self.supplier, customer=self.booking.customer)
            self.assertEqual(self.client.get(reverse("quotes:download_voucher", args=[other.pk, first.pk])).status_code, 404)
            self.booking.refresh_from_db()
            self.assertEqual(self.booking.status, Booking.Status.DRAFT)
            self.assertEqual(self.booking.total_price_gross, Decimal("300"))
            self.assertTrue(self.booking.history_events.filter(description="Supplier voucher uploaded").exists())

    def test_voucher_rejects_invalid_content_and_large_file(self):
        with override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}):
            url = reverse("quotes:upload_voucher", args=[self.booking.pk])
            self.client.post(url, {"file": SimpleUploadedFile("fake.pdf", b"<html>bad</html>")})
            self.client.post(url, {"file": SimpleUploadedFile("huge.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024))})
            self.assertFalse(BookingVoucher.objects.exists())

    def test_confirmed_booking_change_can_be_sent_manually_and_reconfirmed(self):
        self.booking.supplier_booking_number = "SAME-123"
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save()
        message_url = reverse("quotes:supplier_message", args=[self.booking.pk]) + "?change=1"
        response = self.client.get(message_url)
        self.assertContains(response, "Change request SAME-123")
        self.assertContains(response, "updated voucher")
        token = response.context["send_token"]
        response = self.client.post(message_url, {
            "change_mode": "1", "action": "mark_manual", "send_token": token,
            "recipient": "supplier@example.com", "subject": "Change request SAME-123",
            "body": "Please change the return time and send an updated voucher.",
        })
        self.assertRedirects(response, self.url)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.UPDATE_PENDING)
        self.assertEqual(self.booking.supplier_booking_number, "SAME-123")
        self.assertEqual(self.booking.total_price_gross, Decimal("300"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.booking.supplier_deliveries.latest("pk").status, "MANUAL")
        self.client.post(self.url, {"supplier_booking_number": "SAME-123", "status": "CONFIRMED", "flight_number": ""})
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)

    def test_change_message_requires_confirmed_booking(self):
        response = self.client.get(reverse("quotes:supplier_message", args=[self.booking.pk]) + "?change=1")
        self.assertContains(response, "Change request")
        post = self.client.post(reverse("quotes:supplier_message", args=[self.booking.pk]), {
            "change_mode": "1", "action": "mark_manual", "send_token": response.context["send_token"],
            "recipient": "supplier@example.com", "subject": "Change request", "body": "Change dates",
        })
        self.assertContains(post, "после подтверждения заказа")
        self.assertFalse(self.booking.supplier_deliveries.exists())

    def test_confirmed_booking_change_sent_from_system_waits_for_updated_confirmation(self):
        self.booking.supplier_booking_number = "SAME-456"
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save()
        url = reverse("quotes:supplier_message", args=[self.booking.pk]) + "?change=1"
        token = self.client.get(url).context["send_token"]
        response = self.client.post(url, {
            "change_mode": "1", "action": "send", "send_token": token,
            "recipient": "supplier@example.com", "subject": "Change request SAME-456",
            "body": "Please change pickup time and confirm.",
        })
        self.assertRedirects(response, self.url)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.UPDATE_PENDING)
        self.assertEqual(self.booking.supplier_booking_number, "SAME-456")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body, "Please change pickup time and confirm.")
        self.assertEqual(self.booking.supplier_deliveries.latest("pk").status, "SENT")

    def test_reservation_number_and_status_save_without_repricing(self):
        response = self.client.post(self.url, {"supplier_booking_number": "ABC-123", "status": "CONFIRMED"})
        self.assertRedirects(response, self.url)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.supplier_booking_number, "ABC-123")
        self.assertEqual(self.booking.status, "CONFIRMED")
        self.assertEqual(self.booking.confirmed_by_user, self.user)
        self.assertEqual(self.booking.total_price_gross, Decimal("300"))
        self.assertTrue(self.booking.history_events.filter(description="Reservation number/status updated").exists())
        self.assertTrue(self.booking.history_events.filter(
            event_type=BookingHistoryEvent.EventType.STATUS_CHANGED,
            old_status=Booking.Status.DRAFT,
            new_status=Booking.Status.CONFIRMED,
            changes__operator_user_id=self.user.pk,
        ).exists())
        self.assertContains(self.client.get(reverse("quotes:booking_list")), "Подтвердил: operator")
        detail = self.client.get(self.url)
        self.assertContains(detail, "История статусов")
        self.assertContains(detail, "Черновик → Подтверждён · operator")

    def test_existing_booking_can_add_flight_number_without_repricing_or_sending(self):
        self.assertContains(self.client.get(self.url), 'name="flight_number"')
        response = self.client.post(self.url, {
            "supplier_booking_number": "", "status": "DRAFT", "flight_number": "LO123",
        })
        self.assertRedirects(response, self.url)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.flight_number, "LO123")
        self.assertEqual(self.booking.total_price_gross, Decimal("300"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(self.client.get(self.url), "LO123")

    def test_admin_confirmation_records_the_operator_too(self):
        from .admin import BookingAdmin

        self.booking.status = Booking.Status.CONFIRMED
        self.booking.supplier_booking_number = "TEST-123"
        BookingAdmin(Booking, admin.site).save_model(
            SimpleNamespace(user=self.user), self.booking, None, True,
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.confirmed_by_user, self.user)

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
        self.assertTrue(self.booking.history_events.filter(
            event_type=BookingHistoryEvent.EventType.STATUS_CHANGED,
            old_status=Booking.Status.DRAFT,
            new_status=Booking.Status.WAITING_CONFIRMATION,
            changes__operator_user_id=self.user.pk,
        ).exists())
        self.assertEqual(self.booking.supplier_booking_number, "")
        self.assertEqual(self.booking.total_price_gross, 300)
        self.assertContains(self.client.get(self.url), "Черновик → Ожидает подтверждения · operator")
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
        self.assertFalse(self.booking.history_events.filter(
            event_type=BookingHistoryEvent.EventType.STATUS_CHANGED,
        ).exists())
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
