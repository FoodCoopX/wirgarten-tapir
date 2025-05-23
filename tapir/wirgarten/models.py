import datetime
from functools import partial

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import (
    F,
    Index,
    JSONField,
    OuterRef,
    Subquery,
    Sum,
    UniqueConstraint,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from localflavor.generic.models import IBANField

from tapir.accounts.models import TapirUser, KeycloakUserManager
from tapir.configuration.parameter import get_parameter_value
from tapir.core.models import TapirModel
from tapir.log.models import LogEntry, UpdateModelLogEntry
from tapir.wirgarten.constants import NO_DELIVERY, DeliveryCycle
from tapir.wirgarten.parameters import OPTIONS_WEEKDAYS, Parameter
from tapir.wirgarten.utils import format_currency, format_date, get_today


class PickupLocation(TapirModel):
    """
    This is a place where a Member can pick up his/her products.
    """

    name = models.TextField(_("Name"), max_length=150)
    coords_lon = models.DecimalField(
        _("Coordinates Longitude"), decimal_places=10, max_digits=12
    )
    coords_lat = models.DecimalField(
        _("Coordinates Latitude"), decimal_places=10, max_digits=12
    )
    street = models.CharField(_("Street and house number"), max_length=150)
    street_2 = models.CharField(_("Extra address line"), max_length=150, blank=True)
    postcode = models.CharField(_("Postcode"), max_length=32)
    city = models.CharField(_("City"), max_length=50)
    info = models.CharField(_("Additional info"), max_length=1024, blank=True)
    access_code = models.CharField(_("Access Code"), max_length=20, blank=True)
    messenger_group_link = models.CharField(
        _("Messenger Group Link"), max_length=150, blank=True
    )
    contact_name = models.CharField(
        _("Name of the contact"), max_length=150, blank=True
    )
    photo_link = models.CharField(_("Photo Link"), max_length=512, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name", "coords_lat", "coords_lon"],
                name="unique_location",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def opening_times_html(self):
        result = "<table>"
        last_day = None
        for ot in PickupLocationOpeningTime.objects.filter(
            pickup_location_id=self.id
        ).order_by("day_of_week"):
            open_time = ot.open_time.strftime("%H:%M")
            close_time = ot.close_time.strftime("%H:%M")

            result += f"""<tr>
                <th style='font-weight: semibold'>{OPTIONS_WEEKDAYS[ot.day_of_week][1][0:2] if ot.day_of_week != last_day else ""}</td>
                <td style='padding-left:2em; text-align:right'>{open_time}-{close_time}</td>
                </tr>"""
            last_day = ot.day_of_week
        return result + "</table>"

    @property
    def delivery_date_offset(self):
        opening_times = PickupLocationOpeningTime.objects.filter(
            pickup_location_id=self.id
        ).order_by("day_of_week")
        delivery_day = get_parameter_value(Parameter.DELIVERY_DAY)
        smallest_offset = None
        for ot in opening_times:
            offset = ot.day_of_week - delivery_day
            if ot.day_of_week < delivery_day:
                offset += 7
            smallest_offset = (
                min(smallest_offset, offset) if smallest_offset is not None else offset
            )

        return smallest_offset if smallest_offset is not None else 0


class PickupLocationOpeningTime(TapirModel):
    pickup_location = models.ForeignKey(
        "PickupLocation",
        on_delete=models.CASCADE,
        related_name="opening_times",
    )
    day_of_week = models.PositiveSmallIntegerField(
        choices=OPTIONS_WEEKDAYS,
    )
    open_time = models.TimeField()
    close_time = models.TimeField()


class GrowingPeriod(TapirModel):
    """
    The growing period for the WirGarten site. Usually the growing period starts on 1st of March, and ends in the end of next February.
    """

    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{format_date(self.start_date)} - {format_date(self.end_date)}"


class ProductType(TapirModel):
    """
    This is the type of the product, e.g. harvest share, chicken share, ...
    """

    name = models.CharField(max_length=128, null=False, verbose_name=_("Produkt Name"))
    delivery_cycle = models.CharField(
        max_length=16,
        choices=DeliveryCycle,
        null=False,
        default=NO_DELIVERY[0],
        verbose_name=_("Lieferzyklus"),
    )
    contract_link = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        verbose_name=_("Link zu den Vertragsgrundsätzen"),
    )
    icon_link = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        verbose_name=_("Link zum Icon"),
    )
    single_subscription_only = models.BooleanField(
        default=False, verbose_name=_("Nur Einzelabonnement erlaubt")
    )

    def base_price(self, reference_date=None):
        if reference_date is None:
            reference_date = get_today()

        product = self.product_set.get(base=True)
        price_queryset = product.productprice_set.filter(
            valid_from__lte=reference_date
        ).order_by("-valid_from")

        price = price_queryset.first()
        if price is None:
            price = product.productprice_set.order_by("-valid_from").first()

        return price.price if price else None

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["name"],
                name="unique_product_Type",
            )
        ]

    def __str__(self):
        return f"<ProductType: {self.name}>"


class PickupLocationCapability(TapirModel):
    """
    The availability of a product at a certain pickup location.
    """

    product_type = models.ForeignKey(
        ProductType, null=False, on_delete=models.DO_NOTHING
    )
    max_capacity = models.PositiveSmallIntegerField(
        null=True
    )  # This is the capacity in NUMBER of M equivalent share, not the capacity in COST of M equivalent share.
    pickup_location = models.ForeignKey(
        PickupLocation, null=False, on_delete=models.DO_NOTHING
    )

    def __str__(self):
        return f"Location:{self.pickup_location.name} ProductType:{self.product_type.name} Capacity:{self.max_capacity}"


class DeliveryExceptionPeriod(TapirModel):
    """
    Defines a period in which no delivery of a certain product takes place.
    """

    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    product_type = models.ForeignKey(
        ProductType, null=True, on_delete=models.DO_NOTHING
    )
    comment = models.CharField(max_length=128, null=False, default="")


class ProductCapacity(TapirModel):
    """
    This is used to configure how much of a ProductType can be sold in a growing period.
    """

    period = models.ForeignKey(GrowingPeriod, null=False, on_delete=models.DO_NOTHING)
    product_type = models.ForeignKey(
        ProductType, null=False, on_delete=models.DO_NOTHING
    )
    capacity = models.DecimalField(decimal_places=4, max_digits=20, null=False)

    indexes = [Index(fields=["period"], name="idx_productcapacity_period")]


class MemberQuerySet(models.QuerySet):
    def with_active_subscription(self, reference_date: datetime.date | None = None):
        from tapir.wirgarten.service.products import get_active_subscriptions

        return self.filter(
            id__in=get_active_subscriptions(reference_date)
            .values_list("member", flat=True)
            .distinct()
        )

    def without_active_subscription(self, reference_date: datetime.date | None = None):
        return self.exclude(
            id__in=Member.objects.with_active_subscription(reference_date)
        ).distinct()

    def with_shares(self, reference_date: datetime.date | None = None):
        if reference_date is None:
            reference_date = get_today()

        members_with_nb_shares_annotation = Member.objects.annotate(
            total_shares=models.Sum(
                models.Case(
                    models.When(
                        coopsharetransaction__valid_at__lte=reference_date,
                        then=models.F("coopsharetransaction__quantity"),
                    ),
                    default=0,
                    output_field=models.IntegerField(),
                )
            )
        )

        return self.filter(
            id__in=members_with_nb_shares_annotation.filter(total_shares__gte=1)
        )

    def without_shares(self, reference_date: datetime.date | None = None):
        return self.exclude(
            id__in=Member.objects.with_shares(reference_date)
        ).distinct()


class TapirUserManager(models.Manager.from_queryset(MemberQuerySet)):
    @staticmethod
    def normalize_email(email: str) -> str:
        return KeycloakUserManager.normalize_email(email)


class Member(TapirUser):
    """
    A member of WirGarten. Usually a member has coop shares and optionally other subscriptions.
    """

    objects = TapirUserManager()

    account_owner = models.CharField(_("Account owner"), max_length=150, null=True)
    iban = IBANField(_("IBAN"), null=True)
    sepa_consent = models.DateTimeField(_("SEPA Consent"), null=True)
    withdrawal_consent = models.DateTimeField(
        _("Right of withdrawal consent"), null=True
    )
    privacy_consent = models.DateTimeField(_("Privacy consent"), null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    member_no = models.IntegerField(_("Mitgliedsnummer"), unique=True, null=True)
    is_student = models.BooleanField(_("Student*in"), default=False)

    @property
    def pickup_location(self):
        return self.get_pickup_location()

    def get_pickup_location(self, reference_date=None):
        if reference_date is None:
            reference_date = get_today()

        all_locations = self.memberpickuplocation_set.all()

        # If there's only one pickup_location, return it regardless of its valid_from date
        if all_locations.count() == 1:
            return all_locations.first().pickup_location
        else:
            found = (
                self.memberpickuplocation_set.filter(valid_from__lte=reference_date)
                .order_by("-valid_from")
                .values("pickup_location")
            )
            return (
                PickupLocation.objects.get(id=found[0]["pickup_location"])
                if found.exists()
                else None
            )

    @classmethod
    def generate_member_no(cls):
        max_member_no = cls.objects.aggregate(models.Max("member_no"))["member_no__max"]
        return (max_member_no or 0) + 1

    @transaction.atomic
    def save(self, *args, **kwargs):
        if "bypass_keycloak" not in kwargs:
            kwargs["bypass_keycloak"] = get_parameter_value(
                Parameter.MEMBER_BYPASS_KEYCLOAK
            )

        super().save(*args, **kwargs)

    def is_in_coop_trial(self):
        entry_date = self.coop_entry_date
        return entry_date is not None and entry_date > get_today()

    @property
    def has_trial_contracts(self):
        from tapir.wirgarten.service.products import get_future_subscriptions

        subs = get_future_subscriptions().filter(member_id=self.id)
        today = get_today()
        for sub in subs:
            if today < sub.trial_end_date and sub.cancellation_ts is None:
                return True
        return False

    def coop_shares_total_value(self):
        today = get_today()
        return (
            self.coopsharetransaction_set.filter(valid_at__lte=today).aggregate(
                total_value=Sum(F("quantity") * F("share_price"))
            )["total_value"]
            or 0.0
        )

    @property
    def coop_shares_quantity(self):
        today = get_today()
        return (
            self.coopsharetransaction_set.filter(valid_at__lte=today).aggregate(
                quantity=Sum(F("quantity"))
            )["quantity"]
            or 0
        )

    def monthly_payment(self):
        from tapir.wirgarten.service.products import get_active_subscriptions

        today = get_today()
        return (
            get_active_subscriptions()
            .filter(member_id=self.id)
            .annotate(
                product_price=Subquery(
                    ProductPrice.objects.filter(
                        product_id=OuterRef("product_id"), valid_from__lte=today
                    )
                    .order_by("-valid_from")
                    .values("price")[:1],
                    output_field=models.FloatField(),
                ),
            )
            .aggregate(
                total_value=Sum(
                    F("product_price") * F("quantity") * (1 + F("solidarity_price"))
                )
            )["total_value"]
        )

    @property
    def coop_entry_date(self):
        try:
            earliest_coopsharetransaction = self.coopsharetransaction_set.filter(
                transaction_type__in=[
                    CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                    CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
                ]
            ).earliest("valid_at")
            return (
                earliest_coopsharetransaction.valid_at
                if earliest_coopsharetransaction
                else None
            )
        except CoopShareTransaction.DoesNotExist:
            return None

    @property
    def base_subscriptions_text(self):
        """
        Returns a human readable string stating which base products the member has subscribed,
        sorted by their price in ascending order.

        Examples:
        - “einen M-Ernteanteil”
        - “2 M-Ernteanteile”
        - “einen S-Ernteanteil + 2 M-Ernteanteile”
        - “einen S-Ernteanteil + M-Ernteanteil + L-Ernteanteil”
        """

        from collections import Counter
        from tapir.wirgarten.service.products import (
            get_product_price,
            get_active_subscriptions,
        )

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)

        # Get all active base subscriptions for the member
        subscriptions = get_active_subscriptions().filter(
            member_id=self.id, product__type__id=base_product_type_id
        )

        if not subscriptions:
            return ""

        # Count the quantity of each base product subscribed
        product_counts = Counter()
        for sub in subscriptions:
            product_counts[sub.product] += sub.quantity

        # Create a list of tuples (product, quantity, price) and sort by price
        product_info = []
        today = get_today()
        for product, quantity in product_counts.items():
            price = get_product_price(product, today).price
            product_info.append(
                (
                    f"{product.name}-{product.type.name[:-1] if quantity == 1 else product.type.name}",
                    quantity,
                    price,
                )
            )

        # Sort products by price (ascending)
        product_info.sort(key=lambda x: x[2])

        # Create the human-readable text
        base_subscription_texts = []
        for product_name, quantity, _ in product_info:
            if quantity == 1:
                base_subscription_texts.append(f"einen {product_name}")
            else:
                base_subscription_texts.append(f"{quantity} {product_name}")

        return " + ".join(base_subscription_texts)

    def __str__(self):
        return f"[{self.member_no if self.member_no else '---'}] {self.first_name} {self.last_name} ({self.email})"


class MemberPickupLocation(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    pickup_location = models.ForeignKey(PickupLocation, on_delete=models.DO_NOTHING)
    valid_from = models.DateField()

    class Meta:
        unique_together = (
            "member",
            "valid_from",
        )


class Product(TapirModel):
    """
    This is a specific product variation, like "Harvest Shares - M".
    """

    type = models.ForeignKey(
        ProductType, on_delete=models.DO_NOTHING, editable=False, null=False
    )
    name = models.CharField(max_length=128, editable=True, null=False)
    deleted = models.BooleanField(default=False)
    base = models.BooleanField(default=False, null=True)

    def clean(self):
        # Check if there is exactly one base product per ProductType
        base_products = Product.objects.filter(type=self.type, base=True)

        if self.base:
            if base_products.exists() and not base_products.filter(id=self.id).exists():
                raise ValidationError(
                    "There can be only one base product per ProductType."
                )
        else:
            if not base_products.exists() or base_products.filter(id=self.id).exists():
                raise ValidationError(
                    "There must be exactly one base product per ProductType."
                )

    def save(self, *args, **kwargs):
        self.clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    class Meta:
        indexes = [Index(fields=["type"], name="idx_product_type")]

    def __str__(self):
        return f"{self.name} ({self.type.name})"


class ProductPrice(TapirModel):
    """
    Price for a product. A product is only valid to use if it has a price.
    """

    product = models.ForeignKey(
        Product, on_delete=models.DO_NOTHING, editable=False, null=False
    )
    price = models.DecimalField(
        decimal_places=2, max_digits=8, editable=False, null=False
    )
    size = models.DecimalField(
        decimal_places=4, max_digits=8, editable=False, null=False
    )
    valid_from = models.DateField(null=False, editable=False)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["product", "valid_from"],
                name="unique_product_price_date",
            )
        ]
        indexes = [
            Index(fields=["product"], name="idx_productprice_product"),
            Index(fields=["-valid_from"], name="idx_productprice_valid_from"),
        ]

    def __str__(self):
        return f"{self.product} - {self.price} - {self.size} - {self.valid_from} -{self.id}"


class HarvestShareProduct(Product):
    """
    Product variations of harvest share products.
    """

    min_coop_shares = models.IntegerField()


class MandateReference(models.Model):
    """
    The mandate reference is generated for the SEPA payments.
    """

    ref = models.CharField(primary_key=True, null=False, blank=False, max_length=35)
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    start_ts = models.DateTimeField(null=False)
    end_ts = models.DateTimeField(null=True)

    class Meta:
        indexes = [Index(fields=["member"], name="idx_mandatereference_mamber")]


class Payable:
    """
    Interface to define how to calculate the total amount.
    """

    def total_price(self):
        raise NotImplementedError(
            "You need to implement total_price() if you use the PayableMixin!"
        )


class AdminConfirmableMixin(models.Model):
    """
    Mixin to add an admin confirmation field to a model.
    """

    admin_confirmed = models.DateTimeField(null=True)

    class Meta:
        abstract = True


class Subscription(TapirModel, Payable, AdminConfirmableMixin):
    """
    A subscription for a member.
    """

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, null=False)
    period = models.ForeignKey(GrowingPeriod, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField(null=False)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    cancellation_ts = models.DateTimeField(null=True)
    solidarity_price = models.FloatField(default=0.0)
    solidarity_price_absolute = models.DecimalField(
        decimal_places=2, max_digits=12, null=True
    )
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=False
    )
    created_at = models.DateTimeField(default=partial(timezone.now), null=False)
    consent_ts = models.DateTimeField(
        null=True
    )  # TODO this should probably be null=False
    withdrawal_consent_ts = models.DateTimeField(null=True)
    trial_disabled = models.BooleanField(default=False)
    trial_end_date_override = models.DateField(null=True)
    price_override = models.DecimalField(
        decimal_places=2, max_digits=8, null=True, blank=True
    )

    @property
    def trial_end_date(self):
        if self.trial_disabled:
            return get_today() - relativedelta(days=1)

        if self.trial_end_date_override is not None:
            return self.trial_end_date_override

        return self.start_date + relativedelta(months=1, day=1, days=-1)

    @trial_end_date.setter
    def trial_end_date(self, value):
        self.trial_end_date_override = value

    class Meta:
        indexes = [
            models.Index(fields=["period_id"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["member"]),
        ]

    def total_price(self, reference_date=None):
        if self.price_override is not None:
            return float(self.price_override)

        if reference_date is None:
            reference_date = max(self.start_date, get_today())

        if not hasattr(self, "_total_price"):
            from tapir.wirgarten.service.products import get_product_price

            price = get_product_price(self.product, reference_date).price

            if self.solidarity_price_absolute is not None:
                self._total_price = round(
                    float(self.quantity) * float(price)
                    + float(self.solidarity_price_absolute),
                    2,
                )
            else:
                self._total_price = round(
                    float(self.quantity)
                    * float(price)
                    * float(1 + self.solidarity_price),
                    2,
                )
        return self._total_price

    @property
    def total_price_without_soli(self):
        today = get_today()
        if not hasattr(self, "_total_price_without_soli"):
            product_prices = ProductPrice.objects.filter(
                product_id=self.product_id, valid_from__lte=today
            ).order_by("product_id", "-valid_from")
            self._total_price_without_soli = (
                next(
                    (
                        product_price.price
                        for product_price in product_prices
                        if product_price.product_id == self.product_id
                    ),
                    0.0,
                )
                * self.quantity
            )

        return self._total_price_without_soli

    def get_used_capacity(self):
        today = get_today()
        if not hasattr(self, "_used_capacity"):
            from tapir.wirgarten.service.products import get_product_price

            current_product_price = get_product_price(
                product=self.product, reference_date=today
            )

            self._used_capacity = current_product_price.size * self.quantity

        return self._used_capacity

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError({"start_date": "Start date must be before end date."})

        if (
            self.solidarity_price_absolute is not None
            and self.solidarity_price_absolute < 0
        ):
            raise ValidationError(
                {"solidarity_price_absolute": "Solidarity price must be positive."}
            )

        if self.solidarity_price_absolute is not None and self.solidarity_price != 0.0:
            raise ValidationError(
                {
                    "solidarity_price": "Solidarity price must be 0 if absolute solidarity price is set."
                }
            )

    def __str__(self):
        return (
            f"{self.quantity} × {self.product.name} {self.product.type.name}; "
            f"from {self.start_date} to {self.end_date}"
        )

    def long_str(self):
        if self.solidarity_price_absolute is not None:
            soliprice = f"\n\t(Solidaraufschlag: {self.solidarity_price_absolute} €)"
        elif self.solidarity_price is not None:
            soliprice = (
                f"\n\t(Solidaraufschlag: {float(self.solidarity_price) * 100.0} %)"
            )
        else:
            soliprice = ""

        return (
            self.__str__()
            + f" ({format_date(self.start_date)} - {format_date(self.end_date)})"
            + soliprice
        )


class ExportedFile(TapirModel):
    """
    An exported file (blob in DB).
    """

    class FileType(models.TextChoices):
        CSV = "csv", _("CSV")
        PDF = "pdf", _("PDF")

    name = models.CharField(max_length=256, null=False)
    type = models.CharField(max_length=8, choices=FileType.choices, null=False)
    file = models.BinaryField(null=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False)


class PaymentTransaction(TapirModel):
    """
    A payment transaction. This is usually created once a month by a task, when the payments are due.
    The relevant payments must reference the transaction in the same step.
    """

    created_at = models.DateTimeField(null=False, default=partial(timezone.now))
    file = models.ForeignKey(ExportedFile, on_delete=models.DO_NOTHING, null=False)
    type = models.CharField(max_length=32, null=True)


class Payment(TapirModel):
    """
    A payment. Usually payments are created in DB when they are due, but also when the admin edits a future payment.
    If the sepa_payments reference is set, the payment cannot be changed anymore, because it was exported for the bank already.
    """

    class PaymentStatus(models.TextChoices):
        PAID = "PAID", _("Bezahlt")
        DUE = "DUE", _("Offen")

    due_date = models.DateField(null=False)
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=False
    )
    amount = models.DecimalField(decimal_places=2, max_digits=8, null=False)
    status = models.CharField(
        max_length=8,
        choices=PaymentStatus.choices,
        null=False,
        default=PaymentStatus.DUE,
    )
    edited = models.BooleanField(default=False, null=False)
    transaction = models.ForeignKey(
        PaymentTransaction, on_delete=models.DO_NOTHING, null=True
    )
    type = models.CharField(max_length=32, null=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["mandate_ref", "due_date", "type"],
                name="unique_mandate_ref_date",
            )
        ]
        indexes = [
            Index(fields=["mandate_ref"], name="idx_payment_mandate_ref"),
            Index(fields=["due_date"], name="idx_payment_due_date"),
        ]

    def __str__(self):
        return f"[{self.due_date}] {format_currency(self.amount)} €, edited={self.edited}, transaction={self.transaction}, type={self.type}, {self.mandate_ref.ref}"


class CoopShareTransaction(TapirModel, Payable, AdminConfirmableMixin):
    """
    The CoopShareTransaction model represents a transaction related to cooperative shares. It provides a way to track various types of transactions that can occur within a cooperative, such as purchasing, canceling, transferring out, and transferring in shares.

    Attributes:
        transaction_type (CharField): The type of transaction (PURCHASE, CANCELLATION, TRANSFER_OUT, TRANSFER_IN).
        member (ForeignKey): The member associated with the transaction.
        quantity (SmallIntegerField): The quantity of shares involved in the transaction. Must be positive for PURCHASE and TRANSFER_IN, and negative for CANCELLATION and TRANSFER_OUT.
        share_price (DecimalField): The price of a single share at the time of the transaction.
        timestamp (DateTimeField): The date and time when the transaction was created.
        valid_at (DateField): The date when the transaction becomes valid.
        mandate_ref (ForeignKey): The reference to a mandate associated with the transaction (optional).
        transfer_member (ForeignKey): The member associated with the share transfer (TRANSFER_OUT, TRANSFER_IN transactions only).
    """

    class CoopShareTransactionType(models.TextChoices):
        PURCHASE = "purchase", _("Zeichnung von Anteilen")
        CANCELLATION = "cancellation", _("Kündigung von Anteilen")
        TRANSFER_OUT = "transfer_out", _("Abgabe von Anteilen")
        TRANSFER_IN = "transfer_in", _("Empfang von Anteilen")

    transaction_type = models.CharField(
        max_length=30, choices=CoopShareTransactionType.choices, null=False
    )
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    quantity = models.SmallIntegerField(null=False)
    share_price = models.DecimalField(max_digits=5, decimal_places=2, null=False)
    timestamp = models.DateTimeField(default=partial(timezone.now), null=False)
    valid_at = models.DateField(null=False)
    mandate_ref = models.ForeignKey(
        MandateReference, on_delete=models.DO_NOTHING, null=True
    )
    transfer_member = models.ForeignKey(
        Member, on_delete=models.DO_NOTHING, null=True, related_name="transfer_member"
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.DO_NOTHING, null=True, related_name="payment"
    )

    @property
    def total_price(self):
        return self.quantity * self.share_price

    def clean(self):
        # Call the parent class's clean method to ensure any default validation is performed.
        super().clean()

        # Validate the quantity based on the transaction_type.
        if (
            self.transaction_type
            in [
                self.CoopShareTransactionType.CANCELLATION,
                self.CoopShareTransactionType.TRANSFER_OUT,
            ]
            and self.quantity >= 0
        ):
            raise ValidationError(
                {
                    "quantity": _(
                        "For CANCELLATION and TRANSFER_OUT, the quantity must be negative."
                    )
                }
            )
        elif (
            self.transaction_type
            in [
                self.CoopShareTransactionType.PURCHASE,
                self.CoopShareTransactionType.TRANSFER_IN,
            ]
            and self.quantity <= 0
        ):
            raise ValidationError(
                {
                    "quantity": _(
                        "For PURCHASE and TRANSFER_IN, the quantity must be positive."
                    )
                }
            )

        if (
            self.transaction_type
            in [
                self.CoopShareTransactionType.TRANSFER_IN,
                self.CoopShareTransactionType.TRANSFER_OUT,
            ]
            and self.transfer_member is None
        ):
            raise ValidationError(
                {
                    "transfer_member": _(
                        "For TRANSFER_OUT and TRANSFER_IN, the transfer_member must be set."
                    )
                }
            )

    def save(self, *args, **kwargs):
        # Call the clean method to validate the model instance before saving.
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        prefix = f"[{format_date(self.timestamp)}] {abs(self.quantity)} Genossenschaftsanteile"
        if self.transaction_type == self.CoopShareTransactionType.PURCHASE:
            suffix = "gezeichnet"
        elif self.transaction_type == self.CoopShareTransactionType.CANCELLATION:
            suffix = "gekündigt"
        elif self.transaction_type == self.CoopShareTransactionType.TRANSFER_OUT:
            suffix = f"übertragen an {self.transfer_member}"
        elif self.transaction_type == self.CoopShareTransactionType.TRANSFER_IN:
            suffix = f"empfangen von {self.transfer_member}"
        else:
            suffix = f"Unknown transaction type ({self.transaction_type})"
        return f"{prefix} {suffix} - Valid at:{self.valid_at} - Member:{self.member.id}"


class Deliveries(TapirModel):
    """
    History of deliveries.
    """

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    delivery_date = models.DateField(null=False)
    pickup_location = models.ForeignKey(
        PickupLocation, on_delete=models.DO_NOTHING, null=False
    )


class TaxRate(TapirModel):
    """
    Tax rates per product type. This has no influence on the gross price, it is only used to calculate the tax amount from the gross price.
    If valid_to == NULL, the tax rate is used as a fallback. If valid_to != NULL and it is now valid, this one is used.
    """

    product_type = models.ForeignKey(
        ProductType, on_delete=models.DO_NOTHING, null=False
    )
    tax_rate = models.FloatField(null=False)
    valid_from = models.DateField(null=False, default=partial(datetime.date.today))
    valid_to = models.DateField(null=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["product_type", "valid_from"],
                name="unique_tax_rate_product_type_valid_from",
            )
        ]
        indexes = [Index(fields=["product_type"], name="idx_tax_rate_product_type")]


class EditFuturePaymentLogEntry(UpdateModelLogEntry):
    """
    This log entry is created whenever an admin manually changes the amount of a future payment.
    """

    template_name = "wirgarten/log/edit_future_payment_log_entry.html"

    comment = models.CharField(null=False, blank=False, max_length=256)

    def populate(
        self,
        old_frozen=None,
        new_frozen=None,
        old_model=None,
        new_model=None,
        comment=None,
        **kwargs,
    ):
        super(EditFuturePaymentLogEntry, self).populate(
            old_frozen=old_frozen,
            new_frozen=new_frozen,
            old_model=old_model,
            new_model=new_model,
        )
        self.comment = comment
        return self


class TransferCoopSharesLogEntry(LogEntry):
    """
    Documents the transfer of coop shares from 'user' to 'target_member'.
    """

    template_name = "wirgarten/log/transfer_coop_shares_log_entry.html"

    target_member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=False)
    quantity = models.PositiveSmallIntegerField()

    def populate(
        self, actor=None, user=None, target_member=None, quantity=None, **kwargs
    ):
        super(TransferCoopSharesLogEntry, self).populate(actor=actor, user=user)
        self.target_member = target_member
        self.quantity = quantity
        return self


class ReceivedCoopSharesLogEntry(TransferCoopSharesLogEntry):
    """
    Same as TransferCoopSharesLogEntry, but user and target_member are switched. Then you have a log entry for both sides of the transaction.
    """

    template_name = "wirgarten/log/received_coop_shares_log_entry.html"


class SubscriptionChangeLogEntry(LogEntry):
    """
    This log entry is created whenever a Subscription is created or cancelled.
    """

    template_name = "wirgarten/log/subscription_log_entry.html"

    class SubscriptionChangeLogEntryType(models.TextChoices):
        ADDED = "ADDED", _("Vertragsabschluss")
        CANCELLED = "CANCELLED", _("Kündigung")
        RENEWED = "RENEWED", _("Verlängerung")
        NOT_RENEWED = "NOT_RENEWED", _("Keine Verlängerung")

    change_type = models.CharField(
        choices=SubscriptionChangeLogEntryType.choices, null=False, max_length=32
    )
    subscriptions = models.CharField(null=False, blank=False, max_length=1024)

    def populate(
        self,
        actor: TapirUser,
        user: Member,
        change_type: SubscriptionChangeLogEntryType,
        subscriptions: [Subscription],
        **kwargs,
    ):
        super().populate(actor=actor, user=user, **kwargs)
        self.change_type = change_type
        self.subscriptions = ", ".join(
            list(
                map(
                    lambda x: f"{x.quantity} × {x.product.name} ({format_date(x.start_date)} - {format_date(x.end_date)})",
                    subscriptions,
                )
            )
        )

        return self

    def get_context_data(self):
        context = super().get_context_data()
        context["subscriptions"] = self.subscriptions.split(", ")
        context["change_type"] = self.change_type
        return context


class WaitingListEntry(TapirModel):
    class WaitingListType(models.TextChoices):
        HARVEST_SHARES = "HARVEST_SHARES", _("Ernteanteile")
        COOP_SHARES = "COOP_SHARES", _("Genossenschaftsanteile")

    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=True)
    first_name = models.CharField(null=False, blank=False, max_length=256)
    last_name = models.CharField(null=False, blank=False, max_length=256)
    email = models.CharField(null=False, blank=False, max_length=256)
    type = models.CharField(choices=WaitingListType.choices, null=False, max_length=32)
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    privacy_consent = models.DateTimeField(null=False)


class QuestionaireTrafficSourceOption(TapirModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class QuestionaireTrafficSourceResponse(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=True)
    sources = models.ManyToManyField(QuestionaireTrafficSourceOption)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)


class QuestionaireCancellationReasonResponse(TapirModel):
    member = models.ForeignKey(Member, on_delete=models.DO_NOTHING, null=True)
    reason = models.CharField(max_length=150)
    custom = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)


class ScheduledTask(TapirModel):
    """
    A scheduled task is being executed at the given eta by celery
    """

    STATUS_PENDING = "PENDING"
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_DONE = "DONE"
    STATUS_FAILED = "FAILED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    task_function = models.CharField(max_length=255)
    task_args = JSONField(blank=True, default=list)
    task_kwargs = JSONField(blank=True, default=dict)
    eta = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def execute(self):
        from importlib import import_module

        module_name, function_name = self.task_function.rsplit(".", 1)
        module = import_module(module_name)
        function = getattr(module, function_name)
        try:
            self.status = self.STATUS_IN_PROGRESS
            self.save()
            function(*self.task_args, **self.task_kwargs)
            self.status = self.STATUS_DONE
        except Exception as e:
            self.status = self.STATUS_FAILED
            self.error_message = str(e)
        finally:
            self.save()

    def __str__(self):
        return f"{self.task_function} | eta: {self.eta} | status: {self.status}"
