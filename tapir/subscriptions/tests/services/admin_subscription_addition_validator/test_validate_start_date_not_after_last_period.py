import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.admin_subscription_addition_validator import (
    AdminSubscriptionAdditionValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    AdminSubscriptionAdditionValidator,
    "get_last_possible_start_date",
    autospec=True,
    return_value=datetime.date(year=2028, month=12, day=31),
)
class TestAdminSubscriptionAdditionValidatorValidateStartDateNotAfterLastPeriod(
    TapirUnitTest
):
    def test_validateStartDateNotAfterLastPeriod_startDateOnLastPossibleDate_doesNotRaise(
        self, _: MagicMock
    ):
        AdminSubscriptionAdditionValidator.validate_start_date_not_after_last_period(
            start_date=datetime.date(year=2028, month=12, day=31), cache={}
        )

    def test_validateStartDateNotAfterLastPeriod_startDateAfterLastPeriod_raisesValidationError(
        self, _: MagicMock
    ):
        with self.assertRaisesMessage(ValidationError, "bestehenden Vertragsperiode"):
            AdminSubscriptionAdditionValidator.validate_start_date_not_after_last_period(
                start_date=datetime.date(year=2029, month=1, day=1), cache={}
            )

    def test_validateStartDateNotAfterLastPeriod_noGrowingPeriod_raisesValidationError(
        self, mock_get_last_possible_start_date: MagicMock
    ):
        mock_get_last_possible_start_date.return_value = None

        with self.assertRaisesMessage(ValidationError, "bestehenden Vertragsperiode"):
            AdminSubscriptionAdditionValidator.validate_start_date_not_after_last_period(
                start_date=datetime.date(year=2027, month=6, day=7), cache={}
            )
