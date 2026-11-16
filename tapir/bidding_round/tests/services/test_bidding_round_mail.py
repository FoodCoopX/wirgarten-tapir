from decimal import Decimal
from unittest.mock import patch

from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.services.bid_input import BidInput
from tapir.bidding_round.services.bidding_round_mail_token_builder import (
    BiddingRoundMailTokenBuilder,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.helpers import get_product_for_round, create_open_round
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import get_default_mail_content
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundMail(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_saveBid_newBid_firesReceivedMail(self, mock_fire_action):
        bidding_round = create_open_round()
        product = get_product_for_round(bidding_round)
        member = MemberFactory.create()

        BiddingRoundService.save_bid(
            member,
            bidding_round,
            BidInput(product_id=product.id, quantity=1, amount_1=Decimal("80.00")),
            cache={},
        )

        self.assert_mail_event_has_been_triggered(
            mock_fire_action, Events.BIDDING_ROUND_BID_RECEIVED
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_saveBid_existingBid_firesUpdatedMail(self, mock_fire_action):
        bidding_round = create_open_round()
        product = get_product_for_round(bidding_round)
        member = MemberFactory.create()
        bid_input = BidInput(
            product_id=product.id, quantity=1, amount_1=Decimal("80.00")
        )

        BiddingRoundService.save_bid(member, bidding_round, bid_input, cache={})
        BiddingRoundService.save_bid(member, bidding_round, bid_input, cache={})

        self.assert_mail_event_has_been_triggered(
            mock_fire_action, Events.BIDDING_ROUND_BID_UPDATED
        )

    def test_buildBidTokens_default_containsBidTotalAndLink(self):
        bidding_round = create_open_round(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        product = get_product_for_round(bidding_round)
        member = MemberFactory.create()
        bid = BiddingRoundService.save_bid(
            member,
            bidding_round,
            BidInput(
                product_id=product.id,
                quantity=2,
                amount_1=Decimal("80.00"),
                amount_2=Decimal("90.00"),
            ),
            cache={},
            send_mail=False,
        )

        tokens = BiddingRoundMailTokenBuilder.build_bid_tokens(bid, cache={})

        self.assertEqual(bidding_round.name, tokens["round_name"])
        self.assertIn("170,00", tokens["bid_items_html"])
        self.assertIn("2 Anteile", tokens["bid_items_html"])
        self.assertIn("2.040,00", tokens["bid_items_html"])
        self.assertIn("2.040,00", tokens["bid_total_per_year"])
        self.assertIn("/bidding_rounds/", tokens["bid_link"])

    def test_getDefaultMailContent_bidReceived_containsTheBidTokens(self):
        content = get_default_mail_content(Events.BIDDING_ROUND_BID_RECEIVED)

        self.assertIn("Gebot erhalten.Gesamtbetrag pro Jahr", content)

    def test_buildBidTokens_quantityOne_usesSingular(self):
        bidding_round = create_open_round()
        product = get_product_for_round(bidding_round)
        member = MemberFactory.create()
        bid = BiddingRoundService.save_bid(
            member,
            bidding_round,
            BidInput(
                product_id=product.id,
                quantity=1,
                amount_1=Decimal("80.00"),
            ),
            cache={},
            send_mail=False,
        )

        tokens = BiddingRoundMailTokenBuilder.build_bid_tokens(bid, cache={})

        self.assertIn("1 Anteil", tokens["bid_items_html"])
        self.assertNotIn("1 Anteile", tokens["bid_items_html"])
