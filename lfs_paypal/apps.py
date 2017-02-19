from django.apps import AppConfig


class LfsPayPalAppConfig(AppConfig):
    name = 'lfs_paypal'

    def ready(self):
        import listeners

        # See https://bitbucket.org/diefenbach/django-lfs/issue/197/
        from paypal.standard.ipn.views import ipn
        ipn.csrf_exempt = True
