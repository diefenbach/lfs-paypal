import base64
import logging
from django.conf import settings
import requests

PAYPAL_API_BASE = (
    "https://api-m.sandbox.paypal.com" if settings.PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"
)
PAYPAL_OAUTH_API = f"{PAYPAL_API_BASE}/v1/oauth2/token"
PAYPAL_ORDERS_API = f"{PAYPAL_API_BASE}/v2/checkout/orders"
PAYPAL_ORDER_CAPTURE_API = f"{PAYPAL_API_BASE}/v2/checkout/orders/{{}}/capture"

logger = logging.getLogger("lfs.paypal")


def get_paypal_auth_token():
    """
    Get PayPal OAuth access token
    """
    auth_string = f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}"
    auth_bytes = auth_string.encode("ascii")
    auth_base64 = base64.b64encode(auth_bytes).decode("ascii")

    headers = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {"grant_type": "client_credentials"}

    response = requests.post(PAYPAL_OAUTH_API, headers=headers, data=data)

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        logger.error(f"Failed to get PayPal auth token: {response.text}")
        return None
