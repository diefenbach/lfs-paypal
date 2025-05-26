from django.contrib import admin
from .models import PayPalPayment, PayPalPaymentEntry


class PayPalPaymentEntryInline(admin.TabularInline):
    model = PayPalPaymentEntry
    extra = 0
    fields = ("status", "created_at")
    readonly_fields = ("status", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PayPalPayment)
class PayPalPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "order", "amount", "currency", "created_at", "updated_at")
    list_filter = ("currency", "created_at")
    search_fields = ("payment_id", "payer_id", "order__id")
    date_hierarchy = "created_at"
    fields = readonly_fields = ("payment_id", "order", "amount", "currency", "created_at", "updated_at")
    inlines = [PayPalPaymentEntryInline]
