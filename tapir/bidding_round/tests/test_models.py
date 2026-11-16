import pytest
from django.db import IntegrityError, transaction

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundModelConstraints(TapirIntegrationTest):
    def test_round_allowsOnlyOneProductType(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BiddingRoundProductTypeFactory.create(round=bidding_round)

    def test_round_allowsOnlyOneBidPerMember(self):
        bid = BidFactory.create()

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BidFactory.create(round=bid.round, member=bid.member)

    def test_bid_allowsOnlyOneItemPerRoundProductType(self):
        item = BidItemFactory.create()

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                BidItemFactory.create(
                    bid=item.bid, round_product_type=item.round_product_type
                )

    def test_bidItem_quantityOutsideRange_raisesIntegrityError(self):
        for quantity in (0, 6):
            with self.subTest(quantity=quantity), transaction.atomic():
                with pytest.raises(IntegrityError):
                    BidItemFactory.create(quantity=quantity)

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
