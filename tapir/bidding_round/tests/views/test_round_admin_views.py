import datetime
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from tapir.associations.tests.factories import (
    AssociationMembershipTypeFactory,
    AssociationMembershipTypePriceFactory,
)
from tapir.bidding_round.config import (
    ACTIVE,
    TRAFFIC_LIGHT,
    CLOSED,
    CONFIGURATION,
    SIMPLE,
)
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRound,
    BiddingRoundProduct,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductFactory,
    BiddingRoundProductPriceFactory,
)
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now, get_today


class RoundAdminViewTestBase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))


class TestRoundListCreateView(RoundAdminViewTestBase):
    def test_roundCreate_createsConfigurationRound(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "bidding_procedure": "simple",
                "end_at": "2026-12-31T23:59:00+01:00",
                "product_type_id": product_type.id,
            },
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_201_CREATED)
        self.assertEqual(CONFIGURATION, response.json()["status"])

    def test_roundCreate_withBidLevels_storesBidLevels(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "bidding_procedure": "simple",
                "bid_levels": 3,
                "end_at": "2026-12-31T23:59:00+01:00",
                "product_type_id": product_type.id,
            },
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_201_CREATED)
        round_ = BiddingRound.objects.get(id=response.json()["id"])
        self.assertEqual(3, round_.bid_levels)

    def test_roundCreate_withProductType_createsBiddingRoundProduct(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "bidding_procedure": "simple",
                "end_at": "2026-12-31T23:59:00+01:00",
                "product_type_id": product_type.id,
            },
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_201_CREATED)
        round_ = BiddingRound.objects.get(id=response.json()["id"])
        self.assertEqual(
            [product_type.id],
            list(round_.products.values_list("product_type_id", flat=True)),
        )

    def test_roundCreate_withoutProductType_defaultsToTheOnlyProductType(self):
        growing_period = GrowingPeriodFactory.create()
        capacity = ProductCapacityFactory.create(period=growing_period)
        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "bidding_procedure": "simple",
                "end_at": "2026-12-31T23:59:00+01:00",
            },
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_201_CREATED)
        round_ = BiddingRound.objects.get(id=response.json()["id"])
        self.assertEqual(
            [capacity.product_type_id],
            list(round_.products.values_list("product_type_id", flat=True)),
        )

    def test_roundCreate_withValues_storesValues(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        product = ProductFactory.create(type=product_type)
        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "bidding_procedure": "simple",
                "end_at": "2026-12-31T23:59:00+01:00",
                "product_type_id": product_type.id,
                "target_amount_per_year": "1000.00",
                "prices": [
                    {
                        "product_id": product.id,
                        "reference_value": "80.00",
                        "min_amount": "60.00",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_201_CREATED)
        round_ = BiddingRound.objects.get(id=response.json()["id"])
        round_product = round_.products.get()
        self.assertEqual(Decimal("1000.00"), round_product.target_amount_per_year)
        price = BiddingRoundProductPrice.objects.get(
            round_product=round_product, product=product
        )
        self.assertEqual(Decimal("80.00"), price.reference_value)
        self.assertEqual(Decimal("60.00"), price.min_amount)
        self.assertEqual(
            "80.00", response.json()["product"]["prices"][0]["reference_value"]
        )

    def test_roundList_returnsRounds(self):
        BiddingRoundFactory.create()
        response = self.client.get(reverse("bidding_rounds:round_list_create"))
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, len(response.json()))


class TestGrowingPeriodsView(RoundAdminViewTestBase):
    def test_growingPeriods_returnsUpcomingPeriods(self):
        past_period = GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=800),
            end_date=get_today() - datetime.timedelta(days=400),
        )
        future_period = GrowingPeriodFactory.create(
            start_date=get_today() + datetime.timedelta(days=100),
            end_date=get_today() + datetime.timedelta(days=465),
        )
        response = self.client.get(reverse("bidding_rounds:growing_periods"))
        self.assertStatusCode(response, status.HTTP_200_OK)
        ids = [entry["id"] for entry in response.json()]
        self.assertIn(future_period.id, ids)
        self.assertNotIn(past_period.id, ids)


class TestAvailableProductTypesView(RoundAdminViewTestBase):
    def test_availableProductTypes_returnsTypesWithCapacityForPeriod(self):
        growing_period = GrowingPeriodFactory.create()
        capacity = ProductCapacityFactory.create(period=growing_period)
        product = ProductFactory.create(type=capacity.product_type)
        response = self.client.get(
            reverse("bidding_rounds:available_product_types"),
            {"growing_period_id": growing_period.id},
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(1, len(body))
        self.assertEqual(capacity.product_type.id, body[0]["id"])
        self.assertEqual(capacity.product_type.name, body[0]["name"])
        self.assertEqual(1, len(body[0]["products"]))
        self.assertEqual(product.id, body[0]["products"][0]["id"])
        self.assertEqual(product.name, body[0]["products"][0]["name"])
        self.assertIn("size", body[0]["products"][0])


class TestRoundDetailView(RoundAdminViewTestBase):
    def test_roundPatch_editsNameInAnyStatus(self):
        round_ = BiddingRoundFactory.create()
        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"name": "Umbenannt"},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual("Umbenannt", round_.name)

        round_.status = ACTIVE
        round_.save()
        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"name": "Nochmal"},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual("Nochmal", round_.name)

    def test_roundPatch_editsBiddingProcedureWithoutBids(self):
        round_ = BiddingRoundFactory.create()
        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"bidding_procedure": "traffic_light"},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual("traffic_light", round_.bidding_procedure)

    def test_roundPatch_biddingProcedureWithBids_rejects(self):
        round_ = BiddingRoundFactory.create()
        BidFactory.create(round=round_, member=MemberFactory.create())
        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"bidding_procedure": "traffic_light"},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_roundPatch_productTypeWithBids_rejects(self):
        round_ = BiddingRoundFactory.create()
        BidFactory.create(round=round_, member=MemberFactory.create())
        product_type = ProductFactory.create().type
        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"product_type_id": product_type.id},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_roundPatch_namesStillEditableWithBids(self):
        round_ = BiddingRoundFactory.create()
        BidFactory.create(round=round_, member=MemberFactory.create())
        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"name": "Umbenannt"},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual("Umbenannt", round_.name)

    def test_roundPatch_updatesValues(self):
        round_ = BiddingRoundFactory.create()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={
                "target_amount_per_year": "500.00",
                "prices": [
                    {
                        "product_id": product.id,
                        "reference_value": "70.00",
                        "min_amount": "50.00",
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        round_product.refresh_from_db()
        self.assertEqual(Decimal("500.00"), round_product.target_amount_per_year)
        price = BiddingRoundProductPrice.objects.get(
            round_product=round_product, product=product
        )
        self.assertEqual(Decimal("70.00"), price.reference_value)
        self.assertEqual(Decimal("50.00"), price.min_amount)

    def test_roundPatch_valuesWithBids_rejects(self):
        round_ = BiddingRoundFactory.create()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        BidFactory.create(round=round_, member=MemberFactory.create())

        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={"prices": [{"product_id": product.id, "reference_value": "70.00"}]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_roundPatch_wrongProductForPrices_rejects(self):
        round_ = BiddingRoundFactory.create()
        BiddingRoundProductFactory.create(round=round_)
        other_product = ProductFactory.create()

        response = self.client.patch(
            reverse("bidding_rounds:round_detail", args=[round_.id]),
            data={
                "prices": [{"product_id": other_product.id, "reference_value": "70.00"}]
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_roundDelete_configurationRound_succeeds(self):
        round_ = BiddingRoundFactory.create()
        response = self.client.delete(
            reverse("bidding_rounds:round_detail", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BiddingRound.objects.filter(id=round_.id).exists())

    def test_roundDelete_activeRound_rejects(self):
        round_ = BiddingRoundFactory.create(status=ACTIVE)
        response = self.client.delete(
            reverse("bidding_rounds:round_detail", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(BiddingRound.objects.filter(id=round_.id).exists())

    def test_roundDelete_closedRound_succeeds(self):
        round_ = BiddingRoundFactory.create(status=CLOSED)
        response = self.client.delete(
            reverse("bidding_rounds:round_detail", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BiddingRound.objects.filter(id=round_.id).exists())

    def test_roundDelete_closedRoundWithBids_succeeds(self):
        round_ = BiddingRoundFactory.create(status=CLOSED)
        bid = BidFactory.create(round=round_, member=MemberFactory.create())
        bid_id = bid.id
        response = self.client.delete(
            reverse("bidding_rounds:round_detail", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BiddingRound.objects.filter(id=round_.id).exists())
        self.assertFalse(Bid.objects.filter(id=bid_id).exists())


class TestRoundStartView(RoundAdminViewTestBase):
    def _create_round_with_target(self):
        round_ = BiddingRoundFactory.create()
        round_product = BiddingRoundProductFactory.create(round=round_)
        round_product.target_amount_per_year = Decimal("1000.00")
        round_product.save()
        return round_

    def test_roundStart_transitionsToActive(self):
        round_ = self._create_round_with_target()
        response = self.client.post(
            reverse("bidding_rounds:round_start", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual(ACTIVE, round_.status)

    def test_roundStart_withoutTargetAmount_rejects(self):
        round_ = BiddingRoundFactory.create()
        BiddingRoundProductFactory.create(round=round_)
        response = self.client.post(
            reverse("bidding_rounds:round_start", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        round_.refresh_from_db()
        self.assertEqual(CONFIGURATION, round_.status)

    def test_roundStart_withAnotherActiveRound_rejects(self):
        active_round = BiddingRoundFactory.create(status=ACTIVE)
        round_ = self._create_round_with_target()
        response = self.client.post(
            reverse("bidding_rounds:round_start", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        round_.refresh_from_db()
        self.assertEqual(CONFIGURATION, round_.status)
        active_round.refresh_from_db()
        self.assertEqual(ACTIVE, active_round.status)


class TestRoundCloseView(RoundAdminViewTestBase):
    def test_roundClose_transitionsToClosed(self):
        round_ = BiddingRoundFactory.create(status=ACTIVE)
        response = self.client.post(
            reverse("bidding_rounds:round_close", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual(CLOSED, round_.status)


class TestRoundReopenView(RoundAdminViewTestBase):
    def test_roundReopen_transitionsToActive(self):
        round_ = BiddingRoundFactory.create(status=CLOSED)
        response = self.client.post(
            reverse("bidding_rounds:round_reopen", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertEqual(ACTIVE, round_.status)

    def test_roundReopen_withAnotherActiveRound_rejects(self):
        active_round = BiddingRoundFactory.create(status=ACTIVE)
        round_ = BiddingRoundFactory.create(status=CLOSED)
        response = self.client.post(
            reverse("bidding_rounds:round_reopen", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        round_.refresh_from_db()
        self.assertEqual(CLOSED, round_.status)
        active_round.refresh_from_db()
        self.assertEqual(ACTIVE, active_round.status)


class TestRoundResultsView(RoundAdminViewTestBase):
    def test_results_listsBidsAndStats(self):
        round_ = create_open_round()
        round_.include_auto_renewed = False
        round_.save()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member)
        BidItemFactory.create(bid=bid, round_product=round_product, product=product)

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(1, len(data["stats"]))
        member_entries = [
            entry
            for entry in data["results_table"]["members"]
            if entry["member_id"] == member.id
        ]
        self.assertEqual(1, len(member_entries))
        self.assertTrue(member_entries[0]["has_bid"])

    def test_results_returnsBiddableProductsAndPickupLocations(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        ProductPriceFactory.create(product=product, price=Decimal("60.00"), size=1)

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            str(round_product.id),
            data["biddable_product"]["id"],
        )
        self.assertEqual(
            product.id,
            data["biddable_product"]["products"][0]["id"],
        )

    def test_results_returnsTotalsAndShares(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00"), capacity=100
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="50.00")],
            cache={},
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(Decimal("1000.00"), Decimal(data["totals"]["target_per_year"]))
        self.assertEqual(Decimal("100"), Decimal(data["totals"]["target_shares"]))
        self.assertEqual(
            Decimal("600.00"), Decimal(data["stats"][0]["reached_per_year"])
        )

    def test_results_traffic_lightPosition_usesInterpolatedAmount(self):
        round_ = create_open_round()
        round_.bidding_procedure = TRAFFIC_LIGHT
        round_.save()
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

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id]),
            {"traffic_light_position": 25},
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(25.0, data["traffic_light_position"])
        self.assertEqual("traffic_light", data["bidding_procedure"])
        self.assertEqual(
            Decimal("840.00"), Decimal(data["stats"][0]["reached_per_year"])
        )
        self.assertIsNotNone(data["financing_projection"])

    def test_results_traffic_lightPosition_nonAmpelRound_hasFinancingProjectionWithEqualLevels(
        self,
    ):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="80.00")],
            cache={},
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(SIMPLE, data["bidding_procedure"])
        self.assertIsNotNone(data["financing_projection"])
        levels = data["financing_projection"]["levels"]
        self.assertEqual(
            float(levels["green"]["reached_per_year"]),
            float(levels["yellow"]["reached_per_year"]),
        )
        self.assertEqual(
            float(levels["yellow"]["reached_per_year"]),
            float(levels["red"]["reached_per_year"]),
        )

    def test_results_simpleLevels_returnsBidLevelsAndRecommendedLevel(self):
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

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(3, data["bid_levels"])
        self.assertEqual(2, data["recommended_level"])
        self.assertEqual(50.0, data["traffic_light_position"])

    @patch.object(BiddingRoundStatsService, "get_default_position", autospec=True)
    def test_results_simpleRound_doesNotLookUpDefaultPositionPerBid(
        self, mock_get_default_position
    ):
        mock_get_default_position.return_value = 50
        round_ = create_open_round(bid_levels=3)
        round_product, product = create_round_product_with_product(round_)
        for _ in range(5):
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

        mock_get_default_position.reset_mock()
        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        # The default position is resolved once per request (average bid), not
        # once per bid item (regression: this used to hang on large rounds).
        self.assertLessEqual(mock_get_default_position.call_count, 2)

    def test_results_returnsAverageBid(self):
        round_ = create_open_round()
        create_round_product_with_product(
            round_, target_amount_per_year=Decimal("220800.00"), capacity=230
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        average_bid = response.json()["average_bid"]
        self.assertEqual(
            Decimal("80.00"), Decimal(average_bid["amount_per_share_per_month"])
        )
        self.assertEqual(
            Decimal("960.00"), Decimal(average_bid["amount_per_share_per_year"])
        )

    def test_results_returnsExtraPositions(self):
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

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("extra_positions", data)
        self.assertIn("membership", data["extra_positions"])
        self.assertIn("delivery_charge", data["extra_positions"])
        self.assertEqual(Decimal("600.00"), Decimal(data["totals"]["reached_per_year"]))

    def test_results_membershipIncludedInProductType_ignoresMembership(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_STATS_MEMBERSHIP_INCLUDED_IN_PRODUCT_TYPE
        ).update(value="true")
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)

        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, target_amount_per_year=Decimal("1000.00")
        )
        membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipTypePriceFactory.create(
            type=membership_type,
            price=Decimal("10.00"),
            valid_from=round_.growing_period.start_date,
        )
        member = MemberFactory.create()
        BiddingRoundService.save_bid(
            member,
            round_,
            [build_item(round_product, product, amount_1="50.00")],
            cache={},
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(
            Decimal("600.00"), Decimal(data["stats"][0]["reached_per_year"])
        )
        self.assertFalse(data["extra_positions"]["membership"]["applicable"])

    def test_results_filterNoBid_excludesBiddersAndInactiveMembers(self):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_)
        bidder = MemberFactory.create()
        active_non_bidder = MemberFactory.create()
        SubscriptionFactory.create(
            member=active_non_bidder,
            period=round_.growing_period,
            product=product,
        )
        inactive_member = MemberFactory.create()
        BiddingRoundService.save_bid(
            bidder, round_, [build_item(round_product, product)], cache={}
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id]),
            {"filter": "no_bid"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        member_ids = [
            entry["member_id"] for entry in response.json()["results_table"]["members"]
        ]
        self.assertIn(active_non_bidder.id, member_ids)
        self.assertNotIn(bidder.id, member_ids)
        self.assertNotIn(inactive_member.id, member_ids)

    @patch.object(
        AutomaticSubscriptionRenewalService,
        "get_subscriptions_that_will_be_renewed",
        autospec=True,
    )
    def test_results_includeAutoRenewedOverride_changesStats(self, mock_get):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_,
            reference_value=Decimal("70.00"),
            target_amount_per_year=Decimal("1000.00"),
        )
        member = MemberFactory.create()
        auto_product = ProductFactory.create(type=round_product.product_type)
        BiddingRoundProductPriceFactory.create(
            round_product=round_product,
            product=auto_product,
            reference_value=Decimal("70.00"),
        )
        subscription = SubscriptionFactory.create(
            member=member, product=auto_product, quantity=1
        )
        mock_get.return_value = {subscription}

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id]),
            {"include_auto_renewed": "true"},
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            Decimal("840.00"),
            Decimal(response.json()["stats"][0]["reached_per_year"]),
        )

        response = self.client.get(
            reverse("bidding_rounds:round_results", args=[round_.id]),
            {"include_auto_renewed": "false"},
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            Decimal("0.00"),
            Decimal(response.json()["stats"][0]["reached_per_year"]),
        )


class TestBidCreateView(RoundAdminViewTestBase):
    def test_createBid_enteredByAdmin_createsBidWithItems(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()

        response = self.client.post(
            reverse("bidding_rounds:bid_create", args=[round_.id]),
            data={
                "member_id": member.id,
                "items": [build_item(round_product, product, amount_1="75.00")],
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_201_CREATED)
        bid = Bid.objects.get(round=round_, member=member)
        self.assertTrue(bid.entered_by_admin)
        self.assertEqual(1, bid.items.count())
        self.assertEqual(Decimal("75.00"), bid.items.get().amount_1)

    def test_createBid_duplicate_rejects(self):
        round_ = create_open_round()
        bid = BidFactory.create(round=round_, member=MemberFactory.create())
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        response = self.client.post(
            reverse("bidding_rounds:bid_create", args=[round_.id]),
            data={
                "member_id": bid.member_id,
                "items": [build_item(round_product, product)],
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_createBid_withoutMemberId_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)

        response = self.client.post(
            reverse("bidding_rounds:bid_create", args=[round_.id]),
            data={"items": [build_item(round_product, product)]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_createBid_withWrongProductType_rejects(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        other_product = ProductFactory.create()
        member = MemberFactory.create()

        response = self.client.post(
            reverse("bidding_rounds:bid_create", args=[round_.id]),
            data={
                "member_id": member.id,
                "items": [build_item(round_product, other_product)],
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)


class TestBidEditView(RoundAdminViewTestBase):
    def test_patchBid_editsIncludingPickupLocation(self):
        round_ = create_open_round()
        bid = BidFactory.create(round=round_, member=MemberFactory.create())
        pickup_location = PickupLocationFactory.create()

        response = self.client.patch(
            reverse("bidding_rounds:bid_edit", args=[round_.id, bid.id]),
            data={"pickup_location_id": pickup_location.id},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        bid.refresh_from_db()
        self.assertEqual(pickup_location, bid.pickup_location)

    def test_patchBid_replacesItems(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        bid = BidFactory.create(round=round_, member=MemberFactory.create())

        response = self.client.patch(
            reverse("bidding_rounds:bid_edit", args=[round_.id, bid.id]),
            data={"items": [build_item(round_product, product, amount_1="90.00")]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        bid.refresh_from_db()
        self.assertEqual(1, bid.items.count())
        self.assertEqual(Decimal("90.00"), bid.items.get().amount_1)

    def test_patchBid_setsAndClearsAdminConfirmed(self):
        round_ = create_open_round()
        bid = BidFactory.create(round=round_, member=MemberFactory.create())

        response = self.client.patch(
            reverse("bidding_rounds:bid_edit", args=[round_.id, bid.id]),
            data={"admin_confirmed": True},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        bid.refresh_from_db()
        self.assertIsNotNone(bid.admin_confirmed)

        response = self.client.patch(
            reverse("bidding_rounds:bid_edit", args=[round_.id, bid.id]),
            data={"admin_confirmed": False},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_200_OK)
        bid.refresh_from_db()
        self.assertIsNone(bid.admin_confirmed)

    def test_deleteBid_succeeds(self):
        round_ = create_open_round()
        bid = BidFactory.create(round=round_, member=MemberFactory.create())

        response = self.client.delete(
            reverse("bidding_rounds:bid_edit", args=[round_.id, bid.id])
        )

        self.assertStatusCode(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Bid.objects.filter(id=bid.id).exists())

    def test_deleteBid_afterContractsCreated_rejects(self):
        round_ = create_open_round()
        round_.contracts_created_at = get_now()
        round_.save()
        bid = BidFactory.create(round=round_, member=MemberFactory.create())

        response = self.client.delete(
            reverse("bidding_rounds:bid_edit", args=[round_.id, bid.id])
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Bid.objects.filter(id=bid.id).exists())


class TestConfirmBidsView(RoundAdminViewTestBase):
    def test_confirmBids_setsAdminConfirmed(self):
        round_ = create_open_round()
        bid_1 = BidFactory.create(round=round_, member=MemberFactory.create())
        bid_2 = BidFactory.create(round=round_, member=MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:confirm_bids", args=[round_.id]),
            data={"bid_ids": [bid_1.id, bid_2.id]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        bid_1.refresh_from_db()
        bid_2.refresh_from_db()
        self.assertIsNotNone(bid_1.admin_confirmed)
        self.assertIsNotNone(bid_2.admin_confirmed)


class TestCreateContractsView(RoundAdminViewTestBase):
    @patch.object(
        GlobalCapacityChecker,
        "get_product_type_ids_without_enough_capacity_for_order",
        return_value=[],
    )
    def test_createContracts_selectedBids(self, mock_capacity):
        round_ = BiddingRoundFactory.create(
            status=CLOSED,
            end_at=get_now() - datetime.timedelta(days=1),
        )
        round_.average_bid_locked_at = get_now()
        round_.locked_traffic_light_position = Decimal("50")
        round_.locked_surcharge_percent = Decimal("0")
        round_.locked_average_bid_per_share_per_month = Decimal("0")
        round_.locked_average_bid_per_share_per_year = Decimal("0")
        round_.save()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("60.00"),
            size=1,
            valid_from=round_.growing_period.start_date,
        )
        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member, admin_confirmed=get_now())
        BidItemFactory.create(
            bid=bid,
            round_product=round_product,
            product=product,
            amount_1=Decimal("80.00"),
        )

        response = self.client.post(
            reverse("bidding_rounds:create_contracts", args=[round_.id]),
            data={"bid_ids": [bid.id]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json()["errors"])
        self.assertEqual(
            1,
            Subscription.objects.filter(
                member=member, period=round_.growing_period
            ).count(),
        )

    def test_createContracts_requiresClosedRound(self):
        round_ = create_open_round()
        response = self.client.post(
            reverse("bidding_rounds:create_contracts", args=[round_.id]),
            data={},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)


class TestAverageBidLockViews(RoundAdminViewTestBase):
    def _prepare_round(self):
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
        return round_

    def test_lockAverageBid_storesLock(self):
        round_ = self._prepare_round()

        response = self.client.post(
            reverse("bidding_rounds:lock_average_bid", args=[round_.id]),
            data={
                "position": 70,
                "surcharge_percent": 10,
                "surcharge_on_bids": True,
                "surcharge_on_average": True,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertIsNotNone(round_.average_bid_locked_at)
        self.assertEqual(Decimal("70.00"), round_.locked_traffic_light_position)

    def test_lockAverageBid_alreadyLocked_returns400(self):
        round_ = self._prepare_round()
        BiddingRoundService.lock_average_bid(round_, 50, 0, False, False, cache={})

        response = self.client.post(
            reverse("bidding_rounds:lock_average_bid", args=[round_.id]),
            data={"position": 60},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_unlockAverageBid_afterContractsCreated_returns400(self):
        round_ = self._prepare_round()
        round_.average_bid_locked_at = get_now()
        round_.locked_traffic_light_position = Decimal("50")
        round_.contracts_created_at = get_now()
        round_.save()

        response = self.client.post(
            reverse("bidding_rounds:unlock_average_bid", args=[round_.id]),
            data={},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_unlockAverageBid_withoutContracts_clearsLock(self):
        round_ = self._prepare_round()
        BiddingRoundService.lock_average_bid(round_, 50, 0, False, False, cache={})

        response = self.client.post(
            reverse("bidding_rounds:unlock_average_bid", args=[round_.id]),
            data={},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        round_.refresh_from_db()
        self.assertIsNone(round_.average_bid_locked_at)

    def test_deleteContracts_withoutContracts_returns400(self):
        round_ = self._prepare_round()

        response = self.client.post(
            reverse("bidding_rounds:delete_contracts", args=[round_.id]),
            data={},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)


class TestExportCsvView(RoundAdminViewTestBase):
    def test_exportCsv_containsHeaderAndRows(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member)
        BidItemFactory.create(bid=bid, round_product=round_product, product=product)

        response = self.client.get(
            reverse("bidding_rounds:export_csv", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        content = response.content.decode("utf-8")
        self.assertIn("Mitglied", content)
        self.assertIn(product.name, content)
