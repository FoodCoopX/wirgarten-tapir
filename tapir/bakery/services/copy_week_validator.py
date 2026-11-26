from django.core.exceptions import ValidationError


class CopyWeekValidator:
    SOURCE_NOT_BEFORE_TARGET = "Die Vorlage muss eine frühere Woche sein."

    @classmethod
    def validate(
        cls, source_year: int, source_week: int, target_year: int, target_week: int
    ) -> None:
        if (source_year, source_week) >= (target_year, target_week):
            raise ValidationError(cls.SOURCE_NOT_BEFORE_TARGET)
