from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.associations.serializers import (
    AssociationDepositDetailsSerializer,
    IncreaseAssociationDepositRequestSerializer,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_increase_recorder import (
    AssociationDepositIncreaseRecorder,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self


class MemberAssociationDepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str, required=True)],
        responses={200: AssociationDepositDetailsSerializer},
    )
    def get(self, request):
        cache = {}
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, pk=member_id)
        details = AssociationDepositDetailsProvider.get_deposit_details(member, cache)
        details["can_increase"] = details["can_increase"] and (
            request.user.pk == member_id
            or request.user.has_perm(Permission.Coop.MANAGE)
        )
        return Response(AssociationDepositDetailsSerializer(details).data)

    @extend_schema(
        request=IncreaseAssociationDepositRequestSerializer,
        responses={200: AssociationDepositDetailsSerializer},
    )
    def post(self, request):
        cache = {}
        serializer = IncreaseAssociationDepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member_id = serializer.validated_data["member_id"]
        if request.user.pk != member_id and not request.user.has_perm(
            Permission.Coop.MANAGE
        ):
            raise PermissionDenied
        member = get_object_or_404(Member, pk=member_id)
        try:
            AssociationDepositIncreaseRecorder.increase_agreed_deposit(
                member, serializer.validated_data["total_amount"], request.user, cache
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        return Response(
            AssociationDepositDetailsSerializer(
                AssociationDepositDetailsProvider.get_deposit_details(member, cache)
            ).data
        )
