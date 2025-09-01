from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.serializers import (
    ExtendedPaymentSerializer,
    MemberPaymentRhythmDataSerializer,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import (
    Payment,
    CoopShareTransaction,
    MandateReference,
    Member,
)
from tapir.wirgarten.utils import check_permission_or_self, get_today


class GetFutureMemberPaymentsApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: ExtendedPaymentSerializer(many=True)},
        parameters=[OpenApiParameter(name="member_id", type=str)],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)

        member_payments = self.get_due_and_future_payments(member_id)
        extended_payments = self.build_extended_payments(
            member_id=member_id, member_payments=member_payments
        )

        return Response(ExtendedPaymentSerializer(extended_payments, many=True).data)

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
        for payment in member_payments:
            subscriptions = []
            coop_share_transactions = []
            if payment.type == "Genossenschaftsanteile":
                coop_share_transactions = CoopShareTransaction.objects.filter(
                    payment=payment
                )
            else:
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


class GetMemberPaymentRhythmDataApiView(APIView):
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
            member=member, rhythm=rhythm, valid_from=valid_from
        )

        return Response("OK")
