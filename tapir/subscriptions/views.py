from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, OpenApiParameter
from icecream import ic
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.subscriptions.serializers import (
    CancellationDataSerializer,
    CancelSubscriptionsViewResponseSerializer,
)
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Member, Product
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import check_permission_or_self


class GetCancellationDataView(APIView):
    @extend_schema(
        responses={200: CancellationDataSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
        ],
    )
    def get(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        check_permission_or_self(member.id, request)

        data = {
            "can_cancel_coop_membership": MembershipCancellationManager.can_member_cancel_coop_membership(
                member
            ),
            "subscribed_products": self.build_subscribed_products_data(member),
        }

        return Response(
            CancellationDataSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_subscribed_products_data(cls, member):
        return [
            {
                "product": subscribed_product,
                "is_in_trial": TrialPeriodManager.is_product_in_trial(
                    subscribed_product, member
                ),
                "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                    product=subscribed_product, member=member
                ),
            }
            for subscribed_product in cls.get_subscribed_products(member)
        ]

    @classmethod
    def get_subscribed_products(cls, member):
        return {
            subscription.product
            for subscription in get_active_and_future_subscriptions().filter(
                member=member, cancellation_ts__isnull=True
            )
        }


class CancelSubscriptionsView(APIView):
    @extend_schema(
        responses={200: CancelSubscriptionsViewResponseSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="product_ids", type=str, many=True),
            OpenApiParameter(name="cancel_coop_membership", type=bool),
        ],
    )
    def post(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        check_permission_or_self(member.id, request)

        product_ids = request.query_params.getlist("product_ids")
        products_selected_for_cancellation = {
            get_object_or_404(Product, id=product_id)
            for product_id in product_ids
            if product_id != ""
        }
        subscribed_products = GetCancellationDataView.get_subscribed_products(member)
        cancel_coop_membership = (
            request.query_params.get("cancel_coop_membership") == "true"
        )

        if (
            cancel_coop_membership
            and not MembershipCancellationManager.can_member_cancel_coop_membership(
                member
            )
        ):
            return self.build_response(
                False,
                [
                    "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn du noch nicht Mitglied bist."
                ],
            )

        if (
            cancel_coop_membership
            and products_selected_for_cancellation != subscribed_products
        ):
            ic(
                products_selected_for_cancellation,
                subscribed_products,
                products_selected_for_cancellation != subscribed_products,
            )
            return self.build_response(
                False,
                [
                    "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn alle Verträge auch kündigst."
                ],
            )

        if self.is_at_least_one_additional_product_not_selected(
            subscribed_products, products_selected_for_cancellation
        ) and self.are_all_base_products_selected(
            subscribed_products, products_selected_for_cancellation
        ):
            return self.build_response(
                False,
                [
                    _(
                        "Du kannst keine Zusatzabos beziehen wenn du das Basisabo kündigst."
                    )
                ],
            )

        with transaction.atomic():
            for product in products_selected_for_cancellation:
                SubscriptionCancellationManager.cancel_subscriptions(product, member)

            if cancel_coop_membership:
                MembershipCancellationManager.cancel_coop_membership(member)

        return Response("OK", status=status.HTTP_200_OK)

    @staticmethod
    def are_all_base_products_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
    ):
        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id == base_product_type_id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return False

        return True

    @staticmethod
    def is_at_least_one_additional_product_not_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
    ):
        base_product_type_id = get_parameter_value(Parameter.COOP_BASE_PRODUCT_TYPE)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id != base_product_type_id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return True

        return False

    @staticmethod
    def build_response(subscriptions_cancelled: bool, errors: list[str]):
        return Response(
            CancelSubscriptionsViewResponseSerializer(
                {"subscriptions_cancelled": subscriptions_cancelled, "errors": errors}
            ).data,
            status=status.HTTP_200_OK,
        )
