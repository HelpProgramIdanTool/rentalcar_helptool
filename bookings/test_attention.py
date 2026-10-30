from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from customers.models import Customer
from suppliers.models import Supplier
from .attention import attention_bookings
from .models import Booking, SupplierEmailDelivery


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class AttentionQueueTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='owner', is_staff=True)
        self.other = get_user_model().objects.create_user(username='employee')
        self.client.force_login(self.user)
        self.supplier = Supplier.objects.create(supplier_code='ATTENTION', supplier_name='Invented supplier')
        self.customer = Customer.objects.create(first_name='Invented customer')
        self.url = reverse('quotes:attention_queue')

    def booking(self, **kwargs):
        return Booking.objects.create(supplier=self.supplier, customer=self.customer,
            manual_vehicle_price_gross=Decimal('100'), manual_price_override_reason='Invented price',
            **kwargs)

    def pending(self):
        booking = self.booking(status=Booking.Status.UPDATE_PENDING, supplier_booking_number='TEST-123')
        SupplierEmailDelivery.objects.create(booking=booking, token=uuid4(), status='MANUAL',
            sent_at=timezone.now(), recipient='supplier@example.com', subject='Invented update', body='Test')
        return booking

    def test_queue_excludes_drafts_cancelled_archived_and_confirmed(self):
        for status in [Booking.Status.DRAFT, Booking.Status.CANCELLED, Booking.Status.CONFIRMED]:
            self.booking(status=status)
        self.booking(status=Booking.Status.WAITING_CONFIRMATION, is_archived=True)
        waiting = self.booking(status=Booking.Status.WAITING_CONFIRMATION)
        pending = self.pending()
        self.assertEqual(set(attention_bookings(self.user).values_list('pk', flat=True)), {waiting.pk, pending.pk})
        response = self.client.get(self.url)
        self.assertContains(response, 'Требуют внимания — 2')
        self.assertEqual(response.context['booking_attention_count'], 2)

    def test_number_confirmation_preserves_price_and_records_actor(self):
        booking = self.booking(status=Booking.Status.WAITING_CONFIRMATION)
        response = self.client.post(self.url, {'booking_id': booking.pk, 'supplier_booking_number': 'NEW-123'})
        self.assertRedirects(response, self.url)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.total_price_gross, Decimal('100'))
        self.assertEqual(booking.confirmed_by_user, self.user)
        self.assertEqual(attention_bookings(self.user).count(), 0)
        self.assertTrue(booking.history_events.filter(changes__operator_user_id=self.user.pk).exists())

    def test_change_requires_checked_new_voucher_not_old_file(self):
        booking = self.pending()
        # A previous voucher must not count as confirmation of a later request.
        from .models import BookingVoucher
        voucher = BookingVoucher.objects.create(booking=booking,
            file=SimpleUploadedFile('old.pdf', b'%PDF-1.4 old'), original_filename='old.pdf')
        BookingVoucher.objects.filter(pk=voucher.pk).update(received_at=timezone.now()-timezone.timedelta(days=1))
        data = {'booking_id': booking.pk, 'supplier_booking_number': 'TEST-123', 'verified': 'yes'}
        self.assertContains(self.client.post(self.url, data), 'Загрузите новый ваучер')
        data['file'] = SimpleUploadedFile('new.pdf', b'%PDF-1.4 new')
        data.pop('verified')
        self.assertContains(self.client.post(self.url, data), 'Отметьте, что новый ваучер проверен')
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.UPDATE_PENDING)
        self.assertEqual(booking.vouchers.count(), 1)
        data.update(verified='yes', file=SimpleUploadedFile('new.pdf', b'%PDF-1.4 new'))
        self.assertRedirects(self.client.post(self.url, data), self.url)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        self.assertEqual(booking.vouchers.count(), 2)
        self.assertEqual(booking.total_price_gross, Decimal('100'))

    def test_duplicate_number_and_invalid_file_leave_order_pending(self):
        self.booking(supplier_booking_number='TAKEN')
        booking = self.pending()
        data = {'booking_id': booking.pk, 'supplier_booking_number': 'taken', 'verified': 'yes'}
        self.assertContains(self.client.post(self.url, data), 'Проверьте дубликат')
        data.update(supplier_booking_number='TEST-123', file=SimpleUploadedFile('fake.pdf', b'bad'))
        self.assertContains(self.client.post(self.url, data), 'Загрузите PDF')
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.UPDATE_PENDING)
        self.assertFalse(booking.vouchers.exists())

    def test_employee_queue_and_post_are_limited_to_own_orders(self):
        mine = self.booking(status=Booking.Status.WAITING_CONFIRMATION, created_by_user=self.other)
        foreign = self.booking(status=Booking.Status.WAITING_CONFIRMATION, created_by_user=self.user)
        self.client.force_login(self.other)
        self.assertEqual(list(attention_bookings(self.other)), [mine])
        self.assertEqual(self.client.post(self.url, {'booking_id': foreign.pk}).status_code, 404)
        self.assertEqual(self.client.get(self.url).context['booking_attention_count'], 1)

    def test_login_and_csrf_are_required(self):
        from django.test import Client
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {}).status_code, 403)

    def test_existing_fresh_voucher_can_be_verified_and_double_post_is_safe(self):
        from .models import BookingVoucher
        booking = self.pending()
        BookingVoucher.objects.create(booking=booking,
            file=SimpleUploadedFile('fresh.pdf', b'%PDF-1.4 new'), original_filename='fresh.pdf')
        data = {'booking_id': booking.pk, 'supplier_booking_number': 'TEST-123', 'verified': 'yes'}
        self.assertRedirects(self.client.post(self.url, data), self.url)
        event_count = booking.history_events.count()
        self.assertEqual(self.client.post(self.url, data).status_code, 404)
        self.assertEqual(booking.history_events.count(), event_count)

    def test_staff_employee_still_only_sees_own_queue_and_inactive_sees_none(self):
        from employees.models import Employee
        employee = Employee.objects.create(login_user=self.other, first_name='Test', last_name='Employee',
            role=Employee.Role.OPERATOR)
        self.other.is_staff = True
        self.other.save(update_fields=['is_staff'])
        mine = self.booking(status=Booking.Status.UPDATE_PENDING, salesperson_employee=employee)
        self.booking(status=Booking.Status.WAITING_CONFIRMATION, created_by_user=self.user)
        self.assertEqual(list(attention_bookings(self.other)), [mine])
        employee.status = Employee.Status.INACTIVE
        employee.save(update_fields=['status'])
        self.assertFalse(attention_bookings(self.other).exists())

    def test_home_shows_counter_and_each_booking_counts_once(self):
        self.booking(status=Booking.Status.UPDATE_PENDING, supplier_booking_number='')
        response = self.client.get(reverse('quotes:home'))
        self.assertEqual(response.context['booking_attention_count'], 1)
        self.assertContains(response, reverse('quotes:attention_queue'))
        self.assertContains(response, 'background:#b91c1c')
