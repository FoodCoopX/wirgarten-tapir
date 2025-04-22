from rest_framework import serializers

from tapir.pickup_locations.config import (
    OPTIONS_PICKING_MODE,
    PICKING_MODE_BASKET,
    PICKING_MODE_SHARE,
)


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
