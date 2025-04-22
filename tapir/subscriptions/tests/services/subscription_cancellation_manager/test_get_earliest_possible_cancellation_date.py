import datetime
from unittest.mock import patch, Mock, call

from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetEarliestPossibleCancellationDate(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        mock_timezone(self, datetime.datetime(year=2022, month=6, day=9))

    @patch.object(TrialPeriodManager, "get_earliest_trial_cancellation_date")
    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    def test_getEarliestPossibleCancellationDate_atLeastOneSubscriptionInTrial_returnsTrialCancellationDate(
        self,
        mock_is_subscription_in_trial: Mock,
        mock_get_earliest_trial_cancellation_date: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        subscriptions = [
            SubscriptionFactory.create(
                member=member, period=growing_period, product=product
            )
            for _ in range(3)
        ]
        mock_is_subscription_in_trial.side_effect = [False, True, False]
        trial_cancellation_date = Mock()
        mock_get_earliest_trial_cancellation_date.return_value = trial_cancellation_date
        cache = {}
        result = (
            SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                product, member, cache=cache
            )
        )

        self.assertEqual(trial_cancellation_date, result)
        self.assertEqual(2, mock_is_subscription_in_trial.call_count)
        mock_is_subscription_in_trial.assert_has_calls(
            [call(subscription) for subscription in subscriptions[:2]], any_order=True
        )
        mock_get_earliest_trial_cancellation_date.assert_called_once_with(cache=cache)

    @patch.object(TrialPeriodManager, "get_earliest_trial_cancellation_date")
    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    def test_getEarliestPossibleCancellationDate_noSubscriptionInTrial_returnsBiggestSubscriptionEndDate(
        self,
        mock_is_subscription_in_trial: Mock,
        mock_get_earliest_trial_cancellation_date: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        subscriptions = [
            SubscriptionFactory.create(
                member=member,
                period=growing_period,
                product=product,
                end_date=datetime.date(year=2022, month=12, day=end_day),
            )
            for end_day in [30, 10, 20]
        ]
        mock_is_subscription_in_trial.return_value = False

        result = (
            SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                product, member, cache={}
            )
        )

        self.assertEqual(datetime.date(year=2022, month=12, day=30), result)
        self.assertEqual(3, mock_is_subscription_in_trial.call_count)
        mock_is_subscription_in_trial.assert_has_calls(
            [call(subscription) for subscription in subscriptions], any_order=True
        )
        mock_get_earliest_trial_cancellation_date.assert_not_called()
