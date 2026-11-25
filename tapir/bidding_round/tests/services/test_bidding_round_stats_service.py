from decimal import Decimal

from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.wirgarten.tests.factories import ProductFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundStatsService(TapirIntegrationTest):
    def test_buildAdminEvaluation_default_sumsAmountsAndComputesCoverage(self):
        bidding_round = BiddingRoundFactory.create(
            target_amount_per_year=Decimal("1000.00")
        )
        for amount in (Decimal("50.00"), Decimal("100.00")):
            BidFactory.create(round=bidding_round, amount_1=amount)

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

    def test_buildAdminEvaluation_withSeveralShares_multipliesAmountsByQuantity(self):
        bidding_round = BiddingRoundFactory.create(
            target_amount_per_year=Decimal("1000.00")
        )
        BidFactory.create(round=bidding_round, quantity=2, amount_1=Decimal("50.00"))

        evaluation = BiddingRoundStatsService.build_admin_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual("1200.00", evaluation["reached_per_year"])
        self.assertEqual("100.00", evaluation["bidder_average_per_month"])
        self.assertEqual("100.00", evaluation["bids"][0]["amount_per_month"])
        self.assertEqual("1200.00", evaluation["bids"][0]["amount_per_year"])
        self.assertEqual(2, evaluation["bids"][0]["quantity"])

    def test_getCoveragePercent_withoutTarget_returnsZero(self):
        bidding_round = BiddingRoundFactory.create(target_amount_per_year=None)

        self.assertEqual(
            0.0, BiddingRoundStatsService.get_coverage_percent(bidding_round)
        )

    def test_getBidderAveragePerMonth_withoutBids_returnsZero(self):
        bidding_round = BiddingRoundFactory.create()

        self.assertEqual(
            Decimal("0"),
            BiddingRoundStatsService.get_bidder_average_per_month(bidding_round),
        )

    def test_getProductSize_withoutRoundSize_usesTheProductPriceSize(self):
        bidding_round = BiddingRoundFactory.create()
        product = ProductFactory.create(type=bidding_round.product_type)
        BiddingRoundProductPriceFactory.create(
            round=bidding_round, product=product, size=None
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("10.00"),
            size=Decimal("2.0000"),
            valid_from=bidding_round.growing_period.start_date,
        )

        self.assertEqual(
            Decimal("2.0000"),
            BiddingRoundStatsService.get_product_size(product, bidding_round, cache={}),
        )
