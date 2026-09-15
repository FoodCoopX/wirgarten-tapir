from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_list_membersWithCompoundLastName_sortedCaseInsensitivelyByLastName(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        member_ids = {
            MemberFactory.create(last_name="Vogel").id,
            MemberFactory.create(last_name="von Adler").id,
            MemberFactory.create(last_name="Voss").id,
        }

        response = self.client.get(reverse("coop:members-list"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        last_names = [
            member["last_name"]
            for member in response.json()
            if member["id"] in member_ids
        ]
        self.assertEqual(["Vogel", "von Adler", "Voss"], last_names)
