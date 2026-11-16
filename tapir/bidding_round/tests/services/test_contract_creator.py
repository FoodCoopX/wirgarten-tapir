import datetime
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
    BiddingRoundProductTypeFactory,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import Subscription
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
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


class TestContractCreator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_createContracts_whenRoundIsNotClosed_raisesValidationError(self):
        bidding_round = BiddingRoundFactory.create(status=BIDDING_ROUND_STATUS_ACTIVE)

        with pytest.raises(ValidationError):
            ContractCreator.create_contracts_from_bids(bidding_round, cache={})

    def test_createContracts_createsSubscriptionAndContribution(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["subscriptions"]))
        subscription = Subscription.objects.get(member=bid.member, product=product)
        self.assertEqual(1, subscription.quantity)
        self.assertEqual(period.start_date, subscription.start_date)
        self.assertTrue(
            BiddingRoundCreatedSubscription.objects.filter(
                round=bidding_round, subscription=subscription
            ).exists()
        )
        self.assertFalse(
            SolidarityContribution.objects.filter(
                member=bid.member, start_date=period.start_date
            ).exists()
        )
        self.assertIsNone(subscription.price_override)
        self.assertEqual(
            Subscription.PriceMode.BIDDING_ROUND_BID, subscription.price_mode
        )
        self.assertEqual(
            Decimal("80.00"),
            SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=period.start_date, cache={}
            ),
        )
        bidding_round.refresh_from_db()
        self.assertIsNotNone(bidding_round.contracts_created_at)

    def test_createContracts_withSeveralShares_usesTheBidQuantity(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            quantity=2,
        )

        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        subscription = Subscription.objects.get(member=bid.member, product=product)
        self.assertEqual(2, subscription.quantity)
        self.assertFalse(
            SolidarityContribution.objects.filter(
                member=bid.member, start_date=period.start_date
            ).exists()
        )
        self.assertEqual(
            Decimal("160.00"),
            SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=period.start_date, cache={}
            ),
        )

    def test_createContracts_withExistingSubscription_reusesItWithoutDeleting(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            quantity=3,
        )
        existing = SubscriptionFactory.create(
            member=bid.member,
            product=product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
        )

        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        existing.refresh_from_db()
        self.assertEqual(3, existing.quantity)
        self.assertEqual(
            1,
            Subscription.objects.filter(
                member=bid.member, product=product, cancellation_ts__isnull=True
            ).count(),
        )
        self.assertTrue(
            BiddingRoundCreatedSubscription.objects.filter(
                round=bidding_round, subscription=existing
            ).exists()
        )
        self.assertFalse(
            SolidarityContribution.objects.filter(
                member=bid.member, start_date=period.start_date
            ).exists()
        )

    def test_createContracts_calledTwice_raisesValidationError(self):
        bidding_round, bid, _product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        with pytest.raises(ValidationError):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )

    def test_createContracts_whenAnotherRoundInPeriodHasContracts_raisesValidationError(
        self,
    ):
        bidding_round, bid, _product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        BiddingRoundFactory.create(
            growing_period=period,
            status=BIDDING_ROUND_STATUS_CLOSED,
            contracts_created_at=get_now(cache={}),
        )

        with pytest.raises(ValidationError):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )

    def test_createContracts_withSelectedBidIds_createsOnlyThose(self):
        bidding_round, bid, product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        other_bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=other_bid,
            round_product_type=bidding_round.product_types.first(),
            product=product,
            amount_1=Decimal("90.00"),
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, bid_ids=[bid.id], actor=bid.member
        )

        self.assertEqual(1, len(result["subscriptions"]))
        self.assertFalse(
            BiddingRoundCreatedSubscription.objects.filter(
                round=bidding_round, subscription__member=other_bid.member
            ).exists()
        )

    def test_createContracts_withBidRangeBidAtRed_usesTheRedAmount(self):
        bidding_round, bid, _product, period = (
            self._create_closed_bid_range_round_with_bid(Decimal("50.00"))
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, bid_level=2, actor=bid.member
        )

        self.assertEqual([], result["errors"])
        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("10.00"), contribution.amount)

    def _create_closed_round_with_bid(self, bid_amount, standard_price, quantity=1):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period, status=BIDDING_ROUND_STATUS_CLOSED
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        ProductPriceFactory.create(
            product=product,
            price=standard_price,
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
        )
        bid = BidFactory.create(round=bidding_round)
        BidItemFactory.create(
            bid=bid,
            round_product_type=round_product_type,
            product=product,
            quantity=quantity,
            amount_1=bid_amount,
        )
        return bidding_round, bid, product, period

    def _create_closed_bid_range_round_with_bid(self, standard_price):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            status=BIDDING_ROUND_STATUS_ACTIVE,
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE,
            bid_levels=2,
            start_at=get_now(cache={}) - datetime.timedelta(hours=1),
            end_at=get_now(cache={}) + datetime.timedelta(days=1),
        )
        round_product_type = BiddingRoundProductTypeFactory.create(round=bidding_round)
        product = ProductFactory.create(type=round_product_type.product_type)
        ProductPriceFactory.create(
            product=product,
            price=standard_price,
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round_product_type=round_product_type,
            product=product,
        )
        member = MemberFactory.create()
        bid = BiddingRoundService.save_bid(
            member,
            bidding_round,
            [
                {
                    "round_product_type_id": round_product_type.id,
                    "product_id": product.id,
                    "quantity": 1,
                    "amount_1": "70.00",
                    "amount_2": "90.00",
                }
            ],
            cache={},
        )
        BiddingRoundService.close_round(bidding_round, cache={})
        return bidding_round, bid, product, period
