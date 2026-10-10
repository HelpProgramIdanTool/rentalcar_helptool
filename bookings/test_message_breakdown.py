from decimal import Decimal
from types import SimpleNamespace
from django.test import SimpleTestCase
from .message_content import price_breakdown


class MessageBreakdownTests(SimpleTestCase):
    def booking(self, **changes):
        values = dict(vehicle_price_gross=Decimal('245'), vehicle_daily_rate_gross_snapshot=Decimal('245'),
                      rental_days=1, total_price_gross=Decimal('445'), currency='PLN',
                      manual_adjustment_amount=Decimal('100'), subagent_price_adjustment_amount=Decimal('0'))
        values.update(changes)
        return SimpleNamespace(**values)

    def test_manual_fee_is_included_without_repricing(self):
        extra = SimpleNamespace(calculated_price_gross=Decimal('100'), included_in_total=True, calculation_complete=True)
        self.assertEqual(price_breakdown(self.booking(), [extra]), '245+100+100=445 PLN')

    def test_markup_and_mismatch(self):
        self.assertEqual(price_breakdown(self.booking(subagent_price_adjustment_amount=Decimal('100')), []), '245+100+100=445 PLN')
        self.assertIn('please verify breakdown', price_breakdown(self.booking(), []))
