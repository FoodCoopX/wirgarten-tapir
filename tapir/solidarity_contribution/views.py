import decimal
from decimal import Decimal

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.serializers import (
    MemberSolidarityContributionsResponseSerializer,
    UpdateMemberSolidarityContributionRequestSerializer,
    UpdateMemberSolidarityContributionResponseSerializer,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import check_permission_or_self, get_today


class MemberSolidarityContributionsApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MemberSolidarityContributionsResponseSerializer},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)
        cache = {}

        data = {
            "contributions": SolidarityContribution.objects.filter(
                member_id=member_id
            ).order_by("start_date"),
            "change_valid_from": UpdateMemberSolidarityContributionApiView.get_change_date(
                member=Member.objects.get(id=member_id),
                start_contribution_now=True,
                cache=cache,
            ),
            "user_can_set_lower_value": request.user.has_perm(Permission.Coop.MANAGE),
            "user_can_update_contribution": request.user.has_perm(
                Permission.Coop.MANAGE
            )
            or get_parameter_value(
                ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE,
                cache=cache,
            ),
        }

        return Response(MemberSolidarityContributionsResponseSerializer(data).data)


class UpdateMemberSolidarityContributionApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UpdateMemberSolidarityContributionResponseSerializer},
        request=UpdateMemberSolidarityContributionRequestSerializer,
    )
    def post(self, request):
        request_serializer = UpdateMemberSolidarityContributionRequestSerializer(
            data=request.data
        )
        request_serializer.is_valid(raise_exception=True)

        member_id = request_serializer.validated_data["member_id"]
        check_permission_or_self(member_id, request)

        member = get_object_or_404(Member, id=member_id)

        try:
            amount = Decimal(request_serializer.validated_data["amount"])
        except decimal.InvalidOperation:
            return self.build_response(
                member_id=member_id,
                error="Ungültige Zahl " + request_serializer.validated_data["amount"],
            )

        cache = {}
        change_date = self.get_change_date(
            start_contribution_now=request_serializer.validated_data[
                "start_contribution_now"
            ],
            member=member,
            cache=cache,
        )

        if not MemberSolidarityContributionService.is_user_allowed_to_change_contribution(
            logged_in_user=request.user,
            target_member_id=member.id,
            change_date=change_date,
            new_amount=amount,
            cache=cache,
        ):
            return self.build_response(
                member_id=member_id,
                error="Du kannst deinen Solidarbeitrag nur erhöhen, aber nicht selbstständig reduzieren. Kontaktiere dazu deine Solawi an "
                + get_parameter_value(key=ParameterKeys.SITE_ADMIN_EMAIL, cache=cache),
            )

        MemberSolidarityContributionService.assign_contribution_to_member(
            member=member,
            change_date=change_date,
            cache=cache,
            amount=amount,
            actor=request.user,
        )

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            actor=request.user,
            product_type_id_or_soli=MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION,
            reference_date=change_date,
            comment="Solidarbeitrag vom Admin durch dem Mitgliederbereich reduziert",
            cache=cache,
        )

        return self.build_response(member_id=member_id, error=None)

    @classmethod
    def build_response(cls, member_id: str, error: str | None):
        contributions = SolidarityContribution.objects.filter(
            member_id=member_id
        ).order_by("start_date")

        return Response(
            UpdateMemberSolidarityContributionResponseSerializer(
                {
                    "contributions": contributions,
                    "updated": error is None,
                    "error": error,
                }
            ).data
        )

    @classmethod
    def get_change_date(cls, start_contribution_now: bool, member: Member, cache: dict):
        change_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=cache),
            apply_buffer_time=False,
            cache=cache,
        )
        if start_contribution_now:
            return change_date

        first_contribution = (
            SolidarityContribution.objects.filter(member=member)
            .order_by("start_date")
            .first()
        )
        if first_contribution is None:
            return change_date

        return max(change_date, first_contribution.start_date)
