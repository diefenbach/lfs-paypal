# django imports
from django.db import models

# lfs imports
from lfs.order.models import Order

# django-paypal imports
from paypal.standard.ipn.models import PayPalIPN


class PayPalOrderTransaction(models.Model):
    order = models.OneToOneField(Order)
    ipn = models.ManyToManyField(PayPalIPN)
