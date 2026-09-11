from unittest.mock import Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager


class TestCancelDonation(TapirUnitTest):
    def test_cancelDonation_default_callsDelete(self):
        donation = Mock()

        DeliveryDonationManager.cancel_donation(donation)

        donation.delete.assert_called_once_with()
