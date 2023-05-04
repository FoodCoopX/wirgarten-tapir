from dateutil.relativedelta import relativedelta
from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    Product,
    ProductType,
    Subscription,
    MandateReference,
    GrowingPeriod,
)
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    get_next_contract_start_date,
)
from tapir.wirgarten.service.products import (
    get_product_price,
    get_free_product_capacity,
    get_current_growing_period,
)


def has_chicken_shares(cleaned_data):
    for key, val in cleaned_data.items():
        if key.startswith("chicken_shares_") and val is not None and val > 0:
            return True
    return False


class ChickenShareForm(forms.Form):
    intro_template = "wirgarten/registration/steps/chicken_shares.intro.html"
    outro_template = "wirgarten/registration/steps/chicken_shares.outro.html"

    def __init__(self, *args, **kwargs):
        super(ChickenShareForm, self).__init__(
            *args,
            **{
                k: v
                for k, v in kwargs.items()
                if k != "start_date" and k != "choose_growing_period"
            },
        )
        initial = kwargs.get("initial", {})

        self.choose_growing_period = kwargs.get("choose_growing_period", False)
        self.start_date = kwargs.get(
            "start_date", initial.get("start_date", get_next_contract_start_date())
        )
        self.product_type = ProductType.objects.get(name=ProductTypes.CHICKEN_SHARES)
        self.products = {
            """chicken_shares_{variation}""".format(variation=p.name): p
            for p in Product.objects.filter(deleted=False, type=self.product_type)
        }

        prices = {
            prod.id: get_product_price(prod, self.start_date).price
            for prod in self.products.values()
        }

        self.field_order = list(self.products.keys()) + ["consent_chicken_shares"]
        self.n_columns = len(self.products)
        self.colspans = {
            "consent_chicken_shares": self.n_columns,
            "growing_period": self.n_columns,
        }

        if self.choose_growing_period:
            growing_periods = GrowingPeriod.objects.filter(
                end_date__gte=self.start_date + relativedelta(months=-1, days=1),
            ).order_by("start_date")

            self.free_capacity = [
                f"{get_free_product_capacity(self.product_type.id, max(growing_periods[0].start_date, self.start_date))}".replace(
                    ",", "."
                ),
                f"{get_free_product_capacity(self.product_type.id, max(growing_periods[1].start_date, self.start_date))}".replace(
                    ",", "."
                ),
            ]

            self.fields["growing_period"] = forms.ModelChoiceField(
                queryset=growing_periods,
                label=_("Vertragsperiode"),
                required=True,
                empty_label=None,
                initial=0,
            )
        else:
            self.growing_period = get_current_growing_period(self.start_date)

            self.free_capacity = [
                f"{get_free_product_capacity(self.product_type.id, max(self.growing_period.start_date, self.start_date))}".replace(
                    ",", "."
                )
            ]

        for k, v in self.products.items():
            self.fields[k] = forms.IntegerField(
                required=False,
                min_value=0,
                initial=0,
                label=_(
                    """{variation} Hühneranteile""".format(
                        variation=k.replace("chicken_shares_", "")
                    )
                ),
                help_text="""{:.2f} € inkl. MwSt / Monat""".format(prices[v.id]),
            )
        self.fields["consent_chicken_shares"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."
            ),
            help_text=_(
                '<a href="https://lueneburg.wirgarten.com/vertragsgrundsaetze_huehneranteil" target="_blank">Vertragsgrundsätze - Hühneranteile</a>'
            ),
            required=False,
            initial=False,
        )

        self.chicken_share_prices = ",".join(
            map(
                lambda k: k + ":" + str(prices[self.products[k].id]),
                self.products.keys(),
            )
        )

    @transaction.atomic
    def save(self, member_id, mandate_ref: MandateReference = None):
        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(member_id, False)

        now = timezone.now()

        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.pop(
                "growing_period", get_current_growing_period()
            )

        self.subs = []
        for key, quantity in self.cleaned_data.items():
            if quantity and quantity > 0 and key.startswith("chicken_shares_"):
                product = Product.objects.get(
                    type=self.product_type, name=key.replace("chicken_shares_", "")
                )
                self.subs.append(
                    Subscription(
                        member_id=member_id,
                        product=product,
                        quantity=quantity,
                        period=self.growing_period,
                        start_date=max(self.start_date, self.growing_period.start_date),
                        end_date=self.growing_period.end_date,
                        mandate_ref=mandate_ref,
                        consent_ts=now,
                        withdrawal_consent_ts=now,
                    )
                )

        Subscription.objects.bulk_create(self.subs)

    def is_valid(self):
        super().is_valid()

        if has_chicken_shares(self.cleaned_data) and not self.cleaned_data.get(
            "consent_chicken_shares", False
        ):
            self.add_error(
                "consent_chicken_shares",
                _(
                    "Du musst den Vertragsgrundsätzen zustimmen um Hühneranteile zu zeichnen."
                ),
            )
        return len(self.errors) == 0
