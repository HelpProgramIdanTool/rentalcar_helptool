from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase

from .models import Supplier, PriceList, PriceSeason
from .management.commands.import_vehicle_rates import import_kaizen


class ApprovedValidityTests(TestCase):
    def test_reimport_keeps_operator_approved_end_dates(self):
        supplier = Supplier.objects.create(supplier_code='TEST', supplier_name='Kaizen Rent')
        price_list = PriceList.objects.create(supplier=supplier, version='2026-COMFORT',
            name='Test', effective_from=date(2026, 1, 1), effective_to=date(2028, 2, 29))
        season = PriceSeason.objects.create(price_list=price_list, season_code='LOW_AFTER',
            season_name='Test', rental_date_from=date(2026, 8, 22), rental_date_to=date(2028, 2, 29))
        workbook = MagicMock()
        workbook.__getitem__.return_value.iter_rows.return_value = []
        with patch('suppliers.management.commands.import_vehicle_rates.load_workbook', return_value=workbook):
            import_kaizen(Path('synthetic.xlsx'))
        price_list.refresh_from_db()
        season.refresh_from_db()
        self.assertEqual(price_list.effective_to, date(2028, 2, 29))
        self.assertEqual(season.rental_date_to, date(2028, 2, 29))
