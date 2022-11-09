# Generated by Django 3.2.16 on 2023-01-30 18:56

import datetime
import django.contrib.postgres.fields.hstore
from django.db import migrations, models
import django.db.models.deletion
import functools
import localflavor.generic.models
import tapir.accounts.models
import tapir.core.models
import tapir.wirgarten.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("log", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Deliveries",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("delivery_date", models.DateField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="DeliveryExceptionPeriod",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("comment", models.CharField(default="", max_length=128)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="EditFuturePaymentLogEntry",
            fields=[
                (
                    "logentry_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="log.logentry",
                    ),
                ),
                ("old_values", django.contrib.postgres.fields.hstore.HStoreField()),
                ("new_values", django.contrib.postgres.fields.hstore.HStoreField()),
                ("comment", models.CharField(max_length=256)),
            ],
            options={
                "abstract": False,
            },
            bases=("log.logentry",),
        ),
        migrations.CreateModel(
            name="ExportedFile",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=256)),
                (
                    "type",
                    models.CharField(
                        choices=[("csv", "CSV"), ("pdf", "PDF")], max_length=8
                    ),
                ),
                ("file", models.BinaryField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="GrowingPeriod",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="MandateReference",
            fields=[
                (
                    "ref",
                    models.CharField(max_length=35, primary_key=True, serialize=False),
                ),
                ("start_ts", models.DateTimeField()),
                ("end_ts", models.DateTimeField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Member",
            fields=[
                (
                    "tapiruser_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="accounts.tapiruser",
                    ),
                ),
                (
                    "account_owner",
                    models.CharField(
                        max_length=150, null=True, verbose_name="Account owner"
                    ),
                ),
                (
                    "iban",
                    localflavor.generic.models.IBANField(
                        include_countries=None,
                        max_length=34,
                        null=True,
                        use_nordea_extensions=False,
                        verbose_name="IBAN",
                    ),
                ),
                (
                    "bic",
                    localflavor.generic.models.BICField(
                        max_length=11, null=True, verbose_name="BIC"
                    ),
                ),
                (
                    "sepa_consent",
                    models.DateTimeField(null=True, verbose_name="SEPA Consent"),
                ),
                (
                    "withdrawal_consent",
                    models.DateTimeField(
                        null=True, verbose_name="Right of withdrawal consent"
                    ),
                ),
                (
                    "privacy_consent",
                    models.DateTimeField(null=True, verbose_name="Privacy consent"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "abstract": False,
            },
            bases=("accounts.tapiruser",),
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("due_date", models.DateField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8)),
                (
                    "status",
                    models.CharField(
                        choices=[("PAID", "Bezahlt"), ("DUE", "Offen")],
                        default="DUE",
                        max_length=8,
                    ),
                ),
                ("edited", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=functools.partial(datetime.datetime.now, *(), **{})
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PickupLocation",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField(max_length=150, verbose_name="Name")),
                (
                    "coords_lon",
                    models.DecimalField(
                        decimal_places=10,
                        max_digits=12,
                        verbose_name="Coordinates Longitude",
                    ),
                ),
                (
                    "coords_lat",
                    models.DecimalField(
                        decimal_places=10,
                        max_digits=12,
                        verbose_name="Coordinates Latitude",
                    ),
                ),
                (
                    "street",
                    models.CharField(
                        max_length=150, verbose_name="Street and house number"
                    ),
                ),
                (
                    "street_2",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="Extra address line"
                    ),
                ),
                ("postcode", models.CharField(max_length=32, verbose_name="Postcode")),
                ("city", models.CharField(max_length=50, verbose_name="City")),
                (
                    "info",
                    models.CharField(
                        max_length=150,
                        verbose_name="Additional info like opening times",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PickupLocationCapability",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=128)),
                ("deleted", models.BooleanField(default=False)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProductCapacity",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("capacity", models.DecimalField(decimal_places=2, max_digits=20)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProductPrice",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(decimal_places=2, editable=False, max_digits=8),
                ),
                ("valid_from", models.DateField(editable=False)),
            ],
        ),
        migrations.CreateModel(
            name="ProductType",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=128, verbose_name="Produkt Name")),
                (
                    "delivery_cycle",
                    models.CharField(
                        choices=[
                            ("no_delivery", "Keine Lieferung/Abholung"),
                            ("weekly", "1x pro Woche"),
                            ("odd_weeks", "2x pro Monat (ungerade KW)"),
                            ("even_weeks", "2x pro Monat (gerade KW)"),
                            ("monthly", "1x pro Monat"),
                        ],
                        default=("no_delivery", "Keine Lieferung/Abholung"),
                        max_length=16,
                        verbose_name="Lieferzyklus",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TransferCoopSharesLogEntry",
            fields=[
                (
                    "logentry_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="log.logentry",
                    ),
                ),
                ("quantity", models.PositiveSmallIntegerField()),
                (
                    "target_member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.member",
                    ),
                ),
            ],
            bases=("log.logentry",),
        ),
        migrations.CreateModel(
            name="HarvestShareProduct",
            fields=[
                (
                    "product_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wirgarten.product",
                    ),
                ),
                ("min_coop_shares", models.IntegerField()),
            ],
            options={
                "abstract": False,
            },
            bases=("wirgarten.product",),
        ),
        migrations.CreateModel(
            name="ReceivedCoopSharesLogEntry",
            fields=[
                (
                    "transfercoopshareslogentry_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wirgarten.transfercoopshareslogentry",
                    ),
                ),
            ],
            bases=("wirgarten.transfercoopshareslogentry",),
        ),
        migrations.CreateModel(
            name="WaitingListEntry",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=256)),
                ("last_name", models.CharField(max_length=256)),
                ("email", models.CharField(max_length=256)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("HARVEST_SHARES", "Ernteanteile"),
                            ("COOP_SHARES", "Genossenschaftsanteile"),
                        ],
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("privacy_consent", models.DateTimeField()),
                (
                    "member",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.member",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="TaxRate",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("tax_rate", models.FloatField()),
                (
                    "valid_from",
                    models.DateField(
                        default=functools.partial(datetime.date.today, *(), **{})
                    ),
                ),
                ("valid_to", models.DateField(null=True)),
                (
                    "product_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.producttype",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveSmallIntegerField()),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("cancellation_ts", models.DateTimeField(null=True)),
                ("solidarity_price", models.FloatField(default=0.0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "mandate_ref",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.mandatereference",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.member",
                    ),
                ),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.growingperiod",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.product",
                    ),
                ),
            ],
            bases=(models.Model, tapir.wirgarten.models.Payable),
        ),
        migrations.CreateModel(
            name="ShareOwnership",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=functools.partial(
                            tapir.core.models.generate_id, *(), **{}
                        ),
                        max_length=10,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                        verbose_name="ID",
                    ),
                ),
                ("quantity", models.PositiveSmallIntegerField()),
                ("share_price", models.DecimalField(decimal_places=2, max_digits=5)),
                ("entry_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "mandate_ref",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.mandatereference",
                    ),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="wirgarten.member",
                    ),
                ),
            ],
            bases=(models.Model, tapir.wirgarten.models.Payable),
        ),
        migrations.AddConstraint(
            model_name="producttype",
            constraint=models.UniqueConstraint(
                fields=("name",), name="unique_product_Type"
            ),
        ),
        migrations.AddField(
            model_name="productprice",
            name="product",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.product",
            ),
        ),
        migrations.AddField(
            model_name="productcapacity",
            name="period",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.growingperiod",
            ),
        ),
        migrations.AddField(
            model_name="productcapacity",
            name="product_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.producttype",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="type",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.producttype",
            ),
        ),
        migrations.AddField(
            model_name="pickuplocationcapability",
            name="pickup_location",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.pickuplocation",
            ),
        ),
        migrations.AddField(
            model_name="pickuplocationcapability",
            name="product_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.producttype",
            ),
        ),
        migrations.AddConstraint(
            model_name="pickuplocation",
            constraint=models.UniqueConstraint(
                fields=("name", "coords_lat", "coords_lon"), name="unique_location"
            ),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="file",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.exportedfile",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="mandate_ref",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.mandatereference",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="transaction",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.paymenttransaction",
            ),
        ),
        migrations.AddField(
            model_name="member",
            name="pickup_location",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.pickuplocation",
            ),
        ),
        migrations.AddField(
            model_name="mandatereference",
            name="member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING, to="wirgarten.member"
            ),
        ),
        migrations.AddField(
            model_name="deliveryexceptionperiod",
            name="product_type",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.producttype",
            ),
        ),
        migrations.AddField(
            model_name="deliveries",
            name="member",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING, to="wirgarten.member"
            ),
        ),
        migrations.AddField(
            model_name="deliveries",
            name="pickup_location",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="wirgarten.pickuplocation",
            ),
        ),
        migrations.AddIndex(
            model_name="taxrate",
            index=models.Index(
                fields=["product_type"], name="idx_tax_rate_product_type"
            ),
        ),
        migrations.AddConstraint(
            model_name="taxrate",
            constraint=models.UniqueConstraint(
                fields=("product_type", "valid_from"),
                name="unique_tax_rate_product_type_valid_from",
            ),
        ),
        migrations.AddIndex(
            model_name="subscription",
            index=models.Index(
                fields=["period_id", "created_at"],
                name="wirgarten_s_period__f679c5_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="shareownership",
            index=models.Index(fields=["member"], name="idx_shareownership_member"),
        ),
        migrations.AddIndex(
            model_name="productprice",
            index=models.Index(fields=["product"], name="idx_productprice_product"),
        ),
        migrations.AddConstraint(
            model_name="productprice",
            constraint=models.UniqueConstraint(
                fields=("product", "valid_from"), name="unique_product_price_date"
            ),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["mandate_ref"], name="idx_payment_mandate_ref"),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.UniqueConstraint(
                fields=("mandate_ref", "due_date"), name="unique_mandate_ref_date"
            ),
        ),
        migrations.AddIndex(
            model_name="mandatereference",
            index=models.Index(fields=["member"], name="idx_mandatereference_mamber"),
        ),
    ]
