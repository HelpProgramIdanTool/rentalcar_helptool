from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase

from bookings.models import Booking
from customers.models import Customer
from employees.models import SubAgent
from quotes.models import Quote
from quotes.services import calculate_quote_options
from suppliers.models import (
    PriceDayRange, PriceList, PriceSeason, Supplier, SupplierExtra,
    SupplierExtraRate, VehicleComparisonClass, VehicleGroup, VehicleRate,
)


class SubagentPricingTests(TestCase):
    def setUp(self):
        self.agent = SubAgent.objects.create(name="Partner", code_prefix="AB")
        self.customer = Customer.objects.create(email="subagent-test@example.com")
        self.comparison = VehicleComparisonClass.objects.first()

    def quote(self, supplier, group):
        pickup = datetime(2026, 10, 1, 10, tzinfo=ZoneInfo("Europe/Warsaw"))
        quote = Quote.objects.create(
            customer=self.customer, sub_agent=self.agent,
            pickup_datetime=pickup, return_datetime=pickup + timedelta(days=3),
            pickup_location_text="Kraków", return_location_text="Kraków",
        )
        group.comparison_classes.add(self.comparison)
        return quote

    def rate(self, supplier, group, amount, audience, version):
        price_list = PriceList.objects.create(
            supplier=supplier, name=version, version=version,
            effective_from=date(2026, 1, 1), status="ACTIVE", audience=audience,
        )
        season = PriceSeason.objects.create(
            price_list=price_list, season_code="ALL", season_name="All",
            rental_date_from=date(2026, 1, 1),
        )
        days = PriceDayRange.objects.create(
            price_list=price_list, range_code="ALL", label="All", days_from=1,
        )
        return VehicleRate.objects.create(
            season=season, day_range=days, vehicle_group=group,
            daily_rate_gross=amount,
        )

    def test_one_rent_adds_four_percent_to_vehicle_and_extras(self):
        supplier = Supplier.objects.create(
            supplier_code="02X", supplier_name="One test",
            subagent_pricing_method="PERCENT_TOTAL", subagent_markup_percent=4,
        )
        group = VehicleGroup.objects.create(
            supplier=supplier, group_code="T", group_name="Test", deposit_amount=0,
        )
        self.rate(supplier, group, 100, "STANDARD", "standard")
        extra = SupplierExtra.objects.create(
            supplier=supplier, extra_code="MANDATORY", name="Mandatory",
            is_mandatory=True,
        )
        SupplierExtraRate.objects.create(
            extra=extra, calculation_type="PER_RENTAL", amount_gross=50,
            valid_from=date(2026, 1, 1),
        )

        result = calculate_quote_options(self.quote(supplier, group), vehicle_group=group)[0]

        self.assertEqual(result["base"], Decimal("300"))
        self.assertEqual(result["extras_total"], Decimal("50"))
        self.assertEqual(result["subagent_adjustment"], Decimal("14.00"))
        self.assertEqual(result["total"], Decimal("364.00"))

    def test_kaizen_uses_shared_subagent_price_list(self):
        supplier = Supplier.objects.create(
            supplier_code="01X", supplier_name="Kaizen test",
            subagent_pricing_method="DEDICATED",
        )
        group = VehicleGroup.objects.create(
            supplier=supplier, group_code="T", group_name="Test", deposit_amount=0,
        )
        self.rate(supplier, group, 100, "STANDARD", "standard")
        selected = self.rate(supplier, group, 80, "SUBAGENT", "subagent")

        result = calculate_quote_options(self.quote(supplier, group), vehicle_group=group)[0]

        self.assertEqual(result["vehicle_rate"], selected)
        self.assertEqual(result["total"], Decimal("240"))

    def test_supplier_number_is_shown_with_agent_prefix_without_separator(self):
        booking = Booking(sub_agent=self.agent, supplier_booking_number="123456")
        self.assertEqual(booking.marked_supplier_booking_number, "AB123456")
