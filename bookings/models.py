from math import ceil
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
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

    class PriceCalculationStatus(models.TextChoices):
        NOT_CALCULATED = "NOT_CALCULATED", "Not calculated"
        CALCULATED = "CALCULATED", "Calculated"
        NO_RATE = "NO_RATE", "No matching rate"
        OVERRIDDEN = "OVERRIDDEN", "Manually overridden"

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
    calculated_vehicle_price_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    manual_vehicle_price_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Optional manual customer price including VAT.",
    )
    manual_price_override_reason = models.TextField(blank=True)
    vehicle_price_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    vehicle_daily_rate_gross_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        editable=False,
    )
    vehicle_rate = models.ForeignKey(
        "suppliers.VehicleRate",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="booking_snapshots",
        editable=False,
    )
    price_list_version_snapshot = models.CharField(max_length=50, blank=True, editable=False)
    price_season_snapshot = models.CharField(max_length=120, blank=True, editable=False)
    price_day_range_snapshot = models.CharField(max_length=80, blank=True, editable=False)
    price_calculation_status = models.CharField(
        max_length=20,
        choices=PriceCalculationStatus.choices,
        default=PriceCalculationStatus.NOT_CALCULATED,
        editable=False,
    )
    extras_total_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    total_price_gross = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
    )
    currency = models.CharField(max_length=3, default="PLN")
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
        if self.manual_vehicle_price_gross is not None and not self.manual_price_override_reason.strip():
            errors["manual_price_override_reason"] = (
                "Explain why the calculated vehicle price is being changed."
            )
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
        self._calculate_vehicle_price()
        if not self.booking_number:
            self.booking_number = BookingNumberSequence.next_number(timezone.now().year)
        super().save(*args, **kwargs)
        self._sync_mandatory_extras()
        self.recalculate_totals()

    @staticmethod
    def _location_snapshot(location):
        parts = [location.location_name, location.address, location.city]
        return ", ".join(part for part in parts if part)

    def _sync_mandatory_extras(self):
        from suppliers.models import SupplierExtraRate

        self.extras.filter(is_mandatory_snapshot=True).exclude(
            extra__supplier=self.supplier,
            extra__is_mandatory=True,
        ).delete()
        effective_date = (
            self.pickup_datetime.date() if self.pickup_datetime else timezone.localdate()
        )
        mandatory_extras = self.supplier.extras.filter(
            is_active=True,
            is_mandatory=True,
        )
        for extra in mandatory_extras:
            rates = extra.rates.filter(
                is_active=True,
                valid_from__lte=effective_date,
            ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=effective_date))
            if self.pickup_location_id:
                rates = rates.filter(
                    Q(location__isnull=True) | Q(location=self.pickup_location)
                )
            else:
                rates = rates.filter(location__isnull=True)
            selected_rate = rates.order_by("-priority", "-valid_from").first()
            if selected_rate:
                BookingExtra.objects.get_or_create(
                    booking=self,
                    extra=extra,
                    defaults={"rate": selected_rate, "quantity": 1},
                )

    def recalculate_totals(self):
        if not self.pk:
            return
        extras_total = sum(
            (
                item.calculated_price_gross
                for item in self.extras.filter(included_in_total=True)
            ),
            Decimal("0.00"),
        )
        total = self.vehicle_price_gross + extras_total
        type(self).objects.filter(pk=self.pk).update(
            extras_total_gross=extras_total,
            total_price_gross=total,
        )
        self.extras_total_gross = extras_total
        self.total_price_gross = total

    def _calculate_vehicle_price(self):
        from suppliers.models import VehicleRate

        frozen_statuses = {
            self.Status.CONFIRMED,
            self.Status.UPDATE_PENDING,
            self.Status.ACTIVE,
            self.Status.COMPLETED,
            self.Status.SETTLED,
        }
        if self.pk:
            old_status = type(self).objects.filter(pk=self.pk).values_list(
                "status", flat=True
            ).first()
            if old_status in frozen_statuses:
                return
        if not (self.pickup_datetime and self.rental_days and self.vehicle_group_id):
            self._clear_vehicle_price(self.PriceCalculationStatus.NOT_CALCULATED)
            self._apply_manual_vehicle_price()
            return
        pickup_date = self.pickup_datetime.date()
        rates = VehicleRate.objects.filter(
            is_active=True,
            vehicle_group=self.vehicle_group,
            season__is_active=True,
            season__price_list__status="ACTIVE",
            season__price_list__effective_from__lte=pickup_date,
            season__rental_date_from__lte=pickup_date,
            day_range__is_active=True,
            day_range__days_from__lte=self.rental_days,
        ).filter(
            Q(season__price_list__effective_to__isnull=True)
            | Q(season__price_list__effective_to__gte=pickup_date),
            Q(season__rental_date_to__isnull=True)
            | Q(season__rental_date_to__gte=pickup_date),
            Q(day_range__days_to__isnull=True)
            | Q(day_range__days_to__gte=self.rental_days),
        )
        selected_rate = rates.select_related(
            "season__price_list", "day_range"
        ).order_by(
            "-season__price_list__effective_from",
            "-season__priority",
        ).first()
        if not selected_rate:
            self._clear_vehicle_price(self.PriceCalculationStatus.NO_RATE)
            self._apply_manual_vehicle_price()
            return
        self.vehicle_rate = selected_rate
        self.vehicle_daily_rate_gross_snapshot = selected_rate.daily_rate_gross
        self.calculated_vehicle_price_gross = (
            selected_rate.daily_rate_gross * self.rental_days
        )
        self.vehicle_price_gross = self.calculated_vehicle_price_gross
        self.price_list_version_snapshot = selected_rate.season.price_list.version
        self.price_season_snapshot = selected_rate.season.season_name
        self.price_day_range_snapshot = selected_rate.day_range.label
        self.price_calculation_status = self.PriceCalculationStatus.CALCULATED
        self._apply_manual_vehicle_price()

    def _clear_vehicle_price(self, status):
        self.vehicle_rate = None
        self.vehicle_daily_rate_gross_snapshot = None
        self.calculated_vehicle_price_gross = Decimal("0.00")
        self.vehicle_price_gross = Decimal("0.00")
        self.price_list_version_snapshot = ""
        self.price_season_snapshot = ""
        self.price_day_range_snapshot = ""
        self.price_calculation_status = status

    def _apply_manual_vehicle_price(self):
        if self.manual_vehicle_price_gross is not None:
            self.vehicle_price_gross = self.manual_vehicle_price_gross
            self.price_calculation_status = self.PriceCalculationStatus.OVERRIDDEN

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


class BookingExtra(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="extras",
    )
    extra = models.ForeignKey(
        "suppliers.SupplierExtra",
        on_delete=models.PROTECT,
        related_name="booking_entries",
    )
    rate = models.ForeignKey(
        "suppliers.SupplierExtraRate",
        on_delete=models.PROTECT,
        related_name="booking_entries",
    )
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    customer_visible_name = models.CharField(max_length=150)
    supplier_visible_name = models.CharField(max_length=150)
    calculation_type_snapshot = models.CharField(max_length=20)
    unit_price_gross_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount_gross_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    maximum_amount_gross_snapshot = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    calculated_price_gross = models.DecimalField(max_digits=12, decimal_places=2)
    currency_snapshot = models.CharField(max_length=3)
    formula_snapshot = models.JSONField(default=dict, blank=True)
    is_mandatory_snapshot = models.BooleanField(default=False)
    included_in_total = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "extra"],
                name="one_extra_type_per_booking",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.extra_id and self.extra.supplier_id != self.booking.supplier_id:
            errors["extra"] = "The extra must belong to the booking supplier."
        if self.rate_id and self.rate.extra_id != self.extra_id:
            errors["rate"] = "The rate must belong to the selected extra."
        if self.rate_id and self.rate.currency != self.booking.currency:
            errors["rate"] = "Extra and booking currencies must match."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.customer_visible_name = self.extra.name
            self.supplier_visible_name = self.extra.name
            self.calculation_type_snapshot = self.rate.calculation_type
            self.unit_price_gross_snapshot = self.rate.amount_gross
            self.minimum_amount_gross_snapshot = self.rate.minimum_amount_gross
            self.maximum_amount_gross_snapshot = self.rate.maximum_amount_gross
            self.currency_snapshot = self.rate.currency
            self.formula_snapshot = self.rate.formula_config.copy()
            self.is_mandatory_snapshot = self.extra.is_mandatory
        self.calculated_price_gross = self._calculate_price()
        super().save(*args, **kwargs)
        self.booking.recalculate_totals()

    def delete(self, *args, **kwargs):
        booking = self.booking
        result = super().delete(*args, **kwargs)
        booking.recalculate_totals()
        return result

    def _calculate_price(self):
        calculation_type = self.calculation_type_snapshot
        days = Decimal(self.booking.rental_days or 1)
        if calculation_type in ("PER_DAY", "PER_DRIVER_DAY"):
            price = self.unit_price_gross_snapshot * self.quantity * days
        elif calculation_type == "PER_UNIT":
            price = self.unit_price_gross_snapshot * self.quantity
        else:
            price = self.unit_price_gross_snapshot * self.quantity
        if self.minimum_amount_gross_snapshot is not None:
            price = max(price, self.minimum_amount_gross_snapshot)
        if self.maximum_amount_gross_snapshot is not None:
            price = min(price, self.maximum_amount_gross_snapshot)
        return price

    def __str__(self):
        return f"{self.booking} - {self.customer_visible_name}"
