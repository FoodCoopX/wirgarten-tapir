import datetime

from django.core.exceptions import ValidationError

from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_last_day_of_month
from tapir.wirgarten.utils import format_date


class PaymentExportExclusionPeriodValidator:
    @classmethod
    def validate(
        cls,
        member_id: str,
        start_date: datetime.date,
        end_date: datetime.date | None,
        period_id_being_edited: str | None,
        cache: dict,
    ) -> None:
        if start_date.day != 1:
            raise ValidationError(
                "Das Start-Datum muss der erste Tag eines Monats sein"
            )

        if end_date is not None and end_date != get_last_day_of_month(end_date):
            raise ValidationError("Das End-Datum muss der letzte Tag eines Monats sein")

        if end_date is not None and end_date < start_date:
            raise ValidationError("Das End-Datum darf nicht vor dem Start-Datum liegen")

        for other_period in TapirCache.get_payment_export_exclusion_periods_for_member(
            member_id=member_id, cache=cache
        ):
            if other_period.id == period_id_being_edited:
                continue
            if DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=start_date,
                range_1_end=end_date,
                range_2_start=other_period.start_date,
                range_2_end=other_period.end_date,
            ):
                raise ValidationError(
                    "Der Zeitraum überschneidet sich mit dem bestehenden Zeitraum "
                    f"{format_date(other_period.start_date)} - "
                    f"{format_date(other_period.end_date) or 'unbefristet'}"
                )
