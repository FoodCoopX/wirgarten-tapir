import datetime
from unittest.mock import patch, Mock

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCancelSubscriptions(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        self.now = mock_timezone(self, datetime.datetime(year=2022, month=6, day=9))

    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    @patch.object(
        SubscriptionCancellationManager, "get_earliest_possible_cancellation_date"
    )
    def test_cancelSubscriptions_default_cancelsSubscription(
        self,
        mock_get_earliest_possible_cancellation_date: Mock,
        mock_is_subscription_in_trial: Mock,
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
        mock_is_subscription_in_trial.return_value = False

        cancellation_date = datetime.date(year=2024, month=11, day=17)
        mock_get_earliest_possible_cancellation_date.return_value = cancellation_date

        SubscriptionCancellationManager.cancel_subscriptions(product, member)

        for subscription in subscriptions:
            subscription.refresh_from_db()
            self.assertEqual(cancellation_date, subscription.end_date)
            self.assertEqual(self.now, subscription.cancellation_ts)

    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    @patch.object(
        SubscriptionCancellationManager, "get_earliest_possible_cancellation_date"
    )
    def test_cancelSubscriptions_default_deletesFutureSubscriptions(
        self,
        mock_get_earliest_possible_cancellation_date: Mock,
        mock_is_subscription_in_trial: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        active_subscription = SubscriptionFactory.create(
            member=member, period=growing_period, product=product
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            start_date=datetime.datetime(year=2023, month=1, day=1),
            end_date=datetime.datetime(year=2023, month=12, day=31),
        )
        mock_is_subscription_in_trial.return_value = False

        cancellation_date = datetime.date(year=2022, month=12, day=31)
        mock_get_earliest_possible_cancellation_date.return_value = cancellation_date

        SubscriptionCancellationManager.cancel_subscriptions(product, member)

        self.assertEqual(1, Subscription.objects.count())
        self.assertIn(active_subscription, Subscription.objects.all())

    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    def test_cancelSubscriptions_subscriptionIsInNotTrialButAutoRenewIsOff_raisesException(
        self,
        mock_is_subscription_in_trial: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        active_subscription = SubscriptionFactory.create(
            member=member, period=growing_period, product=product
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=False)
        mock_is_subscription_in_trial.return_value = False

        with self.assertRaises(ImproperlyConfigured):
            SubscriptionCancellationManager.cancel_subscriptions(product, member)

        active_subscription.refresh_from_db()
        self.assertIsNone(active_subscription.cancellation_ts)

    @patch.object(TrialPeriodManager, "is_subscription_in_trial")
    @patch.object(
        SubscriptionCancellationManager, "get_earliest_possible_cancellation_date"
    )
    def test_cancelSubscriptions_subscriptionIsInTrialAndAutoRenewIsOn_subscriptionCancelled(
        self,
        mock_get_earliest_possible_cancellation_date: Mock,
        mock_is_subscription_in_trial: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        subscription = SubscriptionFactory.create(
            member=member, period=growing_period, product=product
        )
        mock_is_subscription_in_trial.return_value = True

        cancellation_date = datetime.date(year=2024, month=11, day=17)
        mock_get_earliest_possible_cancellation_date.return_value = cancellation_date

        SubscriptionCancellationManager.cancel_subscriptions(product, member)

        subscription.refresh_from_db()
        self.assertEqual(cancellation_date, subscription.end_date)
        self.assertEqual(self.now, subscription.cancellation_ts)
