from django import forms
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from django.conf import settings
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.forms.subscription import BASE_PRODUCT_FIELD_PREFIX
from tapir.wirgarten.models import HarvestShareProduct
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import get_available_product_types


class CooperativeShareForm(forms.Form):
    min_shares: int = 0

    def __init__(self, *args, **kwargs):
        super(CooperativeShareForm, self).__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        self.intro_template = initial.pop("intro_template", None)
        self.outro_template = initial.pop("outro_template", None)

        self.coop_share_price = settings.COOP_SHARE_PRICE

        self.harvest_shares_products = list(
            HarvestShareProduct.objects.filter(
                deleted=False, type_id__in=get_available_product_types()
            )
        )

        default_min_shares = get_parameter_value(Parameter.COOP_MIN_SHARES)
        for prod in self.harvest_shares_products:
            key = BASE_PRODUCT_FIELD_PREFIX + prod.name
            if key in initial and initial.get(key, 0) is not None:
                self.min_shares += initial.get(key, 0) * prod.min_coop_shares
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
