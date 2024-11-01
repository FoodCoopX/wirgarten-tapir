from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse_lazy
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from tapir.wirgarten.constants import Permission
from tapir.wirgarten.forms.pickup_location import (
    get_pickup_locations_map_data,
    pickup_location_to_dict,
    PickupLocationEditForm,
)
from tapir.wirgarten.models import PickupLocation, PickupLocationCapability
from tapir.wirgarten.service.delivery import get_active_pickup_location_capabilities
from tapir.wirgarten.service.products import get_active_product_types
from tapir.wirgarten.views.modal import get_form_modal

PAGE_ROOT = reverse_lazy("wirgarten:pickup_locations")


class PickupLocationCfgView(PermissionRequiredMixin, generic.TemplateView):
    """
    This view lists all pickup locations and their capabilities.
    """

    template_name = "wirgarten/pickup_location/pickup_location_config.html"
    permission_required = Permission.Coop.VIEW

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        pickup_locations = list(PickupLocation.objects.all().order_by("name"))
        capabilities = get_active_pickup_location_capabilities().values(
            "pickup_location_id",
            "product_type_id",
            "max_capacity",
            "product_type__name",
            "product_type__icon_link",
        )
        context["data"] = get_pickup_locations_map_data(
            pickup_locations=pickup_locations,
            location_capabilities=capabilities,
        )
        context["all_product_types"] = get_active_product_types().values("name")
        context["pickup_locations"] = list(
            map(lambda x: pickup_location_to_dict(capabilities, x), pickup_locations)
        )

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
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:pickup_locations")
        + "?selected="
        + x.id,
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
        **kwargs
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
