import datetime

from tapir.wirgarten.service.pickup_location_date_validation import (
    PickupLocationDateValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestPickupLocationDateValidator(TapirUnitTest):
    def test_validate_startDateNotOnMonday_returnsStartDateError(self):
        errors = PickupLocationDateValidator.validate(datetime.date(2026, 1, 6), None)

        self.assertEqual(
            {
                "start_date": (
                    "Verteilstationen können nur an einem Montag geöffnet werden."
                )
            },
            errors,
        )

    def test_validate_startDateNoneOrOnMonday_returnsNoError(self):
        for start_date in [None, datetime.date(2026, 1, 5)]:
            errors = PickupLocationDateValidator.validate(start_date, None)
            self.assertEqual({}, errors)

    def test_validate_endDateNotOnSunday_returnsEndDateError(self):
        errors = PickupLocationDateValidator.validate(None, datetime.date(2026, 12, 26))

        self.assertEqual(
            {
                "end_date": (
                    "Verteilstationen können nur an einem Sonntag geschlossen werden."
                )
            },
            errors,
        )

    def test_validate_endDateNoneOrOnSunday_returnsNoError(self):
        for end_date in [None, datetime.date(2026, 12, 27)]:
            errors = PickupLocationDateValidator.validate(None, end_date)
            self.assertEqual({}, errors)
