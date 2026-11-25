import datetime
from decimal import Decimal
from unittest.mock import patch

from tapir.bidding_round.config import (
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.services.non_bidder_contribution_service import (
    NonBidderContributionService,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestNonBidderContributionService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _create_round_with_bidder(
        self, status=BIDDING_ROUND_STATUS_ACTIVE, contracts_created_at=None
    ):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            status=status,
            contracts_created_at=contracts_created_at,
            target_amount_per_year=Decimal("1000.00"),
        )
        product = ProductFactory.create(type=bidding_round.product_type)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round=bidding_round,
            product=product,
            reference_value=Decimal("80.00"),
            min_amount=Decimal("60.00"),
        )
        bid = BidFactory.create(
            round=bidding_round, product=product, amount_1=Decimal("80.00")
        )
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            product=product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
        )
        return bidding_round, period, product, bid, member

    def test_applyFloorToMember_setsContributionToBidderAverage(self):
        bidding_round, period, _product, bid, member = self._create_round_with_bidder()

        applied = NonBidderContributionService.apply_floor_to_member(
            member=member,
            bidding_round=bidding_round,
            actor=bid.member,
            cache={},
        )

        self.assertTrue(applied)
        self.assertEqual(
            Decimal("30.00"),
            SolidarityContribution.objects.get(
                member=member, start_date=period.start_date
            ).amount,
        )

    def test_applyLatecomerFloor_closedRound_setsContribution(self):
        _bidding_round, period, _product, bid, member = self._create_round_with_bidder(
            status=BIDDING_ROUND_STATUS_CLOSED,
            contracts_created_at=get_now(cache={}),
        )

        applied = NonBidderContributionService.apply_latecomer_floor(
            member=member,
            contract_start_date=period.start_date,
            actor=bid.member,
            cache={},
        )

        self.assertTrue(applied)
        self.assertEqual(
            Decimal("30.00"),
            SolidarityContribution.objects.get(
                member=member, start_date=period.start_date
            ).amount,
        )

    def test_applyLatecomerFloor_lateStart_keepsTheJoinDate(self):
        _bidding_round, period, _product, bid, member = self._create_round_with_bidder(
            status=BIDDING_ROUND_STATUS_CLOSED,
            contracts_created_at=get_now(cache={}),
        )
        join_date = period.start_date + datetime.timedelta(days=14)

        applied = NonBidderContributionService.apply_latecomer_floor(
            member=member,
            contract_start_date=join_date,
            actor=bid.member,
            cache={},
        )

        self.assertIsNotNone(applied)
        contribution = SolidarityContribution.objects.get(member=member)
        self.assertEqual(join_date, contribution.start_date)
        self.assertEqual(Decimal("30.00"), contribution.amount)

    def test_applyLatecomerFloor_withoutClosedRound_returnsFalse(self):
        _bidding_round, period, _product, bid, member = self._create_round_with_bidder()

        applied = NonBidderContributionService.apply_latecomer_floor(
            member=member,
            contract_start_date=period.start_date,
            actor=bid.member,
            cache={},
        )

        self.assertFalse(applied)

    def test_applyLatecomerFloor_withSeveralClosedRounds_usesTheRoundWithContracts(
        self,
    ):
        _bidding_round, period, _product, bid, member = self._create_round_with_bidder(
            status=BIDDING_ROUND_STATUS_CLOSED,
            contracts_created_at=get_now(cache={}),
        )
        BiddingRoundFactory.create(
            growing_period=period, status=BIDDING_ROUND_STATUS_CLOSED
        )

        applied = NonBidderContributionService.apply_latecomer_floor(
            member=member,
            contract_start_date=period.start_date,
            actor=bid.member,
            cache={},
        )

        self.assertTrue(applied)
        self.assertEqual(
            Decimal("30.00"),
            SolidarityContribution.objects.get(
                member=member, start_date=period.start_date
            ).amount,
        )

    def test_applyLatecomerFloor_withSeveralClosedRoundsWithoutContracts_returnsFalse(
        self,
    ):
        _bidding_round, period, _product, bid, member = self._create_round_with_bidder(
            status=BIDDING_ROUND_STATUS_CLOSED
        )
        BiddingRoundFactory.create(
            growing_period=period, status=BIDDING_ROUND_STATUS_CLOSED
        )

        applied = NonBidderContributionService.apply_latecomer_floor(
            member=member,
            contract_start_date=period.start_date,
            actor=bid.member,
            cache={},
        )

        self.assertFalse(applied)

    def test_applyFloorToMember_givenHighExistingContribution_doesNotLowerIt(self):
        bidding_round, period, _product, bid, member = self._create_round_with_bidder()
        SolidarityContribution.objects.create(
            member=member,
            amount=Decimal("100.00"),
            start_date=period.start_date,
            end_date=period.end_date,
        )

        applied = NonBidderContributionService.apply_floor_to_member(
            member=member,
            bidding_round=bidding_round,
            actor=bid.member,
            cache={},
        )

        self.assertFalse(applied)
        self.assertEqual(
            Decimal("100.00"),
            SolidarityContribution.objects.get(
                member=member, start_date=period.start_date
            ).amount,
        )

    def test_applyNonBidderContributions_appliesFloorToNonBidderSubscription(self):
        bidding_round, period, product, bid, _member = self._create_round_with_bidder(
            status=BIDDING_ROUND_STATUS_CLOSED
        )
        non_bidder = MemberFactory.create()
        SubscriptionFactory.create(
            member=non_bidder,
            product=product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value=set(),
        ):
            applied = NonBidderContributionService.apply_non_bidder_contributions(
                bidding_round, actor=bid.member, cache={}
            )

        self.assertIn(non_bidder.id, applied)
        self.assertEqual(
            Decimal("30.00"),
            SolidarityContribution.objects.get(
                member=non_bidder, start_date=period.start_date
            ).amount,
        )
