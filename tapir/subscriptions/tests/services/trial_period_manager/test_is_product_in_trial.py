import datetime
from unittest.mock import patch, Mock, call

from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestIsProductInTrial(TapirIntegrationTest):
    def setUp(self):
        self.today = mock_timezone(
            self, datetime.datetime(year=2021, month=8, day=10)
        ).date()
        ParameterDefinitions().import_definitions()

    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    def test_isProductInTrial_atLeastOneSubscriptionInTrial_returnsTrue(
        self, mock_is_subscription_in_trial: Mock
    ):
        member = MemberFactory.create()
        product = ProductFactory.create()
        subscriptions = SubscriptionFactory.create_batch(
            size=3, member=member, product=product
        )
        SubscriptionFactory.create(member=member, product=ProductFactory.create())
        mock_is_subscription_in_trial.side_effect = [False, True, False]

        result = TrialPeriodManager.is_product_in_trial(product, member)

        self.assertTrue(result)
        self.assertEqual(2, mock_is_subscription_in_trial.call_count)
        mock_is_subscription_in_trial.assert_has_calls(
            [call(subscription, self.today) for subscription in subscriptions[:2]],
            any_order=True,
        )

    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    def test_isProductInTrial_noSubscriptionInTrial_returnsFalse(
        self, mock_is_subscription_in_trial: Mock
    ):
        member = MemberFactory.create()
        product = ProductFactory.create()
        subscriptions = SubscriptionFactory.create_batch(
            size=3, member=member, product=product
        )
        mock_is_subscription_in_trial.return_value = False

        result = TrialPeriodManager.is_product_in_trial(product, member)

        self.assertFalse(result)
        self.assertEqual(3, mock_is_subscription_in_trial.call_count)
        mock_is_subscription_in_trial.assert_has_calls(
            [call(subscription, self.today) for subscription in subscriptions],
            any_order=True,
        )
