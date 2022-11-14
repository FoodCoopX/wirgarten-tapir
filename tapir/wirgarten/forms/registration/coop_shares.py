from importlib.resources import _

from django import forms

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import HarvestShareProduct
from tapir.wirgarten.parameters import Parameter


class CooperativeShareForm(forms.Form):
    min_shares: int = 0

    def __init__(self, *args, **kwargs):
        super(CooperativeShareForm, self).__init__(*args, **kwargs)
        initial = kwargs["initial"]

        # FIXME: query already executed on first form. Maybe execute it once in the wizard view and pass result to the forms?
        self.harvest_shares_products = {
            """harvest_shares_{variation}""".format(
                variation=p.product_ptr.name.lower()
            ): p.__dict__
            for p in HarvestShareProduct.objects.all()  # FIXME: filter to active ones (service)
        }

        default_min_shares = get_parameter_value(Parameter.COOP_MIN_SHARES)
        for key, val in self.harvest_shares_products.items():
            if key in initial:
                self.min_shares += initial[key] * val["min_coop_shares"]
        if self.min_shares < default_min_shares:
            self.min_shares = default_min_shares

        self.fields["cooperative_shares"] = forms.IntegerField(
            required=True,
            label=_("Anzahl Genossenschaftsanteile"),
            initial=self.min_shares,
        )
        self.fields["statute_consent"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Satzung und die Kündigungsfrist von einem Jahr zum Jahresende zur Kenntnis genommen."
            ),
            help_text=_(
                "Ich verpflichte mich, die nach Gesetz und Satzung geschuldete Einzahlungen auf die Geschäftsanteile zu leisten."
            ),
            required=True,
        )

        self.harvest_share_prices = (
            ",".join(
                map(
                    lambda k: k + ":" + str(self.harvest_shares_products[k]["price"]),
                    self.harvest_shares_products.keys(),
                )
            ),
        )

    intro_template = "wirgarten/registration/steps/coop_shares.intro.html"
    outro_template = "wirgarten/registration/steps/coop_shares.outro.html"
