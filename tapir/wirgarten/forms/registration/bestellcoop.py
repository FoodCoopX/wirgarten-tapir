from django import forms
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.models import (
    Product,
    Subscription,
    GrowingPeriod,
    MandateReference,
)
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    get_next_contract_start_date,
)
from tapir.wirgarten.service.products import (
    get_product_price,
    get_future_subscriptions,
)


class BestellCoopForm(forms.Form):
    bestellcoop = forms.BooleanField(
        label=_("Ich möchte Mitglied der BestellCoop werden!"),
        initial=False,
        required=False,
    )

    consent_bestellcoop = forms.BooleanField(
        label=_("Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."),
        help_text=_(
            '<a href="https://lueneburg.wirgarten.com/vertragsgrundsaetze_bestellcoop" target="_blank">Vertragsgrundsätze - BestellCoop</a>'
        ),
        required=False,
        initial=False,
    )

    intro_template = "wirgarten/registration/steps/bestellcoop.intro.html"
    outro_template = "wirgarten/registration/steps/bestellcoop.outro.html"
    colspans = {}
    n_columns = 1

    def __init__(self, *args, **kwargs):
        super(BestellCoopForm, self).__init__(
            *args, **{k: v for k, v in kwargs.items() if k != "start_date"}
        )
        initial = kwargs.get("initial", {})
        self.start_date = kwargs.get(
            "start_date", initial.get("start_date", get_next_contract_start_date())
        )
        self.growing_period = GrowingPeriod.objects.get(
            start_date__lte=self.start_date, end_date__gt=self.start_date
        )

        self.product = Product.objects.filter(type__name=ProductTypes.BESTELLCOOP)[0]
        self.bestellcoop_price = get_product_price(self.product, self.start_date).price

    def is_valid(self):
        super(BestellCoopForm, self).is_valid()

        if self.cleaned_data.get("bestellcoop", False) and not self.cleaned_data.get(
            "consent_bestellcoop", False
        ):
            self.add_error(
                "consent_bestellcoop",
                _(
                    "Du musst den Vertragsgrundsätzen zustimmen um Mitglied der BestellCoop zu werden."
                ),
            )

        return len(self.errors) == 0

    @transaction.atomic
    def save(self, member_id, mandate_ref: MandateReference = None):
        if self.cleaned_data["bestellcoop"]:
            if (
                get_future_subscriptions(self.start_date)
                .filter(member_id=member_id, product=self.product, cancellation_ts=None)
                .exists()
            ):
                # TODO: Member already has a BestellCoop subscription,
                return

            if not mandate_ref:
                mandate_ref = get_or_create_mandate_ref(member_id, False)

            self.sub = Subscription.objects.create(
                member_id=member_id,
                product=self.product,
                quantity=1,
                start_date=self.start_date,
                end_date=self.growing_period.end_date,
                period=self.growing_period,
                mandate_ref=mandate_ref,
                consent_ts=timezone.now(),
                withdrawal_consent_ts=timezone.now(),
            )
