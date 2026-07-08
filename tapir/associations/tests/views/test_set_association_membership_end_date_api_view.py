import datetime

from django.urls import reverse
from rest_framework import status

from tapir.associations.models import AssociationMembershipUpdatedLogEntry
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class SetAssociationMembershipEndDateApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalMemberTriesToSetEndDate_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        membership = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
        )

        response = self.client.post(
            reverse("associations:set_membership_end_date"),
            data={"membership_id": membership, "end_date": "2021-01-01"},
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        membership.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2000, month=12, day=31), membership.end_date
        )
        self.assertFalse(AssociationMembershipUpdatedLogEntry.objects.exists())

    def test_post_adminSetsEndDate_endDateSetAndLogEntryCreated(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        target_membership = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
        )
        other_membership = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
        )

        response = self.client.post(
            reverse("associations:set_membership_end_date"),
            data={"membership_id": target_membership.id, "end_date": "2021-01-01"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())

        target_membership.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2021, month=1, day=1), target_membership.end_date
        )
        other_membership.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2000, month=12, day=31), other_membership.end_date
        )

        self.assertEqual(1, AssociationMembershipUpdatedLogEntry.objects.count())

    def test_post_adminSetsEndDateBeforeStartDate_returnsError(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)
        membership = AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(year=2000, month=1, day=1),
            end_date=datetime.date(year=2000, month=12, day=31),
        )

        response = self.client.post(
            reverse("associations:set_membership_end_date"),
            data={"membership_id": membership.id, "end_date": "1990-01-01"},
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Das End-Datum muss nach dem Start-Datum sein", response_content["error"]
        )

        membership.refresh_from_db()
        self.assertEqual(
            datetime.date(year=2000, month=12, day=31), membership.end_date
        )
        self.assertFalse(AssociationMembershipUpdatedLogEntry.objects.exists())
