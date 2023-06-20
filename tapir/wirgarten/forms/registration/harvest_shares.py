from datetime import date

from dateutil.relativedelta import relativedelta
from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.forms.pickup_location import (
    PickupLocationChoiceField,
    get_current_capacity,
)
from tapir.wirgarten.models import (
    HarvestShareProduct,
    Subscription,
    ProductType,
    Product,
    GrowingPeriod,
    MandateReference,
    Member,
    MemberPickupLocation,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_next_delivery_date,
)
from tapir.wirgarten.service.member import (
    get_next_contract_start_date,
    get_or_create_mandate_ref,
    change_pickup_location,
    send_contract_change_confirmation,
)
from tapir.wirgarten.service.payment import (
    get_solidarity_overplus,
    get_active_subscriptions_grouped_by_product_type,
)
from tapir.wirgarten.service.products import (
    get_product_price,
    get_available_product_types,
    get_free_product_capacity,
    get_current_growing_period,
    is_harvest_shares_available,
)
from tapir.wirgarten.utils import format_date

SOLIDARITY_PRICES = [
    (0.0, _("Ich möchte den Richtpreis zahlen")),
    ("custom", _("Ich möchte einen anderen Betrag zahlen  ⟶")),
    (0.25, "+ 25% 🤩"),
    (0.2, "+ 20% 😍"),
    (0.15, "+ 15% 🚀"),
    (0.1, "+ 10% 🥳"),
    (0.05, "+ 5% 💚"),
    (-0.05, "- 5%"),
    (-0.10, "- 10%"),
    (-0.15, "- 15%"),
]


def get_solidarity_total(reference_date: date = date.today()) -> float:
    val = get_parameter_value(Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED)
    if val == 0:  # disabled
        return 0.0
    elif val == 1:  # enabled
        return 1000.0
    elif val == 2:  # automatic calculation
        return get_solidarity_overplus(reference_date) or 0.0


HARVEST_SHARE_FIELD_PREFIX = "harvest_shares_"


class HarvestShareForm(forms.Form):
    intro_text_skip_hr = True

    intro_template = "wirgarten/registration/steps/harvest_shares.intro.html"
    outro_template = "wirgarten/registration/steps/harvest_shares.outro.html"

    def __init__(self, *args, **kwargs):
        self.member_id = kwargs.pop("member_id", None)
        super().__init__(
            *args,
            **{
                k: v
                for k, v in kwargs.items()
                if k != "start_date"
                and k != "enable_validation"
                and k != "choose_growing_period"
            },
        )
        initial = kwargs.get("initial", {})
        self.require_at_least_one = kwargs.get("enable_validation", False)
        self.start_date = kwargs.get(
            "start_date", initial.get("start_date", get_next_contract_start_date())
        )

        self.choose_growing_period = kwargs.get("choose_growing_period", False)

        harvest_share_products = list(
            HarvestShareProduct.objects.filter(
                deleted=False, type_id__in=get_available_product_types(self.start_date)
            )
        )
        prices = {
            prod.id: get_product_price(prod, self.start_date).price
            for prod in harvest_share_products
        }

        harvest_share_products = sorted(
            harvest_share_products, key=lambda x: prices[x.id]
        )

        self.products = {
            """harvest_shares_{variation}""".format(
                variation=p.product_ptr.name.lower()
            ): p
            for p in harvest_share_products
        }
        self.field_order = list(self.products.keys()) + [
            "solidarity_price_harvest_shares"
        ]
        self.n_columns = len(self.products)
        self.colspans = {
            "growing_period": self.n_columns,
            "solidarity_price_harvest_shares": self.n_columns - 1,
            "solidarity_price_absolute_harvest_shares": 1,
            "consent_harvest_shares": self.n_columns,
            "pickup_location": self.n_columns,
            "pickup_location_change_date": self.n_columns,
        }

        if self.choose_growing_period:
            growing_periods = GrowingPeriod.objects.filter(
                end_date__gte=self.start_date,
            ).order_by("start_date")

            available_growing_periods = []
            for period in growing_periods:
                if is_harvest_shares_available(period.start_date):
                    available_growing_periods.append(period)

            self.solidarity_total = []
            self.free_capacity = []
            for period in available_growing_periods:
                start_date = max(period.start_date, self.start_date)
                solidarity_total = f"{get_solidarity_total(start_date)}".replace(
                    ",", "."
                )
                self.solidarity_total.append(solidarity_total)

                # Assume harvest_share_products[0] is defined earlier in your code
                free_capacity = f"{get_free_product_capacity(harvest_share_products[0].type.id, start_date)}".replace(
                    ",", "."
                )
                self.free_capacity.append(free_capacity)

            self.fields["growing_period"] = forms.ModelChoiceField(
                queryset=growing_periods.filter(
                    id__in=[x.id for x in available_growing_periods]
                ),
                label=_("Vertragsperiode"),
                required=True,
                empty_label=None,
                initial=0,
            )
        else:
            self.growing_period = get_current_growing_period(self.start_date)
            self.solidarity_total = [
                f"{get_solidarity_total(max(self.growing_period.start_date, self.start_date))}".replace(
                    ",", "."
                )
            ]

            self.free_capacity = [
                f"{get_free_product_capacity(harvest_share_products[0].type.id, max(self.growing_period.start_date, self.start_date))}".replace(
                    ",", "."
                )
            ]

        for prod in harvest_share_products:
            self.fields[
                f"{HARVEST_SHARE_FIELD_PREFIX}{prod.name.lower()}"
            ] = forms.IntegerField(
                required=False,
                max_value=10,
                min_value=0,
                initial=0,
                label=_(f"{prod.name}-Ernteanteile"),
                help_text="""{:.2f} € inkl. MwSt / Monat""".format(prices[prod.id]),
            )

        self.fields["solidarity_price_harvest_shares"] = forms.ChoiceField(
            required=False,
            label=_("Solidarpreis [%]²"),
            choices=SOLIDARITY_PRICES,
            initial=0.05,
        )
        self.fields["solidarity_price_absolute_harvest_shares"] = forms.DecimalField(
            required=False,
            label=_("Solidarpreis [€]²"),
            min_value=0.0,
        )

        self.fields["consent_harvest_shares"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."
            ),
            help_text='<a href="https://lueneburg.wirgarten.com/vertragsgrundsaetze_ernteanteil" target="_blank">Vertragsgrundsätze - Ernteanteile</a>',
            required=False,
            initial=False,
        )

        if self.member_id:
            member = Member.objects.get(id=self.member_id)
            subs = get_active_subscriptions_grouped_by_product_type(
                member, self.start_date
            )

            product_type = ProductType.objects.get(name=ProductTypes.HARVEST_SHARES)
            new_sub_dummy = Subscription(
                quantity=2, product=Product.objects.get(type=product_type, base=True)
            )

            sub_variants = {}
            if product_type.name in subs:
                for sub in subs[product_type.name]:
                    sub_variants[sub.product.name.lower()] = {
                        "quantity": sub.quantity,
                        "solidarity_price": sub.solidarity_price,
                        "solidarity_price_absolute": sub.solidarity_price_absolute,
                    }

                for key, field in self.fields.items():
                    if (
                        key.startswith(HARVEST_SHARE_FIELD_PREFIX)
                        and key.replace(HARVEST_SHARE_FIELD_PREFIX, "") in sub_variants
                    ):
                        field.initial = sub_variants[
                            key.replace(HARVEST_SHARE_FIELD_PREFIX, "")
                        ]["quantity"]
                    elif key == "solidarity_price_harvest_shares":
                        field.initial = list(sub_variants.values())[0][
                            "solidarity_price"
                        ]  # FIXME: maybe the soli price should not be in the subscription but in the Member model..
                    elif key == "solidarity_price_absolute_harvest_shares":
                        field.initial = list(sub_variants.values())[0][
                            "solidarity_price_absolute"
                        ]

            subs[product_type.name] = (
                [new_sub_dummy]
                if product_type.name not in subs
                else (subs[product_type.name] + [new_sub_dummy])
            )
            self.fields["pickup_location"] = PickupLocationChoiceField(
                required=False,
                label=_("Neuen Abholort auswählen"),
                initial={"subs": subs},
            )
            today = date.today()
            next_delivery_date = get_next_delivery_date(
                today + relativedelta(days=2)
            )  # FIXME: the +2 days should be a configurable treshold. It takes some time to prepare the deliveries in which no changes are allowed
            next_month = date.today() + relativedelta(months=1, day=1)
            self.fields["pickup_location_change_date"] = forms.ChoiceField(
                required=False,
                label=_("Abholortwechsel zum"),
                choices=[
                    (
                        next_delivery_date,
                        f"Nächstmöglicher Zeitpunkt ({format_date(next_delivery_date)})",
                    ),
                    (next_month, f"Nächster Monat ({format_date(next_month)})"),
                ],
            )

        self.harvest_shares = ",".join(
            map(
                lambda p: HARVEST_SHARE_FIELD_PREFIX
                + p.name.lower()
                + ":"
                + str(prices[p.id]),
                harvest_share_products,
            )
        )

    @transaction.atomic
    def save(self, mandate_ref: MandateReference = None, send_email: bool = False):
        if not self.member_id:
            return

        product_type = ProductType.objects.get(name=ProductTypes.HARVEST_SHARES)

        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(self.member_id)

        now = timezone.now()

        self.subs = []
        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.get(
                "growing_period", get_current_growing_period()
            )

        subs = get_active_subscriptions_grouped_by_product_type(
            self.member_id, self.start_date
        )
        if product_type.name in subs:
            for sub in subs[product_type.name]:
                sub.end_date = self.start_date - relativedelta(days=1)
                if (
                    sub.start_date > sub.end_date
                ):  # change was done before the contract started, so we can delete the subscription
                    sub.delete()
                else:
                    sub.save()

        for key, quantity in self.cleaned_data.items():
            if (
                key.startswith(HARVEST_SHARE_FIELD_PREFIX)
                and quantity is not None
                and quantity > 0
            ):
                product = Product.objects.get(
                    type=product_type,
                    name=key.replace(HARVEST_SHARE_FIELD_PREFIX, "").upper(),
                )

                solidarity_options = (
                    {
                        "solidarity_price": 0.0,
                        "solidarity_price_absolute": self.cleaned_data[
                            "solidarity_price_absolute_harvest_shares"
                        ],
                    }
                    if self.cleaned_data["solidarity_price_harvest_shares"] == "custom"
                    else {
                        "solidarity_price": self.cleaned_data[
                            "solidarity_price_harvest_shares"
                        ]
                    }
                )

                sub = Subscription.objects.create(
                    member_id=self.member_id,
                    product=product,
                    period=self.growing_period,
                    quantity=quantity,
                    start_date=max(self.start_date, self.growing_period.start_date),
                    end_date=self.growing_period.end_date,
                    mandate_ref=mandate_ref,
                    consent_ts=now,
                    withdrawal_consent_ts=timezone.now(),
                    trial_disabled=True,
                    **solidarity_options,
                )

                self.subs.append(sub)

        new_pickup_location = self.cleaned_data.get("pickup_location")
        change_date = self.cleaned_data.get("pickup_location_change_date")
        if new_pickup_location:
            change_pickup_location(self.member_id, new_pickup_location, change_date)

        if send_email:
            member = Member.objects.get(id=self.member_id)
            send_contract_change_confirmation(member, self.subs)

    def has_harvest_shares(self):
        for key, quantity in self.cleaned_data.items():
            if key.startswith(HARVEST_SHARE_FIELD_PREFIX) and (
                quantity is not None and quantity > 0
            ):
                return True
        return False

    def is_valid(self):
        super().is_valid()

        has_harvest_shares = self.has_harvest_shares()
        if has_harvest_shares and not self.cleaned_data.get(
            "consent_harvest_shares", False
        ):
            self.add_error(
                "consent_harvest_shares",
                _(
                    "Du musst den Vertragsgrundsätzen zustimmen um Ernteanteile zu zeichnen."
                ),
            )

        if self.require_at_least_one and not has_harvest_shares:
            self.add_error(None, _("Bitte wähle mindestens einen Ernteanteil!"))

        new_pickup_location = self.cleaned_data.get("pickup_location")
        if not new_pickup_location and has_harvest_shares and self.member_id:
            product_type = ProductType.objects.get(name=ProductTypes.HARVEST_SHARES)
            next_month = date.today() + relativedelta(months=1, day=1)
            latest_pickup_location = (
                MemberPickupLocation.objects.filter(
                    member_id=self.member_id, valid_from__lte=next_month
                )
                .order_by("-valid_from")
                .first()
            )
            if not latest_pickup_location:
                self.add_error(None, _("Bitte wähle einen Abholort aus!"))
                return False
            else:
                latest_pickup_location = latest_pickup_location.pickup_location

            total = 0.0
            for key, quantity in self.cleaned_data.items():
                if key.startswith(HARVEST_SHARE_FIELD_PREFIX) and (
                    quantity is not None and quantity > 0
                ):
                    product = Product.objects.get(
                        type__name=ProductTypes.HARVEST_SHARES,
                        name__iexact=key.replace(HARVEST_SHARE_FIELD_PREFIX, ""),
                    )
                    total += float(get_product_price(product).price)

            capability = (
                get_active_pickup_location_capabilities()
                .filter(
                    pickup_location=latest_pickup_location,
                    product_type__id=product_type.id,
                )
                .first()
            )
            if capability.max_capacity:
                current_capacity = (
                    get_current_capacity(capability, next_month) + total
                ) / float(product_type.base_price)
                free_capacity = capability.max_capacity - current_capacity
                if current_capacity > free_capacity:
                    self.add_error(
                        "pickup_location", "Abholort ist voll"
                    )  # this is not displayed
                    self.add_error(
                        None,
                        _(
                            "Dein Abholort ist leider voll. Bitte wähle einen anderen Abholort aus."
                        ),
                    )

        return len(self.errors) == 0
