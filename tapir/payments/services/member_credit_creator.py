import datetime
from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.payments.dataclasses import CreditCalculation
from tapir.utils.dataclasses import CalculationPart
from tapir.utils.services.calculation_explanation_builder import (
    CalculationExplanationBuilder,
)
from tapir.payments.models import MemberCredit, MemberCreditCreatedLogEntry
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.payments.services.month_payment_builder_solidarity_contributions import (
    MonthPaymentBuilderSolidarityContributions,
)
from tapir.payments.services.month_payment_builder_subscriptions import (
    MonthPaymentBuilderSubscriptions,
)
from tapir.payments.services.month_payment_builder_utils import MonthPaymentBuilderUtils
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import format_currency


class MemberCreditCreator:
    @classmethod
    def create_member_credit_if_necessary(
        cls,
        member: Member,
        product_type_id_or_soli: str,
        reference_date: datetime.date,
        comment: str,
        cache: dict,
        actor: TapirUser,
    ):
        credit_calculation = cls.get_credit_calculation(
            member=member,
            product_type_id_or_soli=product_type_id_or_soli,
            reference_date=reference_date,
            cache=cache,
        )
        if credit_calculation.amount == 0:
            return None

        return cls.create_credit_and_log_entry(
            member=member,
            actor=actor,
            amount_to_credit=credit_calculation.amount,
            reference_date=reference_date,
            comment=f"{comment}\n{credit_calculation.explanation}",
            product_type_id_or_soli=product_type_id_or_soli,
            cache=cache,
        )

    @classmethod
    def create_credit_and_log_entry(
        cls,
        member: Member,
        actor: TapirUser,
        amount_to_credit: Decimal,
        reference_date: datetime.date,
        comment: str,
        product_type_id_or_soli: str,
        cache: dict,
    ):
        source = product_type_id_or_soli
        if (
            source
            != MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
        ):
            source = TapirCache.get_product_type_by_id(
                cache=cache, product_type_id=source
            ).name

        member_credit = MemberCredit.objects.create(
            due_date=get_last_day_of_month(reference_date),
            member=member,
            amount=amount_to_credit,
            purpose=MemberCredit.PLACEHOLDER_PURPOSE,
            comment=comment,
            source=source,
        )

        MemberCreditCreatedLogEntry().populate(
            user=member, actor=actor, model=member_credit
        ).save()

        return member_credit

    @classmethod
    def save_credits_with_log_entries(
        cls, member_credits: list[MemberCredit], actor: TapirUser | None
    ) -> None:
        for member_credit in member_credits:
            member_credit.save()
            MemberCreditCreatedLogEntry().populate(
                user=member_credit.member, actor=actor, model=member_credit
            ).save()

    @classmethod
    def get_credit_calculation(
        cls,
        member: Member,
        product_type_id_or_soli: str,
        reference_date: datetime.date,
        cache: dict,
    ) -> CreditCalculation:
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
            return CreditCalculation(amount=Decimal("0.00"), explanation="")

        mandate_ref = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )

        if (
            product_type_id_or_soli
            == MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
        ):
            payment_type = (
                MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
            )
        else:
            payment_type = TapirCache.get_product_type_by_id(
                cache=cache, product_type_id=product_type_id_or_soli
            ).name

        already_paid = MonthPaymentBuilderUtils.get_already_paid_amount(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            mandate_ref=mandate_ref,
            payment_type=payment_type,
            cache=cache,
            generated_payments=set(),
        )

        if (
            product_type_id_or_soli
            == MonthPaymentBuilderSolidarityContributions.PAYMENT_TYPE_SOLIDARITY_CONTRIBUTION
        ):
            calculation_parts = cls.get_calculation_parts_solidarity_contributions(
                cache=cache,
                member_id=member.id,
                first_day_of_rhythm_period=first_day_of_rhythm_period,
                last_day_of_rhythm_period=last_day_of_rhythm_period,
            )
        else:
            calculation_parts = cls.get_calculation_parts_subscriptions(
                product_type_id=product_type_id_or_soli,
                cache=cache,
                member_id=member.id,
                first_day_of_rhythm_period=first_day_of_rhythm_period,
                last_day_of_rhythm_period=last_day_of_rhythm_period,
            )

        total_to_pay = sum((part.value for part in calculation_parts), Decimal(0))
        amount_to_credit = max(already_paid - total_to_pay, Decimal(0)).quantize(
            Decimal("0.01")
        )
        return CreditCalculation(
            amount=amount_to_credit,
            explanation=cls._build_explanation(
                calculation_parts=calculation_parts,
                total_to_pay=total_to_pay,
                already_paid=already_paid,
                amount_to_credit=amount_to_credit,
            ),
        )

    @classmethod
    def _build_explanation(
        cls,
        calculation_parts: list[CalculationPart],
        total_to_pay: Decimal,
        already_paid: Decimal,
        amount_to_credit: Decimal,
    ) -> str:
        lines = CalculationExplanationBuilder.build_credit_lines(
            calculation_parts=calculation_parts, total=total_to_pay
        )
        lines.append(f"Bereits bezahlt: {format_currency(already_paid)} €")
        lines.append(f"Gutschrift: {format_currency(amount_to_credit)} €")
        return "\n".join(lines)

    @classmethod
    def get_calculation_parts_solidarity_contributions(
        cls,
        cache: dict,
        member_id: str,
        first_day_of_rhythm_period: datetime.date,
        last_day_of_rhythm_period: datetime.date,
    ) -> list[CalculationPart]:
        contributions = TapirCache.get_all_solidarity_contributions_for_member(
            member_id=member_id, cache=cache
        )
        return MonthPaymentBuilderSolidarityContributions.get_calculation_parts(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            contracts=contributions,
            cache=cache,
        )

    @classmethod
    def get_calculation_parts_subscriptions(
        cls,
        product_type_id: str,
        cache: dict,
        member_id: str,
        first_day_of_rhythm_period: datetime.date,
        last_day_of_rhythm_period: datetime.date,
    ) -> list[CalculationPart]:
        product_type = TapirCache.get_product_type_by_id(
            cache=cache, product_type_id=product_type_id
        )
        subscriptions = [
            subscription
            for subscription in TapirCache.get_all_subscriptions_for_member(
                member_id=member_id, cache=cache
            )
            if subscription.product.type == product_type
        ]
        return MonthPaymentBuilderSubscriptions.get_calculation_parts(
            range_start=first_day_of_rhythm_period,
            range_end=last_day_of_rhythm_period,
            contracts=subscriptions,
            cache=cache,
        )
