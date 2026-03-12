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
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        self.now = mock_timezone(self, datetime.datetime(year=2022, month=6, day=9))

    @patch.object(TrialPeriodManager, "is_contract_in_trial")
    @patch.object(
        SubscriptionCancellationManager,
        "get_earliest_possible_cancellation_date_for_product",
    )
    def test_cancelSubscriptions_default_cancelsSubscription(
        self,
        mock_get_earliest_possible_cancellation_date_for_product: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        subscriptions = SubscriptionFactory.create_batch(
            member=member, period=growing_period, product=product, size=3
        )
        mock_is_contract_in_trial.return_value = False

        cancellation_date = datetime.date(year=2022, month=11, day=17)
        mock_get_earliest_possible_cancellation_date_for_product.return_value = (
            cancellation_date
        )

        SubscriptionCancellationManager.cancel_subscriptions(product, member, cache={})

        for subscription in subscriptions:
            subscription.refresh_from_db()
            self.assertEqual(cancellation_date, subscription.end_date)
            self.assertEqual(self.now, subscription.cancellation_ts)

    @patch.object(TrialPeriodManager, "is_contract_in_trial")
    @patch.object(
        SubscriptionCancellationManager,
        "get_earliest_possible_cancellation_date_for_product",
    )
    def test_cancelSubscriptions_cancellationDateIsBeforeStartDate_deletesFutureSubscriptions(
        self,
        mock_get_earliest_possible_cancellation_date_for_product: Mock,
        mock_is_contract_in_trial: Mock,
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
        mock_is_contract_in_trial.return_value = False

        cancellation_date = datetime.date(year=2022, month=12, day=31)
        mock_get_earliest_possible_cancellation_date_for_product.return_value = (
            cancellation_date
        )

        SubscriptionCancellationManager.cancel_subscriptions(product, member, cache={})

        self.assertEqual(1, Subscription.objects.count())
        self.assertIn(active_subscription, Subscription.objects.all())

    @patch.object(TrialPeriodManager, "is_contract_in_trial")
    def test_cancelSubscriptions_subscriptionIsInNotTrialButAutoRenewIsOff_raisesException(
        self,
        mock_is_contract_in_trial: Mock,
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
        mock_is_contract_in_trial.return_value = False

        with self.assertRaises(ImproperlyConfigured):
            SubscriptionCancellationManager.cancel_subscriptions(
                product, member, cache={}
            )

        active_subscription.refresh_from_db()
        self.assertIsNone(active_subscription.cancellation_ts)

    @patch.object(TrialPeriodManager, "is_contract_in_trial")
    @patch.object(
        SubscriptionCancellationManager,
        "get_earliest_possible_cancellation_date_for_product",
    )
    def test_cancelSubscriptions_subscriptionIsInTrialAndAutoRenewIsOn_subscriptionCancelled(
        self,
        mock_get_earliest_possible_cancellation_date_for_product: Mock,
        mock_is_contract_in_trial: Mock,
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
        mock_is_contract_in_trial.return_value = True

        cancellation_date = datetime.date(year=2022, month=11, day=17)
        mock_get_earliest_possible_cancellation_date_for_product.return_value = (
            cancellation_date
        )

        SubscriptionCancellationManager.cancel_subscriptions(product, member, cache={})

        subscription.refresh_from_db()
        self.assertEqual(cancellation_date, subscription.end_date)
        self.assertEqual(self.now, subscription.cancellation_ts)

    @patch.object(TrialPeriodManager, "is_contract_in_trial")
    @patch.object(
        SubscriptionCancellationManager,
        "get_earliest_possible_cancellation_date_for_product",
    )
    def test_cancelSubscriptions_cancelDateIsSameAsStartDate_deletesSubscription(
        self,
        mock_get_earliest_possible_cancellation_date_for_product: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        product = ProductFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=growing_period,
            product=product,
            start_date=datetime.date(year=2022, month=6, day=1),
        )
        mock_is_contract_in_trial.return_value = True

        cancellation_date = datetime.date(year=2022, month=6, day=1)
        mock_get_earliest_possible_cancellation_date_for_product.return_value = (
            cancellation_date
        )

        SubscriptionCancellationManager.cancel_subscriptions(product, member, cache={})

        self.assertFalse(Subscription.objects.exists())

    @patch.object(TrialPeriodManager, "is_contract_in_trial")
    @patch.object(
        SubscriptionCancellationManager,
        "get_earliest_possible_cancellation_date_for_product",
    )
    def test_cancelSubscriptions_subscriptionIsRenewed_cancelsCurrentAndFutureSubscription(
        self,
        mock_get_earliest_possible_cancellation_date_for_product: Mock,
        mock_is_contract_in_trial: Mock,
    ):
        member = MemberFactory.create()
        current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2023, month=1, day=1),
            end_date=datetime.datetime(year=2023, month=12, day=31),
        )
        product = ProductFactory.create()
        current_subscription = SubscriptionFactory.create(
            member=member, period=current_growing_period, product=product
        )
        renewed_subscription = SubscriptionFactory.create(
            member=member, period=future_growing_period, product=product
        )
        mock_is_contract_in_trial.return_value = False

        cancellation_date = datetime.date(year=2023, month=8, day=19)
        mock_get_earliest_possible_cancellation_date_for_product.return_value = (
            cancellation_date
        )

        SubscriptionCancellationManager.cancel_subscriptions(product, member, cache={})

        current_subscription.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2022, month=12, day=31),
            current_subscription.end_date,
            "The cancellation date is after this subscription's end date therefore the end date should not change",
        )
        self.assertEqual(self.now, current_subscription.cancellation_ts)

        renewed_subscription.refresh_from_db()
        self.assertEqual(cancellation_date, renewed_subscription.end_date)
        self.assertEqual(self.now, renewed_subscription.cancellation_ts)
