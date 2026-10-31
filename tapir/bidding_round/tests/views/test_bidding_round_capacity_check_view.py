from decimal import Decimal

import uuid

from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.tests.factories import BidFactory, BidItemFactory
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, ProductPriceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundCapacityCheckView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.BIDDING_ROUND_ENABLED).update(
            value="true"
        )

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create())

    def _build_round(self, capacity):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, capacity=capacity
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=round_.growing_period.start_date,
        )
        return round_, round_product, product

    def test_capacityCheck_enoughCapacity_returnsSufficient(self):
        round_, round_product, product = self._build_round(capacity=100)

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[round_.id]),
            data={"items": [build_item(round_product, product, quantity=1)]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["sufficient"])
        self.assertEqual("", data["message"])

    def test_capacityCheck_notEnoughCapacityByOtherBid_returnsMessage(self):
        round_, round_product, product = self._build_round(capacity=1)
        other_member = MemberFactory.create()
        bid = BidFactory.create(round=round_, member=other_member)
        BidItemFactory.create(
            bid=bid, round_product=round_product, product=product, quantity=1
        )

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[round_.id]),
            data={"items": [build_item(round_product, product, quantity=1)]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertFalse(data["sufficient"])
        self.assertNotEqual("", data["message"])

    def test_capacityCheck_featureDisabled_returns404(self):
        round_, round_product, product = self._build_round(capacity=100)
        TapirParameter.objects.filter(key=ParameterKeys.BIDDING_ROUND_ENABLED).update(
            value="false"
        )

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[round_.id]),
            data={"items": [build_item(round_product, product, quantity=1)]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_capacityCheck_roundIdNotTheOpenRound_returns404(self):
        self._build_round(capacity=100)

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[uuid.uuid4()]),
            data={"items": []},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_capacityCheck_invalidItems_returns400(self):
        round_, round_product, product = self._build_round(capacity=100)

        response = self.client.post(
            reverse("bidding_rounds:capacity_check", args=[round_.id]),
            data={"items": [{"quantity": 1}]},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
