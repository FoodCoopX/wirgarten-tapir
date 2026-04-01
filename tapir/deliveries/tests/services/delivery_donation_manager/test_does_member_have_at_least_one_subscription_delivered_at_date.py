from unittest.mock import Mock, patch, call

from django.test import SimpleTestCase

from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import SubscriptionFactory


class TestDoesMemberHaveAtLeastOneSubscriptionDeliveredAtDate(SimpleTestCase):
    def test_doesMemberHaveAtLeastOneSubscriptionDeliveredAtDate_noSubscription_returnsFalse(
        self,
    ):
        delivery_date = Mock()
        member_id = "test_member_id"

        cache = {"subscriptions_by_date": {delivery_date: []}}

        result = DeliveryDonationManager.does_member_have_at_least_one_subscription_delivered_at_date(
            member_id=member_id, delivery_date=delivery_date, cache=cache
        )

        self.assertFalse(result)

    @patch.object(
        SubscriptionDeliveredInWeekChecker,
        "is_subscription_delivered_in_week",
        autospec=True,
    )
    @patch.object(TapirCache, "get_subscriptions_active_at_date", autospec=True)
    def test_doesMemberHaveAtLeastOneSubscriptionDeliveredAtDate_noSubscriptionDelivered_returnsFalse(
        self,
        mock_get_subscriptions_active_at_date: Mock,
        mock_is_subscription_delivered_in_week: Mock,
    ):
        subscriptions = SubscriptionFactory.build_batch(size=3)
        mock_get_subscriptions_active_at_date.return_value = subscriptions

        subscription_1, subscription_2, subscription_3 = subscriptions
        subscription_1.member_id = "other_member_id"
        subscription_2.member_id = "other_member_id"
        member_id = "test_member_id"
        subscription_3.member_id = member_id

        delivery_date = Mock()
        cache = {}

        delivered_subscriptions = {subscription_1}
        mock_is_subscription_delivered_in_week.side_effect = (
            lambda **kwargs: kwargs["subscription"] in delivered_subscriptions
        )

        result = DeliveryDonationManager.does_member_have_at_least_one_subscription_delivered_at_date(
            member_id=member_id, delivery_date=delivery_date, cache=cache
        )

        self.assertFalse(result)
        mock_is_subscription_delivered_in_week.assert_called_once_with(
            subscription=subscription_3,
            delivery_date=delivery_date,
            cache=cache,
            skip_donation_check=False,
        )
        mock_get_subscriptions_active_at_date.assert_called_once_with(
            reference_date=delivery_date, cache=cache
        )

    @patch.object(
        SubscriptionDeliveredInWeekChecker,
        "is_subscription_delivered_in_week",
        autospec=True,
    )
    @patch.object(TapirCache, "get_subscriptions_active_at_date", autospec=True)
    def test_doesMemberHaveAtLeastOneSubscriptionDeliveredAtDate_oneSubscriptionDelivered_returnsTrue(
        self,
        mock_get_subscriptions_active_at_date: Mock,
        mock_is_subscription_delivered_in_week: Mock,
    ):
        subscriptions = SubscriptionFactory.build_batch(size=4)
        mock_get_subscriptions_active_at_date.return_value = subscriptions

        subscription_1, subscription_2, subscription_3, subscription_4 = subscriptions
        subscription_1.member_id = "other_member_id"
        subscription_2.member_id = "other_member_id"
        member_id = "test_member_id"
        subscription_3.member_id = member_id
        subscription_4.member_id = member_id

        delivery_date = Mock()
        cache = {}

        delivered_subscriptions = {subscription_1, subscription_4}
        mock_is_subscription_delivered_in_week.side_effect = (
            lambda **kwargs: kwargs["subscription"] in delivered_subscriptions
        )

        result = DeliveryDonationManager.does_member_have_at_least_one_subscription_delivered_at_date(
            member_id=member_id, delivery_date=delivery_date, cache=cache
        )

        self.assertTrue(result)
        self.assertEqual(2, mock_is_subscription_delivered_in_week.call_count)
        mock_is_subscription_delivered_in_week.assert_has_calls(
            [
                call(
                    subscription=subscription,
                    delivery_date=delivery_date,
                    cache=cache,
                    skip_donation_check=False,
                )
                for subscription in [subscription_3, subscription_4]
            ]
        )
        mock_get_subscriptions_active_at_date.assert_called_once_with(
            reference_date=delivery_date, cache=cache
        )
