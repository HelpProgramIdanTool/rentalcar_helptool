from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

from config.rental_duration import calculate_rental_days


class QuoteNumberSequence(models.Model):
    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    @classmethod
    def next_number(cls, year):
        with transaction.atomic():
            sequence, _ = cls.objects.select_for_update().get_or_create(year=year)
            sequence.last_number += 1
            sequence.save(update_fields=["last_number"])
            return f"OF-{year}-{sequence.last_number:05d}"


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        CLOSED = "CLOSED", "Closed"

    quote_number = models.CharField(max_length=20, unique=True, editable=False)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="quotes"
    )
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_quotes",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    language = models.CharField(max_length=50, blank=True)
    pickup_datetime = models.DateTimeField()
    return_datetime = models.DateTimeField()
    rental_days = models.PositiveIntegerField(editable=False)
    pickup_location_text = models.CharField(max_length=300)
    return_location_text = models.CharField(max_length=300)
    pickup_city = models.CharField(max_length=100, blank=True)
    pickup_service = models.CharField(max_length=30, blank=True)
    pickup_address = models.CharField(max_length=300, blank=True)
    return_city = models.CharField(max_length=100, blank=True)
    return_service = models.CharField(max_length=30, blank=True)
    return_address = models.CharField(max_length=300, blank=True)
    cross_border_requested = models.BooleanField(default=False)
    extra_requests = models.JSONField(default=dict, blank=True)
    driver_count = models.PositiveSmallIntegerField(default=1)
    vehicle_request = models.CharField(max_length=200, blank=True)
    requested_vehicle_classes = models.ManyToManyField(
        "suppliers.VehicleComparisonClass",
        related_name="quotes",
        blank=True,
    )
    requested_suppliers = models.ManyToManyField(
        "suppliers.Supplier",
        related_name="requested_in_quotes",
        blank=True,
    )
    customer_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.return_datetime and self.pickup_datetime:
            if self.return_datetime <= self.pickup_datetime:
                raise ValidationError({"return_datetime": "Return must be later than pickup."})

    def save(self, *args, **kwargs):
        if not self.quote_number:
            self.quote_number = QuoteNumberSequence.next_number(self.pickup_datetime.year)
        self.rental_days = calculate_rental_days(
            self.pickup_datetime, self.return_datetime
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quote_number} - {self.customer}"


class QuoteOption(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="options")
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT, related_name="quote_options")
    vehicle_group = models.ForeignKey("suppliers.VehicleGroup", on_delete=models.PROTECT, related_name="quote_options")
    comparison_class = models.ForeignKey("suppliers.VehicleComparisonClass", on_delete=models.PROTECT, related_name="quote_options")
    supplier_name_snapshot = models.CharField(max_length=120)
    vehicle_group_name_snapshot = models.CharField(max_length=120)
    vehicle_models_snapshot = models.TextField(blank=True)
    total_price_gross = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="PLN")
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    deposit_currency = models.CharField(max_length=3, default="PLN")
    calculation_snapshot = models.JSONField(default=dict)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_included = models.BooleanField(default=True)
    is_selected_by_customer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "total_price_gross"]
        constraints = [models.UniqueConstraint(fields=["quote", "vehicle_group"], name="one_option_per_quote_vehicle_group")]

    def __str__(self):
        return f"{self.quote.quote_number} - {self.supplier_name_snapshot} - {self.vehicle_group_name_snapshot}"


class QuoteTemplate(models.Model):
    name = models.CharField(max_length=120)
    language = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["language", "name"]

    def __str__(self):
        return f"{self.name} ({self.language})"


class QuoteTemplateBlock(models.Model):
    template = models.ForeignKey(QuoteTemplate, on_delete=models.CASCADE, related_name="blocks")
    block_key = models.CharField(max_length=50)
    title = models.CharField(max_length=150, blank=True)
    content = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=0)
    condition_code = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [models.UniqueConstraint(fields=["template", "block_key"], name="unique_block_key_per_template")]


class QuoteDocumentBlock(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="document_blocks")
    source_block = models.ForeignKey(QuoteTemplateBlock, on_delete=models.SET_NULL, null=True, blank=True)
    block_key = models.CharField(max_length=50)
    title = models.CharField(max_length=150, blank=True)
    content = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=0)
    condition_code = models.CharField(max_length=40, blank=True)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [models.UniqueConstraint(fields=["quote", "block_key"], name="unique_document_block_per_quote")]
