import datetime
import json
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.associations.models import (
    AssociationMembership,
    AssociationMembershipCreatedLogEntry,
)
from tapir.associations.tests.factories import (
    AssociationMembershipTypeFactory,
    AssociationMembershipFactory,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestExistingMemberUpdatesAssociationMembershipApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )

    def setUp(self) -> None:
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2020, month=1, day=3)
        )

    def test_post_normalMemberUpdatesMembershipOfOtherMember_returns403(self):
        logged_in_user, other_member = MemberFactory.create_batch(
            is_superuser=False, size=2
        )
        self.client.force_login(logged_in_user)

        post_data = {
            "member_id": other_member.id,
            "association_membership_type_id": AssociationMembershipTypeFactory.create().id,
        }
        response = self.client.post(
            reverse("associations:existing_member_updates_membership"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(AssociationMembership.objects.exists())
        self.assertFalse(AssociationMembershipCreatedLogEntry.objects.exists())

    def test_post_normalMemberUpdatesSelf_membershipAndLogEntryCreated(self):
        member = MemberFactory.create(is_superuser=False, sepa_consent=self.now)
        self.client.force_login(member)
        membership_type = AssociationMembershipTypeFactory.create()

        post_data = {
            "member_id": member.id,
            "association_membership_type_id": membership_type.id,
        }
        response = self.client.post(
            reverse("associations:existing_member_updates_membership"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response_content=response.json())

        # The details of the membership and of the log entry are tested in the tests for AssociationMembershipChangeHandler
        self.assertEqual(1, AssociationMembership.objects.count())
        membership = AssociationMembership.objects.get()
        self.assertEqual(member, membership.member)

        self.assertEqual(1, AssociationMembershipCreatedLogEntry.objects.count())
        log_entry = AssociationMembershipCreatedLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)

    def test_post_adminUpdatesOtherMember_membershipAndLogEntryCreated(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)
        membership_type = AssociationMembershipTypeFactory.create()
        other_member = MemberFactory.create(sepa_consent=self.now)

        post_data = {
            "member_id": other_member.id,
            "association_membership_type_id": membership_type.id,
        }
        response = self.client.post(
            reverse("associations:existing_member_updates_membership"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response_content=response.json())

        self.assertEqual(1, AssociationMembership.objects.count())
        membership = AssociationMembership.objects.get()
        self.assertEqual(other_member, membership.member)

        self.assertEqual(1, AssociationMembershipCreatedLogEntry.objects.count())
        log_entry = AssociationMembershipCreatedLogEntry.objects.get()
        self.assertEqual(other_member.email, log_entry.user.email)
        self.assertEqual(admin.email, log_entry.actor.email)

    def test_post_givenMembershipTypeIsSameAsCurrent_returnsAnError(self):
        member = MemberFactory.create(sepa_consent=self.now)
        self.client.force_login(member)
        membership_type = AssociationMembershipTypeFactory.create()
        AssociationMembershipFactory.create(
            member=member,
            start_date=self.growing_period.start_date,
            type=membership_type,
        )

        post_data = {
            "member_id": member.id,
            "association_membership_type_id": membership_type.id,
        }
        response = self.client.post(
            reverse("associations:existing_member_updates_membership"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Du bist schon mitglied mit dem gleichem Mitgliedschaftstyp",
            response_content["error"],
        )

        self.assertEqual(1, AssociationMembership.objects.count())
        self.assertFalse(AssociationMembershipCreatedLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_memberNeedsBankingDataButNoBankingDataGiven_returnsAnError(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(iban=None)
        self.client.force_login(member)
        membership_type = AssociationMembershipTypeFactory.create()

        post_data = {
            "member_id": member.id,
            "association_membership_type_id": membership_type.id,
        }
        response = self.client.post(
            reverse("associations:existing_member_updates_membership"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])

        self.assertEqual(
            "Dieses Mitglied braucht noch Bank-Daten (IBAN usw.)",
            response_content["error"],
        )

        self.assertFalse(AssociationMembership.objects.exists())
        self.assertFalse(AssociationMembershipCreatedLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_memberNeedsBankingDataAndBankingDataGiven_bankingDataUpdatedAndLogEntryCreatedAndEmailSent(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(iban=None)
        self.client.force_login(member)
        membership_type = AssociationMembershipTypeFactory.create()

        post_data = {
            "member_id": member.id,
            "association_membership_type_id": membership_type.id,
            "iban": "NL76RABO8675663943",
            "account_owner": "test_account_owner",
        }
        response = self.client.post(
            reverse("associations:existing_member_updates_membership"),
            data=json.dumps(post_data),
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assert_order_confirmed(response_content)

        member.refresh_from_db()
        self.assertEqual("NL76RABO8675663943", member.iban)
        self.assertEqual("test_account_owner", member.account_owner)
        self.assertEqual(self.now, member.sepa_consent)

        self.assertEqual(1, AssociationMembership.objects.count())
        self.assertEqual(1, AssociationMembershipCreatedLogEntry.objects.count())

        self.assertEqual(1, UpdateTapirUserLogEntry.objects.count())
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual(member.email, log_entry.user.email)
        self.assertEqual(member.email, log_entry.actor.email)

        self.assertEqual(1, mock_fire_action.call_count)
        self.assert_mail_event_has_been_triggered(
            mock_fire_action, key=Events.MEMBERAREA_CHANGE_DATA
        )
