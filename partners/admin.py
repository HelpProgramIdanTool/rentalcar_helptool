from django.contrib import admin
from .models import PartnerAccess, PortalConfiguration, SupplierSummary, PartnerDraft, PartnerDelivery


@admin.register(PartnerAccess)
class PartnerAccessAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'email', 'user', 'is_active']
    search_fields = ['display_name', 'email']


admin.site.register(PortalConfiguration)
admin.site.register(SupplierSummary)


@admin.register(PartnerDraft)
class PartnerDraftAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'quote', 'manual_requested', 'updated_at']
    readonly_fields = ['id', 'partner', 'trip', 'selected_groups', 'quote', 'manual_message', 'manual_requested', 'delivery_html', 'delivery_subject', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        return False


@admin.register(PartnerDelivery)
class PartnerDeliveryAdmin(admin.ModelAdmin):
    list_display = ['draft', 'recipient', 'sent_at']
    readonly_fields = ['draft', 'recipient', 'sent_at', 'error']

    def has_add_permission(self, request):
        return False
