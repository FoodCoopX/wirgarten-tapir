import datetime
import json
from typing import List

from dateutil.relativedelta import relativedelta
from django import forms
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.pickup_locations.services.pickup_location_active_filter import (
    PickupLocationActiveFilter,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    PickupLocation,
    Subscription,
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
)
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import get_today


def get_pickup_locations_map_data(
    pickup_locations, location_capabilities, cache: dict = None
):
    return json.dumps(
        {
            f"{pickup_location.id}": pickup_location_to_dict(
                location_capabilities, pickup_location, cache
            )
            for pickup_location in list(pickup_locations)
        },
    )


def build_capacity_dictionary_for_picking_mode_share(
    capa, next_month: datetime.date, cache: dict
):
    max_capa = capa["max_capacity"]
    current_capa = round(
        PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            pickup_location=PickupLocation.objects.get(id=capa["pickup_location_id"]),
            product_type=TapirCache.get_product_type_by_id(
                cache, capa["product_type_id"]
            ),
            reference_date=next_month,
            cache=cache,
        ),
        2,
    )

    next_month_capa = round(
        PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            pickup_location=PickupLocation.objects.get(id=capa["pickup_location_id"]),
            product_type=TapirCache.get_product_type_by_id(
                cache, capa["product_type_id"]
            ),
            reference_date=next_month,
            cache=cache,
        ),
        2,
    )

    capa_diff = round(next_month_capa - current_capa, 2)
    return {
        "name": capa["product_type__name"],
        "icon": capa["product_type__icon_link"],
        "max_capacity": max_capa,
        "current_capacity": current_capa,
        "next_capacity_diff": (
            f"{'+' if capa_diff > 0 else ''} {capa_diff}" if capa_diff != 0 else ""
        ),
        "capacity_percent": (current_capa / max_capa) if max_capa else None,
    }


def pickup_location_to_dict(
    location_capabilities, pickup_location: PickupLocation, cache: dict = None
):
    next_delivery_date = get_next_delivery_date(cache=cache)
    next_month = next_delivery_date + relativedelta(day=1, months=1)
    if cache is None:
        cache = {}

    capabilities_for_pickup_location = [
        build_capacity_dictionary_for_picking_mode_share(
            capa=capa,
            next_month=next_month,
            cache=cache,
        )
        for capa in location_capabilities
        if capa["pickup_location_id"] == pickup_location.id
    ]
    capabilities_for_pickup_location = list(
        filter(
            lambda capability: capability is not None,
            capabilities_for_pickup_location,
        )
    )

    return {
        "id": pickup_location.id,
        "name": pickup_location.name,
        "opening_times": pickup_location.opening_times_html,
        "street": pickup_location.street,
        "city": f"{pickup_location.postcode} {pickup_location.city}",
        "capabilities": capabilities_for_pickup_location,
        "members": get_active_subscriptions(next_delivery_date, cache)
        .filter(
            member_id__in=MemberPickupLocationGetter.get_members_ids_at_pickup_location(
                pickup_location=pickup_location,
                reference_date=next_delivery_date,
                cache=cache,
            ),
        )
        .values("member_id")
        .distinct()
        .count(),
        "location_route": getattr(pickup_location.location_route, "name", ""),
        "coords": (
            f"{pickup_location.latitude},{pickup_location.longitude}"
            if pickup_location.latitude is not None
            and pickup_location.longitude is not None
            else None
        ),
        "is_home_delivery": pickup_location.is_home_delivery,
        "route_info": pickup_location.route_info,
        "start_date": (
            pickup_location.start_date.isoformat()
            if pickup_location.start_date
            else None
        ),
        "end_date": (
            pickup_location.end_date.isoformat() if pickup_location.end_date else None
        ),
    }


class PickupLocationWidget(forms.Select):
    template_name = "wirgarten/pickup_location/pickup_location.widget.html"

    def __init__(
        self,
        pickup_locations,
        location_capabilities,
        selected_product_types,
        initial,
        cache: dict,
        *args,
        **kwargs,
    ):
        super(PickupLocationWidget, self).__init__(*args, **kwargs)

        self.attrs["selected_product_types"] = selected_product_types
        self.attrs["data"] = get_pickup_locations_map_data(
            pickup_locations, location_capabilities, cache
        )
        self.attrs["initial"] = initial


class PickupLocationChoiceField(forms.ModelChoiceField):
    def __init__(self, **kwargs):
        initial = kwargs.pop("initial", {"subs": {}})
        self.cache = kwargs.pop("cache", {})
        next_month = get_today(cache=self.cache) + relativedelta(months=1, day=1)
        reference_date = kwargs.pop("reference_date", next_month)
        member = kwargs.pop("member", None)

        location_capabilities = get_active_pickup_location_capabilities(
            reference_date=reference_date, cache=self.cache
        ).values(
            "product_type__name",
            "max_capacity",
            "product_type_id",
            "pickup_location_id",
            "product_type__icon_link",
        )

        selected_product_types = {
            product_type_name: sum(
                map(
                    lambda subscription: (
                        float(
                            get_product_price(
                                subscription.product,
                                cache=self.cache,
                            ).size
                        )
                        * (subscription.quantity or 0)
                    ),
                    subscriptions,
                )
            )
            for product_type_name, subscriptions in initial["subs"].items()
            if subscriptions
            and subscriptions[0].product.type.delivery_cycle != NO_DELIVERY[0]
        }
        selected_product_types = {
            product_type_name: capacity_usage
            for product_type_name, capacity_usage in selected_product_types.items()
            if capacity_usage > 0
        }

        subscriptions = []
        for temp in initial["subs"].values():
            subscriptions.extend(temp)
        possible_locations = self.get_possible_locations(
            subscriptions, reference_date, member
        )

        super().__init__(
            queryset=possible_locations,
            initial=0,
            widget=PickupLocationWidget(
                pickup_locations=possible_locations,
                location_capabilities=location_capabilities,
                selected_product_types=selected_product_types,
                initial=initial.get("initial", None),
                cache=self.cache,
            ),
            **kwargs,
        )

    def get_possible_locations(
        self,
        subscriptions: List[Subscription],
        reference_date: datetime.date,
        member: Member | None,
    ):
        possible_location_ids = []

        for pickup_location in PickupLocation.objects.all():
            ordered_products_to_quantity_map = {
                subscription.product: subscription.quantity
                for subscription in subscriptions
            }
            if PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=ordered_products_to_quantity_map,
                already_registered_member=member,
                subscription_start=reference_date,
                cache=self.cache,
            ):
                possible_location_ids.append(pickup_location.id)
        return PickupLocationActiveFilter.get_active_at_date(
            PickupLocation.objects.filter(id__in=possible_location_ids),
            reference_date,
        )

    def label_from_instance(self, obj):
        return f"<strong>{obj.name}</strong><br/><small><span>{obj.street}, {obj.postcode} {obj.city}</span><br />{obj.opening_times_html_small}</small>"


class PickupLocationChoiceForm(forms.Form):
    intro_template = "registration/steps/pickup_location.intro.html"
    intro_text_skip_hr = True

    def __init__(self, *args, **kwargs):
        member = kwargs.pop("member", None)
        self.cache = kwargs.pop("cache", {})
        super().__init__(*args, **kwargs)

        self.fields["pickup_location"] = PickupLocationChoiceField(
            label=_("Abholort"),
            initial=kwargs["initial"],
            member=member,
            cache=self.cache,
        )

        self.intro_templates = [
            self.intro_template.replace(
                "steps/",
                f"steps/{get_parameter_value(ParameterKeys.ORGANISATION_THEME)}/",
            ),
            self.intro_template,
        ]

    def is_valid(self):
        super().is_valid()

        if (
            "pickup_location" not in self.cleaned_data
            or not self.cleaned_data["pickup_location"]
        ):
            self.add_error(
                "pickup_location",
                _("Bitte wähle deinen gewünschten Abholort aus!"),
            )

        return len(self.errors) == 0
