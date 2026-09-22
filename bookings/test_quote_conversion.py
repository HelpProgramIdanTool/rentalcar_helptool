from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from customers.models import Customer
from suppliers.models import Supplier, SupplierLocation, VehicleGroup, VehicleComparisonClass, PriceList, PriceSeason, PriceDayRange, VehicleRate, SupplierExtra, SupplierExtraRate
from quotes.models import Quote, QuoteOption
from .models import Booking


class QuoteConversionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operator")
        self.client.force_login(self.user)
        self.customer = Customer.objects.create(email="old@example.com")
        self.supplier = Supplier.objects.create(supplier_code="02", supplier_name="Test rental")
        self.group = VehicleGroup.objects.create(supplier=self.supplier, group_code="TEST", group_name="Test car", deposit_amount=300)
        self.group.comparison_classes.add(VehicleComparisonClass.objects.first())
        price_list = PriceList.objects.create(supplier=self.supplier, name="Current", version="new", effective_from=date(2026, 1, 1), status="ACTIVE")
        season = PriceSeason.objects.create(price_list=price_list, season_code="ALL", season_name="All", rental_date_from=date(2026, 1, 1))
        days = PriceDayRange.objects.create(price_list=price_list, range_code="ALL", label="All", days_from=1)
        self.rate = VehicleRate.objects.create(season=season, day_range=days, vehicle_group=self.group, daily_rate_gross=100)
        self.quote = Quote.objects.create(customer=self.customer,
            pickup_datetime=datetime(2026, 10, 1, 10, tzinfo=ZoneInfo("Europe/Warsaw")),
            return_datetime=datetime(2026, 10, 4, 10, tzinfo=ZoneInfo("Europe/Warsaw")),
            pickup_city="Kraków", return_city="Kraków", pickup_service="CITY_BRANCH", return_service="CITY_BRANCH")
        self.option = QuoteOption.objects.create(quote=self.quote, supplier=self.supplier, vehicle_group=self.group,
            comparison_class=VehicleComparisonClass.objects.first(), total_price_gross=250, currency="PLN")
        self.url = reverse("quotes:booking_from_offer", args=[self.quote.quote_number, self.option.pk])
        self.data = dict(email="new@example.com", pickup_date="2026-10-01", return_date="2026-10-04",
            pickup_time="10:00", return_time="10:00", pickup_city="Kraków", return_city="Kraków",
            pickup_service="CITY_BRANCH", return_service="CITY_BRANCH", driver_count=2, vehicle_group=self.group.pk)

    def review(self, **changes):
        data = {**self.data, **changes}
        response = self.client.post(self.url, data)
        self.assertIsNotNone(response.context["review_token"], response.context["form"].errors)
        return data, response

    def create(self, data, response):
        return self.client.post(self.url, {**data, "action": "create", "confirm_price": "yes", "review_token": response.context["review_token"]})

    def test_prefilled_get_is_read_only(self):
        response = self.client.get(self.url)
        self.assertContains(response, "old@example.com")
        self.assertContains(response, 'value="01-10-2026"')
        self.assertContains(response, 'name="driver_1_name"')
        self.assertContains(response, 'name="driver_2_name"')
        self.assertNotContains(response, 'name="driver_2_first_name"')
        self.assertFalse(Booking.objects.exists())

    def test_two_driver_names_are_saved_in_the_order(self):
        data, response = self.review(
            driver_1_name="Anna Nowak", driver_2_name="Piotr Kowalski",
        )
        self.create(data, response)
        self.assertEqual(
            list(Booking.objects.get().drivers.values_list("first_name", "last_name", "role")),
            [("Anna", "Nowak", "MAIN"), ("Piotr", "Kowalski", "ADDITIONAL")],
        )
        detail = self.client.get(reverse("quotes:booking_detail", args=[Booking.objects.get().pk]))
        self.assertContains(detail, "Anna Nowak")
        self.assertContains(detail, "Piotr Kowalski")

    def test_car_free_prague_airport_is_a_regular_supplier_location(self):
        self.supplier.supplier_code = "01"
        self.supplier.save(update_fields=["supplier_code"])
        airport = SupplierLocation.objects.create(
            supplier=self.supplier, location_code="PRG", location_name="Prague Airport",
            city="Prague Airport", country="Czech Republic", location_type="AIRPORT",
            airport_code="PRG", supports_pickup=True, supports_return=True,
        )
        data, response = self.review(
            pickup_city="Prague", return_city="Prague",
            pickup_service="AIRPORT", return_service="AIRPORT",
        )
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.pickup_location, airport)
        self.assertEqual(booking.return_location, airport)
        self.assertFalse(booking.extras.filter(extra__extra_code="FOREIGN_CITY_DELIVERY").exists())

    def test_manual_adjustment_from_offer_is_saved_in_booking_total(self):
        self.option.manual_adjustment_label = "Special route"
        self.option.manual_adjustment_amount = 40
        self.option.total_price_gross = 340
        self.option.save(update_fields=["manual_adjustment_label", "manual_adjustment_amount", "total_price_gross"])
        data, response = self.review(
            manual_adjustment_label="Special route", manual_adjustment_amount="40",
        )
        self.assertEqual(response.context["result"]["total"], 340)
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.manual_adjustment_label, "Special route")
        self.assertEqual(booking.manual_adjustment_amount, 40)
        self.assertEqual(booking.total_price_gross, 340)

    def test_created_booking_marks_its_quote_accepted(self):
        data, response = self.review()
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.DRAFT)
        self.create(data, response)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.ACCEPTED)
        self.assertEqual(Booking.objects.get().source_quote, self.quote)

    @override_settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}})
    def test_offer_to_supplier_confirmation_flow(self):
        self.supplier.booking_email = "supplier@example.com"
        self.supplier.save(update_fields=["booking_email"])
        data, reviewed = self.review()
        self.create(data, reviewed)
        booking = Booking.objects.get()
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.ACCEPTED)

        message_url = reverse("quotes:supplier_message", args=[booking.pk])
        message_page = self.client.get(message_url)
        self.client.post(message_url, {
            "recipient": "supplier@example.com", "subject": "Test booking request",
            "body": "Please confirm test booking", "action": "send",
            "send_token": message_page.context["send_token"],
        })
        booking.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(booking.status, Booking.Status.WAITING_CONFIRMATION)

        detail_url = reverse("quotes:booking_detail", args=[booking.pk])
        self.client.post(detail_url, {
            "supplier_booking_number": "TEST-RES-100", "status": Booking.Status.CONFIRMED,
        })
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.supplier_booking_number, "TEST-RES-100")
        self.assertEqual(booking.confirmed_by_user, self.user)
        self.assertEqual(
            list(booking.history_events.filter(event_type="STATUS_CHANGED").values_list("old_status", "new_status")),
            [(Booking.Status.WAITING_CONFIRMATION, Booking.Status.CONFIRMED),
             (Booking.Status.DRAFT, Booking.Status.WAITING_CONFIRMATION)],
        )

    def test_flight_number_from_offer_is_saved_in_booking(self):
        page = self.client.get(self.url)
        self.assertContains(page, 'name="flight_number"')
        self.assertLess(
            page.content.find(b'name="pickup_address"'),
            page.content.find(b'name="flight_number"'),
        )
        data, response = self.review(flight_number="LO123")
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.flight_number, "LO123")
        self.assertContains(
            self.client.get(reverse("quotes:booking_detail", args=[booking.pk])),
            "LO123",
        )

    def test_deposit_uses_group_settings_instead_of_fallback(self):
        from unittest.mock import patch

        self.group.deposit_amount = Decimal("123.00")
        self.group.deposit_currency = "EUR"
        self.group.save(update_fields=["deposit_amount", "deposit_currency"])
        with patch("suppliers.deposit_rules.default_deposit_amount", return_value=Decimal("999")) as fallback:
            _, response = self.review()
            fallback.assert_not_called()
        self.assertEqual(response.context["result"]["deposit_amount"], Decimal("123.00"))
        self.assertEqual(response.context["result"]["deposit_currency"], "EUR")
        self.assertNotContains(response, "уточняется")

    def test_zero_deposit_is_displayed_without_fallback(self):
        from unittest.mock import patch

        self.group.deposit_amount = Decimal("0.00")
        self.group.save(update_fields=["deposit_amount"])
        with patch("suppliers.deposit_rules.default_deposit_amount", return_value=Decimal("999")) as fallback:
            _, response = self.review()
            fallback.assert_not_called()
        self.assertEqual(response.context["result"]["deposit_amount"], Decimal("0.00"))
        self.assertNotContains(response, "уточняется")

    def test_unknown_deposit_is_explicit_in_review(self):
        self.group.deposit_amount = None
        self.group.save(update_fields=["deposit_amount"])
        response = self.client.post(self.url, self.data)
        self.assertIsNone(response.context["result"]["deposit_amount"])
        self.assertContains(response, "Не указан депозит")
        self.assertIsNone(response.context["review_token"])

    def test_missing_deposit_is_not_replaced_by_legacy_amount(self):
        from unittest.mock import patch

        self.group.deposit_amount = None
        self.group.save(update_fields=["deposit_amount"])
        with patch("suppliers.deposit_rules.DEPOSIT_AMOUNTS_PLN", {
            self.supplier.supplier_code: {self.group.group_code: Decimal("999")},
        }):
            response = self.client.post(self.url, self.data)
        self.assertIsNone(response.context["result"]["deposit_amount"])
        self.assertContains(response, "Не указан депозит")

    def test_deposit_change_requires_new_confirmation(self):
        data, response = self.review()
        self.group.deposit_amount = Decimal("120")
        self.group.save(update_fields=["deposit_amount"])
        updated = self.create(data, response)
        self.assertFalse(Booking.objects.exists())
        self.assertEqual(updated.context["result"]["deposit_amount"], Decimal("120"))
        self.create(data, updated)
        self.assertEqual(Booking.objects.get().source_quote_snapshot["deposit"], "120.00")

    def missing_deposit_data(self, usage="once", amount="0", currency="PLN"):
        self.group.deposit_amount = None
        self.group.save(update_fields=["deposit_amount"])
        response = self.client.post(self.url, self.data)
        return {**self.data, "action": "resolve_deposit", "deposit-amount": amount,
                "deposit-currency": currency, "deposit-usage": usage,
                "deposit-context": response.context["deposit_form"]["context"].value()}

    def test_one_time_zero_deposit_survives_confirmation_without_changing_database(self):
        data = self.missing_deposit_data()
        response = self.client.post(self.url, data)
        self.assertIsNotNone(response.context["review_token"])
        self.assertEqual(response.context["result"]["deposit_amount"], Decimal("0"))
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.source_quote_snapshot["deposit"], "0")
        self.assertEqual(booking.source_quote_snapshot["deposit_usage"], "once")
        self.group.refresh_from_db()
        self.assertIsNone(self.group.deposit_amount)

    def test_permanent_deposit_saves_amount_currency_and_audit_record(self):
        from django.contrib.auth.models import Permission
        from django.contrib.admin.models import LogEntry

        self.user.user_permissions.add(Permission.objects.get(codename="change_vehiclegroup"))
        data = self.missing_deposit_data(usage="permanent", amount="125.00", currency="EUR")
        response = self.client.post(self.url, data)
        self.assertIsNotNone(response.context["review_token"])
        self.group.refresh_from_db()
        self.assertEqual(self.group.deposit_amount, Decimal("125"))
        self.assertEqual(self.group.deposit_currency, "EUR")
        self.assertTrue(LogEntry.objects.filter(user=self.user, object_id=str(self.group.pk)).exists())
        self.assertFalse(Booking.objects.exists())
        self.create(self.data, response)
        self.assertEqual(Booking.objects.get().source_quote_snapshot["deposit"], "125.00")

    def test_permanent_deposit_requires_catalog_permission(self):
        data = self.missing_deposit_data(usage="permanent", amount="125")
        response = self.client.post(self.url, data)
        self.assertIsNone(response.context["review_token"])
        self.group.refresh_from_db()
        self.assertIsNone(self.group.deposit_amount)

    def test_invalid_deposit_does_not_save_or_allow_confirmation(self):
        data = self.missing_deposit_data(amount="-1")
        for changes in ({}, {"deposit-amount": ""}, {"deposit-amount": "1.001"},
                        {"deposit-amount": "1", "deposit-currency": "bad"},
                        {"deposit-amount": "1", "deposit-context": "tampered"}):
            with self.subTest(changes=changes):
                response = self.client.post(self.url, {**data, **changes})
                self.assertIsNone(response.context["review_token"])
                self.assertFalse(Booking.objects.exists())
        self.group.refresh_from_db()
        self.assertIsNone(self.group.deposit_amount)

    def test_missing_deposit_cannot_be_bypassed_by_direct_create(self):
        self.missing_deposit_data()
        response = self.client.post(self.url, {**self.data, "action": "create", "confirm_price": "yes"})
        self.assertTrue(response.context["deposit_pending"])
        self.assertFalse(Booking.objects.exists())

    def test_popup_does_not_overwrite_deposit_entered_by_another_operator(self):
        from django.contrib.auth.models import Permission

        self.user.user_permissions.add(Permission.objects.get(codename="change_vehiclegroup"))
        data = self.missing_deposit_data(usage="permanent", amount="125")
        VehicleGroup.objects.filter(pk=self.group.pk).update(deposit_amount=250)
        response = self.client.post(self.url, data)
        self.group.refresh_from_db()
        self.assertEqual(self.group.deposit_amount, Decimal("250"))
        self.assertEqual(response.context["result"]["deposit_amount"], Decimal("250"))

    def test_cancelling_popup_has_not_written_any_value(self):
        self.missing_deposit_data()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.group.refresh_from_db()
        self.assertIsNone(self.group.deposit_amount)
        self.assertFalse(Booking.objects.exists())

    def test_one_time_deposit_cannot_follow_a_different_vehicle_group(self):
        data = self.missing_deposit_data(amount="120")
        group = VehicleGroup.objects.create(supplier=self.supplier, group_code="OTHER", group_name="Other")
        group.comparison_classes.add(VehicleComparisonClass.objects.first())
        VehicleRate.objects.create(season=self.rate.season, day_range=self.rate.day_range, vehicle_group=group, daily_rate_gross=100)
        response = self.client.post(self.url, {**data, "vehicle_group": group.pk})
        self.assertIsNone(response.context["review_token"])
        self.assertContains(response, "Автомобиль изменился")

    def test_permanent_deposit_updates_shared_tariff_group(self):
        from django.contrib.auth.models import Permission

        self.user.user_permissions.add(Permission.objects.get(codename="change_vehiclegroup"))
        source = VehicleGroup.objects.create(supplier=self.supplier, group_code="SOURCE", group_name="Shared tariff")
        VehicleRate.objects.create(season=self.rate.season, day_range=self.rate.day_range, vehicle_group=source, daily_rate_gross=100)
        self.group.rate_source_group = source
        self.group.save(update_fields=["rate_source_group"])
        data = self.missing_deposit_data(usage="permanent", amount="125.00")
        response = self.client.post(self.url, data)
        self.assertIsNotNone(response.context["review_token"])
        source.refresh_from_db()
        self.group.refresh_from_db()
        self.assertEqual(source.deposit_amount, Decimal("125"))
        self.assertIsNone(self.group.deposit_amount)

    def test_changed_price_confirmed_draft_original_untouched_and_repeat_safe(self):
        data, response = self.review()
        self.assertContains(response, "Цена отличается от оферты")
        self.assertEqual(response.context["result"]["total"], Decimal("300"))
        created = self.create(data, response)
        booking = Booking.objects.get()
        self.assertRedirects(created, reverse("quotes:booking_detail", args=[booking.pk]))
        self.assertEqual(booking.total_price_gross, Decimal("300"))
        self.assertEqual(booking.status, "DRAFT")
        self.assertEqual(booking.customer_email_snapshot, "new@example.com")
        self.customer.refresh_from_db()
        self.option.refresh_from_db()
        self.assertEqual(self.customer.email, "old@example.com")
        self.assertEqual(self.option.total_price_gross, Decimal("250"))
        self.assertEqual(len(mail.outbox), 0)
        self.create(data, response)
        self.assertEqual(Booking.objects.count(), 1)

    def test_one_rent_airport_return_does_not_add_fee_to_booking(self):
        airport_fee = SupplierExtra.objects.create(
            supplier=self.supplier, extra_code="AIRPORT_FEE", name="Test airport fee"
        )
        SupplierExtraRate.objects.create(
            extra=airport_fee, valid_from=date(2026, 1, 1),
            calculation_type="PER_RENTAL", amount_gross=50,
        )
        self.option.total_price_gross = Decimal("300.00")
        self.option.save(update_fields=["total_price_gross"])
        data, response = self.review(
            pickup_service="ADDRESS", pickup_address="Test hotel",
            return_service="AIRPORT",
        )
        self.assertEqual(response.context["result"]["total"], Decimal("300.00"))
        self.assertFalse(response.context["changed"])
        self.assertNotIn(
            "AIRPORT_FEE",
            {line["extra"].extra_code for line in response.context["result"]["extra_lines"]},
        )
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.total_price_gross, Decimal("300.00"))
        self.assertFalse(booking.extras.filter(extra__extra_code="AIRPORT_FEE").exists())

    def test_tariff_changed_between_review_and_confirmation(self):
        data, response = self.review()
        VehicleRate.objects.filter(pk=self.rate.pk).update(daily_rate_gross=120)
        result = self.create(data, response)
        self.assertFalse(Booking.objects.exists())
        self.assertEqual(result.context["result"]["total"], Decimal("360"))
        self.assertContains(result, "Данные или тариф могли измениться")

    def test_edit_requires_new_review_and_recalculates_days(self):
        data, response = self.review()
        result = self.create({**data, "return_date": "2026-10-05"}, response)
        self.assertFalse(Booking.objects.exists())
        self.assertEqual(result.context["result"]["total"], Decimal("400"))

    def test_cannot_create_without_signed_review_or_contact(self):
        for changes in ({"action": "create", "confirm_price": "yes"}, {"email": ""}):
            self.client.post(self.url, {**self.data, **changes})
            self.assertFalse(Booking.objects.exists())
            self.quote.refresh_from_db()
            self.assertEqual(self.quote.status, Quote.Status.DRAFT)

    def test_missing_rate_blocks_creation(self):
        self.rate.is_active = False
        self.rate.save()
        response = self.client.post(self.url, self.data)
        self.assertContains(response, "Нет действующего тарифа")
        self.assertFalse(Booking.objects.exists())

    def test_missing_extra_blocks_creation(self):
        response = self.client.post(self.url, {**self.data, "extra_choices": ["CHILD_SEAT"], "child_seat_quantity": 2})
        self.assertContains(response, "Не удалось рассчитать все выбранные добавки")

    def test_extras_quantity_caps_survive_booking_save(self):
        extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code="CHILD_SEAT", name="Seat")
        SupplierExtraRate.objects.create(extra=extra, valid_from=date(2026, 1, 1), calculation_type="PER_DAY", amount_gross=20, maximum_amount_gross=50)
        data, response = self.review(
            extra_choices=["CHILD_SEAT"], child_seat_quantity=2,
            child_seat_1_age="2", child_seat_1_height="88",
            child_seat_1_type_number="Seat 1",
            child_seat_2_age="6", child_seat_2_height="122",
            child_seat_2_type_number="Booster",
        )
        self.assertContains(response, 'name="child_seat_1_age"')
        self.assertContains(response, 'name="child_seat_2_type_number"')
        self.assertEqual(response.context["result"]["total"], Decimal("400"))
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.extras.get().quantity, 2)
        self.assertEqual(booking.child_seat_details, [
            {"age": "2", "height": "88", "type_number": "Seat 1"},
            {"age": "6", "height": "122", "type_number": "Booster"},
        ])
        supplier_message = self.client.get(
            reverse("quotes:supplier_message", args=[booking.pk])
        )
        self.assertContains(supplier_message, "Child seat 1: age 2, height 88 cm, type/number Seat 1")
        self.assertContains(supplier_message, "Child seat 2: age 6, height 122 cm, type/number Booster")
        booking.save()
        self.assertEqual(booking.total_price_gross, Decimal("400"))

    def test_login_and_option_membership(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.user)
        self.option.is_included = False
        self.option.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_newer_price_list_wins(self):
        old_season = self.rate.season
        price_list = PriceList.objects.create(supplier=self.supplier, name="Replacement", version="v2", effective_from=date(2026, 9, 1), status="ACTIVE")
        season = PriceSeason.objects.create(price_list=price_list, season_code="ALL", season_name="New", rental_date_from=date(2026, 1, 1))
        days = PriceDayRange.objects.create(price_list=price_list, range_code="ALL", label="All", days_from=1)
        rate = VehicleRate.objects.create(season=season, day_range=days, vehicle_group=self.group, daily_rate_gross=150)
        data, response = self.review()
        self.assertEqual(response.context["result"]["total"], Decimal("450"))
        self.create(data, response)
        self.assertEqual(Booking.objects.get().vehicle_rate_id, rate.pk)
        self.assertTrue(PriceSeason.objects.filter(pk=old_season.pk).exists())

    def test_cross_border_tariff_change_requires_new_confirmation(self):
        self.supplier.supplier_code = "01"
        self.supplier.save(update_fields=["supplier_code"])
        extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code="CROSS_BORDER", name="Test border cover")
        rate = SupplierExtraRate.objects.create(extra=extra, valid_from=date(2026, 1, 1), calculation_type="PER_RENTAL", amount_gross=555)
        data, response = self.review(cross_border_requested=True)
        self.assertEqual(response.context["result"]["total"], Decimal("855"))
        rate.amount_gross = 650
        rate.save(update_fields=["amount_gross"])
        updated = self.create(data, response)
        self.assertFalse(Booking.objects.exists())
        self.assertEqual(updated.context["result"]["total"], Decimal("950"))
        self.create(data, updated)
        booking = Booking.objects.get()
        self.assertEqual(booking.total_price_gross, Decimal("950"))
        rate.amount_gross = 700
        rate.save(update_fields=["amount_gross"])
        booking.save()
        booking.refresh_from_db()
        self.assertEqual(booking.total_price_gross, Decimal("950"))

    def test_confirmation_checkbox_is_required_even_with_valid_token(self):
        data, response = self.review()
        self.client.post(self.url, {**data, "action": "create", "review_token": response.context["review_token"]})
        self.assertFalse(Booking.objects.exists())

    def test_out_of_hours_charge_is_reviewed_and_saved(self):
        extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code="OUT_OF_HOURS", name="Night service")
        SupplierExtraRate.objects.create(extra=extra, valid_from=date(2026, 1, 1), calculation_type="PER_UNIT", amount_gross=80)
        data, response = self.review(pickup_time="02:00", return_time="02:00")
        self.assertEqual(response.context["result"]["total"], Decimal("460"))
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.total_price_gross, Decimal("460"))
        booking.save()
        self.assertEqual(booking.total_price_gross, Decimal("460"))

    def test_changed_vehicle_group_is_used(self):
        group = VehicleGroup.objects.create(supplier=self.supplier, group_code="SECOND", group_name="Second car", deposit_amount=300)
        group.comparison_classes.add(VehicleComparisonClass.objects.first())
        VehicleRate.objects.create(season=self.rate.season, day_range=self.rate.day_range, vehicle_group=group, daily_rate_gross=200)
        data, response = self.review(vehicle_group=group.pk)
        self.create(data, response)
        booking = Booking.objects.get()
        self.assertEqual(booking.vehicle_group_id, group.pk)
        self.assertEqual(booking.total_price_gross, Decimal("600"))
