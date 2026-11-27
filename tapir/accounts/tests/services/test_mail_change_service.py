import datetime
from unittest.mock import patch, MagicMock

from django.utils import timezone
from tapir.mail.models import (
    StaticSegment,
    StaticSegmentRecipient,
    ExternalRecipient,
    ExternalRecipientConfirmation,
)
from tapir.mail.tests.factories import MailCategoryFactory
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import EmailChangeRequest
from tapir.accounts.services.mail_change_service import MailChangeService
from tapir.core.services.mailman.mailing_list_address_mover import (
    MailingListAddressMover,
)
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import MemberExtraEmail, MemberExtraEmailDeletedLogEntry
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMailChangeService(TapirIntegrationTest):
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_applyMailChange_default_newEmailSavedAndKeycloakUpdated(
        self, mock_fire_action: MagicMock
    ):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        cache = {}

        MailChangeService.apply_mail_change(
            user=user, new_email="new@example.com", actor=user, cache=cache
        )

        user.refresh_from_db()
        self.assertEqual("new@example.com", user.email)

        self.mock_keycloak_client.update_user.assert_called_once_with(
            user_id="1234", payload={"email": "new@example.com"}
        )

        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
                recipient_id_in_base_queryset=user.id,
            ),
        )

    def test_applyMailChange_keycloakRaisesError_changesRolledBack(self):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        cache = {}
        self.mock_keycloak_client.update_user.side_effect = Exception()

        with self.assertRaises(Exception):
            MailChangeService.apply_mail_change(
                user=user, new_email="new@example.com", actor=user, cache=cache
            )

        user.refresh_from_db()
        self.assertEqual("old@example.com", user.email)

        self.mock_keycloak_client.update_user.assert_called_once_with(
            user_id="1234", payload={"email": "new@example.com"}
        )

    def test_applyMailChange_default_oldEmailRequestsDeleted(self):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        cache = {}

        EmailChangeRequest.objects.create(user=user, new_email="request1@example.com")
        outdated_request = EmailChangeRequest.objects.create(
            user=MemberFactory.create(), new_email="request2@example.com"
        )
        EmailChangeRequest.objects.filter(id=outdated_request.id).update(
            created_at=timezone.now() - datetime.timedelta(days=300)
        )
        recent_request = EmailChangeRequest.objects.create(
            user=MemberFactory.create(), new_email="request3@example.com"
        )
        EmailChangeRequest.objects.filter(id=recent_request.id).update(
            created_at=timezone.now() - datetime.timedelta(hours=3)
        )

        MailChangeService.apply_mail_change(
            user=user, new_email="new@example.com", actor=user, cache=cache
        )

        user.refresh_from_db()
        self.assertEqual("new@example.com", user.email)

        self.assertFalse(
            EmailChangeRequest.objects.filter(user=user).exists(),
            "All change requests for the current user should be deleted",
        )
        self.assertEqual(
            {recent_request.id},
            set(EmailChangeRequest.objects.values_list("id", flat=True)),
            "Only the most recent request should still be there",
        )

    def test_applyMailChange_default_staticSegmentRecipientAndExternalRecipientUpdated(
        self,
    ):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        cache = {}
        static_segment = StaticSegment.objects.create(name="test_segment")
        static_recipient_1 = StaticSegmentRecipient.objects.create(
            segment=static_segment,
            first_name="John",
            last_name="Doe",
            email="old@example.com",
        )
        static_recipient_2 = StaticSegmentRecipient.objects.create(
            segment=static_segment,
            first_name="Jane",
            last_name="Doe",
            email="other@example.com",
        )

        external_recipient_1 = ExternalRecipient.objects.create(
            email="old@example.com", first_name="John"
        )
        external_recipient_2 = ExternalRecipient.objects.create(
            email="other@example.com", first_name="Jane"
        )

        MailChangeService.apply_mail_change(
            user=user, new_email="new@example.com", actor=user, cache=cache
        )

        user.refresh_from_db()
        self.assertEqual("new@example.com", user.email)

        static_recipient_1.refresh_from_db()
        self.assertEqual("new@example.com", static_recipient_1.email)
        static_recipient_2.refresh_from_db()
        self.assertEqual("other@example.com", static_recipient_2.email)

        external_recipient_1.refresh_from_db()
        self.assertEqual("new@example.com", external_recipient_1.email)
        external_recipient_2.refresh_from_db()
        self.assertEqual("other@example.com", external_recipient_2.email)

    def test_applyMailChange_newEmailIsAlreadyAnExternalRecipient_mergesTheOldExternalRecipientIntoIt(
        self,
    ):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        shared_category, old_only_category = MailCategoryFactory.create_batch(2)
        old_recipient = ExternalRecipient.objects.create(
            email="old@example.com", first_name="Old"
        )
        new_recipient = ExternalRecipient.objects.create(
            email="new@example.com", first_name="New"
        )
        ExternalRecipientConfirmation.objects.create(
            external_recipient=old_recipient, mail_category=shared_category
        )
        kept_confirmation = ExternalRecipientConfirmation.objects.create(
            external_recipient=new_recipient, mail_category=shared_category
        )
        moved_confirmation = ExternalRecipientConfirmation.objects.create(
            external_recipient=old_recipient, mail_category=old_only_category
        )

        MailChangeService.apply_mail_change(
            user=user, new_email="new@example.com", actor=user, cache={}
        )

        self.assertEqual([new_recipient], list(ExternalRecipient.objects.all()))
        self.assertEqual(
            {kept_confirmation.id, moved_confirmation.id},
            set(
                ExternalRecipientConfirmation.objects.filter(
                    external_recipient=new_recipient
                ).values_list("id", flat=True)
            ),
        )
        self.assertEqual(2, ExternalRecipientConfirmation.objects.count())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_applyMailChange_newEmailIsAnExtraEmail_extraEmailsWithThatAddressDeleted(
        self, _: MagicMock
    ):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        other_member = MemberFactory.create()
        MemberExtraEmailFactory.create(
            member=other_member, email="new@example.com", confirmed_on=timezone.now()
        )
        MemberExtraEmailFactory.create(member=user, email="new@example.com")
        kept = MemberExtraEmailFactory.create(email="other@example.com")

        MailChangeService.apply_mail_change(
            user=user, new_email="new@example.com", actor=user, cache={}
        )

        self.assertEqual([kept], list(MemberExtraEmail.objects.all()))
        self.assertEqual(
            {(other_member.id, "new@example.com"), (user.id, "new@example.com")},
            set(
                MemberExtraEmailDeletedLogEntry.objects.values_list("user_id", "email")
            ),
        )

    @patch.object(MailingListAddressMover, "move_subscriptions", autospec=True)
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_applyMailChange_default_movesTheListSubscriptionsAfterCommit(
        self, _: MagicMock, mock_move_subscriptions: MagicMock
    ):
        user = MemberFactory.create(email="old@example.com")
        cache = {}

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            MailChangeService.apply_mail_change(
                user=user, new_email="new@example.com", actor=user, cache=cache
            )

            mock_move_subscriptions.assert_not_called()

        for callback in callbacks:
            callback()
        mock_move_subscriptions.assert_called_once_with(
            old_email="old@example.com", new_email="new@example.com", cache=cache
        )

    @patch.object(MailingListAddressMover, "move_subscriptions", autospec=True)
    def test_applyMailChange_keycloakRaisesError_listSubscriptionsAreNotMoved(
        self, mock_move_subscriptions: MagicMock
    ):
        user = MemberFactory.create(email="old@example.com")
        self.mock_keycloak_client.update_user.side_effect = Exception()

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(Exception):
                MailChangeService.apply_mail_change(
                    user=user, new_email="new@example.com", actor=user, cache={}
                )

        mock_move_subscriptions.assert_not_called()
