import datetime
from unittest.mock import patch, Mock, ANY

from tapir.payments.services.joker_credit_creator import JokerCreditCreator
from tapir.payments.tasks import create_credits_for_jokers
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


class TestCreateCreditsForJoker(TapirUnitTest):
    @patch.object(JokerCreditCreator, "create_credits_for_jokers", autospec=True)
    def test_createCreditsForJoker_noDateGiven_callsServiceWithTodaysDate(
        self, mock_create_credits_for_jokers: Mock
    ):
        now = mock_timezone(
            test=self, now=datetime.datetime(year=2024, month=3, day=15)
        )

        create_credits_for_jokers()

        mock_create_credits_for_jokers.assert_called_once_with(
            reference_date=now.date(), cache=ANY
        )

    @patch.object(JokerCreditCreator, "create_credits_for_jokers", autospec=True)
    def test_createCreditsForJoker_dateGiven_callsServiceWithGivenDate(
        self, mock_create_credits_for_jokers: Mock
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2024, month=3, day=15))

        create_credits_for_jokers(
            reference_date=datetime.date(year=2026, month=9, day=26)
        )

        mock_create_credits_for_jokers.assert_called_once_with(
            reference_date=datetime.date(year=2026, month=9, day=26), cache=ANY
        )
