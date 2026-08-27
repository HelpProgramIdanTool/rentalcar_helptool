from django.contrib import admin

from .models import TaxRate


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = (
        "country",
        "tax_name",
        "rate_percent",
        "valid_from",
        "valid_to",
        "is_active",
    )
    list_filter = ("country", "tax_name", "is_active")
    search_fields = ("country", "tax_name")
    date_hierarchy = "valid_from"
