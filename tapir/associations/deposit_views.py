from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as RestValidationError,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.associations.serializers import (
    AssociationDepositDetailsSerializer,
    IncreaseAssociationDepositRequestSerializer,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.services.association_deposit_member_service import (
    AssociationDepositMemberService,
)
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self, get_today


class MemberAssociationDepositView(APIView):
    permission_classes = [IsAuthenticated]

    def check_permissions(self, request: Request) -> None:
        super().check_permissions(request)
        self.cache = {}
        if not association_deposits_enabled(self.cache):
            raise PermissionDenied("Vereinseinlagen sind nicht aktiviert.")

    @extend_schema(
        parameters=[OpenApiParameter("member_id", str, OpenApiParameter.PATH)],
        responses={200: AssociationDepositDetailsSerializer},
    )
    def get(self, request: Request, member_id: str) -> Response:
        cache = self.cache
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, pk=member_id)
        details = AssociationDepositMemberService.get_details(
            member=member, cache=cache
        )
        if not request.user.has_perm(Permission.Accounts.MANAGE):
            details["can_increase"] &= get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
            )
        return Response(AssociationDepositDetailsSerializer(details).data)

    @extend_schema(
        parameters=[OpenApiParameter("member_id", str, OpenApiParameter.PATH)],
        request=IncreaseAssociationDepositRequestSerializer,
        responses={200: AssociationDepositDetailsSerializer},
    )
    def post(self, request: Request, member_id: str) -> Response:
        cache = self.cache
        check_permission_or_self(pk=member_id, request=request)
        if not request.user.has_perm(
            Permission.Accounts.MANAGE
        ) and not get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
        ):
            raise PermissionDenied(
                "Einlagenerhöhungen sind für Mitglieder nicht aktiviert."
            )
        member = get_object_or_404(Member, pk=member_id)
        serializer = IncreaseAssociationDepositRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmation"]:
            raise RestValidationError(
                {"confirmation": "Bitte bestätige die einmalige Lastschrift."}
            )
        try:
            amount = AssociationDepositMemberService.validate_increase(
                member=member,
                total_amount=serializer.validated_data["total_amount"],
                cache=cache,
            )
        except DjangoValidationError as error:
            raise RestValidationError(error.messages) from error
        AssociationDepositPaymentCreator.create_deposit_and_payment(
            member=member,
            amount=amount,
            start_date=get_today(cache=cache),
            actor=request.user,
            cache=cache,
        )
        details = AssociationDepositMemberService.get_details(
            member=member, cache=cache
        )
        return Response(AssociationDepositDetailsSerializer(details).data)
