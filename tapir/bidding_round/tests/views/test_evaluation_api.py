import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_SIMPLE,
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
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
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
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


class EvaluationApiTestBase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, True)

    def _login_as_admin(self):
        admin = MemberFactory.create(is_superuser=True, is_staff=True)
        self.client.force_login(admin)
        return admin

    def _create_closed_round_with_bid(
        self,
        bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
        bid_levels=1,
        amounts=None,
        lock=True,
    ):
        period = GrowingPeriodFactory.create(
            start_date=get_now(cache={}).date() + datetime.timedelta(days=30)
        )
        bidding_round = BiddingRoundFactory.create(
            growing_period=period,
            status=BIDDING_ROUND_STATUS_CLOSED,
            bidding_procedure=bidding_procedure,
            bid_levels=bid_levels,
        )
        round_product_type = BiddingRoundProductTypeFactory.create(
            round=bidding_round, target_amount_per_year=Decimal("1000.00")
        )
        product = ProductFactory.create(type=round_product_type.product_type)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=period.start_date - datetime.timedelta(days=1),
        )
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
            quantity=1,
            **(amounts or {"amount_1": Decimal("80.00")}),
        )
        if lock:
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
        return bidding_round, bid, product, period, round_product_type

    def _create_renewing_subscription(self, member, product, period):
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


class TestRoundResultsView(EvaluationApiTestBase):
    def setUp(self):
        super().setUp()
        self._login_as_admin()

    def test_results_withClosedRound_returnsAcceptanceFields(self):
        bidding_round, bid, _product, _period, _round_product_type = (
            self._create_closed_round_with_bid()
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
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
            }.issubset(set(response.data))
        )
        row = response.data["bids"][0]
        self.assertEqual(Decimal("80"), Decimal(row["effective_amount"]))
        self.assertEqual(Decimal("960"), Decimal(row["amount_per_year"]))
        self.assertEqual([], response.data["auto_renewed"])
        self.assertEqual([], response.data["contracts"])
        self.assertIsNone(response.data["contracts_created_at"])
        self.assertEqual(
            bidding_round.growing_period_id, response.data["growing_period_id"]
        )
        self.assertEqual([], response.data["results_table"]["pickup_locations"])

    def test_results_queryCount_doesNotGrowWithBidCount(self):
        bidding_round, _bid, product, _period, round_product_type = (
            self._create_closed_round_with_bid()
        )
        url = reverse("bidding_rounds:round_results", args=[bidding_round.id])

        with CaptureQueriesContext(connection) as one_bid:
            response = self.client.get(url)
        self.assertStatusCode(response, status.HTTP_200_OK)

        for _ in range(5):
            member = MemberFactory.create()
            bid = BidFactory.create(
                round=bidding_round,
                member=member,
                admin_confirmed=get_now(cache={}),
            )
            BidItemFactory.create(
                bid=bid,
                round_product_type=round_product_type,
                product=product,
                quantity=1,
                amount_1=Decimal("75.00"),
            )

        with CaptureQueriesContext(connection) as six_bids:
            response = self.client.get(url)
        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertLessEqual(len(six_bids), len(one_bid) + 10)

    def test_results_queryCount_doesNotGrowWithAutoRenewedContracts(self):
        one_round = self._create_round_with_auto_renewed_contracts(1)
        four_round = self._create_round_with_auto_renewed_contracts(4)

        with CaptureQueriesContext(connection) as one_contract:
            response = self.client.get(
                reverse("bidding_rounds:round_results", args=[one_round.id])
            )
        self.assertStatusCode(response, status.HTTP_200_OK)

        with CaptureQueriesContext(connection) as four_contracts:
            response = self.client.get(
                reverse("bidding_rounds:round_results", args=[four_round.id])
            )
        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertLessEqual(len(four_contracts), len(one_contract) + 10)

    def _create_round_with_auto_renewed_contracts(self, count):
        bidding_round, bid, product, period, _round_product_type = (
            self._create_closed_round_with_bid()
        )
        current_subscriptions = []
        renewed_by_current_id = {}
        for _ in range(count):
            member = MemberFactory.create()
            current_subscription, renewed_subscription = (
                self._create_renewing_subscription(member, product, period)
            )
            current_subscriptions.append(current_subscription)
            renewed_by_current_id[current_subscription.id] = renewed_subscription

        def build_renewed(previous_subscription, cache):
            return renewed_by_current_id[previous_subscription.id]

        with (
            patch.object(
                AutomaticSubscriptionRenewalService,
                "get_subscriptions_that_will_be_renewed",
                return_value=set(current_subscriptions),
            ),
            patch.object(
                AutomaticSubscriptionRenewalService,
                "build_renewed_subscription",
                side_effect=build_renewed,
            ),
        ):
            ContractCreator.create_contracts_from_bids(
                bidding_round,
                cache={},
                actor=bid.member,
                create_auto_renewed_contracts=True,
            )
        return bidding_round

    def test_results_withFilterAndSort_filtersAndOrdersMembers(self):
        self._login_as_admin()
        bidding_round, bid, product, period, _round_product_type = (
            self._create_closed_round_with_bid()
        )
        auto_member = MemberFactory.create(first_name="Zoe", last_name="Zander")
        current_subscription, _renewed = self._create_renewing_subscription(
            member=auto_member, product=product, period=period
        )
        inactive_member = MemberFactory.create(first_name="Anna", last_name="Anders")

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={current_subscription},
        ):
            has_bid = self.client.get(
                reverse("bidding_rounds:round_results", args=[bidding_round.id]),
                {"filter": "has_bid"},
            ).data["results_table"]["members"]
            no_bid = self.client.get(
                reverse("bidding_rounds:round_results", args=[bidding_round.id]),
                {"filter": "no_bid"},
            ).data["results_table"]["members"]
            auto_renewed = self.client.get(
                reverse("bidding_rounds:round_results", args=[bidding_round.id]),
                {"filter": "auto_renewed"},
            ).data["results_table"]["members"]
            all_members = self.client.get(
                reverse("bidding_rounds:round_results", args=[bidding_round.id]),
                {"filter": "all", "sort": "name"},
            ).data["results_table"]["members"]

        self.assertEqual([bid.member_id], [entry["member_id"] for entry in has_bid])
        self.assertEqual([auto_member.id], [entry["member_id"] for entry in no_bid])
        self.assertNotIn(inactive_member.id, [entry["member_id"] for entry in no_bid])
        self.assertEqual(
            [auto_member.id], [entry["member_id"] for entry in auto_renewed]
        )
        names = [entry["member_name"].lower() for entry in all_members]
        self.assertEqual(sorted(names), names)

    def test_results_withIncludeAutoRenewedFalse_emptiesAutoRenewedData(self):
        bidding_round, _bid, product, period, _round_product_type = (
            self._create_closed_round_with_bid()
        )
        auto_member = MemberFactory.create()
        current_subscription, _renewed = self._create_renewing_subscription(
            member=auto_member, product=product, period=period
        )

        with patch.object(
            AutomaticSubscriptionRenewalService,
            "get_subscriptions_that_will_be_renewed",
            return_value={current_subscription},
        ):
            response = self.client.get(
                reverse("bidding_rounds:round_results", args=[bidding_round.id]),
                {"include_auto_renewed": "false"},
            )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.data["auto_renewed"])
        self.assertEqual("0", response.data["auto_renewed_per_year"])

    def test_results_withBidRangePosition_usesEffectiveBidAmount(self):
        bidding_round, _bid, _product, _period, _round_product_type = (
            self._create_closed_round_with_bid(
                bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE,
                bid_levels=2,
                amounts={
                    "amount_1": Decimal("70.00"),
                    "amount_2": Decimal("90.00"),
                },
                lock=False,
            )
        )
        url = reverse("bidding_rounds:round_results", args=[bidding_round.id])

        red = self.client.get(url, {"bid_range_position": 100}).data["bids"][0]
        green = self.client.get(url, {"position": 0}).data["bids"][0]

        self.assertEqual(Decimal("90"), Decimal(red["effective_amount"]))
        self.assertEqual(Decimal("1080"), Decimal(red["amount_per_year"]))
        self.assertEqual(Decimal("70"), Decimal(green["effective_amount"]))
        self.assertEqual(Decimal("840"), Decimal(green["amount_per_year"]))

    def test_results_asNonManager_returns403(self):
        bidding_round, _bid, _product, _period, _round_product_type = (
            self._create_closed_round_with_bid()
        )
        self.client.force_login(MemberFactory.create())

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)


class TestContractSelectionViews(EvaluationApiTestBase):
    def setUp(self):
        super().setUp()
        self.admin = self._login_as_admin()

    def test_checkContracts_withUnconfirmedBid_returnsError(self):
        bidding_round, bid, product, _period, _round_product_type = (
            self._create_closed_round_with_bid()
        )
        bid.admin_confirmed = None
        bid.save()

        response = self.client.post(
            reverse("bidding_rounds:check_contracts", args=[bidding_round.id]),
            {"bid_ids": [bid.id]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, len(response.data["errors"]))
        error = response.data["errors"][0]
        self.assertEqual(bid.id, error["bid_id"])
        self.assertEqual(bid.member_id, error["member_id"])
        self.assertEqual(product.type.name, error["product_name"])
        self.assertEqual([], response.data["subscriptions"])

    def test_checkContracts_withConfirmedBid_returnsNoErrors(self):
        bidding_round, bid, _product, _period, _round_product_type = (
            self._create_closed_round_with_bid()
        )

        response = self.client.post(
            reverse("bidding_rounds:check_contracts", args=[bidding_round.id]),
            {"bid_ids": [bid.id]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.data["errors"])

    def test_createContracts_withSelection_createsOnlySelectedContracts(self):
        bidding_round, bid, product, period, round_product_type = (
            self._create_closed_round_with_bid()
        )
        other_bid = BidFactory.create(
            round=bidding_round, admin_confirmed=get_now(cache={})
        )
        BidItemFactory.create(
            bid=other_bid,
            round_product_type=round_product_type,
            product=product,
            quantity=1,
            amount_1=Decimal("90.00"),
        )
        auto_member = MemberFactory.create()
        current_subscription, renewed_subscription = self._create_renewing_subscription(
            member=auto_member, product=product, period=period
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
            response = self.client.post(
                reverse("bidding_rounds:create_contracts", args=[bidding_round.id]),
                {
                    "bid_ids": [bid.id],
                    "auto_renewed_member_ids": [auto_member.id],
                    "create_auto_renewed_contracts": True,
                },
                content_type="application/json",
            )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.data["errors"])
        created_member_ids = {
            subscription["member_id"] for subscription in response.data["subscriptions"]
        }
        self.assertIn(bid.member_id, created_member_ids)
        self.assertIn(auto_member.id, created_member_ids)
        self.assertNotIn(other_bid.member_id, created_member_ids)
        self.assertTrue(
            BiddingRoundCreatedSubscription.objects.get(
                round=bidding_round, subscription__member=bid.member
            ).is_bidder_contract
        )
        self.assertFalse(
            BiddingRoundCreatedSubscription.objects.get(
                round=bidding_round, subscription=renewed_subscription
            ).is_bidder_contract
        )
        bidding_round.refresh_from_db()
        self.assertIsNotNone(bidding_round.contracts_created_at)

    def test_createContracts_withValidationError_returnsProductName(self):
        bidding_round, bid, product, _period, _round_product_type = (
            self._create_closed_round_with_bid()
        )

        with patch.object(
            ContractCreator,
            "_create_contracts_for_bid",
            side_effect=ValidationError("Kein Vertrag möglich."),
        ):
            response = self.client.post(
                reverse("bidding_rounds:create_contracts", args=[bidding_round.id]),
                {"bid_ids": [bid.id]},
                content_type="application/json",
            )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, len(response.data["errors"]))
        self.assertEqual(product.type.name, response.data["errors"][0]["product_name"])
        self.assertEqual([], response.data["subscriptions"])
