from django.urls import reverse
from rest_framework import status

from tapir.associations.models import AssociationMembershipType
from tapir.associations.tests.factories import (
    AssociationMembershipTypeFactory,
    AssociationMembershipFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssociationMembershipTypeHardAndSoftDeleteApiViews(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_softDelete_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        membership_type = AssociationMembershipTypeFactory.create(deleted=False)
        AssociationMembershipFactory.create(type=membership_type)

        url = reverse("associations:association_membership_type_soft_delete")
        url = f"{url}?type_id={membership_type.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        membership_type.refresh_from_db()
        self.assertFalse(membership_type.deleted)

    def test_softDelete_membershipTypeHasNoMembership_returnsError(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        membership_type = AssociationMembershipTypeFactory.create(deleted=False)

        url = reverse("associations:association_membership_type_soft_delete")
        url = f"{url}?type_id={membership_type.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        response_content = response.json()
        self.assertEqual(
            [
                "This membership type has no membership, it should be hard-deleted instead of soft-deleted"
            ],
            response_content,
        )
        membership_type.refresh_from_db()
        self.assertFalse(membership_type.deleted)

    def test_softDelete_membershipTypeHasMemberships_membershipTypeMarkedAsSoftDeleted(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        membership_type = AssociationMembershipTypeFactory.create(deleted=False)
        AssociationMembershipFactory.create(type=membership_type)

        url = reverse("associations:association_membership_type_soft_delete")
        url = f"{url}?type_id={membership_type.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        membership_type.refresh_from_db()
        self.assertTrue(membership_type.deleted)

    def test_hardDelete_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        membership_type = AssociationMembershipTypeFactory.create()

        url = reverse("associations:association_membership_type_hard_delete")
        url = f"{url}?type_id={membership_type.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            AssociationMembershipType.objects.filter(id=membership_type.id).exists()
        )

    def test_hardDelete_membershipTypeHasMemberships_returnsError(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipFactory.create(type=membership_type)

        url = reverse("associations:association_membership_type_hard_delete")
        url = f"{url}?type_id={membership_type.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        response_content = response.json()
        self.assertEqual(
            [
                "Memberships with this type exist, it should be soft-deleted instead of hard-deleted"
            ],
            response_content,
        )
        membership_type.refresh_from_db()
        self.assertFalse(membership_type.deleted)

    def test_hardDelete_membershipTypeHasNoMemberships_membershipTypeDeleted(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        membership_type = AssociationMembershipTypeFactory.create()

        url = reverse("associations:association_membership_type_hard_delete")
        url = f"{url}?type_id={membership_type.id}"
        response = self.client.delete(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(AssociationMembershipType.objects.exists())
