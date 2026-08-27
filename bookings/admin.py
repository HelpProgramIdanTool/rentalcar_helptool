from django.contrib import admin

from .models import Booking, BookingDriver


class BookingDriverInline(admin.TabularInline):
    model = BookingDriver
    extra = 1


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
    readonly_fields = ("booking_number", "rental_days", "created_at", "updated_at")
    inlines = (BookingDriverInline,)


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
