from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from config.rental_duration import calculate_rental_days


class RentalDurationTests(SimpleTestCase):
    """Check the agreed free-hour rule directly, without a database."""

    def setUp(self):
        self.pickup = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)

    def test_exactly_three_days_costs_three_days(self):
        returned = self.pickup + timedelta(days=3)
        self.assertEqual(calculate_rental_days(self.pickup, returned), 3)

    def test_exactly_twenty_four_hours_costs_one_day(self):
        returned = self.pickup + timedelta(hours=24)
        self.assertEqual(calculate_rental_days(self.pickup, returned), 1)

    def test_forty_extra_minutes_are_free(self):
        returned = self.pickup + timedelta(days=2, minutes=40)
        self.assertEqual(calculate_rental_days(self.pickup, returned), 2)

    def test_exactly_one_extra_hour_is_free(self):
        for days in (1, 3):
            with self.subTest(days=days):
                returned = self.pickup + timedelta(days=days, hours=1)
                self.assertEqual(calculate_rental_days(self.pickup, returned), days)

    def test_one_minute_beyond_free_hour_adds_a_day(self):
        for days in (1, 3):
            with self.subTest(days=days):
                returned = self.pickup + timedelta(days=days, hours=1, minutes=1)
                self.assertEqual(calculate_rental_days(self.pickup, returned), days + 1)

    def test_same_pickup_and_return_has_minimum_one_day(self):
        self.assertEqual(calculate_rental_days(self.pickup, self.pickup), 1)

    def test_return_before_pickup_has_minimum_one_day(self):
        returned = self.pickup - timedelta(minutes=1)
        self.assertEqual(calculate_rental_days(self.pickup, returned), 1)

    def test_spring_clock_change_counts_elapsed_hours(self):
        warsaw = ZoneInfo("Europe/Warsaw")
        pickup = datetime(2026, 3, 28, 12, tzinfo=warsaw)
        returned = datetime(2026, 3, 29, 13, 1, tzinfo=warsaw)
        # The clock jumps forward, so only 24 hours and 1 minute pass.
        self.assertEqual(calculate_rental_days(pickup, returned), 1)
