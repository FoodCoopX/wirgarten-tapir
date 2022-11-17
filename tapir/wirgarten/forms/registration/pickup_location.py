import json
from importlib.resources import _

from django import forms

from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_active_pickup_locations,
)


class PickupLocationWidget(forms.Select):
    template_name = "wirgarten/widgets/pickup_location.widget.html"

    def __init__(
        self,
        pickup_locations,
        location_capabilities,
        selected_product_types,
        *args,
        **kwargs,
    ):
        super(PickupLocationWidget, self).__init__(*args, **kwargs)

        self.attrs["selected_product_types"] = selected_product_types
        self.attrs["data"] = json.dumps(
            {
                f"{pl.id}": {
                    "name": pl.name,
                    "street": pl.street,
                    "city": f"{pl.postcode} {pl.city}",
                    "info": pl.info,
                    "capabilities": list(
                        map(
                            lambda x: x["product_type__name"],
                            location_capabilities.filter(pickup_location=pl).values(
                                "product_type__name"
                            ),
                        )
                    ),
                    "coords": f"{pl.coords_lon},{pl.coords_lat}",
                }
                for pl in list(pickup_locations)
            }
        )


class PickupLocationChoiceField(forms.ModelChoiceField):
    def __init__(self, **kwargs):
        initial = kwargs["initial"]

        location_capabilities = get_active_pickup_location_capabilities()
        pickup_locations = get_active_pickup_locations(location_capabilities)

        selected_product_types = initial["product_types"]
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
            ),
        )

    def label_from_instance(self, obj):
        return f"{obj.name}, {obj.street}, {obj.postcode} {obj.city} ({obj.info})"


class PickupLocationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(PickupLocationForm, self).__init__(*args, **kwargs)

        self.fields["pickup_location"] = PickupLocationChoiceField(
            label=_("Abholort"), **kwargs
        )
