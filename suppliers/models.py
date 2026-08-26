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
