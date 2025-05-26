from django.db import models

from lfs.order.models import Order


class PayPalPayment(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True)
    temp_order_id = models.CharField(max_length=50, unique=True, help_text="PayPal payment ID", default="")
    payment_id = models.CharField(max_length=255, unique=True, help_text="PayPal payment ID")
    payer_id = models.CharField(max_length=255, null=True, blank=True, help_text="PayPal payer ID")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.payment_id} for Order {self.order_id}"

    def add_entry(self, status):
        PayPalPaymentEntry.objects.create(payment=self, status=status)


class PayPalPaymentEntry(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    ]

    payment = models.ForeignKey(PayPalPayment, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return ""
