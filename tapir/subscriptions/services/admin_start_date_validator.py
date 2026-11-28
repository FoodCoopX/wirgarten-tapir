import datetime

from django.core.exceptions import ValidationError

from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.utils import get_today


class AdminStartDateValidator:
    @classmethod
    def validate_start_date(cls, start_date: datetime.date, cache: dict):
        if start_date < get_today(cache=cache):
            raise ValidationError("Das Datum darf nicht in der Vergangenheit liegen.")

        if start_date.weekday() == 0:
            return

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=start_date, cache=cache
        )
        if growing_period is None or growing_period.start_date != start_date:
            raise ValidationError(
                "Das Datum muss ein Montag oder der Beginn einer Vertragsperiode sein."
            )
