# Generated by Django 3.2.12 on 2022-03-17 15:14

from django.db import migrations, models
import localflavor.generic.models


class Migration(migrations.Migration):

    dependencies = [
        ('coop', '0025_draftuser_paid_shares'),
    ]

    operations = [
        migrations.AddField(
            model_name='draftuser',
            name='account_owner',
            field=models.CharField(default='default account owner, just for original migration', max_length=150, verbose_name='Account owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='draftuser',
            name='bic',
            field=localflavor.generic.models.BICField(default='OSDDDE81XXX', max_length=11, verbose_name='BIC'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='draftuser',
            name='iban',
            field=localflavor.generic.models.IBANField(default='DE91100000000123456789', include_countries=None, max_length=34, use_nordea_extensions=False, verbose_name='IBAN'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='draftuser',
            name='paid_membership_fee',
            field=models.BooleanField(default=False, verbose_name='Paid Entrance Fee'),
        ),
        migrations.AlterField(
            model_name='shareowner',
            name='paid_membership_fee',
            field=models.BooleanField(default=True, verbose_name='Paid Entrance Fee'),
        ),
    ]
