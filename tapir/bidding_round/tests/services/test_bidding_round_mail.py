from unittest.mock import patch

from django.conf import settings
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.bidding_round.config import TRAFFIC_LIGHT
from tapir.bidding_round.services.bidding_round_mail_token_builder import (
    BiddingRoundMailTokenBuilder,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.factories import BiddingRoundProductFactory
from tapir.bidding_round.tests.helpers import build_item, create_open_round
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.tapirmail import get_default_mail_content
from tapir.wirgarten.tests.factories import MemberFactory, ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


def _assert_trigger_fired(mock_fire_action, key):
    mock_fire_action.assert_called()
    for call in mock_fire_action.mock_calls:
        trigger_data = call.kwargs["trigger_data"]
        if trigger_data.key == key:
            return
    raise AssertionError(
        f"Expected trigger ({key}) not found in {mock_fire_action.mock_calls}"
    )


class TestBiddingRoundMail(TapirIntegrationTest):
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_saveBid_newBid_firesReceivedMail(self, mock_fire_action):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()

        BiddingRoundService.save_bid(
            member, round_, [build_item(round_product, product)], cache={}
        )

        _assert_trigger_fired(mock_fire_action, Events.BIDDING_ROUND_BID_RECEIVED)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_saveBid_existingBid_firesUpdatedMail(self, mock_fire_action):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        item = build_item(round_product, product)

        BiddingRoundService.save_bid(member, round_, [item], cache={})
        BiddingRoundService.save_bid(member, round_, [item], cache={})

        _assert_trigger_fired(mock_fire_action, Events.BIDDING_ROUND_BID_UPDATED)

    def test_buildBidTokens_containsItemsTotalAndLink(self):
        round_ = create_open_round(bidding_procedure=TRAFFIC_LIGHT)
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        bid = BiddingRoundService.save_bid(
            member,
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="70.00",
                    amount_2="80.00",
                    amount_3="90.00",
                )
            ],
            cache={},
        )

        tokens = BiddingRoundMailTokenBuilder.build_bid_tokens(bid, cache={})

        self.assertEqual(round_.name, tokens["round_name"])
        self.assertIn("80,00", tokens["bid_items_html"])
        self.assertIn("960", tokens["bid_total_per_year"])
        self.assertEqual(settings.SITE_URL + "/bidding_rounds/", tokens["bid_link"])

    def test_getDefaultMailContent_draftsExist(self):
        for key in [
            Events.BIDDING_ROUND_BID_RECEIVED,
            Events.BIDDING_ROUND_BID_UPDATED,
        ]:
            with self.subTest(key=key):
                content = get_default_mail_content(key)
                self.assertIn("Gebot", content)
