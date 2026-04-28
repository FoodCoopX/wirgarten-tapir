import datetime
from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.deliveries.tests.factories import DeliveryDonationFactory
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestCanDonationBeCancelled(TapirUnitTest):
    def setUp(self):
        self.today = mock_timezone(
            test=self, now=datetime.datetime(year=2021, month=11, day=13)
        ).date()

    @patch.object(
        JokerManagementService, "get_date_limit_for_joker_changes", autospec=True
    )
    def test_canDonationBeCancelled_todayIsAfterDateLimit_returnsFalse(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        mock_get_date_limit_for_joker_changes.return_value = (
            self.today - datetime.timedelta(days=1)
        )
        donation = DeliveryDonationFactory.build()
        cache = {}

        result = DeliveryDonationManager.can_donation_be_cancelled(
            donation=donation, cache=cache
        )

        self.assertFalse(result)
        mock_get_date_limit_for_joker_changes.assert_called_once_with(
            reference_date=donation.date, cache=cache
        )

    @patch.object(
        JokerManagementService, "get_date_limit_for_joker_changes", autospec=True
    )
    def test_canDonationBeCancelled_todayIsExactlyAtDateLimit_returnsTrue(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        mock_get_date_limit_for_joker_changes.return_value = self.today
        donation = DeliveryDonationFactory.build()
        cache = {}

        result = DeliveryDonationManager.can_donation_be_cancelled(
            donation=donation, cache=cache
        )

        self.assertTrue(result)
        mock_get_date_limit_for_joker_changes.assert_called_once_with(
            reference_date=donation.date, cache=cache
        )

    @patch.object(
        JokerManagementService, "get_date_limit_for_joker_changes", autospec=True
    )
    def test_canDonationBeCancelled_todayIsBeforeDateLimit_returnsTrue(
        self, mock_get_date_limit_for_joker_changes: Mock
    ):
        mock_get_date_limit_for_joker_changes.return_value = (
            self.today + datetime.timedelta(days=1)
        )
        donation = DeliveryDonationFactory.build()
        cache = {}

        result = DeliveryDonationManager.can_donation_be_cancelled(
            donation=donation, cache=cache
        )

        self.assertTrue(result)
        mock_get_date_limit_for_joker_changes.assert_called_once_with(
            reference_date=donation.date, cache=cache
        )
