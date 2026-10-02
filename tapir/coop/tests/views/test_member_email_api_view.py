from unittest.mock import patch, Mock, ANY

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.accounts.services.email_verification_service import EmailVerificationService
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberEmailApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberTriesToGetDataFromAnotherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_email")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_memberTriesToGetOwnData_returnsCorrectData(self):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("coop:member_email")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "contact_email": "contact@example.com",
                "email": user.email,
                "is_admin": False,
                "verified": False,
            },
            response_content,
        )

    def test_get_adminTriesToGetDataFromAnotherMember_returnsCorrectData(self):
        user = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_email")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual(
            {
                "contact_email": "contact@example.com",
                "email": target.email,
                "is_admin": True,
                "verified": False,
            },
            response_content,
        )

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_memberTriesToUpdateDataFromAnotherMember_returns403(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create(first_name="John")
        self.client.force_login(user)

        url = reverse("coop:member_email")
        response = self.client.post(
            url,
            data={"email": "new@example.com", "member_id": target.id},
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        target.refresh_from_db()
        self.assertEqual("John", target.first_name)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_newEmailIsAlreadyInUse_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(
            is_superuser=False, email="email_before@example.com"
        )
        other_member = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_email")
        response = self.client.post(
            url,
            data={
                "member_id": user.id,
                "email": other_member.email,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Diese E-Mail-Adresse ist schon einem anderen Mitglied zugewiesen.",
            response_content["error"],
        )

        user.refresh_from_db()
        self.assertEqual("email_before@example.com", user.email)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(EmailVerificationService, "is_user_email_verified", autospec=True)
    def test_post_emailWasVerified_sendsEmailChangeConfirmationButDontChangeCurrentMail(
        self, mock_is_user_email_verified: Mock, mock_fire_action: Mock
    ):
        mock_is_user_email_verified.return_value = True
        user_before_changes = MemberFactory.create(email="old_address@example.com")
        self.client.force_login(user_before_changes)

        url = reverse("coop:member_email")
        response = self.client.post(
            url,
            data={
                "member_id": user_before_changes.id,
                "email": "new_address@example.com",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])

        user_after_changes = Member.objects.get(id=user_before_changes.id)
        self.assertEqual("old_address@example.com", user_after_changes.email)

        self.assertEqual(2, mock_fire_action.call_count)

        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_EMAIL_INITIATE, trigger_data.key)
        self.assertEqual(
            user_after_changes.id, trigger_data.recipient_id_in_base_queryset
        )
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual(["verify_link"], list(trigger_data.token_data.keys()))

        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            1
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_EMAIL_HINT, trigger_data.key)
        self.assertEqual(
            TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                email="new_address@example.com",
                first_name=user_before_changes.first_name,  # We are logged in as not-admin, so the name should not change
                last_name=user_before_changes.last_name,
            ),
            trigger_data.recipient_outside_of_base_queryset,
        )
        self.assertIsNone(trigger_data.recipient_id_in_base_queryset)
        self.assertEqual({}, trigger_data.token_data)

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(EmailVerificationService, "send_verification_email", autospec=True)
    @patch.object(EmailVerificationService, "is_user_email_verified", autospec=True)
    def test_post_emailWasNotVerified_changeEmailRightAwayAndSendKeycloakVerificationMail(
        self,
        mock_is_user_email_verified: Mock,
        mock_send_verification_email: Mock,
        mock_fire_action: Mock,
    ):
        mock_is_user_email_verified.return_value = False
        user_before_changes = MemberFactory.create(email="old_address@example.com")
        self.client.force_login(user_before_changes)

        url = reverse("coop:member_email")
        response = self.client.post(
            url,
            data={
                "member_id": user_before_changes.id,
                "email": "new_address@example.com",
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])

        user_after_changes = Member.objects.get(id=user_before_changes.id)
        self.assertEqual("new_address@example.com", user_after_changes.email)

        self.assertEqual(1, mock_fire_action.call_count)

        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_EMAIL_SUCCESS, trigger_data.key)
        self.assertEqual(
            user_after_changes.id, trigger_data.recipient_id_in_base_queryset
        )
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)

        mock_send_verification_email.assert_called_once_with(
            user=user_after_changes, actor=ANY, cache={}
        )
