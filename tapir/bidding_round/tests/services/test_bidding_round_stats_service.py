from decimal import Decimal

from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundStatsService(TapirIntegrationTest):
    def test_evaluation_sumsAmountsAndComputesCoverage(self):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        for amount in (Decimal("50.00"), Decimal("100.00")):
            bid = BidFactory.create(round=bidding_round)
            BidItemFactory.create(
                bid=bid,
                round_product_type=round_product_type,
                amount_1=amount,
            )

        evaluation = BiddingRoundStatsService.build_admin_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual("1800.00", evaluation["reached_per_year"])
        self.assertEqual("1000.00", evaluation["target_per_year"])
        self.assertEqual(180.0, evaluation["coverage_percent"])
        self.assertEqual(2, evaluation["bidder_count"])
        self.assertEqual("75.00", evaluation["bidder_average_per_month"])
        self.assertEqual(2, len(evaluation["bids"]))
        self.assertEqual(
            "600.00",
            next(
                row["amount_per_year"]
                for row in evaluation["bids"]
                if row["amount_per_month"] == "50.00"
            ),
        )

    def test_evaluation_withSeveralShares_multipliesAmountsByQuantity(self):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            quantity=2,
            amount_1=Decimal("50.00"),
        )

        evaluation = BiddingRoundStatsService.build_admin_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual("1200.00", evaluation["reached_per_year"])
        self.assertEqual("100.00", evaluation["bidder_average_per_month"])
        self.assertEqual("100.00", evaluation["bids"][0]["amount_per_month"])
        self.assertEqual("1200.00", evaluation["bids"][0]["amount_per_year"])

    def test_coveragePercent_withoutTarget_returnsZero(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=None
        )

        self.assertEqual(
            0.0, BiddingRoundStatsService.get_coverage_percent(bidding_round)
        )

    def test_bidderAverage_withoutBids_returnsZero(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)

        self.assertEqual(
            Decimal("0"),
            BiddingRoundStatsService.get_bidder_average_per_month(bidding_round),
        )
