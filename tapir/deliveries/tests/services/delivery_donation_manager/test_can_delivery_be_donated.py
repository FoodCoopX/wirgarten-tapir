from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.deliveries.config import (
    DELIVERY_DONATION_MODE_DISABLED,
    DELIVERY_DONATION_MODE_ONLY_AFTER_JOKERS,
    DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
)
from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestCanDeliveryBeDonated(SimpleTestCase):
    def test_canDeliveryBeDonated_donationModeDisabled_returnsFalse(self):
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_DISABLED,
        )

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=Mock(), delivery_date=Mock(), cache=cache
        )

        self.assertFalse(result)

    @patch.object(
        DeliveryDonationManager,
        "does_member_have_at_least_one_subscription_delivered_at_date",
        autospec=True,
    )
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_date_limit",
        autospec=True,
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(JokerManagementService, "can_joker_be_used_in_week", autospec=True)
    def test_canDeliveryBeDonated_donationModeOnlyAfterJokersAndJokerCanBeUsed_returnsFalse(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        cache = {}
        member = Mock()
        delivery_date = Mock()
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ONLY_AFTER_JOKERS,
        )

        self.setup_mocks_so_that_delivery_can_be_donated(
            mock_can_joker_be_used_in_week=mock_can_joker_be_used_in_week,
            mock_does_member_have_a_joker_in_week=mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_date_limit=mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_at_least_one_subscription_delivered_at_date=mock_does_member_have_at_least_one_subscription_delivered_at_date,
        )

        mock_can_joker_be_used_in_week.return_value = True

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=member, delivery_date=delivery_date, cache=cache
        )

        self.assertFalse(result)

        mock_can_joker_be_used_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_not_called()
        mock_can_joker_be_used_relative_to_date_limit.assert_not_called()
        mock_does_member_have_at_least_one_subscription_delivered_at_date.assert_not_called()

    @patch.object(
        DeliveryDonationManager,
        "does_member_have_at_least_one_subscription_delivered_at_date",
        autospec=True,
    )
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_date_limit",
        autospec=True,
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(JokerManagementService, "can_joker_be_used_in_week", autospec=True)
    def test_canDeliveryBeDonated_donationModeOnlyAfterJokersAndJokerCannotBeUsed_returnsTrue(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        cache = {}
        member = Mock()
        delivery_date = Mock()
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ONLY_AFTER_JOKERS,
        )

        self.setup_mocks_so_that_delivery_can_be_donated(
            mock_can_joker_be_used_in_week=mock_can_joker_be_used_in_week,
            mock_does_member_have_a_joker_in_week=mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_date_limit=mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_at_least_one_subscription_delivered_at_date=mock_does_member_have_at_least_one_subscription_delivered_at_date,
        )

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=member, delivery_date=delivery_date, cache=cache
        )

        self.assertTrue(result)

        mock_can_joker_be_used_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_at_least_one_subscription_delivered_at_date.assert_called_once_with(
            member_id=member.id, delivery_date=delivery_date, cache=cache
        )

    @patch.object(
        DeliveryDonationManager,
        "does_member_have_at_least_one_subscription_delivered_at_date",
        autospec=True,
    )
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_date_limit",
        autospec=True,
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(JokerManagementService, "can_joker_be_used_in_week", autospec=True)
    def test_canDeliveryBeDonated_donationModeAlwaysPossible_dontCheckForJoker(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        cache = {}
        member = Mock()
        delivery_date = Mock()
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        self.setup_mocks_so_that_delivery_can_be_donated(
            mock_can_joker_be_used_in_week=mock_can_joker_be_used_in_week,
            mock_does_member_have_a_joker_in_week=mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_date_limit=mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_at_least_one_subscription_delivered_at_date=mock_does_member_have_at_least_one_subscription_delivered_at_date,
        )

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=member, delivery_date=delivery_date, cache=cache
        )

        self.assertTrue(result)

        mock_can_joker_be_used_in_week.assert_not_called()
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_at_least_one_subscription_delivered_at_date.assert_called_once_with(
            member_id=member.id, delivery_date=delivery_date, cache=cache
        )

    @patch.object(
        DeliveryDonationManager,
        "does_member_have_at_least_one_subscription_delivered_at_date",
        autospec=True,
    )
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_date_limit",
        autospec=True,
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(JokerManagementService, "can_joker_be_used_in_week", autospec=True)
    def test_canDeliveryBeDonated_memberHasJokerInGivenWeek_returnsFalse(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        cache = {}
        member = Mock()
        delivery_date = Mock()
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ONLY_AFTER_JOKERS,
        )

        self.setup_mocks_so_that_delivery_can_be_donated(
            mock_can_joker_be_used_in_week=mock_can_joker_be_used_in_week,
            mock_does_member_have_a_joker_in_week=mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_date_limit=mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_at_least_one_subscription_delivered_at_date=mock_does_member_have_at_least_one_subscription_delivered_at_date,
        )

        mock_does_member_have_a_joker_in_week.return_value = True

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=member, delivery_date=delivery_date, cache=cache
        )

        self.assertFalse(result)

        mock_can_joker_be_used_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_not_called()
        mock_does_member_have_at_least_one_subscription_delivered_at_date.assert_not_called()

    @patch.object(
        DeliveryDonationManager,
        "does_member_have_at_least_one_subscription_delivered_at_date",
        autospec=True,
    )
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_date_limit",
        autospec=True,
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(JokerManagementService, "can_joker_be_used_in_week", autospec=True)
    def test_canDeliveryBeDonated_dateIsTooLate_returnsFalse(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        cache = {}
        member = Mock()
        delivery_date = Mock()
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        self.setup_mocks_so_that_delivery_can_be_donated(
            mock_can_joker_be_used_in_week=mock_can_joker_be_used_in_week,
            mock_does_member_have_a_joker_in_week=mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_date_limit=mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_at_least_one_subscription_delivered_at_date=mock_does_member_have_at_least_one_subscription_delivered_at_date,
        )

        mock_can_joker_be_used_relative_to_date_limit.return_value = False

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=member, delivery_date=delivery_date, cache=cache
        )

        self.assertFalse(result)

        mock_can_joker_be_used_in_week.assert_not_called()
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_at_least_one_subscription_delivered_at_date.assert_not_called()

    @patch.object(
        DeliveryDonationManager,
        "does_member_have_at_least_one_subscription_delivered_at_date",
        autospec=True,
    )
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_date_limit",
        autospec=True,
    )
    @patch.object(
        JokerManagementService, "does_member_have_a_joker_in_week", autospec=True
    )
    @patch.object(JokerManagementService, "can_joker_be_used_in_week", autospec=True)
    def test_canDeliveryBeDonated_noSubscriptionDeliveredOnGivenWeek_returnsFalse(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        cache = {}
        member = Mock()
        delivery_date = Mock()
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

        self.setup_mocks_so_that_delivery_can_be_donated(
            mock_can_joker_be_used_in_week=mock_can_joker_be_used_in_week,
            mock_does_member_have_a_joker_in_week=mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_date_limit=mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_at_least_one_subscription_delivered_at_date=mock_does_member_have_at_least_one_subscription_delivered_at_date,
        )

        mock_does_member_have_at_least_one_subscription_delivered_at_date.return_value = (
            False
        )

        result = DeliveryDonationManager.can_delivery_be_donated(
            member=member, delivery_date=delivery_date, cache=cache
        )

        self.assertFalse(result)

        mock_can_joker_be_used_in_week.assert_not_called()
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member=member, reference_date=delivery_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date=delivery_date, cache=cache
        )
        mock_does_member_have_at_least_one_subscription_delivered_at_date.assert_called_once_with(
            member_id=member.id, delivery_date=delivery_date, cache=cache
        )

    def setup_mocks_so_that_delivery_can_be_donated(
        self,
        mock_can_joker_be_used_in_week: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_at_least_one_subscription_delivered_at_date: Mock,
    ):
        mock_can_joker_be_used_in_week.return_value = False
        mock_does_member_have_a_joker_in_week.return_value = False
        mock_can_joker_be_used_relative_to_date_limit.return_value = True
        mock_does_member_have_at_least_one_subscription_delivered_at_date.return_value = (
            True
        )
