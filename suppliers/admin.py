from django.contrib import admin

from .models import (
    Supplier,
    SupplierExtra,
    SupplierExtraRate,
    SupplierLocation,
    PriceDayRange,
    PriceList,
    PriceSeason,
    VehicleRate,
    VehicleGroup,
    VehicleModel,
    VehicleComparisonClass,
)


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
        "rate_source_group",
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


@admin.register(VehicleComparisonClass)
class VehicleComparisonClassAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "vehicle_groups__group_code")
    filter_horizontal = ("vehicle_groups",)


class SupplierExtraRateInline(admin.TabularInline):
    model = SupplierExtraRate
    extra = 0


@admin.register(SupplierExtra)
class SupplierExtraAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "extra_code",
        "supplier",
        "category",
        "is_mandatory",
        "is_active",
    )
    list_filter = ("supplier", "category", "is_mandatory", "is_active")
    search_fields = ("name", "extra_code", "supplier__supplier_name")
    inlines = (SupplierExtraRateInline,)


@admin.register(SupplierExtraRate)
class SupplierExtraRateAdmin(admin.ModelAdmin):
    list_display = (
        "extra",
        "rate_code",
        "calculation_type",
        "amount_gross",
        "currency",
        "location",
        "valid_from",
        "valid_to",
        "is_active",
    )
    list_filter = (
        "extra__supplier",
        "calculation_type",
        "currency",
        "is_active",
    )
    search_fields = (
        "rate_code",
        "extra__name",
        "extra__extra_code",
        "extra__supplier__supplier_name",
    )
    date_hierarchy = "valid_from"


class PriceSeasonInline(admin.TabularInline):
    model = PriceSeason
    extra = 0


class PriceDayRangeInline(admin.TabularInline):
    model = PriceDayRange
    extra = 0


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "version",
        "supplier",
        "effective_from",
        "effective_to",
        "currency",
        "status",
    )
    list_filter = ("supplier", "status", "source_type", "currency")
    search_fields = ("name", "version", "supplier__supplier_name", "source_file")
    inlines = (PriceSeasonInline, PriceDayRangeInline)


@admin.register(PriceSeason)
class PriceSeasonAdmin(admin.ModelAdmin):
    list_display = (
        "season_name",
        "price_list",
        "rental_date_from",
        "rental_date_to",
        "priority",
        "is_active",
    )
    list_filter = ("price_list__supplier", "is_active")
    search_fields = ("season_name", "season_code", "price_list__name")


@admin.register(PriceDayRange)
class PriceDayRangeAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "price_list",
        "days_from",
        "days_to",
        "is_active",
    )
    list_filter = ("price_list__supplier", "is_active")
    search_fields = ("label", "range_code", "price_list__name")


@admin.register(VehicleRate)
class VehicleRateAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_group",
        "season",
        "day_range",
        "daily_rate_gross",
        "currency",
        "is_active",
    )
    list_filter = (
        "season__price_list__supplier",
        "season",
        "day_range",
        "is_active",
    )
    search_fields = (
        "vehicle_group__group_code",
        "vehicle_group__group_name",
        "season__season_name",
    )
