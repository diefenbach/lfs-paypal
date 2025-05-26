import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP


from django.shortcuts import redirect, render
from django.urls import reverse

import requests

from lfs.customer import utils as customer_utils
from lfs.plugins import PaymentMethodProcessor
from lfs.plugins import PM_ORDER_ACCEPTED
from lfs_paypal.models import PayPalPayment, PayPalPaymentEntry
from lfs_paypal.utils import PAYPAL_ORDERS_API, get_paypal_auth_token


# django paypal imports
logger = logging.getLogger("lfs.paypal")


class PayPalProcessor(PaymentMethodProcessor):

    def get_create_order_time(self):
        return PM_ORDER_ACCEPTED

    def process(self):
        """
        Initialize the payment.
        """
        customer = customer_utils.get_customer(self.request)
        cart_price_gross = self.cart.get_total_price_gross(self.request)

        order_amount = Decimal(cart_price_gross)
        order_amount = order_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Get access token
        access_token = get_paypal_auth_token()
        if not access_token:
            return render(
                self.request,
                "lfs_paypal/payment_error.html",
            )

        temp_order_id = str(uuid.uuid4())

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": temp_order_id,
                    "description": f"Payment for Order #{temp_order_id}",
                    "amount": {
                        "currency_code": "EUR",
                        "value": str(order_amount),
                        "breakdown": {"item_total": {"currency_code": "EUR", "value": str(order_amount)}},
                    },
                    "items": [
                        {
                            "name": f"Order #{temp_order_id}",
                            "unit_amount": {"currency_code": "EUR", "value": str(order_amount)},
                            "quantity": "1",
                            "category": "PHYSICAL_GOODS",
                        }
                    ],
                    "shipping": {
                        "name": {
                            "full_name": f"{customer.selected_shipping_address.firstname} {customer.selected_shipping_address.lastname}"
                        },
                        "address": {
                            "address_line_1": customer.selected_shipping_address.line1,
                            "admin_area_2": customer.selected_shipping_address.city,
                            "country_code": customer.selected_shipping_address.country.code,
                            "postal_code": customer.selected_shipping_address.zip_code,
                        },
                    },
                }
            ],
            "application_context": {
                "shipping_preference": "SET_PROVIDED_ADDRESS",
                "return_url": self.request.build_absolute_uri(reverse("paypal:capture_payment")),
                "cancel_url": self.request.build_absolute_uri(reverse("paypal:payment_cancelled")),
                "user_action": "PAY_NOW",
            },
        }

        response = requests.post(PAYPAL_ORDERS_API, headers=headers, json=order_data)

        if response.status_code == 201:
            order_response = response.json()
            order_id_paypal = order_response["id"]

            # Save payment info to database
            paypal_payment = PayPalPayment.objects.create(
                temp_order_id=temp_order_id,
                payment_id=order_id_paypal,
                amount=order_amount,
                currency="EUR",
            )

            paypal_payment.add_entry(status=PayPalPaymentEntry.PENDING)
            # Find approval URL and redirect
            for link in order_response["links"]:
                if link["rel"] == "approve":
                    return redirect(link["href"])

        # Order creation failed
        logger.error(f"PayPal order creation failed: {response.text}")
        return render(
            self.request,
            "lfs_paypal/payment_error.html",
        )
