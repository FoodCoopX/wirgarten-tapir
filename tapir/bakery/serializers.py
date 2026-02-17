from rest_framework import serializers

from tapir.bakery.models import (
    BakeryConfiguration,
    BakeryUserProfile,
    Bread,
    BreadCapacityPickupStation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    Ingredient,
)
from tapir.bakery.utils import can_delete_instance
from tapir.wirgarten.models import PickupLocationOpeningTime


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


class BakeryUserProfileSerializer(serializers.ModelSerializer):
    """Serializer for bakery user profile with pseudonym"""

    member_name = serializers.CharField(
        source="member.get_display_name", read_only=True
    )
    preferred_bread_labels = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True
    )

    class Meta:
        model = BakeryUserProfile
        fields = "__all__"

    def get_display_name(self, obj) -> str:
        return obj.get_display_name()


class PickupLocationOpeningTimeSerializer(serializers.ModelSerializer):
    pickup_location_name = serializers.CharField(
        source="pickup_location.name", read_only=True
    )
    weekday = serializers.IntegerField(source="day_of_week")
    start_time = serializers.TimeField(source="open_time", format="%H:%M")
    end_time = serializers.TimeField(source="close_time", format="%H:%M")

    class Meta:
        model = PickupLocationOpeningTime
        fields = [
            "id",
            "pickup_location",
            "pickup_location_name",
            "weekday",
            "start_time",
            "end_time",
        ]
        read_only_fields = ["id", "pickup_location_name"]


class BreadCapacityPickupStationSerializer(serializers.ModelSerializer):
    pickup_location = serializers.CharField(
        source="pickup_station_day.pickup_location.id", read_only=True
    )
    pickup_location_name = serializers.CharField(
        source="pickup_station_day.pickup_location.name", read_only=True
    )
    weekday = serializers.IntegerField(
        source="pickup_station_day.day_of_week", read_only=True
    )

    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = BreadCapacityPickupStation
        fields = "__all__"


class BakeryConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for bakery configuration"""

    class Meta:
        model = BakeryConfiguration
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
