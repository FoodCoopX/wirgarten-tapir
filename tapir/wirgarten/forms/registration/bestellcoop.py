from importlib.resources import _

from django import forms

from tapir.wirgarten.models import Product
from tapir.wirgarten.service.products import get_product_price


class BestellCoopForm(forms.Form):
    bestellcoop = forms.BooleanField(
        label=_("Ich möchte Mitglied der BestellCoop werden!"),
        initial=False,
        required=False,
    )

    intro_template = "wirgarten/registration/steps/bestellcoop.intro.html"
    outro_template = "wirgarten/registration/steps/bestellcoop.outro.html"

    def __init__(self, **kwargs):
        super(BestellCoopForm, self).__init__(**kwargs)
        prod = Product.objects.filter(type__name="BestellCoop")[0]

        self.bestellcoop_price = get_product_price(prod).price

    def is_valid(self):
        super(BestellCoopForm, self).is_valid()
        return True
