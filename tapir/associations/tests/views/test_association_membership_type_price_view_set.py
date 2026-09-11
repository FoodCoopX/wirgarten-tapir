from django.urls import reverse
from rest_framework import status

from tapir.associations.tests.factories import (
    AssociationMembershipTypePriceFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssociationMembershipTypePriceViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_list_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(
            reverse("associations:association_membership_types_price-list")
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_list_loggedInAsAdmin_returnsCorrectData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        prices = AssociationMembershipTypePriceFactory.create_batch(size=3)

        response = self.client.get(
            reverse("associations:association_membership_types_price-list")
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        price_ids = {price.id for price in prices}
        self.assertEqual(price_ids, {price["id"] for price in response_content})
