import pytest
from django.db import IntegrityError, transaction

from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundModelConstraints(TapirIntegrationTest):
    def test_biddingRound_allowsOnlyOneBidPerMember(self):
        bid = BidFactory.create()

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BidFactory.create(round=bid.round, member=bid.member)

    def test_bid_quantityOutsideRange_raisesIntegrityError(self):
        for quantity in (0, 6):
            with self.subTest(quantity=quantity), transaction.atomic():
                with pytest.raises(IntegrityError):
                    BidFactory.create(quantity=quantity)

    def test_biddingRoundProductPrice_allowsOnlyOnePricePerProduct(self):
        price = BiddingRoundProductPriceFactory.create()

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BiddingRoundProductPriceFactory.create(
                    round=price.round, product=price.product
                )

    def test_createdSubscription_allowsOnlyOneLinkPerRoundAndSubscription(self):
        bidding_round = BiddingRoundFactory.create()
        subscription = SubscriptionFactory.create()
        BiddingRoundCreatedSubscription.objects.create(
            round=bidding_round, subscription=subscription
        )

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BiddingRoundCreatedSubscription.objects.create(
                    round=bidding_round, subscription=subscription
                )

    def test_round_bidRangeRequiresTwoLevels(self):
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BiddingRoundFactory.create(
                    bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE,
                    bid_levels=3,
                )
