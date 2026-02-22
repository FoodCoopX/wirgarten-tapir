from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from tapir.bakery.models import (
    Bread,
    BreadCapacityPickupStation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    Ingredient,
    PreferredLabel,
)
from tapir.bakery.serializers import (
    BreadCapacityPickupStationSerializer,
    BreadContentSerializer,
    BreadDeliverySerializer,
    BreadDetailSerializer,
    BreadLabelSerializer,
    BreadListSerializer,
    IngredientSerializer,
    PreferredLabelBulkUpdateSerializer,
    PreferredLabelSerializer,
)
from tapir.bakery.utils import str_to_bool
from tapir.generic_exports.permissions import HasCoopManagePermission


@extend_schema(tags=["bakery"])
class BreadLabelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bread labels/categories
    """

    queryset = BreadLabel.objects.all()
    serializer_class = BreadLabelSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(tags=["bakery"])
class IngredientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ingredients
    """

    queryset = Ingredient.objects.all()
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
class BreadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bread variants
    """

    queryset = Bread.objects.prefetch_related("labels", "contents__ingredient").all()
    permission_classes = [permissions.IsAuthenticated]

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

    @extend_schema(
        summary="Add an ingredient to a bread",
        request=BreadContentSerializer,
        responses={201: BreadContentSerializer},
    )
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
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        """Filter by label and active status if provided"""
        queryset = super().get_queryset()

        # Filter by label name
        label_id = self.request.query_params.get("label_id", None)
        if label_id:
            queryset = queryset.filter(labels__id=label_id)

        # Filter by active status
        is_active = str_to_bool(self.request.query_params.get("is_active", None))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

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
        label_ids = request.query_params.get("label_ids", "").split(",")

        try:
            label_ids = [int(id) for id in label_ids if id]
        except ValueError:
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
    permission_classes = [permissions.IsAuthenticated]

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
class BreadCapacityPickupStationViewSet(viewsets.ModelViewSet):
    queryset = BreadCapacityPickupStation.objects.all()
    serializer_class = BreadCapacityPickupStationSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="year", type=int),
            OpenApiParameter(name="week", type=int),
            OpenApiParameter(name="pickup_station_ids[]", type=str, many=True),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        year = self.request.query_params.get("year")
        week = self.request.query_params.get("week")
        pickup_station_ids = self.request.query_params.getlist("pickup_station_ids[]")

        if year:
            queryset = queryset.filter(year=year)
        if week:
            queryset = queryset.filter(delivery_week=week)
        if pickup_station_ids:
            queryset = queryset.filter(pickup_station_day__id__in=pickup_station_ids)

        return queryset

    @extend_schema(
        summary="Bulk create/update/delete bread capacities",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer"},
                    "week": {"type": "integer"},
                    "updates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "pickup_station_day": {"type": "string"},
                                "bread": {"type": "string"},
                                "capacity": {"type": "integer", "nullable": True},
                            },
                        },
                    },
                },
                "required": ["year", "week", "updates"],
            }
        },
        responses={
            200: OpenApiResponse(description='{"status": "success"}'),
            400: OpenApiResponse(description="Bad request"),
        },
    )
    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request: Request) -> Response:
        """Bulk create/update/delete capacities"""
        year = request.data.get("year")
        week = request.data.get("week")
        updates = request.data.get("updates", [])

        if not year or not week:
            return Response(
                {"error": "year and week are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for update in updates:
            pickup_station_day_id = update.get("pickup_station_day")
            bread_id = update.get("bread")
            capacity = update.get("capacity")

            if capacity is None:
                # Delete
                BreadCapacityPickupStation.objects.filter(
                    year=year,
                    delivery_week=week,
                    pickup_station_day_id=pickup_station_day_id,
                    bread_id=bread_id,
                ).delete()
            else:
                # Create or update
                BreadCapacityPickupStation.objects.update_or_create(
                    year=year,
                    delivery_week=week,
                    pickup_station_day_id=pickup_station_day_id,
                    bread_id=bread_id,
                    defaults={"capacity": capacity},
                )

        return Response({"status": "success"})


@extend_schema(tags=["bakery"])
class BreadDeliveryViewSet(viewsets.ModelViewSet):
    queryset = BreadDelivery.objects.all()
    serializer_class = BreadDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

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

        # Optional: filter by member
        member_id = self.request.query_params.get("member_id", None)
        year = self.request.query_params.get("year", None)
        delivery_week = self.request.query_params.get("delivery_week", None)
        if member_id is not None:
            queryset = queryset.filter(subscription__member__id=member_id)
        if year is not None:
            queryset = queryset.filter(year=year)
        if delivery_week is not None:
            queryset = queryset.filter(delivery_week=delivery_week)

        return queryset.select_related("bread", "pickup_location")


@extend_schema(
    tags=["Bakery"],
    description="Manage preferred bread labels for a member.",
    request=PreferredLabelSerializer,
    responses={200: PreferredLabelSerializer},
)
class PreferredLabelViewSet(viewsets.ModelViewSet):
    queryset = PreferredLabel.objects.all()
    serializer_class = PreferredLabelSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="member_id",
                type=str,
                description="Filter by member ID",
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        # Optionally filter by member
        member_id = self.request.query_params.get("member_id")
        if member_id:
            return self.queryset.filter(member__id=member_id)
        return self.queryset

    @extend_schema(
        request=PreferredLabelBulkUpdateSerializer,
        responses={200: PreferredLabelBulkUpdateSerializer},
        description="Bulk update preferred bread labels for a member. Replaces all labels for the member with the provided list.",
        tags=["bakery"],
    )
    @action(detail=True, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request, pk=None):
        serializer = PreferredLabelBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        labels = serializer.validated_data["labels"]
        preferred, _ = PreferredLabel.objects.get_or_create(member_id=pk)

        preferred.labels.set(labels)
        preferred.save()
        return Response(serializer.data)
