import datetime

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.deliveries.models import Joker
from tapir.deliveries.serializers import JokerSerializer, DeliverySerializer
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self, get_today


class GetMemberDeliveriesView(APIView):
    @extend_schema(
        responses={200: DeliverySerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)

        deliveries = GetDeliveriesService.get_deliveries(
            member=member,
            date_from=get_today(),
            date_to=get_today() + datetime.timedelta(days=30 * 6),
        )

        return Response(
            DeliverySerializer(deliveries, many=True).data,
            status=status.HTTP_200_OK,
        )


class GetMemberJokersView(APIView):
    @extend_schema(
        responses={200: JokerSerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)

        return Response(
            JokerSerializer(Joker.objects.filter(member_id=member_id), many=True).data,
            status=status.HTTP_200_OK,
        )
