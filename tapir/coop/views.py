from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from icecream import ic
from rest_framework import permissions
from rest_framework.generics import DestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.accounts.models import EmailChangeRequest
from tapir.deliveries.models import Joker
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.models import LogEntry
from tapir.subscriptions.serializers import MemberSerializer
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    MandateReference,
    Subscription,
    CoopShareTransaction,
    Deliveries,
    TransferCoopSharesLogEntry,
    WaitingListEntry,
    QuestionaireTrafficSourceResponse,
    QuestionaireCancellationReasonResponse,
    Payment,
)


class DeleteMemberApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def delete(self, request):
        member_id = request.query_params.get("member_id")
        member = get_object_or_404(Member, id=member_id)

        with transaction.atomic():
            EmailChangeRequest.objects.filter(user=member).delete()
            LogEntry.objects.filter(actor=member).delete()
            LogEntry.objects.filter(user=member).delete()
            TransferCoopSharesLogEntry.objects.filter(target_member=member).delete()
            Payment.objects.filter(mandate_ref__member=member).delete()
            models = [
                Joker,
                MemberPickupLocation,
                Subscription,
                CoopShareTransaction,
                Deliveries,
                WaitingListEntry,
                WaitingListEntry,
                QuestionaireTrafficSourceResponse,
                QuestionaireCancellationReasonResponse,
                MandateReference,
            ]
            for model in models:
                model.objects.filter(member=member).delete()

            member.delete()

        return Response("deleted")


class GetMemberDetailsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: MemberSerializer},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        member = get_object_or_404(Member, id=member_id)

        return Response(MemberSerializer(member).data)
