from django.contrib import admin

from .models import Employee, SubAgent


@admin.register(SubAgent)
class SubAgentAdmin(admin.ModelAdmin):
    list_display = ("code_prefix", "name", "phone", "email", "is_active")
    search_fields = ("code_prefix", "name", "phone", "email")
    list_filter = ("is_active",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "status", "email", "phone", "login_user")
    list_filter = ("role", "status")
    search_fields = ("first_name", "last_name", "email", "phone")
    autocomplete_fields = ("login_user",)
