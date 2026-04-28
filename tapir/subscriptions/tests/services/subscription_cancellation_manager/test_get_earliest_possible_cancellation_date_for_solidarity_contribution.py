import datetime
from unittest.mock import Mock, patch, call

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestGetEarliestPossibleCancellationDateForSolidarityContribution(TapirUnitTest):
    @patch.object(
        TrialPeriodManager, "get_earliest_trial_cancellation_date", autospec=True
    )
    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        SubscriptionCancellationManager,
        "get_solidarity_contributions_that_could_be_cancelled",
        autospec=True,
    )
    def test_getEarliestPossibleCancellationDateForSolidarityContribution_noneOfTheContributionIsOnTrial_returnsEndDateOfLatestContribution(
        self,
        mock_get_solidarity_contributions_that_could_be_cancelled: Mock,
        mock_is_contract_in_trial: Mock,
        mock_get_earliest_trial_cancellation_date: Mock,
    ):
        member = Mock()
        cache = Mock()

        today = mock_timezone(
            test=self, now=datetime.datetime(year=2002, month=9, day=1)
        ).date()

        contributions = SolidarityContributionFactory.build_batch(size=3)
        contributions[0].end_date = datetime.date(year=2002, month=9, day=13)
        contributions[1].end_date = datetime.date(year=2002, month=6, day=28)
        contributions[2].end_date = datetime.date(year=2003, month=1, day=1)
        mock_get_solidarity_contributions_that_could_be_cancelled.return_value = (
            contributions
        )

        mock_is_contract_in_trial.return_value = False

        result = SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_solidarity_contribution(
            member=member, cache=cache
        )

        self.assertEqual(datetime.date(year=2003, month=1, day=1), result)

        mock_get_solidarity_contributions_that_could_be_cancelled.assert_called_once_with(
            member=member, cache=cache
        )
        mock_get_earliest_trial_cancellation_date.assert_not_called()
        self.assertEqual(3, mock_is_contract_in_trial.call_count)
        mock_is_contract_in_trial.assert_has_calls(
            [
                call(contract=contribution, reference_date=today, cache=cache)
                for contribution in contributions
            ],
            any_order=True,
        )

    @patch.object(
        TrialPeriodManager, "get_earliest_trial_cancellation_date", autospec=True
    )
    @patch.object(TrialPeriodManager, "is_contract_in_trial", autospec=True)
    @patch.object(
        SubscriptionCancellationManager,
        "get_solidarity_contributions_that_could_be_cancelled",
        autospec=True,
    )
    def test_getEarliestPossibleCancellationDateForSolidarityContribution_someContributionsAreOnTrial_returnsEarliestTrialEndDate(
        self,
        mock_get_solidarity_contributions_that_could_be_cancelled: Mock,
        mock_is_contract_in_trial: Mock,
        mock_get_earliest_trial_cancellation_date: Mock,
    ):
        member = Mock()
        cache = Mock()

        today = mock_timezone(
            test=self, now=datetime.datetime(year=2002, month=9, day=1)
        ).date()

        contributions = SolidarityContributionFactory.build_batch(size=3)
        mock_get_solidarity_contributions_that_could_be_cancelled.return_value = (
            contributions
        )

        mock_is_contract_in_trial.side_effect = lambda contract, **kwargs: contract in [
            contributions[0],
            contributions[2],
        ]
        cancellation_dates = {
            contributions[0]: datetime.date(year=2025, month=1, day=17),
            contributions[1]: datetime.date(year=2025, month=1, day=5),
            contributions[2]: datetime.date(year=2025, month=1, day=13),
        }
        mock_get_earliest_trial_cancellation_date.side_effect = (
            lambda contract, **kwargs: cancellation_dates[contract]
        )

        result = SubscriptionCancellationManager.get_earliest_possible_cancellation_date_for_solidarity_contribution(
            member=member, cache=cache
        )

        self.assertEqual(datetime.date(year=2025, month=1, day=13), result)

        mock_get_solidarity_contributions_that_could_be_cancelled.assert_called_once_with(
            member=member, cache=cache
        )
        self.assertEqual(2, mock_get_earliest_trial_cancellation_date.call_count)
        mock_get_earliest_trial_cancellation_date.assert_has_calls(
            [
                call(contract=contribution, reference_date=today, cache=cache)
                for contribution in [contributions[0], contributions[2]]
            ],
            any_order=True,
        )
        self.assertEqual(3, mock_is_contract_in_trial.call_count)
        mock_is_contract_in_trial.assert_has_calls(
            [
                call(contract=contribution, reference_date=today, cache=cache)
                for contribution in contributions
            ],
            any_order=True,
        )
