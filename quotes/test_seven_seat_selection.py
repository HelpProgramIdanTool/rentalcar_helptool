from types import SimpleNamespace
from django.test import SimpleTestCase
from .inquiry_import import suitable_group


class SevenSeatSelectionTests(SimpleTestCase):
    def test_seven_seat_van_matches_without_an_suv_comparison_class(self):
        group=SimpleNamespace(seats=7,transmission='AUTOMATIC',body_type='MINIVAN',
            comparison_classes=SimpleNamespace(all=lambda:[SimpleNamespace(code='TEST-OWN-CLASS')]))
        request={'passengers':6,'automatic':True,'categories':['רכב 7 מקומות']}
        self.assertTrue(suitable_group(group,request))
        group.seats=5
        self.assertFalse(suitable_group(group,request))
        group.seats=7
        request['passengers']=8
        self.assertFalse(suitable_group(group,request))
