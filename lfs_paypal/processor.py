# python imports
import locale

# lfs imports
from lfs.plugins import PaymentMethodProcessor
from lfs.plugins import PM_ORDER_IMMEDIATELY
from lfs.caching.utils import lfs_get_object_or_404
from lfs.core.models import Shop

# django imports
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

# django paypal imports
from paypal.standard.conf import POSTBACK_ENDPOINT
from paypal.standard.conf import SANDBOX_POSTBACK_ENDPOINT


class PayPalProcessor(PaymentMethodProcessor):
    def process(self):
        if settings.LFS_PAYPAL_REDIRECT:
            return {
                "accepted": True,
                "next_url": self.order.get_pay_link(self.request),
            }
        else:
            return {
                "accepted": True,
                "next_url": reverse("lfs_thank_you"),
            }

    def get_create_order_time(self):
        return PM_ORDER_IMMEDIATELY

    def get_pay_link(self):
        shop = lfs_get_object_or_404(Shop, pk=1)
        current_site = Site.objects.get(id=settings.SITE_ID)
        conv = locale.localeconv()
        default_currency = conv['int_curr_symbol']

        protocol = 'http'
        if self.request and self.request.is_secure():
            protocol = 'https'

        info = {
            "cmd": "_xclick",
            "upload": "1",
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "currency_code": default_currency,
            "notify_url": "{0}://{1}{2}".format(protocol, current_site.domain, reverse('paypal-ipn')),
            "return": "{0}://{1}{2}".format(protocol, current_site.domain, reverse('lfs_thank_you')),
            "first_name": self.order.invoice_address.firstname,
            "last_name": self.order.invoice_address.lastname,
            "address1": self.order.invoice_address.line1,
            "address2": self.order.invoice_address.line2,
            "city": self.order.invoice_address.city,
            "state": self.order.invoice_address.state,
            "zip": self.order.invoice_address.zip_code,
            "no_shipping": "1",
            "custom": self.order.uuid,
            "invoice": self.order.uuid,
            "item_name": shop.shop_owner,
            "amount": "%.2f" % (self.order.price - self.order.tax),
            "tax": "%.2f" % self.order.tax,
        }

        parameters = "&".join(["%s=%s" % (k, v) for (k, v) in info.items()])
        if getattr(settings, 'PAYPAL_TEST', settings.DEBUG):
            url = SANDBOX_POSTBACK_ENDPOINT + "?" + parameters
        else:
            url = POSTBACK_ENDPOINT + "?" + parameters

        return url
