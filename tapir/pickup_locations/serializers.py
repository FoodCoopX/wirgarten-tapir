from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
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


class PickupLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocation
        fields = "__all__"


class PickupLocationOpeningTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupLocationOpeningTime
        fields = "__all__"

    day_of_week_string = serializers.SerializerMethodField()

    @staticmethod
    def get_day_of_week_string(opening_time: PickupLocationOpeningTime) -> str:
        return OPTIONS_WEEKDAYS[opening_time.day_of_week][1]


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
            "coords_lon",
            "coords_lat",
            "street",
            "street_2",
            "postcode",
            "city",
            "opening_times",
            "current_delivery_charge",
        ]

    opening_times = serializers.SerializerMethodField()
    current_delivery_charge = serializers.SerializerMethodField()

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
