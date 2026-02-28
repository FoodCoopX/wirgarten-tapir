from rest_framework import serializers

from tapir.bakery.models import (
    Bread,
    BreadCapacityPickupLocation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    Ingredient,
    PreferredBread,
    PreferredLabel,
    StoveSession,
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
    capacity = serializers.IntegerField(read_only=True, required=False)
    delivery_count = serializers.IntegerField(read_only=True, required=False)
    available_capacity = serializers.IntegerField(read_only=True, required=False)

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
            "capacity",
            "delivery_count",
            "available_capacity",
        ]
        read_only_fields = [
            "id",
            "capacity",
            "delivery_count",
            "available_capacity",
        ]

    def get_label_names(self, obj) -> list[str]:
        return [label.name for label in obj.labels.all()]


class BreadCapacityPickupLocationSerializer(serializers.ModelSerializer):
    pickup_location_name = serializers.CharField(
        source="pickup_location_day.pickup_location.name", read_only=True
    )
    delivery_day = serializers.IntegerField(
        source="pickup_location.delivery_day", read_only=True
    )

    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = BreadCapacityPickupLocation
        fields = "__all__"


class BreadDeliverySerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)
    pickup_location_name = serializers.CharField(
        source="pickup_location.name", read_only=True
    )
    delivery_day = serializers.IntegerField(
        source="pickup_location.delivery_day", read_only=True
    )

    class Meta:
        model = BreadDelivery
        fields = "__all__"


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


class PreferredLabelSerializer(serializers.ModelSerializer):
    member_id = serializers.CharField(source="member.id", read_only=True)
    labels = serializers.PrimaryKeyRelatedField(
        queryset=BreadLabel.objects.all(), many=True
    )

    class Meta:
        model = PreferredLabel
        fields = ["id", "member_id", "labels"]


class PreferredBreadSerializer(serializers.ModelSerializer):
    member_id = serializers.CharField(source="member.id", read_only=True)
    breads = serializers.PrimaryKeyRelatedField(queryset=Bread.objects.all(), many=True)

    class Meta:
        model = PreferredBread
        fields = ["id", "member_id", "breads"]


class PreferredLabelBulkUpdateSerializer(serializers.Serializer):
    labels = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of BreadLabel IDs to set as preferred for the member.",
    )


class PreferredBreadsBulkUpdateSerializer(serializers.Serializer):
    breads = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of Bread IDs to set as preferred for the member.",
    )


class AbhollisteEntrySerializer(serializers.Serializer):
    """
    Serializer for a single member's entry in the Abholliste
    """

    member_id = serializers.UUIDField()
    display_name = serializers.CharField()
    total_breads = serializers.IntegerField()
    breads = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(allow_null=True))
    )


class BreadCapacityUpdateItemSerializer(serializers.Serializer):
    pickup_location = serializers.CharField(required=True)
    bread = serializers.CharField(required=True)
    capacity = serializers.IntegerField(required=False, allow_null=True)


class BreadCapacityBulkUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=True)
    week = serializers.IntegerField(required=True)
    updates = BreadCapacityUpdateItemSerializer(many=True, required=True)


###---------------- Serializers for solver results and requests ------------------ ##


class StoveLayerSerializer(serializers.Serializer):
    layer = serializers.IntegerField()
    bread_id = serializers.CharField(allow_null=True, required=False)
    bread_name = serializers.CharField(allow_null=True, required=False)
    bread = serializers.CharField(allow_null=True, required=False)  # For empty layers
    quantity = serializers.IntegerField()


class StoveSessionSerializer(serializers.Serializer):
    session = serializers.IntegerField()
    layers = StoveLayerSerializer(many=True)


class BreadQuantitySerializer(serializers.Serializer):
    bread_id = serializers.CharField()
    bread_name = serializers.CharField()
    total = serializers.IntegerField(help_text="Total pieces to bake")
    deliveries = serializers.IntegerField(help_text="Pieces for member deliveries")
    remaining = serializers.IntegerField(
        help_text="Extra pieces beyond deliveries (e.g., for external sale)"
    )


class BreadDistributionSerializer(serializers.Serializer):
    bread_id = serializers.CharField()
    bread_name = serializers.CharField()
    pickup_location_id = serializers.CharField()
    count = serializers.IntegerField()


class RunSolverRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    delivery_week = serializers.IntegerField(min_value=1, max_value=53)
    delivery_day = serializers.IntegerField(min_value=0, max_value=6, required=False)


class RunSolverResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    total_deliveries = serializers.IntegerField()
    sessions_used = serializers.IntegerField(
        help_text="Number of baking sessions needed"
    )

    quantities = BreadQuantitySerializer(many=True)
    stove_sessions = StoveSessionSerializer(many=True)
    distribution = BreadDistributionSerializer(many=True)


class RunSolverErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


class StoveSerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = StoveSession
        fields = "__all__"
