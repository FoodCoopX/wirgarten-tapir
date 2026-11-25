from unittest.mock import patch

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.models import (
    Bid,
    BiddingRound,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(UserGenerator, "get_user_count", return_value=25, autospec=True)
class TestBiddingRoundGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_generateAll_createsActiveRoundWithBids(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        rounds = BiddingRound.objects.filter(status=BIDDING_ROUND_STATUS_ACTIVE)
        self.assertEqual(1, rounds.count())
        self.assertTrue(BiddingRoundProductPrice.objects.exists())
        self.assertTrue(Bid.objects.exists())

    def test_generateAll_createsClosedBidRangeRoundWithTwoAmounts(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        rounds = BiddingRound.objects.filter(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )
        self.assertEqual(1, rounds.count())
        bidding_round = rounds.first()
        self.assertEqual(BIDDING_ROUND_STATUS_CLOSED, bidding_round.status)
        self.assertEqual(2, bidding_round.bid_levels)

        bid = Bid.objects.filter(round=bidding_round).first()
        self.assertIsNotNone(bid)
        self.assertIsNotNone(bid.amount_1)
        self.assertIsNotNone(bid.amount_2)
        self.assertIsNone(bid.amount_3)
        self.assertLess(bid.amount_1, bid.amount_2)

    def test_generateAll_bidRangeRoundReachesCalibratedCoverage(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        bidding_round = BiddingRound.objects.get(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )
        for level, expected in ((1, 81.0), (2, 101.0)):
            self.assertAlmostEqual(
                expected,
                BiddingRoundStatsService.get_coverage_percent(
                    bidding_round,
                    BiddingRoundStatsService.get_level_position(level, bidding_round),
                ),
                delta=1.0,
                msg=f"level {level}",
            )
        self.assertAlmostEqual(
            91.0,
            BiddingRoundStatsService.get_coverage_percent(bidding_round, 50),
            delta=1.0,
            msg="middle position",
        )
