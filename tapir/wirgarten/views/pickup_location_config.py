from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
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
    @transaction.atomic
    def create_pickup_location(form):
        coords = form.cleaned_data["coords"].split(",")
        lon = coords[0].strip()
        lat = coords[1].strip()

        pl = PickupLocation.objects.create(
            name=form.cleaned_data["name"],
            street=form.cleaned_data["street"],
            postcode=form.cleaned_data["postcode"],
            city=form.cleaned_data["city"],
            info=form.cleaned_data["info"],
            coords_lon=lon,
            coords_lat=lat,
        )

        update_pickup_location_capabilities(form, pl)

        return pl

    return get_form_modal(
        request=request,
        form=PickupLocationEditForm,
        handler=lambda form: create_pickup_location(form),
        redirect_url_resolver=lambda x: reverse_lazy("wirgarten:pickup_locations")
        + "?selected="
        + x.id,
    )


def update_pickup_location_capabilities(form, pl):
    capabilities = list(
        map(
            lambda x: x["product_type__id"],
            PickupLocationCapability.objects.filter(pickup_location=pl).values(
                "product_type__id"
            ),
        )
    )
    for pt in form.product_types:
        if pt not in capabilities:  # doesn't exist yet
            if form.cleaned_data["pt_" + pt]:  # is selected
                # --> create
                PickupLocationCapability.objects.create(
                    pickup_location=pl,
                    product_type_id=pt,
                    max_capacity=form.cleaned_data.get("pt_capa_" + pt, None),
                )
        else:
            if not form.cleaned_data["pt_" + pt]:  # exists & is not selected
                # --> delete
                PickupLocationCapability.objects.get(
                    pickup_location=pl, product_type_id=pt
                ).delete()
            else:
                # --> update
                plc = PickupLocationCapability.objects.get(
                    pickup_location=pl, product_type_id=pt
                )
                plc.max_capacity = form.cleaned_data.get("pt_capa_" + pt, None)
                plc.save()


@require_http_methods(["GET", "POST"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def get_pickup_location_edit_form(request, **kwargs):
    @transaction.atomic
    def update_pickup_location(form):
        pl = form.pickup_location
        coords = form.cleaned_data["coords"].split(",")

        pl.coords_lon = coords[0].strip()
        pl.coords_lat = coords[1].strip()

        pl.name = form.cleaned_data["name"]
        pl.street = form.cleaned_data["street"]
        pl.postcode = form.cleaned_data["postcode"]
        pl.city = form.cleaned_data["city"]
        pl.info = form.cleaned_data["info"]

        pl.save()

        update_pickup_location_capabilities(form, pl)

        return pl

    return get_form_modal(
        request=request,
        form=PickupLocationEditForm,
        handler=update_pickup_location,
        redirect_url_resolver=lambda x: PAGE_ROOT + "?selected=" + x.id,
        **kwargs
    )


@require_http_methods(["GET"])
@permission_required(Permission.Coop.MANAGE)
@csrf_protect
def delete_pickup_location(request, **kwargs):
    try:
        pl = PickupLocation.objects.get(id=kwargs["id"])
        PickupLocationCapability.objects.filter(pickup_location=pl).delete()
        pl.delete()
        return HttpResponseRedirect(PAGE_ROOT + "?" + request.environ["QUERY_STRING"])
    except PickupLocation.DoesNotExist:
        return HttpResponse(status=404)
