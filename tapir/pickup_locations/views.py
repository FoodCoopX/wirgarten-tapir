import datetime
import locale
from typing import Dict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, viewsets, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.serializers import PickupLocationSerializer
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.pickup_locations.models import PickupLocationBasketCapacity
from tapir.pickup_locations.serializers import (
    PickupLocationCapacitiesSerializer,
    PickupLocationCapacityEvolutionSerializer,
    PublicPickupLocationSerializer,
    PickupLocationCapacityCheckResponseSerializer,
    PickupLocationCapacityCheckRequestSerializer,
)
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.pickup_locations.services.pickup_location_highest_usage_after_date_service import (
    PickupLocationHighestUsageAfterDateService,
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
        cache = {}
        picking_mode = get_parameter_value(ParameterKeys.PICKING_MODE, cache=cache)

        data = {
            "pickup_location_id": pickup_location.id,
            "pickup_location_name": pickup_location.name,
            "picking_mode": picking_mode,
        }

        if picking_mode == PICKING_MODE_BASKET:
            data["capacities_by_basket_size"] = (
                self.build_serializer_data_picking_mode_basket(
                    pickup_location, cache=cache
                )
            )

        if picking_mode == PICKING_MODE_SHARE:
            data["capacities_by_shares"] = (
                self.build_serializer_data_picking_mode_shares(
                    pickup_location, cache=cache
                )
            )

        return Response(
            PickupLocationCapacitiesSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_serializer_data_picking_mode_basket(
        cls, pickup_location: PickupLocation, cache: Dict
    ):
        return [
            {"basket_size_name": basket_size_name, "capacity": capacity}
            for basket_size_name, capacity in BasketSizeCapacitiesService.get_basket_size_capacities_for_pickup_location(
                pickup_location, cache=cache
            ).items()
        ]

    @classmethod
    def build_serializer_data_picking_mode_shares(
        cls, pickup_location: PickupLocation, cache: Dict
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

        cache = {}
        picking_mode = get_parameter_value(ParameterKeys.PICKING_MODE, cache=cache)
        if request_serializer.validated_data["picking_mode"] != picking_mode:
            raise serializers.ValidationError("Invalid picking mode")

        if picking_mode == PICKING_MODE_BASKET:
            self.save_capacities_by_basket_size(
                pickup_location,
                request_serializer.validated_data["capacities_by_basket_size"],
            )

        if picking_mode == PICKING_MODE_SHARE:
            self.save_capacities_by_share(
                pickup_location,
                request_serializer.validated_data["capacities_by_shares"],
            )

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def save_capacities_by_basket_size(
        pickup_location: PickupLocation, capacities_by_basket_size
    ):
        PickupLocationBasketCapacity.objects.filter(
            pickup_location=pickup_location
        ).delete()
        PickupLocationBasketCapacity.objects.bulk_create(
            [
                PickupLocationBasketCapacity(
                    pickup_location=pickup_location,
                    basket_size_name=capacity["basket_size_name"],
                    capacity=capacity.get("capacity", None),
                )
                for capacity in capacities_by_basket_size
            ]
        )

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
    queryset = PickupLocation.objects.all()
    serializer_class = PickupLocationSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


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
        pickup_location: PickupLocation, cache: Dict
    ):
        data_points = []
        product_types = ProductType.objects.order_by(*product_type_order_by())
        capacities_by_product_type = SharesCapacityService.get_available_share_capacities_for_pickup_location_by_product_type(
            pickup_location
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
    queryset = PickupLocation.objects.all()
    serializer_class = PublicPickupLocationSerializer


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

        pickup_location = TapirCache.get_pickup_location_by_id(
            cache=self.cache,
            pickup_location_id=serializer.validated_data["pickup_location_id"],
        )
        if pickup_location is None:
            raise Http404(
                f"Unknown pickup location, id: '{serializer.validated_data["pickup_location_id"]}'"
            )

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"], cache=self.cache
        )

        subscription_start = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=self.cache),
            apply_buffer_time=True,
            cache=self.cache,
        )

        response_data = {
            "enough_capacity_for_order": PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=order,
                already_registered_member=None,
                subscription_start=subscription_start,
                cache=self.cache,
            )
        }

        return Response(
            PickupLocationCapacityCheckResponseSerializer(response_data).data
        )


class GetMemberPickupLocationApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
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
        reference_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=self.cache),
            apply_buffer_time=False,
            cache=self.cache,
        )
        pickup_location_id = MemberPickupLocationService.get_member_pickup_location_id(
            member=member, reference_date=reference_date
        )

        if pickup_location_id is None:
            return Response({"has_location": False})

        pickup_location = TapirCache.get_pickup_location_by_id(
            cache=self.cache, pickup_location_id=pickup_location_id
        )
        return Response(
            {
                "has_location": True,
                "location": PublicPickupLocationSerializer(pickup_location).data,
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

        try:
            self.validate(member=member, new_pickup_location=new_pickup_location)
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        with transaction.atomic():
            MemberPickupLocationService.link_member_to_pickup_location(
                pickup_location_id=new_pickup_location_id,
                member=member,
                valid_from=calculate_pickup_location_change_date(cache=self.cache),
                actor=request.user,
                cache=self.cache,
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )

    def validate(self, member: Member, new_pickup_location: PickupLocation):
        old_pickup_location_id = (
            MemberPickupLocationService.get_member_pickup_location_id(
                member=member, reference_date=get_today(cache=self.cache)
            )
        )
        if old_pickup_location_id == new_pickup_location.id:
            raise ValidationError("Du bist schon für diese Verteilstation eingetragen.")

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
