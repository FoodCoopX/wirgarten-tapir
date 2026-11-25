import datetime

from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.tests.factories import BiddingRoundProductPriceFactory
from tapir.bidding_round.tests.helpers import (
    bid_payload,
    create_open_round,
    get_product_for_round,
    bid_range_payload,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.accounts.models import TapirUser
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class BiddingRoundApiTestBase(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _enable(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        self._set_parameter(ParameterKeys.BIDDING_ROUND_URL_ENABLED, True)


class TestPublicDataView(BiddingRoundApiTestBase):
    def test_publicData_withoutActiveRound_reportsEnded(self):
        self._enable()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("ended", response.data["round_status"])
        self.assertIsNone(response.data["round"])

    def test_publicData_withProductWithoutPrice_hidesTheProduct(self):
        self._enable()
        bidding_round = create_open_round()
        ProductFactory.create(type=bidding_round.product_type)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, len(response.data["biddable_product"]["products"]))

    def test_publicData_withActiveRound_returnsRoundAndProduct(self):
        self._enable()
        create_open_round()

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("active", response.data["round_status"])
        self.assertEqual(1, len(response.data["biddable_product"]["products"]))
        self.assertEqual(
            "90.00", response.data["biddable_product"]["products"][0]["reference_value"]
        )


class TestMemberBidView(BiddingRoundApiTestBase):
    def test_get_loggedInWithoutMember_returns403(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(
            TapirUser.objects.create(
                username="staff",
                first_name="Staff",
                last_name="Account",
                email="staff@example.com",
            )
        )

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_anonymous_returns401(self):
        self._enable()
        bidding_round = create_open_round()

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_401_UNAUTHORIZED)

    def test_post_validBid_storesBid(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, quantity=2),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        get_response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )
        self.assertStatusCode(get_response, status.HTTP_200_OK)
        bid = get_response.data["bid"]
        self.assertEqual("80.00", bid["amount_1"])
        self.assertEqual(2, bid["quantity"])
        self.assertEqual("1920.00", bid["amount_per_year"])
        self.assertEqual("1920.00", bid["total_per_year"])
        self.assertEqual(get_product_for_round(bidding_round).id, bid["product_id"])

    def test_post_bidRangeBid_storesTwoAmounts(self):
        self._enable()
        bidding_round = create_open_round(
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE, bid_levels=2
        )
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_range_payload(bidding_round, quantity=2),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        bid = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        ).data["bid"]
        self.assertEqual("70.00", bid["amount_1"])
        self.assertEqual("90.00", bid["amount_2"])
        self.assertIsNone(bid["amount_3"])
        self.assertEqual(2, bid["quantity"])

    def test_post_quantityOutOfRange_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, quantity=6),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_get_withExistingSubscription_returnsCurrentQuantity(self):
        self._enable()
        bidding_round = create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member,
            product=get_product_for_round(bidding_round),
            period=bidding_round.growing_period,
            quantity=2,
            start_date=bidding_round.growing_period.start_date,
            end_date=bidding_round.growing_period.end_date,
        )

        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            2,
            response.data["biddable_product"]["products"][0]["current_quantity"],
        )

    def test_post_amountBelowMinimum_returns400(self):
        self._enable()
        bidding_round = create_open_round()
        self.client.force_login(MemberFactory.create())

        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[bidding_round.id]),
            data=bid_payload(bidding_round, amount="10.00"),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)


class TestRoundAdminViews(BiddingRoundApiTestBase):
    def setUp(self):
        super().setUp()
        self._enable()
        self.client.force_login(MemberFactory.create(is_superuser=True, is_staff=True))

    def test_listAndCreate_returnsRound(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()

        create_response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "end_at": (get_now(cache={}) + datetime.timedelta(days=1)).isoformat(),
                "product_type_id": product_type.id,
                "target_amount_per_year": "1000.00",
            },
            content_type="application/json",
        )

        self.assertStatusCode(create_response, status.HTTP_201_CREATED)
        list_response = self.client.get(reverse("bidding_rounds:round_list_create"))
        self.assertStatusCode(list_response, status.HTTP_200_OK)
        self.assertEqual(1, len(list_response.data))

    def test_listAndCreate_withoutProductType_usesTheOnlyProductTypeWithCapacity(
        self,
    ):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        ProductCapacityFactory.create(
            period=growing_period, product_type=product_type, capacity=1000
        )

        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "end_at": (get_now(cache={}) + datetime.timedelta(days=1)).isoformat(),
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_201_CREATED)
        self.assertEqual(product_type.id, response.data["product"]["product_type_id"])

    def test_listAndCreate_withoutProductTypeAndAmbiguousCapacity_returns400(self):
        growing_period = GrowingPeriodFactory.create()
        for _ in range(2):
            ProductCapacityFactory.create(period=growing_period, capacity=1000)

        response = self.client.post(
            reverse("bidding_rounds:round_list_create"),
            data={
                "growing_period_id": growing_period.id,
                "name": "Beitragsrunde Test",
                "end_at": (get_now(cache={}) + datetime.timedelta(days=1)).isoformat(),
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

    def test_startCloseAndResults(self):
        growing_period = GrowingPeriodFactory.create()
        product_type = ProductTypeFactory.create()
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name="Beitragsrunde Test",
            end_at=get_now(cache={}) + datetime.timedelta(days=1),
            product_type_id=product_type.id,
            target_amount_per_year="1000.00",
            cache={},
        )
        BiddingRoundProductPriceFactory.create(
            round=bidding_round,
            product=ProductFactory.create(type=product_type),
        )

        start_response = self.client.post(
            reverse("bidding_rounds:round_start", args=[bidding_round.id])
        )
        self.assertStatusCode(start_response, status.HTTP_200_OK)
        self.assertEqual("active", start_response.data["status"])

        close_response = self.client.post(
            reverse("bidding_rounds:round_close", args=[bidding_round.id])
        )
        self.assertStatusCode(close_response, status.HTTP_200_OK)

        results_response = self.client.get(
            reverse("bidding_rounds:round_results", args=[bidding_round.id])
        )
        self.assertStatusCode(results_response, status.HTTP_200_OK)
        self.assertEqual("1000.00", results_response.data["target_per_year"])
        self.assertEqual(0, results_response.data["bidder_count"])
