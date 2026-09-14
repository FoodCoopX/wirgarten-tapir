from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_memberListView_sortByLastNameAscending_compoundLowercaseLastNameSortedByFirstWord(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        MemberFactory.create(last_name="Vogel")
        MemberFactory.create(last_name="von Adler")
        MemberFactory.create(last_name="Voss")
        MemberFactory.create(last_name="Ahlers")

        response = self.client.get(
            reverse("wirgarten:member_list"), {"o": "last_name_lower"}
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        last_names = [member.last_name for member in response.context["object_list"]]

        self.assertEqual(
            ["Ahlers", "Vogel", "von Adler", "Voss"],
            last_names,
        )
