from django.contrib import admin

from .models import Quote, QuoteDocumentBlock, QuoteOption, QuoteTemplate, QuoteTemplateBlock


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "quote_number", "customer", "status", "sent_at",
        "pickup_datetime", "return_datetime",
    )
    search_fields = ("quote_number", "customer__first_name", "customer__last_name", "customer__email")
    list_filter = ("status", "created_at")


class QuoteTemplateBlockInline(admin.TabularInline):
    model = QuoteTemplateBlock
    extra = 0

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "content" and field:
            field.required = False
            field.help_text = "В представлении используйте {suppliers} для списка фирм. Ссылки: по одной на строку."
        return field


@admin.register(QuoteTemplate)
class QuoteTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "language", "is_active")
    list_filter = ("language", "is_active")
    inlines = (QuoteTemplateBlockInline,)


@admin.register(QuoteDocumentBlock)
class QuoteDocumentBlockAdmin(admin.ModelAdmin):
    list_display = ("quote", "block_key", "display_order", "is_enabled")
    list_filter = ("is_enabled", "condition_code")


@admin.register(QuoteOption)
class QuoteOptionAdmin(admin.ModelAdmin):
    list_display = (
        "quote", "supplier", "vehicle_group", "total_price_gross",
        "deposit_amount", "is_included",
    )
