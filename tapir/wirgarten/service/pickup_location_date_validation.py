import datetime

PICKUP_LOCATION_START_DATE_VALIDATION_MESSAGE = (
    "Verteilstationen können nur an einem Montag geöffnet werden."
)
PICKUP_LOCATION_END_DATE_VALIDATION_MESSAGE = (
    "Verteilstationen können nur an einem Sonntag geschlossen werden."
)


class PickupLocationDateValidator:
    @staticmethod
    def validate(
        start_date: datetime.date | None, end_date: datetime.date | None
    ) -> dict[str, str]:
        errors = {}
        if start_date is not None and start_date.weekday() != 0:
            errors["start_date"] = PICKUP_LOCATION_START_DATE_VALIDATION_MESSAGE
        if end_date is not None and end_date.weekday() != 6:
            errors["end_date"] = PICKUP_LOCATION_END_DATE_VALIDATION_MESSAGE
        return errors
