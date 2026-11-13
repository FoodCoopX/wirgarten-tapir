import pytest
from django.db import IntegrityError

from tapir.bidding_round.config import CONFIGURATION, SIMPLE
from tapir.bidding_round.models import BiddingRound
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRound(TapirIntegrationTest):
    def test_createdWithDefaults_statusIsKonfiguration(self):
        bidding_round = BiddingRoundFactory.create()
        self.assertEqual(CONFIGURATION, bidding_round.status)
        self.assertEqual(SIMPLE, bidding_round.bidding_procedure)
        self.assertEqual(1, bidding_round.bid_levels)
        self.assertTrue(bidding_round.include_auto_renewed)
        self.assertFalse(bidding_round.is_average_bid_locked)

    def test_endAtMissing_raisesIntegrityError(self):
        existing_round = BiddingRoundFactory.create()
        with pytest.raises(IntegrityError):
            BiddingRound.objects.create(
                growing_period=existing_round.growing_period,
                name="Round without end date",
            )

    def test_inheritsTapirModel_createdAndUpdatedAtSet(self):
        bidding_round = BiddingRoundFactory.create()
        self.assertIsNotNone(bidding_round.id)
        self.assertIsNotNone(bidding_round.created_at)
        self.assertIsNotNone(bidding_round.updated_at)


class TestBiddingRoundProduct(TapirIntegrationTest):
    def test_secondProductForRound_raisesIntegrityError(self):
        round_product = BiddingRoundProductFactory.create()
        with pytest.raises(IntegrityError):
            BiddingRoundProductFactory.create(round=round_product.round)

    def test_createdWithDefaults_targetAmountPerYearIsNone(self):
        round_product = BiddingRoundProductFactory.create()
        self.assertIsNone(round_product.target_amount_per_year)


class TestBiddingRoundProductPrice(TapirIntegrationTest):
    def test_duplicateForRoundProductAndProduct_raisesIntegrityError(self):
        price = BiddingRoundProductPriceFactory.create()
        with pytest.raises(IntegrityError):
            BiddingRoundProductPriceFactory.create(
                round_product=price.round_product, product=price.product
            )

    def test_createdWithDefaults_valuesAreNone(self):
        price = BiddingRoundProductPriceFactory.create(
            reference_value=None, min_amount=None
        )
        self.assertIsNone(price.reference_value)
        self.assertIsNone(price.min_amount)


class TestBid(TapirIntegrationTest):
    def test_duplicateForRoundAndMember_raisesIntegrityError(self):
        bid = BidFactory.create()
        with pytest.raises(IntegrityError):
            BidFactory.create(round=bid.round, member=bid.member)


class TestBidItem(TapirIntegrationTest):
    def test_duplicateForBidAndRoundProduct_raisesIntegrityError(self):
        bid_item = BidItemFactory.create()
        with pytest.raises(IntegrityError):
            BidItemFactory.create(
                bid=bid_item.bid, round_product=bid_item.round_product
            )
