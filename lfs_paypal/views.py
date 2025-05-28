import json
import logging

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

import requests
from lfs.cart import utils as cart_utils
from lfs.core.signals import order_paid, order_submitted
from lfs.order.settings import PAID
from lfs.order.utils import add_order
from lfs_paypal.models import PayPalPayment, PayPalPaymentEntry
from lfs_paypal.utils import PAYPAL_ORDER_CAPTURE_API, get_paypal_auth_token

logger = logging.getLogger("lfs.paypal")


@csrf_exempt
def capture_payment(request):
    """
    Capture the PayPal payment after user approval using v2 API.
    This is where PayPal redirects after the user approves the payment.
    """
    token = request.GET.get("token")

    # Get the payment from database - still using payment_id field to store the order ID
    try:
        paypal_payment = PayPalPayment.objects.get(payment_id=token)
    except PayPalPayment.DoesNotExist:
        logger.error(f"Payment not found for token: {token}")
        return render(request, "lfs_paypal/payment_error.html", {"error": "Payment not found."})

    # Get access token
    access_token = get_paypal_auth_token()
    if not access_token:
        return render(
            request, "lfs_paypal/payment_error.html", {"error": "Could not authenticate with PayPal. Please try again."}
        )

    # Capture payment using v2 API
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    capture_url = PAYPAL_ORDER_CAPTURE_API.format(token)
    response = requests.post(capture_url, headers=headers, json={})

    if response.status_code == 201:
        # For any reasons paypal calls this view two times
        cart = cart_utils.get_cart(request)
        if cart is None:
            return redirect(reverse("lfs_thank_you"))

        capture_response = response.json()
        if capture_response["status"] == "COMPLETED":
            logger.info(f"Creating order for payment {token}")
            order = add_order(request)
            logger.info(f"Order created: {order.id}")
            order.state = PAID
            order.save()

            # Notify the system
            order_submitted.send(sender=order, request=request)
            order_paid.send(sender=order, request=request)

            # Save payment info to database
            paypal_payment.order = order
            payer_id = capture_response.get("payer", {}).get("payer_id", "")
            if payer_id:
                paypal_payment.payer_id = payer_id
            paypal_payment.save()
            paypal_payment.add_entry(PayPalPaymentEntry.COMPLETED)

            return redirect(reverse("lfs_thank_you"))

    # Payment capture failed
    paypal_payment.add_entry(PayPalPaymentEntry.FAILED)

    logger.error(f"PayPal payment capture failed: {response.text}")
    return render(request, "lfs_paypal/payment_error.html", {"error": "Payment failed. Please try again."})


def payment_cancelled(request):
    """
    Display payment cancelled page.
    This is designed to be shown in a popup window that will
    communicate with the parent window and close itself.
    """
    return render(request, "lfs_paypal/payment_cancelled.html")


@csrf_exempt
def paypal_webhook(request):
    """
    Webhook for PayPal notifications.
    Updated to support both v1 and v2 event types.
    """
    logger.info(f"PayPal webhook received: {request.body}")
    if request.method == "POST":
        try:
            # Verify webhook
            webhook_data = json.loads(request.body.decode("utf-8"))
            event_type = webhook_data.get("event_type")
            resource = webhook_data.get("resource", {})

            # Process based on event type
            # v1 API event
            if event_type == "PAYMENT.SALE.COMPLETED":
                payment_id = resource.get("parent_payment")
                if payment_id:
                    try:
                        payment = PayPalPayment.objects.get(payment_id=payment_id)
                        payment.add_entry(PayPalPaymentEntry.COMPLETED)
                        logger.info(f"Payment {payment_id} confirmed via webhook (v1)")
                    except PayPalPayment.DoesNotExist:
                        logger.error(f"Payment not found in webhook: {payment_id}")

            # v2 API events
            elif event_type == "CHECKOUT.ORDER.APPROVED":
                order_id = resource.get("id")
                if order_id:
                    try:
                        payment = PayPalPayment.objects.get(payment_id=order_id)
                        payment.add_entry(PayPalPaymentEntry.APPROVED)
                        logger.info(f"Order {order_id} approved via webhook (v2)")
                    except PayPalPayment.DoesNotExist:
                        logger.error(f"Order not found in webhook: {order_id}")

            elif event_type == "CHECKOUT.ORDER.COMPLETED":
                order_id = resource.get("id")
                if order_id:
                    try:
                        payment = PayPalPayment.objects.get(payment_id=order_id)
                        payment.add_entry(PayPalPaymentEntry.COMPLETED)
                        logger.info(f"Order {order_id} completed via webhook (v2)")
                    except PayPalPayment.DoesNotExist:
                        logger.error(f"Order not found in webhook: {order_id}")

            return HttpResponse(status=200)
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return HttpResponse(status=500)

    return HttpResponse(status=400)
