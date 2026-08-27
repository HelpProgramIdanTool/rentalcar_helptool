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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        super().clean()
        if self.status == self.Status.CONFIRMED and not self.supplier_booking_number:
            raise ValidationError(
                {
                    "supplier_booking_number": (
                        "Enter the supplier booking number before confirming the booking."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if not self.booking_number:
            self.booking_number = BookingNumberSequence.next_number(timezone.now().year)
        super().save(*args, **kwargs)

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
