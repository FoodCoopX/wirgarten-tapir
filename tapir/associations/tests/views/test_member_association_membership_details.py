from django.urls import reverse
from rest_framework import status

from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypeFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberAssociationMembershipDetails(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberGetsOwnData_returnsCorrectData(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        memberships = AssociationMembershipFactory.create_batch(size=3, member=member)

        url = reverse("associations:member_association_memberships")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        actual_membership_ids = {
            membership["id"] for membership in response_content["memberships"]
        }
        expected_membership_ids = {membership.id for membership in memberships}
        self.assertEqual(expected_membership_ids, actual_membership_ids)

    def test_get_memberGetsOtherMembersData_returns403(self):
        logged_in_member = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_member)

        url = reverse("associations:member_association_memberships")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_adminGetsOtherMembersData_returnsCorrectData(self):
        admin = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(admin)
        memberships = AssociationMembershipFactory.create_batch(
            size=3, member=other_member
        )

        url = reverse("associations:member_association_memberships")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        actual_membership_ids = {
            membership["id"] for membership in response_content["memberships"]
        }
        expected_membership_ids = {membership.id for membership in memberships}
        self.assertEqual(expected_membership_ids, actual_membership_ids)

    def test_get_onlyOneMembershipTypeAvailable_dontReturnOrderWizardUrl(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        AssociationMembershipTypeFactory.create()

        url = reverse("associations:member_association_memberships")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertIsNone(response_content["order_wizard_url"])

    def test_get_moreThanOneMembershipTypeAvailable_returnsOrderWizardUrl(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        AssociationMembershipTypeFactory.create_batch(size=2)

        url = reverse("associations:member_association_memberships")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            reverse(
                "bestell_wizard:bestell_wizard_association_membership",
                kwargs={"member_id": member.id},
            ),
            response_content["order_wizard_url"],
        )
