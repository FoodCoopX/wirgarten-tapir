from unittest.mock import Mock, patch

from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestJokerManagementServiceCanJokerBeUsedInWeek(TapirUnitTest):
    @staticmethod
    def setup_mocks_so_that_joker_can_be_used(
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
        cache: dict,
    ):
        mock_can_joker_be_used_relative_to_restrictions.return_value = True
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.return_value = (
            True
        )
        mock_can_joker_be_used_relative_to_date_limit.return_value = True
        mock_does_member_have_a_joker_in_week.return_value = False
        mock_can_joker_be_used_relative_to_weeks_without_delivery.return_value = True
        mock_does_member_have_a_donation_in_week.return_value = False
        mock_parameter_value(cache=cache, key=ParameterKeys.JOKERS_ENABLED, value=True)

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_jokerCanBeUsed_returnsTrue(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )

        self.assertTrue(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_donation_in_week.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_memberHasDonation_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )
        mock_does_member_have_a_donation_in_week.return_value = True

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_donation_in_week.assert_called_once_with(
            member=member, reference_date=reference_date, cache=cache
        )

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_restrictionsSayNo_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_joker_in_week,
            cache,
        )
        mock_can_joker_be_used_relative_to_restrictions.return_value = False

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_not_called()
        mock_does_member_have_a_donation_in_week.assert_not_called()

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_maxAmountSayNo_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.return_value = (
            False
        )

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_not_called()
        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_does_member_have_a_donation_in_week.assert_not_called()

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_dateLimitSayNo_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )
        mock_can_joker_be_used_relative_to_date_limit.return_value = False

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_not_called()
        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_not_called()
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_does_member_have_a_donation_in_week.assert_not_called()

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_jokerAlreadyUsedInWeek_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )
        mock_does_member_have_a_joker_in_week.return_value = True

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_not_called()
        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_not_called()
        mock_can_joker_be_used_relative_to_date_limit.assert_not_called()
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_does_member_have_a_donation_in_week.assert_not_called()

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_noDeliveryInGivenWeek_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )
        mock_can_joker_be_used_relative_to_weeks_without_delivery.return_value = False

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date, cache=cache
        )
        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_called_once_with(
            reference_date, cache=cache
        )
        mock_does_member_have_a_donation_in_week.assert_not_called()

    @patch.object(DeliveryDonationManager, "does_member_have_a_donation_in_week")
    @patch.object(
        JokerManagementService, "can_joker_be_used_relative_to_weeks_without_delivery"
    )
    @patch.object(JokerManagementService, "does_member_have_a_joker_in_week")
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_date_limit")
    @patch.object(
        JokerManagementService,
        "can_joker_be_used_relative_to_max_amount_per_growing_period",
    )
    @patch.object(JokerManagementService, "can_joker_be_used_relative_to_restrictions")
    def test_canJokerBeUsed_jokerFeatureDisabled_returnsFalse(
        self,
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
        mock_can_joker_be_used_relative_to_weeks_without_delivery: Mock,
        mock_does_member_have_a_donation_in_week: Mock,
    ):
        member = Mock()
        reference_date = Mock()

        cache = {}
        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
            mock_can_joker_be_used_relative_to_weeks_without_delivery,
            mock_does_member_have_a_donation_in_week,
            cache,
        )
        mock_parameter_value(cache=cache, key=ParameterKeys.JOKERS_ENABLED, value=False)

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(
                member, reference_date, cache=cache
            )
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_not_called()
        mock_can_joker_be_used_relative_to_date_limit.assert_not_called()
        mock_does_member_have_a_joker_in_week.assert_not_called()
        mock_can_joker_be_used_relative_to_weeks_without_delivery.assert_not_called()
        mock_does_member_have_a_donation_in_week.assert_not_called()
