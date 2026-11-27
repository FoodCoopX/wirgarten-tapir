from unittest.mock import MagicMock, patch

from django.test import override_settings

from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)
from tapir.core.services.subscription_management_token_signer import (
    SubscriptionManagementTokenSigner,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@override_settings(SITE_URL="https://tapir.example")
@patch.object(
    SubscriptionManagementTokenSigner, "sign", autospec=True, return_value="the_token"
)
@patch.object(
    TapirCache, "get_member_id_with_main_address", autospec=True, return_value=None
)
class TestBuildLinkForAddress(TapirUnitTest):
    def test_buildLinkForAddress_addressIsAMainAddress_returnsTheAbsoluteMemberProfileUrl(
        self, mock_get_member_id_with_main_address: MagicMock, mock_sign: MagicMock
    ):
        mock_get_member_id_with_main_address.return_value = "member_id"
        cache = {}

        result = SubscriptionManagementLinkProvider.build_link_for_address(
            address="main@example.com", cache=cache
        )

        self.assertEqual("https://tapir.example/tapir/members/member_id", result)
        mock_get_member_id_with_main_address.assert_called_once_with(
            address="main@example.com", cache=cache
        )
        mock_sign.assert_not_called()

    def test_buildLinkForAddress_addressIsNotAMainAddress_returnsTheSignedManagementPageUrl(
        self, _: MagicMock, mock_sign: MagicMock
    ):
        result = SubscriptionManagementLinkProvider.build_link_for_address(
            address="extra@example.com", cache={}
        )

        self.assertEqual(
            "https://tapir.example/core/subscription_management/the_token", result
        )
        mock_sign.assert_called_once_with(address="extra@example.com")
