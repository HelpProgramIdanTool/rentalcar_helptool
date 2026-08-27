from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "status", "email", "phone", "login_user")
    list_filter = ("role", "status")
    search_fields = ("first_name", "last_name", "email", "phone")
    autocomplete_fields = ("login_user",)
