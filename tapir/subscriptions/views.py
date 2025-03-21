from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.subscriptions.serializers import (
    CancellationDataSerializer,
)
from tapir.subscriptions.services.coop_membership_manager import CoopMembershipManager
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Member
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
            "can_cancel_coop_membership": CoopMembershipManager.can_member_cancel_coop_membership(
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
        subscribed_products = set()
        for subscription in get_active_and_future_subscriptions().filter(member=member):
            subscribed_products.add(subscription.product)

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
            for subscribed_product in subscribed_products
        ]
