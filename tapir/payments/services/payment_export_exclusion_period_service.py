import datetime

from django.db.models import Case, DateField, Exists, OuterRef, Q, Value, When
from django.db.models.functions import Greatest
from django.db.models.lookups import Exact

from tapir.configuration.parameter import get_parameter_value
from tapir.payments.config import (
    PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
    PAYMENT_TYPE_COOP_SHARES,
)
from tapir.payments.models import PaymentExportExclusionPeriod
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class PaymentExportExclusionPeriodService:
    @staticmethod
    def get_deposit_collection_date(cache: dict) -> datetime.date:
        today = get_today(cache=cache)
        scheduled_date = PaymentDueDateCalculator.get_first_due_date_on_or_after(
            earliest_date=today.replace(day=1), cache=cache
        )
        return max(today, scheduled_date)

    @classmethod
    def is_payment_excluded(cls, payment: Payment, cache: dict) -> bool:
        if payment.transaction_id is not None:
            return payment.excluded_from_export
        if not get_parameter_value(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, cache=cache
        ):
            return False
        if payment.type == PAYMENT_TYPE_COOP_SHARES:
            return False
        return cls.is_member_excluded(
            member_id=payment.mandate_ref.member_id,
            reference_date=(
                max(payment.due_date, cls.get_deposit_collection_date(cache=cache))
                if payment.type == PAYMENT_TYPE_ASSOCIATION_DEPOSIT
                else payment.due_date
            ),
            cache=cache,
        )

    @staticmethod
    def build_payment_is_excluded_condition(cache: dict) -> Q:
        """Database equivalent of is_payment_excluded."""
        exported_and_excluded = Q(transaction__isnull=False, excluded_from_export=True)
        if not get_parameter_value(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, cache=cache
        ):
            return exported_and_excluded

        reference_date = Case(
            When(
                Exact(OuterRef("type"), Value(PAYMENT_TYPE_ASSOCIATION_DEPOSIT)),
                then=Greatest(
                    OuterRef("due_date"),
                    Value(
                        PaymentExportExclusionPeriodService.get_deposit_collection_date(
                            cache=cache
                        )
                    ),
                ),
            ),
            default=OuterRef("due_date"),
            output_field=DateField(),
        )
        member_is_excluded = Exists(
            PaymentExportExclusionPeriod.objects.filter(
                Q(end_date__isnull=True) | Q(end_date__gte=reference_date),
                member_id=OuterRef("mandate_ref__member_id"),
                start_date__lte=reference_date,
            )
        )
        return exported_and_excluded | (
            Q(transaction__isnull=True)
            & ~Q(type=PAYMENT_TYPE_COOP_SHARES)
            & Q(member_is_excluded)
        )

    @classmethod
    def is_member_excluded(
        cls, member_id: str, reference_date: datetime.date, cache: dict
    ) -> bool:
        return any(
            cls.is_date_within_period(period=period, reference_date=reference_date)
            for period in TapirCache.get_payment_export_exclusion_periods_for_member(
                member_id=member_id, cache=cache
            )
        )

    @classmethod
    def get_current_or_next_period(
        cls, member_id: str, reference_date: datetime.date, cache: dict
    ) -> PaymentExportExclusionPeriod | None:
        return next(
            (
                period
                for period in TapirCache.get_payment_export_exclusion_periods_for_member(
                    member_id=member_id, cache=cache
                )
                if period.end_date is None or period.end_date >= reference_date
            ),
            None,
        )

    @staticmethod
    def is_date_within_period(
        period: PaymentExportExclusionPeriod, reference_date: datetime.date
    ) -> bool:
        if reference_date < period.start_date:
            return False
        return period.end_date is None or reference_date <= period.end_date
