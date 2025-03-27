from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.pickup_locations.models import PickupLocationBasketCapacity
from tapir.pickup_locations.serializers import PickupLocationCapacitiesSerializer
from tapir.pickup_locations.services.basket_size_service import BasketSizeService
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import PickupLocation, PickupLocationCapability, ProductType
from tapir.wirgarten.parameters import Parameter


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

        picking_mode = get_parameter_value(Parameter.PICKING_MODE)

        data = {
            "pickup_location_id": pickup_location.id,
            "pickup_location_name": pickup_location.name,
            "picking_mode": picking_mode,
        }

        if picking_mode == PICKING_MODE_BASKET:
            data["capacities_by_basket_size"] = (
                self.build_serializer_data_picking_mode_basket(pickup_location)
            )

        if picking_mode == PICKING_MODE_SHARE:
            data["capacities_by_shares"] = (
                self.build_serializer_data_picking_mode_shares(pickup_location)
            )

        return Response(
            PickupLocationCapacitiesSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_serializer_data_picking_mode_basket(cls, pickup_location: PickupLocation):
        return [
            {"basket_size_name": basket_size_name, "capacity": capacity}
            for basket_size_name, capacity in BasketSizeService.get_basket_size_capacities_for_pickup_location(
                pickup_location
            ).items()
        ]

    @classmethod
    def build_serializer_data_picking_mode_shares(cls, pickup_location: PickupLocation):
        capacities = {
            product_type.id: {"product_type_name": product_type.name, "capacity": None}
            for product_type in ProductType.objects.all()
        }
        for capability in PickupLocationCapability.objects.filter(
            pickup_location=pickup_location
        ):
            if capability.product_type.id not in capacities.keys():
                continue

            capacities[capability.product_type.id]["capacity"] = capability.max_capacity

        return [
            {
                "product_type_id": product_type_id,
                "product_type_name": capacity_object["product_type_name"],
                "capacity": capacity_object["capacity"],
            }
            for product_type_id, capacity_object in capacities.items()
        ]

    @extend_schema(
        responses={200: str},
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

        picking_mode = get_parameter_value(Parameter.PICKING_MODE)

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
                    capacity=capacity["capacity"],
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
