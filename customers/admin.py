from django.contrib import admin

from .models import Customer, CustomerEvent


class CustomerEventInline(admin.TabularInline):
    model = CustomerEvent
    extra = 0
    fields = (
        "event_date",
        "event_type",
        "severity",
        "title",
        "is_warning",
        "is_resolved",
    )
    show_change_link = True


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "phone_1",
        "email",
        "country",
        "wants_invoice",
        "status",
        "warning_level",
    )
    list_filter = (
        "status",
        "warning_level",
        "wants_invoice",
        "country",
        "preferred_language",
    )
    search_fields = (
        "first_name",
        "last_name",
        "full_name_latin",
        "email",
        "phone_1",
        "phone_2",
        "phone_3",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = (CustomerEventInline,)
    fieldsets = (
        (
            "Customer",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "full_name_latin",
                    "email",
                    "phone_1",
                    "phone_2",
                    "phone_3",
                    "preferred_language",
                )
            },
        ),
        (
            "Home address",
            {"fields": ("country", "city", "address", "postal_code")},
        ),
        (
            "Invoice",
            {
                "fields": (
                    "wants_invoice",
                    "invoice_name",
                    "invoice_tax_id",
                    "invoice_country",
                    "invoice_city",
                    "invoice_address",
                    "invoice_postal_code",
                    "invoice_email",
                )
            },
        ),
        (
            "Internal",
            {
                "fields": (
                    "preferred_supplier",
                    "status",
                    "warning_level",
                    "warning_text",
                    "internal_note",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(CustomerEvent)
class CustomerEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_date",
        "customer",
        "event_type",
        "severity",
        "title",
        "is_warning",
        "is_resolved",
    )
    list_filter = ("event_type", "severity", "is_warning", "is_resolved")
    search_fields = (
        "customer__first_name",
        "customer__last_name",
        "title",
        "description",
    )
    date_hierarchy = "event_date"
