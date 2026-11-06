from django.test import override_settings

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.waiting_list.views import SendWaitingListLinkApiView


class TestSendWaitingListLinkApiView(TapirUnitTest):
    @override_settings(SITE_URL="https://tapir.test")
    def test_buildWaitingListLink_default_returnsFullLink(self):
        result = SendWaitingListLinkApiView.build_waiting_list_link(
            entry_id="test_id", link_key="test_key"
        )

        self.assertEqual(
            "https://tapir.test/waiting_list/waiting_list_confirm?entry_id=test_id&link_key=test_key",
            result,
        )  # Email links must include the configured site URL.
