from tapir.waiting_list.views import PublicConfirmWaitingListEntryView
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPublicConfirmWaitingListEntryView(TapirIntegrationTest):
    def test_wip(self):
        PublicConfirmWaitingListEntryView
