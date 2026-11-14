from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from customers.models import Customer
from suppliers.models import Supplier, SupplierExtra, SupplierExtraRate, VehicleGroup, VehicleComparisonClass, OfferCity, PriceList, PriceSeason, PriceDayRange, VehicleRate
from .models import Quote, QuoteOption
from .one_way import domestic_different_cities
from .services import calculate_quote_options, _extra_price
from .price_validation import quote_price_issues, balanced_snapshot


class OneWaySmallTests(SimpleTestCase):
    def test_fee_must_be_included_in_both_lines_and_total(self):
        option=SimpleNamespace(total_price_gross=Decimal('400'),manual_adjustment_amount=Decimal(0))
        snapshot={'base':'300','extras_total':'100','lines':[{'price':'100'}]}
        self.assertTrue(balanced_snapshot(option,snapshot))
        option.total_price_gross=Decimal('300')
        self.assertFalse(balanced_snapshot(option,snapshot))
    def test_different_polish_cities_only(self):
        self.assertTrue(domestic_different_cities('TEST-A','TEST-B','Poland','PL'))
        self.assertFalse(domestic_different_cities('TEST-A',' test-a ','Poland','Poland'))
        self.assertFalse(domestic_different_cities('TEST-A','TEST-B','Poland','Czechia'))
        self.assertFalse(domestic_different_cities('TEST-A','TEST-B','','Poland'))

    def test_once_per_rental_uses_the_rate_value_not_a_code_constant(self):
        rate=SimpleNamespace(calculation_type='PER_RENTAL',amount_gross=Decimal('100'),minimum_amount_gross=None,maximum_amount_gross=None,formula_config={})
        self.assertEqual(_extra_price(rate,Decimal(3)),Decimal('100'))
        rate.amount_gross=Decimal('150')
        self.assertEqual(_extra_price(rate,Decimal(3)),Decimal('150'))
        rate.amount_gross=Decimal(0)
        self.assertEqual(_extra_price(rate,Decimal(4)),Decimal(0))


class OneWayCalculationTests(TestCase):
    def setUp(self):
        self.supplier=Supplier.objects.create(supplier_code='TEST-ROUTE',supplier_name='TEST-SUPPLIER')
        self.group=VehicleGroup.objects.create(supplier=self.supplier,group_code='TEST-GROUP',group_name='TEST-GROUP')
        self.comparison=VehicleComparisonClass.objects.create(code='TEST-ROUTE',name='TEST-CLASS')
        self.group.comparison_classes.add(self.comparison)
        self.start=(timezone.localtime()+timedelta(days=10)).replace(hour=10,minute=0,second=0,microsecond=0)
        price=PriceList.objects.create(supplier=self.supplier,name='TEST',version='TEST',effective_from=self.start.date()-timedelta(days=1),status='ACTIVE')
        season=PriceSeason.objects.create(price_list=price,season_code='TEST',season_name='TEST',rental_date_from=self.start.date()-timedelta(days=1))
        band=PriceDayRange.objects.create(price_list=price,range_code='TEST',label='TEST',days_from=1)
        VehicleRate.objects.create(season=season,day_range=band,vehicle_group=self.group,daily_rate_gross=100)
        for name,country in [('TEST-A','Poland'),('TEST-B','Poland'),('TEST-C','Czechia')]:
            OfferCity.objects.create(name=name,label=name,country=country,cross_border_required=False)
        self.extra=SupplierExtra.objects.create(supplier=self.supplier,extra_code='TEST-FEE',name='TEST-ONE-WAY-HE',automatic_rule='DOMESTIC_ONE_WAY')
        self.short=SupplierExtraRate.objects.create(extra=self.extra,rate_code='SHORT',calculation_type='PER_RENTAL',amount_gross=100,valid_from=self.start.date()-timedelta(days=1),days_from=1,days_to=3)
        self.free=SupplierExtraRate.objects.create(extra=self.extra,rate_code='LONG',calculation_type='PER_RENTAL',amount_gross=0,valid_from=self.start.date()-timedelta(days=1),days_from=4)

    def quote(self,days=3,**changes):
        customer=Customer.objects.create(first_name='TEST',last_name='',phone_1='')
        values=dict(customer=customer,pickup_datetime=self.start,return_datetime=self.start+timedelta(days=days),pickup_city='TEST-A',return_city='TEST-B',pickup_service='AIRPORT',return_service='AIRPORT',pickup_location_text='TEST-A',return_location_text='TEST-B')
        values.update(changes)
        quote=Quote.objects.create(**values)
        quote.requested_vehicle_groups.add(self.group)
        quote.requested_vehicle_classes.add(self.comparison)
        quote.requested_suppliers.add(self.supplier)
        return quote

    def calculate(self,quote):
        return calculate_quote_options(quote,vehicle_group=self.group)[0]

    def test_day_bands_once_and_all_calculation_paths(self):
        for days,fee in [(1,100),(3,100),(4,0),(10,0)]:
            with self.subTest(days=days):
                quote=self.quote(days)
                option=self.calculate(quote)
                self.assertTrue(option['available'])
                self.assertEqual(option['total'],Decimal(days*100+fee))
                lines=[line for line in option['extra_lines'] if line.get('extra')==self.extra]
                self.assertEqual(len(lines),1)
                self.assertEqual(lines[0]['price'],Decimal(fee))
                self.assertEqual(calculate_quote_options(quote)[0]['total'],option['total'])

    def test_fourth_billable_day_is_free_after_existing_grace_hour(self):
        quote=self.quote(return_datetime=self.start+timedelta(days=3,hours=1,minutes=1))
        self.assertEqual(quote.rental_days,4)
        self.assertEqual(self.calculate(quote)['total'],Decimal('400'))

    def test_existing_free_hour_does_not_change_the_day_band(self):
        quote=self.quote(return_datetime=self.start+timedelta(days=3,minutes=1))
        self.assertEqual(quote.rental_days,3)
        self.assertEqual(self.calculate(quote)['total'],Decimal('400'))

    def test_same_city_different_service_has_no_fee(self):
        quote=self.quote(return_city='TEST-A',return_service='ADDRESS',return_address='TEST-HOTEL')
        self.assertFalse(any(line.get('extra')==self.extra for line in self.calculate(quote)['extra_lines']))

    def test_foreign_city_does_not_receive_domestic_fee(self):
        quote=self.quote(return_city='TEST-C')
        self.assertFalse(any(line.get('extra')==self.extra for line in self.calculate(quote)['extra_lines']))

    def test_price_and_customer_wording_come_from_data(self):
        self.short.amount_gross=150;self.short.save()
        self.extra.customer_name_he='TEST-CUSTOMER-ONE-WAY-HE';self.extra.save()
        option=self.calculate(self.quote())
        self.assertEqual(option['total'],Decimal('450'))
        self.assertIn('TEST-CUSTOMER-ONE-WAY-HE',[line['name'] for line in option['extra_lines']])

    def test_missing_rate_or_unknown_country_blocks_complete_price(self):
        self.short.is_active=False;self.short.save()
        self.assertFalse(self.calculate(self.quote())['available'])
        self.assertFalse(self.calculate(self.quote(return_city='UNKNOWN'))['available'])

    def test_fee_cannot_be_requested_twice(self):
        quote=self.quote();quote.extra_requests={'TEST-FEE':2};quote.save()
        option=self.calculate(quote)
        self.assertEqual(option['total'],Decimal('400'))

    def test_other_supplier_without_rule_is_unchanged(self):
        self.extra.automatic_rule='';self.extra.save()
        self.assertEqual(self.calculate(self.quote())['total'],Decimal('300'))

    def test_old_saved_quote_missing_fee_requires_recalculation(self):
        quote=self.quote()
        QuoteOption.objects.create(quote=quote,supplier=self.supplier,vehicle_group=self.group,comparison_class=self.comparison,supplier_name_snapshot='TEST',vehicle_group_name_snapshot='TEST',total_price_gross=300,calculation_snapshot={'base':'300','extras_total':'0','lines':[]})
        self.assertTrue(quote_price_issues(quote))
