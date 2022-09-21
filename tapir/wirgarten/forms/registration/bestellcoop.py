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
