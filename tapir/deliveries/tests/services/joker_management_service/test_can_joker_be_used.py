from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from tapir.deliveries.services.joker_management_service import JokerManagementService


class TestJokerManagementServiceCanJokerBeUsed(SimpleTestCase):  #
    @staticmethod
    def setup_mocks_so_that_joker_can_be_used(
        mock_can_joker_be_used_relative_to_restrictions: Mock,
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period: Mock,
        mock_can_joker_be_used_relative_to_date_limit: Mock,
        mock_does_member_have_a_joker_in_week: Mock,
    ):
        mock_can_joker_be_used_relative_to_restrictions.return_value = True
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.return_value = (
            True
        )
        mock_can_joker_be_used_relative_to_date_limit.return_value = True
        mock_does_member_have_a_joker_in_week.return_value = False

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
    ):
        member = Mock()
        reference_date = Mock()

        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
        )

        self.assertTrue(
            JokerManagementService.can_joker_be_used_in_week(member, reference_date)
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_called_once_with(
            member, reference_date
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date
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
    ):
        member = Mock()
        reference_date = Mock()

        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
        )
        mock_can_joker_be_used_relative_to_restrictions.return_value = False

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(member, reference_date)
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_called_once_with(
            member, reference_date
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date
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
    ):
        member = Mock()
        reference_date = Mock()

        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
        )
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.return_value = (
            False
        )

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(member, reference_date)
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_called_once_with(
            member, reference_date
        )
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date
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
    ):
        member = Mock()
        reference_date = Mock()

        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
        )
        mock_can_joker_be_used_relative_to_date_limit.return_value = False

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(member, reference_date)
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_not_called()
        mock_can_joker_be_used_relative_to_date_limit.assert_called_once_with(
            reference_date
        )
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date
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
    ):
        member = Mock()
        reference_date = Mock()

        self.setup_mocks_so_that_joker_can_be_used(
            mock_can_joker_be_used_relative_to_restrictions,
            mock_can_joker_be_used_relative_to_max_amount_per_growing_period,
            mock_can_joker_be_used_relative_to_date_limit,
            mock_does_member_have_a_joker_in_week,
        )
        mock_does_member_have_a_joker_in_week.return_value = True

        self.assertFalse(
            JokerManagementService.can_joker_be_used_in_week(member, reference_date)
        )

        mock_can_joker_be_used_relative_to_restrictions.assert_not_called()
        mock_can_joker_be_used_relative_to_max_amount_per_growing_period.assert_not_called()
        mock_can_joker_be_used_relative_to_date_limit.assert_not_called()
        mock_does_member_have_a_joker_in_week.assert_called_once_with(
            member, reference_date
        )
