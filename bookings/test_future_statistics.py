from datetime import datetime
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Booking
from customers.models import Customer
from suppliers.models import Supplier


class FutureStatisticsTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user('TEST-FUTURE-STATS',is_staff=True)
        self.client.force_login(self.user)
        self.customer=Customer.objects.create(first_name='TEST',last_name='CUSTOMER')
        self.first=Supplier.objects.create(supplier_code='FUTURE-A',supplier_name='TEST-FIRM-A')
        self.second=Supplier.objects.create(supplier_code='FUTURE-B',supplier_name='TEST-FIRM-B')
        self.url=reverse('quotes:statistics')

    def booking(self,supplier=None,status='CONFIRMED',start=(2027,1,5),end=(2027,1,8),**kwargs):
        return Booking.objects.create(customer=self.customer,supplier=supplier or self.first,status=status,
            pickup_datetime=timezone.make_aware(datetime(*start,10)),
            return_datetime=timezone.make_aware(datetime(*end,10)),total_price_gross=100,**kwargs)

    def test_future_year_has_counts_by_firm_status_month_and_visible_year_option(self):
        self.booking();self.booking(status='WAITING_CONFIRMATION')
        self.booking(supplier=self.second,status='UPDATE_PENDING',start=(2027,2,1),end=(2027,2,5))
        for status in ['DRAFT','CANCELLED','NO_SHOW']:self.booking(status=status)
        self.booking(is_archived=True)
        self.booking(start=(2026,5,1),end=(2026,5,4))
        response=self.client.get(self.url,{'year':2027})
        self.assertEqual(response.status_code,200)
        self.assertIn(2027,response.context['year_choices'])
        self.assertContains(response,'value="2027" selected')
        self.assertEqual(response.context['booking_counts'],dict(count=3,confirmed=1,waiting=1,changes=1))
        rows=response.context['booking_suppliers']
        self.assertEqual([(r['supplier__supplier_name'],r['count']) for r in rows],[('TEST-FIRM-A',2),('TEST-FIRM-B',1)])
        self.assertEqual([r['count'] for r in response.context['booking_months']],[2,1])

    def test_cross_year_booking_is_counted_by_explicitly_selected_date_without_changing_turnover(self):
        booking=self.booking(start=(2026,12,30),end=(2027,1,3))
        pickup=self.client.get(self.url,{'year':2027,'booking_date_basis':'pickup'})
        returned=self.client.get(self.url,{'year':2027,'booking_date_basis':'return'})
        self.assertEqual(pickup.context['booking_counts']['count'],0)
        self.assertEqual(returned.context['booking_counts']['count'],1)
        self.assertEqual(pickup.context['totals'],returned.context['totals'])
        booking.refresh_from_db()
        self.assertEqual(booking.pickup_datetime.year,2026)

    def test_invalid_basis_is_rejected(self):
        self.assertEqual(self.client.get(self.url,{'year':2027,'booking_date_basis':'created'}).status_code,400)
