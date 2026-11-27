import json
from django.test import TestCase
from customers.models import Customer
from suppliers.models import Supplier,VehicleGroup,VehicleModel
from bookings.models import Booking
from scripts.export_vehicle_days_data import export_data


class VehicleDaysExportTests(TestCase):
    def test_legacy_group_matches_only_within_supplier_and_export_has_no_client_data(self):
        supplier=Supplier.objects.create(supplier_code='EXPORT-TEST',supplier_name='TEST-EXPORT-FIRM')
        group=VehicleGroup.objects.create(supplier=supplier,group_name='TEST-EXPORT-GROUP',group_code='TEST-CODE')
        VehicleModel.objects.create(vehicle_group=group,brand='TEST-BRAND',model='TEST-MODEL')
        customer=Customer.objects.create(first_name='PRIVATE-CLIENT-NAME',email='private@example.invalid')
        for status in ['COMPLETED','CANCELLED']:
            Booking.objects.create(customer=customer,supplier=supplier,status=status,
                source_quote_snapshot={'historical_import':{'raw':{'B':'01/05/2026, 10:00','C':'04/05/2026, 10:00','D':'TEST-EXPORT-GROUP'}}})
        result=export_data(2026)
        row,=[r for r in result['rows'] if r['code']=='TEST-CODE']
        self.assertEqual(row['days'],3)
        self.assertEqual(row['spring'],3)
        self.assertEqual(row['bookings'],1)
        self.assertEqual(row['examples'],'TEST-BRAND TEST-MODEL')
        self.assertNotIn('PRIVATE-CLIENT-NAME',json.dumps(result))
        self.assertNotIn('private@example.invalid',json.dumps(result))
