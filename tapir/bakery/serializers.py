import datetime

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.bakery.models import (
    Bread,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    BreadsPerPickupLocationPerWeek,
    Ingredient,
    PreferredBread,
    StoveSession,
)
from tapir.bakery.services.bread_availability_service import (
    BreadAvailabilityService,
)
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.utils import MAX_PREFERRED_BREADS
from tapir.pickup_locations.models import PickupLocation
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)

# A plausibility limit, not a column limit: a station gets loaves in the
# hundreds, so anything above this is a typo rather than an order.
MAX_PIECES_PER_ENTRY = 1000


def _piece_count():
    return serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=MAX_PIECES_PER_ENTRY
    )


def _get_pickup_location_delivery_day(serializer, obj) -> int | None:
    return PickupLocationDeliveryDayService.get_delivery_day(
        pickup_location_id=obj.pickup_location_id,
        cache=serializer.context["cache"],
    )


class BreadLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreadLabel
        fields = "__all__"
        # A TapirModel id is a plain CharField, which DRF would otherwise leave
        # writable under fields="__all__".
        read_only_fields = ["id"]


class IngredientSerializer(serializers.ModelSerializer):
    can_be_deleted = serializers.SerializerMethodField()

    class Meta:
        model = Ingredient
        fields = "__all__"
        # See BreadLabelSerializer.
        read_only_fields = ["id"]

    @extend_schema_field(serializers.BooleanField)
    def get_can_be_deleted(self, obj):
        is_used = getattr(obj, "is_used", None)
        if is_used is None:
            is_used = BreadContent.objects.filter(ingredient=obj).exists()
        return not is_used


class BreadContentSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)

    class Meta:
        model = BreadContent
        fields = "__all__"
        # See BreadLabelSerializer.
        read_only_fields = ["id"]


PIECE_COUNT_LIMITS = {
    field: {"max_value": MAX_PIECES_PER_ENTRY}
    for field in ["min_pieces", "max_pieces", "min_remaining_pieces"]
}


class BreadListSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(read_only=True, required=False)
    delivery_count = serializers.IntegerField(read_only=True, required=False)
    available_capacity = serializers.IntegerField(read_only=True, required=False)
    contents = BreadContentSerializer(many=True, read_only=True)

    class Meta:
        model = Bread
        fields = "__all__"
        extra_kwargs = PIECE_COUNT_LIMITS
        # See BreadLabelSerializer.
        read_only_fields = ["id"]


class BreadDetailSerializer(serializers.ModelSerializer):
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


class BreadDeliverySerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)
    pickup_location = serializers.SerializerMethodField()
    pickup_location_name = serializers.SerializerMethodField()
    pickup_location_street = serializers.SerializerMethodField()
    pickup_location_city = serializers.SerializerMethodField()
    delivery_day = serializers.SerializerMethodField()
    joker_taken = serializers.SerializerMethodField()
    choosing_deadline = serializers.SerializerMethodField()
    can_still_choose = serializers.SerializerMethodField()

    class Meta:
        model = BreadDelivery
        # `subscription` must stay read-only, or a slot could be reassigned to
        # someone else.
        fields = [
            "id",
            "year",
            "delivery_week",
            "subscription",
            "slot_number",
            "pickup_location",
            "bread",
            "joker_taken",
            "bread_name",
            "pickup_location_name",
            "pickup_location_street",
            "pickup_location_city",
            "delivery_day",
            "choosing_deadline",
            "can_still_choose",
        ]
        read_only_fields = [
            "id",
            "year",
            "delivery_week",
            "subscription",
            "slot_number",
        ]

    def validate_bread(self, bread):
        if self.instance is None:
            return bread

        if not BreadAvailabilityService.is_bread_available_for_delivery(
            self.instance, bread, cache=self.context["cache"]
        ):
            raise serializers.ValidationError(
                f"'{bread.name}' ist in Woche "
                f"{self.instance.delivery_week}/{self.instance.year} an dieser "
                f"Abholstation nicht verfügbar."
            )
        return bread

    def _pickup_location(self, obj):
        return BreadDeliveryContextService.get_pickup_location(
            obj, cache=self.context["cache"]
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_pickup_location(self, obj) -> str | None:
        pickup_location = self._pickup_location(obj)
        return str(pickup_location.id) if pickup_location else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_pickup_location_name(self, obj) -> str | None:
        pickup_location = self._pickup_location(obj)
        return pickup_location.name if pickup_location else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_pickup_location_street(self, obj) -> str | None:
        pickup_location = self._pickup_location(obj)
        return pickup_location.street if pickup_location else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_pickup_location_city(self, obj) -> str | None:
        pickup_location = self._pickup_location(obj)
        return pickup_location.city if pickup_location else None

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_delivery_day(self, obj) -> int | None:
        return PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                obj, cache=self.context["cache"]
            ),
            cache=self.context["cache"],
        )

    @extend_schema_field(serializers.BooleanField())
    def get_joker_taken(self, obj) -> bool:
        return BreadDeliveryContextService.is_joker_taken(
            obj, cache=self.context["cache"]
        )

    @extend_schema_field(serializers.DateField(allow_null=True))
    def get_choosing_deadline(self, obj) -> datetime.date | None:
        return BreadChoiceDeadlineService.get_deadline(
            year=obj.year,
            delivery_week=obj.delivery_week,
            pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                obj, cache=self.context["cache"]
            ),
            cache=self.context["cache"],
        )

    @extend_schema_field(serializers.BooleanField())
    def get_can_still_choose(self, obj) -> bool:
        return BreadChoiceDeadlineService.can_still_choose(
            year=obj.year,
            delivery_week=obj.delivery_week,
            pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                obj, cache=self.context["cache"]
            ),
            cache=self.context["cache"],
        )


class AvailableBreadsForDeliveryListResponseSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    delivery_week = serializers.IntegerField()
    delivery_day = serializers.IntegerField()
    breads = BreadListSerializer(many=True)


class ToggleBreadRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    delivery_week = serializers.IntegerField()
    delivery_day = serializers.IntegerField()
    bread_id = serializers.CharField()
    is_active = serializers.BooleanField()


class ToggleBreadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    created = serializers.BooleanField(required=False)
    deleted = serializers.BooleanField(required=False)
    bread_id = serializers.CharField()


class PreferredBreadSerializer(serializers.ModelSerializer):
    member_id = serializers.CharField(source="member.id", read_only=True)
    breads = serializers.PrimaryKeyRelatedField(queryset=Bread.objects.all(), many=True)

    class Meta:
        model = PreferredBread
        fields = ["id", "member_id", "breads"]
        # See BreadLabelSerializer.
        read_only_fields = ["id"]


class PreferredBreadsBulkUpdateSerializer(serializers.Serializer):
    # A ListField rather than many=True: ManyRelatedField takes no max_length.
    breads = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Bread.objects.all()),
        allow_empty=True,
        max_length=MAX_PREFERRED_BREADS,
        help_text=(
            f"List of Bread IDs to set as preferred for the member, "
            f"at most {MAX_PREFERRED_BREADS}."
        ),
    )

    def validate_breads(self, breads):
        if len(set(breads)) != len(breads):
            raise serializers.ValidationError(
                "Ein Brot kann nicht mehrfach ausgewählt werden."
            )
        return breads


class PickupListEntrySerializer(serializers.Serializer):
    member_id = serializers.CharField()
    member_name = serializers.CharField()
    total = serializers.IntegerField()
    total_assigned = serializers.IntegerField()
    bread_counts = serializers.DictField(child=serializers.IntegerField())
    bread_preferred = serializers.DictField(child=serializers.BooleanField())
    breads = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(allow_null=True))
    )


class PickupListResponseSerializer(serializers.Serializer):
    bread_names = serializers.ListField(child=serializers.CharField())
    bread_totals = serializers.DictField(child=serializers.IntegerField())
    grand_total = serializers.IntegerField()
    entries = PickupListEntrySerializer(many=True)


class PickupListForLocationSerializer(PickupListResponseSerializer):
    pickup_location_id = serializers.CharField()


class PickupListsResponseSerializer(serializers.Serializer):
    """Several stations of one week in a single response."""

    lists = PickupListForLocationSerializer(many=True)


class BreadCapacityUpdateItemSerializer(serializers.Serializer):
    pickup_location = serializers.PrimaryKeyRelatedField(
        queryset=PickupLocation.objects.all(), required=True
    )
    bread = serializers.PrimaryKeyRelatedField(
        queryset=Bread.objects.all(), required=True
    )
    capacity = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=MAX_PIECES_PER_ENTRY
    )


class BreadCapacityBulkUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=True, min_value=0)
    delivery_week = serializers.IntegerField(required=True, min_value=1, max_value=53)
    updates = BreadCapacityUpdateItemSerializer(many=True, required=True)


class PreferredBreadStatisticSerializer(serializers.Serializer):
    bread_name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class PreferredBreadStatisticsSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()
    members_with_preferences = serializers.IntegerField()
    members_without_preferences = serializers.IntegerField()
    breads = PreferredBreadStatisticSerializer(many=True)


class SolverDiagnosticSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=["info", "warning", "error"])
    category = serializers.CharField(allow_blank=True)
    bread_name = serializers.CharField(allow_null=True, required=False)
    location_name = serializers.CharField(allow_null=True, required=False)
    message = serializers.CharField()


class SolverErrorSerializer(serializers.Serializer):
    error = serializers.CharField()
    diagnostics = SolverDiagnosticSerializer(many=True, required=False, default=[])


class SolverPreviewRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    delivery_week = serializers.IntegerField()
    delivery_day = serializers.IntegerField(required=False, allow_null=True)
    max_solutions = serializers.IntegerField(default=5, required=False, min_value=1)


class SolverPreviewBreadQuantitySerializer(serializers.Serializer):
    bread_id = serializers.CharField()
    bread_name = serializers.CharField()
    total = serializers.IntegerField()
    deliveries = serializers.IntegerField()
    remaining = serializers.IntegerField()


class SolverPreviewSolutionSummarySerializer(serializers.Serializer):
    index = serializers.IntegerField()
    total_baked = serializers.IntegerField()
    total_remaining = serializers.IntegerField()
    sessions_used = serializers.IntegerField()
    quantities = SolverPreviewBreadQuantitySerializer(many=True)


class SolverPreviewResponseSerializer(serializers.Serializer):
    total_solutions = serializers.IntegerField()
    solutions = SolverPreviewSolutionSummarySerializer(many=True)
    diagnostics = SolverDiagnosticSerializer(many=True, required=False, default=list)


class SolverPreviewDetailStoveLayerSerializer(serializers.Serializer):
    layer = serializers.IntegerField()
    bread_id = serializers.CharField(required=False, allow_null=True)
    bread_name = serializers.CharField(required=False, allow_null=True)
    quantity = serializers.IntegerField()


class SolverPreviewDetailStoveSessionSerializer(serializers.Serializer):
    session = serializers.IntegerField()
    layers = SolverPreviewDetailStoveLayerSerializer(many=True)


class SolverPreviewDetailDistributionSerializer(serializers.Serializer):
    bread_id = serializers.CharField()
    bread_name = serializers.CharField()
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    count = serializers.IntegerField()


class SolverPreviewDetailResponseSerializer(serializers.Serializer):
    solution_index = serializers.IntegerField()
    total_solutions = serializers.IntegerField()
    quantities = SolverPreviewBreadQuantitySerializer(many=True)
    stove_sessions = SolverPreviewDetailStoveSessionSerializer(many=True)
    distribution = SolverPreviewDetailDistributionSerializer(many=True)


class SolverApplyRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    delivery_week = serializers.IntegerField()
    delivery_day = serializers.IntegerField(required=False, allow_null=True)
    solution_index = serializers.IntegerField(default=0)


class SolverApplyResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    solution_index = serializers.IntegerField()
    message = serializers.CharField()


class StoveSessionSerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = StoveSession
        fields = "__all__"
        read_only_fields = ["id"]


class BreadsPerPickupLocationPerWeekSerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)
    pickup_location_name = serializers.CharField(
        source="pickup_location.name", read_only=True
    )
    delivery_day = serializers.SerializerMethodField()

    class Meta:
        model = BreadsPerPickupLocationPerWeek
        fields = "__all__"
        read_only_fields = ["id"]

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_delivery_day(self, obj) -> int | None:
        return _get_pickup_location_delivery_day(self, obj)


class BreadBreakdownSerializer(serializers.Serializer):
    bread_id = serializers.CharField()
    bread_name = serializers.CharField()
    count = serializers.IntegerField()
    directly_chosen = serializers.IntegerField()


class AssignmentLogEntrySerializer(serializers.Serializer):
    member_name = serializers.CharField()
    member_id = serializers.CharField()
    status = serializers.ChoiceField(
        choices=["directly_chosen", "no_favorites", "got_favorite", "no_match"]
    )
    assigned_bread_id = serializers.CharField(allow_null=True)
    assigned_bread_name = serializers.CharField(allow_null=True)
    preferred_bread_names = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )


class LocationMetricsSerializer(serializers.Serializer):
    pickup_location_id = serializers.CharField()
    pickup_location_name = serializers.CharField()
    delivery_day = serializers.IntegerField()
    total_deliveries = serializers.IntegerField()
    directly_chosen = serializers.IntegerField()
    no_favorites = serializers.IntegerField()
    got_favorite = serializers.IntegerField()
    satisfied = serializers.IntegerField()
    satisfied_percentage = serializers.FloatField()
    no_match = serializers.IntegerField()
    bread_breakdown = BreadBreakdownSerializer(many=True)
    assignment_log = AssignmentLogEntrySerializer(many=True)


class PreferenceSatisfactionResponseSerializer(serializers.Serializer):
    locations = LocationMetricsSerializer(many=True)


class BreadSpecificsPerDeliveryDaySerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = BreadSpecificsPerDeliveryDay
        fields = "__all__"
        extra_kwargs = PIECE_COUNT_LIMITS | {
            "fixed_pieces": {"max_value": MAX_PIECES_PER_ENTRY}
        }
        # See BreadLabelSerializer.
        read_only_fields = ["id"]


class BreadSpecificsPerDeliveryDayBulkUpdateItemSerializer(serializers.Serializer):
    bread = serializers.PrimaryKeyRelatedField(queryset=Bread.objects.all())
    # All four are PositiveIntegerField columns with CHECK (>= 0).
    min_pieces = _piece_count()
    max_pieces = _piece_count()
    min_remaining_pieces = _piece_count()
    fixed_pieces = _piece_count()


class BreadSpecificsPerDeliveryDayBulkUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=0)
    delivery_week = serializers.IntegerField(min_value=1, max_value=53)
    delivery_day = serializers.IntegerField(min_value=0, max_value=6)
    updates = BreadSpecificsPerDeliveryDayBulkUpdateItemSerializer(many=True)


class PickupLocationDeliveryDaySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class PickupLocationsByDeliveryDayResponseSerializer(serializers.Serializer):
    pickup_locations = PickupLocationDeliveryDaySerializer(many=True)


class DeliveryDaysResponseSerializer(serializers.Serializer):
    days = serializers.ListField(child=serializers.IntegerField())


class BreadCapacityAllocationResponseSerializer(serializers.Serializer):
    pickup_locations = PickupLocationDeliveryDaySerializer(many=True)
    allocations = serializers.DictField(
        child=serializers.DictField(child=serializers.IntegerField(allow_null=True))
    )
