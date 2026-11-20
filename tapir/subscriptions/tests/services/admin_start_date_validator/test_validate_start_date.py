import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_start_date_validator import (
    AdminStartDateValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    TapirCache,
    "get_growing_period_at_date",
    autospec=True,
    return_value=GrowingPeriodFactory.build(
        start_date=datetime.date(year=2027, month=1, day=1),
        end_date=datetime.date(year=2027, month=12, day=31),
    ),
)
class TestAdminStartDateValidatorValidateStartDate(TapirUnitTest):
    def setUp(self):
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2026, month=11, day=19))

    def test_validateStartDate_mondayInTheFuture_doesNotRaise(
        self, mock_get_growing_period_at_date: MagicMock
    ):
        AdminStartDateValidator.validate_start_date(
            start_date=datetime.date(year=2026, month=11, day=23), cache={}
        )

        mock_get_growing_period_at_date.assert_not_called()

    def test_validateStartDate_dateInThePast_raisesValidationError(self, _: MagicMock):
        with self.assertRaisesMessage(ValidationError, "nicht in der Vergangenheit"):
            AdminStartDateValidator.validate_start_date(
                start_date=datetime.date(year=2026, month=11, day=16), cache={}
            )

    def test_validateStartDate_growingPeriodStartThatIsNotAMonday_doesNotRaise(
        self, mock_get_growing_period_at_date: MagicMock
    ):
        change_date = datetime.date(year=2027, month=1, day=1)
        cache = {}

        AdminStartDateValidator.validate_start_date(start_date=change_date, cache=cache)

        mock_get_growing_period_at_date.assert_called_once_with(
            reference_date=change_date, cache=cache
        )

    def test_validateStartDate_neitherMondayNorGrowingPeriodStart_raisesValidationError(
        self, _: MagicMock
    ):
        with self.assertRaisesMessage(
            ValidationError, "Montag oder der Beginn einer Vertragsperiode"
        ):
            AdminStartDateValidator.validate_start_date(
                start_date=datetime.date(year=2027, month=1, day=6), cache={}
            )

    def test_validateStartDate_noGrowingPeriodAtDate_raisesValidationError(
        self, mock_get_growing_period_at_date: MagicMock
    ):
        mock_get_growing_period_at_date.return_value = None

        with self.assertRaisesMessage(
            ValidationError, "Montag oder der Beginn einer Vertragsperiode"
        ):
            AdminStartDateValidator.validate_start_date(
                start_date=datetime.date(year=2028, month=1, day=1), cache={}
            )
