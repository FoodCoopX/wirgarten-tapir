from decimal import Decimal

from tapir.bidding_round.config import CLOSED
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.non_bidder_contribution_service import (
    NonBidderContributionService,
)
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestNonBidderContributionService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _prepare_round(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00"), capacity=10
        )
        # The bidder's average (80) sets the floored non-bidder rate.
        BiddingRoundService.save_bid(
            MemberFactory.create(),
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )
        round_.status = CLOSED
        round_.save()
        return round_, product

    def _create_non_bidder(self, round_, product, price="50.00"):
        member = MemberFactory.create()
        ProductPriceFactory.create(
            product=product,
            price=Decimal(price),
            size=Decimal("1"),
            valid_from=round_.growing_period.start_date,
        )
        SubscriptionFactory.create(
            member=member,
            period=round_.growing_period,
            product=product,
            quantity=1,
        )
        return member

    def test_applyFloor_solidarity_raisesContributionToRate(self):
        round_, product = self._prepare_round()
        member = self._create_non_bidder(round_, product, price="50.00")

        applied = NonBidderContributionService.apply_floor_to_member(
            member=member, bidding_round=round_, actor=member, cache={}
        )

        self.assertTrue(applied)
        contribution = SolidarityContribution.objects.get(member=member)
        # Rate 80 - standard 50 = 30.
        self.assertEqual(Decimal("30.00"), contribution.amount)

    def test_applyFloor_solidarity_existingHigherContribution_notLowered(self):
        round_, product = self._prepare_round()
        member = self._create_non_bidder(round_, product, price="50.00")
        SolidarityContribution.objects.create(
            member=member,
            amount=Decimal("100.00"),
            start_date=round_.growing_period.start_date,
            end_date=round_.growing_period.end_date,
        )

        applied = NonBidderContributionService.apply_floor_to_member(
            member=member, bidding_round=round_, actor=member, cache={}
        )

        self.assertFalse(applied)
        self.assertEqual(
            Decimal("100.00"),
            SolidarityContribution.objects.get(member=member).amount,
        )

    def test_applyFloor_bidder_notTouched(self):
        round_, product = self._prepare_round()
        bidder = round_.bids.first().member
        SubscriptionFactory.create(
            member=bidder,
            period=round_.growing_period,
            product=product,
            quantity=1,
        )

        applied = NonBidderContributionService.apply_floor_to_member(
            member=bidder, bidding_round=round_, actor=bidder, cache={}
        )

        self.assertFalse(applied)
        self.assertFalse(SolidarityContribution.objects.filter(member=bidder).exists())
