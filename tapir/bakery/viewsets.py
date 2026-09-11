from functools import cached_property

from django.db import transaction
from django.db.models import Exists, OuterRef, ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response

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
from tapir.bakery.serializers import (
    BreadCapacityBulkUpdateSerializer,
    BreadCapacityPickupLocationSerializer,
    BreadContentSerializer,
    BreadDeliverySerializer,
    BreadDetailSerializer,
    BreadLabelSerializer,
    BreadListSerializer,
    BreadSpecificsPerDeliveryDayBulkUpdateSerializer,
    BreadSpecificsPerDeliveryDaySerializer,
    BreadsPerPickupLocationPerWeekSerializer,
    IngredientSerializer,
    PreferredBreadsBulkUpdateSerializer,
    PreferredBreadSerializer,
    StoveSessionSerializer,
)
from tapir.bakery.services.bread_availability_service import (
    BreadAvailabilityService,
)
from tapir.bakery.services.bread_choice_service import (
    BreadChoiceNotAllowed,
    BreadChoiceService,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.utils import int_query_param, str_to_bool
from tapir.generic_exports.permissions import HasCoopManagePermission, IsReadOnly
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self


class ProtectedDeleteConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "protected"


class RequestCacheMixin:
    """One TapirCache for the whole request, shared with the serializer."""

    @cached_property
    def tapir_cache(self) -> dict:
        return {}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = self.tapir_cache
        return context


class ProtectedDeleteMixin:
    """
    Turns a blocked delete into a 409 the caller can act on.

    Bread and Ingredient are both referenced with on_delete=PROTECT, so
    deleting one that is still in use would otherwise surface as a 500 with no
    hint of what was in the way.
    """

    protected_delete_message = (
        "Der Eintrag wird noch verwendet und kann nicht gelöscht werden. "
        "Setze ihn stattdessen auf inaktiv."
    )

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except ProtectedError as error:
            raise ProtectedDeleteConflict(self.protected_delete_message) from error


@extend_schema(tags=["bakery"])
class BreadLabelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bread labels/categories
    """

    queryset = BreadLabel.objects.all()
    serializer_class = BreadLabelSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsReadOnly | HasCoopManagePermission,
    ]


@extend_schema(tags=["bakery"])
class IngredientViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing ingredients
    """

    protected_delete_message = (
        "Diese Zutat wird noch in Rezepten verwendet und kann nicht gelöscht werden."
    )

    # Annotated so can_be_deleted does not cost an EXISTS per row.
    queryset = Ingredient.objects.annotate(
        is_used=Exists(BreadContent.objects.filter(ingredient=OuterRef("pk")))
    )
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="is_organic", type=bool, description="Filter by organic status"
            ),
            OpenApiParameter(
                name="is_active", type=bool, description="Filter by active status"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Filter by organic status if provided"""
        queryset = super().get_queryset()
        is_organic = str_to_bool(self.request.query_params.get("is_organic", None))
        is_active = str_to_bool(self.request.query_params.get("is_active", None))

        if is_organic is not None:
            queryset = queryset.filter(is_organic=is_organic)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        return queryset


@extend_schema(tags=["bakery"])
class BreadViewSet(RequestCacheMixin, ProtectedDeleteMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing bread variants
    """

    protected_delete_message = (
        "Dieses Brot ist schon Wochen zugeordnet und kann nicht gelöscht "
        "werden. Setze es stattdessen auf inaktiv."
    )

    queryset = Bread.objects.prefetch_related("labels", "contents__ingredient").all()
    permission_classes = [
        permissions.IsAuthenticated,
        IsReadOnly | HasCoopManagePermission,
    ]

    @extend_schema(
        summary="Get all ingredients for a specific bread",
        responses={200: BreadContentSerializer(many=True)},
    )
    @action(detail=True, methods=["get", "post"], url_path="contents")
    def contents(self, request: Request, pk=None) -> Response:
        """Get or add contents (ingredients) for a specific bread"""
        bread = self.get_object()

        if request.method == "GET":
            contents = BreadContent.objects.filter(bread=bread).select_related(
                "ingredient"
            )
            serializer = BreadContentSerializer(contents, many=True)
            return Response(serializer.data)

        # POST
        data = request.data.copy()
        data["bread"] = bread.id
        serializer = BreadContentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
        """Use detailed serializer for retrieve, list serializer otherwise"""
        if self.action == "retrieve":
            return BreadDetailSerializer
        return BreadListSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="label_id", type=str, description="Filter by label ID"
            ),
            OpenApiParameter(
                name="is_active", type=bool, description="Filter by active status"
            ),
            OpenApiParameter(
                name="pickup_location_id",
                type=str,
                description="Filter by pickup location ID (requires year and week)",
            ),
            OpenApiParameter(
                name="year",
                type=int,
                description="Filter by delivery year (requires pickup_location_id and week)",
            ),
            OpenApiParameter(
                name="week",
                type=int,
                description="Filter by delivery week (requires pickup_location_id and year)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Filter by label and active status if provided"""
        queryset = super().get_queryset()

        # Filter by label name
        label_id = self.request.query_params.get("label_id", None)
        pickup_location_id = self.request.query_params.get("pickup_location_id", None)
        year = int_query_param(self.request, "year")
        week = int_query_param(self.request, "week")
        if label_id:
            queryset = queryset.filter(labels__id=label_id)

        # Filter by active status
        is_active = str_to_bool(self.request.query_params.get("is_active", None))

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if pickup_location_id and year and week:
            queryset = BreadAvailabilityService.annotate_remaining_capacity(
                queryset,
                pickup_location_id=pickup_location_id,
                year=year,
                delivery_week=week,
                cache=self.tapir_cache,
            )

        queryset = queryset.order_by("name")

        return queryset

    @extend_schema(
        summary="Get breads filtered by multiple label IDs",
        parameters=[
            OpenApiParameter(
                name="label_ids",
                type=str,
                description="Comma-separated label IDs",
                required=True,
            )
        ],
        responses={
            200: BreadListSerializer(many=True),
            400: OpenApiResponse(description="Invalid label IDs"),
        },
    )
    @action(detail=False, methods=["get"], url_path="by-labels")
    def by_labels(self, request: Request) -> Response:
        """Get breads filtered by multiple label IDs"""
        label_ids = [
            label_id.strip()
            for label_id in request.query_params.get("label_ids", "").split(",")
            if label_id.strip()
        ]

        if not label_ids:
            return Response({"error": "Invalid label IDs provided"}, status=400)

        # Validate that all provided IDs correspond to existing labels
        existing_count = BreadLabel.objects.filter(id__in=label_ids).count()
        if existing_count != len(label_ids):
            return Response({"error": "Invalid label IDs provided"}, status=400)

        breads = self.get_queryset().filter(labels__id__in=label_ids).distinct()
        serializer = self.get_serializer(breads, many=True)
        return Response(serializer.data)


@extend_schema(tags=["bakery"])
class BreadContentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bread contents (ingredient amounts)
    """

    queryset = BreadContent.objects.select_related("bread", "ingredient").all()
    serializer_class = BreadContentSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsReadOnly | HasCoopManagePermission,
    ]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="bread", type=str, description="Filter by bread ID"),
            OpenApiParameter(
                name="ingredient_id", type=str, description="Filter by ingredient ID"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Filter by bread or ingredient if provided"""
        queryset = super().get_queryset()

        # Filter by bread ID
        bread_id = self.request.query_params.get("bread", None)
        if bread_id:
            queryset = queryset.filter(bread_id=bread_id)

        # Filter by ingredient ID
        ingredient_id = self.request.query_params.get("ingredient_id", None)
        if ingredient_id:
            queryset = queryset.filter(ingredient_id=ingredient_id)

        return queryset


@extend_schema(tags=["bakery"])
class BreadCapacityPickupLocationViewSet(viewsets.ModelViewSet):
    queryset = BreadCapacityPickupLocation.objects.select_related(
        "bread", "pickup_location"
    ).all()
    serializer_class = BreadCapacityPickupLocationSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="year", type=int),
            OpenApiParameter(name="week", type=int),
            OpenApiParameter(name="pickup_location_ids[]", type=str, many=True),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        year = int_query_param(self.request, "year")
        week = int_query_param(self.request, "week")
        pickup_location_ids = self.request.query_params.getlist("pickup_location_ids[]")

        if year:
            queryset = queryset.filter(year=year)
        if week:
            queryset = queryset.filter(delivery_week=week)
        if pickup_location_ids:
            queryset = queryset.filter(pickup_location__id__in=pickup_location_ids)

        return queryset

    @extend_schema(
        summary="Bulk create/update/delete bread capacities",
        request=BreadCapacityBulkUpdateSerializer,
        responses={
            200: OpenApiResponse(description='{"status": "success"}'),
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request: Request) -> Response:
        """Bulk create/update/delete capacities"""
        # Through the serializer the schema already advertises, like the
        # sibling bulk_update below.
        serializer = BreadCapacityBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        week = data["delivery_week"]

        for update in data["updates"]:
            # PrimaryKeyRelatedField hands back the objects, already validated.
            pickup_location_id = update["pickup_location"].pk
            bread_id = update["bread"].pk
            capacity = update.get("capacity")

            if capacity is None:
                # Delete
                BreadCapacityPickupLocation.objects.filter(
                    year=year,
                    delivery_week=week,
                    pickup_location_id=pickup_location_id,
                    bread_id=bread_id,
                ).delete()
            else:
                # Create or update
                BreadCapacityPickupLocation.objects.update_or_create(
                    year=year,
                    delivery_week=week,
                    pickup_location_id=pickup_location_id,
                    bread_id=bread_id,
                    defaults={"capacity": capacity},
                )

        return Response({"status": "success"})


@extend_schema(tags=["bakery"])
class BreadDeliveryViewSet(RequestCacheMixin, viewsets.ModelViewSet):
    # Needs a docstring of its own: without one the class inherits
    # RequestCacheMixin's, and drf-spectacular publishes that as the endpoint
    # description.
    """A member's bread slots: one per delivered week per share."""

    queryset = BreadDelivery.objects.all()
    serializer_class = BreadDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    # Rows are created and deleted by ensure_bread_deliveries_for_member, never
    # over the API. Members only ever PATCH a bread onto an existing slot, and
    # create/update/destroy would bypass the capacity check entirely.
    http_method_names = ["get", "patch", "head", "options"]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="year", type=int),
            OpenApiParameter(name="delivery_week", type=int),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        if kwargs.get("many") and args:
            # The serializer derives the station and the joker status per row,
            # so preload both for the whole page at once rather than letting
            # each row go and ask for its own member.
            member_ids = {delivery.subscription.member_id for delivery in list(args[0])}
            TapirCache.get_jokers_by_member_id_for_members(
                member_ids=member_ids, cache=self.tapir_cache
            )
            MemberPickupLocationService.get_member_pickup_locations_objects_for_members(
                member_ids=member_ids, cache=self.tapir_cache
            )
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        # Scoped unconditionally, not just when member_id is given: get_object()
        # runs through here too, so this is what secures the detail routes. A
        # foreign pk 404s instead of being readable or writable.
        if not self.request.user.has_perm(Permission.Accounts.MANAGE):
            queryset = queryset.filter(subscription__member_id=self.request.user.pk)

        member_id = self.request.query_params.get("member_id", None)
        year = int_query_param(self.request, "year")
        delivery_week = int_query_param(self.request, "delivery_week")
        if member_id is not None:
            queryset = queryset.filter(subscription__member__id=member_id)
        if year is not None:
            queryset = queryset.filter(year=year)
        if delivery_week is not None:
            queryset = queryset.filter(delivery_week=delivery_week)

        # subscription__member is what the derived pickup location and joker
        # status are resolved from.
        return queryset.select_related("bread", "subscription__member")

    @extend_schema(
        responses={
            200: BreadDeliverySerializer,
            400: OpenApiResponse(
                description=(
                    "Choosing is closed for this week, not released for "
                    "members, or no capacity is left for the selected bread"
                )
            ),
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        Update a bread delivery with capacity checking and locking.

        When a bread is being selected, this method:
        1. Locks the relevant capacity and delivery rows to prevent race conditions
        2. Checks if there's available capacity for the selected bread
        3. Only allows the update if capacity is available
        """
        # Absent and explicitly null are different requests: leaving the key
        # out is "change something else", sending null is "clear my choice",
        # and clearing is subject to the choosing deadline like any other
        # change.
        if "bread" not in request.data:
            return super().partial_update(request, *args, **kwargs)

        new_bread_id = request.data.get("bread")

        with transaction.atomic():
            # Through get_queryset(), so the ownership scoping applies here
            # too. select_related(None) drops the joins it adds for
            # serialization: they are nullable, and Postgres refuses FOR UPDATE
            # on the nullable side of an outer join.
            delivery = get_object_or_404(
                self.get_queryset().select_related(None).select_for_update(),
                pk=kwargs["pk"],
            )

            old_bread_id = str(delivery.bread_id) if delivery.bread_id else None
            if old_bread_id == new_bread_id:
                return super().partial_update(request, *args, **kwargs)

            cache = self.tapir_cache
            pickup_location_id = BreadDeliveryContextService.get_pickup_location_id(
                delivery, cache=cache
            )

            try:
                # A member is bound by the choosing rules; staff answering the
                # phone are not.
                if not request.user.has_perm(Permission.Accounts.MANAGE):
                    BreadChoiceService.check_member_may_change(
                        delivery, pickup_location_id, cache=cache
                    )
                if new_bread_id and pickup_location_id:
                    BreadChoiceService.check_capacity_available(
                        delivery, new_bread_id, pickup_location_id, cache=cache
                    )
            except BreadChoiceNotAllowed as error:
                return Response(
                    {"error": str(error)}, status=status.HTTP_400_BAD_REQUEST
                )

            return super().partial_update(request, *args, **kwargs)


@extend_schema(
    tags=["bakery"],
    description="Read preferred breads for a member.",
    responses={200: PreferredBreadSerializer},
)
class PreferredBreadViewSet(viewsets.ReadOnlyModelViewSet):
    """Favourites are read here and written through bulk-update only."""

    queryset = PreferredBread.objects.all()
    serializer_class = PreferredBreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="member_id",
                type=str,
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        # super(), not self.queryset: the class-level queryset object keeps
        # its _result_cache, which would freeze the rows at the first request
        # of the worker process.
        queryset = super().get_queryset()
        # Without this a bare list dumps the whole member -> favourites map.
        if not self.request.user.has_perm(Permission.Accounts.MANAGE):
            queryset = queryset.filter(member_id=self.request.user.pk)

        member_id = self.request.query_params.get("member_id")
        if member_id:
            queryset = queryset.filter(member__id=member_id)
        return queryset

    @extend_schema(
        request=PreferredBreadsBulkUpdateSerializer,
        responses={200: PreferredBreadsBulkUpdateSerializer},
        description="Bulk update preferred breads for a member. Replaces all breads for the member with the provided list.",
        tags=["bakery"],
    )
    @action(detail=True, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request, pk=None):
        # Unlike the inherited detail routes, <pk> here is a Member id, not a
        # PreferredBread id, so the queryset scoping does not cover it.
        # Permission first, so an unauthorised caller cannot tell "no such
        # member" from "not your member". Then resolve, because the FK is
        # DEFERRABLE INITIALLY DEFERRED and an unknown id would otherwise
        # survive get_or_create and fail at commit, too late for a 404.
        check_permission_or_self(pk, request)
        get_object_or_404(Member, id=pk)

        serializer = PreferredBreadsBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        breads = serializer.validated_data["breads"]
        preferred, _ = PreferredBread.objects.get_or_create(member_id=pk)

        preferred.breads.set(breads)
        return Response(serializer.data)


@extend_schema(tags=["bakery"])
class StoveSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing stove sessions (baking plan).
    Read-only - sessions are created by the solver.
    """

    queryset = StoveSession.objects.select_related("bread").all()
    serializer_class = StoveSessionSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="year",
                type=int,
                required=False,
            ),
            OpenApiParameter(
                name="delivery_week",
                type=int,
                required=False,
            ),
            OpenApiParameter(
                name="delivery_day",
                type=int,
                required=False,
            ),
        ],
        responses={200: StoveSessionSerializer(many=True)},
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        """Get all stove sessions, optionally filtered by year/week/day"""
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Filter by year, week, and day if provided"""
        queryset = super().get_queryset()

        year = int_query_param(self.request, "year")
        delivery_week = int_query_param(self.request, "delivery_week")
        delivery_day = int_query_param(self.request, "delivery_day")

        if year is not None:
            queryset = queryset.filter(year=year)
        if delivery_week is not None:
            queryset = queryset.filter(delivery_week=delivery_week)
        if delivery_day is not None:
            queryset = queryset.filter(delivery_day=delivery_day)

        return queryset.order_by("session_number", "layer_number")


@extend_schema(tags=["bakery"])
class BreadsPerPickupLocationPerWeekViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing breads per pickup location per week.
    Read-only - data is created by the solver.
    """

    queryset = BreadsPerPickupLocationPerWeek.objects.select_related(
        "bread", "pickup_location"
    ).all()
    serializer_class = BreadsPerPickupLocationPerWeekSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="year",
                type=int,
                required=False,
            ),
            OpenApiParameter(
                name="delivery_week",
                type=int,
                required=False,
            ),
            OpenApiParameter(
                name="delivery_day",
                type=int,
                required=False,
            ),
        ],
        responses={200: BreadsPerPickupLocationPerWeekSerializer(many=True)},
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        """Get all breads per pickup location per week, optionally filtered by year/week/day"""
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Filter by year, week, and day if provided"""
        queryset = super().get_queryset()

        year = int_query_param(self.request, "year")
        delivery_week = int_query_param(self.request, "delivery_week")
        delivery_day = int_query_param(self.request, "delivery_day")

        if year is not None:
            queryset = queryset.filter(year=year)
        if delivery_week is not None:
            queryset = queryset.filter(delivery_week=delivery_week)
        if delivery_day is not None:
            # A station's delivery day is the earliest of its opening days,
            # not merely any day it is open.
            queryset = queryset.filter(
                pickup_location_id__in=PickupLocationDeliveryDayService.get_pickup_location_ids_for_delivery_day(
                    day=delivery_day, cache={}
                )
            )

        return queryset.order_by("bread__name")


@extend_schema(tags=["bakery"])
class BreadSpecificsPerDeliveryDayViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bread-specific overrides per delivery day.
    Only created when overrides to the bread defaults are needed.
    """

    queryset = BreadSpecificsPerDeliveryDay.objects.select_related("bread").all()
    serializer_class = BreadSpecificsPerDeliveryDaySerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="year", type=int, required=False),
            OpenApiParameter(name="delivery_week", type=int, required=False),
            OpenApiParameter(name="delivery_day", type=int, required=False),
            OpenApiParameter(name="bread_id", type=str, required=False),
        ],
        responses={200: BreadSpecificsPerDeliveryDaySerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        year = int_query_param(self.request, "year")
        delivery_week = int_query_param(self.request, "delivery_week")
        delivery_day = int_query_param(self.request, "delivery_day")
        bread_id = self.request.query_params.get("bread_id")

        if year is not None:
            queryset = queryset.filter(year=year)
        if delivery_week is not None:
            queryset = queryset.filter(delivery_week=delivery_week)
        if delivery_day is not None:
            queryset = queryset.filter(delivery_day=delivery_day)
        if bread_id is not None:
            queryset = queryset.filter(bread_id=bread_id)

        return queryset.order_by("delivery_day", "bread__name")

    @extend_schema(
        summary="Bulk create/update/delete bread specifics per delivery day",
        request=BreadSpecificsPerDeliveryDayBulkUpdateSerializer,
        responses={
            200: OpenApiResponse(description='{"status": "success"}'),
            400: OpenApiResponse(description="Validation errors"),
        },
    )
    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request: Request) -> Response:
        serializer = BreadSpecificsPerDeliveryDayBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        year = data["year"]
        delivery_week = data["delivery_week"]
        delivery_day = data["delivery_day"]

        for update in data["updates"]:
            bread_id = update["bread"].pk
            # if all fields are None, delete the entry
            field_values = {
                k: update.get(k)
                for k in [
                    "min_pieces",
                    "max_pieces",
                    "min_remaining_pieces",
                    "fixed_pieces",
                ]
            }

            if all(v is None for v in field_values.values()):
                BreadSpecificsPerDeliveryDay.objects.filter(
                    year=year,
                    delivery_week=delivery_week,
                    delivery_day=delivery_day,
                    bread_id=bread_id,
                ).delete()
            else:
                BreadSpecificsPerDeliveryDay.objects.update_or_create(
                    year=year,
                    delivery_week=delivery_week,
                    delivery_day=delivery_day,
                    bread_id=bread_id,
                    defaults=field_values,
                )

        return Response({"status": "success"})
