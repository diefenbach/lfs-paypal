What is it?
===========

lfs_paypal is the integration of PayPal into `LFS`_. `LFS`_ is an online shop
based on Django.

1.4.1 (2017-03-09)
==================
* Add data migrations for new processor place

1.4 (2017-02-19)
================
* Add Django 1.10 support

1.3 (2015-04-24)
================
* Fixes tests
* Changes order field to OneToOneField
* Removes app_label
* Adds initial migrations

1.2 (2014-06-11)
================
* Removes django-paypal from install_requires

1.1 (2014-06-08)
================
* Adds Django 1.6 suppport

1.0
===
Initial release

.. _`LFS`: http://pypi.python.org/pypi/django-lfs


How it works
############

1. When PayPal is selected as the payment method, the `PayPalProcessor.process()` method is invoked
2. This method obtains an OAuth access token from the PayPal API via `get_paypal_auth_token()`
3. Using this access token, a payment order is created by sending a POST request to `PAYPAL_ORDERS_API`
4. Upon receiving a 201 (Created) HTTP status code, a `PayPalPayment` object is persisted in the database with the PayPal order ID
5. The user is then redirected to the PayPal approval URL to authenticate and authorize the payment
6. After successful authorization, PayPal redirects the user to the `capture_payment` view (specified in the `return_url` parameter during order creation, see 3. above)
7. The `capture_payment` view retrieves the PayPal order ID from the request parameters, fetches the corresponding `PayPalPayment` record, and generates a new OAuth token
8. The payment is then captured by sending a POST request to `PAYPAL_ORDER_CAPTURE_API`
9. If the response status is "COMPLETED", an order is created in the LFS system, associated with the PayPal payment, and the user is redirected to the thank you page
10. After successful payment capture, PayPal sends a webhook event to the URL configured in the PayPal Developer Dashboard.
