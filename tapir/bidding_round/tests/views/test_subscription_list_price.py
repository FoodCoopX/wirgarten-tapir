import datetime
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.contract_creator import ContractCreator
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
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


class TestSubscriptionListPrice(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_subscriptionList_bidContract_showsBidderAveragePrice(self):
        bidding_round, bid, product, period = self._create_closed_round_with_bid(
            bid_amount=Decimal("80.00"), standard_price=Decimal("50.00")
        )
        ContractCreator.create_contracts_from_bids(
            bidding_round, cache={}, actor=bid.member, bid_ids=[bid.id]
        )

        subscription = self._get_listed_subscription(period, bid.member)

        self.assertEqual(Decimal("80.00"), subscription.monthly_price)

    def test_subscriptionList_autoRenewedContract_showsNonBidderPrice(self):
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

        subscription = self._get_listed_subscription(period, non_bidder)

        self.assertEqual(Decimal("90.00"), subscription.monthly_price)

    def _get_listed_subscription(self, period, member):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        response = self.client.get(
            reverse("wirgarten:subscription_list"), {"period": period.id}
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        return next(
            subscription
            for subscription in response.context["object_list"]
            if subscription.member_id == member.id
        )

    def _create_closed_round_with_bid(self, bid_amount, standard_price, quantity=1):
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
        BiddingRoundService.lock_average_bid(
            bidding_round,
            position=0,
            surcharge_percent=0,
            surcharge_on_bids=False,
            surcharge_on_average=False,
            cache={},
        )
        bid.admin_confirmed = get_now(cache={})
        bid.save()
        return bidding_round, bid, product, period
