import json
from unittest.mock import patch, Mock

from rest_framework import status
from rest_framework.reverse import reverse

from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import ProductType
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberWithSubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetMemberDeliveriesView(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)

    @patch.object(GetDeliveriesService, "get_deliveries")
    def test_getMemberDeliveriesView_accessOtherMemberDeliveriesAsNormalUser_returns403(
        self, mock_get_deliveries: Mock
    ):
        user = MemberFactory.create()
        other_member = MemberFactory.create()

        self.client.force_login(user)

        response = self.client.get(
            reverse("Deliveries:member_deliveries") + "?member_id=" + other_member.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
        mock_get_deliveries.assert_not_called()

    def test_getMemberDeliveriesView_accessOtherMemberDeliveriesAsAdmin_returnsDeliveries(
        self,
    ):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberWithSubscriptionFactory.create()
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        self.client.force_login(user)

        response = self.client.get(
            reverse("Deliveries:member_deliveries") + "?member_id=" + other_member.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_content = json.loads(response.content)
        response_content[0]["delivery_date"] = "2023-03-15"

    def test_getMemberDeliveriesView_accessOwnDeliveriesAsNormalMember_returnsDeliveries(
        self,
    ):
        user = MemberWithSubscriptionFactory.create(is_superuser=False)
        ProductType.objects.update(delivery_cycle=WEEKLY[0])
        self.client.force_login(user)

        response = self.client.get(
            reverse("Deliveries:member_deliveries") + "?member_id=" + user.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_content = json.loads(response.content)
        response_content[0]["delivery_date"] = "2023-03-15"
