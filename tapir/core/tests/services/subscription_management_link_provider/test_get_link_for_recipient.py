from unittest.mock import MagicMock, patch

from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)
from tapir.mail.tests.factories import StaticSegmentRecipientFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetLinkForRecipient(TapirUnitTest):
    @patch.object(
        SubscriptionManagementLinkProvider,
        "build_link_for_address",
        autospec=True,
        return_value="https://management.link",
    )
    def test_getLinkForRecipient_default_buildsTheLinkForTheRecipientAddress(
        self, mock_build_link_for_address: MagicMock
    ):
        recipient = StaticSegmentRecipientFactory.build(email="static@example.com")
        cache = {}

        result = SubscriptionManagementLinkProvider.get_link_for_recipient(
            recipient=recipient, cache=cache
        )

        self.assertEqual("https://management.link", result)
        mock_build_link_for_address.assert_called_once_with(
            address="static@example.com", cache=cache
        )
