from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from config.rental_duration import calculate_rental_days


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
    created_by_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bookings",
    )
    salesperson_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sold_bookings",
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
    customer_name_snapshot = models.CharField(max_length=200, blank=True)
    customer_email_snapshot = models.EmailField(blank=True)
    customer_phone_1_snapshot = models.CharField(max_length=30, blank=True)
    customer_phone_2_snapshot = models.CharField(max_length=30, blank=True)
    customer_phone_3_snapshot = models.CharField(max_length=30, blank=True)
    customer_country_snapshot = models.CharField(max_length=100, blank=True)
    customer_city_snapshot = models.CharField(max_length=100, blank=True)
    customer_address_snapshot = models.CharField(max_length=255, blank=True)
    customer_postal_code_snapshot = models.CharField(max_length=20, blank=True)
    wants_invoice_snapshot = models.BooleanField(default=False)
    invoice_name_snapshot = models.CharField(max_length=200, blank=True)
    invoice_tax_id_snapshot = models.CharField(max_length=50, blank=True)
    invoice_country_snapshot = models.CharField(max_length=100, blank=True)
    invoice_city_snapshot = models.CharField(max_length=100, blank=True)
    invoice_address_snapshot = models.CharField(max_length=255, blank=True)
    invoice_postal_code_snapshot = models.CharField(max_length=20, blank=True)
    invoice_email_snapshot = models.EmailField(blank=True)
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
        is_new = self._state.adding
        old_values = self._history_values() if not is_new else {}
        if is_new:
            self._copy_customer_snapshot()
        if self.pickup_location and not self.pickup_location_text:
            self.pickup_location_text = self._location_snapshot(self.pickup_location)
        if self.return_location and not self.return_location_text:
            self.return_location_text = self._location_snapshot(self.return_location)
        if self.pickup_datetime and self.return_datetime:
            duration_seconds = (self.return_datetime - self.pickup_datetime).total_seconds()
            if duration_seconds > 0:
                self.rental_days = calculate_rental_days(
                    self.pickup_datetime, self.return_datetime
                )
        else:
            self.rental_days = None
        self._calculate_vehicle_price()
        if not self.booking_number:
            self.booking_number = BookingNumberSequence.next_number(timezone.now().year)
        super().save(*args, **kwargs)
        self._sync_mandatory_extras()
        self.sync_after_hours_extra()
        self.recalculate_extra_prices()
        self._record_history(is_new, old_values)

    def _history_values(self):
        fields = (
            "status",
            "supplier_booking_number",
            "supplier_id",
            "vehicle_group_id",
            "pickup_datetime",
            "return_datetime",
            "pickup_location_id",
            "return_location_id",
            "pickup_address",
            "return_address",
            "flight_number",
            "manual_vehicle_price_gross",
            "manual_price_override_reason",
        )
        return type(self).objects.filter(pk=self.pk).values(*fields).get()

    def _record_history(self, is_new, old_values):
        actor = getattr(self, "_history_actor", None)
        if is_new:
            self.log_history(
                BookingHistoryEvent.EventType.CREATED,
                "Booking created",
                created_by=actor or self.created_by_employee,
            )
            if self.manual_vehicle_price_gross is not None:
                self.log_history(
                    BookingHistoryEvent.EventType.PRICE_OVERRIDE,
                    "Vehicle price manually overridden when booking was created",
                    changes={
                        "manual_vehicle_price_gross": {
                            "old": None,
                            "new": str(self.manual_vehicle_price_gross),
                        },
                        "reason": {
                            "old": "",
                            "new": self.manual_price_override_reason,
                        },
                    },
                    created_by=actor or self.created_by_employee,
                )
            return
        new_values = {
            key: getattr(self, key)
            for key in old_values
        }
        if old_values["status"] != new_values["status"]:
            event_type = BookingHistoryEvent.EventType.STATUS_CHANGED
            if new_values["status"] == self.Status.CANCELLED:
                event_type = BookingHistoryEvent.EventType.CANCELLED
            elif new_values["status"] == self.Status.NO_SHOW:
                event_type = BookingHistoryEvent.EventType.NO_SHOW
            self.log_history(
                event_type,
                f"Status changed from {old_values['status']} to {new_values['status']}",
                old_status=old_values["status"],
                new_status=new_values["status"],
                created_by=actor,
            )
        price_fields = ("manual_vehicle_price_gross", "manual_price_override_reason")
        price_changes = self._changed_values(old_values, new_values, price_fields)
        if price_changes:
            self.log_history(
                BookingHistoryEvent.EventType.PRICE_OVERRIDE,
                "Manual vehicle price changed",
                changes=price_changes,
                created_by=actor,
            )
        detail_fields = tuple(
            key
            for key in old_values
            if key not in {"status", *price_fields}
        )
        detail_changes = self._changed_values(old_values, new_values, detail_fields)
        if detail_changes:
            self.log_history(
                BookingHistoryEvent.EventType.DETAILS_CHANGED,
                "Booking details changed",
                changes=detail_changes,
                created_by=actor,
            )

    @staticmethod
    def _changed_values(old_values, new_values, fields):
        changes = {}
        for field in fields:
            if old_values[field] != new_values[field]:
                changes[field] = {
                    "old": str(old_values[field]) if old_values[field] is not None else None,
                    "new": str(new_values[field]) if new_values[field] is not None else None,
                }
        return changes

    def log_history(
        self,
        event_type,
        description,
        *,
        changes=None,
        old_status="",
        new_status="",
        created_by=None,
    ):
        return BookingHistoryEvent.objects.create(
            booking=self,
            event_type=event_type,
            description=description,
            changes=changes or {},
            old_status=old_status,
            new_status=new_status,
            created_by=created_by,
        )

    def _copy_customer_snapshot(self):
        customer = self.customer
        self.customer_name_snapshot = str(customer)
        self.customer_email_snapshot = customer.email
        self.customer_phone_1_snapshot = customer.phone_1
        self.customer_phone_2_snapshot = customer.phone_2
        self.customer_phone_3_snapshot = customer.phone_3
        self.customer_country_snapshot = customer.country
        self.customer_city_snapshot = customer.city
        self.customer_address_snapshot = customer.address
        self.customer_postal_code_snapshot = customer.postal_code
        self.wants_invoice_snapshot = customer.wants_invoice
        self.invoice_name_snapshot = customer.invoice_name
        self.invoice_tax_id_snapshot = customer.invoice_tax_id
        self.invoice_country_snapshot = customer.invoice_country
        self.invoice_city_snapshot = customer.invoice_city
        self.invoice_address_snapshot = customer.invoice_address
        self.invoice_postal_code_snapshot = customer.invoice_postal_code
        self.invoice_email_snapshot = customer.invoice_email

    @staticmethod
    def _location_snapshot(location):
        parts = [location.location_name, location.address, location.city]
        return ", ".join(part for part in parts if part)

    def _sync_mandatory_extras(self):
        self.extras.filter(is_mandatory_snapshot=True).exclude(
            extra__supplier=self.supplier,
            extra__is_mandatory=True,
        ).delete()
        effective_date = (
            timezone.localtime(self.pickup_datetime).date()
            if self.pickup_datetime
            else timezone.localdate()
        )
        mandatory_extras = self.supplier.extras.filter(
            is_active=True,
            is_mandatory=True,
        )
        for extra in mandatory_extras:
            selected_rate = self._select_extra_rate(extra, effective_date)
            if selected_rate:
                BookingExtra.objects.get_or_create(
                    booking=self,
                    extra=extra,
                    defaults={"rate": selected_rate, "quantity": 1},
                )

    def _select_extra_rate(self, extra, effective_date=None):
        effective_date = effective_date or (
            timezone.localtime(self.pickup_datetime).date()
            if self.pickup_datetime
            else timezone.localdate()
        )
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
        return rates.order_by("-priority", "-valid_from").first()

    def sync_additional_driver_extra(self):
        paid_driver_count = max(self.drivers.count() - 2, 0)
        try:
            extra = self.supplier.extras.get(
                extra_code="ADDITIONAL_DRIVER",
                is_active=True,
            )
        except self.supplier.extras.model.DoesNotExist:
            return
        existing = self.extras.filter(extra=extra).first()
        if paid_driver_count == 0:
            if existing:
                existing.delete()
            return
        selected_rate = self._select_extra_rate(extra)
        if selected_rate:
            booking_extra, _ = BookingExtra.objects.get_or_create(
                booking=self,
                extra=extra,
                defaults={"rate": selected_rate, "quantity": paid_driver_count},
            )
            if booking_extra.quantity != paid_driver_count:
                booking_extra.quantity = paid_driver_count
                booking_extra.save()

    def sync_young_driver_extras(self):
        young_driver_count = self.drivers.filter(young_driver_status=True).count()
        extras = self.supplier.extras.filter(
            extra_code__in=("YOUNG_DRIVER", "YOUNG_DRIVER_21_24"),
            is_active=True,
        )
        for extra in extras:
            existing = self.extras.filter(extra=extra).first()
            if young_driver_count == 0:
                if existing:
                    existing.delete()
                continue
            selected_rate = self._select_extra_rate(extra)
            if selected_rate:
                booking_extra, _ = BookingExtra.objects.get_or_create(
                    booking=self,
                    extra=extra,
                    defaults={"rate": selected_rate, "quantity": young_driver_count},
                )
                if booking_extra.quantity != young_driver_count:
                    booking_extra.quantity = young_driver_count
                    booking_extra.save()

    def sync_after_hours_extra(self):
        events = (
            (self.pickup_datetime, self.pickup_location),
            (self.return_datetime, self.return_location),
        )
        event_count = sum(
            self._needs_after_hours_charge(value, location)
            for value, location in events
            if value
        )
        extras = self.supplier.extras.filter(
            extra_code__in=("NIGHT_SERVICE", "OUT_OF_HOURS"),
            is_active=True,
        )
        for extra in extras:
            existing = self.extras.filter(extra=extra).first()
            if event_count == 0:
                if existing:
                    existing.delete()
                continue
            selected_rate = self._select_extra_rate(extra)
            if selected_rate:
                booking_extra, _ = BookingExtra.objects.get_or_create(
                    booking=self,
                    extra=extra,
                    defaults={"rate": selected_rate, "quantity": event_count},
                )
                if booking_extra.quantity != event_count:
                    booking_extra.quantity = event_count
                    booking_extra.save()

    @staticmethod
    def _is_after_hours(value):
        local_hour = timezone.localtime(value).hour
        return local_hour >= 20 or local_hour < 8

    def _needs_after_hours_charge(self, value, location):
        if not self._is_after_hours(value):
            return False
        if (
            self.supplier.supplier_name == "Kaizen Rent"
            and location
            and location.airport_code.upper() in {"GDN", "KTW", "KRK", "WAW"}
        ):
            return False
        return True

    def recalculate_extra_prices(self):
        for item in self.extras.all():
            price = item._calculate_price()
            BookingExtra.objects.filter(pk=item.pk).update(
                calculated_price_gross=price,
                calculation_complete=item.calculation_complete,
                calculation_warning=item.calculation_warning,
            )
        self.recalculate_totals()

    def recalculate_totals(self):
        if not self.pk:
            return
        extras_total = sum(
            (
                item.calculated_price_gross
                for item in self.extras.filter(
                    included_in_total=True,
                    calculation_complete=True,
                )
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
        pickup_date = timezone.localtime(self.pickup_datetime).date()
        rates = VehicleRate.objects.filter(
            is_active=True,
            vehicle_group=self.vehicle_group.effective_rate_group,
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

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        self.booking.sync_additional_driver_extra()
        self.booking.sync_young_driver_extras()
        self.booking.recalculate_extra_prices()
        self.booking.log_history(
            BookingHistoryEvent.EventType.DRIVER_CHANGED,
            f"Driver {'added' if is_new else 'updated'}: {self.first_name} {self.last_name}",
        )

    def delete(self, *args, **kwargs):
        booking = self.booking
        result = super().delete(*args, **kwargs)
        booking.sync_additional_driver_extra()
        booking.sync_young_driver_extras()
        booking.recalculate_extra_prices()
        booking.log_history(
            BookingHistoryEvent.EventType.DRIVER_CHANGED,
            f"Driver removed: {self.first_name} {self.last_name}",
        )
        return result


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
    distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    formula_units = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Special units used by a formula, for example missing fuel litres.",
    )
    actual_cost_gross = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
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
    calculation_complete = models.BooleanField(default=True, editable=False)
    calculation_warning = models.CharField(max_length=250, blank=True, editable=False)
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
        is_new = self._state.adding
        if is_new:
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
        self.booking.log_history(
            BookingHistoryEvent.EventType.EXTRA_CHANGED,
            f"Extra {'added' if is_new else 'updated'}: {self.customer_visible_name}",
            changes={
                "quantity": str(self.quantity),
                "calculated_price_gross": str(self.calculated_price_gross),
            },
        )

    def delete(self, *args, **kwargs):
        booking = self.booking
        result = super().delete(*args, **kwargs)
        booking.recalculate_totals()
        booking.log_history(
            BookingHistoryEvent.EventType.EXTRA_CHANGED,
            f"Extra removed: {self.customer_visible_name}",
        )
        return result

    def _calculate_price(self):
        self.calculation_complete = True
        self.calculation_warning = ""
        calculation_type = self.calculation_type_snapshot
        days = Decimal(self.booking.rental_days or 1)
        formula = self.formula_snapshot or {}
        if self.extra.extra_code == "ADDITIONAL_DRIVER":
            paid_drivers = Decimal(max(self.booking.drivers.count() - 2, 0))
            if calculation_type in ("PER_DAY", "PER_DRIVER_DAY"):
                price = self.unit_price_gross_snapshot * paid_drivers * days
            else:
                price = self.unit_price_gross_snapshot * paid_drivers
        elif calculation_type == "PER_DRIVER_DAY":
            matching_drivers = Decimal(
                self.booking.drivers.filter(young_driver_status=True).count()
            )
            price = self.unit_price_gross_snapshot * matching_drivers * days
        elif calculation_type == "PER_DAY":
            price = self.unit_price_gross_snapshot * self.quantity * days
        elif calculation_type == "PER_UNIT":
            price = self.unit_price_gross_snapshot * self.quantity
        elif calculation_type == "FORMULA":
            price = self._calculate_formula(formula, days)
        else:
            price = self.unit_price_gross_snapshot * self.quantity
        if self.minimum_amount_gross_snapshot is not None:
            price = max(price, self.minimum_amount_gross_snapshot)
        if self.maximum_amount_gross_snapshot is not None:
            price = min(price, self.maximum_amount_gross_snapshot)
        return price

    def _calculate_formula(self, formula, days):
        if "total_per_rental_gross" in formula:
            return Decimal(str(formula["total_per_rental_gross"])) * self.quantity
        if "per_rental_gross" in formula or "per_rental_day_gross" in formula:
            base = Decimal(str(formula.get("per_rental_gross", 0)))
            per_day = Decimal(str(formula.get("per_rental_day_gross", 0)))
            return (base + per_day * days) * self.quantity
        price = self.unit_price_gross_snapshot * self.quantity
        if "per_km_gross" in formula:
            if self.distance_km is None:
                self.calculation_complete = False
                self.calculation_warning = "Enter distance in kilometres."
                return Decimal("0.00")
            price += Decimal(str(formula["per_km_gross"])) * self.distance_km
        if "per_missing_liter_gross" in formula:
            if self.formula_units is None:
                self.calculation_complete = False
                self.calculation_warning = "Enter the number of missing fuel litres."
                return Decimal("0.00")
            price += Decimal(str(formula["per_missing_liter_gross"])) * self.formula_units
        if "plus" in formula:
            if self.actual_cost_gross is None:
                self.calculation_complete = False
                self.calculation_warning = f"Enter actual cost: {formula['plus']}."
                return Decimal("0.00")
            price += self.actual_cost_gross
        return price

    def __str__(self):
        return f"{self.booking} - {self.customer_visible_name}"


class BookingHistoryEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        STATUS_CHANGED = "STATUS_CHANGED", "Status changed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No-show"
        DETAILS_CHANGED = "DETAILS_CHANGED", "Details changed"
        PRICE_OVERRIDE = "PRICE_OVERRIDE", "Price overridden"
        DRIVER_CHANGED = "DRIVER_CHANGED", "Driver changed"
        EXTRA_CHANGED = "EXTRA_CHANGED", "Extra changed"
        NOTE = "NOTE", "Note"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="history_events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    description = models.TextField()
    changes = models.JSONField(default=dict, blank=True)
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)
    created_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking_history_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.booking} - {self.get_event_type_display()}"
