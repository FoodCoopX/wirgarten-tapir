import datetime
from webbrowser import parse_args

from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.member_number_service import MemberNumberService
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.payments.config import IntendedUseTokens
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.types import TokenReplacers
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.wirgarten.models import Payment, Member, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import format_date, format_currency


class IntendedUsePatternExpander:
    MAX_LENGTH_PER_LINE = 27
    MIN_TOKEN_LENGTH = 5

    @classmethod
    def expand_pattern_contracts(
        cls,
        pattern: str,
        payment: Payment,
        cache: dict,
        token_value_overrides: dict[str, str] = None,
    ):
        if token_value_overrides is None:
            token_value_overrides = {}

        reference_date = payment.subscription_payment_range_end
        member = payment.mandate_ref.member

        subscriptions = Subscription.objects.filter(
            member_id=member.id,
            start_date__lte=payment.subscription_payment_range_end,
            end_date__gte=payment.subscription_payment_range_start,
        )

        monthly_price_without_solidarity = sum(
            subscription.total_price(reference_date=reference_date, cache=cache)
            for subscription in subscriptions
        )
        monthly_price_just_solidarity = (
            MemberSolidarityContributionService.get_member_contribution(
                member_id=member.id,
                reference_date=reference_date,
                cache=cache,
            )
        )

        replacements = cls.get_common_token_replacers(member=member, cache=cache) | {
            IntendedUseTokens.MONTHLY_PRICE_CONTRACTS_WITHOUT_SOLI: lambda: format_currency(
                monthly_price_without_solidarity
            ),
            IntendedUseTokens.MONTHLY_PRICE_CONTRACTS_WITH_SOLI: lambda: format_currency(
                monthly_price_without_solidarity + monthly_price_just_solidarity
            ),
            IntendedUseTokens.MONTHLY_PRICE_JUST_SOLI: lambda: format_currency(
                monthly_price_just_solidarity
            ),
            IntendedUseTokens.TOTAL_PRICE_CONTRACTS_WITHOUT_SOLI: lambda: format_currency(
                monthly_price_without_solidarity
                * cls.get_nb_months(
                    member=member, reference_date=reference_date, cache=cache
                )
            ),
            IntendedUseTokens.TOTAL_PRICE_CONTRACTS_WITH_SOLI: lambda: format_currency(
                (monthly_price_without_solidarity + monthly_price_just_solidarity)
                * cls.get_nb_months(
                    member=member, reference_date=reference_date, cache=cache
                )
            ),
            IntendedUseTokens.TOTAL_PRICE_JUST_SOLI: lambda: format_currency(
                monthly_price_just_solidarity
                * cls.get_nb_months(
                    member=member, reference_date=reference_date, cache=cache
                )
            ),
            IntendedUseTokens.CONTRACT_LIST: lambda: ", ".join(
                subscription.short_str() for subscription in subscriptions
            ),
            IntendedUseTokens.PAYMENT_RHYTHM: lambda: MemberPaymentRhythmService.get_rhythm_display_name(
                rhythm=MemberPaymentRhythmService.get_member_payment_rhythm(
                    member=member,
                    reference_date=reference_date,
                    cache=cache,
                )
            ),
        }

        return cls.apply_replacements(
            pattern, replacements, token_value_overrides=token_value_overrides
        )

    @classmethod
    def get_nb_months(cls, member: Member, reference_date: datetime.date, cache: dict):
        payment_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member,
            reference_date=reference_date,
            cache=cache,
        )
        return MemberPaymentRhythmService.get_number_of_months_paid_in_advance(
            rhythm=payment_rhythm
        )

    @classmethod
    def expand_pattern_coop_shares_bought(
        cls,
        pattern: str,
        member: Member,
        number_of_shares: int,
        cache: dict,
        token_value_overrides: dict = None,
    ):
        if token_value_overrides is None:
            token_value_overrides = {}

        replacements = cls.get_common_token_replacers(member=member, cache=cache) | {
            IntendedUseTokens.NUMBER_OF_COOP_SHARES: lambda: str(number_of_shares),
            IntendedUseTokens.COOP_ENTRY_DATE: lambda: format_date(
                MembershipCancellationManager.get_coop_entry_date(member)
            ),
            IntendedUseTokens.PRICE_SINGLE_SHARE: lambda: format_currency(
                get_parameter_value(key=ParameterKeys.COOP_SHARE_PRICE, cache=cache)
            ),
        }

        return cls.apply_replacements(pattern, replacements, token_value_overrides)

    @classmethod
    def get_common_token_replacers(cls, member: Member, cache: dict):
        return {
            IntendedUseTokens.SITE_NAME: lambda: get_parameter_value(
                key=ParameterKeys.SITE_NAME, cache=cache
            ),
            IntendedUseTokens.FIRST_NAME: lambda: member.first_name,
            IntendedUseTokens.LAST_NAME: lambda: member.last_name,
            IntendedUseTokens.MEMBER_NUMBER_SHORT: lambda: str(member.member_no),
            IntendedUseTokens.MEMBER_NUMBER_LONG: lambda: MemberNumberService.format_member_number(
                member_number=member.member_no, cache=cache
            )
            or "",
            IntendedUseTokens.MEMBER_NUMBER_WITHOUT_PREFIX: lambda: MemberNumberService.build_formatted_number(
                member_number=member.member_no,
                prefix="",
                length=get_parameter_value(
                    key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, cache=cache
                ),
            ),
        }

    @staticmethod
    def _get_token_with_braces(token: str):
        return f"{{{token}}}"

    @classmethod
    def apply_replacements(
        cls,
        pattern,
        replacements: TokenReplacers,
        token_value_overrides: dict[str, str],
    ):
        pattern_lines = pattern.strip().split("\n")
        expanded_lines = []
        for pattern_line in pattern_lines:
            expanded_lines.append(
                cls.apply_replacements_for_line(
                    line=pattern_line,
                    replacements=replacements,
                    token_value_overrides=token_value_overrides,
                )
            )

        return "\n".join(expanded_lines)

    @classmethod
    def apply_replacements_for_line(
        cls,
        line: str,
        replacements: TokenReplacers,
        token_value_overrides: dict[str, str],
    ):
        current_max_token_length = cls.MAX_LENGTH_PER_LINE
        result = cls.apply_replacements_for_line_with_max_length(
            line=line,
            replacements=replacements,
            max_length=current_max_token_length,
            token_value_overrides=token_value_overrides,
        )
        while len(result) > cls.MAX_LENGTH_PER_LINE:
            current_max_token_length -= 1
            if current_max_token_length < cls.MIN_TOKEN_LENGTH:
                raise ValidationError(
                    f"Diese Zeile: '{line}' ist zu lang wenn die Tokens expandiert sind."
                )

            result = cls.apply_replacements_for_line_with_max_length(
                line=line,
                replacements=replacements,
                max_length=current_max_token_length,
                token_value_overrides=token_value_overrides,
            )
        return result

    @classmethod
    def apply_replacements_for_line_with_max_length(
        cls,
        line: str,
        replacements: TokenReplacers,
        max_length: int,
        token_value_overrides: dict[str, str],
    ):
        result = line
        for token, provider in replacements.items():
            token_with_braces = cls._get_token_with_braces(token)
            if token_with_braces not in result:
                continue

            if token in token_value_overrides:
                value = token_value_overrides[token]
            else:
                value = provider()

            result = result.replace(token_with_braces, value[:max_length])
        return result
