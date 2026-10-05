import datetime
from unittest.mock import patch, MagicMock

from django.utils import timezone
from tapir_mail.models import StaticSegment, StaticSegmentRecipient, ExternalRecipient
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import EmailChangeRequest
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.accounts.services.mail_change_service import MailChangeService
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMailChangeService(TapirIntegrationTest):
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    @patch.object(KeycloakUserManager, "get_keycloak_client")
    def test_applyMailChange_default_newEmailSavedAndKeycloakUpdated(
        self, mock_get_keycloak_client: MagicMock, mock_fire_action: MagicMock
    ):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        cache = {}
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client

        MailChangeService.apply_mail_change(
            user=user, new_email="new@example.com", cache=cache
        )

        user.refresh_from_db()
        self.assertEqual("new@example.com", user.email)

        mock_client.update_user.assert_called_once_with(
            user_id="1234", payload={"email": "new@example.com"}
        )

        mock_fire_action.assert_called_once_with(
            trigger_data=TransactionalTriggerData(
                key=Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS,
                recipient_id_in_base_queryset=user.id,
            ),
        )

    @patch.object(KeycloakUserManager, "get_keycloak_client")
    def test_applyMailChange_keycloakRaisesError_changesRolledBack(
        self, mock_get_keycloak_client: MagicMock
    ):
        user = MemberFactory.create(email="old@example.com", keycloak_id="1234")
        cache = {}
        mock_client = MagicMock()
        mock_get_keycloak_client.return_value = mock_client
        mock_client.update_user.side_effect = Exception()

        with self.assertRaises(Exception):
            MailChangeService.apply_mail_change(
                user=user, new_email="new@example.com", cache=cache
            )

        user.refresh_from_db()
        self.assertEqual("old@example.com", user.email)

        mock_client.update_user.assert_called_once_with(
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
            user=user, new_email="new@example.com", cache=cache
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
            user=user, new_email="new@example.com", cache=cache
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
