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
    supports_pickup = models.BooleanField(default=True)
    supports_return = models.BooleanField(default=True)
    supports_delivery = models.BooleanField(default=False)
    supports_after_hours = models.BooleanField(default=False)
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
