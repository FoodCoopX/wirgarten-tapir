from collections import OrderedDict
from datetime import date

from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.utils.forms import DateInput
from tapir.wirgarten.forms.pickup_location import (
    PickupLocationChoiceField,
)
from tapir.wirgarten.models import (
    GrowingPeriod,
    HarvestShareProduct,
    MandateReference,
    Member,
    MemberPickupLocation,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_next_delivery_date,
)
from tapir.wirgarten.service.member import (
    change_pickup_location,
    get_next_contract_start_date,
    get_or_create_mandate_ref,
    send_order_confirmation,
)
from tapir.wirgarten.service.payment import (
    get_active_subscriptions_grouped_by_product_type,
    get_automatically_calculated_solidarity_excess,
)
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_current_growing_period,
    get_free_product_capacity,
    get_product_price,
    get_total_price_for_subs,
    get_next_growing_period,
)
from tapir.wirgarten.utils import format_date, get_now, get_today

SOLIDARITY_PRICES = [
    (0.0, _("Ich möchte den Richtpreis zahlen")),
    ("custom", _("Ich möchte einen anderen Betrag zahlen  ⟶")),
    (0.25, "+ 25% 🤩"),
    (0.2, "+ 20% 😍"),
    (0.15, "+ 15% 🚀"),
    (0.1, "+ 10% 🥳"),
    (0.05, "+ 5% 💚"),
    (-0.05, "- 5%"),
    (-0.10, "- 10%"),
    (-0.15, "- 15%"),
]


def get_available_solidarity(reference_date: date = get_today()) -> float:
    val = get_parameter_value(Parameter.HARVEST_NEGATIVE_SOLIPRICE_ENABLED)
    if val == 0:  # disabled
        return 0.0
    elif val == 1:  # enabled
        return 1000.0
    elif val == 2:  # automatic calculation
        return get_automatically_calculated_solidarity_excess(reference_date) or 0.0


BASE_PRODUCT_FIELD_PREFIX = "base_product_"


class BaseProductForm(forms.Form):
    intro_text_skip_hr = True

    sum_template = "wirgarten/member/base_product_sum.html"

    def __init__(self, *args, **kwargs):
        self.member_id = kwargs.pop("member_id", None)
        self.is_admin = kwargs.pop("is_admin", False)
        self.require_at_least_one = kwargs.pop("enable_validation", False)
        self.choose_growing_period = kwargs.pop("choose_growing_period", False)
        initial = kwargs.get("initial", {})

        self.start_date = kwargs.pop(
            "start_date", initial.get("start_date", get_next_contract_start_date())
        )
        self.intro_template = initial.pop("intro_template", None)
        self.outro_template = initial.pop("outro_template", None)

        if initial and not self.choose_growing_period:
            next_growing_period = get_next_growing_period()
            self.choose_growing_period = (
                next_growing_period
                and (next_growing_period.start_date - get_today()).days <= 61
            )

        super().__init__(*args, **kwargs)

        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        harvest_share_products = Product.objects.filter(
            deleted=False, type_id=base_product_type_id
        )
        for p in harvest_share_products:
            price = get_product_price(p)
            if price and price.valid_from > self.start_date:
                harvest_share_products = harvest_share_products.exclude(id=p.id)

        self.n_columns = max(2, len(harvest_share_products))

        prices = {
            prod.id: get_product_price(prod, self.start_date).price
            for prod in harvest_share_products
        }

        harvest_share_products = sorted(
            harvest_share_products, key=lambda x: prices[x.id]
        )

        self.product_type = ProductType.objects.get(id=base_product_type_id)
        self.products = (
            {
                """harvest_shares_{variation}""".format(variation=p.product_ptr.name): p
                for p in harvest_share_products
            }
            if type(harvest_share_products[0]) == HarvestShareProduct
            else {
                """harvest_shares_{variation}""".format(variation=p.name): p
                for p in harvest_share_products
            }
        )

        self.field_order = list(self.products.keys()) + [
            "solidarity_price_harvest_shares"
        ]
        self.colspans = {
            "growing_period": self.n_columns,
            "solidarity_price_harvest_shares": self.n_columns - 1,
            "solidarity_price_absolute_harvest_shares": 1,
            "consent_harvest_shares": self.n_columns,
            "pickup_location": self.n_columns,
            "pickup_location_change_date": self.n_columns,
        }

        for prod_field in self.products.keys():
            self.colspans[prod_field] = self.n_columns // len(self.products)

        if self.choose_growing_period:
            available_growing_periods = GrowingPeriod.objects.filter(
                end_date__gte=self.start_date,
            ).order_by("start_date")

            self.solidarity_total = []
            self.free_capacity = []
            for period in available_growing_periods:
                start_date = max(period.start_date, self.start_date)
                solidarity_total = f"{get_available_solidarity(start_date)}".replace(
                    ",", "."
                )
                self.solidarity_total.append(solidarity_total)

                free_capacity = f"{get_free_product_capacity(harvest_share_products[0].type.id, start_date)}".replace(
                    ",", "."
                )
                self.free_capacity.append(free_capacity)

            self.fields["growing_period"] = forms.ModelChoiceField(
                queryset=available_growing_periods,
                label=_("Vertragsperiode"),
                required=True,
                empty_label=None,
                initial=0,
                help_text=(
                    None
                    if self.member_id
                    else _(
                        "<span style='font-weight: bold; color: #CC3333;'>Hinweis: Wenn du sowohl für die aktuelle (bis zum 30.6.) "
                        "als auch kommende Vertragsperiode (ab 1.7.) "
                        "Ernteanteile zeichnen möchtest, dann wähle die aktuelle Vertragsperiode aus "
                        "und verlängere anschließend bequem über den Mitgliederbereich deinen Vertrag "
                        "für die kommende Vertragsperiode. So musst du nicht erneut die Formularseiten ausfüllen</span>"
                    )
                ),
            )
        else:
            self.growing_period = get_current_growing_period(self.start_date)
            self.solidarity_total = [
                f"{get_available_solidarity(max(self.growing_period.start_date, self.start_date))}".replace(
                    ",", "."
                )
            ]

            self.free_capacity = [
                f"{get_free_product_capacity(harvest_share_products[0].type.id, max(self.growing_period.start_date, self.start_date))}".replace(
                    ",", "."
                )
            ]

        for prod_field in harvest_share_products:
            self.fields[f"{BASE_PRODUCT_FIELD_PREFIX}{prod_field.name}"] = (
                forms.IntegerField(
                    required=False,
                    max_value=10,
                    min_value=0,
                    initial=0,
                    label=_(f"{prod_field.name}-{self.product_type.name}"),
                    help_text="""{:.2f} € inkl. MwSt / Monat""".format(
                        prices[prod_field.id]
                    ),
                )
            )

        self.fields["solidarity_price_harvest_shares"] = forms.ChoiceField(
            required=False,
            label=_("Solidarpreis [%]²"),
            choices=SOLIDARITY_PRICES,
            initial=0.0,
        )
        self.fields["solidarity_price_absolute_harvest_shares"] = forms.DecimalField(
            required=False,
            label=_("Solidarpreis [€]²"),
            min_value=0.0,
        )

        if self.product_type.contract_link:
            self.fields["consent_harvest_shares"] = forms.BooleanField(
                label=_(
                    "Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."
                ),
                help_text=f'<a href="{self.product_type.contract_link}" target="_blank">Vertragsgrundsätze - {self.product_type.name}</a>',
                required=False,
                initial=False,
            )

        if self.member_id:
            member = Member.objects.get(id=self.member_id)
            subs = get_active_subscriptions_grouped_by_product_type(
                member, self.start_date
            )

            new_sub_dummy = Subscription(
                quantity=1,
                product=Product.objects.get(type=self.product_type, base=True),
            )

            sub_variants = {}
            if self.product_type.name in subs:
                for sub in subs[self.product_type.name]:
                    sub_variants[sub.product.name] = {
                        "quantity": sub.quantity,
                        "solidarity_price": sub.solidarity_price,
                        "solidarity_price_absolute": sub.solidarity_price_absolute,
                    }

                self.current_used_capacity = get_total_price_for_subs(
                    subs[self.product_type.name]
                )
                if len(sub_variants) > 0:
                    soli_absolute = list(sub_variants.values())[0][
                        "solidarity_price_absolute"
                    ]
                    for key, field in self.fields.items():
                        if (
                            key.startswith(BASE_PRODUCT_FIELD_PREFIX)
                            and key.replace(BASE_PRODUCT_FIELD_PREFIX, "")
                            in sub_variants
                        ):
                            field.initial = sub_variants[
                                key.replace(BASE_PRODUCT_FIELD_PREFIX, "")
                            ]["quantity"]
                        elif key == "solidarity_price_harvest_shares":
                            field.initial = (
                                list(sub_variants.values())[0]["solidarity_price"]
                                if not soli_absolute
                                else "custom"
                            )  # FIXME: maybe the soli price should not be in the subscription but in the Member model..
                        elif key == "solidarity_price_absolute_harvest_shares":
                            field.initial = soli_absolute

            subs[self.product_type.name] = (
                [new_sub_dummy]
                if self.product_type.name not in subs
                else (subs[self.product_type.name] + [new_sub_dummy])
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
            if next_month < next_delivery_date:
                next_month += relativedelta(months=1)
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

        self.harvest_shares = ",".join(
            map(
                lambda p: BASE_PRODUCT_FIELD_PREFIX + p.name + ":" + str(prices[p.id]),
                harvest_share_products,
            )
        )

    @transaction.atomic
    def save(
        self,
        mandate_ref: MandateReference = None,
        member_id: str = None,
    ):
        member_id = member_id or self.member_id

        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(member_id)

        now = get_now()

        self.subs = []
        existing_trial_end_date = cancel_subs_for_edit(
            member_id, self.start_date, self.product_type
        )

        for key, quantity in self.cleaned_data.items():
            if not (
                key.startswith(BASE_PRODUCT_FIELD_PREFIX)
                and quantity is not None
                and quantity > 0
            ):
                continue

            product = Product.objects.get(
                type=self.product_type,
                name=key.replace(BASE_PRODUCT_FIELD_PREFIX, ""),
            )

            notice_period_duration_in_months = None
            if get_parameter_value(Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL):
                notice_period_duration_in_months = (
                    NoticePeriodManager.get_notice_period_duration(
                        self.product_type, self.growing_period
                    )
                )

            sub = Subscription.objects.create(
                member_id=member_id,
                product=product,
                period=self.growing_period,
                quantity=quantity,
                start_date=self.start_date,
                end_date=self.growing_period.end_date,
                mandate_ref=mandate_ref,
                consent_ts=(
                    now
                    if self.product_type.contract_link
                    and self.cleaned_data["consent_harvest_shares"]
                    else None
                ),
                withdrawal_consent_ts=now,
                trial_end_date_override=existing_trial_end_date,
                **self.build_solidarity_fields(),
                notice_period_duration_in_months=notice_period_duration_in_months,
            )

            self.subs.append(sub)

        member = Member.objects.get(id=member_id)
        member.sepa_consent = now
        member.save()

        new_pickup_location = self.cleaned_data.get("pickup_location")
        if new_pickup_location:
            change_date = self.cleaned_data.get("pickup_location_change_date")
            change_pickup_location(member_id, new_pickup_location, change_date)

    def build_solidarity_fields(self):
        selected_option = self.cleaned_data["solidarity_price_harvest_shares"]
        if selected_option == "custom":
            return {
                "solidarity_price": 0.0,
                "solidarity_price_absolute": self.cleaned_data[
                    "solidarity_price_absolute_harvest_shares"
                ],
            }
        return {"solidarity_price": selected_option}

    def has_harvest_shares(self):
        for key, quantity in self.cleaned_data.items():
            if key.startswith(BASE_PRODUCT_FIELD_PREFIX) and (
                quantity is not None and quantity > 0
            ):
                return True
        return False

    def validate_harvest_shares_consent(self):
        if self.product_type.contract_link and not self.cleaned_data.get(
            "consent_harvest_shares", False
        ):
            self.add_error(
                "consent_harvest_shares",
                _(
                    f"Du musst den Vertragsgrundsätzen zustimmen um {self.product_type.name} zu zeichnen."
                ),
            )

    def validate_pickup_location(self):
        if not MemberPickupLocation.objects.filter(member_id=self.member_id).exists():
            self.add_error(None, _("Bitte wähle einen Abholort aus!"))
            return False

    def get_pickup_location(self):
        pickup_location = self.cleaned_data.get("pickup_location")
        if pickup_location:
            return pickup_location

        member_pickup_locations = MemberPickupLocation.objects.filter(
            member_id=self.member_id
        )
        if member_pickup_locations.count() == 1:
            return member_pickup_locations.get().pickup_location

        next_month = get_today() + relativedelta(months=1, day=1)
        return (
            member_pickup_locations.filter(valid_from__lte=next_month)
            .order_by("-valid_from")
            .first()
            .pickup_location
        )

    def calculate_capacity_used_by_the_ordered_products(
        self, return_capacity_in_euros: bool = False
    ):
        base_prod_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)

        total = 0.0
        for key, quantity in self.cleaned_data.items():
            if not key.startswith(BASE_PRODUCT_FIELD_PREFIX) or not quantity:
                continue
            next_month = get_today() + relativedelta(months=1, day=1)
            product = Product.objects.get(
                type_id=base_prod_type_id,
                name__iexact=key.replace(BASE_PRODUCT_FIELD_PREFIX, ""),
            )
            relevant_value = get_product_price(product, next_month).size
            if return_capacity_in_euros:
                relevant_value = get_product_price(product, next_month).price
            total += float(relevant_value) * quantity
        return total

    def calculate_capacity_used_by_the_current_subscriptions(
        self, product_type_id: str
    ):
        next_month = get_today() + relativedelta(months=1, day=1)
        current_subscriptions = get_active_subscriptions(next_month).filter(
            member_id=self.member_id, product__type_id=product_type_id
        )
        return sum(
            [subscription.get_used_capacity() for subscription in current_subscriptions]
        )

    def validate_pickup_location_capacity(self):
        base_prod_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)

        ordered_products_to_quantity_map = {}
        for key, quantity in self.cleaned_data.items():
            if not key.startswith(BASE_PRODUCT_FIELD_PREFIX):
                continue
            product = Product.objects.get(
                type_id=base_prod_type_id,
                name__iexact=key.replace(BASE_PRODUCT_FIELD_PREFIX, ""),
            )
            ordered_products_to_quantity_map[product] = quantity

        validate_pickup_location_capacity(
            form=self,
            pickup_location=self.get_pickup_location(),
            ordered_products_to_quantity_map=ordered_products_to_quantity_map,
            start_date=self.start_date,
            member_id=self.member_id,
        )

    def validate_total_capacity(self):
        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        free_capacity = get_free_product_capacity(
            product_type_id=base_product_type_id,
            reference_date=self.start_date,
        )
        ordered_capacity = self.calculate_capacity_used_by_the_ordered_products()
        currently_used_capacity = float(
            self.calculate_capacity_used_by_the_current_subscriptions(
                base_product_type_id
            )
        )

        if free_capacity < (ordered_capacity - currently_used_capacity):
            self.add_error(
                None,
                f"Die ausgewählte Ernteanteile sind größer als die verfügbare Kapazität! Verfügbar: {round(free_capacity, 2)}",
            )

    def validate_solidarity_price(self):
        solidarity_fields = self.build_solidarity_fields()
        ordered_solidarity_factor = float(
            solidarity_fields["solidarity_price_absolute"]
            if "solidarity_price_absolute" in solidarity_fields.keys()
            else solidarity_fields["solidarity_price"]
        )
        if ordered_solidarity_factor >= 0:
            return

        excess_solidarity = get_available_solidarity(self.start_date)

        ordered_capacity = self.calculate_capacity_used_by_the_ordered_products(True)
        solidarity_part_of_the_ordered_capacity = (
            ordered_capacity * -ordered_solidarity_factor
        )

        if solidarity_part_of_the_ordered_capacity > excess_solidarity:
            self.add_error(
                "solidarity_price_harvest_shares",
                "Der Solidartopf ist leider nicht ausreichend ausgefüllt.",
            )

    def is_valid(self):
        super().is_valid()

        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.get(
                "growing_period", get_current_growing_period()
            )

        self.start_date = max(self.start_date, self.growing_period.start_date)

        has_harvest_shares = self.has_harvest_shares()
        if self.require_at_least_one and not has_harvest_shares:
            self.add_error(
                None, f"Bitte wähle mindestens einen {self.product_type.name}!"
            )

        if has_harvest_shares:
            self.validate_harvest_shares_consent()
            if self.member_id:
                self.validate_pickup_location()
                self.validate_pickup_location_capacity()
            self.validate_total_capacity()
            self.validate_solidarity_price()

        self.validate_cannot_reduce_size()

        return len(self.errors) == 0

    def validate_cannot_reduce_size(self):
        if not self.should_validate_cannot_reduce_size():
            return

        subscriptions = get_active_subscriptions(self.start_date).filter(
            member__id=self.member_id
        )
        total_current_subscription_size = sum(
            [subscription.get_used_capacity() for subscription in subscriptions]
        )
        ordered_size = self.calculate_capacity_used_by_the_ordered_products()
        if ordered_size < total_current_subscription_size:
            self.add_error(
                None,
                _(
                    f"Während eine Vertrag läuft es ist nur erlaubt die Größe des Vertrags zu erhöhen. "
                    f"Deiner aktueller Vertrag für diese Periode entspricht Größe {total_current_subscription_size:.2f}. "
                    f"Deiner letzter Auswahl hier entsprach Größe {ordered_size:.2f}."
                ),
            )

    def should_validate_cannot_reduce_size(self):
        # Members cannot reduce the size of their subscriptions for the currently ongoing growing period.
        growing_period = get_current_growing_period(self.start_date)
        if not growing_period:
            return False
        if growing_period.start_date > get_today():
            return False

        subscriptions = Subscription.objects.filter(
            member__id=self.member_id, period=growing_period
        )
        return subscriptions.exists()


def validate_pickup_location_capacity(
    form, pickup_location, ordered_products_to_quantity_map, start_date, member_id
):
    member = None
    if member_id:
        member = Member.objects.get(id=member_id)

    if not PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
        pickup_location=pickup_location,
        ordered_products_to_quantity_map=ordered_products_to_quantity_map,
        already_registered_member=member,
        subscription_start=start_date,
    ):
        form.add_error("pickup_location", "Abholort ist voll")  # this is not displayed
        form.add_error(
            None,
            _("Dein Abholort ist leider voll. Bitte wähle einen anderen Abholort aus."),
        )


class AdditionalProductForm(forms.Form):
    sum_template = "wirgarten/member/additional_product_sum.html"

    def __init__(self, *args, **kwargs):
        self.is_admin = kwargs.pop("is_admin", False)
        self.member_id = kwargs.pop("member_id", None)
        initial = kwargs.get("initial", {})
        product_type_id = kwargs.pop(
            "product_type_id", initial.pop("product_type_id", None)
        )

        self.product_type = get_object_or_404(ProductType, id=product_type_id)

        self.intro_template = initial.pop("intro_template", None)
        self.outro_template = initial.pop("outro_template", None)

        self.field_prefix = self.product_type.id + "_"
        self.choose_growing_period = kwargs.pop("choose_growing_period", False)
        self.start_date = kwargs.pop(
            "start_date", initial.get("start_date", get_next_contract_start_date())
        )
        super(AdditionalProductForm, self).__init__(*args, **kwargs)

        self.consent_field_key = f"consent_{self.field_prefix}"
        products_queryset = Product.objects.filter(
            deleted=False, type=self.product_type
        )

        # Calculate prices for each product
        prices = {
            prod.id: get_product_price(prod, self.start_date).price
            for prod in products_queryset
        }

        # Sort products by their prices in ascending order
        sorted_products = sorted(products_queryset, key=lambda x: prices[x.id])

        # Create an OrderedDict to maintain the sorted order
        self.products = OrderedDict(
            (f"{self.field_prefix}{prod.name}", prod) for prod in sorted_products
        )

        self.n_columns = len(self.products)
        self.colspans = {
            self.consent_field_key: self.n_columns,
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

        if self.product_type.single_subscription_only:
            prod_name = [p for p in self.products.values() if p.base][0].name
            self.fields[self.field_prefix + prod_name] = forms.BooleanField(
                required=False,
                label=_(f"{prod_name} {self.product_type.name}"),
            )
        else:
            for k, v in self.products.items():
                self.fields[k] = forms.IntegerField(
                    required=False,
                    min_value=0,
                    initial=0,
                    label=_(
                        f"{k.replace(self.field_prefix, '')} {self.product_type.name}"
                    ),
                    help_text="""{:.2f} € inkl. MwSt / Monat""".format(prices[v.id]),
                )

        if self.product_type.contract_link:
            self.fields[self.consent_field_key] = forms.BooleanField(
                label=_(
                    "Ja, ich habe die Vertragsgrundsätze gelesen und stimme diesen zu."
                ),
                help_text=_(
                    f'<a href="{self.product_type.contract_link}" target="_blank">Vertragsgrundsätze - {self.product_type.name}</a>'
                ),
                required=False,
                initial=False,
            )

        if self.member_id:
            member = Member.objects.get(id=self.member_id)
            subs = get_active_subscriptions_grouped_by_product_type(member)

            today = get_today()
            next_delivery_date = get_next_delivery_date(today + relativedelta(days=2))
            # FIXME: the +2 days should be a configurable threshold.
            # FIXME: It takes some time to prepare the deliveries in which no changes are allowed
            next_month = today + relativedelta(months=1, day=1)

            def add_pickup_location_fields():
                # FIXME: no dummy, use the real diff value
                new_sub_dummy = Subscription(
                    quantity=1,
                    product=Product.objects.get(type=self.product_type, base=True),
                )
                subs[self.product_type.name] = (
                    [new_sub_dummy]
                    if self.product_type.name not in subs
                    else (subs[self.product_type.name] + [new_sub_dummy])
                )
                self.fields["pickup_location"] = PickupLocationChoiceField(
                    required=False,
                    label=_("Neuen Abholort auswählen"),
                    initial={"subs": subs},
                )
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

            capability = (
                get_active_pickup_location_capabilities()
                .filter(
                    pickup_location=member.pickup_location,
                    product_type__id=self.product_type.id,
                )
                .first()
            )
            if not capability:
                add_pickup_location_fields()

        self.prices = ",".join(
            map(
                lambda k: k + ":" + str(prices[self.products[k].id]),
                self.products.keys(),
            )
        )

    @transaction.atomic
    def save(
        self,
        member_id: str = None,
        mandate_ref: MandateReference = None,
        send_mail: bool = False,
    ):
        if not member_id:
            if not self.member_id:
                raise ValueError("member_id must be set")
            member_id = self.member_id
        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(member_id)

        now = get_now()

        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.pop(
                "growing_period", get_current_growing_period()
            )

        self.start_date = max(self.start_date, self.growing_period.start_date)

        existing_trial_end_date = cancel_subs_for_edit(
            member_id, self.start_date, self.product_type
        )

        self.subs = []
        for key, quantity in self.cleaned_data.items():
            if key.startswith(self.field_prefix) and quantity and quantity > 0:
                product = Product.objects.get(
                    type=self.product_type,
                    name=key.replace(self.field_prefix, ""),
                )
                notice_period_duration_in_months = None
                if get_parameter_value(Parameter.SUBSCRIPTION_AUTOMATIC_RENEWAL):
                    notice_period_duration_in_months = (
                        NoticePeriodManager.get_notice_period_duration(
                            self.product_type, self.growing_period
                        )
                    )
                self.subs.append(
                    Subscription(
                        member_id=member_id,
                        product=product,
                        quantity=quantity,
                        period=self.growing_period,
                        start_date=self.start_date,
                        end_date=self.growing_period.end_date,
                        mandate_ref=mandate_ref,
                        consent_ts=now if self.product_type.contract_link else None,
                        withdrawal_consent_ts=now,
                        trial_end_date_override=existing_trial_end_date,
                        notice_period_duration_in_months=notice_period_duration_in_months,
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

    def has_shares_selected(self):
        return self.get_total_ordered_quantity() > 0

    def get_total_ordered_quantity(self):
        total = 0.0
        for key, quantity in self.cleaned_data.items():
            if key.startswith(self.field_prefix) and (
                quantity is not None and quantity > 0
            ):
                product = Product.objects.get(
                    type_id=self.product_type.id,
                    name__iexact=key.replace(self.field_prefix, ""),
                )
                total += float(get_product_price(product).size)
        return total

    def validate_contract_signed(self):
        has_shares_selected = self.has_shares_selected()
        if (
            self.product_type.contract_link
            and has_shares_selected
            and not self.cleaned_data.get(self.consent_field_key, False)
        ):
            self.add_error(
                self.consent_field_key,
                f"Du musst den Vertragsgrundsätzen zustimmen um {self.product_type.name} zu zeichnen.",
            )

    def validate_pickup_location(self) -> bool:
        new_pickup_location = self.cleaned_data.get("pickup_location")
        has_shares_selected = self.has_shares_selected()
        if new_pickup_location or not has_shares_selected or not self.member_id:
            return True

        next_month = get_today() + relativedelta(months=1, day=1)
        latest_member_pickup_location = (
            MemberPickupLocation.objects.filter(
                member_id=self.member_id, valid_from__lte=next_month
            )
            .order_by("-valid_from")
            .first()
        )
        if not latest_member_pickup_location:
            self.add_error(None, _("Bitte wähle einen Abholort aus!"))
            return False

        ordered_products_to_quantity_map = {}
        for key, quantity in self.cleaned_data.items():
            if not key.startswith(self.field_prefix):
                continue
            product = Product.objects.get(
                type_id=self.product_type.id,
                name__iexact=key.replace(self.field_prefix, ""),
            )
            ordered_products_to_quantity_map[product] = quantity

        validate_pickup_location_capacity(
            form=self,
            pickup_location=latest_member_pickup_location.pickup_location,
            ordered_products_to_quantity_map=ordered_products_to_quantity_map,
            start_date=self.start_date,
            member_id=self.member_id,
        )

        return True

    def validate_has_base_product_subscription_at_same_growing_period(self):
        if not self.member_id or not self.has_shares_selected():
            return

        growing_period = getattr(
            self,
            "growing_period",
            self.cleaned_data.pop("growing_period", get_current_growing_period()),
        )
        if not Subscription.objects.filter(
            member__id=self.member_id,
            period=growing_period,
            product__type__id=get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE),
        ).exists():
            self.add_error(
                None,
                "Um Anteile von diese zusätzliche Produkte zu bestellen, "
                "musst du Anteile von der Basis-Produkt an der gleiche Vertragsperiode haben.",
            )

    def is_valid(self):
        result = super().is_valid()

        self.validate_contract_signed()
        self.validate_has_base_product_subscription_at_same_growing_period()
        if not self.validate_pickup_location():
            return False

        return result and len(self.errors) == 0


def cancel_subs_for_edit(
    member_id: str, start_date: date, product_type: ProductType
) -> date:
    """
    Cancels all subscriptions of the given product type for the given member and start date because they changed their contract.

    :param member_id: The member's id
    :param start_date: The start date of the new contract
    :param product_type: The product type of the subscriptions to cancel

    :return: The trial end date of the last subscription that was canceled
    """

    subs = get_active_subscriptions(start_date).filter(
        member_id=member_id, product__type=product_type
    )

    existing_trial_end_date = None

    for sub in subs:
        sub.end_date = start_date - relativedelta(days=1)
        existing_trial_end_date = sub.trial_end_date
        if (
            sub.start_date > sub.end_date
        ):  # change was done before the contract started, so we can delete the subscription
            sub.delete()
        else:
            sub.save()

    return existing_trial_end_date


class EditSubscriptionPriceForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.subscription_id = kwargs.pop("pk", None)
        self.subscription = Subscription.objects.get(id=self.subscription_id)
        super().__init__(*args, **kwargs)

        self.fields["new_price"] = forms.DecimalField(
            required=False,
            label=_("Neuer Preis"),
            localize=True,
            max_digits=6,
            decimal_places=2,
            min_value=0.0,
            initial=self.subscription.total_price,
            help_text="Leer lassen um den Preis zurückzusetzen (automatisch berechnen)",
        )

    def save(self):
        if self.cleaned_data["new_price"]:
            self.subscription.price_override = self.cleaned_data["new_price"]
            self.subscription.solidarity_price = 0.0
            self.subscription.solidarity_price_absolute = None
        else:
            self.subscription.price_override = None
        self.subscription.save()
        return self.subscription


class EditSubscriptionDatesForm(forms.Form):
    start_date = forms.DateField(widget=DateInput)
    end_date = forms.DateField(widget=DateInput)

    def __init__(self, *args, **kwargs):
        self.subscription_id = kwargs.pop("pk", None)
        self.subscription = Subscription.objects.get(id=self.subscription_id)
        super().__init__(*args, **kwargs)

    def get_initial_for_field(self, field, field_name):
        if field_name == "start_date":
            return self.subscription.start_date
        if field_name == "end_date":
            return self.subscription.end_date
        return super().get_initial_for_field(field, field_name)

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("start_date") > cleaned_data.get("end_date"):
            raise ValidationError("Das Anfangsdatum muss vor dem Endsdatum sein")

        return cleaned_data

    def save(self):
        self.subscription.start_date = self.cleaned_data["start_date"]
        self.subscription.end_date = self.cleaned_data["end_date"]
        self.subscription.save()
        return self.subscription
