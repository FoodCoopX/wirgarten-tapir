from typing import Dict

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.subscriptions.serializers import (
    CancellationDataSerializer,
    CancelSubscriptionsViewResponseSerializer,
)
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    Product,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import (
    check_permission_or_self,
    format_date,
)


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

        cache = {}
        data = {
            "can_cancel_coop_membership": MembershipCancellationManager.can_member_cancel_coop_membership(
                member, cache=cache
            ),
            "subscribed_products": self.build_subscribed_products_data(
                member, cache=cache
            ),
            "legal_status": get_parameter_value(
                ParameterKeys.ORGANISATION_LEGAL_STATUS, cache=cache
            ),
        }

        return Response(
            CancellationDataSerializer(data).data,
            status=status.HTTP_200_OK,
        )

    @classmethod
    def build_subscribed_products_data(cls, member, cache: Dict):
        return [
            {
                "product": subscribed_product,
                "is_in_trial": TrialPeriodManager.is_product_in_trial(
                    subscribed_product, member, cache=cache
                ),
                "cancellation_date": SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                    product=subscribed_product, member=member, cache=cache
                ),
            }
            for subscribed_product in cls.get_subscribed_products(member, cache=cache)
        ]

    @classmethod
    def get_subscribed_products(cls, member, cache: Dict):
        return {
            subscription.product
            for subscription in get_active_and_future_subscriptions(cache=cache).filter(
                member=member, cancellation_ts__isnull=True
            )
        }


class CancelSubscriptionsView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

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
        subscribed_products = GetCancellationDataView.get_subscribed_products(
            member, cache=self.cache
        )

        cancel_coop_membership = (
            request.query_params.get("cancel_coop_membership") == "true"
        )
        if (
            cancel_coop_membership
            and not MembershipCancellationManager.can_member_cancel_coop_membership(
                member, cache=self.cache
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
            return self.build_response(
                False,
                [
                    "Es ist nur möglich die Beitrittserklärung zu widerrufen wenn alle Verträge auch kündigst."
                ],
            )

        if (
            not get_parameter_value(
                ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
                cache=self.cache,
            )
            and self.is_at_least_one_additional_product_not_selected(
                subscribed_products,
                products_selected_for_cancellation,
                cache=self.cache,
            )
            and self.are_all_base_products_selected(
                subscribed_products,
                products_selected_for_cancellation,
                cache=self.cache,
            )
        ):
            return self.build_response(
                False,
                ["Du kannst keine Zusatzabos beziehen wenn du das Basis-Abo kündigst."],
            )

        with transaction.atomic():
            for product in products_selected_for_cancellation:
                cancelled_subscriptions = (
                    SubscriptionCancellationManager.cancel_subscriptions(
                        product, member, cache=self.cache
                    )
                )
                if len(cancelled_subscriptions) > 0:
                    TransactionalTrigger.fire_action(
                        TransactionalTriggerData(
                            key=Events.CONTRACT_CANCELLED,
                            recipient_id_in_base_queryset=member.id,
                            token_data={
                                "contract_list": cancelled_subscriptions,
                                "contract_end_date": format_date(
                                    cancelled_subscriptions[0].end_date
                                ),
                            },
                        ),
                    )

            if cancel_coop_membership:
                MembershipCancellationManager.cancel_coop_membership(
                    member, cache=self.cache
                )

        return self.build_response(subscriptions_cancelled=True, errors=[])

    @staticmethod
    def are_all_base_products_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
        cache: Dict,
    ):
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id == base_product_type.id
                and subscribed_product not in products_selected_for_cancellation
            ):
                return False

        return True

    @staticmethod
    def is_at_least_one_additional_product_not_selected(
        subscribed_products: set[Product],
        products_selected_for_cancellation: set[Product],
        cache: Dict,
    ):
        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
        for subscribed_product in subscribed_products:
            if (
                subscribed_product.type_id != base_product_type.id
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
