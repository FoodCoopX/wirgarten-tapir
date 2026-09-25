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
from tapir.bakery.permissions import IsReadOnly
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
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
    """Turns a delete blocked by on_delete=PROTECT into a 409."""

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
    queryset = BreadLabel.objects.all()
    serializer_class = BreadLabelSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        IsReadOnly | HasCoopManagePermission,
    ]


@extend_schema(tags=["bakery"])
class IngredientViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    protected_delete_message = (
        "Diese Zutat wird noch in Rezepten verwendet und kann nicht gelöscht werden."
    )

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
        bread = self.get_object()

        if request.method == "GET":
            contents = BreadContent.objects.filter(bread=bread).select_related(
                "ingredient"
            )
            serializer = BreadContentSerializer(contents, many=True)
            return Response(serializer.data)

        data = request.data.copy()
        data["bread"] = bread.id
        serializer = BreadContentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_serializer_class(self):
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
        queryset = super().get_queryset()

        label_id = self.request.query_params.get("label_id", None)
        pickup_location_id = self.request.query_params.get("pickup_location_id", None)
        year = int_query_param(self.request, "year")
        week = int_query_param(self.request, "week")
        if label_id:
            queryset = queryset.filter(labels__id=label_id)

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
        label_ids = [
            label_id.strip()
            for label_id in request.query_params.get("label_ids", "").split(",")
            if label_id.strip()
        ]

        if not label_ids:
            return Response({"error": "Invalid label IDs provided"}, status=400)

        existing_count = BreadLabel.objects.filter(id__in=label_ids).count()
        if existing_count != len(label_ids):
            return Response({"error": "Invalid label IDs provided"}, status=400)

        breads = self.get_queryset().filter(labels__id__in=label_ids).distinct()
        serializer = self.get_serializer(breads, many=True)
        return Response(serializer.data)


@extend_schema(tags=["bakery"])
class BreadContentViewSet(viewsets.ModelViewSet):
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
        queryset = super().get_queryset()

        bread_id = self.request.query_params.get("bread", None)
        if bread_id:
            queryset = queryset.filter(bread_id=bread_id)

        ingredient_id = self.request.query_params.get("ingredient_id", None)
        if ingredient_id:
            queryset = queryset.filter(ingredient_id=ingredient_id)

        return queryset


@extend_schema(tags=["bakery"])
class BreadDeliveryViewSet(RequestCacheMixin, viewsets.ModelViewSet):
    # Without a docstring of its own, drf-spectacular publishes
    # RequestCacheMixin's as this endpoint's description.
    """A member's bread slots: one per delivered week per share."""

    queryset = BreadDelivery.objects.all()
    serializer_class = BreadDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]
    # Rows are created and deleted by BreadDeliveryService, never over the API.
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

    def get_queryset(self):
        queryset = super().get_queryset()

        # get_object() runs through here too, so this is what stops a member
        # reading or writing another member's slots.
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
        # Absent and explicitly null differ: null clears the choice and is still
        # subject to the choosing deadline.
        if "bread" not in request.data:
            return super().partial_update(request, *args, **kwargs)

        new_bread_id = request.data.get("bread")

        with transaction.atomic():
            # select_related(None): Postgres refuses FOR UPDATE on the nullable
            # side of an outer join.
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
        # <pk> is a Member id here, not a PreferredBread id. The FK is
        # DEFERRABLE INITIALLY DEFERRED, so an unknown id would survive
        # get_or_create and only fail at commit.
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
    """The baking plan; the rows are written by the solver."""

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
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
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
    """The solver's distribution result per pickup location and week."""

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
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
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
    """Rows exist only where the bread defaults need overriding for a day."""

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
