import datetime

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, permissions
from rest_framework.exceptions import (
    MethodNotAllowed,
    ValidationError as RestValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.associations.apps import AssociationsConfig
from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembershipTypePrice,
    AssociationMembership,
    AssociationMembershipUpdatedLogEntry,
)
from tapir.associations.serializers import (
    AssociationMembershipTypeSerializer,
    AssociationMembershipTypePriceSerializer,
    AdminSetAssociationMembershipRequestSerializer,
    MemberAssociationMembershipDetailsSerializer,
    ExistingMemberUpdatesAssociationMembershipRequest,
    SetAssociationMembershipEndDateRequestSerializer,
    NumberOfAssociationMembersPerMonthResponseSerializer,
)
from tapir.associations.services.association_membership_change_handler import (
    AssociationMembershipChangeHandler,
)
from tapir.associations.services.dashboard_data_builder import DashboardDataBuilder
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
from tapir.wirgarten.utils import (
    check_permission_or_self,
    get_today,
    get_now,
    format_date,
)


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

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            method="DELETE",
            detail="Association membership types must be deleted via the dedicated hard-delete / soft-delete calls",
        )


class AssociationMembershipTypeSoftDeleteApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        parameters=[OpenApiParameter(name="type_id", type=str)],
    )
    def delete(self, request):
        type_id = request.query_params.get("type_id")
        membership_type = get_object_or_404(AssociationMembershipType, id=type_id)

        if not AssociationMembership.objects.filter(type=membership_type).exists():
            raise RestValidationError(
                "This membership type has no membership, it should be hard-deleted instead of soft-deleted"
            )

        membership_type.deleted = True
        membership_type.save()

        return Response("Marked as deleted")


class AssociationMembershipTypeHardDeleteApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        parameters=[OpenApiParameter(name="type_id", type=str)],
    )
    def delete(self, request):
        type_id = request.query_params.get("type_id")
        membership_type = get_object_or_404(AssociationMembershipType, id=type_id)

        if AssociationMembership.objects.filter(type=membership_type).exists():
            raise RestValidationError(
                "Memberships with this type exist, it should be soft-deleted instead of hard-deleted"
            )

        membership_type.delete()

        return Response("deleted")


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
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

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


class SetAssociationMembershipEndDateApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=SetAssociationMembershipEndDateRequestSerializer,
    )
    def post(self, request):
        serializer = SetAssociationMembershipEndDateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cache = {}

        membership = get_object_or_404(
            AssociationMembership, id=serializer.validated_data["membership_id"]
        )
        end_date = serializer.validated_data["end_date"]

        if end_date < membership.start_date:
            return Response(
                OrderConfirmationResponseSerializer(
                    {
                        "order_confirmed": False,
                        "error": "Das End-Datum muss nach dem Start-Datum sein",
                    }
                ).data
            )

        with transaction.atomic():
            before_changes = freeze_for_log(membership)
            end_date_before = membership.end_date
            membership.end_date = end_date
            membership.cancellation_ts = get_now(cache=cache)
            membership.save()
            AssociationMembershipUpdatedLogEntry().populate(
                old_frozen=before_changes,
                new_model=membership,
                actor=request.user,
                user=membership.member,
            ).save()

            TransactionalTrigger.fire_action(
                trigger_data=TransactionalTriggerData(
                    key=AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_END_DATE_SET,
                    recipient_id_in_base_queryset=membership.member_id,
                    token_data={
                        "end_date_before": format_date(end_date_before),
                        "end_date_after": format_date(membership.end_date),
                        "membership_type_name": membership.type.name,
                    },
                ),
            )

        return Response(
            OrderConfirmationResponseSerializer({"order_confirmed": True}).data
        )


class NumberOfAssociationMembersPerMonthApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="start_date", type=datetime.date),
            OpenApiParameter(name="end_date", type=datetime.date),
        ],
        responses={200: NumberOfAssociationMembersPerMonthResponseSerializer},
    )
    def get(self, request):
        start_date_as_string = request.query_params.get("start_date")
        start_date = datetime.datetime.strptime(start_date_as_string, "%Y-%m-%d").date()
        end_date_as_string = request.query_params.get("end_date")
        end_date = datetime.datetime.strptime(end_date_as_string, "%Y-%m-%d").date()

        labels, datasets = DashboardDataBuilder.build_dashboard_data(
            start_date=start_date, end_date=end_date, count_function=self.count_function
        )

        return Response(
            NumberOfAssociationMembersPerMonthResponseSerializer(
                {
                    "labels": labels,
                    "datasets": datasets,
                }
            ).data
        )

    @classmethod
    def count_function(
        cls, current_date: datetime.date, membership_type: AssociationMembershipType
    ):
        return (
            AssociationMembership.objects.filter(
                start_date__lte=current_date, type=membership_type
            )
            .filter(Q(end_date=None) | Q(end_date__gte=current_date))
            .count()
        )


class NumberOfAssociationMembershipCancellationRelativeToEndDatePerMonthApiView(
    APIView
):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="start_date", type=datetime.date),
            OpenApiParameter(name="end_date", type=datetime.date),
        ],
        responses={200: NumberOfAssociationMembersPerMonthResponseSerializer},
    )
    def get(self, request):
        start_date_as_string = request.query_params.get("start_date")
        start_date = datetime.datetime.strptime(start_date_as_string, "%Y-%m-%d").date()
        end_date_as_string = request.query_params.get("end_date")
        end_date = datetime.datetime.strptime(end_date_as_string, "%Y-%m-%d").date()

        labels, datasets = DashboardDataBuilder.build_dashboard_data(
            start_date=start_date, end_date=end_date, count_function=self.count_function
        )

        return Response(
            NumberOfAssociationMembersPerMonthResponseSerializer(
                {
                    "labels": labels,
                    "datasets": datasets,
                }
            ).data
        )

    @classmethod
    def count_function(
        cls, current_date: datetime.date, membership_type: AssociationMembershipType
    ):
        return AssociationMembership.objects.filter(
            type=membership_type,
            end_date__year=current_date.year,
            end_date__month=current_date.month,
        ).count()


class NumberOfAssociationMembershipCancellationRelativeToCancellationDatePerMonthApiView(
    APIView
):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="start_date", type=datetime.date),
            OpenApiParameter(name="end_date", type=datetime.date),
        ],
        responses={200: NumberOfAssociationMembersPerMonthResponseSerializer},
    )
    def get(self, request):
        start_date_as_string = request.query_params.get("start_date")
        start_date = datetime.datetime.strptime(start_date_as_string, "%Y-%m-%d").date()
        end_date_as_string = request.query_params.get("end_date")
        end_date = datetime.datetime.strptime(end_date_as_string, "%Y-%m-%d").date()

        labels, datasets = DashboardDataBuilder.build_dashboard_data(
            start_date=start_date, end_date=end_date, count_function=self.count_function
        )

        return Response(
            NumberOfAssociationMembersPerMonthResponseSerializer(
                {
                    "labels": labels,
                    "datasets": datasets,
                }
            ).data
        )

    @classmethod
    def count_function(
        cls, current_date: datetime.date, membership_type: AssociationMembershipType
    ):
        return AssociationMembership.objects.filter(
            type=membership_type,
            cancellation_ts__year=current_date.year,
            cancellation_ts__month=current_date.month,
        ).count()
