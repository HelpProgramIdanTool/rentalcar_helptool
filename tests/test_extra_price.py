from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from quotes.services import _extra_price, _quoted_extra_price


def make_rate(calculation_type="PER_DAY", amount="50", minimum=None, maximum=None,
              formula=None):
    """Invent a rate for a calculation; no supplier records are needed."""
    return SimpleNamespace(
        calculation_type=calculation_type,
        amount_gross=Decimal(amount),
        minimum_amount_gross=Decimal(minimum) if minimum is not None else None,
        maximum_amount_gross=Decimal(maximum) if maximum is not None else None,
        formula_config=formula or {},
    )


class ExtraPriceTests(SimpleTestCase):
    def test_cross_border_price_comes_from_selected_rate(self):
        extra = SimpleNamespace(supplier=SimpleNamespace(supplier_code="01"), extra_code="CROSS_BORDER")
        rate = make_rate(calculation_type="PER_RENTAL", amount="555")
        self.assertEqual(_quoted_extra_price(extra, rate, Decimal("5")), Decimal("555"))

    def test_existing_cross_border_rate_keeps_its_price(self):
        extra = SimpleNamespace(supplier=SimpleNamespace(supplier_code="01"), extra_code="CROSS_BORDER")
        rate = make_rate(calculation_type="PER_RENTAL", amount="499")
        self.assertEqual(_quoted_extra_price(extra, rate, Decimal("5")), Decimal("499"))

    def test_daily_price_multiplies_by_rental_days(self):
        self.assertEqual(_extra_price(make_rate(), Decimal("4")), Decimal("200"))

    def test_per_rental_price_does_not_depend_on_days(self):
        rate = make_rate(calculation_type="PER_RENTAL")
        for days in ("1", "4", "20"):
            with self.subTest(days=days):
                self.assertEqual(_extra_price(rate, Decimal(days)), Decimal("50"))

    def test_driver_daily_price_counts_days_and_drivers(self):
        rate = make_rate(calculation_type="PER_DRIVER_DAY")
        self.assertEqual(_extra_price(rate, Decimal("4"), Decimal("2")), Decimal("400"))

    def test_formula_adds_base_and_daily_charge(self):
        rate = make_rate(calculation_type="FORMULA", amount="999", formula={
            "per_rental_gross": "100", "per_rental_day_gross": "25",
        })
        self.assertEqual(_extra_price(rate, Decimal("4")), Decimal("200"))

    def test_formula_uses_rate_amount_when_base_is_not_specified(self):
        rate = make_rate(calculation_type="FORMULA", formula={"per_rental_day_gross": "25"})
        self.assertEqual(_extra_price(rate, Decimal("4")), Decimal("150"))

    def test_fixed_formula_total_does_not_depend_on_days(self):
        rate = make_rate(calculation_type="FORMULA", amount="999", formula={
            "total_per_rental_gross": "100",
        })
        for days in ("1", "4", "20"):
            with self.subTest(days=days):
                self.assertEqual(_extra_price(rate, Decimal(days)), Decimal("100"))

    def test_minimum_applies_below_limit_but_does_not_replace_higher_price(self):
        rate = make_rate(minimum="100")
        for days, expected in (("1", "100"), ("2", "100"), ("3", "150")):
            with self.subTest(days=days):
                self.assertEqual(_extra_price(rate, Decimal(days)), Decimal(expected))

    def test_maximum_applies_above_limit_but_does_not_replace_lower_price(self):
        rate = make_rate(maximum="100")
        for days, expected in (("1", "50"), ("2", "100"), ("3", "100")):
            with self.subTest(days=days):
                self.assertEqual(_extra_price(rate, Decimal(days)), Decimal(expected))

    def test_two_items_double_the_price(self):
        self.assertEqual(_extra_price(make_rate(), Decimal("4"), Decimal("2")), Decimal("400"))

    def test_maximum_is_per_item_not_per_whole_order(self):
        rate = make_rate(maximum="100")
        self.assertEqual(_extra_price(rate, Decimal("4"), Decimal("2")), Decimal("200"))

    def test_minimum_is_per_item_not_per_whole_order(self):
        rate = make_rate(minimum="100")
        self.assertEqual(_extra_price(rate, Decimal("1"), Decimal("2")), Decimal("200"))

    def test_formula_price_also_respects_cap_and_quantity(self):
        rate = make_rate(calculation_type="FORMULA", maximum="150", formula={
            "per_rental_gross": "100", "per_rental_day_gross": "25",
        })
        self.assertEqual(_extra_price(rate, Decimal("4"), Decimal("2")), Decimal("300"))

    def test_fractional_prices_keep_exact_cents(self):
        rate = make_rate(amount="12.35")
        self.assertEqual(_extra_price(rate, Decimal("3"), Decimal("2")), Decimal("74.10"))
