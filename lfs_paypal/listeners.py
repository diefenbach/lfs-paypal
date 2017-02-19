# python imports
import logging

# django imports
from django.conf import settings

# lfs imports
import lfs.core.signals
from lfs.order.models import Order
from lfs.order.settings import PAID
from lfs.order.settings import PAYMENT_FAILED
from lfs.order.settings import PAYMENT_FLAGGED
from lfs.mail import utils as mail_utils

# lfs-paypal imports
from lfs_paypal.models import PayPalOrderTransaction

# django-paypal imports
from paypal.standard.ipn.signals import valid_ipn_received, invalid_ipn_received
from paypal.standard.models import ST_PP_COMPLETED

# load logger
logger = logging.getLogger(__name__)


def mark_payment(pp_obj, order_state=PAID):
    order = None
    try:
        logger.info("PayPal: getting order for uuid %s" % pp_obj.custom)
        order_uuid = pp_obj.custom
        order = Order.objects.get(uuid=order_uuid)
        if order is not None:
            order_old_state = order.state
            order.state = order_state
            order.save()
            if order_old_state != PAID and order_state == PAID:
                lfs.core.signals.order_paid.send(sender=order)
                if getattr(settings, 'LFS_SEND_ORDER_MAIL_ON_PAYMENT', False):
                    mail_utils.send_order_received_mail(None, order)
    except Order.DoesNotExist, e:
        logger.error("PayPal: %s" % e)
    return order


def successful_payment(sender, **kwargs):
    logger.info("PayPal: successful ipn payment")
    ipn_obj = sender
    order = mark_payment(ipn_obj, PAID)
    if order is not None:
        transaction, created = PayPalOrderTransaction.objects.get_or_create(order=order)
        transaction.ipn.add(ipn_obj)
        transaction.save()
    else:
        logger.warning("PayPal: successful ipn payment, no order found for uuid %s" % ipn_obj.custom)


def unsuccessful_payment(sender, **kwargs):
    logger.info("PayPal: unsuccessful ipn payment")
    ipn_obj = sender
    if ipn_obj:
        order = None
        if ipn_obj.payment_status == ST_PP_COMPLETED:
            logger.info("PayPal: payment flaged")
            order = mark_payment(ipn_obj, PAYMENT_FLAGGED)
        else:
            logger.info("PayPal: payment failed")
            order = mark_payment(ipn_obj, PAYMENT_FAILED)
        if order is not None:
            transaction, created = PayPalOrderTransaction.objects.get_or_create(order=order)
            transaction.ipn.add(ipn_obj)
            transaction.save()
        else:
            logger.warning("PayPal: unsuccessful ipn payment, no order found for uuid %s" % ipn_obj.custom)
    else:
        logger.warning("PayPal: unsuccessful ipn payment signal with no ipn object")


def successful_pdt(sender, **kwargs):
    logger.info("PayPal: successful pdt payment")
    pdt_obj = sender
    mark_payment(pdt_obj, True)


def unsuccesful_pdt(sender, **kwargs):
    logger.info("PayPal: unsuccessful pdt payment")
    pdt_obj = sender
    mark_payment(pdt_obj, False)

valid_ipn_received.connect(successful_payment, dispatch_uid="Order.ipn_successful")
invalid_ipn_received.connect(unsuccessful_payment, dispatch_uid="Order.ipn_unsuccessful")
