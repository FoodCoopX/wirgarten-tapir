import datetime

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.bakery.models import (
    Bread,
    BreadCapacityPickupLocation,
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
from tapir.utils.shortcuts import get_serializer_cache

# The ceiling a PositiveIntegerField gets from Postgres. A bulk endpoint that
# skips the ModelSerializer has to state it itself.
MAX_POSITIVE_INTEGER = 2147483647


def _piece_count():
    return serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=MAX_POSITIVE_INTEGER
    )


# A method field rather than source="pickup_location.delivery_day": the weekday
# is derived from the location's opening times, so reading it through the model
# costs one query per row.
def _get_pickup_location_delivery_day(serializer, obj) -> int | None:
    return PickupLocationDeliveryDayService.get_delivery_day(
        pickup_location_id=obj.pickup_location_id,
        cache=get_serializer_cache(serializer),
    )


class BreadLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreadLabel
        fields = "__all__"
        # A TapirModel id is a plain editable CharField, so DRF leaves it
        # writable under fields="__all__", and a PATCH carrying a forged id
        # makes Django INSERT a second row instead of updating this one.
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
        # Annotated once by IngredientViewSet; the fallback keeps the
        # serializer usable on its own.
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


class BreadListSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(read_only=True, required=False)
    delivery_count = serializers.IntegerField(read_only=True, required=False)
    available_capacity = serializers.IntegerField(read_only=True, required=False)
    # Served with the list, which BreadViewSet already prefetches, so the
    # member-facing cards do not need one HTTP request per bread.
    contents = BreadContentSerializer(many=True, read_only=True)

    class Meta:
        model = Bread
        fields = "__all__"
        # See BreadLabelSerializer.
        read_only_fields = ["id"]


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
        source="pickup_location.name", read_only=True
    )
    delivery_day = serializers.SerializerMethodField()

    bread_name = serializers.CharField(source="bread.name", read_only=True)

    class Meta:
        model = BreadCapacityPickupLocation
        fields = "__all__"
        # See BreadLabelSerializer.
        read_only_fields = ["id"]

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_delivery_day(self, obj) -> int | None:
        return _get_pickup_location_delivery_day(self, obj)


class BreadDeliverySerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source="bread.name", read_only=True)
    # The station, its labels, the weekday and the joker status are all
    # derived from the member's pickup location history and their jokers.
    pickup_location = serializers.SerializerMethodField()
    pickup_location_name = serializers.SerializerMethodField()
    pickup_location_street = serializers.SerializerMethodField()
    pickup_location_city = serializers.SerializerMethodField()
    delivery_day = serializers.SerializerMethodField()
    joker_taken = serializers.SerializerMethodField()
    # Served rather than left to the client to work out from the raw
    # configuration: the deadline is the same rule the API enforces on write.
    choosing_deadline = serializers.SerializerMethodField()
    can_still_choose = serializers.SerializerMethodField()

    class Meta:
        model = BreadDelivery
        # `bread` is the only thing a member may set; in particular
        # `subscription` must not be, or a slot could be reassigned to someone
        # else. `id` is listed too: it is a CharField pk, which DRF would
        # otherwise leave writable.
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
        # The station a slot resolves to decides which breads it can be given,
        # so this needs the instance and only applies on update.
        if self.instance is None:
            return bread

        if not BreadAvailabilityService.is_bread_available_for_delivery(
            self.instance, bread, cache=get_serializer_cache(self)
        ):
            raise serializers.ValidationError(
                f"'{bread.name}' ist in Woche "
                f"{self.instance.delivery_week}/{self.instance.year} an dieser "
                f"Abholstation nicht verfügbar."
            )
        return bread

    def _pickup_location(self, obj):
        return BreadDeliveryContextService.get_pickup_location(
            obj, cache=get_serializer_cache(self)
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
                obj, cache=get_serializer_cache(self)
            ),
            cache=get_serializer_cache(self),
        )

    @extend_schema_field(serializers.BooleanField())
    def get_joker_taken(self, obj) -> bool:
        return BreadDeliveryContextService.is_joker_taken(
            obj, cache=get_serializer_cache(self)
        )

    @extend_schema_field(serializers.DateField(allow_null=True))
    def get_choosing_deadline(self, obj) -> datetime.date | None:
        return BreadChoiceDeadlineService.get_deadline(
            year=obj.year,
            delivery_week=obj.delivery_week,
            pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                obj, cache=get_serializer_cache(self)
            ),
            cache=get_serializer_cache(self),
        )

    @extend_schema_field(serializers.BooleanField())
    def get_can_still_choose(self, obj) -> bool:
        return BreadChoiceDeadlineService.can_still_choose(
            year=obj.year,
            delivery_week=obj.delivery_week,
            pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                obj, cache=get_serializer_cache(self)
            ),
            cache=get_serializer_cache(self),
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
    # Related fields rather than plain strings, so an unknown or over-long id
    # is a 400 rather than reaching the database. A ListField rather than
    # many=True: ManyRelatedField takes no max_length, and this way
    # drf-spectacular emits maxItems into the schema, so the generated client
    # carries the same limit the modal enforces.
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
    """
    Several stations of one week in a single response.

    One request per station would re-derive the whole week each time, since
    each request starts with an empty cache.
    """

    lists = PickupListForLocationSerializer(many=True)


class BreadCapacityUpdateItemSerializer(serializers.Serializer):
    # Related fields rather than raw strings: the ids go straight into
    # update_or_create, so an unknown one has to be rejected here.
    pickup_location = serializers.PrimaryKeyRelatedField(
        queryset=PickupLocation.objects.all(), required=True
    )
    bread = serializers.PrimaryKeyRelatedField(
        queryset=Bread.objects.all(), required=True
    )
    # The column is a PositiveIntegerField with CHECK (capacity >= 0).
    capacity = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=MAX_POSITIVE_INTEGER
    )


class BreadCapacityBulkUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=True, min_value=0)
    delivery_week = serializers.IntegerField(required=True, min_value=1, max_value=53)
    updates = BreadCapacityUpdateItemSerializer(many=True, required=True)


###---------------- Serializers for solver results and requests ------------------ ##


class PreferredBreadStatisticSerializer(serializers.Serializer):
    bread_name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class PreferredBreadStatisticsSerializer(serializers.Serializer):
    """Declared so the endpoint appears in the schema with a real shape."""

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
