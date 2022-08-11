import json
from importlib.resources import _

from django import forms

from tapir.wirgarten.models import PickupLocation


class PickupLocationChoiceField(forms.ModelChoiceField):

    # TODO: additional products are only available at some pickup locations, so the corresponding query must be used depending on which products are selected
    def __init__(self, queryset=PickupLocation.objects.all(), **kwargs):
        super().__init__(queryset=queryset, **kwargs)

    def label_from_instance(self, obj):
        return """{pl.name}, {pl.street}, {pl.postcode} {pl.city} ({pl.info})""".format(
            pl=obj
        )


class PickupLocationForm(forms.Form):
    outro_template = "wirgarten/registration/steps/pickup_location.outro.html"

    def __init__(self, *args, **kwargs):
        super(PickupLocationForm, self).__init__(*args, **kwargs)
        self.fields["pickup_location"] = PickupLocationChoiceField(
            label=_("Abholort"), initial=0
        )

        self.coords = json.dumps(
            {
                pl.pk: """{pl.coords_lon},{pl.coords_lat}""".format(pl=pl)
                for pl in self.fields["pickup_location"].queryset
            }
        )
