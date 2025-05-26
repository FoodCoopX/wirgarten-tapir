import datetime
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.subscriptions.views import GetCancellationDataView
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGet(TapirIntegrationTest):
    maxDiff = 2000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def setUp(self) -> None:
        mock_timezone(self, datetime.datetime(year=2023, month=2, day=15))

    def test_get_normalMemberAsksForOwnData_returnsCorrectData(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        subscriptions = SubscriptionFactory.create_batch(size=3, member=member)

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        returned_product_ids = [
            subscribed_product["product"]["id"]
            for subscribed_product in response_content["subscribed_products"]
        ]
        expected_product_ids = [
            subscription.product.id for subscription in subscriptions
        ]
        self.assertCountEqual(expected_product_ids, returned_product_ids)

    def test_get_normalMemberAsksForDataOfOtherMember_returnsStatus403(
        self,
    ):
        user = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={other_member.id}")

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    @patch.object(GetCancellationDataView, "build_subscribed_products_data")
    @patch.object(MembershipCancellationManager, "can_member_cancel_coop_membership")
    def test_get_adminAsksForDataOfOtherMember_returnsStatus200(self, *_):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("subscriptions:cancellation_data")
        response = self.client.get(f"{url}?member_id={other_member.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
