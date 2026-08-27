from django.contrib import admin

from .models import Booking, BookingDriver, BookingExtra


class BookingDriverInline(admin.TabularInline):
    model = BookingDriver
    extra = 1


class BookingExtraInline(admin.TabularInline):
    model = BookingExtra
    extra = 0
    readonly_fields = (
        "customer_visible_name",
        "calculation_type_snapshot",
        "unit_price_gross_snapshot",
        "minimum_amount_gross_snapshot",
        "maximum_amount_gross_snapshot",
        "calculated_price_gross",
        "calculation_complete",
        "calculation_warning",
        "currency_snapshot",
        "is_mandatory_snapshot",
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_number",
        "supplier_booking_number",
        "customer",
        "supplier",
        "status",
        "pickup_location",
        "return_location",
        "vehicle_group",
        "pickup_datetime",
        "return_datetime",
        "rental_days",
        "vehicle_price_gross",
        "extras_total_gross",
        "total_price_gross",
        "price_calculation_status",
        "currency",
        "created_at",
    )
    list_filter = ("status", "supplier")
    search_fields = (
        "booking_number",
        "supplier_booking_number",
        "customer__first_name",
        "customer__last_name",
        "customer__phone_1",
        "customer__email",
    )
    readonly_fields = (
        "booking_number",
        "rental_days",
        "calculated_vehicle_price_gross",
        "vehicle_price_gross",
        "vehicle_daily_rate_gross_snapshot",
        "vehicle_rate",
        "price_list_version_snapshot",
        "price_season_snapshot",
        "price_day_range_snapshot",
        "price_calculation_status",
        "extras_total_gross",
        "total_price_gross",
        "created_at",
        "updated_at",
    )
    inlines = (BookingDriverInline, BookingExtraInline)


@admin.register(BookingDriver)
class BookingDriverAdmin(admin.ModelAdmin):
    list_display = ("booking", "first_name", "last_name", "role")
    list_filter = ("role", "young_driver_status")
    search_fields = (
        "booking__booking_number",
        "first_name",
        "last_name",
        "phone_snapshot",
    )


@admin.register(BookingExtra)
class BookingExtraAdmin(admin.ModelAdmin):
    list_display = (
        "booking",
        "customer_visible_name",
        "quantity",
        "distance_km",
        "formula_units",
        "actual_cost_gross",
        "calculated_price_gross",
        "currency_snapshot",
        "is_mandatory_snapshot",
        "included_in_total",
    )
    list_filter = (
        "calculation_complete",
        "is_mandatory_snapshot",
        "included_in_total",
        "extra__supplier",
    )
    search_fields = (
        "booking__booking_number",
        "customer_visible_name",
        "extra__extra_code",
    )
    readonly_fields = (
        "customer_visible_name",
        "supplier_visible_name",
        "calculation_type_snapshot",
        "unit_price_gross_snapshot",
        "minimum_amount_gross_snapshot",
        "maximum_amount_gross_snapshot",
        "calculated_price_gross",
        "calculation_complete",
        "calculation_warning",
        "currency_snapshot",
        "formula_snapshot",
        "is_mandatory_snapshot",
    )
