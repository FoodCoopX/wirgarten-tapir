from datetime import date
from importlib.resources import _

from django import forms
from django.db import transaction

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
    get_active_product_types,
    get_future_subscriptions,
)


class BestellCoopForm(forms.Form):
    bestellcoop = forms.BooleanField(
        label=_("Ich möchte Mitglied der BestellCoop werden!"),
        initial=False,
        required=False,
    )

    intro_template = "wirgarten/registration/steps/bestellcoop.intro.html"
    outro_template = "wirgarten/registration/steps/bestellcoop.outro.html"

    def __init__(self, *args, **kwargs):
        super(BestellCoopForm, self).__init__(*args, **kwargs)
        self.product = Product.objects.filter(type__name=ProductTypes.BESTELLCOOP)[0]
        self.bestellcoop_price = get_product_price(self.product).price

    def is_valid(self):
        super(BestellCoopForm, self).is_valid()
        return True

    @transaction.atomic
    def save(
        self,
        member_id,
        mandate_ref: MandateReference = None,
        growing_period: GrowingPeriod = None,
    ):
        if self.cleaned_data["bestellcoop"]:
            today = date.today()
            if not growing_period:
                growing_period = GrowingPeriod.objects.get(
                    start_date__lte=today, end_date__gte=today
                )

            start_date = get_next_contract_start_date(today)
            end_date = growing_period.end_date

            if (
                get_future_subscriptions(start_date)
                .filter(member_id=member_id, product=self.product)
                .exists()
            ):
                # TODO: Member already has a BestellCoop subscription,
                return

            if not mandate_ref:
                mandate_ref = get_or_create_mandate_ref(member_id, False)

            Subscription.objects.create(
                member_id=member_id,
                product=self.product,
                quantity=1,
                start_date=start_date,
                end_date=end_date,
                period=growing_period,
                mandate_ref=mandate_ref,
            )
