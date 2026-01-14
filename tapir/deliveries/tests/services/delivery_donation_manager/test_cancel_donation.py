from unittest.mock import Mock

from django.test import SimpleTestCase

from tapir.deliveries.services.delivery_donation_manager import DeliveryDonationManager


class TestCancelDonation(SimpleTestCase):
    def test_cancelDonation_default_callsDelete(self):
        donation = Mock()

        DeliveryDonationManager.cancel_donation(donation)

        donation.delete.assert_called_once_with()
