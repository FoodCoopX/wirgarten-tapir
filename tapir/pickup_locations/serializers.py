from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.deliveries.serializers import PickupLocationOpeningTimeSerializer
from tapir.pickup_locations.config import (
    OPTIONS_PICKING_MODE,
    PICKING_MODE_BASKET,
    PICKING_MODE_SHARE,
)
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
    picking_mode = serializers.ChoiceField(choices=OPTIONS_PICKING_MODE)
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    capacities_by_shares = PickupLocationCapacityByShareSerializer(
        many=True, required=False
    )
    capacities_by_basket_size = PickupLocationCapacityByBasketSizeSerializer(
        many=True, required=False
    )

    def validate(self, data):
        data = super().validate(data)

        if "picking_mode" not in data.keys():
            return data

        if (
            data["picking_mode"] == PICKING_MODE_BASKET
            and data.get("capacities_by_basket_size", None) is None
        ):
            raise serializers.ValidationError(
                f"If the picking mode is '{PICKING_MODE_BASKET}', the field 'capacities_by_basket_size' must be set."
            )

        if (
            data["picking_mode"] == PICKING_MODE_SHARE
            and data.get("capacities_by_shares", None) is None
        ):
            raise serializers.ValidationError(
                f"If the picking mode is '{PICKING_MODE_SHARE}', the field 'capacities_by_shares' must be set."
            )

        return data


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
        ]

    opening_times = serializers.SerializerMethodField()

    @extend_schema_field(PickupLocationOpeningTimeSerializer(many=True))
    def get_opening_times(self, pickup_location: PickupLocation):
        return PickupLocationOpeningTimeSerializer(
            PickupLocationOpeningTime.objects.filter(pickup_location=pickup_location),
            many=True,
        ).data
