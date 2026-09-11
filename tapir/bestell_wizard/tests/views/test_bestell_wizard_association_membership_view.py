from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBestellWizardAssociationMembershipView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberGetsOwnPage_returns200(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.get(
            reverse(
                "bestell_wizard:bestell_wizard_association_membership",
                kwargs={"member_id": member.id},
            )
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_adminGetsPageOfOtherMember_returns200(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        other_member = MemberFactory.create()

        response = self.client.get(
            reverse(
                "bestell_wizard:bestell_wizard_association_membership",
                kwargs={"member_id": other_member.id},
            )
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_get_normalMemberGetsPageOfOtherMember_returns403(self):
        logged_in_user = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_user)
        other_member = MemberFactory.create()

        response = self.client.get(
            reverse(
                "bestell_wizard:bestell_wizard_association_membership",
                kwargs={"member_id": other_member.id},
            )
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
