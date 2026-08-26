from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_name", "supplier_code", "status", "default_currency")
    list_filter = ("status", "default_currency")
    search_fields = ("supplier_name", "supplier_code", "legal_name")
