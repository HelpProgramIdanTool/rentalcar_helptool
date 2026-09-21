from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from customers.models import Customer
from employees.models import Employee, SubAgent
from quotes.models import Quote, QuoteOption
from suppliers.models import Supplier, SupplierExtra, SupplierExtraRate
from .models import Booking
from . import test_quote_conversion as conversion_test_data


class ManualBookingTests(TestCase):
    def setUp(self):
        # Reuse invented tariff data, then remove the offer entirely.
        conversion_test_data.QuoteConversionTests.setUp(self)
        QuoteOption.objects.all().delete()
        Quote.objects.all().delete()
        self.url = reverse("quotes:new_booking")
        token = self.client.get(self.url).context["form"]["entry_token"].value()
        self.data.update(supplier=self.supplier.pk, order_source="SELF", customer_name="Test Customer", driver_count=1,
                         driver_1_name="Test Driver", entry_token=token)

    def review(self, **changes):
        data = {**self.data, **changes}
        response = self.client.post(self.url, data)
        self.assertIsNotNone(response.context["review_token"], response.context["form"].errors)
        return data, response

    def confirm(self, data, response):
        return self.client.post(self.url, {**data, "action": "create", "confirm_price": "yes", "review_token": response.context["review_token"]})

    def test_manual_order_creates_no_offer_and_can_prepare_supplier_message(self):
        data, response = self.review()
        self.assertFalse(Booking.objects.exists())
        self.confirm(data, response)
        booking = Booking.objects.get()
        self.assertIsNone(booking.source_quote_id)
        self.assertFalse(Quote.objects.exists())
        self.assertEqual(booking.created_by_user, self.user)
        self.assertEqual(booking.drivers.get().first_name, "Test")
        self.assertEqual(booking.total_price_gross, 300)
        message = self.client.get(reverse("quotes:supplier_message", args=[booking.pk]))
        self.assertContains(message, "Test Driver")
        self.assertEqual(len(mail.outbox), 0)
        self.confirm(data, response)
        self.assertEqual(Booking.objects.count(), 1)

    def test_two_drivers_and_young_driver_are_visible_saved_and_priced(self):
        extra = SupplierExtra.objects.create(
            supplier=self.supplier, extra_code="YOUNG_DRIVER", name="Young driver fee",
        )
        SupplierExtraRate.objects.create(
            extra=extra, calculation_type="PER_DRIVER_DAY", amount_gross=10,
            valid_from="2026-01-01",
        )
        page = self.client.get(self.url)
        self.assertContains(page, 'name="driver_1_name"')
        self.assertContains(page, 'name="driver_1_young"')
        data, response = self.review(
            driver_count=2, driver_1_name="First Driver", driver_2_name="Second Driver",
            driver_2_young="on",
        )
        self.assertEqual(response.context["result"]["total"], 330)
        self.confirm(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.drivers.count(), 2)
        self.assertFalse(booking.drivers.get(display_order=1).young_driver_status)
        self.assertTrue(booking.drivers.get(display_order=2).young_driver_status)
        self.assertEqual(booking.total_price_gross, 330)

    def test_employee_owner_and_actual_creator_are_separate(self):
        owner = Employee.objects.create(first_name="Sales", last_name="Person", role="SALES")
        data, response = self.review(order_source="EMPLOYEE", responsible=owner.pk)
        self.confirm(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.salesperson_employee, owner)
        self.assertEqual(booking.created_by_user, self.user)

    def test_subagent_has_separate_contact_in_supplier_message(self):
        agent = SubAgent.objects.create(name="Test partner", phone="+48000000000")
        data, response = self.review(order_source="SUBAGENT", sub_agent=agent.pk)
        self.confirm(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.sub_agent, agent)
        message = self.client.get(reverse("quotes:supplier_message", args=[booking.pk]))
        self.assertIn("+48000000000 (Sub-agent)", message.context["body"])

    def test_selected_customer_is_not_overwritten(self):
        original_email = self.customer.email
        data, response = self.review(existing_customer=self.customer.pk, email="edited@example.com")
        self.confirm(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.customer_id, self.customer.pk)
        self.assertEqual(booking.customer_email_snapshot, "edited@example.com")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, original_email)

    def test_new_customer_is_not_merged_on_shared_email(self):
        before = Customer.objects.count()
        data, response = self.review(email=self.customer.email)
        self.confirm(data, response)
        self.assertEqual(Customer.objects.count(), before + 1)

    def test_required_employee_or_subagent_and_supplier_validation(self):
        for changes, field in (({"order_source": "EMPLOYEE"}, "responsible"),
                               ({"order_source": "SUBAGENT"}, "sub_agent"),
                               ({"driver_count": 2}, "driver_2_name")):
            response = self.client.post(self.url, {**self.data, **changes})
            self.assertIn(field, response.context["form"].errors)
        self.assertFalse(Booking.objects.exists())

    def test_modified_request_requires_new_confirmation(self):
        data, response = self.review()
        self.confirm({**data, "return_date": "2026-10-05"}, response)
        self.assertFalse(Booking.objects.exists())

    def test_token_cannot_be_used_by_another_user(self):
        self.client.force_login(get_user_model().objects.create_user(username="other"))
        response = self.client.post(self.url, self.data)
        self.assertContains(response, "Форма устарела")
        self.assertFalse(Booking.objects.exists())

    def test_existing_customer_can_prefill_form_and_login_is_required(self):
        response = self.client.get(self.url, {"customer": self.customer.pk})
        self.assertEqual(response.context["form"]["email"].value(), self.customer.email)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_group_of_another_supplier_is_rejected(self):
        supplier = Supplier.objects.create(supplier_code="OTHER", supplier_name="Other supplier")
        response = self.client.post(self.url, {**self.data, "supplier": supplier.pk})
        self.assertIn("vehicle_group", response.context["form"].errors)
        self.assertFalse(Booking.objects.exists())

    def test_missing_deposit_uses_popup_without_creating_customer_or_order(self):
        self.group.deposit_amount = None
        self.group.save(update_fields=["deposit_amount"])
        count = Customer.objects.count()
        response = self.client.post(self.url, self.data)
        self.assertTrue(response.context["deposit_pending"])
        self.assertIsNone(response.context["review_token"])
        self.assertEqual(Customer.objects.count(), count)
        self.assertFalse(Booking.objects.exists())

    def test_new_order_always_has_no_supplier_reservation_number(self):
        data, response = self.review(supplier_booking_number="injected-number")
        self.assertNotIn("supplier_booking_number", response.context["form"].fields)
        self.confirm(data, response)
        self.assertEqual(Booking.objects.get().supplier_booking_number, "")

    def test_vehicle_note_survives_creation_and_appears_in_supplier_message(self):
        data, response = self.review(vehicle_note="SEDAN", pickup_date="01-10-2026", return_date="04-10-2026")
        self.confirm(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.source_quote_snapshot["request"]["vehicle_note"], "SEDAN")
        message = self.client.get(reverse("quotes:supplier_message", args=[booking.pk]))
        self.assertIn("SEDAN", message.context["body"])

    def test_invoice_fields_start_hidden_but_checkbox_is_visible(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'data-field="invoice_name" hidden')
        self.assertContains(response, 'id="id_wants_invoice"')
        self.assertContains(response, 'placeholder="ДД-ММ-ГГГГ"')

    def test_compact_customer_and_location_fields(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'name="customer_name"')
        self.assertNotContains(response, 'name="first_name"')
        self.assertNotContains(response, 'name="last_name"')
        self.assertContains(response, "+ Добавить телефон")
        self.assertContains(response, "Отель при получении")
        self.assertContains(response, "Отель при возврате")
        data, reviewed = self.review(hotel_name="Pickup Test Hotel", return_hotel_name="Return Test Hotel")
        self.confirm(data, reviewed)
        booking = Booking.objects.get()
        self.assertEqual(booking.customer_name_snapshot, "Test Customer")
        self.assertEqual(booking.hotel_name, "Pickup Test Hotel")
        self.assertEqual(booking.return_hotel_name, "Return Test Hotel")
