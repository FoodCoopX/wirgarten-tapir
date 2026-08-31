import datetime
import locale

from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, viewsets, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.pickup_locations.serializers import (
    PickupLocationCapacitiesSerializer,
    PickupLocationCapacityEvolutionSerializer,
    PickupLocationDeliveryChargeCreateRequestSerializer,
    PickupLocationDeliveryChargesResponseSerializer,
    PublicPickupLocationSerializer,
    PickupLocationCapacityCheckResponseSerializer,
    PickupLocationCapacityCheckRequestSerializer,
    PickupLocationSerializer,
    LocationRouteSerializer,
    PickupLocationGrowingPeriodResponseSerializer,
    PickupLocationGrowingPeriodSetRequestSerializer,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.pickup_locations.services.pickup_location_growing_period_filter import (
    filter_pickup_locations_for_growing_period,
)
from tapir.pickup_locations.services.pickup_location_highest_usage_after_date_service import (
    PickupLocationHighestUsageAfterDateService,
)
from tapir.pickup_locations.services.public_pickup_locations_provider import (
    PublicPickupLocationProvider,
)
from tapir.pickup_locations.services.share_capacities_service import (
    SharesCapacityService,
)
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    PickupLocation,
    PickupLocationCapability,
    ProductType,
    Member,
    GrowingPeriod,
    LocationRoute,
    PickupLocationGrowingPeriod,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date
from tapir.wirgarten.service.product_standard_order import product_type_order_by
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_today, check_permission_or_self


class PickupLocationCapacitiesView(APIView):
    @extend_schema(
        responses={200: PickupLocationCapacitiesSerializer()},
        parameters=[OpenApiParameter(name="pickup_location_id", type=str)],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Products.VIEW):
            return Response(status=status.HTTP_403_FORBIDDEN)

        pickup_location = get_object_or_404(
            PickupLocation, id=request.query_params.get("pickup_location_id")
        )

        data = {
            "pickup_location_id": pickup_location.id,
            "pickup_location_name": pickup_location.name,
            "capacities_by_shares": self.build_serializer_data_picking_mode_shares(
                pickup_location, cache={}
            ),
        }

        return Response(
            PickupLocationCapacitiesSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_serializer_data_picking_mode_shares(
        cls, pickup_location: PickupLocation, cache: dict
    ):
        capacities = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            pickup_location, cache=cache
        )

        return [
            {
                "product_type_id": product_type.id,
                "product_type_name": product_type.name,
                "capacity": capacity,
            }
            for product_type, capacity in capacities.items()
        ]

    @extend_schema(
        responses={200: str, 400: str},
        request=PickupLocationCapacitiesSerializer(),
    )
    def patch(self, request):
        if not request.user.has_perm(Permission.Products.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        request_serializer = PickupLocationCapacitiesSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        pickup_location = get_object_or_404(
            PickupLocation, id=request_serializer.validated_data["pickup_location_id"]
        )

        self.save_capacities_by_share(
            pickup_location,
            request_serializer.validated_data["capacities_by_shares"],
        )

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def save_capacities_by_share(pickup_location: PickupLocation, capacities_by_shares):
        PickupLocationCapability.objects.filter(
            pickup_location=pickup_location
        ).delete()
        PickupLocationCapability.objects.bulk_create(
            [
                PickupLocationCapability(
                    pickup_location=pickup_location,
                    product_type_id=capacity["product_type_id"],
                    max_capacity=capacity.get("capacity", None),
                )
                for capacity in capacities_by_shares
            ]
        )


class PickupLocationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PickupLocationSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    def get_queryset(self):
        qs = PickupLocation.objects.all()
        if not get_parameter_value(
            key=ParameterKeys.PICKUP_LOCATION_GROWING_PERIOD_ENABLED, cache=self.cache
        ):
            return qs
        growing_period_id = self.request.query_params.get("growing_period_id")
        if growing_period_id is None:
            gp = TapirCache.get_growing_period_at_date(
                reference_date=get_today(cache=self.cache), cache=self.cache
            )
            growing_period_id = gp.id if gp is not None else None
        return filter_pickup_locations_for_growing_period(
            qs, growing_period_id, self.cache
        )


class PickupLocationCapacityEvolutionView(APIView):
    @extend_schema(
        responses={200: PickupLocationCapacityEvolutionSerializer()},
        parameters=[OpenApiParameter(name="pickup_location_id", type=str)],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Products.VIEW):
            return Response(status=status.HTTP_403_FORBIDDEN)

        pickup_location = get_object_or_404(
            PickupLocation, id=request.query_params.get("pickup_location_id")
        )
        cache = {}
        data = self.build_data_for_picking_mode_shares(pickup_location, cache)

        return Response(PickupLocationCapacityEvolutionSerializer(data).data)

    @staticmethod
    def build_data_for_picking_mode_shares(
        pickup_location: PickupLocation, cache: dict
    ):
        data_points = []
        product_types = ProductType.objects.order_by(*product_type_order_by())
        capacities_by_product_type = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            pickup_location, cache=cache
        )

        max_date = PickupLocationHighestUsageAfterDateService.get_date_of_last_possible_capacity_change(
            pickup_location, cache
        )
        current_date = get_today()
        while current_date < max_date:
            values = []
            for product_type in product_types:
                capacity = capacities_by_product_type.get(product_type, 0)
                if capacity is None:
                    values.append("Unbegrenzt")
                else:
                    values.append(
                        locale.format_string(
                            "%.2f",
                            PickupLocationCapacityModeShareChecker.get_free_capacity_at_date(
                                pickup_location=pickup_location,
                                product_type=product_type,
                                reference_date=current_date,
                                cache=cache,
                            ),
                        )
                    )
            if len(data_points) == 0 or data_points[-1]["values"] != values:
                data_points.append(
                    {
                        "date": current_date,
                        "values": values,
                    }
                )

            current_date = get_monday(current_date + datetime.timedelta(days=7))

        return {
            "table_headers": product_types.values_list("name", flat=True),
            "data_points": data_points,
        }


class PublicPickupLocationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    serializer_class = PublicPickupLocationSerializer

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    def get_queryset(self):
        growing_period_id = self.request.query_params.get("growing_period_id", None)
        return PublicPickupLocationProvider.get_pickup_locations_available_for_members(
            cache=self.cache, growing_period_id=growing_period_id
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = self.cache
        return context


class PickupLocationCapacityCheckApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: PickupLocationCapacityCheckResponseSerializer()},
        request=PickupLocationCapacityCheckRequestSerializer,
    )
    def post(self, request):
        serializer = PickupLocationCapacityCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"], cache=self.cache
        )

        growing_period_id = serializer.validated_data.get("growing_period_id", None)
        if growing_period_id is None:
            subscription_start = (
                ContractStartDateCalculator.get_next_contract_start_date(
                    reference_date=get_today(cache=self.cache),
                    apply_buffer_time=True,
                    cache=self.cache,
                )
            )
        else:
            growing_period = get_object_or_404(
                GrowingPeriod, id=serializer.validated_data["growing_period_id"]
            )

            subscription_start = ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
                apply_buffer_time=True,
                cache=self.cache,
            )

        candidates = PickupLocation.objects.all()
        candidates = filter_pickup_locations_for_growing_period(
            candidates, growing_period_id, self.cache
        )

        pickup_location_ids_with_enough_capacity_for_order = [
            pickup_location.id
            for pickup_location in candidates
            if PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=order,
                already_registered_member=None,
                subscription_start=subscription_start,
                cache=self.cache,
            )
        ]

        return Response(
            PickupLocationCapacityCheckResponseSerializer(
                {
                    "pickup_location_ids_with_enough_capacity_for_order": pickup_location_ids_with_enough_capacity_for_order
                }
            ).data
        )


class GetMemberPickupLocationApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="growing_period_id", type=str, required=False),
        ],
        responses={
            200: inline_serializer(
                name="mpl",
                fields={
                    "has_location": serializers.BooleanField(),
                    "location": PublicPickupLocationSerializer(required=False),
                },
            )
        },
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)

        growing_period_id = request.query_params.get("growing_period_id", None)
        if growing_period_id:
            growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)
            reference_date = ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
                apply_buffer_time=False,
                cache=self.cache,
            )
        else:
            reference_date = ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=self.cache),
                apply_buffer_time=False,
                cache=self.cache,
            )

        pickup_location_id = MemberPickupLocationGetter.get_member_pickup_location_id(
            member=member, reference_date=reference_date
        )

        if pickup_location_id is None:
            return Response({"has_location": False})

        # If the period-assignment feature is on, the historical PL is only
        # "current" if it is still offered for the requested period.
        allowed = filter_pickup_locations_for_growing_period(
            PickupLocation.objects.filter(id=pickup_location_id),
            growing_period_id,
            self.cache,
        )
        if not allowed.exists():
            return Response({"has_location": False})

        pickup_location = TapirCache.get_pickup_location_by_id(
            cache=self.cache, pickup_location_id=pickup_location_id
        )
        return Response(
            {
                "has_location": True,
                "location": PublicPickupLocationSerializer(
                    pickup_location, context={"cache": self.cache}
                ).data,
            }
        )


class ChangeMemberPickupLocationApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="pickup_location_id", type=str),
            OpenApiParameter(name="growing_period_id", type=str, required=False),
        ],
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)
        new_pickup_location_id = request.query_params.get("pickup_location_id")
        new_pickup_location = get_object_or_404(
            PickupLocation, id=new_pickup_location_id
        )
        growing_period_id = request.query_params.get("growing_period_id", None)

        valid_from = calculate_pickup_location_change_date(cache=self.cache)

        try:
            self.validate(
                member=member,
                new_pickup_location=new_pickup_location,
                valid_from=valid_from,
                growing_period_id=growing_period_id,
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        with transaction.atomic():
            MemberPickupLocationSetter.link_member_to_pickup_location(
                pickup_location_id=new_pickup_location_id,
                member=member,
                valid_from=valid_from,
                actor=request.user,
                cache=self.cache,
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )

    def validate(
        self,
        member: Member,
        new_pickup_location: PickupLocation,
        valid_from: datetime.date,
        growing_period_id: str | None = None,
    ):
        old_pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=valid_from
            )
        )
        if old_pickup_location_id == new_pickup_location.id:
            raise ValidationError("Du bist schon für diese Verteilstation eingetragen.")

        if new_pickup_location.id == get_parameter_value(
            key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
            cache=self.cache,
        ):
            raise ValidationError(
                "Dieser Abholort kann nicht ausgewählt werden (Das ist die Spende-Sonder-Ort)."
            )

        # Period-assignment feature: if a growing_period_id is supplied and the
        # feature is on, the new PL must be linked to that period. When feature
        # is off, the helper returns the queryset unchanged.
        if (
            growing_period_id is not None
            and not filter_pickup_locations_for_growing_period(
                PickupLocation.objects.filter(id=new_pickup_location.id),
                growing_period_id,
                self.cache,
            ).exists()
        ):
            raise ValidationError(
                "Dieser Abholort ist für die ausgewählte Vertragsperiode nicht verfügbar."
            )

        subscriptions = (
            get_active_and_future_subscriptions(cache=self.cache)
            .filter(member=member)
            .select_related("product")
        )
        order = {
            subscription.product: subscription.quantity
            for subscription in subscriptions
        }
        if not OrderValidator.does_order_need_a_pickup_location(
            order=order, cache=self.cache
        ):
            raise ValidationError("Deine Verträge brauchen keine Verteilstation.")

        change_date = (
            calculate_pickup_location_change_date(cache=self.cache)
            if old_pickup_location_id is not None
            else get_today(cache=self.cache)
        )

        if not PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
            pickup_location=new_pickup_location,
            order=order,
            already_registered_member=member,
            subscription_start=change_date,
            cache=self.cache,
        ):
            raise ValidationError(
                "Diese Abholort hat nicht genug Kapazitäten für deine Verträge."
            )


class PickupLocationDeliveryChargesView(APIView):
    @extend_schema(
        responses={200: PickupLocationDeliveryChargesResponseSerializer()},
        parameters=[OpenApiParameter(name="pickup_location_id", type=str)],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Products.VIEW):
            return Response(status=status.HTTP_403_FORBIDDEN)

        pickup_location = get_object_or_404(
            PickupLocation, id=request.query_params.get("pickup_location_id")
        )
        entries = PickupLocationDeliveryCharge.objects.filter(
            pickup_location=pickup_location
        ).order_by("-valid_from")

        return Response(
            PickupLocationDeliveryChargesResponseSerializer(
                {
                    "pickup_location_id": pickup_location.id,
                    "pickup_location_name": pickup_location.name,
                    "entries": entries,
                }
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: str, 400: str},
        request=PickupLocationDeliveryChargeCreateRequestSerializer(),
    )
    def post(self, request):
        if not request.user.has_perm(Permission.Products.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        request_serializer = PickupLocationDeliveryChargeCreateRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        pickup_location = get_object_or_404(
            PickupLocation,
            id=request_serializer.validated_data["pickup_location_id"],
        )

        try:
            PickupLocationDeliveryChargeService.save_charge(
                pickup_location=pickup_location,
                amount=request_serializer.validated_data["amount"],
                valid_from=request_serializer.validated_data["valid_from"],
                cache={},
            )
        except ValidationError as error:
            return Response(
                {"error": error.message}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response("OK", status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: str, 400: str},
        parameters=[OpenApiParameter(name="id", type=str)],
    )
    def delete(self, request):
        if not request.user.has_perm(Permission.Products.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        charge_id = request.query_params.get("id")

        try:
            PickupLocationDeliveryChargeService.delete_charge(
                charge_id=charge_id, cache={}
            )
        except PickupLocationDeliveryCharge.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        except ValidationError as error:
            return Response(
                {"error": error.message}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response("OK", status=status.HTTP_200_OK)


class LocationRouteViewSet(viewsets.ModelViewSet):
    queryset = LocationRoute.objects.order_by("name")
    serializer_class = LocationRouteSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


class PickupLocationGrowingPeriodViewSet(viewsets.ViewSet):
    """
    Admin API for managing which GrowingPeriods a PickupLocation is assigned to.
    Feature flag ``wirgarten.delivery.pickup_location_growing_period.enabled``
    is enforced by callers' filter logic; this endpoint always allows editing
    so admins can pre-configure assignments before enabling the feature.
    """

    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: PickupLocationGrowingPeriodResponseSerializer(many=True)},
        parameters=[OpenApiParameter(name="pickup_location_id", type=str)],
    )
    def list(self, request):
        pickup_location = get_object_or_404(
            PickupLocation, id=request.query_params.get("pickup_location_id")
        )
        growing_periods = GrowingPeriod.objects.filter(
            pickup_location_links__pickup_location=pickup_location
        ).order_by("start_date")
        return Response(
            [
                PickupLocationGrowingPeriodResponseSerializer(
                    {
                        "pickup_location_id": pickup_location.id,
                        "pickup_location_name": pickup_location.name,
                        "growing_periods": growing_periods,
                    }
                ).data
            ]
        )

    @extend_schema(
        request=PickupLocationGrowingPeriodSetRequestSerializer(),
        responses={200: str},
    )
    def create(self, request):
        serializer = PickupLocationGrowingPeriodSetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pickup_location = get_object_or_404(
            PickupLocation, id=serializer.validated_data["pickup_location_id"]
        )
        growing_period_ids = serializer.validated_data["growing_period_ids"]

        # Validate all ids exist before mutating.
        existing_ids = set(
            GrowingPeriod.objects.filter(id__in=growing_period_ids).values_list(
                "id", flat=True
            )
        )
        missing = [gid for gid in growing_period_ids if gid not in existing_ids]
        if missing:
            return Response(
                {"error": f"Unknown growing_period_ids: {missing}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            PickupLocationGrowingPeriod.objects.filter(
                pickup_location=pickup_location
            ).delete()
            PickupLocationGrowingPeriod.objects.bulk_create(
                [
                    PickupLocationGrowingPeriod(
                        pickup_location=pickup_location,
                        growing_period_id=gid,
                    )
                    for gid in growing_period_ids
                ]
            )

        return Response("OK", status=status.HTTP_200_OK)
