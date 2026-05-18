from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.deliveries.serializers import PickupLocationOpeningTimeSerializer
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.wirgarten.models import PickupLocation, PickupLocationOpeningTime
from tapir.wirgarten.utils import get_today


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
        amount = PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
            pickup_location_id=pickup_location.id,
            reference_date=get_today(cache=cache),
            cache=cache,
        )
        return str(amount)


class PickupLocationCapacityCheckResponseSerializer(serializers.Serializer):
    enough_capacity_for_order = serializers.BooleanField()


class PickupLocationCapacityCheckRequestSerializer(serializers.Serializer):
    shopping_cart = serializers.DictField(child=serializers.IntegerField())
    pickup_location_id = serializers.CharField()
    growing_period_id = serializers.CharField(allow_null=True)


class PickupLocationDeliveryChargeEntrySerializer(serializers.Serializer):
    id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    valid_from = serializers.DateField()


class PickupLocationDeliveryChargesResponseSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    entries = PickupLocationDeliveryChargeEntrySerializer(many=True)


class PickupLocationDeliveryChargeCreateRequestSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    valid_from = serializers.DateField()
