from django.contrib import admin

from .models import Quote, QuoteDocumentBlock, QuoteOption, QuoteTemplate, QuoteTemplateBlock


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("quote_number", "customer", "status", "pickup_datetime", "return_datetime")
    search_fields = ("quote_number", "customer__first_name", "customer__last_name", "customer__email")
    list_filter = ("status", "created_at")


class QuoteTemplateBlockInline(admin.TabularInline):
    model = QuoteTemplateBlock
    extra = 0


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
