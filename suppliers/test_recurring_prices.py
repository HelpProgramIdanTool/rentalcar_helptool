from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from customers.models import Customer
from employees.models import SubAgent
from quotes.forms import FirstInquiryForm
from quotes.models import Quote
from quotes.services import calculate_quote_options, _extra_price
from suppliers.models import (
    Supplier, VehicleGroup, VehicleComparisonClass, PriceList, PriceSeason,
    PriceDayRange, VehicleRate, SupplierExtra, SupplierExtraRate,
)


class RecurringSeasonTests(SimpleTestCase):
    def test_repeated_season_keeps_exact_day_boundaries(self):
        price_list = PriceList(repeat_annually=True)
        season = PriceSeason(price_list=price_list, rental_date_from=date(2026, 6, 24), rental_date_to=date(2026, 8, 21))
        for year in (2027, 2040):
            self.assertFalse(season.applies_on(date(year, 6, 23)))
            self.assertTrue(season.applies_on(date(year, 6, 24)))
            self.assertTrue(season.applies_on(date(year, 8, 21)))
            self.assertFalse(season.applies_on(date(year, 8, 22)))

    def test_repeated_winter_season_crosses_new_year(self):
        season = PriceSeason(price_list=PriceList(repeat_annually=True),
            rental_date_from=date(2026, 8, 22), rental_date_to=date(2027, 1, 31))
        self.assertTrue(season.applies_on(date(2030, 1, 31)))
        self.assertTrue(season.applies_on(date(2030, 8, 22)))
        self.assertFalse(season.applies_on(date(2030, 2, 1)))

    def test_months_repeat_without_an_expiry_year(self):
        season = PriceSeason(recurring_months=[1, 2, 3, 4, 5, 10, 11])
        for year in (2026, 2027, 2040):
            self.assertTrue(season.applies_on(date(year, 5, 31)))
            self.assertFalse(season.applies_on(date(year, 6, 1)))
            self.assertFalse(season.applies_on(date(year, 12, 1)))

    def test_dated_seasons_keep_inclusive_boundaries(self):
        season = PriceSeason(rental_date_from=date(2026, 5, 1), rental_date_to=date(2026, 5, 31))
        self.assertTrue(season.applies_on(date(2026, 5, 31)))
        self.assertFalse(season.applies_on(date(2027, 5, 31)))

    def test_invalid_month_configuration_is_rejected(self):
        for months in ([0], [13], ['5'], [True], {'month': 5}):
            with self.subTest(months=months), self.assertRaises(ValidationError):
                PriceSeason(recurring_months=months, rental_date_from=date(2026, 1, 1)).clean()

    def test_daily_limit_applies_per_requested_unit(self):
        rate = SupplierExtraRate(calculation_type='PER_DAY', amount_gross=Decimal(7), maximum_amount_gross=Decimal(70))
        self.assertEqual(_extra_price(rate, 9, Decimal(2)), Decimal(126))
        self.assertEqual(_extra_price(rate, 10, Decimal(2)), Decimal(140))
        self.assertEqual(_extra_price(rate, 15, Decimal(2)), Decimal(140))


class RecurringQuoteTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(supplier_code='TEST-REPEAT', supplier_name='Test Repeat', included_driver_count=1, subagent_pricing_method='UNAVAILABLE')
        self.group = VehicleGroup.objects.create(supplier=self.supplier, group_code='OWN-GROUP', group_name='Own group')
        self.comparison = VehicleComparisonClass.objects.create(code='TEST-OWN', name='Own class')
        self.comparison.vehicle_groups.add(self.group)
        price_list = PriceList.objects.create(supplier=self.supplier, name='Test', version='TEST', effective_from=date(2026, 1, 1), status='ACTIVE')
        days = PriceDayRange.objects.create(price_list=price_list, range_code='ALL', days_from=1)
        for code, months, amount in [('LOW', [1,2,3,4,5,10,11], 100), ('HIGH', [6,7,8,9,12], 200)]:
            season = PriceSeason.objects.create(price_list=price_list, season_code=code, season_name=code, rental_date_from=date(2026,1,1), recurring_months=months)
            VehicleRate.objects.create(season=season, vehicle_group=self.group, day_range=days, daily_rate_gross=amount)
        extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code='ADDITIONAL_DRIVER', name='TEST-DRIVER')
        SupplierExtraRate.objects.create(extra=extra, calculation_type='PER_DAY', amount_gross=7, maximum_amount_gross=70, valid_from=date(2026,1,1))
        self.quote = Quote.objects.create(customer=Customer.objects.create(email='invented@example.com'), pickup_datetime=datetime(2027,5,30,12,tzinfo=ZoneInfo('Europe/Warsaw')), return_datetime=datetime(2027,6,3,12,tzinfo=ZoneInfo('Europe/Warsaw')), driver_count=2)
        self.quote.requested_vehicle_classes.add(self.comparison)
        self.quote.requested_vehicle_groups.add(self.group)
        self.quote.requested_suppliers.add(self.supplier)

    def test_pickup_season_covers_entire_rental_and_second_driver_is_charged(self):
        result, = calculate_quote_options(self.quote)
        self.assertTrue(result['available'])
        self.assertEqual(result['base'], Decimal(400))
        self.assertEqual(result['extras_total'], Decimal(28))
        self.assertEqual(result['total'], Decimal(428))

    def test_expired_last_price_list_repeats_and_newer_price_list_wins(self):
        from bookings.models import Booking
        old = self.supplier.price_lists.get(version='TEST')
        old.effective_to = date(2026, 12, 31)
        old.save(update_fields=['effective_to'])
        old.seasons.update(recurring_months=[], rental_date_from=date(2026, 1, 1),
                           rental_date_to=date(2026, 12, 31))
        old.seasons.filter(season_code='HIGH').update(is_active=False)
        result, = calculate_quote_options(self.quote)
        self.assertTrue(result['available'])
        self.assertEqual(result['daily_rate'], Decimal(100))
        booking = Booking.objects.create(customer=self.quote.customer, supplier=self.supplier,
            vehicle_group=self.group, pickup_datetime=self.quote.pickup_datetime,
            return_datetime=self.quote.return_datetime)
        self.assertEqual(booking.vehicle_daily_rate_gross_snapshot, Decimal(100))
        newer = PriceList.objects.create(supplier=self.supplier, version='NEW', name='New',
            effective_from=date(2027, 1, 1), effective_to=date(2027, 12, 31), status='ACTIVE')
        season = PriceSeason.objects.create(price_list=newer, season_code='ALL', season_name='TEST',
            rental_date_from=date(2027, 1, 1), rental_date_to=date(2027, 12, 31))
        days = PriceDayRange.objects.create(price_list=newer, range_code='ALL', days_from=1)
        VehicleRate.objects.create(season=season, day_range=days, vehicle_group=self.group, daily_rate_gross=300)
        result, = calculate_quote_options(self.quote)
        self.assertEqual(result['daily_rate'], Decimal(300))

    def test_two_included_drivers_have_no_extra_charge(self):
        self.supplier.included_driver_count = 2
        self.supplier.save(update_fields=['included_driver_count'])
        result, = calculate_quote_options(self.quote)
        self.assertEqual(result['extras_total'], Decimal(0))
        self.assertEqual(result['total'], Decimal(400))
        self.assertFalse(any(line.get('extra') and line['extra'].extra_code == 'ADDITIONAL_DRIVER'
                             for line in result['extra_lines']))
        self.quote.driver_count = 3
        result, = calculate_quote_options(self.quote)
        self.assertEqual(result['extras_total'], Decimal(28))

    def test_december_in_later_year_uses_high_season(self):
        self.quote.pickup_datetime = self.quote.pickup_datetime.replace(year=2040, month=12, day=1)
        self.quote.return_datetime = self.quote.pickup_datetime + timedelta(days=4)
        result, = calculate_quote_options(self.quote)
        self.assertEqual(result['daily_rate'], Decimal(200))

    def test_unsupported_supplier_never_uses_standard_price_for_subagent(self):
        self.quote.sub_agent = SubAgent.objects.create(name='Test Agent', code_prefix='TT')
        self.assertEqual(calculate_quote_options(self.quote), [])

    def test_form_exposes_own_group_and_subagent_restriction(self):
        form = FirstInquiryForm()
        self.assertIn(self.group, form.fields['vehicle_groups'].queryset)
        self.assertIn(self.supplier.pk, form.subagent_unavailable_supplier_ids)
        self.assertIn(self.supplier.pk, form.initial['suppliers'])

    def test_supplier_benefits_are_read_from_data_without_standard_promises(self):
        self.supplier.included_benefits = ['TEST-BENEFIT-HE']
        self.supplier.save()
        result, = calculate_quote_options(self.quote)
        from quotes.services import STANDARD_INCLUDED_ITEMS
        self.assertIn('TEST-BENEFIT-HE', result['included_items'])
        for item in STANDARD_INCLUDED_ITEMS:
            self.assertNotIn(item, result['included_items'])

    def test_form_rejects_unsupported_group_for_subagent(self):
        agent = SubAgent.objects.create(name='Test Agent', code_prefix='TT')
        form = FirstInquiryForm(data={
            'email': 'invented@example.com', 'sub_agent': agent.pk,
            'vehicle_groups': [self.group.pk], 'suppliers': [self.supplier.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertIn('vehicle_groups', form.errors)

    def test_foreign_return_adds_city_fee_and_cross_border_once(self):
        from suppliers.models import OfferCity, CityServiceRule
        city = OfferCity.objects.create(name='Test Foreign City', label='Test City', country='Test Country')
        return_extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code='FOREIGN_RETURN', name='TEST-RETURN')
        border_extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code='CROSS_BORDER', name='TEST-BORDER')
        for extra, amount in ((return_extra, 80), (border_extra, 30)):
            SupplierExtraRate.objects.create(extra=extra, calculation_type='PER_UNIT', amount_gross=amount, valid_from=date(2026,1,1))
        CityServiceRule.objects.create(city=city, supplier=self.supplier, extra=return_extra, supports_pickup=False)
        self.quote.driver_count = 1
        self.quote.return_city = city.name
        self.quote.cross_border_requested = True
        result, = calculate_quote_options(self.quote)
        self.assertTrue(result['available'])
        self.assertEqual(result['extras_total'], Decimal(110))
        self.assertEqual(result['total'], Decimal(510))
        self.assertEqual({line['extra'].extra_code for line in result['extra_lines']}, {'FOREIGN_RETURN', 'CROSS_BORDER'})
        self.quote.pickup_city = city.name
        self.quote.return_city = 'Test Domestic City'
        result, = calculate_quote_options(self.quote)
        self.assertFalse(result['available'])
        self.assertIn('Получение', result['reason'])
