from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_list_membersWithCompoundLastNameAndNoMemberNumber_sortedCaseInsensitivelyByLastName(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        vogel = MemberFactory.create(last_name="Vogel")
        von_adler = MemberFactory.create(last_name="von Adler")
        voss = MemberFactory.create(last_name="Voss")
        member_ids = {vogel.id, von_adler.id, voss.id}
        # member_no is the primary ordering field, so it must be null here for
        # all three members, otherwise it alone determines the order and the
        # last_name tiebreaker this test is meant to exercise never applies.
        Member.objects.filter(id__in=member_ids).update(member_no=None)

        response = self.client.get(reverse("coop:members-list"))

        self.assertStatusCode(response, status.HTTP_200_OK)
        last_names = [
            member["last_name"]
            for member in response.json()
            if member["id"] in member_ids
        ]
        self.assertEqual(["Vogel", "von Adler", "Voss"], last_names)
