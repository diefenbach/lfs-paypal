# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ipn', '__first__'),
        ('order', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PayPalOrderTransaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ipn', models.ManyToManyField(to='ipn.PayPalIPN')),
                ('order', models.OneToOneField(to='order.Order')),
            ],
        ),
    ]
