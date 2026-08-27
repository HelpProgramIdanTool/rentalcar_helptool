from django.contrib import admin

from .models import Supplier, SupplierLocation, VehicleGroup, VehicleModel


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
        "phone",
        "location_type",
        "has_rental_desk",
        "supports_self_return_via_key_box",
        "is_active",
    )
    list_filter = (
        "supplier",
        "location_type",
        "has_rental_desk",
        "supports_terminal_delivery",
        "supports_address_delivery",
        "supports_self_return_via_key_box",
        "is_active",
        "country",
    )
    search_fields = (
        "location_name",
        "location_code",
        "city",
        "airport_code",
        "phone",
        "supplier__supplier_name",
    )


class VehicleModelInline(admin.TabularInline):
    model = VehicleModel
    extra = 0


@admin.register(VehicleGroup)
class VehicleGroupAdmin(admin.ModelAdmin):
    list_display = (
        "group_name",
        "group_code",
        "supplier",
        "transmission",
        "body_type",
        "is_active",
    )
    list_filter = ("supplier", "transmission", "body_type", "is_active")
    search_fields = ("group_name", "group_code", "supplier__supplier_name")
    inlines = (VehicleModelInline,)


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ("model", "brand", "vehicle_group", "is_active")
    list_filter = ("vehicle_group__supplier", "is_active")
    search_fields = (
        "brand",
        "model",
        "vehicle_group__group_name",
        "vehicle_group__group_code",
    )
