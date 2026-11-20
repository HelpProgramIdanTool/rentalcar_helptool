from django.contrib import admin
from .models import PartnerAccess, PortalConfiguration, SupplierSummary, PartnerDraft, PartnerDelivery, PartnerWorkspaceRecord


@admin.register(PartnerAccess)
class PartnerAccessAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'email', 'user', 'is_test', 'is_active']
    search_fields = ['display_name', 'email']
    def has_add_permission(self,request):return request.user.is_superuser
    def has_change_permission(self,request,obj=None):return request.user.is_superuser
    def has_delete_permission(self,request,obj=None):return request.user.is_superuser


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


@admin.register(PartnerWorkspaceRecord)
class PartnerWorkspaceRecordAdmin(admin.ModelAdmin):
    list_display=['number','partner','kind','status','customer_name','is_test','created_at']
    list_filter=['kind','status','partner','is_test']
    search_fields=['customer_name','partner__display_name']
    readonly_fields=['id','partner','parent','draft','booking','kind','customer_name','trip','options','price_versions','details','created_by','is_test','created_at','updated_at']
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False
