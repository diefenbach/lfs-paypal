# django imports
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.file import SessionStore

# lfs imports
from lfs.core.models import Country
from lfs.order.models import Order
from lfs.order.settings import PAID
from lfs.order.settings import PAYMENT_FAILED
from lfs.order.settings import PAYMENT_FLAGGED
from lfs.order.settings import SUBMITTED
from lfs.payment.models import PaymentMethod
from lfs.tests.utils import RequestFactory
from lfs.order.utils import add_order
from lfs.addresses.models import Address
from lfs.payment.models import PaymentMethod
from lfs.shipping.models import ShippingMethod
from lfs.tax.models import Tax
from lfs.customer.models import Customer
from lfs.catalog.models import Product
from lfs.cart.models import Cart
from lfs.cart.models import CartItem

# lfs_paypal imports
from lfs_paypal.models import PayPalOrderTransaction

# django-paypal imports
from paypal.standard.ipn.models import PayPalIPN
from paypal.standard.models import ST_PP_COMPLETED, ST_PP_DENIED


class PayPalPaymentTestCase(TestCase):
    """Tests paypal payments
    """
    fixtures = ['lfs_shop.xml']

    def setUp(self):

        self.uuid = "981242b5-fb0c-4563-bccb-e03033673d2a"
        self.IPN_POST_PARAMS = {
            "protection_eligibility": "Ineligible",
            "last_name": "User",
            "txn_id": "51403485VH153354B",
            "receiver_email": settings.PAYPAL_RECEIVER_EMAIL,
            "payment_status": ST_PP_COMPLETED,
            "payment_gross": "10.00",
            "tax": "0.00",
            "residence_country": "US",
            "invoice": "0004",
            "payer_status": "verified",
            "txn_type": "express_checkout",
            "handling_amount": "0.00",
            "payment_date": "23:04:06 Feb 02, 2009 PST",
            "first_name": "Test",
            "item_name": "Something from the shop",
            "charset": "windows-1252",
            "custom": self.uuid,
            "notify_version": "2.6",
            "transaction_subject": "",
            "test_ipn": "1",
            "item_number": "1",
            "receiver_id": "258DLEHY2BDK6",
            "payer_id": "BN5JZ2V7MLEV4",
            "verify_sign": "An5ns1Kso7MWUdW4ErQKJJJ4qi4-AqdZy6dD.sGO3sDhTf1wAbuO2IZ7",
            "payment_fee": "0.59",
            "mc_fee": "0.59",
            "mc_currency": "USD",
            "shipping": "0.00",
            "payer_email": "bishan_1233269544_per@gmail.com",
            "payment_type": "instant",
            "mc_gross": "10.00",
            "quantity": "1",
        }

        session = SessionStore()
        session.save()

        rf = RequestFactory()
        self.request = rf.get('/')
        self.request.session = session
        self.request.user = AnonymousUser()

        tax = Tax.objects.create(rate=19)

        shipping_method = ShippingMethod.objects.create(
            name="Standard",
            active=True,
            price=1.0,
            tax=tax
        )

        payment_method = PaymentMethod.objects.create(
            name="Direct Debit",
            active=True,
            tax=tax,
        )

        us = Country.objects.get(code="us")
        ie = Country.objects.get(code="ie")

        address1 = Address.objects.create(
            firstname="John",
            lastname="Doe",
            company_name="Doe Ltd.",
            line1="Street 42",
            city="Gotham City",
            zip_code="2342",
            country=ie,
            phone="555-111111",
            email="john@doe.com",
        )

        address2 = Address.objects.create(
            firstname="bill",
            lastname="blah",
            company_name="Doe Ltd.",
            line1="bills house",
            line2="bills street",
            state="bills state",
            city="Smallville",
            zip_code="bills zip code",
            country=us,
            phone="666-111111",
            email="jane@doe.com",
        )

        self.customer = Customer.objects.create(
            session=session.session_key,
            selected_shipping_method=shipping_method,
            selected_payment_method=payment_method,
            selected_shipping_address=address1,
            selected_invoice_address=address2,
        )

        self.p1 = Product.objects.create(
            name="Product 1",
            slug="product-1",
            sku="sku-1",
            price=1.1,
            tax=tax,
            active=True,
        )

        self.p2 = Product.objects.create(
            name="Product 2",
            slug="product-2",
            sku="sku-2",
            price=2.2,
            tax=tax,
            active=True,
        )

        cart = Cart.objects.create(
            session=session.session_key
        )

        item = CartItem.objects.create(
            cart=cart,
            product=self.p1,
            amount=2,
        )

        item = CartItem.objects.create(
            cart=cart,
            product=self.p2,
            amount=3,
        )

    def test_successful_order_transaction_created(self):
        """Tests we have a transaction associated with an order after payment
        """
        def fake_postback(self, test=True):
            """Perform a Fake PayPal IPN Postback request."""
            return 'VERIFIED'

        PayPalIPN._postback = fake_postback

        order = add_order(self.request)
        order.uuid = self.uuid
        self.assertEqual(order.state, SUBMITTED)
        order.save()
        self.assertEqual(len(PayPalIPN.objects.all()), 0)
        self.assertEqual(len(PayPalOrderTransaction.objects.all()), 0)
        post_params = self.IPN_POST_PARAMS
        response = self.client.post(reverse('paypal-ipn'), post_params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(PayPalIPN.objects.all()), 1)
        self.assertEqual(len(PayPalOrderTransaction.objects.all()), 1)
        ipn_obj = PayPalIPN.objects.all()[0]
        self.assertEqual(ipn_obj.flag, False)
        order = Order.objects.all()[0]
        self.assertEqual(order.state, PAID)

    def test_failed_order_transaction_created(self):
        """Tests a failed paypal transaction
        """
        def fake_postback(self, test=True):
            """Perform a Fake PayPal IPN Postback request."""
            return 'INVALID'

        PayPalIPN._postback = fake_postback

        country = Country.objects.get(code="ie")
        order = add_order(self.request)
        order.uuid = self.uuid
        self.assertEqual(order.state, SUBMITTED)
        order.save()
        self.assertEqual(len(PayPalIPN.objects.all()), 0)
        self.assertEqual(len(PayPalOrderTransaction.objects.all()), 0)
        post_params = self.IPN_POST_PARAMS
        payment_status_update = {"payment_status": ST_PP_DENIED}
        post_params.update(payment_status_update)
        response = self.client.post(reverse('paypal-ipn'), post_params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(PayPalIPN.objects.all()), 1)
        self.assertEqual(len(PayPalOrderTransaction.objects.all()), 1)
        ipn_obj = PayPalIPN.objects.all()[0]
        self.assertEqual(ipn_obj.payment_status, ST_PP_DENIED)
        self.assertEqual(ipn_obj.flag, True)
        order = Order.objects.all()[0]
        self.assertEqual(order.state, PAYMENT_FAILED)

    def test_succesful_order_with_flagged_payment_invalid_receiver_email(self):
        """Tests a succesful paypal transaction that is flagged with an invalide receiver email
        """
        def fake_postback(self, test=True):
            """Perform a Fake PayPal IPN Postback request."""
            return 'VERIFIED'

        PayPalIPN._postback = fake_postback
        country = Country.objects.get(code="ie")
        order = add_order(self.request)
        order.uuid = self.uuid
        self.assertEqual(order.state, SUBMITTED)
        order.save()
        self.assertEqual(len(PayPalIPN.objects.all()), 0)
        self.assertEqual(len(PayPalOrderTransaction.objects.all()), 0)
        post_params = self.IPN_POST_PARAMS
        incorrect_receiver_email_update = {"receiver_email": "incorrect_email@someotherbusiness.com"}
        post_params.update(incorrect_receiver_email_update)
        response = self.client.post(reverse('paypal-ipn'), post_params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(PayPalIPN.objects.all()), 1)
        self.assertEqual(len(PayPalOrderTransaction.objects.all()), 1)
        ipn_obj = PayPalIPN.objects.all()[0]
        self.assertEqual(ipn_obj.payment_status, ST_PP_COMPLETED)
        self.assertEqual(ipn_obj.flag, True)
        self.assertEqual(ipn_obj.flag_info, u'Invalid receiver_email. (incorrect_email@someotherbusiness.com)')
        order = Order.objects.all()[0]
        self.assertEqual(order.state, PAYMENT_FLAGGED)

    def test_correct_address_fields_set_on_checkout(self):
        country = Country.objects.get(code="us")
        order = add_order(self.request)
        order.uuid = self.uuid
        self.assertEqual(order.state, SUBMITTED)
        order.payment_method = PaymentMethod.objects.get(pk=3)
        order.save()
        url = order.get_pay_link(None)

        # test unique id
        self.assertEqual(('custom=' + self.uuid) in url, True)

        # test address stuff
        self.assertEqual('first_name=bill' in url, True)
        self.assertEqual('last_name=blah' in url, True)
        self.assertEqual('address1=bills house' in url, True)
        self.assertEqual('address2=bills street' in url, True)
        self.assertEqual('state=bills state' in url, True)
        self.assertEqual('zip=bills zip code' in url, True)
