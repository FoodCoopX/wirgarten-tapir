from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.deliveries.serializers import PickupLocationOpeningTimeSerializer
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.shortcuts import get_serializer_cache
from tapir.wirgarten.models import PickupLocation, PickupLocationOpeningTime


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
    delivery_day = serializers.SerializerMethodField()

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
            "delivery_day",
        ]

    opening_times = serializers.SerializerMethodField()

    @extend_schema_field(PickupLocationOpeningTimeSerializer(many=True))
    def get_opening_times(self, pickup_location: PickupLocation):
        return PickupLocationOpeningTimeSerializer(
            PickupLocationOpeningTime.objects.filter(pickup_location=pickup_location),
            many=True,
        ).data

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_delivery_day(self, pickup_location: PickupLocation):
        # None when the pickup location has no opening times configured
        return PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id=pickup_location.id, cache=get_serializer_cache(self)
        )


class PickupLocationCapacityCheckResponseSerializer(serializers.Serializer):
    enough_capacity_for_order = serializers.BooleanField()


class PickupLocationCapacityCheckRequestSerializer(serializers.Serializer):
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    pickup_location_id = serializers.CharField()
    growing_period_id = serializers.CharField(allow_null=True)


class PickupLocationDeliveryDaySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class PickupLocationsByDeliveryDayResponseSerializer(serializers.Serializer):
    pickup_locations = PickupLocationDeliveryDaySerializer(many=True)


class DeliveryDaysResponseSerializer(serializers.Serializer):
    days = serializers.ListField(child=serializers.IntegerField())
