from types import SimpleNamespace
from decimal import Decimal
from django.test import SimpleTestCase, TestCase
from .airport_location import is_airport_location, airport_service_conflicts
from .services import _service_extra_requests


class AirportLocationTests(SimpleTestCase):
    def test_english_airport_in_hebrew_email_is_not_imported_as_address(self):
        from .inquiry_import import parse_free_text_inquiry
        data, _, _ = parse_free_text_inquiry('איסוף : 20.10.27\nלודז (Airport) בשעה 10.00\nהחזרה : 22.10.27\nורשה נמל תעופה בשעה 04.00')
        self.assertEqual(data['pickup_service'], 'AIRPORT')

    def test_explicit_airport_names_in_supported_languages(self):
        for text in ['Airport', 'Łódź Airport', 'Lotnisko Łódź', 'Port Lotniczy', 'Аэропорт Лодзь', 'שדה תעופה', 'נמל התעופה']:
            with self.subTest(text=text):
                self.assertTrue(is_airport_location(text))

    def test_airport_hotel_is_not_airport_pickup(self):
        for text in ['Airport Hotel', 'מלון ליד שדה תעופה', 'Отель аэропорт', 'Main Street 5', '']:
            self.assertFalse(is_airport_location(text))

    def test_conflict_requires_explicit_address_and_airport_name(self):
        self.assertEqual(airport_service_conflicts({'pickup_service':'ADDRESS','pickup_address':'Airport'}),['pickup'])
        self.assertEqual(airport_service_conflicts({'pickup_service':'AIRPORT','pickup_address':'Airport'}),[])

    def test_confirmed_airport_pickup_requests_one_airport_fee(self):
        quote=SimpleNamespace(pickup_service='AIRPORT',return_service='AIRPORT')
        self.assertEqual(_service_extra_requests(quote,'02'),{'AIRPORT_FEE':Decimal(1)})


class AirportQuoteFlowTests(TestCase):
    def setUp(self):
        from suppliers.test_recurring_prices import RecurringQuoteTests
        RecurringQuoteTests.setUp(self)

    def test_saved_address_airport_cannot_produce_incomplete_price(self):
        from .services import calculate_quote_options
        self.quote.pickup_service='ADDRESS'
        self.quote.pickup_address='Airport'
        option,=calculate_quote_options(self.quote)
        self.assertFalse(option['available'])
        self.assertIn('аэропорт',option['reason'])

    def test_airport_pickup_adds_configured_fee_to_final_total(self):
        from datetime import date
        from suppliers.models import SupplierExtra,SupplierExtraRate
        from .services import calculate_quote_options
        self.supplier.supplier_code='02'
        self.supplier.save(update_fields=['supplier_code'])
        extra=SupplierExtra.objects.create(supplier=self.supplier,extra_code='AIRPORT_FEE',name='TEST-AIRPORT-FEE')
        SupplierExtraRate.objects.create(extra=extra,amount_gross=17,calculation_type='PER_RENTAL',valid_from=date(2026,1,1))
        self.quote.pickup_service='AIRPORT'
        option,=calculate_quote_options(self.quote)
        self.assertTrue(option['available'])
        self.assertEqual(option['total'],Decimal(445))
        self.assertEqual([line['price'] for line in option['extra_lines'] if line['extra'].extra_code=='AIRPORT_FEE'],[Decimal(17)])

    def test_form_rejects_address_airport_before_saving(self):
        from .forms import FirstInquiryForm
        # Use only the pricing inputs so no customer or supplier is created.
        form=FirstInquiryForm({'pickup_date':'25.11.2027','return_date':'26.11.2027',
            'pickup_time':'10:00','return_time':'10:00','pickup_city':'Łódź',
            'return_city':'Warszawa','pickup_service':'ADDRESS','pickup_address':'Airport',
            'return_service':'AIRPORT','driver_count':'1','rental_country':'PL'},pricing_only=True)
        self.assertFalse(form.is_valid())
        self.assertIn('pickup_service',form.errors)
