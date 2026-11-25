from django.test import TestCase
from . import tests as inquiry_tests
from .forms import FirstInquiryForm
from suppliers.models import Supplier, VehicleGroup


class SupplierExclusionTests(TestCase):
    def setUp(self):
        inquiry_tests.FirstInquiryTests.setUp(self)

    def test_stale_group_of_unchecked_supplier_is_removed(self):
        other=Supplier.objects.create(supplier_code='EXCLUDED-TEST',supplier_name='EXCLUDED-TEST')
        group=VehicleGroup.objects.create(supplier=other,group_code='EXCLUDED',group_name='EXCLUDED',rate_source_group=self.form_groups[0])
        data=inquiry_tests.FirstInquiryTests.data(self)
        data['vehicle_groups']=[str(self.form_groups[0].pk),str(group.pk)]
        form=FirstInquiryForm(data)
        self.assertTrue(form.is_valid(),form.errors)
        self.assertNotIn(group,form.cleaned_data['vehicle_groups'])

    def test_only_excluded_groups_cannot_save_quote(self):
        other=Supplier.objects.create(supplier_code='EXCLUDED-TEST',supplier_name='EXCLUDED-TEST')
        group=VehicleGroup.objects.create(supplier=other,group_code='EXCLUDED',group_name='EXCLUDED',rate_source_group=self.form_groups[0])
        data=inquiry_tests.FirstInquiryTests.data(self)
        data['vehicle_groups']=[str(group.pk)]
        form=FirstInquiryForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('vehicle_groups',form.errors)
