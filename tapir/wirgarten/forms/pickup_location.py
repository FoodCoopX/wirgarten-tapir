import json
from datetime import datetime
from typing import List

from dateutil.relativedelta import relativedelta
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils.translation import gettext_lazy as _

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    MemberPickupLocation,
    PickupLocation,
    PickupLocationOpeningTime,
    Product,
    Subscription,
    Member,
    ProductType,
)
from tapir.wirgarten.service.delivery import (
    get_active_pickup_location_capabilities,
    get_next_delivery_date,
)
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import get_today


def get_pickup_locations_map_data(pickup_locations, location_capabilities):
    return json.dumps(
        {
            f"{pl.id}": pickup_location_to_dict(location_capabilities, pl)
            for pl in list(pickup_locations)
        }
    )


def pickup_location_to_dict(location_capabilities, pickup_location):
    next_delivery_date = get_next_delivery_date()
    next_month = next_delivery_date + relativedelta(day=1, months=1)

    def map_capa(capa):
        max_capa = capa["max_capacity"]
        try:
            base_product = Product.objects.get(
                type_id=capa["product_type_id"], base=True
            )
        except Product.DoesNotExist:
            return None

        current_capa = round(
            PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
                pickup_location=PickupLocation.objects.get(
                    id=capa["pickup_location_id"]
                ),
                product_type=ProductType.objects.get(id=capa["product_type_id"]),
                reference_date=next_month,
            )
            / float(
                get_product_price(
                    base_product,
                    next_delivery_date,
                ).size
            ),
            2,
        )

        next_month_capa = round(
            PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
                pickup_location=PickupLocation.objects.get(
                    id=capa["pickup_location_id"]
                ),
                product_type=ProductType.objects.get(id=capa["product_type_id"]),
                reference_date=next_month,
            )
            / float(
                get_product_price(
                    base_product,
                    next_month,
                ).size
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

    return {
        "id": pickup_location.id,
        "name": pickup_location.name,
        "opening_times": pickup_location.opening_times_html,
        "street": pickup_location.street,
        "city": f"{pickup_location.postcode} {pickup_location.city}",
        "capabilities": list(
            [
                x
                for x in [
                    map_capa(capa)
                    for capa in location_capabilities
                    if capa["pickup_location_id"] == pickup_location.id
                ]
                if x is not None
            ]
        ),
        "members": get_active_subscriptions(next_delivery_date)
        .annotate(
            latest_pickup_location_id=Subquery(
                MemberPickupLocation.objects.filter(
                    member=OuterRef("member"), valid_from__lte=next_delivery_date
                )
                .order_by("-valid_from")
                .values("pickup_location_id")[:1]
            )
        )
        .filter(
            latest_pickup_location_id=pickup_location.id,
        )
        .values("member_id")
        .distinct()
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
        initial = kwargs.pop("initial", {"subs": {}})
        next_month = get_today() + relativedelta(months=1, day=1)
        reference_date = kwargs.pop("reference_date", next_month)
        member = kwargs.pop("member", None)

        location_capabilities = get_active_pickup_location_capabilities(
            reference_date=reference_date
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
                    lambda subscription: float(
                        get_product_price(subscription.product).size
                    )
                    * (subscription.quantity or 0),
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

        super(PickupLocationChoiceField, self).__init__(
            queryset=possible_locations,
            initial=0,
            widget=PickupLocationWidget(
                pickup_locations=possible_locations,
                location_capabilities=location_capabilities,
                selected_product_types=selected_product_types,
                initial=initial.get("initial", None),
            ),
            **kwargs,
        )

    @staticmethod
    def get_possible_locations(
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
                ordered_products_to_quantity_map=ordered_products_to_quantity_map,
                already_registered_member=member,
                subscription_start=reference_date,
            ):
                possible_location_ids.append(pickup_location.id)
        return PickupLocation.objects.filter(id__in=possible_location_ids)

    def label_from_instance(self, obj):
        return f"<strong>{obj.name}</strong><br/><small>{obj.street}, {obj.postcode} {obj.city}</small>"


class PickupLocationChoiceForm(forms.Form):
    intro_template = "registration/steps/pickup_location.intro.html"
    intro_text_skip_hr = True

    def __init__(self, *args, **kwargs):
        member = kwargs.pop("member", None)
        super(PickupLocationChoiceForm, self).__init__(*args, **kwargs)

        self.fields["pickup_location"] = PickupLocationChoiceField(
            label=_("Abholort"),
            initial=kwargs["initial"],
            member=member,
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
            label=_("Straße & Hausnummer"), required=True
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
            self.fields["coords"].initial = (
                f"{self.pickup_location.coords_lon},{self.pickup_location.coords_lat}"
            )
            self.fields["name"].initial = self.pickup_location.name
            self.fields["street"].initial = self.pickup_location.street
            self.fields["postcode"].initial = self.pickup_location.postcode
            self.fields["city"].initial = self.pickup_location.city
            self.fields["info"].initial = self.pickup_location.info
            self.fields["access_code"].initial = self.pickup_location.access_code
            self.fields["messenger_group_link"].initial = (
                self.pickup_location.messenger_group_link
            )
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
        pl = (
            self.pickup_location
            if hasattr(self, "pickup_location")
            else PickupLocation()
        )
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

        return pl
