import datetime
from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.models import MemberCredit, MemberCreditCreatedLogEntry
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import Member, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import get_or_create_mandate_ref


class MemberCreditCreator:
    @classmethod
    def create_member_credit_if_necessary(
        cls,
        member: Member,
        product_type: ProductType,
        reference_date: datetime.date,
        comment: str,
        cache: dict,
        actor: TapirUser,
    ):
        amount_to_credit = cls.get_amount_to_credit(
            member=member,
            product_type=product_type,
            reference_date=reference_date,
            cache=cache,
        )
        if amount_to_credit == 0:
            return

        cls.create_credit_and_log_entry(
            member=member,
            actor=actor,
            amount_to_credit=amount_to_credit,
            reference_date=reference_date,
            comment=comment,
        )

    @classmethod
    def create_credit_and_log_entry(
        cls,
        member: Member,
        actor: TapirUser,
        amount_to_credit: Decimal,
        reference_date: datetime.date,
        comment: str,
    ):
        member_credit = MemberCredit.objects.create(
            due_date=get_last_day_of_month(reference_date),
            member=member,
            amount=amount_to_credit,
            purpose="TODO, warten auf US 2.2 und 2.6",
            comment=comment,
        )

        MemberCreditCreatedLogEntry().populate(
            user=member, actor=actor, model=member_credit
        ).save()

    @classmethod
    def get_amount_to_credit(
        cls,
        member: Member,
        product_type: ProductType,
        reference_date: datetime.date,
        cache: dict,
    ):
        member_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
            member=member, reference_date=reference_date, cache=cache
        )
        first_of_month = reference_date.replace(day=1)
        first_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_first_day_of_rhythm_period(
                rhythm=member_rhythm, reference_date=first_of_month, cache=cache
            )
        )
        last_day_of_rhythm_period = (
            MemberPaymentRhythmService.get_last_day_of_rhythm_period(
                rhythm=member_rhythm, reference_date=first_of_month, cache=cache
            )
        )

        payment_start_date = get_parameter_value(
            key=ParameterKeys.PAYMENT_START_DATE, cache=cache
        )
        first_day_of_rhythm_period = max(payment_start_date, first_day_of_rhythm_period)
        if first_day_of_rhythm_period > last_day_of_rhythm_period:
            return None

        mandate_ref = get_or_create_mandate_ref(member=member, cache=cache)

        already_paid = MonthPaymentBuilderUtils.get_already_paid_amount(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            payment_type=product_type.name,
            cache=cache,
            generated_payments=set(),
        )

        subscriptions = TapirCache.get_subscriptions_by_product_type(cache=cache).get(
            product_type, set()
        )
        subscriptions = [
            subscription
            for subscription in subscriptions
            if subscription.member_id == member.id
        ]
        total_to_pay = MonthPaymentBuilderSubscriptions.get_total_to_pay(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            contracts=subscriptions,
            cache=cache,
        )

        amount_to_credit = already_paid - total_to_pay
        return max(amount_to_credit, Decimal(0))
