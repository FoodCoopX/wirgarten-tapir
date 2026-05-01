import datetime
import random

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.serializers import ListField
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES, IntendedUseTokens
from tapir.payments.models import (
    MemberPaymentRhythm,
    MemberCredit,
    MemberCreditCreatedLogEntry,
    MemberCreditSettledLogEntry,
)
from tapir.payments.serializers import (
    MemberPaymentRhythmDataSerializer,
    FuturePaymentsResponseSerializer,
    ExtendedMemberCreditSerializer,
    MemberCreditCreateSerializer,
    CabLoggedInUserChangeTargetsPaymentRhythmResponseSerializer,
    PaymentIntendedUsePreviewResponseSerializer,
)
from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month, get_last_day_of_month
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Payment,
    CoopShareTransaction,
    MandateReference,
    Member,
    Subscription,
    ProductType,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref
from tapir.wirgarten.utils import (
    check_permission_or_self,
    get_today,
    format_date,
    format_currency,
)


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
            member_id=member_id, member_payments=member_payments, cache=self.cache
        )

        member_credits = MemberCredit.objects.filter(
            member_id=member_id, due_date__gte=get_today(cache=self.cache)
        ).order_by("due_date")

        return Response(
            FuturePaymentsResponseSerializer(
                {
                    "payments": sorted(
                        extended_payments,
                        key=lambda extended_payment: extended_payment[
                            "payment"
                        ].due_date,
                    ),
                    "credits": member_credits,
                    "trial_period_enabled": get_parameter_value(
                        key=ParameterKeys.TRIAL_PERIOD_ENABLED, cache=self.cache
                    ),
                }
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

    @classmethod
    def build_extended_payments(cls, member_id, member_payments, cache: dict):
        extended_payments = []
        existing_subscriptions = [
            subscription
            for subscription in TapirCache.get_all_subscriptions(cache=cache)
            if subscription.member_id == member_id
        ]
        existing_contributions = [
            contribution
            for contribution in TapirCache.get_all_solidarity_contributions(cache=cache)
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
                        cls.get_relevant_solidarity_contributions(
                            existing_contributions=existing_contributions,
                            member_id=member_id,
                            payment=payment,
                            cache=cache,
                        )
                    )
                case _:
                    subscriptions = cls.get_relevant_subscriptions(
                        existing_subscriptions=existing_subscriptions,
                        member_id=member_id,
                        payment=payment,
                        cache=cache,
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

    @classmethod
    def get_relevant_subscriptions(
        cls, existing_subscriptions, member_id, payment, cache: dict
    ):
        planned_renewed_subscriptions = [
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription=subscription, cache=cache
            )
            for subscription in AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=payment.due_date, cache=cache
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

    @classmethod
    def get_relevant_solidarity_contributions(
        cls, existing_contributions, member_id, payment, cache: dict
    ):
        planned_renewed_contributions = [
            AutomaticSolidarityContributionRenewalService.build_renewed_contribution(
                contribution=contribution, cache=cache
            )
            for contribution in AutomaticSolidarityContributionRenewalService.get_contributions_that_will_be_renewed(
                reference_date=payment.due_date, cache=cache
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


class GetPastMemberPaymentsApiView(APIView):
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

        member_payments = self.get_past_payments(member_id)
        extended_payments = GetFutureMemberPaymentsApiView.build_extended_payments(
            member_id=member_id, member_payments=member_payments, cache=self.cache
        )

        member_credits = MemberCredit.objects.filter(
            member_id=member_id, due_date__lte=get_today(cache=self.cache)
        ).order_by("-due_date")

        return Response(
            FuturePaymentsResponseSerializer(
                {
                    "payments": sorted(
                        extended_payments,
                        key=lambda extended_payment: extended_payment[
                            "payment"
                        ].due_date,
                        reverse=True,
                    ),
                    "credits": member_credits,
                    "trial_period_enabled": get_parameter_value(
                        key=ParameterKeys.TRIAL_PERIOD_ENABLED, cache=self.cache
                    ),
                }
            ).data
        )

    def get_past_payments(self, member_id):
        mandate_ref_ids = MandateReference.objects.filter(
            member_id=member_id
        ).values_list("ref", flat=True)

        member_payments = set(
            Payment.objects.filter(mandate_ref__ref__in=mandate_ref_ids).filter(
                due_date__lte=get_today(cache=self.cache)
            )
        )

        return member_payments


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
            OpenApiParameter(
                name="show_all",
                type=bool,
                required=False,
                description="Show all credits",
            ),
        ],
    )
    def get(self, request):
        member_credits = MemberCredit.objects.order_by("-due_date")

        show_all = request.query_params.get("show_all", "false").lower() == "true"
        if not show_all:
            member_credits = member_credits.filter(settled_on__isnull=True)

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


class MemberCreditSettleApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        request=inline_serializer(
            name="MemberCreditSettle",
            fields={
                "credit_ids": ListField(child=serializers.CharField()),
            },
        ),
    )
    def post(self, request):
        credit_ids = request.data.get("credit_ids", [])
        credits_to_account = list(
            MemberCredit.objects.filter(id__in=credit_ids, settled_on__isnull=True)
        )
        now = timezone.now()
        for credit in credits_to_account:
            credit.settled_on = now
            credit.save()
            MemberCreditSettledLogEntry().populate(
                model=credit, user=credit.member, actor=request.user
            ).save()
        return Response(f"OK ({len(credits_to_account)} gebucht)")


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


class PaymentIntendedUsePreviewContractsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: PaymentIntendedUsePreviewResponseSerializer},
        parameters=[
            OpenApiParameter(name="pattern_old", type=str, required=True),
            OpenApiParameter(name="pattern_new", type=str, required=True),
        ],
    )
    def get(self, request):
        pattern_old = request.query_params.get("pattern_old", "")
        pattern_new = request.query_params.get("pattern_new", "")
        cache = {}

        payments = self._get_random_payments(cache=cache)

        response_data = {
            "previews_old": ["" for _ in payments],
            "previews_new": ["" for _ in payments],
            "error": "",
            "tokens": sorted(IntendedUseTokens.COMMON_TOKENS)
            + sorted(IntendedUseTokens.CONTRACT_TOKENS),
            "payments": payments,
            "members": [payment.mandate_ref.member for payment in payments],
        }
        try:
            response_data["previews_old"] = [
                IntendedUsePatternExpander.expand_pattern_contracts(
                    pattern=pattern_old, payment=payment, cache=cache
                )
                for payment in payments
            ]
            response_data["previews_new"] = [
                IntendedUsePatternExpander.expand_pattern_contracts(
                    pattern=pattern_new, payment=payment, cache=cache
                )
                for payment in payments
            ]
            self._add_fake_data(
                response_data=response_data,
                pattern_old=pattern_old,
                pattern_new=pattern_new,
                cache=cache,
            )
        except Exception as error:
            response_data["error"] = getattr(error, "message", repr(error))

        return Response(PaymentIntendedUsePreviewResponseSerializer(response_data).data)

    @classmethod
    def _get_random_payments(cls, cache: dict):
        first_subscription = Subscription.objects.order_by("start_date").first()
        if first_subscription is None:
            return []

        min_date = first_subscription.start_date
        max_date = min(
            Subscription.objects.order_by("start_date").last().start_date,
            get_today(cache=cache),
        )
        random_date = min_date + datetime.timedelta(
            days=random.randint(0, (max_date - min_date).days)
        )
        payments = Payment.objects.exclude(type=PAYMENT_TYPE_COOP_SHARES).filter(
            due_date__year=random_date.year, due_date__month=random_date.month
        )

        combined_payments = list(
            PaymentExportBuilder.combine_contract_payments_by_mandate_ref(
                payments=list(payments)
            )
        )
        payments = random.sample(combined_payments, k=min(len(combined_payments), 5))
        return sorted(
            payments,
            key=lambda payment: (
                payment.mandate_ref.member.member_no,
                payment.mandate_ref.member.last_name,
            ),
        )

    @classmethod
    def _add_fake_data(
        cls, response_data: dict, pattern_old: str, pattern_new: str, cache: dict
    ):
        fake_members = [
            Member(first_name="John", last_name="Doe", member_no=14, id="14"),
            Member(
                first_name="Maximilian",
                last_name="Mustermann",
                member_no=123456,
                id="123456",
            ),
        ]

        today = get_today(cache=cache)

        for fake_member in fake_members:
            is_short_member = fake_member.first_name == "John"

            token_value_overrides = {
                IntendedUseTokens.MONTHLY_PRICE_CONTRACTS_WITHOUT_SOLI: format_currency(
                    10 if is_short_member else 100
                ),
                IntendedUseTokens.MONTHLY_PRICE_CONTRACTS_WITH_SOLI: format_currency(
                    5 if is_short_member else 150
                ),
                IntendedUseTokens.MONTHLY_PRICE_JUST_SOLI: format_currency(
                    -5 if is_short_member else 50
                ),
                IntendedUseTokens.TOTAL_PRICE_CONTRACTS_WITHOUT_SOLI: format_currency(
                    10 if is_short_member else 1200
                ),
                IntendedUseTokens.TOTAL_PRICE_CONTRACTS_WITH_SOLI: format_currency(
                    5 if is_short_member else 900
                ),
                IntendedUseTokens.TOTAL_PRICE_JUST_SOLI: format_currency(
                    -5 if is_short_member else 300
                ),
                IntendedUseTokens.CONTRACT_LIST: cls._build_fake_contract_list(
                    short_version=is_short_member, cache=cache
                ),
                IntendedUseTokens.PAYMENT_RHYTHM: (
                    MemberPaymentRhythm.Rhythm.MONTHLY.label
                    if is_short_member
                    else MemberPaymentRhythm.Rhythm.QUARTERLY.label
                ),
            }

            response_data["members"].insert(0, fake_member)
            payment = Payment(
                mandate_ref=MandateReference(member=fake_member),
                amount=100,
                subscription_payment_range_start=(
                    today - datetime.timedelta(days=120)
                ).replace(day=1),
                subscription_payment_range_end=get_last_day_of_month(
                    today - datetime.timedelta(days=30)
                ),
            )
            response_data["payments"].insert(0, payment)
            response_data["previews_old"].insert(
                0,
                IntendedUsePatternExpander.expand_pattern_contracts(
                    pattern=pattern_old,
                    payment=payment,
                    cache=cache,
                    token_value_overrides=token_value_overrides,
                ),
            )
            response_data["previews_new"].insert(
                0,
                IntendedUsePatternExpander.expand_pattern_contracts(
                    pattern=pattern_new,
                    payment=payment,
                    cache=cache,
                    token_value_overrides=token_value_overrides,
                ),
            )

    @classmethod
    def _build_fake_contract_list(cls, short_version: bool, cache: dict):
        product_types = TapirCache.get_all_product_types(cache=cache)
        product_types = sorted(
            product_types,
            key=lambda product_type: product_type.name,
            reverse=not short_version,
        )

        product_type = product_types[0]
        product = cls._get_product_with_according_to_name_length(
            product_type=product_type, cache=cache, shortest=short_version
        )
        quantity = 1 if short_version else 13
        contract_list = Subscription(product=product, quantity=quantity).short_str()

        if short_version or len(product_types) == 1:
            return contract_list

        product_type = product_types[1]
        product = cls._get_product_with_according_to_name_length(
            product_type=product_type, cache=cache, shortest=short_version
        )
        quantity = 17
        contract_list += (
            ", " + Subscription(product=product, quantity=quantity).short_str()
        )

        return contract_list

    @classmethod
    def _get_product_with_according_to_name_length(
        cls, product_type: ProductType, cache: dict, shortest: bool
    ):
        products = TapirCache.get_products_with_product_type(
            cache=cache, product_type_id=product_type.id
        )
        products = sorted(
            products,
            key=lambda product: product.name,
            reverse=not shortest,
        )
        return products[0]


class PaymentIntendedUsePreviewCoopSharesApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: PaymentIntendedUsePreviewResponseSerializer},
        parameters=[
            OpenApiParameter(name="pattern_old", type=str, required=True),
            OpenApiParameter(name="pattern_new", type=str, required=True),
        ],
    )
    def get(self, request):
        pattern_old = request.query_params.get("pattern_old", "")
        pattern_new = request.query_params.get("pattern_new", "")
        cache = {}

        payments = self._get_random_payments(cache=cache)

        response_data = {
            "previews_old": ["" for _ in payments],
            "previews_new": ["" for _ in payments],
            "error": "",
            "tokens": sorted(IntendedUseTokens.COMMON_TOKENS)
            + sorted(IntendedUseTokens.COOP_SHARE_TOKENS),
            "payments": payments,
            "members": [payment.mandate_ref.member for payment in payments],
        }
        try:
            response_data["previews_old"] = [
                self._build_preview(payment=payment, pattern=pattern_old, cache=cache)
                for payment in payments
            ]
            response_data["previews_new"] = [
                self._build_preview(payment=payment, pattern=pattern_new, cache=cache)
                for payment in payments
            ]
            self._add_fake_data(
                response_data=response_data,
                pattern_old=pattern_old,
                pattern_new=pattern_new,
                cache=cache,
            )
        except Exception as error:
            response_data["error"] = getattr(error, "message", repr(error))

        return Response(PaymentIntendedUsePreviewResponseSerializer(response_data).data)

    @classmethod
    def _build_preview(cls, payment: Payment, pattern: str, cache: dict):
        return IntendedUsePatternExpander.expand_pattern_coop_shares_bought(
            pattern=pattern,
            member=payment.mandate_ref.member,
            number_of_shares=round(
                payment.amount
                / get_parameter_value(ParameterKeys.COOP_SHARE_PRICE, cache=cache)
            ),
            cache=cache,
        )

    @classmethod
    def _get_random_payments(cls, cache: dict):
        return list(
            Payment.objects.filter(type=PAYMENT_TYPE_COOP_SHARES)
            .select_related("mandate_ref__member")
            .order_by("?")[:5]
        )

    @classmethod
    def _add_fake_data(
        cls, response_data: dict, pattern_old: str, pattern_new: str, cache: dict
    ):
        fake_members = [
            Member(first_name="John", last_name="Doe", member_no=14),
            Member(first_name="Maximilian", last_name="Mustermann", member_no=123456),
        ]

        token_value_overrides = {
            IntendedUseTokens.COOP_ENTRY_DATE: format_date(get_today(cache=cache)),
        }

        for fake_member in fake_members:
            response_data["members"].insert(0, fake_member)
            response_data["payments"].insert(
                0,
                Payment(mandate_ref=MandateReference(member=fake_member), amount=100),
            )
            number_of_shares = 1 if fake_member.first_name == "John" else 123

            response_data["previews_old"].insert(
                0,
                IntendedUsePatternExpander.expand_pattern_coop_shares_bought(
                    pattern=pattern_old,
                    member=fake_member,
                    number_of_shares=number_of_shares,
                    cache=cache,
                    token_value_overrides=token_value_overrides,
                ),
            )
            response_data["previews_new"].insert(
                0,
                IntendedUsePatternExpander.expand_pattern_coop_shares_bought(
                    pattern=pattern_new,
                    member=fake_member,
                    number_of_shares=number_of_shares,
                    cache=cache,
                    token_value_overrides=token_value_overrides,
                ),
            )
