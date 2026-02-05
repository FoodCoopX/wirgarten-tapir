from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.payments.models import (
    MemberPaymentRhythm,
    MemberCredit,
    MemberCreditCreatedLogEntry,
)
from tapir.payments.serializers import (
    MemberPaymentRhythmDataSerializer,
    FuturePaymentsResponseSerializer,
    ExtendedMemberCreditSerializer,
    MemberCreditCreateSerializer,
    CabLoggedInUserChangeTargetsPaymentRhythmResponseSerializer,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Payment,
    CoopShareTransaction,
    MandateReference,
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.utils import check_permission_or_self, get_today


class GetFutureMemberPaymentsApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: FuturePaymentsResponseSerializer},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        if not request.user.has_perm(
            Permission.Coop.MANAGE
        ) and not get_parameter_value(
            ParameterKeys.MEMBERS_CAN_SEE_OWN_PAYMENTS, cache=self.cache
        ):
            raise PermissionDenied()

        member_payments = self.get_due_and_future_payments(member_id)
        extended_payments = self.build_extended_payments(
            member_id=member_id, member_payments=member_payments
        )

        member_credits = MemberCredit.objects.filter(
            member_id=member_id, due_date__gte=get_today(cache=self.cache)
        ).order_by("due_date")

        return Response(
            FuturePaymentsResponseSerializer(
                {"payments": extended_payments, "credits": member_credits}
            ).data
        )

    def get_due_and_future_payments(self, member_id):
        mandate_ref_ids = MandateReference.objects.filter(
            member_id=member_id
        ).values_list("ref", flat=True)
        member_payments = set(
            Payment.objects.filter(mandate_ref__ref__in=mandate_ref_ids).filter(
                Q(
                    due_date__gte=get_today(cache=self.cache),
                )
                | Q(status=Payment.PaymentStatus.DUE)
            )
        )
        current_month = get_today(cache=self.cache)
        current_month = current_month.replace(day=1)
        generated_payments = set()
        for _ in range(12):
            payments = MonthPaymentBuilder.build_payments_for_month(
                reference_date=current_month,
                cache=self.cache,
                generated_payments=generated_payments,
            )
            member_payments.update(
                [
                    payment
                    for payment in payments
                    if payment.mandate_ref_id in mandate_ref_ids
                ]
            )
            generated_payments.update(member_payments)
            current_month = get_first_of_next_month(current_month)
        return member_payments

    def build_extended_payments(self, member_id, member_payments):
        extended_payments = []
        existing_subscriptions = [
            subscription
            for subscription in TapirCache.get_all_subscriptions(cache=self.cache)
            if subscription.member_id == member_id
        ]
        existing_contributions = [
            contribution
            for contribution in TapirCache.get_all_solidarity_contributions(
                cache=self.cache
            )
            if contribution.member_id == member_id
        ]
        for payment in member_payments:
            subscriptions = []
            coop_share_transactions = []
            solidarity_contributions = []
            match payment.type:
                case "Genossenschaftsanteile":
                    coop_share_transactions = CoopShareTransaction.objects.filter(
                        payment=payment
                    )
                case (
                    MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
                ):
                    solidarity_contributions = (
                        self.get_relevant_solidarity_contributions(
                            existing_contributions=existing_contributions,
                            member_id=member_id,
                            payment=payment,
                        )
                    )
                case _:
                    subscriptions = self.get_relevant_subscriptions(
                        existing_subscriptions=existing_subscriptions,
                        member_id=member_id,
                        payment=payment,
                    )

            extended_payments.append(
                {
                    "payment": payment,
                    "subscriptions": subscriptions,
                    "coop_share_transactions": coop_share_transactions,
                    "solidarity_contributions": solidarity_contributions,
                }
            )
        return extended_payments

    def get_relevant_subscriptions(self, existing_subscriptions, member_id, payment):
        planned_renewed_subscriptions = [
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=subscription, cache=self.cache
            )
            for subscription in AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=payment.due_date, cache=self.cache
            )
            if subscription.member_id == member_id
        ]
        subscriptions = [
            subscription
            for subscription in existing_subscriptions + planned_renewed_subscriptions
            if subscription.mandate_ref == payment.mandate_ref
            and subscription.product.type.name == payment.type
            and DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=subscription.start_date,
                range_1_end=subscription.end_date,
                range_2_start=payment.subscription_payment_range_start,
                range_2_end=payment.subscription_payment_range_end,
            )
        ]
        return subscriptions

    def get_relevant_solidarity_contributions(
        self, existing_contributions, member_id, payment
    ):
        planned_renewed_contributions = [
            AutomaticSolidarityContributionRenewalService.build_renewed_contribution(
                contribution=contribution, cache=self.cache
            )
            for contribution in AutomaticSolidarityContributionRenewalService.get_contributions_that_will_be_renewed(
                reference_date=payment.due_date, cache=self.cache
            )
            if contribution.member_id == member_id
        ]
        contributions = [
            contribution
            for contribution in existing_contributions + planned_renewed_contributions
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=contribution.start_date,
                range_1_end=contribution.end_date,
                range_2_start=payment.subscription_payment_range_start,
                range_2_end=payment.subscription_payment_range_end,
            )
        ]
        return contributions


class GetMemberPaymentRhythmDataApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: MemberPaymentRhythmDataSerializer},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member = get_object_or_404(Member, id=request.query_params.get("member_id"))
        date = MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
            member=member, reference_date=get_today(cache=self.cache), cache=self.cache
        )
        current_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=get_today(cache=self.cache),
            cache=self.cache,
        )
        allowed_rhythms = {
            rhythm: MemberPaymentRhythmService.get_rhythm_display_name(rhythm=rhythm)
            for rhythm in MemberPaymentRhythmService.get_allowed_rhythms(
                cache=self.cache
            )
        }

        return Response(
            MemberPaymentRhythmDataSerializer(
                {
                    "date_of_next_rhythm_change": date,
                    "current_rhythm": current_rhythm,
                    "allowed_rhythms": allowed_rhythms,
                    "rhythm_history": MemberPaymentRhythm.objects.filter(
                        member=member
                    ).order_by("valid_from"),
                }
            ).data
        )


class SetMemberPaymentRhythmApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: str},
        request=inline_serializer(
            name="payment_rhythm_serializer",
            fields={
                "rhythm": serializers.CharField(),
                "member_id": serializers.CharField(),
            },
        ),
    )
    def post(self, request):
        member = get_object_or_404(Member, id=request.data["member_id"])

        rhythm = request.data.get("rhythm")
        if not MemberPaymentRhythmService.is_payment_rhythm_allowed(
            rhythm, cache=self.cache
        ):
            raise ValidationError(
                f"Diese Zahlungsintervall {rhythm} is nicht erlaubt, erlaubt sind: {MemberPaymentRhythmService.get_allowed_rhythms(cache=self.cache)}"
            )

        valid_from = MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
            member=member, reference_date=get_today(cache=self.cache), cache=self.cache
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            rhythm=rhythm,
            valid_from=valid_from,
            cache=self.cache,
            actor=request.user,
        )

        return Response("OK")


class MemberCreditTemplateView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Payments.VIEW
    template_name = "payments/credit_list.html"


class MemberCreditListApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: ExtendedMemberCreditSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="month_filter", type=int, required=False),
            OpenApiParameter(name="year_filter", type=int, required=False),
        ],
    )
    def get(self, request):
        member_credits = MemberCredit.objects.order_by("-due_date")

        month_filter = request.query_params.get("month_filter", None)
        if month_filter is not None and int(month_filter) > 0:
            member_credits = member_credits.filter(due_date__month=int(month_filter))

        year_filter = request.query_params.get("year_filter", None)
        if year_filter is not None:
            member_credits = member_credits.filter(due_date__year=int(year_filter))

        extended_credits = [
            {
                "credit": credit,
                "member": credit.member,
                "member_url": credit.member.get_absolute_url(),
                "mandate_ref": get_or_create_mandate_ref(
                    member=credit.member, cache=self.cache
                ).ref,
            }
            for credit in member_credits
        ]

        return Response(
            ExtendedMemberCreditSerializer(extended_credits, many=True).data
        )


class MemberCreditCreateApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(responses={200: str}, request=MemberCreditCreateSerializer)
    def post(self, request):
        serializer = MemberCreditCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = get_object_or_404(Member, id=serializer.validated_data["member_id"])

        member_credit = MemberCredit.objects.create(
            due_date=serializer.validated_data["due_date"],
            member=member,
            amount=serializer.validated_data["amount"],
            purpose=serializer.validated_data["purpose"],
            comment=serializer.validated_data["comment"],
        )

        MemberCreditCreatedLogEntry().populate(
            model=member_credit, user=member, actor=request.user
        ).save()

        return Response("OK")


class CabLoggedInUserChangeTargetsPaymentRhythm(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: CabLoggedInUserChangeTargetsPaymentRhythmResponseSerializer},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        member = get_object_or_404(Member, id=member_id)
        check_permission_or_self(member_id, request)

        if request.user.has_perm(Permission.Coop.MANAGE):
            can_change = True

        else:
            can_change = (
                TapirCache.get_member_payment_rhythm_object(
                    member=member,
                    reference_date=get_today(cache=self.cache),
                    cache=self.cache,
                )
                is None
            )

        current_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member, reference_date=get_today(cache=self.cache), cache=self.cache
        )

        data = {"can_change": can_change, "current_rhythm": current_rhythm}

        return Response(
            CabLoggedInUserChangeTargetsPaymentRhythmResponseSerializer(data).data
        )
