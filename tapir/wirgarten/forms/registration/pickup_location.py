import json
from importlib.resources import _

from django import forms

from tapir.wirgarten.models import PickupLocation, PickupLocationCapability


class PickupLocationChoiceField(forms.ModelChoiceField):

    # TODO: additional products are only available at some pickup locations, so the corresponding query must be used depending on which products are selected
    def __init__(self, queryset, **kwargs):
        super().__init__(queryset=queryset, **kwargs)

    def label_from_instance(self, obj):
        return """{pl.name}, {pl.street}, {pl.postcode} {pl.city} ({pl.info})""".format(
            pl=obj
        )


class PickupLocationForm(forms.Form):
    outro_template = "wirgarten/registration/steps/pickup_location.outro.html"

    def __init__(self, *args, **kwargs):
        super(PickupLocationForm, self).__init__(*args)

        initial = kwargs["initial"]
        filtered_pickup_locations = PickupLocation.objects.all()
        # TODO: fix product_type__name to __id, when wizard is rdy
        for product_type_id in initial["product_types"]:
            filtered_pickup_locations = filtered_pickup_locations.filter(
                id__in=PickupLocationCapability.objects.filter(
                    product_type__name=product_type_id
                ).values("pickup_location__id")
            )

        self.fields["pickup_location"] = PickupLocationChoiceField(
            label=_("Abholort"), initial=0, queryset=filtered_pickup_locations
        )

        self.coords = json.dumps(
            {
                f"{pl.id}": """{pl.coords_lon},{pl.coords_lat}""".format(pl=pl)
                for pl in self.fields["pickup_location"].queryset
            }
        )
