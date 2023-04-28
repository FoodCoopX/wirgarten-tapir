from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from tapir import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.forms.registration import HARVEST_SHARE_FIELD_PREFIX
from tapir.wirgarten.models import HarvestShareProduct
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_available_product_types


class CooperativeShareForm(forms.Form):
    intro_template = "wirgarten/registration/steps/coop_shares.intro.html"
    outro_template = "wirgarten/registration/steps/coop_shares.outro.html"

    min_shares: int = 0

    def __init__(self, *args, **kwargs):
        super(CooperativeShareForm, self).__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})

        self.coop_share_price = settings.COOP_SHARE_PRICE

        self.harvest_shares_products = list(
            HarvestShareProduct.objects.filter(
                deleted=False, type_id__in=get_available_product_types()
            )
        )

        default_min_shares = (
            get_parameter_value(Parameter.COOP_MIN_SHARES) if "initial" in kwargs else 1
        )
        for prod in self.harvest_shares_products:
            key = HARVEST_SHARE_FIELD_PREFIX + prod.name.lower()
            if key in initial:
                self.min_shares += initial[key] * prod.min_coop_shares
        if self.min_shares < default_min_shares:
            self.min_shares = default_min_shares

        self.min_amount = self.min_shares * self.coop_share_price

        self.fields["cooperative_shares"] = forms.IntegerField(
            required=True,
            label=_("Genossenschaftsanteile (€)"),
            help_text=_(
                f"Der Betrag muss durch {settings.COOP_SHARE_PRICE} teilbar sein."
            ),
            initial=self.min_amount,
            validators=[MinValueValidator(self.min_amount)],
        )
        self.fields["statute_consent"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Satzung und die Kündigungsfrist von einem Jahr zum Jahresende zur Kenntnis genommen. Ich verpflichte mich, die nach Gesetz und Satzung geschuldete Einzahlungen auf die Geschäftsanteile zu leisten."
            ),
            help_text=f'<a href="{get_parameter_value(Parameter.COOP_STATUTE_LINK)}" target="_blank">Satzung der Genossenschaft</a>',
            required=True,
        )
