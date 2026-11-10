from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.views import generic

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_active_filter import (
    PickupLocationActiveFilter,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.pickup_location import (
    get_pickup_locations_map_data,
    pickup_location_to_dict,
)
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_active_pickup_location_capabilities
from tapir.wirgarten.service.products import get_active_product_types
from tapir.wirgarten.utils import get_today


class PickupLocationCfgView(PermissionRequiredMixin, generic.TemplateView):
    """
    This view lists all pickup locations and their capabilities.
    """

    template_name = "wirgarten/pickup_location/pickup_location_config.html"
    permission_required = Permission.Coop.VIEW

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        cache = {}

        pickup_locations = self.get_filtered_pickup_locations(cache=cache)

        capabilities = get_active_pickup_location_capabilities(cache=cache).values(
            "pickup_location_id",
            "product_type_id",
            "max_capacity",
            "product_type__name",
            "product_type__icon_link",
        )

        context["data"] = get_pickup_locations_map_data(
            pickup_locations=pickup_locations,
            location_capabilities=capabilities,
            cache=cache,
        )

        context["all_product_types"] = get_active_product_types(cache=cache).values(
            "name"
        )

        context["pickup_locations"] = list(
            map(
                lambda pickup_location: pickup_location_to_dict(
                    location_capabilities=capabilities,
                    pickup_location=pickup_location,
                    cache=cache,
                ),
                pickup_locations,
            )
        )

        context["enable_delivery_charge"] = get_parameter_value(
            key=ParameterKeys.DELIVERY_CHARGE_PER_PICKUP_LOCATION_ENABLED, cache=cache
        )

        request = self.request
        context["search"] = request.GET.get("search", "")
        context["show_ended"] = request.GET.get("show_ended") == "on"

        context["cache"] = cache

        return context

    def get_filtered_pickup_locations(self, cache: dict):
        request = self.request
        queryset = PickupLocation.objects.all().order_by("location_route__name", "name")

        search = request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(street__icontains=search)
                | Q(postcode__icontains=search)
                | Q(city__icontains=search)
            )

        if request.GET.get("show_ended") != "on":
            queryset = PickupLocationActiveFilter.get_not_ended_at_date(
                queryset, get_today(cache=cache)
            )

        return list(queryset)
