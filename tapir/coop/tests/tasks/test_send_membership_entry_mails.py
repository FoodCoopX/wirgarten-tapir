import datetime
from unittest.mock import patch, Mock

from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.coop.tasks import send_membership_entry_mails
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COMPANY,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import CoopShareTransactionFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestSendMembershipEntryMail(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_coopMembershipStartedButMailAlreadySent_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        transaction = CoopShareTransactionFactory.create(
            valid_at=datetime.date(year=2010, month=1, day=1)
        )
        transaction.member.has_received_membership_started_mail = True
        transaction.member.save()

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_coopMembershipStartedAndMailNotSentYet_sendMailAndUpdateMember(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        transaction = CoopShareTransactionFactory.create(
            valid_at=datetime.date(year=2010, month=1, day=1)
        )
        member = transaction.member
        member.has_received_membership_started_mail = False
        member.save()

        send_membership_entry_mails()

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action,
            key=Events.MEMBERSHIP_ENTRY,
        )
        member.refresh_from_db()
        self.assertTrue(member.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_coopMembershipStartsTodayAndMailNotSentYet_sendMailAndUpdateMember(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )
        now = mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        transaction = CoopShareTransactionFactory.create(valid_at=now.date())
        member = transaction.member
        member.has_received_membership_started_mail = False
        member.save()

        send_membership_entry_mails()

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action,
            key=Events.MEMBERSHIP_ENTRY,
        )
        member.refresh_from_db()
        self.assertTrue(member.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_mailNotSentYetButCoopMembershipNotStarted_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        transaction = CoopShareTransactionFactory.create(
            valid_at=datetime.date(year=2011, month=1, day=1)
        )
        member = transaction.member
        member.has_received_membership_started_mail = False
        member.save()

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()
        member.refresh_from_db()
        self.assertFalse(member.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_mailNotSentYetButNoCoopShareExists_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        member = MemberFactory.create(has_received_membership_started_mail=False)

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()
        member.refresh_from_db()
        self.assertFalse(member.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_associationMembershipStartedButMailAlreadySent_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        member = MemberFactory.create(has_received_membership_started_mail=True)
        AssociationMembershipFactory.create(
            member=member, start_date=datetime.date(year=2010, month=1, day=1)
        )

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_associationMembershipStartedAndMailNotSentYet_sendMailAndUpdateMember(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        member = MemberFactory.create(has_received_membership_started_mail=False)
        AssociationMembershipFactory.create(
            member=member, start_date=datetime.date(year=2010, month=1, day=1)
        )

        send_membership_entry_mails()

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action,
            key=Events.MEMBERSHIP_ENTRY,
        )
        member.refresh_from_db()
        self.assertTrue(member.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_associationMembershipStartsTodayAndMailNotSentYet_sendMailAndUpdateMember(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )
        now = mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        member = MemberFactory.create(has_received_membership_started_mail=False)
        AssociationMembershipFactory.create(member=member, start_date=now.date())

        send_membership_entry_mails()

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action,
            key=Events.MEMBERSHIP_ENTRY,
        )
        member.refresh_from_db()
        self.assertTrue(member.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_mailNotSentYetButAssociationMembershipNotStarted_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        member = MemberFactory.create(has_received_membership_started_mail=False)
        AssociationMembershipFactory.create(
            member=member, start_date=datetime.date(year=2011, month=1, day=1)
        )

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_mailNotSentYetButNoAssociationMembershipExists_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        MemberFactory.create(has_received_membership_started_mail=False)

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_mailNotSentYetButAssociationMembershipExistsOnlyForSomeMembers_dontSendMail(
        self, mock_fire_action: Mock
    ):
        # regression test for ticket AUG#139 https://support.foodcoopx.de/conversation/139?folder_id=75
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))

        member_with_membership = MemberFactory.create(
            has_received_membership_started_mail=False
        )
        member_without_membership = MemberFactory.create(
            has_received_membership_started_mail=False
        )

        AssociationMembershipFactory.create(
            member=member_with_membership,
            start_date=datetime.date(year=2010, month=1, day=1),
        )

        send_membership_entry_mails()

        mock_fire_action.assert_called_once()
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action,
            key=Events.MEMBERSHIP_ENTRY,
        )
        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.mock_calls[0].kwargs[
            "trigger_data"
        ]
        self.assertEqual(
            member_with_membership.id, trigger_data.recipient_id_in_base_queryset
        )
        member_with_membership.refresh_from_db()
        self.assertTrue(member_with_membership.has_received_membership_started_mail)
        member_without_membership.refresh_from_db()
        self.assertFalse(member_without_membership.has_received_membership_started_mail)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_sendMembershipEntryMails_mailNotSentYetButLegalStatusDoesntHaveMemberships_dontSendMail(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COMPANY
        )
        mock_timezone(test=self, now=datetime.datetime(year=2010, month=8, day=1))
        member = MemberFactory.create(has_received_membership_started_mail=False)
        AssociationMembershipFactory.create(
            member=member, start_date=datetime.date(year=2010, month=1, day=1)
        )
        CoopShareTransactionFactory.create(
            member=member, valid_at=datetime.date(year=2010, month=1, day=1)
        )

        send_membership_entry_mails()

        mock_fire_action.assert_not_called()
