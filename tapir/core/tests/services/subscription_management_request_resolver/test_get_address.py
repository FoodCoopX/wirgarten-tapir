from unittest.mock import MagicMock, patch

from rest_framework.exceptions import PermissionDenied

from tapir.core.services.subscription_management_request_resolver import (
    SubscriptionManagementRequestResolver,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "is_member_main_address", autospec=True, return_value=False)
@patch.object(
    SubscriptionManagementTokenSigner,
    "get_address",
    autospec=True,
    return_value="address@example.com",
)
class TestGetAddress(TapirUnitTest):
    def test_getAddress_validTokenForANonMainAddress_returnsTheAddress(
        self, mock_get_address: MagicMock, mock_is_member_main_address: MagicMock
    ):
        cache = {}

        result = SubscriptionManagementRequestResolver.get_address(
            token="the_token", cache=cache
        )

        self.assertEqual("address@example.com", result)
        mock_get_address.assert_called_once_with(token="the_token")
        mock_is_member_main_address.assert_called_once_with(
            address="address@example.com", cache=cache
        )

    def test_getAddress_tokenIsInvalid_raisesPermissionDenied(
        self, mock_get_address: MagicMock, _: MagicMock
    ):
        mock_get_address.return_value = None

        with self.assertRaisesMessage(
            PermissionDenied, "Dieser Link ist abgelaufen oder ungültig."
        ):
            SubscriptionManagementRequestResolver.get_address(
                token="the_token", cache={}
            )

    def test_getAddress_tokenIsMissing_raisesPermissionDenied(
        self, mock_get_address: MagicMock, _: MagicMock
    ):
        mock_get_address.return_value = None

        with self.assertRaisesMessage(
            PermissionDenied, "Dieser Link ist abgelaufen oder ungültig."
        ):
            SubscriptionManagementRequestResolver.get_address(token=None, cache={})

        mock_get_address.assert_called_once_with(token="")

    def test_getAddress_addressIsAMainAddress_raisesPermissionDenied(
        self, _: MagicMock, mock_is_member_main_address: MagicMock
    ):
        mock_is_member_main_address.return_value = True

        with self.assertRaisesMessage(
            PermissionDenied, "Dieser Link ist abgelaufen oder ungültig."
        ):
            SubscriptionManagementRequestResolver.get_address(
                token="the_token", cache={}
            )
