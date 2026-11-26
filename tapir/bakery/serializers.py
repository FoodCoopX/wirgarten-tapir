import datetime

from django.db import models
from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.bakery.models import (
    Bread,
    BreadContent,
    BreadDelivery,
    BreadGroup,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    BreadsPerPickupLocationPerWeek,
    BreadsToBakePerWeek,
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
from tapir.bakery.services.direct_order_limit_service import (
    CAPACITY_SOURCE_BREAD_MAX,
    CAPACITY_SOURCE_DAY_MAX,
    CAPACITY_SOURCE_FIXED,
    CAPACITY_SOURCE_GROUP_MAX,
)
from tapir.bakery.utils import (
    ISO_WEEK_MISSING_MESSAGE,
    MAX_PREFERRED_BREADS,
    is_valid_iso_week,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)

# A plausibility limit, not a column limit: a station gets loaves in the
# hundreds, so anything above this is a typo rather than an order.
MAX_PIECES_PER_ENTRY = 1000


def validate_iso_week(data: dict, year_field: str, week_field: str):
    """For a serializer's validate(): KW 53 exists only in some years."""
    if not is_valid_iso_week(data[year_field], data[week_field]):
        raise serializers.ValidationError({week_field: ISO_WEEK_MISSING_MESSAGE})


def _piece_count():
    return serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=MAX_PIECES_PER_ENTRY
    )


def _get_pickup_location_delivery_day(serializer, obj) -> int | None:
    return PickupLocationDeliveryDayService.get_delivery_day(
        pickup_location_id=obj.pickup_location_id,
        cache=serializer.context["cache"],
    )


BREAD_NAME_SOURCE = "bread.name"


class BreadLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreadLabel
        fields = "__all__"
        # A TapirModel id is a plain CharField, which DRF would otherwise leave
        # writable under fields="__all__".
        read_only_fields = ["id"]


class BreadGroupSerializer(serializers.ModelSerializer):
    bread_names = serializers.SerializerMethodField()

    class Meta:
        model = BreadGroup
        fields = "__all__"
        # See BreadLabelSerializer.
        read_only_fields = ["id"]

    def get_bread_names(self, obj) -> list[str]:
        # BreadGroupViewSet prefetches them in the database's name order, the
        # one the oven plan and the baking list use.
        return [bread.name for bread in obj.breads.all()]


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


class BreadPictureField(serializers.ImageField):
    def to_representation(self, value):
        if not value:
            return None
        url = reverse("bakery:bread-picture", args=[value.instance.id])
        # The stored name changes on every upload, which busts browser caches.
        url = f"{url}?v={value.name.rsplit('/', 1)[-1]}"
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


BREAD_PICTURE_FIELD_MAPPING = {
    **serializers.ModelSerializer.serializer_field_mapping,
    models.ImageField: BreadPictureField,
}


PIECE_COUNT_LIMITS = {
    field: {"max_value": MAX_PIECES_PER_ENTRY}
    for field in ["min_pieces", "max_pieces", "min_remaining_pieces"]
}


CAPACITY_HELP = (
    "Set for a station's week only: the bread's direct-order limit on the "
    "station's delivery day, null when unlimited."
)
DELIVERY_COUNT_HELP = (
    "Set for a station's week only: direct orders of the bread on the "
    "station's delivery day, over all stations delivered that day."
)
AVAILABLE_CAPACITY_HELP = (
    "Set for a station's week only: what is left of the bread's limit and "
    "its group's, null when neither has one."
)


class BreadListSerializer(serializers.ModelSerializer):
    serializer_field_mapping = BREAD_PICTURE_FIELD_MAPPING
    capacity = serializers.IntegerField(
        read_only=True, required=False, allow_null=True, help_text=CAPACITY_HELP
    )
    delivery_count = serializers.IntegerField(
        read_only=True, required=False, help_text=DELIVERY_COUNT_HELP
    )
    available_capacity = serializers.IntegerField(
        read_only=True,
        required=False,
        allow_null=True,
        help_text=AVAILABLE_CAPACITY_HELP,
    )
    contents = BreadContentSerializer(many=True, read_only=True)
    group_name = serializers.CharField(
        source="group.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Bread
        fields = "__all__"
        extra_kwargs = PIECE_COUNT_LIMITS
        # See BreadLabelSerializer.
        read_only_fields = ["id"]


class BreadDetailSerializer(serializers.ModelSerializer):
    serializer_field_mapping = BREAD_PICTURE_FIELD_MAPPING
    labels = BreadLabelSerializer(many=True, read_only=True)
    contents = BreadContentSerializer(many=True, read_only=True)
    label_names = serializers.SerializerMethodField()
    capacity = serializers.IntegerField(
        read_only=True, required=False, allow_null=True, help_text=CAPACITY_HELP
    )
    delivery_count = serializers.IntegerField(
        read_only=True, required=False, help_text=DELIVERY_COUNT_HELP
    )
    available_capacity = serializers.IntegerField(
        read_only=True,
        required=False,
        allow_null=True,
        help_text=AVAILABLE_CAPACITY_HELP,
    )

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
    bread_name = serializers.CharField(source=BREAD_NAME_SOURCE, read_only=True)
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
    delivery_day_is_over = serializers.BooleanField(
        help_text="Its breads can no longer be switched on or off."
    )
    breads = BreadListSerializer(many=True)


class ToggleBreadRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    delivery_week = serializers.IntegerField(min_value=1, max_value=53)
    delivery_day = serializers.IntegerField(min_value=0, max_value=6)
    bread_id = serializers.CharField()
    is_active = serializers.BooleanField()
    dry_run = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "Changes nothing; cleared_choices says how many choices switching "
            "the bread off would clear."
        ),
    )

    def validate(self, data):
        validate_iso_week(data, "year", "delivery_week")
        return data


class ToggleBreadResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    created = serializers.BooleanField(required=False)
    deleted = serializers.BooleanField(required=False)
    cleared_choices = serializers.IntegerField(
        required=False,
        help_text=(
            "Members' choices of the bread on that day, cleared when it is "
            "switched off, or that would be with dry_run."
        ),
    )
    bread_id = serializers.CharField()


class WeekSettingsSourceSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    delivery_week = serializers.IntegerField()
    bread_count = serializers.IntegerField(
        help_text="Distinct active breads baked that week, over all its days."
    )


class WeekSettingsSourcesResponseSerializer(serializers.Serializer):
    sources = WeekSettingsSourceSerializer(
        many=True,
        help_text=(
            "Weeks before the given one that bake an active bread, latest first."
        ),
    )


class CopyWeekSettingsRequestSerializer(serializers.Serializer):
    source_year = serializers.IntegerField()
    source_week = serializers.IntegerField(min_value=1, max_value=53)
    target_year = serializers.IntegerField()
    target_week = serializers.IntegerField(min_value=1, max_value=53)
    dry_run = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Changes nothing; the response says what copying would do.",
    )

    def validate(self, data):
        validate_iso_week(data, "source_year", "source_week")
        validate_iso_week(data, "target_year", "target_week")
        return data


class CopyWeekSettingsResponseSerializer(serializers.Serializer):
    copied_days = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Days of the target week replaced, or that would be with dry_run.",
    )
    kept_days = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Days of the target week that are over and keep their settings.",
    )
    cleared_choices = serializers.IntegerField(
        help_text="Members' choices of breads the copy stops baking on their day."
    )


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
    bread_name = serializers.CharField(source=BREAD_NAME_SOURCE, read_only=True)

    class Meta:
        model = StoveSession
        fields = "__all__"
        read_only_fields = ["id"]


class BreadsToBakePerWeekSerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source=BREAD_NAME_SOURCE, read_only=True)

    class Meta:
        model = BreadsToBakePerWeek
        fields = "__all__"
        read_only_fields = ["id"]


class BreadsPerPickupLocationPerWeekSerializer(serializers.ModelSerializer):
    bread_name = serializers.CharField(source=BREAD_NAME_SOURCE, read_only=True)
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
    bread_name = serializers.CharField(source=BREAD_NAME_SOURCE, read_only=True)

    class Meta:
        model = BreadSpecificsPerDeliveryDay
        fields = "__all__"
        extra_kwargs = PIECE_COUNT_LIMITS | {
            "fixed_pieces": {"max_value": MAX_PIECES_PER_ENTRY}
        }
        # See BreadLabelSerializer.
        read_only_fields = ["id"]

    def validate(self, data):
        # A partial update may change only one of the two.
        validate_iso_week(
            {
                "year": data.get("year", getattr(self.instance, "year", None)),
                "delivery_week": data.get(
                    "delivery_week", getattr(self.instance, "delivery_week", None)
                ),
            },
            "year",
            "delivery_week",
        )
        return data


class BreadSpecificsPerDeliveryDayBulkUpdateItemSerializer(serializers.Serializer):
    """A field left out keeps its value; null clears it."""

    bread = serializers.PrimaryKeyRelatedField(queryset=Bread.objects.all())
    # All four are PositiveIntegerField columns with CHECK (>= 0).
    min_pieces = _piece_count()
    max_pieces = _piece_count()
    min_remaining_pieces = _piece_count()
    fixed_pieces = _piece_count()
    max_direct_order_percent = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=100
    )


class BreadSpecificsPerDeliveryDayBulkUpdateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=0)
    delivery_week = serializers.IntegerField(min_value=1, max_value=53)
    delivery_day = serializers.IntegerField(min_value=0, max_value=6)
    updates = BreadSpecificsPerDeliveryDayBulkUpdateItemSerializer(many=True)

    def validate(self, data):
        validate_iso_week(data, "year", "delivery_week")
        return data


class PickupLocationDeliveryDaySerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class PickupLocationsByDeliveryDayResponseSerializer(serializers.Serializer):
    pickup_locations = PickupLocationDeliveryDaySerializer(many=True)


class DeliveryDaysResponseSerializer(serializers.Serializer):
    days = serializers.ListField(child=serializers.IntegerField())


class BreadDirectOrderLimitSerializer(serializers.Serializer):
    bread_id = serializers.CharField()
    bread_name = serializers.CharField()
    group_id = serializers.CharField(allow_null=True)
    group_name = serializers.CharField(allow_null=True)
    total_capacity = serializers.IntegerField(
        allow_null=True,
        help_text="What may be baked of the bread that day; null when nothing bounds it.",
    )
    total_capacity_source = serializers.ChoiceField(
        choices=[
            CAPACITY_SOURCE_FIXED,
            CAPACITY_SOURCE_DAY_MAX,
            CAPACITY_SOURCE_GROUP_MAX,
            CAPACITY_SOURCE_BREAD_MAX,
        ],
        allow_null=True,
    )
    min_remaining = serializers.IntegerField()
    default_percent = serializers.IntegerField()
    percent = serializers.IntegerField()
    limit = serializers.IntegerField(
        allow_null=True,
        help_text="How many members may choose directly; null means unlimited.",
    )
    ordered = serializers.IntegerField()


class GroupDirectOrderLimitSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    group_name = serializers.CharField()
    bread_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="The breads sharing the group's limit: those without a fixed amount.",
    )
    max_pieces = serializers.IntegerField(allow_null=True)
    fixed_pieces = serializers.IntegerField(
        help_text="What the group's breads with a fixed amount take of max_pieces."
    )
    total_capacity = serializers.IntegerField(
        allow_null=True, help_text="max_pieces less fixed_pieces."
    )
    min_remaining = serializers.IntegerField()
    open_min_pieces = serializers.IntegerField(
        help_text=(
            "Day minimums of the group's breads not yet covered by their own "
            "orders and Min. Rest, held back like Min. Rest."
        )
    )
    percent = serializers.IntegerField()
    limit = serializers.IntegerField(allow_null=True)
    ordered = serializers.IntegerField()


class DirectOrderLimitsResponseSerializer(serializers.Serializer):
    breads = BreadDirectOrderLimitSerializer(many=True)
    groups = GroupDirectOrderLimitSerializer(many=True)
