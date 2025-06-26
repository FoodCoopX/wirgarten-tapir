from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.serializers import ProductSerializer
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.basket_size_capacities_service import (
    BasketSizeCapacitiesService,
)
from tapir.subscriptions.serializers import (
    ExtendedProductSerializer,
    PublicProductTypeSerializer,
)
from tapir.subscriptions.services.product_updater import ProductUpdater
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Product,
    ProductType,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_product_price,
)


class ExtendedProductView(APIView):
    @extend_schema(
        responses={200: ExtendedProductSerializer()},
        parameters=[OpenApiParameter(name="product_id", type=str)],
    )
    def get(self, request):
        if not request.user.has_perm(Permission.Products.VIEW):
            return Response(status=status.HTTP_403_FORBIDDEN)

        product = get_object_or_404(Product, id=request.query_params.get("product_id"))

        data = {
            attribute: getattr(product, attribute)
            for attribute in [
                "id",
                "name",
                "deleted",
                "base",
                "description_in_bestellwizard",
                "url_of_image_in_bestellwizard",
            ]
        }

        cache = {}
        product_price_object = get_product_price(product, cache=cache)
        if product_price_object:
            data.update(
                {"price": product_price_object.price, "size": product_price_object.size}
            )
        else:
            data.update({"price": 0, "size": 0})

        data["basket_size_equivalences"] = [
            {"basket_size_name": size_name, "quantity": quantity}
            for size_name, quantity in BasketSizeCapacitiesService.get_basket_size_equivalences_for_product(
                product
            ).items()
        ]

        data["picking_mode"] = get_parameter_value(
            ParameterKeys.PICKING_MODE, cache=cache
        )

        return Response(
            ExtendedProductSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: str},
        request=ExtendedProductSerializer(),
    )
    def patch(self, request):
        if not request.user.has_perm(Permission.Products.MANAGE):
            return Response(status=status.HTTP_403_FORBIDDEN)

        request_serializer = ExtendedProductSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        product = get_object_or_404(Product, id=request_serializer.validated_data["id"])

        with transaction.atomic():
            ProductUpdater.update_product(product, request_serializer)

        return Response(
            "OK",
            status=status.HTTP_200_OK,
        )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    queryset = Product.objects.select_related("type")
    serializer_class = ProductSerializer


class PublicProductTypeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = []
    queryset = ProductType.objects.all()
    serializer_class = PublicProductTypeSerializer
