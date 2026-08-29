from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Supplier(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    supplier_code = models.CharField(max_length=30, unique=True)
    supplier_name = models.CharField(max_length=120)
    legal_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    default_currency = models.CharField(max_length=3, default="PLN")
    booking_email = models.EmailField(blank=True)
    changes_email = models.EmailField(blank=True)
    settlement_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    website = models.URLField(blank=True)
    internal_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["supplier_name"]

    def __str__(self):
        return self.supplier_name


class SupplierLocation(models.Model):
    class LocationType(models.TextChoices):
        BRANCH = "BRANCH", "Branch"
        AIRPORT = "AIRPORT", "Airport"
        HOTEL_DELIVERY = "HOTEL_DELIVERY", "Hotel delivery"
        ADDRESS_DELIVERY = "ADDRESS_DELIVERY", "Address delivery"
        SEASONAL_POINT = "SEASONAL_POINT", "Seasonal point"
        CUSTOM_POINT = "CUSTOM_POINT", "Custom point"
        OTHER = "OTHER", "Other"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="locations",
    )
    location_code = models.CharField(max_length=30)
    location_name = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Poland")
    address = models.CharField(max_length=250, blank=True)
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.BRANCH,
    )
    airport_code = models.CharField(max_length=3, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    supports_pickup = models.BooleanField(default=True)
    supports_return = models.BooleanField(default=True)
    has_rental_desk = models.BooleanField(default=False)
    supports_terminal_delivery = models.BooleanField(default=False)
    supports_address_delivery = models.BooleanField(default=False)
    supports_after_hours = models.BooleanField(default=False)
    supports_self_return_via_key_box = models.BooleanField(default=False)
    requires_prepayment = models.BooleanField(default=False)
    default_pickup_instructions = models.TextField(blank=True)
    default_return_instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    internal_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["supplier__supplier_name", "location_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "location_code"],
                name="unique_location_code_per_supplier",
            ),
        ]

    def __str__(self):
        return f"{self.supplier.supplier_name} — {self.location_name}"


class VehicleGroup(models.Model):
    class Transmission(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATIC = "AUTOMATIC", "Automatic"
        UNKNOWN = "UNKNOWN", "Unknown"

    class BodyType(models.TextChoices):
        SEDAN = "SEDAN", "Sedan"
        HATCHBACK = "HATCHBACK", "Hatchback"
        SUV = "SUV", "SUV"
        ESTATE = "ESTATE", "Estate / Wagon"
        MINIVAN = "MINIVAN", "Minivan"
        VAN = "VAN", "Van"
        PICKUP = "PICKUP", "Pickup"
        COUPE = "COUPE", "Coupe"
        CABRIO = "CABRIO", "Cabrio"
        OTHER = "OTHER", "Other"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="vehicle_groups",
    )
    rate_source_group = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="groups_using_this_rate",
        help_text="Tariff group to use when a price list has a broader group name.",
    )
    group_code = models.CharField(max_length=40)
    group_name = models.CharField(max_length=120)
    category = models.CharField(max_length=80, blank=True)
    body_type = models.CharField(max_length=20, choices=BodyType.choices, blank=True)
    transmission = models.CharField(
        max_length=10,
        choices=Transmission.choices,
        default=Transmission.UNKNOWN,
    )
    seats = models.PositiveSmallIntegerField(null=True, blank=True)
    doors = models.PositiveSmallIntegerField(null=True, blank=True)
    luggage_volume_liters = models.PositiveIntegerField(null=True, blank=True)
    luggage_large = models.PositiveSmallIntegerField(null=True, blank=True)
    luggage_small = models.PositiveSmallIntegerField(null=True, blank=True)
    luggage_priority = models.PositiveSmallIntegerField(default=0)
    cargo_note = models.CharField(max_length=250, blank=True)
    fuel_type_note = models.CharField(max_length=120, blank=True)
    deposit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Card authorization amount for this vehicle group.",
    )
    deposit_currency = models.CharField(max_length=3, default="PLN")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    internal_note = models.TextField(blank=True)
    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)
    booking_open_from = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["supplier__supplier_name", "display_order", "group_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "group_code"],
                name="unique_vehicle_group_code_per_supplier",
            ),
        ]

    @property
    def effective_rate_group(self):
        return self.rate_source_group or self

    def __str__(self):
        return f"{self.supplier.supplier_name} — {self.group_name} ({self.group_code})"


class VehicleModel(models.Model):
    vehicle_group = models.ForeignKey(
        VehicleGroup,
        on_delete=models.CASCADE,
        related_name="models",
    )
    brand = models.CharField(max_length=80, blank=True)
    model = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "brand", "model"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle_group", "brand", "model"],
                name="unique_model_per_vehicle_group",
            ),
        ]

    def __str__(self):
        return " ".join(part for part in (self.brand, self.model) if part)


class VehicleComparisonClass(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    vehicle_groups = models.ManyToManyField(
        VehicleGroup,
        related_name="comparison_classes",
        blank=True,
    )

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name


class SupplierExtra(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="extras",
    )
    extra_code = models.CharField(max_length=40)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["supplier__supplier_name", "category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "extra_code"],
                name="unique_extra_code_per_supplier",
            )
        ]

    def __str__(self):
        return f"{self.supplier.supplier_name} — {self.name}"


class SupplierExtraRate(models.Model):
    class CalculationType(models.TextChoices):
        FIXED = "FIXED", "Fixed"
        PER_DAY = "PER_DAY", "Per day"
        PER_RENTAL = "PER_RENTAL", "Per rental"
        PER_UNIT = "PER_UNIT", "Per unit"
        PER_DRIVER_DAY = "PER_DRIVER_DAY", "Per driver per day"
        FORMULA = "FORMULA", "Formula"

    extra = models.ForeignKey(
        SupplierExtra,
        on_delete=models.CASCADE,
        related_name="rates",
    )
    rate_code = models.CharField(max_length=50, default="DEFAULT")
    location = models.ForeignKey(
        SupplierLocation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="extra_rates",
    )
    calculation_type = models.CharField(
        max_length=20,
        choices=CalculationType.choices,
    )
    amount_gross = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Final customer price including VAT.",
    )
    currency = models.CharField(max_length=3, default="PLN")
    days_from = models.PositiveSmallIntegerField(null=True, blank=True)
    days_to = models.PositiveSmallIntegerField(null=True, blank=True)
    minimum_amount_gross = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    maximum_amount_gross = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    formula_config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["extra", "-priority", "-valid_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["extra", "rate_code"],
                name="unique_rate_code_per_extra",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.location_id and self.extra_id:
            if self.location.supplier_id != self.extra.supplier_id:
                errors["location"] = "The location must belong to the same supplier."
        if self.days_from and self.days_to and self.days_to < self.days_from:
            errors["days_to"] = "The last rental day cannot be before the first."
        if self.valid_to and self.valid_to < self.valid_from:
            errors["valid_to"] = "The end date cannot be before the start date."
        if (
            self.minimum_amount_gross is not None
            and self.maximum_amount_gross is not None
            and self.maximum_amount_gross < self.minimum_amount_gross
        ):
            errors["maximum_amount_gross"] = (
                "The maximum amount cannot be below the minimum amount."
            )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.extra} — {self.amount_gross} {self.currency} "
            f"({self.get_calculation_type_display()})"
        )


class PriceList(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    class SourceType(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        EXCEL = "EXCEL", "Excel"

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="price_lists",
    )
    name = models.CharField(max_length=150)
    version = models.CharField(max_length=50)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="PLN")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
    )
    source_file = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["supplier__supplier_name", "-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["supplier", "version"],
                name="unique_price_list_version_per_supplier",
            )
        ]

    def clean(self):
        super().clean()
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError(
                {"effective_to": "The end date cannot be before the start date."}
            )

    def __str__(self):
        return f"{self.supplier.supplier_name} - {self.name} ({self.version})"


class PriceSeason(models.Model):
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name="seasons",
    )
    season_code = models.CharField(max_length=50)
    season_name = models.CharField(max_length=120)
    rental_date_from = models.DateField()
    rental_date_to = models.DateField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["rental_date_from", "-priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["price_list", "season_code"],
                name="unique_season_code_per_price_list",
            )
        ]

    def clean(self):
        super().clean()
        if self.rental_date_to and self.rental_date_to < self.rental_date_from:
            raise ValidationError(
                {"rental_date_to": "The end date cannot be before the start date."}
            )

    def __str__(self):
        return f"{self.price_list} - {self.season_name}"


class PriceDayRange(models.Model):
    price_list = models.ForeignKey(
        PriceList,
        on_delete=models.CASCADE,
        related_name="day_ranges",
    )
    range_code = models.CharField(max_length=30)
    label = models.CharField(max_length=80)
    days_from = models.PositiveSmallIntegerField()
    days_to = models.PositiveSmallIntegerField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["sort_order", "days_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["price_list", "range_code"],
                name="unique_day_range_code_per_price_list",
            )
        ]

    def clean(self):
        super().clean()
        if self.days_to is not None and self.days_to < self.days_from:
            raise ValidationError(
                {"days_to": "The last day cannot be before the first day."}
            )

    def __str__(self):
        return f"{self.price_list} - {self.label}"


class VehicleRate(models.Model):
    season = models.ForeignKey(
        PriceSeason,
        on_delete=models.CASCADE,
        related_name="vehicle_rates",
    )
    vehicle_group = models.ForeignKey(
        VehicleGroup,
        on_delete=models.PROTECT,
        related_name="rates",
    )
    day_range = models.ForeignKey(
        PriceDayRange,
        on_delete=models.PROTECT,
        related_name="vehicle_rates",
    )
    daily_rate_gross = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Daily customer price including VAT.",
    )
    currency = models.CharField(max_length=3, default="PLN")
    is_active = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["season", "vehicle_group", "day_range"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "vehicle_group", "day_range"],
                name="unique_vehicle_rate",
            )
        ]

    def clean(self):
        super().clean()
        errors = {}
        price_list = self.season.price_list
        if self.day_range.price_list_id != price_list.id:
            errors["day_range"] = "Day range and season must use the same price list."
        if self.vehicle_group.supplier_id != price_list.supplier_id:
            errors["vehicle_group"] = "Vehicle group must belong to the supplier."
        if self.currency != price_list.currency:
            errors["currency"] = "Rate and price-list currencies must match."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f"{self.vehicle_group} - {self.season.season_name} - "
            f"{self.day_range.label}: {self.daily_rate_gross} {self.currency}/day"
        )
