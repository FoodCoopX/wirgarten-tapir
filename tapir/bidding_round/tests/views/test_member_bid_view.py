from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.models import Bid
from tapir.bidding_round.tests.factories import (
    BidFactory,
    BiddingRoundProductFactory,
)
from tapir.bidding_round.tests.helpers import create_open_round
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, ProductFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberBidView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_bidGet_prefilledForMember(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()
        BidFactory.create(round=round_, member=member)

        self.client.force_login(member)
        response = self.client.get(
            reverse("bidding_rounds:member_bid", args=[round_.id])
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(str(round_.id), data["round"]["id"])
        self.assertIsNotNone(data["bid"])
        self.assertEqual(str(round_product.id), data["biddable_product"]["id"])

    def test_bidPost_savesBid(self):
        round_ = create_open_round()
        round_product = BiddingRoundProductFactory.create(round=round_)
        product = ProductFactory.create(type=round_product.product_type)
        member = MemberFactory.create()

        self.client.force_login(member)
        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[round_.id]),
            data={
                "items": [
                    {
                        "round_product_id": round_product.id,
                        "product_id": product.id,
                        "quantity": 1,
                        "amount_1": "80.00",
                    }
                ]
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(1, Bid.objects.filter(round=round_, member=member).count())

    def test_bidPost_notAuthenticated_403(self):
        round_ = create_open_round()
        response = self.client.post(
            reverse("bidding_rounds:member_bid", args=[round_.id]),
            data={"items": []},
            content_type="application/json",
        )
        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
