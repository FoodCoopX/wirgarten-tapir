import datetime
from decimal import Decimal
from unittest.mock import patch

from tapir.associations.tests.factories import (
    AssociationMembershipTypeFactory,
    AssociationMembershipTypePriceFactory,
)
from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
)
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberPickupLocationFactory,
    MemberFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
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
            0.0, BiddingRoundStatsService.get_coverage_percent(bidding_round, cache={})
        )

    def test_bidderAverage_withoutBids_returnsZero(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)

        self.assertEqual(
            Decimal("0"),
            BiddingRoundStatsService.get_bidder_average_per_month(
                bidding_round, cache={}
            ),
        )

    def _create_bid_item(self, bidding_round, **amounts):
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        bid = BidFactory.create(round=bidding_round)
        return BidItemFactory.create(
            bid=bid, round_product_type=round_product_type, **amounts
        )

    def test_getAmountForPosition_bidRange_interpolatesBetweenLevels(self):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        item = self._create_bid_item(
            bidding_round,
            amount_1=Decimal("70.00"),
            amount_2=Decimal("90.00"),
        )

        for position, expected in (
            (0, Decimal("70.00")),
            (25, Decimal("75.00")),
            (50, Decimal("80.00")),
            (75, Decimal("85.00")),
            (100, Decimal("90.00")),
        ):
            self.assertEqual(
                expected,
                BiddingRoundStatsService.get_amount_for_position(
                    item, position, bidding_round
                ),
            )

    def test_getAmountForPosition_bidRangeWithZeroGreen_keepsZero(self):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        item = self._create_bid_item(
            bidding_round,
            amount_1=Decimal("0.00"),
            amount_2=Decimal("90.00"),
        )

        self.assertEqual(
            Decimal("0.00"),
            BiddingRoundStatsService.get_amount_for_position(item, 0, bidding_round),
        )
        self.assertEqual(
            Decimal("45.00"),
            BiddingRoundStatsService.get_amount_for_position(item, 50, bidding_round),
        )

    def test_getAmountForPosition_simpleWithoutFurtherLevels_repeatsTheAmount(self):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE, bid_levels=1
        )
        item = self._create_bid_item(bidding_round, amount_1=Decimal("80.00"))

        for position in (0, 50, 100):
            self.assertEqual(
                Decimal("80.00"),
                BiddingRoundStatsService.get_amount_for_position(
                    item, position, bidding_round
                ),
            )

    def test_clampPosition_invalidValue_fallsBackToMiddle(self):
        self.assertEqual(
            Decimal("50"), BiddingRoundStatsService.clamp_position("not-a-number")
        )

    def test_recommendedLevel_bidRange_returnsSecondLevelAndMiddlePosition(self):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )

        self.assertEqual(
            2, BiddingRoundStatsService.get_recommended_level(bidding_round, cache={})
        )
        self.assertEqual(
            Decimal("50"),
            BiddingRoundStatsService.get_default_position(bidding_round, cache={}),
        )

    def _create_three_level_round(self, amounts):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE, bid_levels=3
        )
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            amount_1=amounts[0],
            amount_2=amounts[1],
            amount_3=amounts[2],
        )
        return bidding_round

    def test_recommendedLevel_simpleWithThreeLevels_returnsSecondLevel(self):
        bidding_round = self._create_three_level_round(
            (Decimal("60.00"), Decimal("90.00"), Decimal("120.00"))
        )

        self.assertEqual(
            2, BiddingRoundStatsService.get_recommended_level(bidding_round, cache={})
        )
        self.assertEqual(
            Decimal("50"),
            BiddingRoundStatsService.get_default_position(bidding_round, cache={}),
        )

    def test_recommendedLevel_simpleWithThreeLevels_returnsThirdLevel(self):
        bidding_round = self._create_three_level_round(
            (Decimal("60.00"), Decimal("70.00"), Decimal("80.00"))
        )

        self.assertEqual(
            3, BiddingRoundStatsService.get_recommended_level(bidding_round, cache={})
        )
        self.assertEqual(
            Decimal("100"),
            BiddingRoundStatsService.get_default_position(bidding_round, cache={}),
        )

    def test_recommendedLevel_simpleWithThreeLevels_returnsFirstLevel(self):
        bidding_round = self._create_three_level_round(
            (Decimal("100.00"), Decimal("110.00"), Decimal("120.00"))
        )

        self.assertEqual(
            1, BiddingRoundStatsService.get_recommended_level(bidding_round, cache={})
        )
        self.assertEqual(
            Decimal("0"),
            BiddingRoundStatsService.get_default_position(bidding_round, cache={}),
        )

    def test_buildLevelsEvaluation_bidRange_includesGreenAndRed(self):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            amount_1=Decimal("60.00"),
            amount_2=Decimal("120.00"),
        )

        levels = BiddingRoundStatsService.build_levels_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual({"green", "red"}, set(levels))
        self.assertEqual("red", levels["green"]["coverage_status"])
        self.assertEqual("green", levels["red"]["coverage_status"])

    def test_buildLevelsEvaluation_simpleWithThreeLevels_usesLevelPositions(self):
        bidding_round = self._create_three_level_round(
            (Decimal("60.00"), Decimal("90.00"), Decimal("120.00"))
        )

        levels = BiddingRoundStatsService.build_levels_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual(72.0, levels["green"]["coverage_percent"])
        self.assertEqual(108.0, levels["yellow"]["coverage_percent"])
        self.assertEqual(144.0, levels["red"]["coverage_percent"])

    def test_buildPublicEvaluation_withSeveralShares_countsQuantity(self):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type, product=product, size=1
        )
        ProductPriceFactory.create(product=product, size=1)
        ProductCapacityFactory.create(
            period=bidding_round.growing_period,
            product_type=round_product_type.product_type,
            capacity=4,
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            quantity=2,
            amount_1=Decimal("80.00"),
        )

        evaluation = BiddingRoundStatsService.build_public_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual(Decimal("2"), Decimal(evaluation["current_shares"]))
        self.assertEqual(50.0, evaluation["utilization_percent"])

    def test_autoRenewed_includedInCoverage(self):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
            reference_value=Decimal("80.00"),
            min_amount=Decimal("60.00"),
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            amount_1=Decimal("80.00"),
        )
        auto_renewed_subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            product=product,
            period=bidding_round.growing_period,
            quantity=1,
            start_date=bidding_round.growing_period.start_date,
            end_date=bidding_round.growing_period.end_date,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={auto_renewed_subscription},
        ):
            evaluation = BiddingRoundStatsService.build_admin_evaluation(
                bidding_round, cache={}
            )

        self.assertEqual("960.00", evaluation["auto_renewed_per_year"])
        self.assertEqual(1, len(evaluation["auto_renewed"]))
        self.assertEqual(192.0, evaluation["coverage_percent"])
        self.assertEqual("80.00", evaluation["non_bidder_rate_per_share"])

    def test_buildPublicEvaluation_containsOnlyAggregates(self):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        member = MemberFactory.create()
        bid = BidFactory.create(round=bidding_round, member=member)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            amount_1=Decimal("80.00"),
        )

        public = BiddingRoundStatsService.build_public_evaluation(
            bidding_round, cache={}
        )

        self.assertEqual(
            {
                "bidding_procedure",
                "bid_levels",
                "recommended_level",
                "bid_range_position",
                "coverage_status",
                "target_per_year",
                "capacity_shares",
                "current_shares",
                "utilization_percent",
                "coverage_percent",
                "bidder_average_per_month",
                "levels",
            },
            set(public),
        )
        self.assertNotIn(str(member), str(public))

    def test_includeAutoRenewedFalse_excludesAutoRenewedMembers(self):
        bidding_round = BiddingRoundFactory.create(include_auto_renewed=False)
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            amount_1=Decimal("80.00"),
        )
        auto_renewed_subscription = SubscriptionFactory.create(
            member=MemberFactory.create(),
            product=product,
            period=bidding_round.growing_period,
            quantity=1,
            start_date=bidding_round.growing_period.start_date,
            end_date=bidding_round.growing_period.end_date,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={auto_renewed_subscription},
        ):
            evaluation = BiddingRoundStatsService.build_admin_evaluation(
                bidding_round, cache={}
            )

        self.assertEqual("0", evaluation["auto_renewed_per_year"])
        self.assertEqual([], evaluation["auto_renewed"])

    def test_buildExtraPositions_membership_appliesAssociationPrice(self):
        ParameterDefinitions().import_definitions(bulk_create=True)
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        membership_type = AssociationMembershipTypeFactory.create(
            order_in_bestell_wizard=-1
        )
        AssociationMembershipTypePriceFactory.create(
            type=membership_type,
            valid_from=bidding_round.growing_period.start_date,
            price=Decimal("5.00"),
        )
        BidFactory.create(round=bidding_round)

        positions = BiddingRoundStatsService.build_extra_positions(
            bidding_round, cache={}
        )

        self.assertTrue(positions["membership"]["applicable"])
        self.assertEqual(Decimal("60.00"), positions["membership"]["reached_per_year"])

    def test_buildExtraPositions_deliveryCharge_sumsTheBids(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        pickup_location = PickupLocationFactory.create()
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=bidding_round.growing_period.start_date
            - datetime.timedelta(days=1),
        )
        BidFactory.create(round=bidding_round, member=member)

        with patch.object(
            BiddingRoundDeliveryChargeService,
            "get_yearly_delivery_charge",
            return_value=Decimal("12.00"),
        ):
            positions = BiddingRoundStatsService.build_extra_positions(
                bidding_round, cache={}
            )

        self.assertTrue(positions["delivery_charge"]["applicable"])
        self.assertEqual(
            Decimal("12.00"), positions["delivery_charge"]["reached_per_year"]
        )
