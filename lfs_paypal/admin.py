from django.contrib import admin
from .models import PayPalPayment, PayPalPaymentEntry


class PayPalPaymentEntryInline(admin.TabularInline):
    model = PayPalPaymentEntry
    extra = 0
    fields = ("status", "created_at_with_seconds")
    readonly_fields = ("status", "created_at_with_seconds")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def created_at_with_seconds(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M:%S")

    created_at_with_seconds.short_description = "Created At"


@admin.register(PayPalPayment)
class PayPalPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "order", "amount", "currency", "created_at", "updated_at")
    list_filter = ("currency", "created_at")
    search_fields = ("payment_id", "payer_id", "order__id")
    date_hierarchy = "created_at"
    fields = readonly_fields = ("payment_id", "order", "amount", "currency", "created_at", "updated_at")
    inlines = [PayPalPaymentEntryInline]
