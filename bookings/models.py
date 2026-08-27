from math import ceil

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


class BookingNumberSequence(models.Model):
    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    @classmethod
    def next_number(cls, year):
        with transaction.atomic():
            sequence, _ = cls.objects.select_for_update().get_or_create(year=year)
            sequence.last_number += 1
            sequence.save(update_fields=["last_number"])
            return f"RC-{year}-{sequence.last_number:05d}"


class Booking(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        WAITING_CONFIRMATION = "WAITING_CONFIRMATION", "Waiting confirmation"
        CONFIRMED = "CONFIRMED", "Confirmed"
        UPDATE_PENDING = "UPDATE_PENDING", "Update pending"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No-show"
        SETTLED = "SETTLED", "Settled"

    booking_number = models.CharField(max_length=20, unique=True, editable=False)
    supplier_booking_number = models.CharField(max_length=100, blank=True)
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    pickup_datetime = models.DateTimeField(null=True, blank=True)
    return_datetime = models.DateTimeField(null=True, blank=True)
    rental_days = models.PositiveIntegerField(null=True, blank=True, editable=False)
    pickup_location = models.ForeignKey(
        "suppliers.SupplierLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pickup_bookings",
    )
    return_location = models.ForeignKey(
        "suppliers.SupplierLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="return_bookings",
    )
    pickup_location_text = models.CharField(max_length=300, blank=True)
    return_location_text = models.CharField(max_length=300, blank=True)
    pickup_address = models.CharField(max_length=300, blank=True)
    return_address = models.CharField(max_length=300, blank=True)
    hotel_name = models.CharField(max_length=200, blank=True)
    flight_number = models.CharField(max_length=50, blank=True)
    vehicle_group = models.ForeignKey(
        "suppliers.VehicleGroup",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        errors = {}
        if self.pickup_location_id and self.pickup_location.supplier_id != self.supplier_id:
            errors["pickup_location"] = "Pickup location must belong to the supplier."
        if self.return_location_id and self.return_location.supplier_id != self.supplier_id:
            errors["return_location"] = "Return location must belong to the supplier."
        if self.vehicle_group_id and self.vehicle_group.supplier_id != self.supplier_id:
            errors["vehicle_group"] = "Vehicle group must belong to the supplier."
        if errors:
            raise ValidationError(errors)
        if bool(self.pickup_datetime) != bool(self.return_datetime):
            raise ValidationError(
                "Enter both pickup and return date and time, or leave both empty."
            )
        if (
            self.pickup_datetime
            and self.return_datetime
            and self.return_datetime <= self.pickup_datetime
        ):
            raise ValidationError(
                {"return_datetime": "Return must be later than pickup."}
            )
        if self.status == self.Status.CONFIRMED and not self.supplier_booking_number:
            raise ValidationError(
                {
                    "supplier_booking_number": (
                        "Enter the supplier booking number before confirming the booking."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.pickup_location and not self.pickup_location_text:
            self.pickup_location_text = self._location_snapshot(self.pickup_location)
        if self.return_location and not self.return_location_text:
            self.return_location_text = self._location_snapshot(self.return_location)
        if self.pickup_datetime and self.return_datetime:
            duration_seconds = (
                self.return_datetime - self.pickup_datetime
            ).total_seconds()
            if duration_seconds > 0:
                self.rental_days = max(1, ceil(duration_seconds / 86400))
        else:
            self.rental_days = None
        if not self.booking_number:
            self.booking_number = BookingNumberSequence.next_number(timezone.now().year)
        super().save(*args, **kwargs)

    @staticmethod
    def _location_snapshot(location):
        parts = [location.location_name, location.address, location.city]
        return ", ".join(part for part in parts if part)

    def __str__(self):
        return self.booking_number


class BookingDriver(models.Model):
    class Role(models.TextChoices):
        MAIN = "MAIN", "Main"
        ADDITIONAL = "ADDITIONAL", "Additional"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="drivers",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_driver_entries",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=Role.choices)
    phone_snapshot = models.CharField(max_length=30, blank=True)
    display_order = models.PositiveSmallIntegerField(default=1)
    young_driver_status = models.BooleanField(default=False)
    rule_warning = models.TextField(blank=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=Q(role="MAIN"),
                name="one_main_driver_per_booking",
            )
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
