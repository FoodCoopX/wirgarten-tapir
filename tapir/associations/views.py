import datetime

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
    AssociationMembership,
)
from tapir.associations.serializers import (
    AssociationMembershipTypeSerializer,
    AssociationMembershipTypePriceSerializer,
    AdminSetAssociationMembershipRequestSerializer,
    MemberAssociationMembershipDetailsSerializer,
    ExistingMemberUpdatesAssociationMembershipRequest,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.util import freeze_for_log
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.growing_period_choice_provider import (
    GrowingPeriodChoiceProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import check_permission_or_self, get_today, get_now


class AssociationMembershipConfigView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "associations/association_membership_config_view.html"


class AssociationMembershipTypeViewSet(viewsets.ModelViewSet):
    queryset = AssociationMembershipType.objects.all()
    serializer_class = AssociationMembershipTypeSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = context.get("cache", {})
        return context


class AssociationMembershipTypePriceViewSet(viewsets.ModelViewSet):
    queryset = AssociationMembershipTypePrice.objects.all()
    serializer_class = AssociationMembershipTypePriceSerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["cache"] = context.get("cache", {})
        return context


class MemberAssociationMembershipDetails(APIView):
    permission_classes = []

    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
        responses={200: MemberAssociationMembershipDetailsSerializer()},
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)

        memberships = AssociationMembership.objects.filter(
            member_id=member_id
        ).order_by("start_date")
        order_wizard_url = None
        if AssociationMembershipType.objects.count() > 1:
            order_wizard_url = reverse(
                "bestell_wizard:bestell_wizard_association_membership",
                kwargs={"member_id": member_id},
            )

        return Response(
            MemberAssociationMembershipDetailsSerializer(
                {"memberships": memberships, "order_wizard_url": order_wizard_url},
                context={"cache": {}},
            ).data
        )


class AdminSetAssociationMembership(APIView):
    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=AdminSetAssociationMembershipRequestSerializer,
    )
    def post(self, request):
        serializer = AdminSetAssociationMembershipRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cache = {}

        member = get_object_or_404(Member, id=serializer.validated_data["member_id"])
        membership_type = get_object_or_404(
            AssociationMembershipType,
            id=serializer.validated_data["membership_type_id"],
        )
        start_date = serializer.validated_data["start_date"]

        with transaction.atomic():
            AssociationMembershipChangeHandler.start_membership(
                member=member,
                association_membership_type=membership_type,
                start_date=start_date,
                actor=request.user,
                cache=cache,
            )

        return Response(
            OrderConfirmationResponseSerializer({"order_confirmed": True}).data
        )


class ExistingMemberUpdatesAssociationMembershipApiView(APIView):
    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=ExistingMemberUpdatesAssociationMembershipRequest,
    )
    def post(self, request):
        serializer = ExistingMemberUpdatesAssociationMembershipRequest(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(pk=member_id, request=request)
        cache = {}

        member = Member.objects.get(id=member_id)

        iban = serializer.validated_data.get("iban", None)
        account_owner = serializer.validated_data.get("account_owner", None)
        association_membership_type = get_object_or_404(
            AssociationMembershipType,
            id=serializer.validated_data["association_membership_type_id"],
        )
        try:
            start_date, update_banking_data = self.validate(
                member=member,
                iban=iban,
                account_owner=account_owner,
                association_membership_type=association_membership_type,
                cache=cache,
            )
        except DjangoValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {
                        "order_confirmed": False,
                        "error": error.message,
                    }
                ).data
            )

        with transaction.atomic():
            self.apply_changes(
                member=member,
                association_membership_type=association_membership_type,
                start_date=start_date,
                update_banking_data=update_banking_data,
                iban=iban,
                account_owner=account_owner,
                actor=request.user,
                cache=cache,
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {
                    "order_confirmed": True,
                    "redirect_url": reverse(
                        "wirgarten:member_detail", kwargs={"pk": member_id}
                    ),
                }
            ).data
        )

    @classmethod
    def validate(
        cls,
        member: Member,
        iban: str | None,
        account_owner: str | None,
        association_membership_type: AssociationMembershipType,
        cache: dict,
    ):
        today = get_today(cache=cache)
        growing_periods = GrowingPeriodChoiceProvider.get_available_growing_periods(
            reference_date=today, cache=cache
        )
        start_date = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_periods[0],
                reference_date=today,
                cache=cache,
                apply_buffer_time=True,
            )
        )

        current_membership = TapirCache.get_member_association_membership_at_date(
            member=member, reference_date=start_date, cache=cache
        )

        if (
            current_membership
            and current_membership.type == association_membership_type
        ):
            raise DjangoValidationError(
                "Du bist schon mitglied mit dem gleichem Mitgliedschaftstyp"
            )

        needs_banking_data = (
            MemberNeedsBankingDataChecker.does_member_need_banking_data(member)
        )

        if needs_banking_data and (not iban or not account_owner):
            raise DjangoValidationError(
                "Dieses Mitglied braucht noch Bank-Daten (IBAN usw.)"
            )

        return start_date, needs_banking_data

    @classmethod
    def apply_changes(
        cls,
        member: Member,
        association_membership_type: AssociationMembershipType,
        start_date: datetime.date,
        actor,
        update_banking_data: bool,
        iban: str | None,
        account_owner: str | None,
        cache: dict,
    ):

        with transaction.atomic():
            AssociationMembershipChangeHandler.start_membership(
                member=member,
                association_membership_type=association_membership_type,
                start_date=start_date,
                actor=actor,
                cache=cache,
            )

            if update_banking_data:
                frozen_before = freeze_for_log(member)
                member.iban = iban
                member.account_owner = account_owner
                member.sepa_consent = get_now(cache=cache)
                member.save()

                UpdateTapirUserLogEntry().populate(
                    old_frozen=frozen_before,
                    new_model=member,
                    actor=actor,
                    user=member,
                ).save()

                TransactionalTrigger.fire_action(
                    trigger_data=TransactionalTriggerData(
                        key=Events.MEMBERAREA_CHANGE_DATA,
                        recipient_id_in_base_queryset=member.id,
                    ),
                )
