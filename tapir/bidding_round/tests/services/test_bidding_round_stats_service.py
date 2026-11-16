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
from tapir.bidding_round.models import BiddingRoundCreatedSubscription
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
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


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

        self.assertEqual(
            Decimal("960.00"), Decimal(evaluation["auto_renewed_per_year"])
        )
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

    def test_buildExtraPositions_membershipFeeWaivedWithProducts_isNotApplicable(
        self,
    ):
        ParameterDefinitions().import_definitions(bulk_create=True)
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(
            ParameterKeys.ASSOCIATIONS_MEMBERSHIP_FEE_WAIVED_WITH_PRODUCTS, True
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
        projection = BiddingRoundStatsService.build_financing_projection(
            bidding_round, cache={}
        )

        self.assertFalse(positions["membership"]["applicable"])
        self.assertEqual(Decimal("0"), positions["membership"]["reached_per_year"])
        self.assertEqual(Decimal("0"), projection["membership_per_year"])

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

    def test_buildNonBidderRatePerShare_withSurchargeOnAverage_appliesSurcharge(self):
        bidding_round = BiddingRoundFactory.create(
            average_bid_locked_at=get_now(cache={}),
            locked_surcharge_percent=Decimal("10"),
            locked_surcharge_on_average=True,
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type, product=product, size=1
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            amount_1=Decimal("80.00"),
        )

        rate = BiddingRoundStatsService.build_non_bidder_rate_per_share(
            bidding_round, cache={}
        )

        self.assertEqual(Decimal("88.00"), rate)

    def test_buildNonBidderRatePerShare_afterLock_usesLockedValue(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        bidding_round.average_bid_locked_at = get_now(cache={})
        bidding_round.locked_bidder_average_per_share_per_month = Decimal("42.00")
        bidding_round.save()

        self.assertEqual(
            Decimal("42.00"),
            BiddingRoundStatsService.build_non_bidder_rate_per_share(
                bidding_round, cache={}
            ),
        )

    def test_getBidderAveragePerSharePerMonth_afterLock_usesLockedValue(self):
        bidding_round = BiddingRoundFactory.create()
        BiddingRoundProductTypeFactory.create(round=bidding_round)
        bidding_round.average_bid_locked_at = get_now(cache={})
        bidding_round.locked_bidder_average_per_share_per_month = Decimal("42.00")
        bidding_round.save()

        self.assertEqual(
            Decimal("42.00"),
            BiddingRoundStatsService.get_bidder_average_per_share_per_month(
                bidding_round, cache={}
            ),
        )

    def test_buildLockedAverageBid_surchargeOnBids_capsAtRed(self):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type, product=product, size=1
        )
        ProductPriceFactory.create(
            product=product,
            size=1,
            valid_from=bidding_round.growing_period.start_date,
        )
        BidItemFactory.create(
            bid=BidFactory.create(round=bidding_round),
            round_product_type=round_product_type,
            product=product,
            amount_1=Decimal("70.00"),
            amount_2=Decimal("90.00"),
        )

        locked = BiddingRoundStatsService.build_locked_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=50,
            surcharge_on_bids=True,
            surcharge_on_average=False,
            cache={},
        )

        self.assertEqual(Decimal("90.00"), locked["bidder_amount_per_share_per_month"])

    def test_getAutoRenewedSubscriptions_withRenewingAndCreatedLinks_returnsOnlyNonBidders(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        renewing = self._create_subscription(
            member=MemberFactory.create(), product=product, round=bidding_round
        )
        created_non_bidder = self._create_subscription(
            member=MemberFactory.create(), product=product, round=bidding_round
        )
        BiddingRoundCreatedSubscription.objects.create(
            round=bidding_round,
            subscription=created_non_bidder,
            is_bidder_contract=False,
        )
        created_bidder = self._create_subscription(
            member=MemberFactory.create(), product=product, round=bidding_round
        )
        BiddingRoundCreatedSubscription.objects.create(
            round=bidding_round,
            subscription=created_bidder,
            is_bidder_contract=True,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={renewing},
        ):
            subscriptions = BiddingRoundStatsService.get_auto_renewed_subscriptions(
                bidding_round, cache={}
            )

        subscription_ids = {subscription.id for subscription in subscriptions}
        self.assertIn(renewing.id, subscription_ids)
        self.assertIn(created_non_bidder.id, subscription_ids)
        self.assertNotIn(created_bidder.id, subscription_ids)

    def test_getAutoRenewedByMember_withRenewingSubscription_returnsFullDetails(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        self._create_product_price(product, bidding_round, size=1)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
            reference_value=Decimal("90.00"),
        )
        pickup_location = PickupLocationFactory.create(name="Hof Nord")
        auto_member = MemberFactory.create(email="auto@example.com")
        MemberPickupLocationFactory.create(
            member=auto_member,
            pickup_location=pickup_location,
            valid_from=bidding_round.growing_period.start_date
            - datetime.timedelta(days=1),
        )
        renewing = self._create_subscription(
            member=auto_member,
            product=product,
            round=bidding_round,
            quantity=2,
        )
        bidder = MemberFactory.create()
        bidder_renewing = self._create_subscription(
            member=bidder, product=product, round=bidding_round
        )
        BidFactory.create(round=bidding_round, member=bidder)

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={renewing, bidder_renewing},
        ):
            result = BiddingRoundStatsService.get_auto_renewed_by_member(
                bidding_round, cache={}
            )

        self.assertNotIn(bidder.id, result)
        entry = result[auto_member.id]
        self.assertEqual("auto@example.com", entry["member_email"])
        self.assertEqual(pickup_location.id, entry["pickup_location_id"])
        self.assertEqual("Hof Nord", entry["pickup_location_name"])
        self.assertEqual(Decimal("2"), entry["shares"])
        self.assertEqual(Decimal("2160.00"), entry["euro_per_year"])
        self.assertEqual(Decimal("180"), entry["euro_per_month"])
        self.assertEqual(
            [
                {
                    "product_type_name": product.type.name,
                    "product_name": product.name,
                    "quantity": 2,
                }
            ],
            entry["items"],
        )
        self.assertEqual(entry["euro_per_month"], entry["monthly_reference"])
        self.assertEqual(entry["euro_per_year"], entry["yearly_reference"])

    def test_buildFinancingProjection_withBidAndCapacity_returnsSharesAndLevels(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        self._create_product_price(product, bidding_round, size=1)
        ProductCapacityFactory.create(
            period=bidding_round.growing_period,
            product_type=round_product_type.product_type,
            capacity=10,
        )
        self._create_item_for(
            bidding_round=bidding_round,
            round_product_type=round_product_type,
            product=product,
            quantity=1,
            amount_1=Decimal("80.00"),
        )

        projection = BiddingRoundStatsService.build_financing_projection(
            bidding_round, cache={}
        )

        self.assertEqual(Decimal("1000.00"), projection["target_per_year"])
        self.assertEqual(Decimal("10.00"), projection["capacity_shares"])
        self.assertEqual(Decimal("1"), projection["bid_shares"])
        self.assertEqual(Decimal("9"), projection["remaining_shares"])
        self.assertEqual(Decimal("0"), projection["fixed_per_year"])
        self.assertEqual(
            Decimal("960.00"), projection["levels"]["green"]["reached_per_year"]
        )
        self.assertEqual(
            Decimal("80.00"),
            projection["levels"]["green"]["average_per_share_per_month"],
        )
        self.assertFalse(projection["membership_included_in_product_type"])

    def test_buildStatsAndTotals_withBid_returnsCoverageAndShares(self):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        self._create_product_price(product, bidding_round, size=1)
        ProductCapacityFactory.create(
            period=bidding_round.growing_period,
            product_type=round_product_type.product_type,
            capacity=10,
        )
        self._create_item_for(
            bidding_round=bidding_round,
            round_product_type=round_product_type,
            product=product,
            quantity=1,
            amount_1=Decimal("80.00"),
        )

        stats = BiddingRoundStatsService.build_stats(bidding_round, cache={})

        self.assertEqual(1, len(stats))
        entry = stats[0]
        self.assertEqual(Decimal("1000.00"), entry["target_per_year"])
        self.assertEqual(Decimal("960.00"), entry["reached_per_year"])
        self.assertEqual(96.0, entry["percent"])
        self.assertEqual(Decimal("40.00"), entry["deficit"])
        self.assertEqual("yellow", entry["coverage_status"])
        self.assertEqual(Decimal("10.00"), entry["target_shares"])
        self.assertEqual(Decimal("1"), entry["reached_shares"])
        self.assertEqual(10.0, entry["shares_percent"])
        self.assertEqual(Decimal("9.00"), entry["shares_deficit"])
        self.assertEqual("red", entry["shares_coverage_status"])

        totals = BiddingRoundStatsService.build_totals(
            stats, extra_reached_per_year=Decimal("40.00")
        )

        self.assertEqual(Decimal("1000.00"), totals["reached_per_year"])
        self.assertEqual(100.0, totals["percent"])
        self.assertIsNone(totals["deficit"])
        self.assertEqual("green", totals["coverage_status"])

        average_bid = BiddingRoundStatsService.build_average_bid(
            bidding_round, cache={}
        )

        self.assertEqual(Decimal("1000.00"), average_bid["target_per_year"])
        self.assertEqual(Decimal("10.00"), average_bid["capacity_shares"])
        self.assertEqual(Decimal("80.00"), average_bid["amount_per_share_per_month"])
        self.assertEqual(Decimal("960.00"), average_bid["amount_per_share_per_year"])

    def test_buildResultsTable_withBidAutoRenewedAndInactiveMember_marksEachMember(
        self,
    ):
        bidding_round = BiddingRoundFactory.create()
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        self._create_product_price(product, bidding_round, size=1)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
            reference_value=Decimal("80.00"),
        )
        pickup_location = PickupLocationFactory.create(name="Hof Süd")
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type=round_product_type.product_type,
            max_capacity=10,
        )
        bid_member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=bid_member,
            pickup_location=pickup_location,
            valid_from=bidding_round.growing_period.start_date
            - datetime.timedelta(days=1),
        )
        bid = BidFactory.create(round=bidding_round, member=bid_member)
        self._create_item_for(
            bidding_round=bidding_round,
            round_product_type=round_product_type,
            product=product,
            bid=bid,
            quantity=2,
            amount_1=Decimal("80.00"),
        )
        active_member = MemberFactory.create()
        self._create_subscription(
            member=active_member, product=product, round=bidding_round
        )
        auto_member = MemberFactory.create()
        auto_subscription = self._create_subscription(
            member=auto_member, product=product, round=bidding_round
        )
        inactive_member = MemberFactory.create()

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={auto_subscription},
        ):
            table = BiddingRoundStatsService.build_results_table(
                bidding_round, cache={}
            )

        members_by_id = {entry["member"].id: entry for entry in table["members"]}
        self.assertTrue(members_by_id[bid_member.id]["has_bid"])
        self.assertTrue(members_by_id[bid_member.id]["is_active_in_contract_period"])
        self.assertTrue(members_by_id[active_member.id]["is_active_in_contract_period"])
        self.assertFalse(members_by_id[inactive_member.id]["has_bid"])
        self.assertFalse(
            members_by_id[inactive_member.id]["is_active_in_contract_period"]
        )
        self.assertTrue(members_by_id[auto_member.id]["is_auto_renewed"])
        self.assertEqual(
            [
                {
                    "product_type_name": product.type.name,
                    "product_name": product.name,
                    "quantity": 1,
                }
            ],
            members_by_id[auto_member.id]["auto_renewed_items"],
        )
        self.assertEqual(
            Decimal("960.00"),
            members_by_id[auto_member.id]["auto_renewed_amount_per_year"],
        )
        self.assertEqual(
            Decimal("80.00"),
            members_by_id[auto_member.id]["auto_renewed_amount_per_month"],
        )

        pickup_entries = {
            entry["pickup_location"].id: entry for entry in table["pickup_locations"]
        }
        self.assertEqual(Decimal("10"), pickup_entries[pickup_location.id]["capacity"])
        self.assertEqual(Decimal("2"), pickup_entries[pickup_location.id]["demand"])
        self.assertEqual(20.0, pickup_entries[pickup_location.id]["fill_percent"])

    def test_buildAdminEvaluation_returnsAcceptanceFieldsAndEffectiveBidAmounts(
        self,
    ):
        bidding_round = BiddingRoundFactory.create(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        self._create_product_price(product, bidding_round, size=1)
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
            reference_value=Decimal("80.00"),
        )
        bid_member = MemberFactory.create()
        self._create_item_for(
            bidding_round=bidding_round,
            round_product_type=round_product_type,
            product=product,
            amount_1=Decimal("70.00"),
            amount_2=Decimal("90.00"),
        )
        auto_member = MemberFactory.create()
        auto_subscription = self._create_subscription(
            member=auto_member, product=product, round=bidding_round
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={auto_subscription},
        ):
            evaluation = BiddingRoundStatsService.build_admin_evaluation(
                bidding_round, cache={}, bid_range_position=100
            )

        self.assertTrue(
            {
                "display_name",
                "stats",
                "totals",
                "average_bid",
                "auto_renewed_enabled",
                "financing_projection",
                "results_table",
                "biddable_product",
                "pickup_locations",
                "bid_options",
                "contracts_created_at",
                "growing_period_id",
                "contracts",
            }.issubset(set(evaluation))
        )
        self.assertEqual(100.0, evaluation["bid_range_position"])
        self.assertEqual("90.00", evaluation["bids"][0]["effective_amount"])
        self.assertEqual("1080.00", evaluation["bids"][0]["amount_per_year"])
        self.assertIsNone(evaluation["bids"][0]["pickup_location_name"])
        auto_entry = evaluation["auto_renewed"][0]
        self.assertTrue(
            {
                "items",
                "pickup_location_id",
                "pickup_location_name",
                "shares",
                "euro_per_year",
                "euro_per_month",
                "member_email",
            }.issubset(set(auto_entry))
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={auto_subscription},
        ):
            evaluation_without_auto_renewed = (
                BiddingRoundStatsService.build_admin_evaluation(
                    bidding_round, cache={}, include_auto_renewed=False
                )
            )

        self.assertEqual([], evaluation_without_auto_renewed["auto_renewed"])
        self.assertEqual("0", evaluation_without_auto_renewed["auto_renewed_per_year"])

    @staticmethod
    def _create_product_price(product, bidding_round, size=1):
        ProductPriceFactory.create(
            product=product,
            size=size,
            valid_from=bidding_round.growing_period.start_date
            - datetime.timedelta(days=1),
        )

    @staticmethod
    def _create_subscription(member, product, round, quantity=1):
        return SubscriptionFactory.create(
            member=member,
            product=product,
            period=round.growing_period,
            quantity=quantity,
            start_date=round.growing_period.start_date,
            end_date=round.growing_period.end_date,
        )

    @staticmethod
    def _create_item_for(
        bidding_round,
        round_product_type,
        product,
        bid=None,
        quantity=1,
        **amounts,
    ):
        bid = bid or BidFactory.create(round=bidding_round)
        return BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            quantity=quantity,
            **amounts,
        )
