from django.contrib import admin

from .models import Supplier, SupplierLocation


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_name", "supplier_code", "status", "default_currency")
    list_filter = ("status", "default_currency")
    search_fields = ("supplier_name", "supplier_code", "legal_name")


@admin.register(SupplierLocation)
class SupplierLocationAdmin(admin.ModelAdmin):
    list_display = (
        "location_name",
        "supplier",
        "city",
        "location_type",
        "is_active",
    )
    list_filter = ("supplier", "location_type", "is_active", "country")
    search_fields = (
        "location_name",
        "location_code",
        "city",
        "airport_code",
        "supplier__supplier_name",
    )
