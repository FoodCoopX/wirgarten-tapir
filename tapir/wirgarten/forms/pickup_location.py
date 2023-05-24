import json
from datetime import date, datetime
from math import ceil

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Subquery, OuterRef, Sum, DecimalField
from django.utils.translation import gettext_lazy as _

from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    PickupLocation,
    MemberPickupLocation,
    ProductPrice,
    Product,
    ProductType,
    PickupLocationCapability,
    PickupLocationOpeningTime,
)
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
)
from tapir.wirgarten.service.products import (
    get_active_product_types,
    get_future_subscriptions,
    get_product_price,
)


def get_pickup_locations_map_data(pickup_locations, location_capabilities):
    return json.dumps(
        {
            f"{pl.id}": pickup_location_to_dict(location_capabilities, pl)
            for pl in list(pickup_locations)
        }
    )


def get_current_capacity(capability):
    current_date = date.today()

    latest_pickup_locations = MemberPickupLocation.objects.filter(
        member=OuterRef("member"),
        valid_from__lte=current_date,
        pickup_location_id=capability["pickup_location_id"],
    ).order_by("-valid_from")

    active_subscriptions = get_future_subscriptions().filter(
        member_id=Subquery(latest_pickup_locations.values("member_id")[:1]),
        product__type_id=capability["product_type_id"],
    )

    # Get the most recent valid price for each product
    latest_product_prices = ProductPrice.objects.filter(
        product=OuterRef("product"), valid_from__lte=current_date
    ).order_by("-valid_from")

    # Annotate these subscriptions with their total price (without solidarity price)
    # and sum these prices
    total_price = active_subscriptions.annotate(
        latest_price=Subquery(
            latest_product_prices.values("price")[:1],
            output_field=DecimalField(decimal_places=2),
        )
    ).aggregate(total_price=Sum("latest_price"))["total_price"]

    return float(total_price) if total_price else 0


def pickup_location_to_dict(location_capabilities, pickup_location):
    # FIXME: Icons should be configured with the ProductType ?
    PRODUCT_TYPE_ICONS = {
        "Ernteanteile": "/static/wirgarten/images/icons/Ernteanteil.svg",
        "Hühneranteile": "/static/wirgarten/images/icons/Huehneranteil.svg",
    }

    today = date.today()

    def map_capa(capa):
        max_capa = capa["max_capacity"]
        current_capa = ceil(
            get_current_capacity(capa)
            / float(
                get_product_price(
                    Product.objects.get(type_id=capa["product_type_id"], base=True)
                ).price
            )
        )
        return {
            "name": capa["product_type__name"],
            "icon": PRODUCT_TYPE_ICONS.get(capa["product_type__name"], "?"),
            "max_capacity": max_capa,
            "current_capacity": current_capa,
            "capacity_percent": (current_capa / max_capa) if max_capa else None,
        }

    return {
        "id": pickup_location.id,
        "name": pickup_location.name,
        "street": pickup_location.street,
        "city": f"{pickup_location.postcode} {pickup_location.city}",
        "info": pickup_location.info.replace(", ", "<br/>"),
        "capabilities": list(
            map(
                map_capa,
                [
                    capa
                    for capa in location_capabilities
                    if capa["pickup_location_id"] == pickup_location.id
                ],
            )
        ),
        # FIXME: member count should be filtered by active subscriptions
        "members": MemberPickupLocation.objects.filter(
            valid_from__lte=today, pickup_location=pickup_location
        )
        .order_by("member", "-valid_from")
        .distinct("member")
        .count(),
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

        self.attrs["selected_product_types"] = selected_product_types
        self.attrs["data"] = get_pickup_locations_map_data(
            pickup_locations, location_capabilities
        )
        self.attrs["initial"] = initial


class PickupLocationChoiceField(forms.ModelChoiceField):
    def __init__(self, **kwargs):
        initial = kwargs["initial"]

        location_capabilities = get_active_pickup_location_capabilities().values(
            "product_type__name",
            "max_capacity",
            "product_type_id",
            "pickup_location_id",
        )

        selected_product_types = {
            product_type_name: sum(
                map(
                    lambda x: float(get_product_price(x.product).price) * x.quantity,
                    sub,
                )
            )
            / float(sub[0].product.type.base_price)
            for product_type_name, sub in initial["subs"].items()
            if sub[0].product.type.delivery_cycle != NO_DELIVERY[0]
        }

        possible_locations = PickupLocation.objects.filter(
            id__in=map(lambda x: x["pickup_location_id"], location_capabilities)
        )
        for pt_name in selected_product_types:
            possible_locations = possible_locations.filter(
                id__in=[
                    capa["pickup_location_id"]
                    for capa in location_capabilities
                    if capa["product_type__name"] == pt_name
                ]
            )
            # get current free capacity for each location and filter out locations with no capacity
            for pl in possible_locations:
                for capa in location_capabilities:
                    if (
                        pl.id == capa["pickup_location_id"]
                        and capa["max_capacity"]
                        and capa["product_type__name"] == pt_name
                    ):
                        current_capacity = get_current_capacity(capa) / float(
                            ProductType.objects.get(name=pt_name).base_price
                        )
                        free_capacity = capa["max_capacity"] - current_capacity
                        if selected_product_types[pt_name] > free_capacity:
                            possible_locations = possible_locations.exclude(id=pl.id)

        super(PickupLocationChoiceField, self).__init__(
            queryset=possible_locations,
            initial=0,
            widget=PickupLocationWidget(
                pickup_locations=PickupLocation.objects.all(),
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
    n_columns = 2

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

        self.fields["access_code"] = forms.CharField(
            label=_("Zugangscode"), required=False
        )
        self.fields["messenger_group_link"] = forms.CharField(
            label=_("Link zur Signal-Gruppe"), required=False
        )
        self.fields["contact_name"] = forms.CharField(
            label=_("Name der Abholort-Pat*innen"), required=False
        )
        self.fields["photo_link"] = forms.CharField(
            label=_("Link zum Foto des Abholorts"), required=False
        )
        self.fields["info"] = forms.CharField(
            label=_("Zusätzliche Informationen zur Abholung"),
            required=False,
            help_text="z.B.: im Hinterhof",
        )

        self.colspans = {
            "coords": 2,
            "info": 2,
            "monday_times": 2,
            "tuesday_times": 2,
            "wednesday_times": 2,
            "thursday_times": 2,
            "friday_times": 2,
            "saturday_times": 2,
            "sunday_times": 2,
        }

        self.product_types = list(
            get_active_product_types()
            .exclude(delivery_cycle=NO_DELIVERY[0])
            .order_by("name")
        )

        for pt in self.product_types:
            self.fields["pt_" + pt.id] = forms.BooleanField(
                label=_(pt.name),
                required=False,
                help_text=f"Hier können {pt.name} abgeholt werden",
            )
            self.fields["pt_capa_" + pt.id] = forms.IntegerField(
                label=_("Kapazität (in Anteilen)"),
                required=False,
                min_value=0,
                widget=forms.NumberInput(attrs={"placeholder": "Unbegrenzt"}),
            )

        self.fields["monday_times"] = forms.CharField(
            label=_("Montag"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
        )
        self.fields["tuesday_times"] = forms.CharField(
            label=_("Dienstag"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
        )
        self.fields["wednesday_times"] = forms.CharField(
            label=_("Mittwoch"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
        )
        self.fields["thursday_times"] = forms.CharField(
            label=_("Donnerstag"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
        )
        self.fields["friday_times"] = forms.CharField(
            label=_("Freitag"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
        )
        self.fields["saturday_times"] = forms.CharField(
            label=_("Samstag"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
        )
        self.fields["sunday_times"] = forms.CharField(
            label=_("Sonntag"),
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "HH:MM-HH:MM"}),
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
            self.fields["access_code"].initial = self.pickup_location.access_code
            self.fields[
                "messenger_group_link"
            ].initial = self.pickup_location.messenger_group_link
            self.fields["contact_name"].initial = self.pickup_location.contact_name
            self.fields["photo_link"].initial = self.pickup_location.photo_link

            opening_times = PickupLocationOpeningTime.objects.filter(
                pickup_location=self.pickup_location
            )
            opening_times_map = {}
            for ot in opening_times:
                times_list = opening_times_map.get(ot.day_of_week, [])
                times_list.append(
                    f"{ot.open_time.strftime('%H:%M')}-{ot.close_time.strftime('%H:%M')}"
                )
                opening_times_map[ot.day_of_week] = times_list

            self.fields["monday_times"].initial = ", ".join(
                opening_times_map[0] if 0 in opening_times_map else []
            )
            self.fields["tuesday_times"].initial = ", ".join(
                opening_times_map[1] if 1 in opening_times_map else []
            )
            self.fields["wednesday_times"].initial = ", ".join(
                opening_times_map[2] if 2 in opening_times_map else []
            )
            self.fields["thursday_times"].initial = ", ".join(
                opening_times_map[3] if 3 in opening_times_map else []
            )
            self.fields["friday_times"].initial = ", ".join(
                opening_times_map[4] if 4 in opening_times_map else []
            )
            self.fields["saturday_times"].initial = ", ".join(
                opening_times_map[5] if 5 in opening_times_map else []
            )
            self.fields["sunday_times"].initial = ", ".join(
                opening_times_map[6] if 6 in opening_times_map else []
            )

            for ptc in get_active_pickup_location_capabilities().filter(
                pickup_location=self.pickup_location
            ):
                key = "pt_" + ptc.product_type.id
                if key in self.fields:
                    self.fields[key].initial = True
                    self.fields[
                        "pt_capa_" + ptc.product_type.id
                    ].initial = ptc.max_capacity

        self.product_types = list(map(lambda x: x.id, self.product_types))

    def clean(self):
        cleaned_data = super().clean()

        def validate_times(field):
            times = cleaned_data.get(field)
            if times:
                times = [time.strip() for time in times.split(",")]
                for time in times:
                    try:
                        start, end = time.split("-")
                        start_time = datetime.strptime(start, "%H:%M")
                        end_time = datetime.strptime(end, "%H:%M")

                        if start_time >= end_time:
                            self.add_error(
                                field,
                                ValidationError(
                                    "End time must be later than start time"
                                ),
                            )

                    except Exception:
                        self.add_error(
                            field,
                            ValidationError(
                                "Bitte geben Sie die Öffnungszeiten im Format 'HH:MM-HH:MM' an."
                            ),
                        )

        coords = cleaned_data.get("coords")
        if coords:
            coords = coords.split(",")
            if len(coords) != 2:
                self.add_error(
                    "coords",
                    ValidationError(
                        "Bitte geben Sie die Koordinaten im Format 'Längengrad,Breitengrad' an."
                    ),
                )
            try:
                float(coords[0].strip())
                float(coords[1].strip())
            except Exception:
                self.add_error(
                    "coords",
                    ValidationError(
                        "Bitte geben Sie die Koordinaten im Format 'Längengrad,Breitengrad' an."
                    ),
                )

        validate_times("monday_times")
        validate_times("tuesday_times")
        validate_times("wednesday_times")
        validate_times("thursday_times")
        validate_times("friday_times")
        validate_times("saturday_times")
        validate_times("sunday_times")

        return cleaned_data

    @transaction.atomic
    def save(self):
        pl = self.pickup_location
        coords = self.cleaned_data["coords"].split(",")

        pl.coords_lon = coords[0].strip()
        pl.coords_lat = coords[1].strip()

        pl.name = self.cleaned_data["name"]
        pl.street = self.cleaned_data["street"]
        pl.postcode = self.cleaned_data["postcode"]
        pl.city = self.cleaned_data["city"]
        pl.info = self.cleaned_data["info"]
        pl.access_code = self.cleaned_data["access_code"]
        pl.contact_name = self.cleaned_data["contact_name"]
        pl.messenger_group_link = self.cleaned_data["messenger_group_link"]
        pl.photo_link = self.cleaned_data["photo_link"]

        pl.save()

        PickupLocationOpeningTime.objects.filter(pickup_location=pl).delete()

        def create_opening_time(day: int, times: str):
            monday_times = times.split(",")
            for time in monday_times:
                if not time.strip():
                    continue
                start, end = time.split("-")
                PickupLocationOpeningTime.objects.create(
                    pickup_location=pl,
                    day_of_week=day,
                    open_time=start.strip(),
                    close_time=end.strip(),
                )

        create_opening_time(0, self.cleaned_data["monday_times"])
        create_opening_time(1, self.cleaned_data["tuesday_times"])
        create_opening_time(2, self.cleaned_data["wednesday_times"])
        create_opening_time(3, self.cleaned_data["thursday_times"])
        create_opening_time(4, self.cleaned_data["friday_times"])
        create_opening_time(5, self.cleaned_data["saturday_times"])
        create_opening_time(6, self.cleaned_data["sunday_times"])

        capabilities = list(
            map(
                lambda x: x["product_type__id"],
                PickupLocationCapability.objects.filter(pickup_location=pl).values(
                    "product_type__id"
                ),
            )
        )
        for pt in self.product_types:
            if pt not in capabilities:  # doesn't exist yet
                if self.cleaned_data["pt_" + pt]:  # is selected
                    # --> create
                    PickupLocationCapability.objects.create(
                        pickup_location=pl,
                        product_type_id=pt,
                        max_capacity=self.cleaned_data.get("pt_capa_" + pt, None),
                    )
            else:
                if not self.cleaned_data["pt_" + pt]:  # exists & is not selected
                    # --> delete
                    PickupLocationCapability.objects.get(
                        pickup_location=pl, product_type_id=pt
                    ).delete()
                else:
                    # --> update
                    plc = PickupLocationCapability.objects.get(
                        pickup_location=pl, product_type_id=pt
                    )
                    plc.max_capacity = self.cleaned_data.get("pt_capa_" + pt, None)
                    plc.save()

        return pl
