from django.test import TestCase
from suppliers.models import SupplierExtra, SupplierExtraRate
from . import test_manual as manual_data
from .models import Booking


class ConditionalBookingDriverTests(TestCase):
    review=manual_data.ManualBookingTests.review
    confirm=manual_data.ManualBookingTests.confirm

    def setUp(self):
        manual_data.ManualBookingTests.setUp(self)
        self.supplier.minimum_driver_age=18
        self.supplier.minimum_license_months=0
        self.supplier.customer_conditions={'driver_rules':{'version':1,'surcharge_age_below':24,'surcharge_license_months_below':12}}
        self.supplier.save()
        self.extra=SupplierExtra.objects.create(supplier=self.supplier,extra_code='YOUNG_DRIVER',name='TEST DRIVER FEE')
        SupplierExtraRate.objects.create(extra=self.extra,calculation_type='PER_DRIVER_DAY',amount_gross=10,valid_from='2020-01-01')

    def standard(self, **changes):
        return dict(driver_detail_mode='conditional',driver_count=2,driver_1_name='TEST FIRST',driver_2_name='TEST SECOND',**changes)

    def test_standard_drivers_need_names_without_age_or_experience(self):
        data,response=self.review(**self.standard())
        self.assertEqual(response.context['result']['extras_total'],0)
        self.confirm(data,response)
        self.assertEqual(list(Booking.objects.get().drivers.values_list('age_at_pickup','license_months_at_pickup')),[(None,None),(None,None)])

    def test_only_marked_driver_needs_numeric_details_and_pays(self):
        data,response=self.review(**self.standard(driver_1_young='on',driver_1_age=22,driver_1_license_months=4))
        self.assertEqual(response.context['result']['extras_total'],30)
        self.confirm(data,response)
        booking=Booking.objects.get()
        self.assertEqual(booking.drivers.get(display_order=1).age_at_pickup,22)
        self.assertIsNone(booking.drivers.get(display_order=2).age_at_pickup)
        self.assertEqual(booking.extras.get(extra=self.extra).quantity,1)

    def test_marked_driver_without_facts_cannot_be_saved(self):
        response=self.client.post(self.url,{**self.data,**self.standard(driver_1_young='on')})
        self.assertIsNone(response.context['review_token'])
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertFalse(Booking.objects.exists())

    def test_standard_declaration_also_works_without_new_ui_marker(self):
        import json
        data,response=self.review(driver_count=2,driver_1_name='TEST FIRST',driver_2_name='TEST SECOND',
            driver_requirements=json.dumps({'exception':False,'drivers':[]}))
        self.assertEqual(response.context['result']['extras_total'],0)

    def test_known_exception_is_restored_even_when_supplier_charges_no_fee(self):
        from .manual import clone_initial
        from .amendments import initial_data
        self.supplier.customer_conditions={'driver_rules':{'version':1,'surcharge_age_below':21}}
        self.supplier.save()
        data,response=self.review(**self.standard(driver_1_young='on',driver_1_age=22,driver_1_license_months=24))
        self.assertEqual(response.context['result']['extras_total'],0)
        self.confirm(data,response)
        booking=Booking.objects.get()
        self.assertFalse(booking.drivers.get(display_order=1).young_driver_status)
        self.assertTrue(clone_initial(booking)['driver_1_young'])
        self.assertTrue(initial_data(booking)['driver_1_young'])
