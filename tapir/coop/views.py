from django.core.exceptions import BadRequest
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.coop.serializers import MinimumNumberOfSharesResponseSerializer
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.settings import COOP_SHARE_PRICE


class MinimumNumberOfSharesApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: MinimumNumberOfSharesResponseSerializer},
        parameters=[
            OpenApiParameter(name="product_ids", type=str, many=True),
            OpenApiParameter(name="quantities", type=int, many=True),
        ],
    )
    def get(self, request):
        product_ids = request.query_params.getlist("product_ids")
        quantities = request.query_params.getlist("quantities")
        cache = {}

        if len(product_ids) != len(quantities):
            raise BadRequest("Different number of product ids and quantities")

        ordered_products_id_to_quantity_map = {
            product_id: int(quantities[index])
            for index, product_id in enumerate(product_ids)
        }

        minimum_number_of_shares = (
            MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
                ordered_products_id_to_quantity_map, cache=cache
            )
        )

        return Response(
            MinimumNumberOfSharesResponseSerializer(
                {
                    "minimum_number_of_shares": minimum_number_of_shares,
                    "price_of_a_share": COOP_SHARE_PRICE,
                }
            ).data,
            status=status.HTTP_200_OK,
        )
