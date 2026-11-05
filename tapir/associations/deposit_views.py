from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.associations.deposit_serializers import (
    DepositChangeSerializer,
    DepositDetailsSerializer,
)
from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_service import (
    AssociationDepositService,
)
from tapir.associations.services.deposit_configuration import DepositConfiguration
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member


class MemberDepositView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def check_access(request, member_id):
        if request.user.pk != member_id and not request.user.has_perm(
            Permission.Coop.MANAGE
        ):
            raise PermissionDenied()

    @staticmethod
    def details(member, request, cache):
        deposit = AssociationDeposit.objects.filter(member=member).first()
        configuration = DepositConfiguration.get(cache)
        data = {
            "configuration": configuration,
            "exists": deposit is not None,
            "can_manage": request.user.has_perm(Permission.Coop.MANAGE),
            "can_increase": bool(
                configuration["enabled"]
                and configuration["allow_extra_member"]
                and deposit
                and deposit.agreed_amount is not None
                and not deposit.hardship_pending
                and not deposit.cancellation_date
            ),
            "revision": deposit.revision if deposit else 0,
            "agreed_amount": deposit.agreed_amount if deposit else None,
            "hardship_pending": deposit.hardship_pending if deposit else False,
            "exception_authorized": deposit.exception_authorized if deposit else False,
            "cancellation_date": deposit.cancellation_date if deposit else None,
            **(
                AssociationDepositService.balances(deposit, cache)
                if deposit
                else dict.fromkeys(
                    [
                        "received",
                        "refunded",
                        "balance",
                        "pending",
                        "committed",
                        "refundable",
                    ],
                    0,
                )
            ),
            "payments": (
                [
                    dict(
                        id=p.pk,
                        amount=p.amount,
                        due_date=p.due_date,
                        exported=p.transaction_id is not None,
                        instalment_number=p.instalment_number,
                    )
                    for p in deposit.payments.order_by("due_date", "id")
                ]
                if deposit
                else []
            ),
            "bookings": (
                deposit.bookings.order_by("date", "created_at") if deposit else []
            ),
        }
        return DepositDetailsSerializer(data).data

    @extend_schema(responses=DepositDetailsSerializer)
    def get(self, request, member_id):
        self.check_access(request, member_id)
        return Response(
            self.details(get_object_or_404(Member, pk=member_id), request, {})
        )

    @extend_schema(request=DepositChangeSerializer, responses=DepositDetailsSerializer)
    def post(self, request, member_id):
        self.check_access(request, member_id)
        serializer = DepositChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        administrative = request.user.has_perm(Permission.Coop.MANAGE)
        if data["action"] != "increase" and not administrative:
            raise PermissionDenied()
        member = get_object_or_404(Member, pk=member_id)
        cache = {}
        try:
            AssociationDepositService.apply(
                member=member,
                actor=request.user,
                cache=cache,
                request_id=str(data.pop("request_id")),
                expected_revision=data.pop("expected_revision"),
                data=data,
                administrative=administrative and data["action"] != "increase",
            )
        except DjangoValidationError as error:
            raise ValidationError(error.messages)
        return Response(self.details(member, request, cache))
