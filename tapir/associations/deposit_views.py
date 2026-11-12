from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.associations.serializers import (
    AssociationDepositDetailsSerializer,
    IncreaseAssociationDepositRequestSerializer,
)
from tapir.associations.services.association_deposit_member_service import (
    AssociationDepositMemberService,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self


class MemberAssociationDepositView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("member_id", str, OpenApiParameter.PATH)],
        responses={200: AssociationDepositDetailsSerializer},
    )
    def get(self, request, member_id):
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, pk=member_id)
        details = AssociationDepositMemberService.get_details(member, {})
        details["can_increase"] &= request.user.pk == member_id
        return Response(AssociationDepositDetailsSerializer(details).data)

    @extend_schema(
        parameters=[OpenApiParameter("member_id", str, OpenApiParameter.PATH)],
        request=IncreaseAssociationDepositRequestSerializer,
        responses={200: AssociationDepositDetailsSerializer},
    )
    def post(self, request, member_id):
        if request.user.pk != member_id:
            raise PermissionDenied
        member = get_object_or_404(Member, pk=member_id)
        serializer = IncreaseAssociationDepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmation"]:
            raise ValidationError(
                {"confirmation": "Bitte bestätige die einmalige Lastschrift."}
            )
        cache = {}
        try:
            AssociationDepositMemberService.increase(
                member,
                serializer.validated_data["total_amount"],
                serializer.validated_data["previous_amount"],
                request.user,
                cache,
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages) from error
        details = AssociationDepositMemberService.get_details(member, cache)
        return Response(AssociationDepositDetailsSerializer(details).data)
