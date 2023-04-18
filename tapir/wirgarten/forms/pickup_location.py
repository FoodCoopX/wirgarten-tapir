import json
from django.utils.translation import gettext_lazy as _

from django import forms

from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import PickupLocation, Member
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_active_pickup_locations,
)
from tapir.wirgarten.service.products import get_active_product_types


def get_pickup_locations_map_data(pickup_locations, location_capabilities):
    return json.dumps(
        {
            f"{pl.id}": pickup_location_to_dict(location_capabilities, pl)
            for pl in list(pickup_locations)
        }
    )


def pickup_location_to_dict(location_capabilities, pickup_location):
    # FIXME: Icons should be configured with the ProductType ?
    PRODUCT_TYPE_ICONS = {
        "Ernteanteile": "/static/wirgarten/images/icons/Ernteanteil.svg",
        "Hühneranteile": "/static/wirgarten/images/icons/Huehneranteil.svg",
    }

    return {
        "id": pickup_location.id,
        "name": pickup_location.name,
        "street": pickup_location.street,
        "city": f"{pickup_location.postcode} {pickup_location.city}",
        "info": pickup_location.info.replace(", ", "<br/>"),
        "capabilities": list(
            map(
                lambda x: {
                    "name": x["product_type__name"],
                    "icon": PRODUCT_TYPE_ICONS.get(x["product_type__name"], "?"),
                },
                location_capabilities.filter(pickup_location=pickup_location).values(
                    "product_type__name"
                ),
            )
        ),
        # FIXME: member count should be filtered by active subscriptions
        "members": len(Member.objects.filter(pickup_location=pickup_location)),
        "coords": f"{pickup_location.coords_lon},{pickup_location.coords_lat}",
    }


class PickupLocationWidget(forms.Select):
    template_name = "wirgarten/pickup_location/pickup_location.widget.html"

    def __init__(
        self,
        pickup_locations,
        location_capabilities,
        selected_product_types,
        initial,
        *args,
        **kwargs,
    ):
        super(PickupLocationWidget, self).__init__(*args, **kwargs)

        print(selected_product_types)  # TODO remove
        self.attrs["selected_product_types"] = selected_product_types
        self.attrs["data"] = get_pickup_locations_map_data(
            pickup_locations, location_capabilities
        )
        self.attrs["initial"] = initial


class PickupLocationChoiceField(forms.ModelChoiceField):
    def __init__(self, **kwargs):
        initial = kwargs["initial"]

        location_capabilities = get_active_pickup_location_capabilities()
        pickup_locations = get_active_pickup_locations(location_capabilities)

        all_prod_types_with_delivery = map(
            lambda x: x["name"],
            get_active_product_types()
            .exclude(delivery_cycle=NO_DELIVERY)
            .values("name"),
        )
        selected_product_types = list(
            (
                pt
                for pt in initial["product_types"]
                if pt in all_prod_types_with_delivery
            )
        )

        possible_locations = pickup_locations
        for pt_name in selected_product_types:
            possible_locations = possible_locations.filter(
                id__in=location_capabilities.filter(product_type__name=pt_name).values(
                    "pickup_location__id"
                )
            )

        super(PickupLocationChoiceField, self).__init__(
            queryset=possible_locations,
            initial=0,
            widget=PickupLocationWidget(
                pickup_locations=pickup_locations,
                location_capabilities=location_capabilities,
                selected_product_types=selected_product_types,
                initial=initial.get("initial", None),
            ),
            label=kwargs["label"],
        )

    def label_from_instance(self, obj):
        info = obj.info
        info = info.replace(",", "<br/> • ")
        info = " • " + info
        return f"<strong>{obj.name}</strong>, <small>{obj.street}, {obj.postcode} {obj.city}<br/>{info}</small>"


class PickupLocationChoiceForm(forms.Form):
    intro_template = "wirgarten/registration/steps/pickup_location.intro.html"
    intro_text_skip_hr = True

    def __init__(self, *args, **kwargs):
        super(PickupLocationChoiceForm, self).__init__(*args, **kwargs)

        self.fields["pickup_location"] = PickupLocationChoiceField(
            label=_("Abholort"), **kwargs
        )

    def is_valid(self):
        super().is_valid()

        print(self.cleaned_data)

        if (
            "pickup_location" not in self.cleaned_data
            or not self.cleaned_data["pickup_location"]
        ):
            self.add_error(
                "pickup_location",
                _("Bitte wähle deinen gewünschten Abholort aus!"),
            )
        return len(self.errors) == 0


class PickupLocationEditForm(forms.Form):
    template_name = "wirgarten/pickup_location/pickup_location_edit.form.html"

    def __init__(self, *args, **kwargs):
        super(PickupLocationEditForm, self).__init__(*args)

        self.fields["coords"] = forms.CharField(
            label=_("Koordinaten"), help_text="z.B: 53.2731785,10.3741756"
        )
        self.fields["name"] = forms.CharField(label=_("Name"), required=True)
        self.fields["street"] = forms.CharField(
            label=("Straße & Hausnummer"), required=True
        )
        self.fields["postcode"] = forms.CharField(
            label=_("Postleitzahl"), required=True
        )
        self.fields["city"] = forms.CharField(label=_("Ort"), required=True)
        self.fields["info"] = forms.CharField(
            label=_("Infos zur Abholung (Öffnungszeiten, etc.)"),
            required=True,
            help_text="z.B.: mittwochs 15:30 Uhr bis donnerstags 12:00 Uhr, Zugang per Zahlencode jederzeit möglich",
        )

        self.product_types = list(
            get_active_product_types()
            .exclude(delivery_cycle=NO_DELIVERY[0])
            .order_by("name")
        )

        for pt in self.product_types:
            self.fields["pt_" + pt.id] = forms.BooleanField(
                label=_(pt.name), required=False
            )

        if "id" in kwargs:
            self.pickup_location = PickupLocation.objects.get(id=kwargs["id"])
            self.fields[
                "coords"
            ].initial = (
                f"{self.pickup_location.coords_lon},{self.pickup_location.coords_lat}"
            )
            self.fields["name"].initial = self.pickup_location.name
            self.fields["street"].initial = self.pickup_location.street
            self.fields["postcode"].initial = self.pickup_location.postcode
            self.fields["city"].initial = self.pickup_location.city
            self.fields["info"].initial = self.pickup_location.info

            for ptc in get_active_pickup_location_capabilities().filter(
                pickup_location=self.pickup_location
            ):
                key = "pt_" + ptc.product_type.id
                if key in self.fields:
                    self.fields[key].initial = True
