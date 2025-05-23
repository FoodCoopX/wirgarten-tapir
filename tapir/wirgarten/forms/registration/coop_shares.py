from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.forms.subscription import BASE_PRODUCT_FIELD_PREFIX
from tapir.wirgarten.models import HarvestShareProduct
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_available_product_types


class CooperativeShareForm(forms.Form):
    min_shares: int = 0

    def __init__(self, *args, **kwargs):
        show_student_checkbox = kwargs.pop("show_student_checkbox", True)
        self.member_is_student = kwargs.pop("member_is_student", False)
        self.cache = kwargs.pop("cache", {})
        super().__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        self.intro_templates = initial.pop("intro_templates", None)
        self.outro_templates = initial.pop("outro_templates", None)

        self.coop_share_price = settings.COOP_SHARE_PRICE

        self.harvest_shares_products = list(
            HarvestShareProduct.objects.filter(
                deleted=False, type_id__in=get_available_product_types(cache=self.cache)
            )
        )

        default_min_shares = get_parameter_value(
            ParameterKeys.COOP_MIN_SHARES, cache=self.cache
        )
        for prod in self.harvest_shares_products:
            key = BASE_PRODUCT_FIELD_PREFIX + prod.name
            if key in initial and initial.get(key, 0) is not None:
                self.min_shares += initial.get(key, 0) * prod.min_coop_shares
        if self.min_shares < default_min_shares:
            self.min_shares = default_min_shares

        self.min_amount = self.min_shares * self.coop_share_price

        self.fields["cooperative_shares"] = forms.IntegerField(
            required=False,
            label=_("Genossenschaftsanteile (€)"),
            help_text=_(
                f"Der Betrag muss durch {settings.COOP_SHARE_PRICE} teilbar sein."
            ),
            initial=self.min_amount,
        )

        if show_student_checkbox:
            self.fields["is_student"] = forms.BooleanField(
                required=False,
                label=_(
                    "Ich bin Student*in und kann keine Genossenschaftsanteile zeichnen"
                ),
                help_text="Die Immatrikulationsbescheinigung muss per Mail an <a href='mailto:lueneburg@wirgarten.com'>lueneburg@wirgarten.com</a> gesendet werden.",
            )
        self.fields["statute_consent"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Satzung und die Kündigungsfrist von einem Jahr zum Jahresende zur Kenntnis genommen. Ich verpflichte mich, die nach Gesetz und Satzung geschuldete Einzahlungen auf die Geschäftsanteile zu leisten."
            ),
            help_text=f'<a href="{get_parameter_value(ParameterKeys.COOP_STATUTE_LINK, cache=self.cache)}" target="_blank">Satzung der Genossenschaft</a>',
            required=False,
        )

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("is_student", False):
            # The person is registering and is a student: they cannot order any shares and cannot become a member
            cleaned_data["cooperative_shares"] = 0
            cleaned_data["statute_consent"] = False
            return cleaned_data

        min_amount = (
            settings.COOP_SHARE_PRICE if self.member_is_student else self.min_amount
        )
        if cleaned_data.get("cooperative_shares") < min_amount:
            self.add_error(
                "cooperative_shares",
                ValidationError(
                    MinValueValidator.message,
                    params={"limit_value": self.min_amount},
                ),
            )
        if not cleaned_data.get("statute_consent", False):
            self.add_error(
                "statute_consent",
                ValidationError(
                    self.fields["statute_consent"].error_messages["required"],
                ),
            )

        return cleaned_data
