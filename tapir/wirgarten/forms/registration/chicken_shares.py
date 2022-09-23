from importlib.resources import _

from django import forms

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Product, ProductType
from tapir.wirgarten.parameters import Parameter


def has_chicken_shares(cleaned_data):
    for key, val in cleaned_data.items():
        if key.startswith("chicken_shares_"):
            if val > 0:
                return True
        return False


class ChickenShareForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(ChickenShareForm, self).__init__(*args, **kwargs)

        product_type = ProductType.objects.get(name="Hühneranteile")
        self.products = {
            """chicken_shares_{variation}""".format(variation=p.name): p.__dict__
            for p in Product.objects.filter(deleted=0, type=product_type)
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
                help_text="""{:.2f} € / Monat""".format(v["price"]),
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
                lambda k: k + ":" + str(self.products[k]["price"]),
                self.products.keys(),
            )
        )

    intro_template = "wirgarten/registration/steps/chicken_shares.intro.html"
    outro_template = "wirgarten/registration/steps/chicken_shares.outro.html"

    def clean(self):
        cleaned_data = super().clean()
        if has_chicken_shares(cleaned_data):
            if not cleaned_data.get("consent"):
                self.add_error(
                    "consent",
                    _(
                        "Du musst den Vertragsgrundsätzen zustimmen um Hühneranteile zu zeichnen."
                    ),
                )
