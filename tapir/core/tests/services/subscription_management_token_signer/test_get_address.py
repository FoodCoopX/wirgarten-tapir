from unittest.mock import MagicMock, patch

from django.core import signing

from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(signing.time, "time", autospec=True, return_value=1_000_000)
class TestGetAddress(TapirUnitTest):
    def test_getAddress_tokenWithinValidity_returnsTheSignedAddress(
        self, mock_time: MagicMock
    ):
        token = SubscriptionManagementTokenSigner.sign(address="extra@example.com")
        mock_time.return_value += (
            SubscriptionManagementTokenSigner.VALIDITY_HOURS * 3600 - 1
        )

        result = SubscriptionManagementTokenSigner.get_address(token=token)

        self.assertEqual("extra@example.com", result)

    def test_getAddress_tokenExpired_returnsNone(self, mock_time: MagicMock):
        token = SubscriptionManagementTokenSigner.sign(address="extra@example.com")
        mock_time.return_value += (
            SubscriptionManagementTokenSigner.VALIDITY_HOURS * 3600 + 1
        )

        result = SubscriptionManagementTokenSigner.get_address(token=token)

        self.assertIsNone(result)

    def test_getAddress_tokenTamperedWith_returnsNone(self, _: MagicMock):
        token = SubscriptionManagementTokenSigner.sign(address="extra@example.com")

        result = SubscriptionManagementTokenSigner.get_address(
            token=token[:-1] + ("A" if token[-1] != "A" else "B"),
        )

        self.assertIsNone(result)

    def test_getAddress_tokenSignedWithAnotherSalt_returnsNone(self, _: MagicMock):
        token = signing.dumps("extra@example.com", salt="another_salt")

        result = SubscriptionManagementTokenSigner.get_address(token=token)

        self.assertIsNone(result)
