from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, Mock
from django.test import SimpleTestCase
from scripts.partner_design_prices import calculate


class LocalDesignCalculatorTests(SimpleTestCase):
    def payload(self):
        return dict(pickupCity='Kraków',returnCity='Kraków',pickupService='AIRPORT',
                    returnService='AIRPORT',pickupDate='01.12.2030',returnDate='05.12.2030',
                    pickupTime='10:00',returnTime='10:30',seats='0',gear='אוטומטית')

    @patch('suppliers.models.OfferCity.objects.filter')
    @patch('partners.services.calculate_options')
    def test_price_and_deposit_are_read_from_shared_calculator(self,calculator,cities):
        cities.return_value.values_list.return_value=[]
        categories=Mock()
        categories.filter.return_value.values_list.return_value=['TEST CATEGORY']
        group=SimpleNamespace(customer_name_he='TEST GROUP',group_name='FALLBACK',
                              transmission='AUTOMATIC',form_categories=categories)
        calculator.return_value={7:dict(group=group,supplier=SimpleNamespace(supplier_name='TEST SUPPLIER'),
                                       models='TEST MODEL',total=Decimal('100.00'),currency='PLN',
                                       deposit_amount=Decimal('50.00'),deposit_currency='PLN')}
        result=calculate(self.payload())
        calculator.assert_called_once()
        self.assertEqual(result['options'][0]['total'],'100.00')
        self.assertEqual(result['options'][0]['deposit'],'50.00')
        self.assertEqual(result['options'][0]['group'],'TEST GROUP')
        self.assertEqual(result['options'][0]['categories'],['TEST CATEGORY'])
        group.transmission='MANUAL'
        self.assertEqual(calculate(self.payload())['options'],[])

    @patch('suppliers.models.OfferCity.objects.filter')
    @patch('partners.services.calculate_options')
    def test_unlisted_city_is_not_silently_quoted(self,calculator,cities):
        cities.return_value.values_list.return_value=[]
        with self.assertRaises(ValueError):
            calculate({**self.payload(),'pickupCity':'NOT A CONFIGURED CITY'})
        calculator.assert_not_called()

    @patch('suppliers.models.OfferCity.objects.filter')
    @patch('partners.services.calculate_options')
    def test_time_must_match_half_hour_controls(self,calculator,cities):
        cities.return_value.values_list.return_value=[]
        with self.assertRaises(ValueError):
            calculate({**self.payload(),'pickupTime':'10:17'})
        calculator.assert_not_called()
