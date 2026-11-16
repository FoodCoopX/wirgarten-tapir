import datetime

from tapir.payments.models import PaymentExportExclusionPeriod
from tapir.utils.services.tapir_cache import TapirCache


class PaymentExportExclusionPeriodService:
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
