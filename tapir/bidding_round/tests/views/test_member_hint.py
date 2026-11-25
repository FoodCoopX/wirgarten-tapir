from django.urls import reverse
from rest_framework import status

from tapir.bidding_round.tests.helpers import create_open_round
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberHint(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_memberDetail_activeRound_showsHint(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.client.get(reverse("wirgarten:member_detail", args=[member.id]))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertContains(response, "Zur Beitragsrunde")
        self.assertContains(response, "Gib dein Gebot für die nächste Saison ab.")

    def test_memberDetail_flagOff_hidesHint(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, False)
        create_open_round()
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.client.get(reverse("wirgarten:member_detail", args=[member.id]))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertNotContains(response, "Gib dein Gebot für die nächste Saison ab.")

    def test_memberDetail_noActiveRound_hidesHint(self):
        self._set_parameter(ParameterKeys.BIDDING_ROUND_ENABLED, True)
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.client.get(reverse("wirgarten:member_detail", args=[member.id]))

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertNotContains(response, "Gib dein Gebot für die nächste Saison ab.")
