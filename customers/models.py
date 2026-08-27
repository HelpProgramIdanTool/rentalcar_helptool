from django.db import models


class Customer(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        BLOCKED = "BLOCKED", "Blocked"

    class WarningLevel(models.TextChoices):
        NONE = "NONE", "None"
        INFO = "INFO", "Information"
        WARNING = "WARNING", "Warning"
        SERIOUS = "SERIOUS", "Serious"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    full_name_latin = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone_1 = models.CharField(max_length=30)
    phone_2 = models.CharField(max_length=30, blank=True)
    phone_3 = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=50, blank=True)
    preferred_supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_by_customers",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    warning_level = models.CharField(
        max_length=20,
        choices=WarningLevel.choices,
        default=WarningLevel.NONE,
    )
    warning_text = models.TextField(blank=True)
    internal_note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class CustomerEvent(models.Model):
    class EventType(models.TextChoices):
        CANCELLATION = "CANCELLATION", "Cancellation"
        REFUSAL = "REFUSAL", "Refusal"
        NO_SHOW = "NO_SHOW", "No-show"
        ACCIDENT = "ACCIDENT", "Accident"
        DAMAGE = "DAMAGE", "Damage"
        COMPLAINT = "COMPLAINT", "Complaint"
        PAYMENT_ISSUE = "PAYMENT_ISSUE", "Payment issue"
        LATE_RETURN = "LATE_RETURN", "Late return"
        DISPUTE = "DISPUTE", "Dispute"
        SUPPLIER_PREFERENCE = "SUPPLIER_PREFERENCE", "Supplier preference"
        POSITIVE_NOTE = "POSITIVE_NOTE", "Positive note"
        MANUAL_WARNING = "MANUAL_WARNING", "Manual warning"
        OTHER = "OTHER", "Other"

    class Severity(models.TextChoices):
        INFO = "INFO", "Information"
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    event_date = models.DateField()
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFO,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    supplier = models.ForeignKey(
        "suppliers.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_events",
    )
    created_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_events",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_warning = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.customer}: {self.title}"

