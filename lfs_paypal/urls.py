from django.urls import path
from . import views

app_name = "paypal"

urlpatterns = [
    path("capture-payment/", views.capture_payment, name="capture_payment"),
    path("payment-cancelled/", views.payment_cancelled, name="payment_cancelled"),
    path("webhook/", views.paypal_webhook, name="paypal_webhook"),
]
