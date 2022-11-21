from importlib.resources import _

from django import forms

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Product, ProductType
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_product_price


def has_chicken_shares(cleaned_data):
    for key, val in cleaned_data.items():
        if key.startswith("chicken_shares_") and val > 0:
            return True
        return False


class ChickenShareForm(forms.Form):
    intro_template = "wirgarten/registration/steps/chicken_shares.intro.html"
    outro_template = "wirgarten/registration/steps/chicken_shares.outro.html"

    def __init__(self, *args, **kwargs):
        super(ChickenShareForm, self).__init__(*args, **kwargs)

        self.products = {
            """chicken_shares_{variation}""".format(variation=p.name): p
            for p in Product.objects.filter(
                deleted=False, type=ProductType.objects.get(name="Hühneranteile")
            )
        }

        prices = {
            prod.id: get_product_price(prod).price for prod in self.products.values()
        }

        self.field_order = list(self.products.keys()) + ["consent"]
        self.n_columns = len(self.products)
        self.colspans = {"consent": self.n_columns}

        for k, v in self.products.items():
            self.fields[k] = forms.IntegerField(
                required=True,
                max_value=get_parameter_value(Parameter.CHICKEN_MAX_SHARES),
                min_value=0,
                initial=0,
                label=_(
                    """{variation} Hühneranteile""".format(
                        variation=k.replace("chicken_shares_", "")
                    )
                ),
                help_text="""{:.2f} € / Monat""".format(prices[v.id]),
            )
        self.fields["consent"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."
            ),
            help_text=_(
                "Hast du die Vertragsgrundsätze gelesen und stimmst diesen zu?"
            ),
            required=False,
        )

        self.chicken_share_prices = ",".join(
            map(
                lambda k: k + ":" + str(prices[self.products[k].id]),
                self.products.keys(),
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        if has_chicken_shares(cleaned_data) and not cleaned_data.get("consent"):
            self.add_error(
                "consent",
                _(
                    "Du musst den Vertragsgrundsätzen zustimmen um Hühneranteile zu zeichnen."
                ),
            )
