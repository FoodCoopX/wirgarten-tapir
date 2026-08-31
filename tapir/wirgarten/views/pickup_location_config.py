from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django_filters.views import FilterView
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.pickup_location import (
    get_pickup_locations_map_data,
    pickup_location_to_dict,
    PickupLocationEditForm,
)
from tapir.wirgarten.models import PickupLocation, PickupLocationCapability
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import get_active_pickup_location_capabilities
from tapir.wirgarten.service.products import get_active_product_types
from tapir.wirgarten.views.modal import get_form_modal
from tapir.wirgarten.views.pickup_location_filter import PickupLocationFilter

PAGE_ROOT = reverse_lazy("wirgarten:pickup_locations")


class _DisabledFilterset:
    """Stand-in that mimics the django-filter Filterset API just enough to
    make ``filter-list.html`` render the page without a filter card.

    Only used when the ``PICKUP_LOCATION_GROWING_PERIOD_ENABLED`` feature flag
    is off, so the page keeps its pre-filter behaviour exactly.
    """

    qs = None
    form = None


class PickupLocationCfgView(PermissionRequiredMixin, FilterView):
    """
    This view lists all pickup locations and their capabilities.
    """

    template_name = "wirgarten/pickup_location/pickup_location_config.html"
    permission_required = Permission.Coop.VIEW
    model = PickupLocation
    filterset_class = PickupLocationFilter
    paginate_by = 20

    _LEGACY_TEMPLATE = "wirgarten/pickup_location/pickup_location_config_legacy.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self._enable_growing_period_filter: bool | None = None

    def _is_growing_period_filter_enabled(self) -> bool:
        if self._enable_growing_period_filter is None:
            self._enable_growing_period_filter = bool(
                get_parameter_value(
                    key=ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED,
                    cache=self.cache,
                )
            )
        return self._enable_growing_period_filter

    def get_queryset(self):
        return PickupLocation.objects.all().order_by("location_route__name", "name")

    def get_filterset_kwargs(self, filterset_class):
        kwargs = super().get_filterset_kwargs(filterset_class)
        kwargs["cache"] = self.cache
        return kwargs

    def get_template_names(self):
        if self._is_growing_period_filter_enabled():
            return [self.template_name]
        return [self._LEGACY_TEMPLATE]

    def get(self, request, *args, **kwargs):
        if not self._is_growing_period_filter_enabled():
            # Feature off: behave like the original TemplateView – no filter,
            # no pagination, no filter card on the right. The legacy template
            # preserves the original 2-column (table | map) layout.
            self.filterset = _DisabledFilterset()
            self.object_list = self.get_queryset()
            context = self.get_context_data(
                filter=self.filterset, object_list=self.object_list
            )
            return self.render_to_response(context)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        cache = self.cache

        page_pls = list(context["object_list"])

        capabilities = get_active_pickup_location_capabilities(cache=cache).values(
            "pickup_location_id",
            "product_type_id",
            "max_capacity",
            "product_type__name",
            "product_type__icon_link",
        )

        context["data"] = get_pickup_locations_map_data(
            pickup_locations=self.object_list,
            location_capabilities=capabilities,
            cache=cache,
        )

        context["all_product_types"] = get_active_product_types(cache=cache).values(
            "name"
        )

        enable_growing_period_filter = self._is_growing_period_filter_enabled()

        # Build a {pickup_location_id: [short_label, ...]} map so the admin
        # table can show which GrowingPeriods each PL is linked to.
        growing_periods_by_pl: dict[str, list[str]] = {}
        if enable_growing_period_filter:
            from tapir.wirgarten.models import PickupLocationGrowingPeriod

            for link in PickupLocationGrowingPeriod.objects.select_related(
                "growing_period"
            ).order_by("growing_period__start_date"):
                growing_periods_by_pl.setdefault(link.pickup_location_id, []).append(
                    link.growing_period.start_date.strftime("%-d.%-m.%Y")
                )

        context["pickup_locations"] = list(
            map(
                lambda pickup_location: {
                    **pickup_location_to_dict(
                        location_capabilities=capabilities,
                        pickup_location=pickup_location,
                        cache=cache,
                    ),
                    "growing_periods": growing_periods_by_pl.get(
                        pickup_location.id, []
                    ),
                },
                page_pls,
            )
        )

        context["enable_delivery_charge"] = get_parameter_value(
            key=ParameterKeys.DELIVERY_CHARGE_PER_PICKUP_LOCATION_ENABLED, cache=cache
        )

        context["enable_growing_period_filter"] = enable_growing_period_filter

        # Enable the 3-column layout (table | map | filter) in filter-list.html.
        context["secondary_panel"] = bool(enable_growing_period_filter)

        return context


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def get_pickup_location_add_form(request, **kwargs):
    """
    This view handles the admin modal form for adding a new pickup location.
    """

    return get_form_modal(
        request=request,
        form_class=PickupLocationEditForm,
        handler=lambda x: x.save(),
        redirect_url_resolver=lambda x: (
            reverse_lazy("wirgarten:pickup_locations") + "?selected=" + x.id
        ),
    )


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def get_pickup_location_edit_form(request, **kwargs):
    """
    This view handles the admin modal form for editing a pickup location.
    """
    return get_form_modal(
        request=request,
        form_class=PickupLocationEditForm,
        handler=lambda x: x.save(),
        redirect_url_resolver=lambda x: PAGE_ROOT + "?selected=" + x.id,
        **kwargs,
    )


@require_http_methods(["GET"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def delete_pickup_location(request, **kwargs):
    """
    This view deletes a pickup location.
    """
    try:
        pl = PickupLocation.objects.get(id=kwargs["id"])
        PickupLocationCapability.objects.filter(pickup_location=pl).delete()
        pl.delete()
        return HttpResponseRedirect(PAGE_ROOT + "?" + request.environ["QUERY_STRING"])
    except PickupLocation.DoesNotExist:
        return HttpResponse(status=404)
