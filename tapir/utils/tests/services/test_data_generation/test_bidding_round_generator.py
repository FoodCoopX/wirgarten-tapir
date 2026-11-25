from decimal import Decimal, ROUND_CEILING
from unittest.mock import patch

import pytest

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_PROCEDURE_SIMPLE,
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
from tapir.configuration.parameter import get_parameter_value
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation import bidding_round_generator
from tapir.utils.services.test_data_generation.bidding_round_generator import (
    HARVEST_SHARE_PRODUCT_TYPE_NAME,
)
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.user_generator import UserGenerator
from tapir.utils.services.test_data_generation.vierlande_generator import (
    VierlandeGenerator,
)
from tapir.wirgarten.models import GrowingPeriod, ProductType, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_today

VIERLANDE_SMALL_VARIANTS = [
    {
        "name": "einfach",
        "base_price": 70,
        "size": 1.0,
        "count": 30,
        "base": True,
        "description": "Der einfache Ernteanteil.",
    },
    {
        "name": "groß",
        "base_price": 140,
        "size": 2.0,
        "count": 2,
        "base": False,
        "description": "Der große Ernteanteil.",
    },
]
VIERLANDE_SMALL_MEMBER_COUNT = 40


@patch.object(UserGenerator, "get_user_count", return_value=25, autospec=True)
class TestBiddingRoundGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _admin_percent(bidding_round, level):
        position = BiddingRoundStatsService.get_level_position(level, bidding_round)
        reached_per_year = BiddingRoundStatsService.get_reached_per_year(
            bidding_round, position, cache={}
        )
        extra_positions = BiddingRoundStatsService.build_extra_positions(
            bidding_round, cache={}
        )
        extra_reached_per_year = sum(
            (
                entry["reached_per_year"]
                for entry in extra_positions.values()
                if entry["applicable"]
            ),
            Decimal("0"),
        )
        target_per_year = BiddingRoundStatsService.get_target_per_year(bidding_round)
        if not target_per_year:
            return None
        return float(
            (reached_per_year + extra_reached_per_year) / target_per_year * 100
        )

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
                self._admin_percent(bidding_round, level),
                delta=1.0,
                msg=f"level {level}",
            )
        self.assertAlmostEqual(
            91.0,
            BiddingRoundStatsService.get_coverage_percent(bidding_round, 50, cache={}),
            delta=1.0,
            msg="middle position",
        )

    def test_generateAll_createsClosedThreeLevelSimpleRound(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        rounds = BiddingRound.objects.filter(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
            bid_levels=3,
            status=BIDDING_ROUND_STATUS_CLOSED,
        )
        self.assertEqual(1, rounds.count())

        bid = Bid.objects.filter(round=rounds.first()).first()
        self.assertIsNotNone(bid)
        self.assertIsNotNone(bid.amount_1)
        self.assertIsNotNone(bid.amount_2)
        self.assertIsNotNone(bid.amount_3)
        self.assertLess(bid.amount_1, bid.amount_2)
        self.assertLess(bid.amount_2, bid.amount_3)

    def test_generateAll_simpleThreeLevelRoundReachesCalibratedCoverage(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        bidding_round = BiddingRound.objects.get(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
            bid_levels=3,
            status=BIDDING_ROUND_STATUS_CLOSED,
        )
        for level, expected in ((1, 81.0), (2, 91.0), (3, 109.0)):
            self.assertAlmostEqual(
                expected,
                self._admin_percent(bidding_round, level),
                delta=1.0,
                msg=f"level {level}",
            )

    def test_generateAll_splitsMembersIntoBiddersAutoRenewedAndFree(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        active_round = BiddingRound.objects.get(status=BIDDING_ROUND_STATUS_ACTIVE)
        today = get_today(cache={})
        current_period = (
            GrowingPeriod.objects.filter(start_date__lte=today, end_date__gte=today)
            .order_by("start_date")
            .first()
        )
        all_member_ids = set(
            Subscription.objects.filter(
                period=current_period,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
            ).values_list("member_id", flat=True)
        )
        pre_cancelled_member_ids = set(
            Subscription.objects.filter(
                period=current_period,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
                cancellation_ts__lt=active_round.start_at,
            ).values_list("member_id", flat=True)
        )
        free_member_ids = set(
            Subscription.objects.filter(
                period=current_period,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
                cancellation_ts__gte=active_round.start_at,
            ).values_list("member_id", flat=True)
        )
        member_count = len(all_member_ids - pre_cancelled_member_ids)
        bid_member_ids = set(active_round.bids.values_list("member_id", flat=True))
        bidder_count = int(member_count * 0.6)
        free_count = member_count - bidder_count - int(member_count * 0.3)

        self.assertEqual(bidder_count, len(bid_member_ids))
        self.assertEqual(free_count, len(free_member_ids))
        self.assertTrue(bid_member_ids.isdisjoint(free_member_ids))
        self.assertTrue(bid_member_ids.issubset(all_member_ids))

    def test_generateAll_activeRoundUsesTheMiddleLevelAmount(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        levels_round = BiddingRound.objects.get(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
            bid_levels=3,
            status=BIDDING_ROUND_STATUS_CLOSED,
        )
        active_round = BiddingRound.objects.get(status=BIDDING_ROUND_STATUS_ACTIVE)
        active_bid = active_round.bids.select_related("member").first()
        levels_bid = Bid.objects.get(round=levels_round, member=active_bid.member)

        self.assertEqual(levels_bid.amount_2, active_bid.amount_1)

    def test_calibrateAmounts_fallsBackWhenTheTargetIsUnreachable(self, _count):
        assignments = [{"size": Decimal("1"), "quantity": 1, "factor": Decimal("1")}]
        amounts = bidding_round_generator.BiddingRoundGenerator._calibrate_amounts(
            assignments,
            fixed_per_year=Decimal("100.00"),
            target_amount_per_year=Decimal("1.00"),
            ratios=bidding_round_generator.SIMPLE_LEVEL_TARGET_RATIOS,
        )

        self.assertGreater(amounts[0][0], Decimal("0"))
        self.assertLess(amounts[0][0], amounts[0][1])
        self.assertLess(amounts[0][1], amounts[0][2])

    def test_generateAll_derivesTargetForNonVierlande(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        bidding_round = BiddingRound.objects.get(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )
        self.assertLess(
            BiddingRoundStatsService.get_target_per_year(bidding_round),
            bidding_round_generator.TARGET_AMOUNT_PER_YEAR,
        )
        reference_values = {
            price.product_id: price.reference_value
            for price in BiddingRoundProductPrice.objects.filter(round=bidding_round)
        }
        ratios = [
            (item.amount_1 + item.amount_2)
            / Decimal("2")
            / reference_values[item.product_id]
            for item in Bid.objects.filter(round=bidding_round).select_related(
                "product"
            )
        ]
        self.assertAlmostEqual(1.0, float(sum(ratios) / len(ratios)), delta=0.1)

    def test_generateAll_withoutAutomaticRenewalUsesNinetyPercentBidders(self, _count):
        DataGenerator.generate_all(Organization.WIRGARTEN)

        active_round = BiddingRound.objects.get(status=BIDDING_ROUND_STATUS_ACTIVE)
        today = get_today(cache={})
        current_period = (
            GrowingPeriod.objects.filter(start_date__lte=today, end_date__gte=today)
            .order_by("start_date")
            .first()
        )
        all_member_ids = set(
            Subscription.objects.filter(
                period=current_period,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
            ).values_list("member_id", flat=True)
        )
        pre_cancelled_member_ids = set(
            Subscription.objects.filter(
                period=current_period,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
                cancellation_ts__lt=active_round.start_at,
            ).values_list("member_id", flat=True)
        )
        member_count = len(all_member_ids - pre_cancelled_member_ids)
        evaluation = BiddingRoundStatsService.build_admin_evaluation(
            active_round, cache={}
        )

        self.assertEqual(int(member_count * 0.9), active_round.bids.count())
        self.assertEqual(0, len(evaluation["auto_renewed"]))

        bid_range_round = BiddingRound.objects.get(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )
        for level, expected in ((1, 81.0), (2, 101.0)):
            self.assertAlmostEqual(
                expected,
                self._admin_percent(bid_range_round, level),
                delta=1.0,
                msg=f"level {level}",
            )

    def test_generateAll_createsNoPeriodlessHarvestShareSubscriptions(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        self.assertFalse(
            Subscription.objects.filter(
                period__isnull=True,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
            ).exists()
        )

    def test_generateAll_setsRealisticCapacity(self, _count):
        DataGenerator.generate_all(Organization.BIOTOP)

        today = get_today(cache={})
        current_period = (
            GrowingPeriod.objects.filter(start_date__lte=today, end_date__gte=today)
            .order_by("start_date")
            .first()
        )
        product_type = ProductType.objects.get(name=HARVEST_SHARE_PRODUCT_TYPE_NAME)
        active_round = BiddingRound.objects.get(status=BIDDING_ROUND_STATUS_ACTIVE)
        total_shares = Decimal("0")
        for subscription in (
            Subscription.objects.filter(
                period=current_period, product__type=product_type
            )
            .exclude(cancellation_ts__lt=active_round.start_at)
            .select_related("product")
        ):
            product_price = get_product_price(
                product=subscription.product,
                reference_date=current_period.start_date,
                cache={},
            )
            size = (
                Decimal(str(product_price.size))
                if product_price is not None and product_price.size
                else Decimal("1")
            )
            total_shares += size * subscription.quantity
        expected_capacity = total_shares.to_integral_value(rounding=ROUND_CEILING)

        capacity = BiddingRoundStatsService.get_capacity_shares(active_round, cache={})

        self.assertEqual(expected_capacity, capacity)
        self.assertLess(capacity, Decimal("1000"))

    @pytest.mark.slow
    def test_generateAll_vierlandeIncludesDeliveryChargesAndWaivesMembership(
        self, _count
    ):
        with (
            patch.object(
                VierlandeGenerator, "HARVEST_SHARE_VARIANTS", VIERLANDE_SMALL_VARIANTS
            ),
            patch.object(
                VierlandeGenerator, "TOTAL_MEMBER_COUNT", VIERLANDE_SMALL_MEMBER_COUNT
            ),
        ):
            DataGenerator.generate_all(Organization.VIERLANDE)

        bidding_round = BiddingRound.objects.get(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE
        )
        for level, expected in ((1, 81.0), (2, 101.0)):
            self.assertAlmostEqual(
                expected,
                self._admin_percent(bidding_round, level),
                delta=1.0,
                msg=f"level {level}",
            )

        self.assertEqual(
            bidding_round_generator.TARGET_AMOUNT_PER_YEAR,
            BiddingRoundStatsService.get_target_per_year(bidding_round),
        )

        extra_positions = BiddingRoundStatsService.build_extra_positions(
            bidding_round, cache={}
        )
        self.assertGreater(
            extra_positions["delivery_charge"]["reached_per_year"], Decimal("0")
        )
        self.assertFalse(extra_positions["membership"]["applicable"])
        self.assertEqual(
            Decimal("0"), extra_positions["membership"]["reached_per_year"]
        )
        self.assertTrue(
            get_parameter_value(
                ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS,
                cache={},
            )
        )

        active_round = BiddingRound.objects.get(status=BIDDING_ROUND_STATUS_ACTIVE)
        today = get_today(cache={})
        current_period = (
            GrowingPeriod.objects.filter(start_date__lte=today, end_date__gte=today)
            .order_by("start_date")
            .first()
        )
        member_count = (
            Subscription.objects.filter(
                period=current_period,
                product__type__name=HARVEST_SHARE_PRODUCT_TYPE_NAME,
            )
            .values("member_id")
            .distinct()
            .count()
        )
        evaluation = BiddingRoundStatsService.build_admin_evaluation(
            active_round, cache={}
        )
        self.assertEqual(int(member_count * 0.6), active_round.bids.count())
        self.assertEqual(int(member_count * 0.3), len(evaluation["auto_renewed"]))
