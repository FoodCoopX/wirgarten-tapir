from rest_framework import serializers

from tapir.bakery.models import (
    Bread,
    BreadCapacityPickupStation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    Ingredient,
)
from tapir.bakery.utils import can_delete_instance


class BreadLabelSerializer(serializers.ModelSerializer):
    """Serializer for bread labels/categories"""

    class Meta:
        model = BreadLabel
        fields = "__all__"


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for ingredients"""

    can_be_deleted = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = "__all__"

    def get_can_be_deleted(self, obj):
        can_delete, _ = can_delete_instance(obj)
        return can_delete


class BreadContentSerializer(serializers.ModelSerializer):
    """Serializer for bread content (ingredient amounts)"""

    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = BreadContent
        fields = "__all__"


class BreadListSerializer(serializers.ModelSerializer):
    """Serializer for bread list view (minimal data)"""

    class Meta:
        model = Bread
        fields = "__all__"


class BreadDetailSerializer(serializers.ModelSerializer):
    """Serializer for bread detail view (includes ingredients)"""

    labels = BreadLabelSerializer(many=True, read_only=True)
    contents = BreadContentSerializer(many=True, read_only=True)
    label_names = serializers.SerializerMethodField()

    class Meta:
        model = Bread
        fields = [
            "id",
            "name",
            "picture",
            "description",
            "weight",
            "labels",
            "label_names",
            "contents",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_label_names(self, obj) -> list[str]:
        return [label.name for label in obj.labels.all()]


class BreadCapacityPickupStationSerializer(serializers.ModelSerializer):
    pickup_location = serializers.CharField(
        source="pickup_station_day.pickup_location.id", read_only=True
    )
    pickup_location_name = serializers.CharField(
        source="pickup_station_day.pickup_location.name", read_only=True
    )
    delivery_day = serializers.IntegerField(
        source="pickup_station_day.day_of_week", read_only=True
    )

    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = BreadCapacityPickupStation
        fields = "__all__"


class BreadDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = BreadDelivery
        fields = [
            "id",
            "year",
            "delivery_week",
            "delivery_day",
            "subscription",
            "bread",
        ]

    def validate(self, data):
        # Check total count for this week/day/subscription
        total = BreadDelivery.objects.filter(
            year=data["year"],
            delivery_week=data["delivery_week"],
            delivery_day=data["delivery_day"],
            subscription=data["subscription"],
        ).count()

        if self.instance:
            # Editing existing — don't count itself
            total -= 1

        if total >= data["subscription"].quantity:
            raise serializers.ValidationError(
                f"Maximum {data['subscription'].quantity} bread(s) allowed"
            )

        return data


class AvailableBreadsForDeliveryListResponseSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    week = serializers.IntegerField()
    day = serializers.IntegerField()
    breads = BreadListSerializer(many=True)


class ToggleBreadRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    week = serializers.IntegerField()
    day = serializers.IntegerField()
    bread_id = serializers.CharField()
    is_active = serializers.BooleanField()


class ToggleBreadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    created = serializers.BooleanField(required=False)
    deleted = serializers.BooleanField(required=False)
    bread_id = serializers.CharField()
