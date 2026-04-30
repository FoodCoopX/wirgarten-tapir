from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import (
    Payment,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class PaymentExportIntendedUseBuilder:
    @classmethod
    def build_intended_use(cls, payment: Payment, is_contracts: bool, cache: dict):
        if get_parameter_value(
            key=ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM, cache=cache
        ):
            return cls._build_intended_use_from_pattern(
                payment=payment, is_contracts=is_contracts, cache=cache
            )

        return cls._build_intended_use_legacy(
            is_contracts=is_contracts, payment=payment, cache=cache
        )

    @classmethod
    def _build_intended_use_legacy(
        cls, payment: Payment, is_contracts: bool, cache: dict
    ):
        payment_type_display = cls.get_payment_type_display_legacy(
            contract_payments=is_contracts
        )
        return f"{get_parameter_value(key=ParameterKeys.SITE_NAME, cache=cache)}, {payment.mandate_ref.member.last_name}, {payment_type_display}"

    @classmethod
    def _build_intended_use_from_pattern(
        cls, payment: Payment, is_contracts: bool, cache: dict
    ):
        if is_contracts:
            parameter_key = cls._get_intended_use_case(payment=payment, cache=cache)
            return IntendedUsePatternExpander.expand_pattern_contracts(
                pattern=get_parameter_value(key=parameter_key, cache=cache),
                payment=payment,
                cache=cache,
            )
        return IntendedUsePatternExpander.expand_pattern_coop_shares_bought(
            pattern=get_parameter_value(
                key=ParameterKeys.PAYMENT_INTENDED_USE_COOP_SHARES, cache=cache
            ),
            member=payment.mandate_ref.member,
            number_of_shares=round(
                payment.amount
                / get_parameter_value(key=ParameterKeys.COOP_SHARE_PRICE, cache=cache)
            ),
            cache=cache,
        )

    @classmethod
    def _get_intended_use_case(cls, payment: Payment, cache: dict):
        member_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=payment.mandate_ref.member,
            reference_date=payment.subscription_payment_range_start,
            cache=cache,
        )

        range_start = payment.subscription_payment_range_start
        start_if_normal = MemberPaymentRhythmService.get_first_day_of_rhythm_period(
            rhythm=member_rhythm, reference_date=range_start, cache=cache
        )
        range_end = payment.subscription_payment_range_end
        end_if_normal = MemberPaymentRhythmService.get_last_day_of_rhythm_period(
            rhythm=member_rhythm, reference_date=range_end, cache=cache
        )
        if range_start != start_if_normal or range_end != end_if_normal:
            return ParameterKeys.PAYMENT_INTENDED_USE_MULTIPLE_MONTH_INVOICE

        solidarity_contribution = SolidarityContribution.objects.filter(
            member=payment.mandate_ref.member,
            start_date__lte=payment.subscription_payment_range_end,
            end_date__gte=payment.subscription_payment_range_start,
        ).first()
        if solidarity_contribution is None:
            return ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE

        subscriptions = IntendedUsePatternExpander.get_relevant_subscriptions(
            payment=payment, member=payment.mandate_ref.member
        )

        if not subscriptions.exists():
            return ParameterKeys.PAYMENT_INTENDED_USE_SOLI_CONTRIBUTION_ONLY

        if solidarity_contribution.amount < 0:
            return (
                ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE_SOLIDARITY_SUPPORTED
            )

        return ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE

    @classmethod
    def get_payment_type_display_legacy(cls, contract_payments: bool):
        return "Verträge" if contract_payments else PAYMENT_TYPE_COOP_SHARES
