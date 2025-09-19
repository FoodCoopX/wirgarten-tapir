from django.core.exceptions import BadRequest, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.coop.serializers import MinimumNumberOfSharesResponseSerializer
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.utils import check_permission_or_self, get_today


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
            product_id: int(quantities[index] or 0)
            for index, product_id in enumerate(product_ids)
            if product_id != ""
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
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class ExistingMemberPurchasesSharesApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: str},
        parameters=[
            OpenApiParameter(name="member_id", type=str, required=True),
            OpenApiParameter(name="number_of_shares_to_add", type=int, required=True),
        ],
    )
    def post(self, request):
        member_id = request.query_params.get("member_id")
        member = get_object_or_404(Member, id=member_id)
        check_permission_or_self(pk=member_id, request=request)

        number_of_shares_to_add = int(
            request.query_params.get("number_of_shares_to_add")
        )
        if number_of_shares_to_add <= 0:
            raise ValidationError("Number of coop shares must be positive")

        if not member.is_student:
            self.validate_number_of_shares(
                number_of_shares_to_add=number_of_shares_to_add,
                cache=self.cache,
                member=member,
            )

        with transaction.atomic():
            CoopSharePurchaseHandler.buy_cooperative_shares(
                quantity=number_of_shares_to_add,
                member=member,
                shares_valid_at=ContractStartDateCalculator.get_next_contract_start_date(
                    reference_date=get_today(cache=self.cache),
                    apply_buffer_time=True,
                    cache=self.cache,
                ),
                cache=self.cache,
            )

        return Response("OK")

    @classmethod
    def validate_number_of_shares(
        cls, number_of_shares_to_add: int, cache: dict, member: Member
    ):
        ordered_products_id_to_quantity_map = {}
        for subscription in TapirCache.get_active_and_future_subscriptions_by_member_id(
            cache=cache, reference_date=get_today(cache=cache)
        ).get(member.id, []):
            ordered_products_id_to_quantity_map[subscription.product_id] = (
                subscription.quantity
            )

        total_min_shares = (
            MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
                ordered_products_id_to_quantity_map=ordered_products_id_to_quantity_map,
                cache=cache,
            )
        )

        current_shares = sum(
            [
                share_transaction.quantity
                for share_transaction in CoopShareTransaction.objects.filter(
                    member=member
                )
            ]
        )

        if current_shares + number_of_shares_to_add < total_min_shares:
            raise ValidationError(
                f"The minimum final number of shares is {total_min_shares}, "
                f"this member currently has {current_shares}, adding {number_of_shares_to_add} is not enough."
            )
