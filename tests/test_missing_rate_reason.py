from datetime import date

from django.test import TestCase

from quotes.services import _missing_rate_reason
from suppliers.models import (
    PriceDayRange, PriceList, PriceSeason, Supplier, VehicleGroup, VehicleRate,
)


class MissingRateReasonTests(TestCase):
    def test_expired_price_list_reports_its_actual_end_date(self):
        supplier = Supplier.objects.create(supplier_code="TEST", supplier_name="Test rental")
        group = VehicleGroup.objects.create(supplier=supplier, group_code="TEST", group_name="Test car")
        price_list = PriceList.objects.create(
            supplier=supplier, name="Test list", version="test-v1",
            effective_from=date(2026, 1, 1), effective_to=date(2027, 1, 31), status="ACTIVE",
        )
        season = PriceSeason.objects.create(
            price_list=price_list, season_code="ALL", season_name="Test season",
            rental_date_from=date(2026, 1, 1), rental_date_to=date(2027, 1, 31),
        )
        day_range = PriceDayRange.objects.create(
            price_list=price_list, range_code="WEEK", label="Test days", days_from=7, days_to=14,
        )
        VehicleRate.objects.create(
            season=season, day_range=day_range, vehicle_group=group, daily_rate_gross=100,
        )

        reason = _missing_rate_reason(group, date(2027, 8, 20), 9)
        self.assertIn("31.01.2027", reason)
