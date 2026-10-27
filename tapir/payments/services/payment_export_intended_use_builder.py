from tapir.associations.services.association_membership_price_type_getter import (
    AssociationMembershipTypePriceGetter,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
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
                key=(
                    ParameterKeys.PAYMENT_INTENDED_USE_COOP_SHARES
                    if payment.instalment_number is None
                    else ParameterKeys.PAYMENT_INTENDED_USE_COOP_SHARES_INSTALMENT
                ),
                cache=cache,
            ),
            member=payment.mandate_ref.member,
            payment=payment,
            number_of_shares=cls.get_number_of_coop_shares(
                payment=payment, cache=cache
            ),
            cache=cache,
        )

    @classmethod
    def get_number_of_coop_shares(cls, payment: Payment, cache: dict) -> int:
        if payment.coop_share_transaction is not None:
            return payment.coop_share_transaction.quantity

        # Payments created before 27.10.26  were not linked to their transaction
        return round(
            payment.amount
            / get_parameter_value(key=ParameterKeys.COOP_SHARE_PRICE, cache=cache)
        )

    @classmethod
    def _get_intended_use_case(cls, payment: Payment, cache: dict):
        if cls._is_last_payment(payment=payment, cache=cache):
            return ParameterKeys.PAYMENT_INTENDED_USE_LAST_INVOICE

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

        member_contributions = TapirCache.get_all_solidarity_contributions_for_member(
            member_id=payment.mandate_ref.member_id, cache=cache
        )
        relevant_contributions = [
            contribution
            for contribution in member_contributions
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=payment.subscription_payment_range_start,
                range_1_end=payment.subscription_payment_range_end,
                range_2_start=contribution.start_date,
                range_2_end=contribution.end_date,
            )
        ]
        if len(relevant_contributions) == 0:
            return ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE

        subscriptions = IntendedUsePatternExpander.get_relevant_subscriptions(
            payment=payment, member=payment.mandate_ref.member, cache=cache
        )

        if len(subscriptions) == 0:
            return ParameterKeys.PAYMENT_INTENDED_USE_SOLI_CONTRIBUTION_ONLY

        if relevant_contributions[0].amount < 0:
            return (
                ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE_SOLIDARITY_SUPPORTED
            )

        return ParameterKeys.PAYMENT_INTENDED_USE_MONTHLY_INVOICE

    @classmethod
    def _is_last_payment(cls, payment: Payment, cache: dict):
        member_id = payment.mandate_ref.member_id
        range_start = payment.subscription_payment_range_start
        range_end = payment.subscription_payment_range_end

        contracts = TapirCache.get_all_subscriptions_for_member(
            member_id=member_id, cache=cache
        ) + [
            contribution
            for contribution in TapirCache.get_all_solidarity_contributions_for_member(
                member_id=member_id, cache=cache
            )
            if contribution.amount > 0
        ]
        contracts += [
            membership
            for membership in TapirCache.get_member_association_memberships(
                cache=cache, member=payment.mandate_ref.member
            )
            if AssociationMembershipTypePriceGetter.get_price(
                membership_type=membership.type,
                reference_date=max(membership.start_date, range_start),
                cache=cache,
            )
            > 0
        ]

        contracts_in_range = [
            contract
            for contract in contracts
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=contract.start_date,
                range_1_end=contract.end_date,
                range_2_start=range_start,
                range_2_end=range_end,
            )
        ]
        if len(contracts_in_range) == 0:
            return False

        # Uncancelled contracts may still be renewed, automatically or by the member
        if any(contract.cancellation_ts is None for contract in contracts_in_range):
            return False

        return not any(
            contract.end_date is None or contract.end_date > range_end
            for contract in contracts
        )

    @classmethod
    def get_payment_type_display_legacy(cls, contract_payments: bool):
        return "Verträge" if contract_payments else PAYMENT_TYPE_COOP_SHARES
