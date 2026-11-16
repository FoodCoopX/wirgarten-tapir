import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_STATUS_ACTIVE,
    BIDDING_ROUND_STATUS_CLOSED,
)
from tapir.bidding_round.models import Bid, BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bid_input import BidInput
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MandateReferenceFactory,
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
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            other_bids=[(1, Decimal("50.00"))],
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member, bid_ids=[bid.id]
        )

        self.assertEqual([], result.errors)
        self.assertEqual(1, len(result.subscriptions))
        subscription = Subscription.objects.get(member=bid.member, product=product)
        self.assertEqual(1, subscription.quantity)
        self.assertEqual(period.start_date, subscription.start_date)
        link = BiddingRoundCreatedSubscription.objects.get(
            round=bidding_round, subscription=subscription
        )
        self.assertEqual(Decimal("65.0000"), link.monthly_price_per_share)
        self.assertIsNone(subscription.price_override)
        self.assertEqual(
            Subscription.PriceMode.BIDDING_ROUND_BID, subscription.price_mode
        )
        self.assertEqual(
            Decimal("65.00"),
            SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=period.start_date, cache={}
            ),
        )
        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("15.00"), contribution.amount)
        bidding_round.refresh_from_db()
        self.assertIsNotNone(bidding_round.contracts_created_at)

    def test_createContracts_roundChangesLater_keepsTheFrozenPrice(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            other_bids=[(1, Decimal("50.00"))],
        )
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member, bid_ids=[bid.id]
        )
        bid.amount_1 = Decimal("95.00")
        bid.save(update_fields=["amount_1", "updated_at"])

        subscription = Subscription.objects.get(member=bid.member, product=product)

        self.assertEqual(
            Decimal("65.00"),
            SubscriptionPriceCalculator.get_monthly_price(
                subscription, reference_date=period.start_date, cache={}
            ),
        )

    def test_createContracts_withSeveralShares_usesTheBidQuantity(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            quantity=2,
            other_bids=[(2, Decimal("50.00"))],
        )

        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member, bid_ids=[bid.id]
        )

        subscription = Subscription.objects.get(member=bid.member, product=product)
        self.assertEqual(2, subscription.quantity)
        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("30.00"), contribution.amount)

    def test_createContracts_withExistingSubscription_reusesItWithoutDeleting(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            quantity=3,
            other_bids=[(3, Decimal("50.00"))],
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
            bidding_round, cache={}, actor=bid.member, bid_ids=[bid.id]
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
        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("45.00"), contribution.amount)

    def test_createContracts_otherShareSizeNotStarted_replacesIt(self):
        period, bidding_round, old_product, new_product = (
            self._create_round_with_two_share_sizes()
        )
        member = MemberFactory.create()
        existing = SubscriptionFactory.create(
            member=member,
            product=old_product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
        )
        BidFactory.create(
            round=bidding_round,
            member=member,
            product=new_product,
            amount_1=Decimal("80.00"),
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=member
        )

        self.assertEqual([], result.errors)
        self.assertFalse(Subscription.objects.filter(pk=existing.pk).exists())
        new_subscription = Subscription.objects.get(member=member, product=new_product)
        self.assertEqual(
            Subscription.PriceMode.BIDDING_ROUND_BID, new_subscription.price_mode
        )
        self.assertEqual(
            1,
            Subscription.objects.filter(
                member=member, cancellation_ts__isnull=True
            ).count(),
        )

    def test_createContracts_otherShareSizeStarted_reportsErrorAndWritesNothing(self):
        period, bidding_round, old_product, new_product = (
            self._create_round_with_two_share_sizes()
        )
        member = MemberFactory.create()
        existing = SubscriptionFactory.create(
            member=member,
            product=old_product,
            period=period,
            quantity=1,
            start_date=get_now(cache={}).date() - datetime.timedelta(days=10),
            end_date=period.end_date,
        )
        BidFactory.create(
            round=bidding_round,
            member=member,
            product=new_product,
            amount_1=Decimal("80.00"),
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=member
        )

        self.assertEqual(1, len(result.errors))
        self.assertIn("anderen Anteilsgröße", result.errors[0].error)
        self.assertTrue(Subscription.objects.filter(pk=existing.pk).exists())
        self.assertFalse(
            Subscription.objects.filter(member=member, product=new_product).exists()
        )
        bidding_round.refresh_from_db()
        self.assertIsNone(bidding_round.contracts_created_at)

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
        other_bid = BidFactory.create(
            round=bidding_round, product=product, amount_1=Decimal("90.00")
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, bid_ids=[bid.id], actor=bid.member
        )

        self.assertEqual(1, len(result.subscriptions))
        self.assertFalse(
            BiddingRoundCreatedSubscription.objects.filter(
                round=bidding_round, subscription__member=other_bid.member
            ).exists()
        )

    def test_createContracts_withLockedRedPosition_usesTheRedAmount(self):
        bidding_round, bid, product, period = (
            self._create_closed_bid_range_round_with_bid(Decimal("50.00"))
        )
        other_bid = BidFactory.create(
            round=bidding_round,
            product=product,
            amount_1=Decimal("50.00"),
            amount_2=Decimal("60.00"),
        )
        other_bid.admin_confirmed = get_now(cache={})
        other_bid.save()
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=100,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        self.assertEqual([], result.errors)
        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("15.00"), contribution.amount)

    def test_createContracts_withLockedGreenPosition_usesTheGreenAmount(self):
        bidding_round, bid, product, period = (
            self._create_closed_bid_range_round_with_bid(Decimal("50.00"))
        )
        other_bid = BidFactory.create(
            round=bidding_round,
            product=product,
            amount_1=Decimal("50.00"),
            amount_2=Decimal("60.00"),
        )
        other_bid.admin_confirmed = get_now(cache={})
        other_bid.save()
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        self.assertEqual([], result.errors)
        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("10.00"), contribution.amount)

    def test_createContracts_withAutoRenewed_usesTheFrozenRoundPrice(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        non_bidder = MemberFactory.create()
        previous_period = GrowingPeriodFactory.create(
            start_date=period.start_date - datetime.timedelta(days=365),
            end_date=period.start_date - datetime.timedelta(days=1),
        )
        current_subscription = SubscriptionFactory.create(
            member=non_bidder,
            product=product,
            period=previous_period,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )
        renewed_subscription = SubscriptionFactory.build(
            member=non_bidder,
            product=product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
            mandate_ref=MandateReferenceFactory.create(member=non_bidder),
        )

        with (
            patch.object(
                AutomaticSubscriptionRenewalService,
                "get_subscriptions_that_will_be_renewed",
                return_value={current_subscription},
            ),
            patch.object(
                AutomaticSubscriptionRenewalService,
                "build_renewed_subscription",
                return_value=renewed_subscription,
            ),
        ):
            ContractCreator.create_contracts_from_bids(
                bidding_round,
                cache={},
                actor=bid.member,
                create_auto_renewed_contracts=True,
            )

        link = BiddingRoundCreatedSubscription.objects.get(
            round=bidding_round, subscription=renewed_subscription
        )
        self.assertEqual(Decimal("90.0000"), link.monthly_price_per_share)
        self.assertEqual(
            Decimal("90.00"),
            SubscriptionPriceCalculator.get_monthly_price(
                renewed_subscription, reference_date=period.start_date, cache={}
            ),
        )
        self.assertFalse(
            SolidarityContribution.objects.filter(
                member=non_bidder, start_date=period.start_date
            ).exists()
        )
        renewed_subscription.refresh_from_db()
        self.assertEqual(
            Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED,
            renewed_subscription.price_mode,
        )

    def _create_closed_round_with_bid(
        self,
        bid_amount,
        standard_price,
        quantity=1,
        other_bids=None,
        surcharge_percent=0,
        surcharge_on_bids=False,
        surcharge_on_average=False,
    ):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period, status=BIDDING_ROUND_STATUS_CLOSED
        )
        product = ProductFactory.create(type=bidding_round.product_type)
        ProductPriceFactory.create(
            product=product,
            price=standard_price,
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round=bidding_round,
            product=product,
        )
        bid = BidFactory.create(
            round=bidding_round,
            product=product,
            quantity=quantity,
            amount_1=bid_amount,
        )
        for other_quantity, other_amount in other_bids or []:
            other_bid = BidFactory.create(
                round=bidding_round,
                product=product,
                quantity=other_quantity,
                amount_1=other_amount,
            )
            other_bid.admin_confirmed = get_now(cache={})
            other_bid.save()
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=surcharge_percent,
            surcharge_on_bids=surcharge_on_bids,
            surcharge_on_average=surcharge_on_average,
            cache={},
        )
        bid.admin_confirmed = get_now(cache={})
        bid.save()
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
        product = ProductFactory.create(type=bidding_round.product_type)
        ProductPriceFactory.create(
            product=product,
            price=standard_price,
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round=bidding_round,
            product=product,
        )
        member = MemberFactory.create()
        bid = BiddingRoundService.save_bid(
            member,
            bidding_round,
            BidInput(
                product_id=product.id,
                quantity=1,
                amount_1=Decimal("70.00"),
                amount_2=Decimal("90.00"),
            ),
            cache={},
        )
        bid.admin_confirmed = get_now(cache={})
        bid.save()
        BiddingRoundService.close_round(bidding_round, cache={})
        return bidding_round, bid, product, period

    def test_createContracts_withoutLockedAverageBid_raisesValidationError(self):
        bidding_round, bid, _product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        bidding_round.average_bid_locked_at = None
        bidding_round.save()

        with pytest.raises(ValidationError):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )

    def test_createContracts_withUnconfirmedBid_raisesValidationError(self):
        bidding_round, bid, _product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        bid.admin_confirmed = None
        bid.save()

        with pytest.raises(ValidationError):
            ContractCreator.create_contracts_from_bids(
                bidding_round, cache={}, actor=bid.member
            )

    def test_createContracts_withSurchargeOnBids_appliesSurchargeToContribution(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"),
            standard_price=Decimal("50.00"),
            other_bids=[(1, Decimal("50.00"))],
            surcharge_percent=Decimal("10"),
            surcharge_on_bids=True,
        )

        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        contribution = SolidarityContribution.objects.get(
            member=bid.member, start_date=period.start_date
        )
        self.assertEqual(Decimal("16.50"), contribution.amount)

    def test_createContracts_lockedPositionIgnoresBidLevel(self):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            status=BIDDING_ROUND_STATUS_CLOSED,
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE,
            bid_levels=2,
        )
        product = ProductFactory.create(type=bidding_round.product_type)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(round=bidding_round, product=product)
        bid = BidFactory.create(
            round=bidding_round,
            product=product,
            amount_1=Decimal("70.00"),
            amount_2=Decimal("90.00"),
        )
        other_bid = BidFactory.create(
            round=bidding_round,
            product=product,
            amount_1=Decimal("50.00"),
            amount_2=Decimal("70.00"),
        )
        other_bid.admin_confirmed = get_now(cache={})
        other_bid.save()
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=50,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )
        bid.admin_confirmed = get_now(cache={})
        bid.save()

        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member, bid_level=3
        )

        self.assertEqual(
            Decimal("10.00"),
            SolidarityContribution.objects.get(
                member=bid.member, start_date=period.start_date
            ).amount,
        )

    def test_createContracts_otherShareSizeNotStarted_replacesIt(self):
        period, bidding_round, old_product, new_product = (
            self._create_round_with_two_share_sizes()
        )
        member = MemberFactory.create()
        existing = SubscriptionFactory.create(
            member=member,
            product=old_product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
        )
        BidFactory.create(
            round=bidding_round,
            member=member,
            product=new_product,
            amount_1=Decimal("80.00"),
        )
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )
        Bid.objects.filter(round=bidding_round, member=member).update(
            admin_confirmed=get_now(cache={})
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=member
        )

        self.assertEqual([], result.errors)
        self.assertFalse(Subscription.objects.filter(pk=existing.pk).exists())
        new_subscription = Subscription.objects.get(member=member, product=new_product)
        self.assertEqual(
            Subscription.PriceMode.BIDDING_ROUND_BID, new_subscription.price_mode
        )
        self.assertEqual(
            1,
            Subscription.objects.filter(
                member=member, cancellation_ts__isnull=True
            ).count(),
        )

    def test_createContracts_otherShareSizeStarted_reportsErrorAndWritesNothing(self):
        period, bidding_round, old_product, new_product = (
            self._create_round_with_two_share_sizes()
        )
        member = MemberFactory.create()
        existing = SubscriptionFactory.create(
            member=member,
            product=old_product,
            period=period,
            quantity=1,
            start_date=get_now(cache={}).date() - datetime.timedelta(days=10),
            end_date=period.end_date,
        )
        BidFactory.create(
            round=bidding_round,
            member=member,
            product=new_product,
            amount_1=Decimal("80.00"),
        )
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )
        Bid.objects.filter(round=bidding_round, member=member).update(
            admin_confirmed=get_now(cache={})
        )

        result = ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=member
        )

        self.assertEqual(1, len(result.errors))
        self.assertIn("anderen Anteilsgröße", result.errors[0].error)
        self.assertTrue(Subscription.objects.filter(pk=existing.pk).exists())
        self.assertFalse(
            Subscription.objects.filter(member=member, product=new_product).exists()
        )
        bidding_round.refresh_from_db()
        self.assertIsNone(bidding_round.contracts_created_at)

    def test_createContracts_bidderContract_setsBidderContractTrue(self):
        bidding_round, bid, product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )

        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member
        )

        link = BiddingRoundCreatedSubscription.objects.get(
            round=bidding_round, subscription__member=bid.member
        )
        self.assertTrue(link.is_bidder_contract)

    def test_createContracts_autoRenewedContract_setsBidderContractFalse(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        non_bidder = MemberFactory.create()
        current_subscription, renewed_subscription = self._create_renewing_subscription(
            member=non_bidder, product=product, period=period
        )

        with (
            patch.object(
                AutomaticSubscriptionRenewalService,
                "get_subscriptions_that_will_be_renewed",
                return_value={current_subscription},
            ),
            patch.object(
                AutomaticSubscriptionRenewalService,
                "build_renewed_subscription",
                return_value=renewed_subscription,
            ),
        ):
            ContractCreator.create_contracts_from_bids(
                bidding_round,
                cache={},
                actor=bid.member,
                create_auto_renewed_contracts=True,
            )

        link = BiddingRoundCreatedSubscription.objects.get(
            round=bidding_round, subscription=renewed_subscription
        )
        self.assertFalse(link.is_bidder_contract)

    def test_createContracts_withAutoRenewedMemberIds_createsOnlySelectedMember(
        self,
    ):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        selected_member = MemberFactory.create()
        other_member = MemberFactory.create()
        selected_current, selected_renewed = self._create_renewing_subscription(
            member=selected_member, product=product, period=period
        )
        other_current, other_renewed = self._create_renewing_subscription(
            member=other_member, product=product, period=period
        )

        def build_renewed(subscription, cache):
            if subscription.member_id == selected_member.id:
                return selected_renewed
            return other_renewed

        with (
            patch.object(
                AutomaticSubscriptionRenewalService,
                "get_subscriptions_that_will_be_renewed",
                return_value={selected_current, other_current},
            ),
            patch.object(
                AutomaticSubscriptionRenewalService,
                "build_renewed_subscription",
                side_effect=build_renewed,
            ),
        ):
            result = ContractCreator.create_contracts_from_bids(
                bidding_round,
                cache={},
                actor=bid.member,
                create_auto_renewed_contracts=True,
                auto_renewed_member_ids=[selected_member.id],
            )

        created_member_ids = {
            subscription.member_id for subscription in result.subscriptions
        }
        self.assertIn(selected_member.id, created_member_ids)
        self.assertNotIn(other_member.id, created_member_ids)
        self.assertFalse(
            Subscription.objects.filter(
                member=other_member, period=period, cancellation_ts__isnull=True
            ).exists()
        )

    def test_checkContracts_withUnconfirmedBid_returnsErrorWithoutWriting(self):
        bidding_round, bid, product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        bid.admin_confirmed = None
        bid.save()

        errors = ContractCreator.check_contracts_from_bids(
            bidding_round, cache={}, bid_ids=[bid.id]
        )

        self.assertEqual(1, len(errors))
        self.assertEqual(bid.id, errors[0]["bid_id"])
        self.assertEqual(bid.member, errors[0]["member"])
        self.assertEqual(product.type.name, errors[0]["product_name"])
        self.assertFalse(
            BiddingRoundCreatedSubscription.objects.filter(round=bidding_round).exists()
        )
        bidding_round.refresh_from_db()
        self.assertIsNone(bidding_round.contracts_created_at)

    def _create_round_with_two_share_sizes(self):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period, status=BIDDING_ROUND_STATUS_CLOSED
        )
        old_product = ProductFactory.create(
            type=bidding_round.product_type, name="Mittlere Kiste"
        )
        new_product = ProductFactory.create(
            type=bidding_round.product_type, name="Große Kiste"
        )
        ProductPriceFactory.create(
            product=new_product,
            price=Decimal("50.00"),
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
        BiddingRoundProductPriceFactory.create(
            round=bidding_round,
            product=new_product,
        )
        return period, bidding_round, old_product, new_product

    def test_checkContracts_withConfirmedBid_returnsEmpty(self):
        bidding_round, bid, _product, _period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )

        errors = ContractCreator.check_contracts_from_bids(
            bidding_round, cache={}, bid_ids=[bid.id]
        )

        self.assertEqual([], errors)

    @staticmethod
    def _create_renewing_subscription(member, product, period):
        previous_period = GrowingPeriodFactory.create(
            start_date=period.start_date - datetime.timedelta(days=365),
            end_date=period.start_date - datetime.timedelta(days=1),
        )
        current_subscription = SubscriptionFactory.create(
            member=member,
            product=product,
            period=previous_period,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )
        renewed_subscription = SubscriptionFactory.build(
            member=member,
            product=product,
            period=period,
            quantity=1,
            start_date=period.start_date,
            end_date=period.end_date,
            mandate_ref=MandateReferenceFactory.create(member=member),
        )
        return current_subscription, renewed_subscription
