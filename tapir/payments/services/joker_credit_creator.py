import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.deliveries.services.member_specific_delivery_day_calculator import (
    MemberSpecificDeliveryDayCalculator,
)
from tapir.payments.models import MemberCredit
from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.utils.shortcuts import get_last_day_of_month, get_monday
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.utils import format_date


class JokerCreditCreator:
    @classmethod
    def create_credits_for_jokers(cls, reference_date: datetime.date, cache: dict):
        member_credits = [
            cls._build_credit_for_joker(
                joker=joker, reference_date=reference_date, cache=cache
            )
            for joker in Joker.objects.filter(membercredit__isnull=True)
            if not JokerManagementService.can_joker_be_cancelled(
                joker=joker, reference_date=reference_date, cache=cache
            )
        ]
        MemberCredit.objects.bulk_create(member_credits)

    @classmethod
    def _build_credit_for_joker(
        cls, joker: Joker, reference_date: datetime.date, cache: dict
    ):
        delivery_date = MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id=joker.member.id,
            delivery_date=get_next_delivery_date(get_monday(joker.date), cache=cache),
            cache=cache,
        )
        amount = JokerValueService.get_joker_credit_value_for_single_joker(
            member=joker.member, joker_date=joker.date, cache=cache
        )
        purpose = IntendedUsePatternExpander.expand_pattern_joker(
            pattern=get_parameter_value(
                key=ParameterKeys.PAYMENT_INTENDED_USE_JOKER_CREDIT, cache=cache
            ),
            member=joker.member,
            reference_date=reference_date,
            cache=cache,
        )

        return MemberCredit(
            member=joker.member,
            joker=joker,
            amount=amount,
            due_date=get_last_day_of_month(reference_date),
            purpose=purpose,
            comment=f"Joker am {format_date(delivery_date)}",
            source="Joker",
        )
