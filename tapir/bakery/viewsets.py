from django.core.exceptions import ValidationError
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
)
from tapir.bakery.serializers import (
    BreadCapacityPickupStationSerializer,
    BreadContentSerializer,
    BreadDeliverySerializer,
    BreadDetailSerializer,
    BreadLabelSerializer,
    BreadListSerializer,
    IngredientSerializer,
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
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


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
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

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
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

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
            OpenApiParameter(name="pickup_station_ids[]", type=int, many=True),
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
                                "pickup_station_day": {"type": "integer"},
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
    filterset_fields = [
        "subscription",
        "year",
        "delivery_week",
        "delivery_day",
        "bread",
    ]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="member", type=str, description="Filter by member ID"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        # Optional: filter by member
        member_id = self.request.query_params.get("member", None)
        if member_id:
            queryset = queryset.filter(subscription__member__id=member_id)

        return queryset.select_related("subscription", "bread")

    def perform_create(self, serializer):
        # Additional validation on create
        subscription = serializer.validated_data["subscription"]
        year = serializer.validated_data["year"]
        delivery_week = serializer.validated_data["delivery_week"]
        delivery_day = serializer.validated_data["delivery_day"]

        # Count existing deliveries for this week
        existing_count = BreadDelivery.objects.filter(
            subscription=subscription,
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
        ).count()

        if existing_count >= subscription.quantity:
            raise ValidationError(
                f"Maximum {subscription.quantity} bread(s) allowed per week"
            )

        serializer.save()

    @extend_schema(
        summary="Replace all bread selections for a given week/day/subscription",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "subscription": {"type": "string"},
                    "year": {"type": "integer"},
                    "delivery_week": {"type": "integer"},
                    "delivery_day": {"type": "integer"},
                    "breads": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "subscription",
                    "year",
                    "delivery_week",
                    "delivery_day",
                    "breads",
                ],
            }
        },
        responses={
            200: BreadDeliverySerializer(many=True),
            400: OpenApiResponse(description="Bad request"),
            404: OpenApiResponse(description="Subscription not found"),
        },
    )
    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request):
        """
        Replace all bread selections for a given week/day/subscription.
        Payload: {
            "subscription": "id",
            "year": 2025,
            "delivery_week": 10,
            "delivery_day": 2,
            "breads": ["bread_id_1", "bread_id_2", "bread_id_1"]  // can have duplicates
        }
        """
        from tapir.wirgarten.models import Subscription

        subscription_id = request.data.get("subscription")
        year = request.data.get("year")
        delivery_week = request.data.get("delivery_week")
        delivery_day = request.data.get("delivery_day")
        bread_ids = request.data.get("breads", [])

        try:
            subscription = Subscription.objects.get(id=subscription_id)
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=404)

        # Validate quantity
        if len(bread_ids) > subscription.quantity:
            return Response(
                {"error": f"Maximum {subscription.quantity} bread(s) allowed"},
                status=400,
            )

        # Delete existing selections
        BreadDelivery.objects.filter(
            subscription=subscription,
            year=year,
            delivery_week=delivery_week,
            delivery_day=delivery_day,
        ).delete()

        # Create new selections
        deliveries = []
        for bread_id in bread_ids:
            try:
                bread = Bread.objects.get(id=bread_id)
                delivery = BreadDelivery.objects.create(
                    subscription=subscription,
                    year=year,
                    delivery_week=delivery_week,
                    delivery_day=delivery_day,
                    bread=bread,
                )
                deliveries.append(delivery)
            except Bread.DoesNotExist:
                pass

        serializer = self.get_serializer(deliveries, many=True)
        return Response(serializer.data)
