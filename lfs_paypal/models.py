# django imports
from django.db import models

# lfs imports
from lfs.order.models import Order

# django-paypal imports
from paypal.standard.ipn.models import PayPalIPN


class PayPalOrderTransaction(models.Model):
    order = models.ForeignKey(Order, unique=True)
    ipn = models.ManyToManyField(PayPalIPN)

    class Meta:
        app_label = "payment"  # No migration needed after factored out


# See https://bitbucket.org/diefenbach/django-lfs/issue/197/
from paypal.standard.ipn.views import ipn
ipn.csrf_exempt = True

from lfs_paypal.listeners import *
