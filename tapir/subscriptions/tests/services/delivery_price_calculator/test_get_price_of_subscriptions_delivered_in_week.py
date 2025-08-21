from unittest.mock import Mock, patch, call

from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetPriceOfSubscriptionsDeliveredInWeek(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(
        DeliveryPriceCalculator, "get_price_of_single_delivery_without_solidarity"
    )
    @patch.object(
        DeliveryPriceCalculator, "get_subscriptions_that_get_delivered_in_week"
    )
    def test_getPriceOfSubscriptionsDeliveredInWeek_default_returnsSumOfPriceTimesQuantity(
        self,
        mock_get_subscriptions_that_get_delivered_in_week: Mock,
        mock_get_price_of_single_delivery_without_solidarity: Mock,
    ):
        subscriptions = [Mock(), Mock()]
        subscriptions[0].quantity = 2
        subscriptions[1].quantity = 4
        mock_get_subscriptions_that_get_delivered_in_week.return_value = subscriptions
        mock_get_price_of_single_delivery_without_solidarity.side_effect = [15, 26]
        member = Mock()
        reference_date = Mock()
        cache = {}

        result = DeliveryPriceCalculator.get_price_of_subscriptions_delivered_in_week(
            member=member,
            reference_date=reference_date,
            only_subscriptions_affected_by_jokers=False,
            cache={},
        )

        self.assertEqual(2 * 15 + 4 * 26, result)

        mock_get_subscriptions_that_get_delivered_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        self.assertEqual(
            2, mock_get_price_of_single_delivery_without_solidarity.call_count
        )
        mock_get_price_of_single_delivery_without_solidarity.assert_has_calls(
            [
                call(subscription, reference_date, cache=cache)
                for subscription in subscriptions
            ],
            any_order=True,
        )

    @patch.object(
        DeliveryPriceCalculator, "get_price_of_single_delivery_without_solidarity"
    )
    @patch.object(
        DeliveryPriceCalculator, "get_subscriptions_that_get_delivered_in_week"
    )
    def test_getPriceOfSubscriptionsDeliveredInWeek_onlySubscriptionsAffectedByJokers_returnsSumOnlyForSubscriptionsAffectedByJokers(
        self,
        mock_get_subscriptions_that_get_delivered_in_week: Mock,
        mock_get_price_of_single_delivery_without_solidarity: Mock,
    ):
        SubscriptionFactory.create(
            product__type__is_affected_by_jokers=False, quantity=2
        )
        subscription_2 = SubscriptionFactory.create(
            product__type__is_affected_by_jokers=True, quantity=4
        )

        mock_get_subscriptions_that_get_delivered_in_week.return_value = (
            Subscription.objects.all()
        )
        mock_get_price_of_single_delivery_without_solidarity.return_value = 26
        member = Mock()
        reference_date = Mock()
        cache = {}

        result = DeliveryPriceCalculator.get_price_of_subscriptions_delivered_in_week(
            member=member,
            reference_date=reference_date,
            only_subscriptions_affected_by_jokers=True,
            cache=cache,
        )

        self.assertEqual(4 * 26, result)

        mock_get_subscriptions_that_get_delivered_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_get_price_of_single_delivery_without_solidarity.assert_called_once_with(
            subscription_2, reference_date, cache=cache
        )
