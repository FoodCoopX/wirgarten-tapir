from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.config import ACTIVE, CLOSED
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BidItemFactory,
    BiddingRoundFactory,
    BiddingRoundProductFactory,
)
from tapir.bidding_round.tests.helpers import create_open_round
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPublicDataView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        TapirParameter.objects.filter(key=ParameterKeys.BIDDING_ROUND_ENABLED).update(
            value="true"
        )

    def test_publicData_flagsAndRoundAndTexts(self):
        round_ = create_open_round()
        BiddingRoundProductFactory.create(round=round_)

        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["enabled"])
        self.assertEqual(str(round_.id), data["round"]["id"])
        self.assertEqual("active", data["round_status"])
        self.assertTrue(data["texts"]["intro_title"])
        self.assertTrue(data["texts"]["bid"]["quantity_label"])

    def test_publicData_bidOptions_defaultToFalse(self):
        create_open_round()
        response = self.client.get(reverse("bidding_rounds:public_data"))
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(response.json()["bid_options"]["quantity_enabled"])

        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_BID_QUANTITY_ENABLED
        ).update(value="true")
        response = self.client.get(reverse("bidding_rounds:public_data"))
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.json()["bid_options"]["quantity_enabled"])

    def test_publicData_noOpenRound_returnsEndedState(self):
        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertIsNone(data["round"])
        self.assertEqual("ended", data["round_status"])

    def test_publicData_pickupLocationsOnlyWhenFeatureEnabled(self):
        round_ = create_open_round()
        pickup_location = PickupLocationFactory.create()

        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="false")
        response = self.client.get(reverse("bidding_rounds:public_data"))
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json()["pickup_locations"])

        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        response = self.client.get(reverse("bidding_rounds:public_data"))
        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertIn(
            pickup_location.id,
            [entry["id"] for entry in response.json()["pickup_locations"]],
        )

    def test_publicData_authenticatedMember_returnsExistingBid(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member)
        BidItemFactory.create(bid=bid, round_product=round_product, product=product)

        self.client.force_login(member)
        response = self.client.get(reverse("bidding_rounds:public_data"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(str(bid.id), response.json()["bid"]["id"])


class TestPublicResultsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        TapirParameter.objects.filter(key=ParameterKeys.BIDDING_ROUND_ENABLED).update(
            value="true"
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_URL_ENABLED
        ).update(value="true")

    def test_publicResults_returnsReducedEvaluation(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=member)
        BidItemFactory.create(bid=bid, round_product=round_product, product=product)

        response = self.client.get(
            reverse("bidding_rounds:public_results", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual("simple", data["bidding_procedure"])
        self.assertEqual(1, data["bid_levels"])
        self.assertIn("utilization_percent", data)
        self.assertIn("current_shares", data)
        self.assertIn("capacity_shares", data)
        self.assertIn("green", data["levels"])
        self.assertIn("current_coverage_percent", data["levels"]["green"])
        # Internal financing details are not exposed.
        self.assertNotIn("membership_per_year", data)
        self.assertNotIn("delivery_charge_per_year", data)
        self.assertNotIn("auto_shares", data)
        self.assertNotIn("remaining_shares", data)

    def test_publicResults_requiresAktivRound(self):
        round_ = BiddingRoundFactory.create(status=CLOSED)
        response = self.client.get(
            reverse("bidding_rounds:public_results", args=[round_.id])
        )
        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
