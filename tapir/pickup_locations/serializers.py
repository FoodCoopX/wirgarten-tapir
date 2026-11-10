from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.wirgarten.constants import OPTIONS_WEEKDAYS
from tapir.wirgarten.models import (
    PickupLocation,
    PickupLocationOpeningTime,
    LocationRoute,
)
from tapir.wirgarten.utils import get_today


class PickupLocationOpeningTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocationOpeningTime
        fields = "__all__"

    day_of_week_string = serializers.SerializerMethodField()

    @staticmethod
    def get_day_of_week_string(opening_time: PickupLocationOpeningTime) -> str:
        return OPTIONS_WEEKDAYS[opening_time.day_of_week][1]


class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = "__all__"

    delivery_day = serializers.SerializerMethodField()
    opening_times = PickupLocationOpeningTimeSerializer(many=True, read_only=True)

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_delivery_day(self, pickup_location: PickupLocation) -> int | None:
        return PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id=pickup_location.id, cache=self.context["cache"]
        )


class PickupLocationOpeningTimeInputSerializer(serializers.Serializer):
    day_of_week = serializers.ChoiceField(choices=OPTIONS_WEEKDAYS)
    open_time = serializers.TimeField()
    close_time = serializers.TimeField()


class PickupLocationSaveRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    latitude = serializers.DecimalField(
        max_digits=None, decimal_places=None, allow_null=True, default=None
    )
    longitude = serializers.DecimalField(
        max_digits=None, decimal_places=None, allow_null=True, default=None
    )
    street = serializers.CharField(max_length=150)
    street_2 = serializers.CharField(max_length=150, allow_blank=True, default="")
    postcode = serializers.CharField(max_length=32)
    city = serializers.CharField(max_length=50)
    info = serializers.CharField(max_length=3000, allow_blank=True, default="")
    access_code = serializers.CharField(max_length=20, allow_blank=True, default="")
    messenger_group_link = serializers.CharField(
        max_length=150, allow_blank=True, default=""
    )
    contact_name = serializers.CharField(max_length=150, allow_blank=True, default="")
    photo_link = serializers.CharField(max_length=512, allow_blank=True, default="")
    location_route_id = serializers.CharField(allow_null=True, default=None)
    route_info = serializers.CharField(max_length=3000, allow_blank=True, default="")
    start_date = serializers.DateField(allow_null=True, default=None)
    end_date = serializers.DateField(allow_null=True, default=None)
    show_details_in_basket_totals_export = serializers.BooleanField(default=False)
    is_home_delivery = serializers.BooleanField(default=False)
    opening_times = PickupLocationOpeningTimeInputSerializer(many=True)


class ProductBasketSizeEquivalenceSerializer(serializers.Serializer):
    basket_size_name = serializers.CharField()
    quantity = serializers.IntegerField()


class PickupLocationCapacityByShareSerializer(serializers.Serializer):
    product_type_name = serializers.CharField()
    product_type_id = serializers.CharField()
    capacity = serializers.IntegerField(required=False)


class PickupLocationCapacityByBasketSizeSerializer(serializers.Serializer):
    basket_size_name = serializers.CharField()
    capacity = serializers.IntegerField(required=False)


class PickupLocationCapacitiesSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    capacities_by_shares = PickupLocationCapacityByShareSerializer(many=True)


class PickupLocationCapacityChangePointSerializer(serializers.Serializer):
    date = serializers.DateField()
    values = serializers.ListField(
        child=serializers.CharField(),
    )


class PickupLocationCapacityEvolutionSerializer(serializers.Serializer):
    table_headers = serializers.ListField(child=serializers.CharField())
    data_points = PickupLocationCapacityChangePointSerializer(many=True)


class PublicPickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = [
            "id",
            "name",
            "latitude",
            "longitude",
            "street",
            "street_2",
            "postcode",
            "city",
            "opening_times",
            "current_delivery_charge",
            "delivery_day",
            "is_home_delivery",
        ]
        read_only_fields = fields

    opening_times = serializers.SerializerMethodField()
    current_delivery_charge = serializers.SerializerMethodField()
    delivery_day = serializers.SerializerMethodField()

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_delivery_day(self, pickup_location: PickupLocation) -> int | None:
        if not settings.BAKERY_ENABLED:
            return None

        return PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id=pickup_location.id, cache=self.context["cache"]
        )

    @extend_schema_field(PickupLocationOpeningTimeSerializer(many=True))
    def get_opening_times(self, pickup_location: PickupLocation):
        return PickupLocationOpeningTimeSerializer(
            PickupLocationOpeningTime.objects.filter(pickup_location=pickup_location),
            many=True,
        ).data

    @extend_schema_field(serializers.DecimalField(max_digits=8, decimal_places=2))
    def get_current_delivery_charge(self, pickup_location: PickupLocation):
        cache = self.context.get("cache", {})
        reference_date = self.context.get(
            "reference_date_for_delivery_charge", get_today(cache=cache)
        )
        amount = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=pickup_location.id,
            reference_date=reference_date,
            cache=cache,
        )
        return str(amount)


class PickupLocationCapacityCheckResponseSerializer(serializers.Serializer):
    pickup_location_ids_with_enough_capacity_for_order = serializers.ListField(
        child=serializers.CharField()
    )


class PickupLocationCapacityCheckRequestSerializer(serializers.Serializer):
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    growing_period_id = serializers.CharField(allow_null=True)


class PickupLocationDeliveryChargeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocationDeliveryCharge
        fields = ["id", "amount", "valid_from"]


class PickupLocationDeliveryChargesResponseSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    entries = PickupLocationDeliveryChargeEntrySerializer(many=True)


class PickupLocationDeliveryChargeCreateRequestSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    valid_from = serializers.DateField()


class LocationRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationRoute
        fields = "__all__"

    pickup_location_names = serializers.SerializerMethodField()

    @staticmethod
    def get_pickup_location_names(location_route: LocationRoute) -> list[str]:
        return list(
            PickupLocation.objects.filter(location_route=location_route)
            .order_by("name")
            .values_list("name", flat=True)
        )
