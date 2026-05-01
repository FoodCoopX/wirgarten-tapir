from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
    DELIVERY_DONATION_MODE_DISABLED,
)
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.subscriptions.services.subscription_delivered_in_week_checked import (
    SubscriptionDeliveredInWeekChecker,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestSubscriptionDeliveredInWeekChecker(TapirUnitTest):
    @patch.object(DeliveryDateCalculator, "is_week_delivered", autospec=True)
    def test_isSubscriptionDeliveredInWeek_weekIsNotCoveredByCycle_returnsFalse(
        self, mock_is_week_delivered: Mock
    ):
        mock_is_week_delivered.return_value = False

        subscription = Mock()
        delivery_date = Mock()
        cache = Mock()

        result = SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
            subscription=subscription,
            delivery_date=delivery_date,
            cache=cache,
            skip_donation_check=False,
        )

        self.assertFalse(result)
        mock_is_week_delivered.assert_called_once_with(
            product_type=subscription.product.type,
            delivery_date=delivery_date,
            check_for_weeks_without_delivery=True,
            cache=cache,
        )

    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(DeliveryDateCalculator, "is_week_delivered", autospec=True)
    def test_isSubscriptionDeliveredInWeek_memberHasJokerOnWeek_returnsFalse(
        self, mock_is_week_delivered: Mock, mock_does_member_have_a_joker_in_week: Mock
    ):
        mock_is_week_delivered.return_value = True
        mock_does_member_have_a_joker_in_week.return_value = True

        subscription = Mock()
        delivery_date = Mock()
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.JOKERS_ENABLED, value=True)

        result = SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
            subscription=subscription,
            delivery_date=delivery_date,
            cache=cache,
            skip_donation_check=False,
        )

        self.assertFalse(result)

        mock_is_week_delivered.assert_called_once_with(
            product_type=subscription.product.type,
            delivery_date=delivery_date,
            check_for_weeks_without_delivery=True,
            cache=cache,
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member=subscription.member, reference_date=delivery_date, cache=cache
        )

    @patch.object(
        DeliveryDonationManager, "does_member_have_a_donation_in_week", autospec=True
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(DeliveryDateCalculator, "is_week_delivered", autospec=True)
    def test_isSubscriptionDeliveredInWeek_memberHasDonationOnWeek_returnsFalse(
        self,
        mock_is_week_delivered: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        mock_is_week_delivered.return_value = True
        mock_does_member_have_a_donation_in_week.return_value = True

        subscription = Mock()
        delivery_date = Mock()
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.JOKERS_ENABLED, value=False)
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        result = SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
            subscription=subscription,
            delivery_date=delivery_date,
            cache=cache,
            skip_donation_check=False,
        )

        self.assertFalse(result)

        mock_is_week_delivered.assert_called_once_with(
            product_type=subscription.product.type,
            delivery_date=delivery_date,
            check_for_weeks_without_delivery=True,
            cache=cache,
        )
        mock_does_member_have_a_joker_in_week.assert_not_called()
        mock_does_member_have_a_donation_in_week.assert_called_once_with(
            member=subscription.member, reference_date=delivery_date, cache=cache
        )

    @patch.object(
        DeliveryDonationManager, "does_member_have_a_donation_in_week", autospec=True
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(DeliveryDateCalculator, "is_week_delivered", autospec=True)
    def test_isSubscriptionDeliveredInWeek_subscriptionIsDelivered_returnsTrue(
        self,
        mock_is_week_delivered: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        mock_is_week_delivered.return_value = True

        subscription = Mock()
        delivery_date = Mock()
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.JOKERS_ENABLED, value=False)
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_DISABLED,
        )

        result = SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
            subscription=subscription,
            delivery_date=delivery_date,
            cache=cache,
            skip_donation_check=False,
        )

        self.assertTrue(result)

        mock_is_week_delivered.assert_called_once_with(
            product_type=subscription.product.type,
            delivery_date=delivery_date,
            check_for_weeks_without_delivery=True,
            cache=cache,
        )
        mock_does_member_have_a_joker_in_week.assert_not_called()
        mock_does_member_have_a_donation_in_week.assert_not_called()

    @patch.object(
        DeliveryDonationManager, "does_member_have_a_donation_in_week", autospec=True
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(DeliveryDateCalculator, "is_week_delivered", autospec=True)
    def test_isSubscriptionDeliveredInWeek_memberHasDonationOnWeekButDonationCheckIsSkipped_returnsTrue(
        self,
        mock_is_week_delivered: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        mock_is_week_delivered.return_value = True
        mock_does_member_have_a_donation_in_week.return_value = True

        subscription = Mock()
        delivery_date = Mock()
        cache = {}
        mock_parameter_value(cache=cache, key=ParameterKeys.JOKERS_ENABLED, value=False)
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        result = SubscriptionDeliveredInWeekChecker.is_subscription_delivered_in_week(
            subscription=subscription,
            delivery_date=delivery_date,
            cache=cache,
            skip_donation_check=True,
        )

        self.assertTrue(result)

        mock_is_week_delivered.assert_called_once_with(
            product_type=subscription.product.type,
            delivery_date=delivery_date,
            check_for_weeks_without_delivery=True,
            cache=cache,
        )
        mock_does_member_have_a_joker_in_week.assert_not_called()
        mock_does_member_have_a_donation_in_week.assert_not_called()
