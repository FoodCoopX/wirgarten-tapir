from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAdminSubscriptionChangeMemberSearchApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _search(self, search: str):
        return self.client.get(
            reverse("subscriptions:admin_subscription_change_member_search"),
            {"search": search},
        )

    def test_get_normalMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self._search(search=member.last_name)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_searchByFirstAndLastName_returnsMatchingMembers(self):
        self._login_as_admin()
        member = MemberFactory.create(first_name="Erika", last_name="Mustermann")
        MemberFactory.create(first_name="Max", last_name="Beispiel")

        response = self._search(search="erika muster")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([member.id], [result["id"] for result in response.json()])
        self.assertEqual("Erika Mustermann", response.json()[0]["display_name"])

    def test_get_emptySearch_returnsNothing(self):
        self._login_as_admin()
        MemberFactory.create()

        response = self._search(search=" ")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual([], response.json())
