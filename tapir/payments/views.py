from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.payments.serializers import ExtendedPaymentSerializer
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

        mandate_ref_ids = MandateReference.objects.filter(
            member_id=member_id
        ).values_list("ref", flat=True)
        member_payments = list(
            Payment.objects.filter(mandate_ref__ref__in=mandate_ref_ids).filter(
                Q(
                    due_date__gte=get_today(cache=self.cache),
                )
                | Q(status=Payment.PaymentStatus.DUE)
            )
        )

        current_month = get_today(cache=self.cache)
        generated_payments = []
        for _ in range(12):
            current_month = get_first_of_next_month(current_month)
            payments = MonthPaymentBuilder.build_payments_for_month(
                reference_date=current_month,
                cache=self.cache,
                generated_payments=generated_payments,
            )
            generated_payments.extend(payments)
            member_payments.extend(
                [
                    payment
                    for payment in payments
                    if payment.mandate_ref_id in mandate_ref_ids
                ]
            )

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
                subscriptions = self.get_subscriptions(
                    existing_subscriptions, member_id, payment, subscriptions
                )
            extended_payments.append(
                {
                    "payment": payment,
                    "subscriptions": subscriptions,
                    "coop_share_transactions": coop_share_transactions,
                }
            )

        return Response(ExtendedPaymentSerializer(extended_payments, many=True).data)

    def get_subscriptions(
        self, existing_subscriptions, member_id, payment, subscriptions
    ):
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
