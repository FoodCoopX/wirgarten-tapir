import datetime
from unittest.mock import patch, Mock

from django.utils import timezone
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.associations.apps import AssociationsConfig
from tapir.associations.tasks import trigger_association_membership_ends_today_mails
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestTriggerAssociationMembershipEndsTodayMails(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2020, month=12, day=31)
        )

    @staticmethod
    def create_membership_that_should_trigger_a_mail():
        return AssociationMembershipFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1),
            end_date=datetime.date(year=2020, month=12, day=31),
            cancellation_ts=datetime.datetime(
                year=2020, month=10, day=13, hour=12, tzinfo=datetime.timezone.utc
            ),
            membership_ended_mail_sent_on=None,
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_triggerAssociationMembershipEndsTodayMails_membershipEndsAndNoFutureMembership_mailTriggered(
        self, mock_fire_action: Mock
    ):
        membership = self.create_membership_that_should_trigger_a_mail()

        trigger_association_membership_ends_today_mails()

        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key=AssociationsConfig.MAIL_TRIGGER_ASSOCIATION_MEMBERSHIP_ENDS_TODAY,
                recipient_id_in_base_queryset=membership.member_id,
                token_data={
                    "membership_type_name": membership.type.name,
                    "end_date_set_on": "13.10.2020",
                },
            )
        )
        membership.refresh_from_db()
        self.assertEqual(self.now, membership.membership_ended_mail_sent_on)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_triggerAssociationMembershipEndsTodayMails_membershipEndsButAFutureMembershipExists_mailNotTriggered(
        self, mock_fire_action: Mock
    ):
        membership = self.create_membership_that_should_trigger_a_mail()
        AssociationMembershipFactory.create(
            member=membership.member,
            start_date=datetime.date(year=2021, month=1, day=1),
            end_date=datetime.date(year=2021, month=12, day=31),
        )

        trigger_association_membership_ends_today_mails()

        mock_fire_action.assert_not_called()
        membership.refresh_from_db()
        self.assertIsNone(membership.membership_ended_mail_sent_on)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_triggerAssociationMembershipEndsTodayMails_membershipEndedTooLongAgo_mailNotTriggered(
        self, mock_fire_action: Mock
    ):
        membership = self.create_membership_that_should_trigger_a_mail()
        membership.end_date = datetime.date(year=2020, month=12, day=15)
        membership.save()

        trigger_association_membership_ends_today_mails()

        mock_fire_action.assert_not_called()
        membership.refresh_from_db()
        self.assertIsNone(membership.membership_ended_mail_sent_on)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_triggerAssociationMembershipEndsTodayMails_membershipNotEndedYet_mailNotTriggered(
        self, mock_fire_action: Mock
    ):
        membership = self.create_membership_that_should_trigger_a_mail()
        membership.end_date = datetime.date(year=2021, month=1, day=1)
        membership.save()

        trigger_association_membership_ends_today_mails()

        mock_fire_action.assert_not_called()
        membership.refresh_from_db()
        self.assertIsNone(membership.membership_ended_mail_sent_on)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_triggerAssociationMembershipEndsTodayMails_membershipHasNoEndDate_mailNotTriggered(
        self, mock_fire_action: Mock
    ):
        membership = self.create_membership_that_should_trigger_a_mail()
        membership.end_date = None
        membership.save()

        trigger_association_membership_ends_today_mails()

        mock_fire_action.assert_not_called()
        membership.refresh_from_db()
        self.assertIsNone(membership.membership_ended_mail_sent_on)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_triggerAssociationMembershipEndsTodayMails_mailAlreadyTriggered_mailNotTriggered(
        self, mock_fire_action: Mock
    ):
        membership = self.create_membership_that_should_trigger_a_mail()
        sent_on_before_changes = timezone.now()
        membership.membership_ended_mail_sent_on = sent_on_before_changes
        membership.save()

        trigger_association_membership_ends_today_mails()

        mock_fire_action.assert_not_called()
        membership.refresh_from_db()
        self.assertEqual(
            sent_on_before_changes, membership.membership_ended_mail_sent_on
        )
