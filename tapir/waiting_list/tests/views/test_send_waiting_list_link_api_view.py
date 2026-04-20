from django.test import SimpleTestCase

from tapir.waiting_list.views import SendWaitingListLinkApiView


class TestSendWaitingListLinkApiView(SimpleTestCase):
    def test_buildWaitingListLink_default_returnsFullLink(self):
        result = SendWaitingListLinkApiView.build_waiting_list_link(
            entry_id="test_id", link_key="test_key"
        )

        self.assertEqual(
            "http://localhost:8000/waiting_list/waiting_list_confirm?entry_id=test_id&link_key=test_key",
            result,
        )  # It is important that the URL root (here localhost:8000 but in general tapir.solawi.de) is included: this link will be sent by mail.
