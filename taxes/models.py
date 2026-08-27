from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class TaxRate(models.Model):
    country = models.CharField(max_length=100)
    tax_name = models.CharField(max_length=50, default="VAT")
    rate_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["country", "tax_name", "-valid_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "tax_name", "valid_from"],
                name="unique_tax_rate_start_date",
            ),
            models.CheckConstraint(
                condition=Q(rate_percent__gte=0) & Q(rate_percent__lte=100),
                name="tax_rate_between_zero_and_one_hundred",
            ),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gte=models.F("valid_from")),
                name="tax_rate_end_not_before_start",
            ),
        ]

    def clean(self):
        super().clean()
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError(
                {"valid_to": "The end date cannot be earlier than the start date."}
            )

    def __str__(self):
        return f"{self.country} {self.tax_name} {self.rate_percent}%"
