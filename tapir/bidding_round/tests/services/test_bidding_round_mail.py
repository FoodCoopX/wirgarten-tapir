from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.tapirmail import get_default_mail_content
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundMailDrafts(TapirIntegrationTest):
    def test_getDefaultMailContent_draftsExist(self):
        for key in [
            Events.BIDDING_ROUND_BID_RECEIVED,
            Events.BIDDING_ROUND_BID_UPDATED,
        ]:
            with self.subTest(key=key):
                content = get_default_mail_content(key)
                self.assertIn("Gebot", content)
