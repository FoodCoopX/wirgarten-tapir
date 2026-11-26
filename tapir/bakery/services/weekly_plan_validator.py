from django.core.exceptions import ValidationError

from tapir.bakery.models import AvailableBreadsForDeliveryDay
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)


class WeeklyPlanValidator:
    """Checks a change of the weekly bread plan before WeeklyPlanService applies it."""

    DELIVERY_DAY_IS_OVER = "Dieser Liefertag ist schon vorbei."
    SOURCE_NOT_BEFORE_TARGET = "Die Vorlage muss eine frühere Woche sein."
    SOURCE_WITHOUT_BREADS = "In der Vorlage wird kein aktives Brot gebacken."

    @classmethod
    def validate_set_bread_baked(
        cls, year: int, delivery_week: int, delivery_day: int, cache: dict
    ) -> None:
        if BreadChoiceDeadlineService.is_delivery_day_over(
            year, delivery_week, delivery_day, cache=cache
        ):
            raise ValidationError(cls.DELIVERY_DAY_IS_OVER)

    @classmethod
    def validate_copy_week(
        cls, source_year: int, source_week: int, target_year: int, target_week: int
    ) -> None:
        if (source_year, source_week) >= (target_year, target_week):
            raise ValidationError(cls.SOURCE_NOT_BEFORE_TARGET)
        # Copying a week without breads would empty the target week.
        if not AvailableBreadsForDeliveryDay.objects.filter(
            year=source_year, delivery_week=source_week, bread__is_active=True
        ).exists():
            raise ValidationError(cls.SOURCE_WITHOUT_BREADS)
