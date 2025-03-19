from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.subscriptions.serializers import CancellationDataSerializer
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Member, ProductType, Subscription
from tapir.wirgarten.service.products import get_active_subscriptions
from tapir.wirgarten.utils import check_permission_or_self, get_today


class GetCancellationDataView(APIView):
    @extend_schema(
        responses={200: CancellationDataSerializer()},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
            OpenApiParameter(name="product_type_name", type=str),
        ],
    )
    def get(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        check_permission_or_self(member.id, request)

        product_type = get_object_or_404(
            ProductType, name=request.query_params.get("product_type_name")
        )
        for subscription in get_active_subscriptions().filter(
            member=member, product__type=product_type
        ):
            if TrialPeriodManager.is_subscription_in_trial(subscription):
                return Response(
                    CancellationDataSerializer({"is_in_trial": True}).data,
                    status=status.HTTP_200_OK,
                )

        subscription_end_date = (
            Subscription.objects.filter(
                end_date__gte=get_today(), member=member, product__type=product_type
            )
            .order_by("-end_date")
            .first()
            .end_date
        )

        return Response(
            CancellationDataSerializer(
                {"is_in_trial": False, "subscription_end_date": subscription_end_date}
            ).data,
            status=status.HTTP_200_OK,
        )
