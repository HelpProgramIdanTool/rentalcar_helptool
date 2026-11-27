import json
from decimal import Decimal
from django.test import TestCase
from suppliers.models import SupplierExtra, SupplierExtraRate
from . import test_price_preview as preview_data
from .services import calculate_quote_options
from .inquiry_import import parse_inquiry


class DriverRequirementsFlowTests(TestCase):
    setUp = preview_data.PricePreviewTests.setUp

    def configure(self, minimum_age=18, minimum_months=0, fee_age=24, fee_months=12):
        self.supplier.minimum_driver_age = minimum_age
        self.supplier.minimum_license_months = minimum_months
        self.supplier.customer_conditions = {'driver_rules': {'version': 1,
            'surcharge_age_below': fee_age, 'surcharge_license_months_below': fee_months}}
        self.supplier.save()
        extra = SupplierExtra.objects.create(supplier=self.supplier, extra_code='YOUNG_DRIVER', name='TEST-DRIVER-FEE')
        SupplierExtraRate.objects.create(extra=extra, calculation_type='PER_DRIVER_DAY', amount_gross=10,
            maximum_amount_gross=25, valid_from='2020-01-01')
        return extra

    def details(self, age=22, months=4):
        return {'exception': True, 'drivers': [{'age': age, 'license_months': months}] * 2}

    def test_preview_counts_each_person_once_and_caps_each_separately(self):
        extra = self.configure()
        response = self.client.post(self.url, {**self.data, 'driver_requirements': json.dumps(self.details())})
        self.assertEqual(response.status_code, 200, response.content)
        self.quote.driver_requirements = self.details()
        option, = calculate_quote_options(self.quote)
        line, = [line for line in option['extra_lines'] if line.get('extra') == extra]
        self.assertEqual(line['quantity'], 2)
        self.assertEqual(line['price'], Decimal(50))
        self.assertEqual(Decimal(response.json()['prices'][str(self.group.pk)]['total']), option['total'])
        self.assertEqual(self.quote.extra_requests, {})

    def test_ineligible_supplier_is_hidden_and_reason_is_returned(self):
        self.configure(minimum_age=21, minimum_months=12)
        response = self.client.post(self.url, {**self.data, 'driver_requirements': json.dumps(self.details(months=11))})
        price = response.json()['prices'][str(self.group.pk)]
        self.assertFalse(price['available'])
        self.assertTrue(price['not_offered'])
        self.assertIn('12', price['reason'])

    def test_missing_driver_rows_block_calculation(self):
        response = self.client.post(self.url, {**self.data, 'driver_requirements': json.dumps({'exception': True})})
        self.assertEqual(response.status_code, 400)
        self.assertIn('driver_requirements', response.json()['errors'])

    def test_explicit_standard_declaration_does_not_charge(self):
        self.configure()
        self.quote.driver_requirements = {'exception': False, 'drivers': []}
        self.quote.extra_requests = {'YOUNG_DRIVER': 2}
        result, = calculate_quote_options(self.quote)
        self.assertFalse(any(line['extra'].extra_code == 'YOUNG_DRIVER' for line in result['extra_lines']))

    def test_import_preserves_numeric_driver_details(self):
        text = 'מספר פנייה: TEST\nקבלת הרכב:\nעיר: קרקוב\nDriver requirements JSON: ' + json.dumps(self.details())
        data, _, _ = parse_inquiry(text)
        self.assertEqual(data['driver_requirements'], self.details())
        self.assertEqual(data['driver_count'], 2)

    def test_old_negative_declaration_requires_numeric_clarification(self):
        text = 'מספר פנייה: TEST\nכל נהג מעל גיל 24 ועם לפחות שנה רישיון: לא\nקבלת הרכב:\nעיר: קרקוב'
        data, _, warnings = parse_inquiry(text)
        self.assertEqual(data['driver_requirements'], {'exception':True,'drivers':[]})
        self.assertTrue(any('старая форма' in item for item in warnings))
