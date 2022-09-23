from importlib.resources import _

from django import forms

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import HarvestShareProduct
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


def get_solidarity_price_choices():
    if get_parameter_value(Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED):
        return SOLIDARITY_PRICES
    else:
        return filter(lambda sp: sp[0] >= 0, SOLIDARITY_PRICES)


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
            choices=get_solidarity_price_choices(),
        )

        self.harvest_shares = ",".join(
            map(
                lambda k: k + ":" + str(self.products[k]["price"]),
                self.products,
            )
        )
