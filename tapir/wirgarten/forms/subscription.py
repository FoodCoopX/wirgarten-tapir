from collections import OrderedDict
from datetime import date
from math import floor, ceil
from typing import Dict

from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.config import SOLIDARITY_UNIT_PERCENT, SOLIDARITY_UNIT_ABSOLUTE
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.solidarity_validator import SolidarityValidator
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.forms import DateInput
from tapir.utils.services.tapir_cache import TapirCache
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
from tapir.wirgarten.parameter_keys import ParameterKeys
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
        self.cache = kwargs.pop("cache", {})

        self.start_date = kwargs.pop(
            "start_date",
            initial.get("start_date", get_next_contract_start_date(cache=self.cache)),
        )
        self.intro_templates = initial.pop("intro_templates", None)
        self.outro_templates = initial.pop("outro_templates", None)

        if initial and not self.choose_growing_period:
            next_growing_period = get_next_growing_period(cache=self.cache)
            self.choose_growing_period = (
                next_growing_period
                and (next_growing_period.start_date - get_today(cache=self.cache)).days
                <= 61
            )

        super().__init__(*args, **kwargs)

        base_product_type = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        )
        harvest_share_products = Product.objects.filter(
            deleted=False, type=base_product_type
        )
        for p in harvest_share_products:
            price = get_product_price(p, cache=self.cache)
            if price and price.valid_from > self.start_date:
                harvest_share_products = harvest_share_products.exclude(id=p.id)

        self.n_columns = max(2, len(harvest_share_products))

        prices = {
            prod.id: get_product_price(prod, self.start_date, cache=self.cache).price
            for prod in harvest_share_products
        }

        harvest_share_products = sorted(
            harvest_share_products, key=lambda x: prices[x.id]
        )

        self.product_type = base_product_type
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

        self.field_order = list(self.products.keys()) + ["solidarity_price_choice"]
        self.colspans = {
            "growing_period": self.n_columns,
            "solidarity_price_choice": floor(self.n_columns / 2),
            "solidarity_price_custom": ceil(self.n_columns / 2),
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
                solidarity_total = f"{SolidarityValidator.get_solidarity_excess(reference_date=start_date, cache=self.cache)}".replace(
                    ",", "."
                )
                self.solidarity_total.append(solidarity_total)

                free_capacity = f"{get_free_product_capacity(harvest_share_products[0].type.id, start_date, cache=self.cache)}".replace(
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
            self.growing_period = get_current_growing_period(
                self.start_date, cache=self.cache
            )

            self.solidarity_total = [
                f"{SolidarityValidator.get_solidarity_excess(reference_date=max(self.growing_period.start_date, self.start_date), cache=self.cache)}".replace(
                    ",", "."
                )
            ]

            self.free_capacity = [
                f"{get_free_product_capacity(harvest_share_products[0].type.id, max(self.growing_period.start_date, self.start_date), cache=self.cache)}".replace(
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
                    label=prod_field.name,
                    help_text="""{:.2f} € inkl. MwSt / Monat""".format(
                        prices[prod_field.id]
                    ),
                )
            )

        solidarity_choices = (
            SolidarityValidator.get_solidarity_dropdown_value_as_sorted_tuples(
                cache=self.cache
            )
        )
        self.fields["solidarity_price_choice"] = forms.ChoiceField(
            required=False,
            label=_("Solidarbeitrag²"),
            choices=solidarity_choices,
        )
        solidarity_price_custom_field = forms.DecimalField(
            required=False,
            label=_("Solidarbeitrag² (personalisierter Beitrag)"),
        )
        if (
            get_parameter_value(ParameterKeys.SOLIDARITY_UNIT)
            == SOLIDARITY_UNIT_PERCENT
        ):
            solidarity_price_custom_field.help_text = _(
                "Bitte ein Prozentzahl eingeben. Beispiel: '5' eingeben um 5% extra beizutragen."
            )
        self.fields["solidarity_price_custom"] = solidarity_price_custom_field

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
                member, self.start_date, cache=self.cache
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
                        "solidarity_price_percentage": sub.solidarity_price_percentage,
                        "solidarity_price_absolute": (
                            float(sub.solidarity_price_absolute)
                            if sub.solidarity_price_absolute
                            else None
                        ),
                    }

                self.current_used_capacity = get_total_price_for_subs(
                    subs[self.product_type.name], cache=self.cache
                )
                if len(sub_variants) > 0:
                    solidarity_key = "solidarity_price_percentage"
                    if (
                        get_parameter_value(
                            ParameterKeys.SOLIDARITY_UNIT, cache=self.cache
                        )
                        == SOLIDARITY_UNIT_ABSOLUTE
                    ):
                        solidarity_key = "solidarity_price_absolute"
                    solidarity_value = list(sub_variants.values())[0][solidarity_key]
                    dropdown_choices = (
                        SolidarityValidator.get_solidarity_dropdown_values(
                            cache=self.cache
                        ).keys()
                    )
                    for key, field in self.fields.items():
                        if (
                            key.startswith(BASE_PRODUCT_FIELD_PREFIX)
                            and key.replace(BASE_PRODUCT_FIELD_PREFIX, "")
                            in sub_variants
                        ):
                            field.initial = sub_variants[
                                key.replace(BASE_PRODUCT_FIELD_PREFIX, "")
                            ]["quantity"]
                        elif key == "solidarity_price_choice":
                            field.initial = (
                                solidarity_value
                                if solidarity_value in dropdown_choices
                                else "custom"
                            )
                        elif key == "solidarity_price_custom":
                            field.initial = (
                                solidarity_value
                                if solidarity_value not in dropdown_choices
                                else 0
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
                cache=self.cache,
            )

            today = get_today(self.cache)
            next_delivery_date = get_next_delivery_date(
                today + relativedelta(days=2), cache=self.cache
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

        if self.choose_growing_period:
            available_growing_periods = GrowingPeriod.objects.filter(
                end_date__gte=self.start_date,
            ).order_by("start_date")
        else:
            available_growing_periods = [self.growing_period]
        harvest_share_strings = []
        for growing_period in available_growing_periods:
            prices = {
                prod.id: get_product_price(
                    prod, max(self.start_date, growing_period.start_date)
                ).price
                for prod in harvest_share_products
            }
            harvest_share_strings.append(
                ",".join(
                    map(
                        lambda p: BASE_PRODUCT_FIELD_PREFIX
                        + p.name
                        + ":"
                        + str(prices[p.id]),
                        harvest_share_products,
                    )
                )
            )
        self.harvest_shares = ";".join(harvest_share_strings)
        self.solidarity_unit = get_parameter_value(
            ParameterKeys.SOLIDARITY_UNIT, cache=self.cache
        )

    @transaction.atomic
    def save(
        self,
        mandate_ref: MandateReference = None,
        member_id: str = None,
    ):
        member_id = member_id or self.member_id

        if not mandate_ref:
            mandate_ref = get_or_create_mandate_ref(member_id, cache=self.cache)
        now = get_now(cache=self.cache)

        self.subscriptions = []
        existing_trial_end_date = cancel_subs_for_edit(
            member_id, self.start_date, self.product_type, cache=self.cache
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

            notice_period_duration = None
            if get_parameter_value(
                ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=self.cache
            ):
                notice_period_duration = NoticePeriodManager.get_notice_period_duration(
                    self.product_type, self.growing_period, cache=self.cache
                )

            end_date = self.growing_period.end_date
            if not product.type.subscriptions_have_end_dates:
                end_date = None

            sub = Subscription.objects.create(
                member_id=member_id,
                product=product,
                period=self.growing_period,
                quantity=quantity,
                start_date=self.start_date,
                end_date=end_date,
                mandate_ref=mandate_ref,
                consent_ts=(
                    now
                    if self.product_type.contract_link
                    and self.cleaned_data["consent_harvest_shares"]
                    else None
                ),
                withdrawal_consent_ts=now,
                trial_disabled=not get_parameter_value(
                    ParameterKeys.TRIAL_PERIOD_ENABLED, cache=self.cache
                ),
                trial_end_date_override=existing_trial_end_date,
                **self.build_solidarity_fields(),
                notice_period_duration=notice_period_duration,
            )

            self.subscriptions.append(sub)

        TapirCache.clear_category(cache=self.cache, category="subscriptions")
        member = Member.objects.get(id=member_id)
        member.sepa_consent = now
        member.save(cache=self.cache)

        new_pickup_location = self.cleaned_data.get("pickup_location")
        if new_pickup_location:
            change_date = self.cleaned_data.get("pickup_location_change_date")
            change_pickup_location(member_id, new_pickup_location, change_date)

    def build_solidarity_fields(self):
        value = self.cleaned_data["solidarity_price_choice"]
        if value == "custom":
            value = self.cleaned_data["solidarity_price_custom"]

        if (
            get_parameter_value(ParameterKeys.SOLIDARITY_UNIT)
            == SOLIDARITY_UNIT_PERCENT
        ):
            return {
                "solidarity_price_percentage": float(value) / 100,
                "solidarity_price_absolute": None,
            }
        return {
            "solidarity_price_percentage": None,
            "solidarity_price_absolute": float(value),
        }

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
            raise ValidationError(
                {
                    "consent_harvest_shares": _(
                        f"Du musst den Vertragsgrundsätzen zustimmen um {self.product_type.name} zu zeichnen."
                    )
                }
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

        next_month = get_today(cache=self.cache) + relativedelta(months=1, day=1)
        return (
            member_pickup_locations.filter(valid_from__lte=next_month)
            .order_by("-valid_from")
            .first()
            .pickup_location
        )

    def clean(self):
        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.get(
                "growing_period", get_current_growing_period(cache=self.cache)
            )

        self.start_date = max(self.start_date, self.growing_period.start_date)

        has_harvest_shares = self.has_harvest_shares()
        if self.require_at_least_one and not has_harvest_shares:
            self.add_error(
                None, f"Bitte wähle mindestens einen {self.product_type.name}!"
            )

        product_type_id = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        ).id
        if has_harvest_shares:
            self.validate_harvest_shares_consent()
            if self.member_id:
                self.validate_pickup_location()
                SubscriptionChangeValidator.validate_pickup_location_capacity(
                    pickup_location=self.get_pickup_location(),
                    form=self,
                    field_prefix=BASE_PRODUCT_FIELD_PREFIX,
                    subscription_start_date=self.start_date,
                    member=Member.objects.get(id=self.member_id),
                    cache=self.cache,
                )
            SolidarityValidator.validate_solidarity_price(
                form=self,
                start_date=self.start_date,
                field_prefix=BASE_PRODUCT_FIELD_PREFIX,
                cache=self.cache,
            )
            SubscriptionChangeValidator.validate_total_capacity(
                form=self,
                field_prefix=BASE_PRODUCT_FIELD_PREFIX,
                product_type_id=product_type_id,
                member_id=self.member_id,
                subscription_start_date=self.start_date,
                cache=self.cache,
            )

        SubscriptionChangeValidator.validate_cannot_reduce_size(
            logged_in_user_is_admin=self.is_admin,
            subscription_start_date=self.start_date,
            member_id=self.member_id,
            form=self,
            field_prefix=BASE_PRODUCT_FIELD_PREFIX,
            product_type_id=product_type_id,
            cache=self.cache,
        )

        SubscriptionChangeValidator.validate_must_be_subscribed_to(
            form=self,
            field_prefix=BASE_PRODUCT_FIELD_PREFIX,
            product_type=self.product_type,
            cache=self.cache,
        )

        SubscriptionChangeValidator.validate_single_subscription(
            form=self,
            field_prefix=BASE_PRODUCT_FIELD_PREFIX,
            product_type=self.product_type,
        )

        SubscriptionChangeValidator.validate_soliprice_change(
            form=self,
            field_prefix=BASE_PRODUCT_FIELD_PREFIX,
            member_id=self.member_id,
            subscription_start_date=self.start_date,
            logged_in_user_is_admin=self.is_admin,
            cache=self.cache,
        )

        if self.member_id:
            SubscriptionChangeValidator.validate_at_least_one_change(
                form=self,
                field_prefix=BASE_PRODUCT_FIELD_PREFIX,
                member_id=self.member_id,
                subscription_start_date=self.start_date,
                cache=self.cache,
            )

        return super().clean()


class AdditionalProductForm(forms.Form):
    sum_template = "wirgarten/member/additional_product_sum.html"

    def __init__(self, *args, **kwargs):
        self.is_admin = kwargs.pop("is_admin", False)
        self.member_id = kwargs.pop("member_id", None)
        initial = kwargs.get("initial", {})
        self.cache = kwargs.pop("cache", {})
        product_type_id = kwargs.pop(
            "product_type_id", initial.pop("product_type_id", None)
        )

        self.product_type = get_object_or_404(ProductType, id=product_type_id)

        self.intro_templates = initial.pop("intro_templates", None)
        self.outro_templates = initial.pop("outro_templates", None)

        self.field_prefix = self.product_type.id + "_"
        self.choose_growing_period = kwargs.pop("choose_growing_period", False)

        self.start_date = kwargs.pop(
            "start_date",
            initial.get("start_date", get_next_contract_start_date(cache=self.cache)),
        )
        super().__init__(*args, **kwargs)

        self.consent_field_key = f"consent_{self.field_prefix}"
        products_queryset = Product.objects.filter(
            deleted=False, type=self.product_type
        )

        # Calculate prices for each product
        prices = {
            prod.id: get_product_price(prod, self.start_date, cache=self.cache).price
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
                    f"{get_free_product_capacity(self.product_type.id, max(period.start_date, self.start_date), cache=self.cache)}".replace(
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
            self.growing_period = get_current_growing_period(
                self.start_date, cache=self.cache
            )
            self.free_capacity = [
                f"{get_free_product_capacity(self.product_type.id, max(self.growing_period.start_date, self.start_date), cache=self.cache)}".replace(
                    ",", "."
                )
            ]

        if self.product_type.single_subscription_only:
            for field_key, product in self.products.items():
                self.fields[field_key] = forms.BooleanField(
                    required=False,
                    initial=False,
                    label=product.name,
                    help_text="""{:.2f} € inkl. MwSt / Monat""".format(
                        prices[product.id]
                    ),
                )
        else:
            for field_key, product in self.products.items():
                self.fields[field_key] = forms.IntegerField(
                    required=False,
                    min_value=0,
                    initial=0,
                    label=product.name,
                    help_text="""{:.2f} € inkl. MwSt / Monat""".format(
                        prices[product.id]
                    ),
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

            for field_key, product in self.products.items():
                relevant_subscription = None
                for subscription in subs[self.product_type.name]:
                    if subscription.product_id == product.id:
                        relevant_subscription = subscription

                if relevant_subscription is None:
                    continue

                if self.product_type.single_subscription_only:
                    self.fields[field_key].initial = relevant_subscription.quantity > 0
                else:
                    self.fields[field_key].initial = relevant_subscription.quantity

            today = get_today(cache=self.cache)
            next_delivery_date = get_next_delivery_date(
                today + relativedelta(days=2), cache=self.cache
            )
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
                    cache=self.cache,
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
                get_active_pickup_location_capabilities(cache=self.cache)
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
        now = get_now(cache=self.cache)

        if not hasattr(self, "growing_period"):
            self.growing_period = self.cleaned_data.pop(
                "growing_period", get_current_growing_period(cache=self.cache)
            )

        self.start_date = max(self.start_date, self.growing_period.start_date)

        existing_trial_end_date = cancel_subs_for_edit(
            member_id, self.start_date, self.product_type, cache=self.cache
        )

        self.subscriptions = []
        for key, quantity in self.cleaned_data.items():
            if key.startswith(self.field_prefix) and quantity and quantity > 0:
                product = Product.objects.get(
                    type=self.product_type,
                    name=key.replace(self.field_prefix, ""),
                )
                notice_period_duration = None
                if get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=self.cache
                ):
                    notice_period_duration = (
                        NoticePeriodManager.get_notice_period_duration(
                            self.product_type, self.growing_period, cache=self.cache
                        )
                    )
                end_date = self.growing_period.end_date
                if not product.type.subscriptions_have_end_dates:
                    end_date = None
                self.subscriptions.append(
                    Subscription(
                        member_id=member_id,
                        product=product,
                        quantity=quantity,
                        period=self.growing_period,
                        start_date=self.start_date,
                        end_date=end_date,
                        mandate_ref=mandate_ref,
                        consent_ts=now if self.product_type.contract_link else None,
                        withdrawal_consent_ts=now,
                        trial_disabled=not get_parameter_value(
                            ParameterKeys.TRIAL_PERIOD_ENABLED, cache=self.cache
                        ),
                        trial_end_date_override=existing_trial_end_date,
                        notice_period_duration=notice_period_duration,
                    )
                )

        Subscription.objects.bulk_create(self.subscriptions)

        TapirCache.clear_category(cache=self.cache, category="subscriptions")
        Member.objects.filter(id=member_id).update(sepa_consent=get_now())

        new_pickup_location = self.cleaned_data.get("pickup_location")
        change_date = self.cleaned_data.get("pickup_location_change_date")
        if new_pickup_location:
            change_pickup_location(member_id, new_pickup_location, change_date)

        if send_mail:
            member = Member.objects.get(id=member_id)
            send_order_confirmation(member, self.subscriptions, cache=self.cache)

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
            raise ValidationError(
                {
                    self.consent_field_key: f"Du musst den Vertragsgrundsätzen zustimmen um {self.product_type.name} zu zeichnen."
                }
            )

    def get_pickup_location(self):
        pickup_location = self.cleaned_data.get("pickup_location")
        if pickup_location:
            return pickup_location

        member_pickup_locations = MemberPickupLocation.objects.filter(
            member_id=self.member_id
        )
        if member_pickup_locations.count() == 1:
            return member_pickup_locations.get().pickup_location

        next_month = get_today(cache=self.cache) + relativedelta(months=1, day=1)
        return (
            member_pickup_locations.filter(valid_from__lte=next_month)
            .order_by("-valid_from")
            .first()
            .pickup_location
        )

    def validate_pickup_location(self, cache: Dict):
        new_pickup_location = self.cleaned_data.get("pickup_location")
        has_shares_selected = self.has_shares_selected()
        if new_pickup_location or not has_shares_selected or not self.member_id:
            return

        next_month = get_today(cache=cache) + relativedelta(months=1, day=1)
        latest_member_pickup_location = (
            MemberPickupLocation.objects.filter(
                member_id=self.member_id, valid_from__lte=next_month
            )
            .order_by("-valid_from")
            .first()
        )
        if not latest_member_pickup_location:
            raise ValidationError(_("Bitte wähle einen Abholort aus!"))

    def validate_has_base_product_subscription_at_same_growing_period(
        self, cache: Dict
    ):
        if not self.member_id or not self.has_shares_selected():
            return

        growing_period = getattr(
            self,
            "growing_period",
            self.cleaned_data.pop(
                "growing_period", get_current_growing_period(cache=cache)
            ),
        )
        if not Subscription.objects.filter(
            member__id=self.member_id,
            period=growing_period,
            product__type=BaseProductTypeService.get_base_product_type(cache=cache),
        ).exists():
            self.add_error(
                None,
                "Um Anteile von diese zusätzliche Produkte zu bestellen, "
                "musst du Anteile von der Basis-Produkt an der gleiche Vertragsperiode haben.",
            )

    def clean(self):
        self.validate_contract_signed()

        if not get_parameter_value(
            ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            cache=self.cache,
        ):
            self.validate_has_base_product_subscription_at_same_growing_period(
                cache=self.cache
            )

        if self.member_id:
            self.validate_pickup_location(cache=self.cache)
            SubscriptionChangeValidator.validate_pickup_location_capacity(
                pickup_location=self.get_pickup_location(),
                form=self,
                field_prefix=BASE_PRODUCT_FIELD_PREFIX,
                subscription_start_date=self.start_date,
                member=Member.objects.get(id=self.member_id),
                cache=self.cache,
            )
            SubscriptionChangeValidator.validate_cannot_reduce_size(
                logged_in_user_is_admin=self.is_admin,
                subscription_start_date=self.start_date,
                member_id=self.member_id,
                form=self,
                field_prefix=self.field_prefix,
                product_type_id=self.product_type.id,
                cache=self.cache,
            )
        SubscriptionChangeValidator.validate_total_capacity(
            form=self,
            field_prefix=self.field_prefix,
            product_type_id=self.product_type.id,
            member_id=self.member_id,
            subscription_start_date=self.start_date,
            cache=self.cache,
        )

        SubscriptionChangeValidator.validate_must_be_subscribed_to(
            form=self,
            field_prefix=self.field_prefix,
            product_type=self.product_type,
            cache=self.cache,
        )

        SubscriptionChangeValidator.validate_single_subscription(
            form=self, field_prefix=self.field_prefix, product_type=self.product_type
        )

        return super().clean()


def cancel_subs_for_edit(
    member_id: str, start_date: date, product_type: ProductType, cache: Dict
) -> date:
    """
    Cancels all subscriptions of the given product type for the given member and start date because they changed their contract.

    :return: The trial end date of the last subscription that was canceled
    """

    subscriptions = get_active_subscriptions(start_date, cache=cache).filter(
        member_id=member_id, product__type=product_type
    )

    existing_trial_end_date = None

    for subscription in subscriptions:
        subscription.end_date = start_date - relativedelta(days=1)
        subscription.cancellation_ts = get_now(cache=cache)
        if (
            subscription.start_date > subscription.end_date
        ):  # change was done before the contract started, so we can delete the subscription
            subscription.delete()
        else:
            existing_trial_end_date = TrialPeriodManager.get_end_of_trial_period(
                subscription, cache=cache
            )
            subscription.save()

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
            self.subscription.solidarity_price_percentage = 0.0
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
