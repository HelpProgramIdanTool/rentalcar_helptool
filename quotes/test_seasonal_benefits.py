from datetime import date
from django.test import SimpleTestCase
from .seasonal_benefits import seasonal_included_items


class SeasonalBenefitsTests(SimpleTestCase):
    def test_winter_overlap_and_boundaries(self):
        rules = [{'start_month': 11, 'start_day': 1, 'end_month': 4, 'end_day': 30,
                  'text': 'TEST-SEASONAL-BENEFIT'}]
        for start, end, expected in [
            (date(2026, 10, 30), date(2026, 10, 31), False),
            (date(2026, 10, 31), date(2026, 11, 1), True),
            (date(2026, 11, 1), date(2026, 11, 2), True),
            (date(2026, 12, 30), date(2027, 1, 3), True),
            (date(2027, 4, 30), date(2027, 5, 1), True),
            (date(2027, 5, 1), date(2027, 10, 31), False),
            (date(2027, 10, 1), date(2028, 5, 1), True),
            (date(2028, 2, 29), date(2028, 3, 1), True),
        ]:
            with self.subTest(start=start, end=end):
                self.assertEqual(seasonal_included_items(start, end, rules),
                    ['TEST-SEASONAL-BENEFIT'] if expected else [])

    def test_period_and_wording_come_from_configuration(self):
        rules = [{'start_month': 6, 'start_day': 1, 'end_month': 8, 'end_day': 31,
                  'text': 'TEST-SUMMER'}]
        self.assertEqual(seasonal_included_items(date(2027, 7, 1), date(2027, 7, 2), rules), ['TEST-SUMMER'])
        self.assertEqual(seasonal_included_items(date(2027, 1, 1), date(2027, 1, 2), rules), [])
