from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry, KeycloakUser
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberBankDataApiView(TapirIntegrationTest):
    SIMPLE_FIELDS = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "street",
        "street_2",
        "postcode",
        "city",
    ]

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_memberTriesToGetDataFromAnotherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_memberTriesToGetOwnData_returnsCorrectData(self):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        for field in self.SIMPLE_FIELDS:
            self.assertEqual(getattr(user, field), response_content[field])

    def test_get_adminTriesToGetDataFromAnotherMember_returnsCorrectData(self):
        user = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        for field in self.SIMPLE_FIELDS:
            self.assertEqual(getattr(target, field), response_content[field])

    def test_get_studentStatusEnabledButLegalStatusIsNotCooperative_returnsNoneAsStudentStatus(
        self,
    ):
        user = MemberFactory.create()
        self.client.force_login(user)
        TapirParameter.objects.filter(
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_ASSOCIATION)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertIsNone(response_content["is_student"])

    def test_get_studentStatusEnabledAndLegalStatusIsCooperative_returnsCorrectValueForStudentStatus(
        self,
    ):
        user = MemberFactory.create(is_student=True)
        self.client.force_login(user)
        TapirParameter.objects.filter(
            key=ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS
        ).update(value=LEGAL_STATUS_COOPERATIVE)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["is_student"])

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_memberTriesToUpdateDataFromAnotherMember_returns403(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create(first_name="John")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.patch(
            url,
            data={
                "member_id": "unused",
                "first_name": "test_fn",
                "last_name": "test_ln",
                "street": "test_street",
                "street_2": "test_street2",
                "email": target.email,  # emails get tested separately since it triggers the mail change process
                "phone_number": "+4917744563327",
                "postcode": 12345,
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        target.refresh_from_db()
        self.assertEqual("John", target.first_name)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_memberTriesToUpdateOwnData_updatesDataAndCreateLogEntryAndSendMail(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        data = {
            "member_id": user.id,
            "first_name": "test_fn",
            "last_name": "test_ln",
            "street": "test_street",
            "street_2": "test_street2",
            "email": user.email,  # emails get tested separately since it triggers the mail change process
            "phone_number": "+4917744563327",
            "postcode": "12345",
            "city": "test_city",
            "is_student": False,
        }
        response = self.client.patch(
            url,
            data=data,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])

        user.refresh_from_db()
        for field_name, value in data.items():
            if field_name not in self.SIMPLE_FIELDS:
                continue
            self.assertEqual(data[field_name], getattr(user, field_name))

        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual(user.email, log_entry.actor.email)
        self.assertEqual(user.email, log_entry.user.email)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_DATA, trigger_data.key)
        self.assertEqual(user.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual({}, trigger_data.token_data)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_adminTriesToUpdateDataOfAnOtherMember_updatesDataAndCreateLogEntryAndSendMail(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(is_superuser=False)
        self.client.force_login(admin)

        url = reverse("coop:member_personal_data")
        data = {
            "member_id": target.id,
            "first_name": "test_fn",
            "last_name": "test_ln",
            "street": "test_street",
            "street_2": "test_street2",
            "email": target.email,  # emails get tested separately since it triggers the mail change process
            "phone_number": "+4917744563327",
            "postcode": "12345",
            "city": "test_city",
            "is_student": False,
        }
        response = self.client.patch(
            url,
            data=data,
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])

        target.refresh_from_db()
        for field_name, value in data.items():
            if field_name not in self.SIMPLE_FIELDS:
                continue
            self.assertEqual(data[field_name], getattr(target, field_name))

        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(target.email, log_entry.user.email)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_DATA, trigger_data.key)
        self.assertEqual(target.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual({}, trigger_data.token_data)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_newEmailIsAlreadyInUse_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(
            is_superuser=False, email="email_before@example.com"
        )
        other_member = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.patch(
            url,
            data={
                "member_id": user.id,
                "first_name": "test_fn",
                "last_name": "test_ln",
                "street": "test_street",
                "street_2": "test_street2",
                "email": other_member.email,
                "phone_number": "+4917744563327",
                "postcode": 12345,
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Diese E-Mail-Adresse ist schon ein anderes Mitglied zugewiesen.",
            response_content["error"],
        )

        user.refresh_from_db()
        self.assertEqual("email_before@example.com", user.email)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_phoneNumberIsInvalid_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False, phone_number="017726254738")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.patch(
            url,
            data={
                "member_id": user.id,
                "first_name": "test_fn",
                "last_name": "test_ln",
                "street": "test_street",
                "street_2": "test_street2",
                "email": user.email,
                "phone_number": "123",
                "postcode": "12345",
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Ungültige Telefonnummer",
            response_content["error"],
        )

        user.refresh_from_db()
        self.assertEqual("017726254738", user.phone_number)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_normalMemberTriesToChangeStudentStatus_dontApplyChangesAndReturnError(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False, is_student=False)
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.patch(
            url,
            data={
                "member_id": user.id,
                "first_name": "test_fn",
                "last_name": "test_ln",
                "street": "test_street",
                "street_2": "test_street2",
                "email": user.email,
                "phone_number": "017726254738",
                "postcode": "12345",
                "city": "test_city",
                "is_student": True,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            "Nur Admins dürfen den Studenten-Status ändern.",
            response_content["error"],
        )

        user.refresh_from_db()
        self.assertFalse(user.is_student)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    def test_patch_adminMemberTriesToChangeStudentStatus_studentStatusChanged(self):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(is_student=False)
        self.client.force_login(admin)

        url = reverse("coop:member_personal_data")
        response = self.client.patch(
            url,
            data={
                "member_id": target.id,
                "first_name": "test_fn",
                "last_name": "test_ln",
                "street": "test_street",
                "street_2": "test_street2",
                "email": target.email,
                "phone_number": "017726254738",
                "postcode": "12345",
                "city": "test_city",
                "is_student": True,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(
            response_content["error"],
        )

        target.refresh_from_db()
        self.assertTrue(target.is_student)

    @patch.object(TransactionalTrigger, "fire_action")
    @patch.object(KeycloakUser, "email_verified", autospec=True)
    def test_patch_emailChanged_sendsEmailChangeConfirmationButDontChangeCurrentMail(
        self, mock_email_verified: Mock, mock_fire_action: Mock
    ):
        mock_email_verified.return_value = True
        user = MemberFactory.create(email="old_address@example.com")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.patch(
            url,
            data={
                "member_id": user.id,
                "first_name": "test_fn",
                "last_name": "test_ln",
                "street": "test_street",
                "street_2": "test_street2",
                "email": "new_address@example.com",
                "phone_number": "017726254738",
                "postcode": "12345",
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])

        user.refresh_from_db()
        self.assertEqual("old_address@example.com", user.email)

        self.assertEqual(3, mock_fire_action.call_count)

        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_DATA, trigger_data.key)

        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            1
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_EMAIL_INITIATE, trigger_data.key)
        self.assertEqual(user.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual(["verify_link"], list(trigger_data.token_data.keys()))

        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            2
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_EMAIL_HINT, trigger_data.key)
        self.assertEqual(
            TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                email="new_address@example.com",
                first_name="test_fn",
                last_name="test_ln",
            ),
            trigger_data.recipient_outside_of_base_queryset,
        )
        self.assertIsNone(trigger_data.recipient_id_in_base_queryset)
        self.assertEqual({}, trigger_data.token_data)
