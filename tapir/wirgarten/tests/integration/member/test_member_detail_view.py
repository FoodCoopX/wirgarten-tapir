from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDetailView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_memberDetailView_memberViewsOwnPage_countryIsShownInPersonalDataCard(
        self,
    ):
        member = MemberFactory.create(is_superuser=False, country="AT")
        self.client.force_login(member)

        response = self.client.get(
            reverse("wirgarten:member_detail", kwargs={"pk": member.id})
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertContains(response, '<div class="col-8" id="tapir_user_country">AT')

    def test_memberDetailView_adminViewsOtherMember_countryIsShownInPersonalDataCard(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        member = MemberFactory.create(country="DE")

        response = self.client.get(
            reverse("wirgarten:member_detail", kwargs={"pk": member.id})
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertContains(response, '<div class="col-8" id="tapir_user_country">DE')
