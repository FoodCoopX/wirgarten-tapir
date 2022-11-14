from importlib.resources import _

from django import forms


class BestellCoopForm(forms.Form):
    bestellcoop = forms.BooleanField(
        label=_("Ich möchte Mitglied der BestellCoop werden!"),
        initial=False,
        required=False,
    )

    intro_template = "wirgarten/registration/steps/bestellcoop.intro.html"
    outro_template = "wirgarten/registration/steps/bestellcoop.outro.html"

    def __init__(self, **kwargs):
        super(BestellCoopForm, self).__init__()
        self.bestellcoop_price = kwargs["initial"]["bestellcoop_price"]

    def is_valid(self):
        return True
