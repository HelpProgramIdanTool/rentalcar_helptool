"""The operator's queue; reading it never changes booking prices."""
from django.db.models import Q, F, OuterRef, Subquery
from django.db.models.functions import Coalesce

from employees.models import Employee
from .models import Booking, SupplierEmailDelivery


def visible_bookings(user):
    bookings = Booking.objects.all()
    employee = Employee.objects.filter(login_user=user).first()
    if user.is_superuser or (user.is_staff and employee is None) or (
        employee and employee.status == Employee.Status.ACTIVE
        and employee.role in [Employee.Role.OWNER_ADMIN, Employee.Role.ADMIN]
    ):
        return bookings
    if employee and employee.status != Employee.Status.ACTIVE:
        return bookings.none()
    return bookings.filter(Q(created_by_user=user) | Q(salesperson_employee__login_user=user))


def attention_bookings(user):
    sent = SupplierEmailDelivery.objects.filter(
        booking_id=OuterRef('pk'), status__in=['SENT', 'MANUAL'], sent_at__isnull=False,
    ).order_by('-sent_at')
    return visible_bookings(user).filter(
        Q(status=Booking.Status.UPDATE_PENDING)
        | Q(status=Booking.Status.WAITING_CONFIRMATION, supplier_booking_number__regex=r'^\s*$')
    ).annotate(waiting_since=Coalesce(Subquery(sent.values('sent_at')[:1]), 'updated_at')
    ).select_related('supplier').order_by(F('pickup_datetime').asc(nulls_last=True), 'pk')


def attention_count(request):
    if not request.user.is_authenticated:
        return {}
    return {'booking_attention_count': attention_bookings(request.user).count()}
