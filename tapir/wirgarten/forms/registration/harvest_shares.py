from datetime import date

from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    HarvestShareProduct,
    Subscription,
    ProductType,
    Product,
    GrowingPeriod,
    MandateReference,
    Member,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.member import (
    get_next_contract_start_date,
    get_or_create_mandate_ref,
    send_order_confirmation,
)
from tapir.wirgarten.service.payment import (
    get_solidarity_overplus,
)
from tapir.wirgarten.service.products import (
    get_product_price,
    get_available_product_types,
    get_free_product_capacity,
)

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
        super().__init__(
            *args,
            **{
                k: v
                for k, v in kwargs.items()
                if k != "start_date" and k != "enable_validation"
            },
        )
        self.require_at_least_one = kwargs.get("enable_validation", False)
        self.start_date = kwargs.get("start_date", get_next_contract_start_date())
        self.growing_period = GrowingPeriod.objects.get(
            start_date__lte=self.start_date, end_date__gt=self.start_date
        )

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
            "solidarity_price_harvest_shares": self.n_columns - 1,
            "solidarity_price_absolute_harvest_shares": 1,
            "consent_harvest_shares": self.n_columns,
        }

        self.solidarity_total = f"{get_solidarity_total(self.start_date)}".replace(
            ",", "."
        )

        self.free_capacity = f"{get_free_product_capacity(harvest_share_products[0].type.id, self.start_date)}".replace(
            ",", "."
        )
        for prod in harvest_share_products:
            self.fields[
                f"{HARVEST_SHARE_FIELD_PREFIX}{prod.name.lower()}"
            ] = forms.IntegerField(
                required=False,
                max_value=10,
                min_value=0,
                initial=0 if prod.name.lower() != "m" else 1,
                label=_(f"{prod.name}-Ernteanteile"),
                help_text="""{:.2f} € inkl. MwSt / Monat""".format(prices[prod.id]),
            )

        self.fields["solidarity_price_harvest_shares"] = forms.ChoiceField(
            required=False,
            label=_("Solidarpreis²"),
            choices=SOLIDARITY_PRICES,
            initial=0.05,
        )
        self.fields["solidarity_price_absolute_harvest_shares"] = forms.DecimalField(
            required=False,
            label=_("Solidaraufschlag [€]²"),
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
    def save(
        self, member_id, mandate_ref: MandateReference = None, send_email: bool = False
    ):
        product_type = ProductType.objects.get(name=ProductTypes.HARVEST_SHARES)

        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(member_id, False)

        now = timezone.now()

        self.subs = []
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
                    member_id=member_id,
                    product=product,
                    period=self.growing_period,
                    quantity=quantity,
                    start_date=self.start_date,
                    end_date=self.growing_period.end_date,
                    mandate_ref=mandate_ref,
                    consent_ts=now,
                    withdrawal_consent_ts=timezone.now(),
                    **solidarity_options,
                )

                self.subs.append(sub)

        if send_email:
            member = Member.objects.get(id=member_id)
            send_order_confirmation(member, self.subs)

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

        return len(self.errors) == 0
