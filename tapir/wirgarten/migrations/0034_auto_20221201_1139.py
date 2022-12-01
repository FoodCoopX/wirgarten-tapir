# Generated by Django 3.2.16 on 2022-12-01 10:39

from django.db import migrations, models
import localflavor.generic.models


class Migration(migrations.Migration):

    dependencies = [
        ("wirgarten", "0033_transfercoopshareslogentry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="member",
            name="account_owner",
            field=models.CharField(
                max_length=150, null=True, verbose_name="Account owner"
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="bic",
            field=localflavor.generic.models.BICField(
                max_length=11, null=True, verbose_name="BIC"
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="iban",
            field=localflavor.generic.models.IBANField(
                include_countries=None,
                max_length=34,
                null=True,
                use_nordea_extensions=False,
                verbose_name="IBAN",
            ),
        ),
        migrations.AlterField(
            model_name="member",
            name="privacy_consent",
            field=models.DateTimeField(null=True, verbose_name="Privacy consent"),
        ),
        migrations.AlterField(
            model_name="member",
            name="sepa_consent",
            field=models.DateTimeField(null=True, verbose_name="SEPA Consent"),
        ),
        migrations.AlterField(
            model_name="member",
            name="withdrawal_consent",
            field=models.DateTimeField(
                null=True, verbose_name="Right of withdrawal consent"
            ),
        ),
    ]
