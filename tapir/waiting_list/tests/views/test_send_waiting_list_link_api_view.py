from django.conf import settings
from django.test import override_settings

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.waiting_list.views import SendWaitingListLinkApiView


class TestSendWaitingListLinkApiView(TapirUnitTest):
    def test_buildWaitingListLink_default_returnsFullLink(self):
        result = SendWaitingListLinkApiView.build_waiting_list_link(
            entry_id="test_id", link_key="test_key"
        )

        self.assertEqual(
            f"{settings.SITE_URL}/waiting_list/waiting_list_confirm?entry_id=test_id&link_key=test_key",
            result,
        )

    @override_settings(SITE_URL="http://tapir.test:8000")
    def test_buildWaitingListLink_usesConfiguredSiteAddress(self):
        self.assertEqual(
            "http://tapir.test:8000/waiting_list/waiting_list_confirm?entry_id=test_id&link_key=test_key",
            SendWaitingListLinkApiView.build_waiting_list_link("test_id", "test_key"),
        )
