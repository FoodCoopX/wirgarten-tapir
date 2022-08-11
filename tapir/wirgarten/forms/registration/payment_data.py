from importlib.resources import _

from django import forms
from localflavor.exceptions import ValidationError
from localflavor.generic.validators import IBANValidator, BICValidator

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameters import Parameter


class PaymentDataForm(forms.Form):
    account_owner = forms.CharField(label=_("Kontoinhaber"))
    iban = forms.CharField(label=_("IBAN"))
    bic = forms.CharField(label=_("BIC"))

    def __init__(self, *args, **kwargs):
        super(PaymentDataForm, self).__init__(*args, **kwargs)
        self.fields["sepa_consent"] = forms.BooleanField(
            label=_(
                """Ich ermächtige die {site_name} die gezeichneten Geschäftsanteile sowie die monatlichen Beträge für den 
                Ernteanteil und ggf. weitere Produkte mittels Lastschrift von meinem Bankkonto einzuziehen. Zugleich 
                weise ich mein Kreditinstitut an, die gezogene Lastschrift einzulösen. """
            ).format(site_name=get_parameter_value(Parameter.SITE_NAME)),
            required=True,
        )

    colspans = {"account_owner": 2, "sepa_consent": 2}
    n_columns = 2

    def get_initial_for_field(self, field, field_name):
        if not hasattr(self, "instance") or self.instance is None:
            return

        if field_name in ["account_owner", "iban", "bic"]:
            return getattr(self.instance, field_name)
        else:
            return super().get_initial_for_field(field, field_name)

    def clean_iban(self):
        # Théo 17.03.22 : I tried just putting iban and bic as fields in the Meta class,
        # I was getting django errors that I didn't manage to solve, so I made them manually.
        iban = self.cleaned_data["iban"]
        try:
            IBANValidator()(iban)
        except ValidationError:
            self.add_error("iban", _("Ungültige IBAN"))
        return iban

    def clean_bic(self):
        bic = self.cleaned_data["bic"]
        try:
            BICValidator()(bic)
        except ValidationError:
            self.add_error("bic", _("Ungültige BIC"))
        return bic
