import decimal
from decimal import Decimal

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.serializers import (
    SolidarityContributionSerializer,
    MemberSolidarityContributionsResponseSerializer,
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
            "change_valid_from": ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=cache),
                apply_buffer_time=False,
                cache=cache,
            ),
            "user_can_set_lower_value": request.user.has_perm(Permission.Coop.MANAGE),
        }

        return Response(MemberSolidarityContributionsResponseSerializer(data).data)


class UpdateMemberSolidarityContributionApiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: SolidarityContributionSerializer(many=True)},
        request=inline_serializer(
            name="soli_serializer",
            fields={
                "amount": serializers.FloatField(),
                "member_id": serializers.CharField(),
            },
        ),
    )
    def post(self, request):
        member_id = request.data.get("member_id")
        check_permission_or_self(member_id, request)

        member = get_object_or_404(Member, id=member_id)

        try:
            amount = Decimal(request.data.get("amount"))
        except decimal.InvalidOperation:
            raise ValidationError("Ungültige Zahl " + request.data.get("amount"))

        cache = {}
        change_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=cache),
            apply_buffer_time=False,
            cache=cache,
        )

        if not MemberSolidarityContributionService.is_user_allowed_to_change_contribution(
            logged_in_user=request.user,
            target_member_id=member.id,
            change_date=change_date,
            new_amount=amount,
            cache=cache,
        ):
            raise ValidationError(
                "Nur Admins können den Solidarbeitrag nach Unten anpassen. Kontaktiere bitte "
                + get_parameter_value(key=ParameterKeys.SITE_ADMIN_EMAIL, cache=cache)
            )

        MemberSolidarityContributionService.assign_contribution_to_member(
            member_id=member.id, change_date=change_date, cache=cache, amount=amount
        )

        contributions = SolidarityContribution.objects.filter(
            member_id=member_id
        ).order_by("start_date")

        return Response(SolidarityContributionSerializer(contributions, many=True).data)
