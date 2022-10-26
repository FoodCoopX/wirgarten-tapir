import datetime
from importlib.resources import _

from django import forms
from django.db import models
from django.db.models import Sum, F

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import HarvestShareProduct, Subscription
from tapir.wirgarten.parameters import Parameter

SOLIDARITY_PRICES = [
    (0.0, _("Ich möchte keinen Solidarpreis zahlen")),
    (0.25, "+ 25% 🤩"),
    (0.2, "+ 20% 😍"),
    (0.15, "+ 15% 🚀"),
    (0.1, "+ 10% 🥳"),
    (0.05, "+ 5% 💚"),
    (-0.05, "- 5%"),
    (-0.10, "- 10%"),
    (-0.15, "- 15%"),
]


def get_solidarity_total() -> float:
    val = get_parameter_value(Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED)
    if val == 0:  # disabled
        return 0.0
    elif val == 1:  # enabled
        return 1000.0  # FIXME: configuration property: max solidarity discount for one user
    elif val == 2:  # automatic calculation
        today = datetime.date.today()
        solidarity_total = (
            Subscription.objects.filter(start_date__lte=today, end_date__gte=today)
            .values("quantity", "product__price", "solidarity_price")
            .aggregate(
                total=Sum(
                    F("quantity") * F("product__price") * F("solidarity_price"),
                    output_field=models.DecimalField(),
                )
            )
        )

        return solidarity_total["total"]


class HarvestShareForm(forms.Form):
    intro_text_skip_hr = True

    intro_template = "wirgarten/registration/steps/harvest_shares.intro.html"
    outro_template = "wirgarten/registration/steps/harvest_shares.outro.html"

    def __init__(self, *args, **kwargs):
        super(HarvestShareForm, self).__init__(*args, **kwargs)

        self.products = {
            """harvest_shares_{variation}""".format(
                variation=p.product_ptr.name.lower()
            ): p.__dict__
            for p in HarvestShareProduct.objects.all()
        }

        self.field_order = list(self.products.keys()) + ["solidarity_price"]
        self.n_columns = len(self.products)
        self.colspans = {"solidarity_price": self.n_columns}

        self.solidarity_total = get_solidarity_total()

        for k, v in self.products.items():
            self.fields[k] = forms.IntegerField(
                required=True,
                max_value=10,
                min_value=0,
                initial=0,
                label=_(
                    """{variation}-Ernteanteile""".format(
                        variation=k.replace("harvest_shares_", "").upper()
                    )
                ),
                help_text="""{:.2f} € / Monat""".format(v["price"]),
            )

        self.fields["solidarity_price"] = forms.ChoiceField(
            required=True,
            label=_("Solidarpreis"),
            choices=SOLIDARITY_PRICES,
        )

        self.harvest_shares = ",".join(
            map(
                lambda k: k + ":" + str(self.products[k]["price"]),
                self.products,
            )
        )
