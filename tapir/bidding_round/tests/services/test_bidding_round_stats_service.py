from decimal import Decimal
from unittest.mock import MagicMock, patch

from tapir.associations.tests.factories import (
    AssociationMembershipTypeFactory,
    AssociationMembershipTypePriceFactory,
)
from tapir.bidding_round.services.bidding_round_delivery_charge_service import (
    BiddingRoundDeliveryChargeService,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.factories import (
    BiddingRoundProductFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundStatsService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_buildStats_perProduct_calculatesTargetReachedPercentAndDeficit(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="50.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        self.assertEqual(Decimal("1000.00"), stats[0]["target_per_year"])
        self.assertEqual(Decimal("600.00"), stats[0]["reached_per_year"])
        self.assertEqual(60.0, stats[0]["percent"])
        self.assertEqual(Decimal("400.00"), stats[0]["deficit"])

    def test_buildStats_traffic_lightIndicator_greenWhen100Percent(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="100.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        self.assertEqual("green", stats[0]["traffic_light"])

    def test_buildStats_traffic_lightIndicator_yellowWhen90to99Percent(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1200.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="95.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        self.assertEqual(95.0, stats[0]["percent"])
        self.assertEqual("yellow", stats[0]["traffic_light"])

    def test_buildStats_traffic_lightPosition_interpolatesBetweenGreenYellowRed(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="60.00",
                    amount_2="80.00",
                    amount_3="100.00",
                )
            ],
            cache={},
        )

        def reached(position):
            return BiddingRoundStatsService.build_stats(
                round_,
                include_auto_renewed=False,
                traffic_light_position=position,
                cache={},
            )[0]["reached_per_year"]

        self.assertEqual(Decimal("720.00"), reached(0))  # green
        self.assertEqual(Decimal("840.00"), reached(25))  # 1/2 between green/yellow
        self.assertEqual(Decimal("960.00"), reached(50))  # zufrieden
        self.assertEqual(Decimal("1080.00"), reached(75))  # 1/2 zwischen gelb/rot
        self.assertEqual(Decimal("1200.00"), reached(100))  # rot

    def test_buildStats_traffic_lightPositionGreen_withoutGreenAmount_fallsBackToYellow(
        self,
    ):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, traffic_light_position=0, cache={}
        )

        self.assertEqual(Decimal("960.00"), stats[0]["reached_per_year"])

    def test_buildStats_traffic_lightPositionOutOfRange_isClamped(self):
        round_ = create_open_round(bid_levels=2)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="60.00", amount_2="80.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, traffic_light_position=999, cache={}
        )

        self.assertEqual(Decimal("960.00"), stats[0]["reached_per_year"])

    def test_buildAverageBid_noBids_usesTargetPerCapacity(self):
        round_ = create_open_round()
        create_round_product_with_product(
            round_,
            target_amount_per_year=Decimal("220800.00"),
            capacity=230,
        )

        average_bid = BiddingRoundStatsService.build_average_bid(round_, cache={})

        self.assertEqual(Decimal("220800.00"), average_bid["target_per_year"])
        self.assertEqual(Decimal("230"), average_bid["capacity_shares"])
        self.assertEqual(Decimal("80.00"), average_bid["amount_per_share_per_month"])
        self.assertEqual(Decimal("960.00"), average_bid["amount_per_share_per_year"])

    def test_buildAverageBid_usesShareWeightedAverageOfBids(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("220800.00")
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="100.00")],
            cache={},
        )

        average_bid = BiddingRoundStatsService.build_average_bid(round_, cache={})

        self.assertEqual(Decimal("90.00"), average_bid["amount_per_share_per_month"])
        self.assertEqual(Decimal("1080.00"), average_bid["amount_per_share_per_year"])

    def test_buildFinancingProjection_returnsAnchorsAndShares(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("220800.00"), capacity=230
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="60.00",
                    amount_2="80.00",
                    amount_3="100.00",
                )
            ],
            cache={},
        )

        projection = BiddingRoundStatsService.build_financing_projection(
            round_, cache={}
        )

        self.assertEqual(Decimal("220800.00"), projection["target_per_year"])
        self.assertEqual(Decimal("230"), projection["capacity_shares"])
        self.assertEqual(Decimal("1"), projection["bid_shares"])
        self.assertEqual(Decimal("229"), projection["remaining_shares"])
        self.assertEqual(
            Decimal("720.00"), projection["levels"]["green"]["reached_per_year"]
        )
        self.assertEqual(
            Decimal("960.00"), projection["levels"]["yellow"]["reached_per_year"]
        )
        self.assertEqual(
            Decimal("1200.00"), projection["levels"]["red"]["reached_per_year"]
        )
        self.assertEqual(
            Decimal("80.00"),
            projection["levels"]["yellow"]["average_per_share_per_month"],
        )

    def test_buildFinancingProjection_membershipIncluded_hasNoMembershipPosition(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)

        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipTypePriceFactory.create(
            type=membership_type,
            price=Decimal("10.00"),
            valid_from=round_.growing_period.start_date,
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )

        projection = BiddingRoundStatsService.build_financing_projection(
            round_, membership_included_in_product_type=True, cache={}
        )

        self.assertEqual(Decimal("0"), projection["membership_per_year"])

    def test_buildAverageBid_zeroCapacity_returnsNoneAmounts(self):
        round_ = create_open_round()
        BiddingRoundProductFactory.create(round=round_)

        average_bid = BiddingRoundStatsService.build_average_bid(round_, cache={})

        self.assertIsNone(average_bid["amount_per_share_per_month"])
        self.assertIsNone(average_bid["amount_per_share_per_year"])

    def test_buildExtraPositionsMembership_notApplicableForCooperative(self):
        round_ = create_open_round()
        create_round_product_with_product(round_)

        positions = BiddingRoundStatsService.build_extra_positions(round_, cache={})

        self.assertFalse(positions["membership"]["applicable"])
        self.assertEqual(Decimal("0"), positions["membership"]["reached_per_year"])

    def test_buildExtraPositionsMembership_forAssociation_sumsPriceOverBids(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)

        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipTypePriceFactory.create(
            type=membership_type,
            price=Decimal("10.00"),
            valid_from=round_.growing_period.start_date,
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )

        positions = BiddingRoundStatsService.build_extra_positions(round_, cache={})

        self.assertTrue(positions["membership"]["applicable"])
        self.assertEqual(Decimal("240.00"), positions["membership"]["reached_per_year"])

    @patch.object(
        BiddingRoundDeliveryChargeService,
        "get_yearly_delivery_charge",
        return_value=Decimal("78.00"),
    )
    def test_buildExtraPositions_deliveryCharge_sumsOverBids(self, mock_charge):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )

        positions = BiddingRoundStatsService.build_extra_positions(round_, cache={})

        self.assertTrue(positions["delivery_charge"]["applicable"])
        self.assertEqual(
            Decimal("156.00"), positions["delivery_charge"]["reached_per_year"]
        )

    def test_buildExtraPositions_deliveryCharge_noCharge_notApplicable(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )

        positions = BiddingRoundStatsService.build_extra_positions(round_, cache={})

        self.assertFalse(positions["delivery_charge"]["applicable"])

    def test_buildExtraPositions_membershipIncludedInProductType_notApplicable(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)

        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipTypePriceFactory.create(
            type=membership_type,
            price=Decimal("10.00"),
            valid_from=round_.growing_period.start_date,
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product)],
            cache={},
        )

        positions = BiddingRoundStatsService.build_extra_positions(
            round_, membership_included_in_product_type=True, cache={}
        )

        self.assertFalse(positions["membership"]["applicable"])

    def test_buildTotals_addsExtraReachedPerYear(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="50.00")],
            cache={},
        )
        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        totals = BiddingRoundStatsService.build_totals(
            stats, extra_reached_per_year=Decimal("200.00")
        )

        self.assertEqual(Decimal("800.00"), totals["reached_per_year"])
        self.assertEqual(80.0, totals["percent"])

    def test_buildStats_traffic_lightIndicator_redBelow90Percent(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1200.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        self.assertEqual(80.0, stats[0]["percent"])
        self.assertEqual("red", stats[0]["traffic_light"])

    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    def test_buildStats_includeAutoRenewed_addsReferenceValuesForNonBidders(
        self, mock_get_subscriptions
    ):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_,
            reference_value=Decimal("70.00"),
            target_amount_per_year=Decimal("1000.00"),
        )
        auto_renewed_member = MemberFactory.create()
        auto_renewed_product = ProductFactory.create(type=round_product.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product=round_product,
            product=auto_renewed_product,
            reference_value=Decimal("70.00"),
        )
        subscription = SubscriptionFactory.create(
            member=auto_renewed_member,
            product=auto_renewed_product,
            quantity=1,
        )
        mock_get_subscriptions.return_value = {subscription}

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=True, cache={}
        )

        self.assertEqual(Decimal("840.00"), stats[0]["reached_per_year"])
        self.assertEqual(Decimal("1"), stats[0]["reached_shares"])

    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    def test_buildStats_excludeAutoRenewed_ignoresNonBidders(
        self, mock_get_subscriptions
    ):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_,
            reference_value=Decimal("70.00"),
            target_amount_per_year=Decimal("1000.00"),
        )
        auto_renewed_member = MemberFactory.create()
        auto_renewed_product = ProductFactory.create(type=round_product.product_type)
        subscription = SubscriptionFactory.create(
            member=auto_renewed_member,
            product=auto_renewed_product,
            quantity=1,
        )
        mock_get_subscriptions.return_value = {subscription}

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        self.assertEqual(Decimal("0.00"), stats[0]["reached_per_year"])

    def test_buildPublicStats_aggregatesOnly_noMemberData(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="50.00")],
            cache={},
        )

        public_stats = BiddingRoundStatsService.build_public_stats(round_, cache={})

        self.assertIsInstance(public_stats, list)
        self.assertEqual(1, len(public_stats))
        self.assertNotIn("members", public_stats[0])
        self.assertNotIn("member", public_stats[0])
        self.assertEqual(Decimal("600.00"), public_stats[0]["reached_per_year"])

    def test_buildStats_includesTargetAndReachedShares(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=2,
            valid_from=round_.growing_period.start_date,
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, quantity=2, amount_1="50.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )

        self.assertEqual(Decimal("100"), stats[0]["target_shares"])
        self.assertEqual(Decimal("4"), stats[0]["reached_shares"])
        self.assertEqual(4.0, stats[0]["shares_percent"])
        self.assertEqual(Decimal("96"), stats[0]["shares_deficit"])

    def test_buildTotals_sumsEuroAndShares(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("3000.00"), capacity=150
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="50.00")],
            cache={},
        )

        stats = BiddingRoundStatsService.build_stats(
            round_, include_auto_renewed=False, cache={}
        )
        totals = BiddingRoundStatsService.build_totals(stats)

        self.assertEqual(Decimal("3000.00"), totals["target_per_year"])
        self.assertEqual(Decimal("600.00"), totals["reached_per_year"])
        self.assertEqual(Decimal("150"), totals["target_shares"])
        self.assertEqual(Decimal("1"), totals["reached_shares"])
        self.assertEqual(20.0, totals["percent"])
        self.assertEqual(0.6667, round(totals["shares_percent"], 4))

    def test_buildResultsTable_listsMembersWithBidStatus(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        member_with_bid = MemberFactory.create()
        member_without_bid = MemberFactory.create()
        BiddingRoundService.save_bid(
            member_with_bid, round_, [build_item(round_product, product)], cache={}
        )

        table = BiddingRoundStatsService.build_results_table(round_, cache={})

        members_by_id = {entry["member"].id: entry for entry in table["members"]}
        self.assertTrue(members_by_id[member_with_bid.id]["has_bid"])
        self.assertFalse(members_by_id[member_without_bid.id]["has_bid"])

    def test_buildResultsTable_autoRenewedMember_marksReferenceAmount(self):
        round_ = create_open_round()
        round_.include_auto_renewed = True
        round_.save()
        round_product, product = create_round_product_with_product(
            round_, reference_value=Decimal("10.00")
        )
        member = MemberFactory.create()
        subscription = MagicMock(member_id=member.id, quantity=2, product=product)

        with (
            patch.object(
                AutomaticSubscriptionRenewalService,
                "get_subscriptions_that_will_be_renewed",
                return_value={subscription},
            ),
            patch.object(
                BiddingRoundStatsService,
                "_get_product_size",
                return_value=Decimal("1"),
            ),
        ):
            table = BiddingRoundStatsService.build_results_table(round_, cache={})

        entry = next(
            entry for entry in table["members"] if entry["member"].id == member.id
        )
        self.assertTrue(entry["is_auto_renewed"])
        self.assertEqual(Decimal("240.00"), entry["auto_renewed_amount_per_year"])
        self.assertEqual(Decimal("20.00"), entry["auto_renewed_amount_per_month"])

    def test_buildResultsTable_autoRenewedDisabled_marksNoAutoRenewed(self):
        round_ = create_open_round()
        round_.include_auto_renewed = False
        round_.save()
        round_product, product = create_round_product_with_product(
            round_, reference_value=Decimal("10.00")
        )
        member = MemberFactory.create()
        subscription = MagicMock(member_id=member.id, quantity=2, product=product)

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={subscription},
        ):
            table = BiddingRoundStatsService.build_results_table(round_, cache={})

        entry = next(
            entry for entry in table["members"] if entry["member"].id == member.id
        )
        self.assertFalse(entry["is_auto_renewed"])
        self.assertIsNone(entry["auto_renewed_amount_per_year"])

    def test_buildRecommendedLevel_simpleLevels_firstLevelAt90Percent(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="50.00",
                    amount_2="76.00",
                    amount_3="100.00",
                )
            ],
            cache={},
        )

        # 60 % / 91.2 % / 120 % -> level 2 is the first at or above 90 %.
        self.assertEqual(
            2, BiddingRoundStatsService.build_recommended_level(round_, cache={})
        )

    def test_buildRecommendedLevel_simpleLevels_noneReaches90_returnsLastLevel(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("2000.00")
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="50.00",
                    amount_2="60.00",
                    amount_3="70.00",
                )
            ],
            cache={},
        )

        self.assertEqual(
            3, BiddingRoundStatsService.build_recommended_level(round_, cache={})
        )

    def test_buildRecommendedLevelAmpel_returnsMiddleLevel(self):
        round_ = create_open_round(bidding_procedure="traffic_light")

        self.assertEqual(
            2, BiddingRoundStatsService.build_recommended_level(round_, cache={})
        )

    def test_getDefaultPosition_simpleLevels_returnsRecommendedPosition(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="50.00",
                    amount_2="76.00",
                    amount_3="100.00",
                )
            ],
            cache={},
        )

        self.assertEqual(
            Decimal("50"),
            BiddingRoundStatsService.get_default_position(round_, cache={}),
        )

    def test_buildPublicStats_simpleLevels_usesRecommendedPosition(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="50.00",
                    amount_2="76.00",
                    amount_3="100.00",
                )
            ],
            cache={},
        )

        public_stats = BiddingRoundStatsService.build_public_stats(round_, cache={})

        # Recommended level 2 -> 76.00 * 12 = 912.00.
        self.assertEqual(Decimal("912.00"), public_stats[0]["reached_per_year"])

    def test_buildPublicEvaluation_returnsUtilizationAndCoverage(self):
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00"), capacity=10
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [
                build_item(
                    round_product,
                    product,
                    amount_1="50.00",
                    amount_2="76.00",
                    amount_3="100.00",
                )
            ],
            cache={},
        )

        evaluation = BiddingRoundStatsService.build_public_evaluation(round_, cache={})

        self.assertEqual(3, evaluation["bid_levels"])
        self.assertEqual(2, evaluation["recommended_level"])
        self.assertAlmostEqual(
            float(evaluation["current_shares"] / evaluation["capacity_shares"] * 100),
            evaluation["utilization_percent"],
            places=2,
        )
        green = evaluation["levels"]["green"]["current_coverage_percent"]
        yellow = evaluation["levels"]["yellow"]["current_coverage_percent"]
        red = evaluation["levels"]["red"]["current_coverage_percent"]
        self.assertLess(green, yellow)
        self.assertLess(yellow, red)
        for key in ("green", "yellow", "red"):
            level = evaluation["levels"][key]
            self.assertIn("current_total_per_year", level)
            self.assertIn("bidder_average_per_month", level)
            # The non-bidder average and the full-capacity coverage are not
            # exposed publicly anymore.
            self.assertNotIn("non_bidder_average_per_month", level)
            self.assertNotIn("coverage_percent", level)

    def test_buildPublicEvaluation_doesNotExposeInternalKeys(self):
        round_ = create_open_round()
        create_round_product_with_product(round_)

        evaluation = BiddingRoundStatsService.build_public_evaluation(round_, cache={})

        for internal_key in (
            "membership_per_year",
            "delivery_charge_per_year",
            "auto_shares",
            "remaining_shares",
            "fixed_per_year",
            "auto_renew_per_year",
        ):
            self.assertNotIn(internal_key, evaluation)

    def test_buildPublicEvaluationAmpel_returnsMiddleRecommendedLevel(self):
        round_ = create_open_round(bidding_procedure="traffic_light")
        create_round_product_with_product(round_)

        evaluation = BiddingRoundStatsService.build_public_evaluation(round_, cache={})

        self.assertEqual(2, evaluation["recommended_level"])

    def test_buildNonBidderRatePerShare_appliesFloor(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00"), capacity=10
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )

        rate = BiddingRoundStatsService.build_non_bidder_rate_per_share(
            round_, bid_level=1, cache={}
        )

        # Bidders' average (80) is above the derived average, so the floor wins.
        self.assertEqual(Decimal("80.00"), rate)

    def test_buildNonBidderRatePerShare_flagOff_usesDerivedAverage(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00"), capacity=10
        )
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_NON_BIDDERS_MIN_AVERAGE
        ).update(value="false")

        rate = BiddingRoundStatsService.build_non_bidder_rate_per_share(
            round_, bid_level=1, cache={}
        )

        self.assertLess(rate, Decimal("80.00"))

    def test_buildResults_pickupLocationsEnabled_capacityVsDemand(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type=round_product.product_type,
            max_capacity=30,
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product)],
            pickup_location_id=pickup_location.id,
            cache={},
        )

        table = BiddingRoundStatsService.build_results_table(round_, cache={})

        pickup_location_entry = next(
            entry
            for entry in table["pickup_locations"]
            if entry["pickup_location"] == pickup_location
        )
        self.assertEqual(30, pickup_location_entry["capacity"])
        self.assertEqual(Decimal("1"), pickup_location_entry["demand"])
        self.assertAlmostEqual(100 / 30, pickup_location_entry["fill_percent"])

    def test_buildResults_pickupLocationsEnabled_countsDemandPerLocation(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        pickup_location = PickupLocationFactory.create()
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, quantity=3)],
            pickup_location_id=pickup_location.id,
            cache={},
        )

        table = BiddingRoundStatsService.build_results_table(round_, cache={})

        entries = {
            entry["pickup_location"].id: entry for entry in table["pickup_locations"]
        }
        self.assertEqual(Decimal("3"), entries[pickup_location.id]["demand"])

    def test_buildResults_pickupLocationsDisabled_omitsCapacityView(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        round_ = create_open_round()
        create_round_product_with_product(round_)

        table = BiddingRoundStatsService.build_results_table(round_, cache={})

        self.assertNotIn("pickup_locations", table)

    def test_buildPublicPickupLocationUtilization_marksFullDepots(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type=round_product.product_type,
            max_capacity=3,
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, quantity=3)],
            pickup_location_id=pickup_location.id,
            cache={},
        )

        utilization = BiddingRoundStatsService.build_public_pickup_location_utilization(
            round_, cache={}
        )

        entry = utilization[pickup_location.id]
        self.assertEqual("3", entry["capacity"])
        self.assertEqual("3", entry["demand"])
        self.assertTrue(entry["is_full"])
        self.assertAlmostEqual(100.0, entry["fill_percent"])
