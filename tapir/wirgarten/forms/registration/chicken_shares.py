from dateutil.relativedelta import relativedelta
from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.wirgarten.constants import ProductTypes
from tapir.wirgarten.forms.pickup_location import (
    PickupLocationChoiceField,
    get_current_capacity,
)
from tapir.wirgarten.models import (
    Product,
    ProductType,
    Subscription,
    MandateReference,
    GrowingPeriod,
    Member,
    MemberPickupLocation,
)
from tapir.wirgarten.service.delivery import (
    get_next_delivery_date,
    get_active_pickup_location_capabilities,
)
from tapir.wirgarten.service.member import (
    get_or_create_mandate_ref,
    get_next_contract_start_date,
    send_order_confirmation,
    change_pickup_location,
)
from tapir.wirgarten.service.payment import (
    get_active_subscriptions_grouped_by_product_type,
)
from tapir.wirgarten.service.products import (
    get_product_price,
    get_free_product_capacity,
    get_current_growing_period,
)
from tapir.wirgarten.utils import format_date, get_now, get_today

CHICKEN_SHARE_FIELD_PREFIX = "chicken_shares_"


class ChickenShareForm(forms.Form):
    intro_template = "wirgarten/registration/steps/chicken_shares.intro.html"
    outro_template = "wirgarten/registration/steps/chicken_shares.outro.html"

    def __init__(self, *args, **kwargs):
        self.member_id = kwargs.pop("member_id", None)
        super(ChickenShareForm, self).__init__(
            *args,
            **{
                k: v
                for k, v in kwargs.items()
                if k != "start_date" and k != "choose_growing_period"
            },
        )
        initial = kwargs.get("initial", {})

        self.choose_growing_period = kwargs.get("choose_growing_period", False)
        self.start_date = kwargs.get(
            "start_date", initial.get("start_date", get_next_contract_start_date())
        )
        self.product_type = ProductType.objects.get(name=ProductTypes.CHICKEN_SHARES)
        self.products = {
            """chicken_shares_{variation}""".format(variation=p.name): p
            for p in Product.objects.filter(deleted=False, type=self.product_type)
        }

        prices = {
            prod.id: get_product_price(prod, self.start_date).price
            for prod in self.products.values()
        }

        self.field_order = list(self.products.keys()) + ["consent_chicken_shares"]
        self.n_columns = len(self.products)
        self.colspans = {
            "consent_chicken_shares": self.n_columns,
            "growing_period": self.n_columns,
            "pickup_location": self.n_columns,
            "pickup_location_change_date": self.n_columns,
        }

        if self.choose_growing_period:
            growing_periods = GrowingPeriod.objects.filter(
                end_date__gte=self.start_date,
            ).order_by("start_date")

            self.free_capacity = []
            for period in growing_periods:
                self.free_capacity.append(
                    f"{get_free_product_capacity(self.product_type.id, max(period.start_date, self.start_date))}".replace(
                        ",", "."
                    )
                )

            self.fields["growing_period"] = forms.ModelChoiceField(
                queryset=growing_periods,
                label=_("Vertragsperiode"),
                required=True,
                empty_label=None,
                initial=0,
            )
        else:
            self.growing_period = get_current_growing_period(self.start_date)

            self.free_capacity = [
                f"{get_free_product_capacity(self.product_type.id, max(self.growing_period.start_date, self.start_date))}".replace(
                    ",", "."
                )
            ]

        for k, v in self.products.items():
            self.fields[k] = forms.IntegerField(
                required=False,
                min_value=0,
                initial=0,
                label=_(
                    """{variation} Hühneranteile""".format(
                        variation=k.replace("chicken_shares_", "")
                    )
                ),
                help_text="""{:.2f} € inkl. MwSt / Monat""".format(prices[v.id]),
            )
        self.fields["consent_chicken_shares"] = forms.BooleanField(
            label=_(
                "Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."
            ),
            help_text=_(
                '<a href="https://lueneburg.wirgarten.com/vertragsgrundsaetze_huehneranteil" target="_blank">Vertragsgrundsätze - Hühneranteile</a>'
            ),
            required=False,
            initial=False,
        )

        if self.member_id:
            member = Member.objects.get(id=self.member_id)
            subs = get_active_subscriptions_grouped_by_product_type(member)
            product_type = ProductType.objects.get(name=ProductTypes.CHICKEN_SHARES)
            new_sub_dummy = Subscription(
                quantity=1, product=Product.objects.get(type=product_type, base=True)
            )
            subs[product_type.name] = (
                [new_sub_dummy]
                if product_type.name not in subs
                else (subs[product_type.name] + [new_sub_dummy])
            )
            self.fields["pickup_location"] = PickupLocationChoiceField(
                required=False,
                label=_("Neuen Abholort auswählen"),
                initial={"subs": subs},
            )
            today = get_today()
            next_delivery_date = get_next_delivery_date(
                today + relativedelta(days=2)
            )  # FIXME: the +2 days should be a configurable treshold. It takes some time to prepare the deliveries in which no changes are allowed
            next_month = today + relativedelta(months=1, day=1)
            self.fields["pickup_location_change_date"] = forms.ChoiceField(
                required=False,
                label=_("Abholortwechsel zum"),
                choices=[
                    (
                        next_delivery_date,
                        f"Nächstmöglicher Zeitpunkt ({format_date(next_delivery_date)})",
                    ),
                    (next_month, f"Nächster Monat ({format_date(next_month)})"),
                ],
            )

        self.chicken_share_prices = ",".join(
            map(
                lambda k: k + ":" + str(prices[self.products[k].id]),
                self.products.keys(),
            )
        )

    def has_chicken_shares(self):
        for key, val in self.cleaned_data.items():
            if key.startswith("chicken_shares_") and val is not None and val > 0:
                return True
        return False

    @transaction.atomic
    def save(
        self, member_id, mandate_ref: MandateReference = None, send_mail: bool = False
    ):
        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(member_id)

        now = get_now()

        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.pop(
                "growing_period", get_current_growing_period()
            )

        self.subs = []
        for key, quantity in self.cleaned_data.items():
            if key.startswith(CHICKEN_SHARE_FIELD_PREFIX) and quantity and quantity > 0:
                product = Product.objects.get(
                    type=self.product_type,
                    name=key.replace(CHICKEN_SHARE_FIELD_PREFIX, ""),
                )
                self.subs.append(
                    Subscription(
                        member_id=member_id,
                        product=product,
                        quantity=quantity,
                        period=self.growing_period,
                        start_date=max(self.start_date, self.growing_period.start_date),
                        end_date=self.growing_period.end_date,
                        mandate_ref=mandate_ref,
                        consent_ts=now,
                        withdrawal_consent_ts=now,
                    )
                )

        Subscription.objects.bulk_create(self.subs)
        Member.objects.filter(id=member_id).update(sepa_consent=get_now())

        new_pickup_location = self.cleaned_data.get("pickup_location")
        change_date = self.cleaned_data.get("pickup_location_change_date")
        if new_pickup_location:
            change_pickup_location(member_id, new_pickup_location, change_date)

        if send_mail:
            member = Member.objects.get(id=member_id)
            send_order_confirmation(member, self.subs)

    def is_valid(self):
        super().is_valid()

        has_chicken_shares = self.has_chicken_shares()
        if has_chicken_shares and not self.cleaned_data.get(
            "consent_chicken_shares", False
        ):
            self.add_error(
                "consent_chicken_shares",
                _(
                    "Du musst den Vertragsgrundsätzen zustimmen um Hühneranteile zu zeichnen."
                ),
            )

        new_pickup_location = self.cleaned_data.get("pickup_location")
        if not new_pickup_location and has_chicken_shares and self.member_id:
            product_type = ProductType.objects.get(name=ProductTypes.CHICKEN_SHARES)
            next_month = get_today() + relativedelta(months=1, day=1)
            latest_pickup_location = (
                MemberPickupLocation.objects.filter(
                    member_id=self.member_id, valid_from__lte=next_month
                )
                .order_by("-valid_from")
                .first()
            )
            if not latest_pickup_location:
                self.add_error(None, _("Bitte wähle einen Abholort aus!"))
                return False
            else:
                latest_pickup_location = latest_pickup_location.pickup_location

            total = 0.0
            for key, quantity in self.cleaned_data.items():
                if key.startswith(CHICKEN_SHARE_FIELD_PREFIX) and (
                    quantity is not None and quantity > 0
                ):
                    product = Product.objects.get(
                        type_id=product_type.id,
                        name__iexact=key.replace(CHICKEN_SHARE_FIELD_PREFIX, ""),
                    )
                    total += float(get_product_price(product).price)

            capability = get_active_pickup_location_capabilities().filter(
                pickup_location=latest_pickup_location,
                product_type__id=product_type.id,
            )
            if not capability.exists():
                self.add_error(
                    "pickup_location", "Abholort unterstützt Produkt nicht"
                )  # this is not displayed
                self.add_error(
                    None,
                    "An deinem Abholort können leider keine Hühneranteile abgeholt werden. Bitte wähle einen anderen Abholort aus.",
                )
            else:
                capability = capability.first()
                if capability.max_capacity:
                    current_capacity = (
                        get_current_capacity(capability, next_month) + total
                    ) / float(product_type.base_price)
                    free_capacity = capability.max_capacity - current_capacity
                    if current_capacity > free_capacity:
                        self.add_error(
                            "pickup_location", "Abholort ist voll"
                        )  # this is not displayed
                        self.add_error(
                            None,
                            _(
                                "Dein Abholort ist leider voll. Bitte wähle einen anderen Abholort aus."
                            ),
                        )

        return len(self.errors) == 0
