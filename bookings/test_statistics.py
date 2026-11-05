from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from bookings.statistics import booking_summary, supplier_summary
from customers.models import Customer
from employees.models import Employee
from suppliers.models import Supplier
from bookings.statistics_dates import source_date, resolve_return, reference_rates


class StatisticsCalculationTests(SimpleTestCase):
    def test_reference_rates_match_category_and_currency(self):
        booking = SimpleNamespace(pickup_datetime=timezone.make_aware(datetime(2026, 1, 1)),
            return_datetime=timezone.make_aware(datetime(2026, 1, 3)),
            vehicle_group_id=8, supplier_id=2, currency='EUR',
            vehicle_price_gross=Decimal('200'), total_price_gross=Decimal('300'))
        rates = reference_rates([booking])
        self.assertEqual(rates, {(2, 'EUR', ('group', 8)): (Decimal('100'), 1)})

    def test_source_date_and_money_estimate_cross_year(self):
        self.assertEqual(source_date('12/7/.26, 11:00'), date(2026, 7, 12))
        self.assertIsNone(source_date('31/2/26'))
        booking = SimpleNamespace(pickup_datetime=timezone.make_aware(datetime(2026, 12, 28)),
            source_quote_snapshot={}, rental_days=None, vehicle_group_id=1, supplier_id=1,
            currency='PLN', vehicle_daily_rate_gross_snapshot=None,
            vehicle_price_gross=Decimal('700'), total_price_gross=Decimal('800'))
        result = resolve_return(booking, [], {(1, 'PLN', ('group', 1)): (Decimal('100'), 3)})
        self.assertEqual(result['return_date'], date(2027, 1, 4))
        self.assertTrue(result['estimated'])
        result = resolve_return(booking, [{'return': '2027-01-02'}], {})
        self.assertEqual(result['return_date'], date(2027, 1, 2))
        self.assertFalse(result['estimated'])
        self.assertIsNone(resolve_return(booking, [], {})['return_date'])
        self.assertIsNone(resolve_return(booking, [{'return': '2027-01-02'},
            {'return': '2027-01-03'}], {})['return_date'])

    def test_currencies_months_future_and_averages(self):
        def record(amount, month, firm='TEST', currency='PLN'):
            return dict(gross=amount, month=month, supplier=firm, currency=currency,
                        return_date=date(2026, month, 1))
        result = booking_summary([record('100', 1), record('300', 12),
            record('50', 1, 'OTHER'), record('999', 1, currency='EUR')], date(2026, 6, 1))
        pln = next(row for row in result['totals'] if row['currency'] == 'PLN')
        self.assertEqual(pln['gross'], Decimal('450'))
        self.assertEqual(pln['elapsed'], Decimal('150'))
        self.assertEqual(pln['future'], Decimal('300'))
        self.assertEqual(pln['average'], Decimal('150'))
        self.assertEqual(len(result['months']), 4)
        self.assertEqual(booking_summary([], date.today())['totals'], [])

    def test_supplier_net_uses_report_then_saved_vat_and_refuses_partial_total(self):
        def batch(lines, vat):
            row = SimpleNamespace(supplier_lines=lines)
            return SimpleNamespace(vat=vat, rows=SimpleNamespace(all=lambda: [row]))
        results = supplier_summary([
            batch([{'gross': '123', 'net': '90'}], Decimal('23')),
            batch([{'gross': '123'}], Decimal('23')),
            batch([{'gross': '123'}, {'gross': '50', 'net': '40'}], None)])
        self.assertEqual(results[0]['net'], Decimal('90'))
        self.assertEqual(results[1]['net'], Decimal('100'))
        self.assertIsNone(results[2]['net'])
        self.assertEqual(results[2]['gross'], Decimal('173'))


class StatisticsPageTests(TestCase):
    def test_source_return_is_included_without_writing_booking(self):
        booking = Booking.objects.create(customer=self.customer, supplier=self.supplier,
            status='COMPLETED', source_quote_snapshot={'historical_import': {
                'raw': {'B': '20/12/26', 'C': '27/12/26'}}},
            vehicle_price_gross=700, total_price_gross=700)
        self.client.force_login(self.user)
        response = self.client.get(self.url, {'year': 2026})
        self.assertEqual(response.context['totals'][0]['gross'], Decimal('700'))
        self.assertEqual(len(response.context['recovered']), 1)
        self.assertEqual(response.context['documented'], [])
        booking.refresh_from_db()
        self.assertIsNone(booking.return_datetime)

    def setUp(self):
        self.user = get_user_model().objects.create_user('stats-owner', is_staff=True)
        self.url = reverse('quotes:statistics')
        self.supplier = Supplier.objects.create(supplier_code='STAT', supplier_name='TEST-FIRM')
        self.customer = Customer.objects.create(first_name='TEST', last_name='CLIENT')

    def test_permissions_login_and_restricted_employee(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        Employee.objects.create(first_name='TEST', last_name='SALES', login_user=self.user,
                                role=Employee.Role.SALES)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_year_return_date_statuses_and_no_data_changes(self):
        booking = Booking.objects.create(customer=self.customer, supplier=self.supplier,
            status='COMPLETED', source_quote_snapshot={'historical_import': {'test': True}},
            vehicle_price_gross=100, total_price_gross=100)
        # The report must use return year even when pickup was in the previous year.
        Booking.objects.filter(pk=booking.pk).update(
            pickup_datetime=timezone.make_aware(datetime(2025, 12, 30)),
            return_datetime=timezone.make_aware(datetime(2026, 1, 2)))
        self.client.force_login(self.user)
        for status, expected in [('COMPLETED', 1), ('DRAFT', 0), ('CANCELLED', 0),
                                 ('NO_SHOW', 0), ('WAITING_CONFIRMATION', 1)]:
            Booking.objects.filter(pk=booking.pk).update(status=status)
            response = self.client.get(self.url, {'year': 2026})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(sum(row['count'] for row in response.context['totals']), expected)
        self.assertEqual(self.client.get(self.url, {'year': 2025}).context['totals'], [])
        Booking.objects.filter(pk=booking.pk).update(is_archived=True)
        self.assertEqual(self.client.get(self.url, {'year': 2026}).context['totals'], [])
        booking.refresh_from_db()
        self.assertEqual(booking.total_price_gross, Decimal('100'))
        self.assertEqual(self.client.get(self.url, {'year': 'bad'}).status_code, 400)
