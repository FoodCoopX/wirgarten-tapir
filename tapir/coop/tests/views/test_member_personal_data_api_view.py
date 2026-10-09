from unittest.mock import patch, Mock, ANY

from django.urls import reverse
from rest_framework import status
from tapir_mail.models import StaticSegment, StaticSegmentRecipient
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION, LEGAL_STATUS_COOPERATIVE
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberPersonalDataApiView(TapirIntegrationTest):
    SIMPLE_FIELDS = [
        "phone_number",
        "phone_number_landline",
        "street",
        "street_2",
        "postcode",
        "city",
    ]
    SIMPLE_FIELDS_ADMIN_EDIT_ONLY = ["first_name", "last_name"]
    ALL_SIMPLE_FIELDS = SIMPLE_FIELDS + SIMPLE_FIELDS_ADMIN_EDIT_ONLY

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
        user = MemberFactory.create(is_superuser=False, phone_number="017726254738")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        for field in self.ALL_SIMPLE_FIELDS:
            self.assertEqual(getattr(user, field), response_content[field])

        self.assertFalse(response_content["can_edit_name"])

    def test_get_adminTriesToGetDataFromAnotherMember_returnsCorrectData(self):
        user = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(phone_number="017726254738")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        for field in self.ALL_SIMPLE_FIELDS:
            self.assertEqual(getattr(target, field), response_content[field])
        self.assertTrue(response_content["can_edit_name"])

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

    def test_get_studentStatusDisabledAndLegalStatusIsCooperative_returnsNoneAsStudentStatus(
        self,
    ):
        user = MemberFactory.create(is_student=True)
        self.client.force_login(user)
        self._set_parameter(
            ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES, False
        )
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_COOPERATIVE
        )

        url = reverse("coop:member_personal_data")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertIsNone(response_content["is_student"])

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
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

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_memberTriesToUpdateOwnData_updatesDataAndCreateLogEntryAndSendMail(
        self, mock_fire_action: Mock
    ):
        user_before_changes = MemberFactory.create(is_superuser=False)
        self.client.force_login(user_before_changes)

        url = reverse("coop:member_personal_data")
        data = {
            "member_id": user_before_changes.id,
            "first_name": "test_fn",
            "last_name": "test_ln",
            "street": "test_street",
            "street_2": "test_street2",
            "email": user_before_changes.email,  # emails get tested separately since it triggers the mail change process
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

        user_after_changes = Member.objects.get(id=user_before_changes.id)
        for field_name, value in data.items():
            if field_name in self.SIMPLE_FIELDS:
                self.assertEqual(
                    data[field_name], getattr(user_after_changes, field_name)
                )
            if field_name in self.SIMPLE_FIELDS_ADMIN_EDIT_ONLY:
                self.assertEqual(
                    getattr(user_before_changes, field_name),
                    getattr(user_after_changes, field_name),
                )

        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual(user_after_changes.email, log_entry.actor.email)
        self.assertEqual(user_after_changes.email, log_entry.user.email)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].args[0]
        self.assertEqual(Events.MEMBERAREA_CHANGE_DATA, trigger_data.key)
        self.assertEqual(
            user_after_changes.id, trigger_data.recipient_id_in_base_queryset
        )
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual({}, trigger_data.token_data)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
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
            "country": "DE",
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
            if field_name not in self.ALL_SIMPLE_FIELDS:
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

    def test_get_memberGetsOwnData_returnsCountryButCannotEditIt(self):
        user = MemberFactory.create(is_superuser=False, country="AT")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.get(f"{url}?member_id={user.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual("AT", response_content["country"])
        self.assertFalse(response_content["can_edit_country"])

    def test_get_adminGetsDataFromAnotherMember_returnsCountryAndCanEditCountry(self):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(country="AT")
        self.client.force_login(admin)

        url = reverse("coop:member_personal_data")
        response = self.client.get(f"{url}?member_id={target.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual("AT", response_content["country"])
        self.assertTrue(response_content["can_edit_country"])

    def _patch_country(self, actor, target, country):
        self.client.force_login(actor)
        data = {
            "member_id": target.id,
            "first_name": target.first_name,
            "last_name": target.last_name,
            "street": "test_street",
            "street_2": "",
            "email": target.email,
            "phone_number": "+4917744563327",
            "postcode": "12345",
            "city": "test_city",
            "country": country,
            "is_student": False,
        }
        if country is None:
            del data["country"]
        return self.client.patch(
            reverse("coop:member_personal_data"),
            data=data,
            content_type="application/json",
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_adminChangesCountry_countryIsSaved(self, _):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(country="DE")

        response = self._patch_country(admin, target, "AT")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertTrue(response.json()["order_confirmed"])
        target.refresh_from_db()
        self.assertEqual("AT", target.country)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_memberTriesToChangeOwnCountry_countryIsNotChanged(self, _):
        user = MemberFactory.create(is_superuser=False, country="DE")

        response = self._patch_country(user, user, "AT")

        self.assertStatusCode(response, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual("DE", user.country)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_adminSendsCountryOutsideOfDeAndAt_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(country="DE")

        response = self._patch_country(admin, target, "FR")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertIsNotNone(response_content["error"])
        target.refresh_from_db()
        self.assertEqual("DE", target.country)
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_adminSendsNoCountry_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(country="AT")

        response = self._patch_country(admin, target, None)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(response.json()["order_confirmed"])
        target.refresh_from_db()
        self.assertEqual("AT", target.country)
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
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

    def test_get_memberHasNoPhoneNumber_returnsEmptyString(self):
        user = MemberFactory.create(is_superuser=False, phone_number=None)
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.get(f"{url}?member_id={user.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual("", response.json()["phone_number"])

    def test_get_default_returnsPhoneNumberRequiredParameter(self):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        url = reverse("coop:member_personal_data")

        for value in [True, False]:
            self._set_parameter(ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, value)
            response = self.client.get(f"{url}?member_id={user.id}")

            self.assertStatusCode(response, status.HTTP_200_OK)
            self.assertEqual(value, response.json()["phone_number_required"])

    def _patch_phone_number(self, user, phone_number):
        self.client.force_login(user)
        return self.client.patch(
            reverse("coop:member_personal_data"),
            data={
                "member_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "street": "test_street",
                "street_2": "",
                "phone_number": phone_number,
                "postcode": "12345",
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_phoneNumberEmptyAndRequired_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, True)
        user = MemberFactory.create(is_superuser=False, phone_number="017726254738")

        response = self._patch_phone_number(user, "")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual("Bitte gib eine Telefonnummer an.", response_content["error"])
        user.refresh_from_db()
        self.assertEqual("017726254738", user.phone_number)
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_phoneNumberEmptyAndNotRequired_removesPhoneNumber(
        self, mock_fire_action: Mock
    ):
        self._set_parameter(ParameterKeys.MEMBER_PHONE_NUMBER_REQUIRED, False)
        user = MemberFactory.create(is_superuser=False, phone_number="017726254738")

        response = self._patch_phone_number(user, "")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        user.refresh_from_db()
        self.assertFalse(user.phone_number)
        mock_fire_action.assert_called_once()

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_setsSecondPhoneNumber_savesIt(self, mock_fire_action: Mock):
        user = MemberFactory.create(is_superuser=False, phone_number_landline=None)
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
                "phone_number": "017726254738",
                "phone_number_landline": "+4930123456",
                "postcode": "12345",
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])

        user.refresh_from_db()
        self.assertEqual("+4930123456", user.phone_number_landline)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_secondPhoneNumberLeftBlank_isNotRequired(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False, phone_number_landline=None)
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
                "phone_number": "017726254738",
                "phone_number_landline": "",
                "postcode": "12345",
                "city": "test_city",
                "is_student": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])

        user.refresh_from_db()
        self.assertIsNone(user.phone_number_landline)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_secondPhoneNumberIsInvalid_dontApplyChangesAndReturnsError(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(
            is_superuser=False, phone_number_landline="+4930123456"
        )
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
                "phone_number": "017726254738",
                "phone_number_landline": "123",
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
        self.assertEqual("+4930123456", user.phone_number_landline)

        mock_fire_action.assert_not_called()
        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
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
                "phone_number": "017726254738",
                "postcode": "12345",
                "city": "test_city",
                "country": "DE",
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

    @patch.object(KeycloakUserManager, "update_keycloak_user_name", autospec=True)
    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_nameChanged_updatesStaticRecipientsAndKeycloak(
        self, mock_fire_action: Mock, mock_update_keycloak_user_name: Mock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        target_user = MemberFactory.create(is_superuser=False)

        static_segment = StaticSegment.objects.create(name="test_segment")
        target_recipient = StaticSegmentRecipient.objects.create(
            segment=static_segment,
            email=target_user.email,
            first_name="old_fn",
            last_name="old_ln",
        )
        other_recipient = StaticSegmentRecipient.objects.create(
            segment=static_segment,
            email="other@example.com",
            first_name="old_fn_2",
            last_name="old_ln_2",
        )

        url = reverse("coop:member_personal_data")
        data = {
            "member_id": target_user.id,
            "first_name": "test_fn",
            "last_name": "test_ln",
            "street": "test_street",
            "street_2": "test_street2",
            "phone_number": "017726254738",
            "postcode": "12345",
            "city": "test_city",
            "country": "DE",
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

        mock_update_keycloak_user_name.assert_called_once_with(
            user=target_user, cache=ANY
        )

        target_recipient.refresh_from_db()
        self.assertEqual("test_fn", target_recipient.first_name)
        self.assertEqual("test_ln", target_recipient.last_name)

        other_recipient.refresh_from_db()
        self.assertEqual("old_fn_2", other_recipient.first_name)
        self.assertEqual("old_ln_2", other_recipient.last_name)

    def test_get_bakeryEnabled_returnsPseudonymAndPseudonymEnabled(self):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, True)
        user = MemberFactory.create(is_superuser=False, pseudonym="test_pseudonym")
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.get(f"{url}?member_id={user.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual("test_pseudonym", response_content["pseudonym"])
        self.assertTrue(response_content["pseudonym_enabled"])

    def test_get_bakeryDisabled_returnsPseudonymDisabled(self):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, False)
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("coop:member_personal_data")
        response = self.client.get(f"{url}?member_id={user.id}")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertFalse(response.json()["pseudonym_enabled"])

    def _patch_pseudonym(self, user, pseudonym):
        self.client.force_login(user)
        data = {
            "member_id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "street": "test_street",
            "street_2": "",
            "phone_number": "017726254738",
            "postcode": "12345",
            "city": "test_city",
            "is_student": False,
        }
        if pseudonym is not None:
            data["pseudonym"] = pseudonym
        return self.client.patch(
            reverse("coop:member_personal_data"),
            data=data,
            content_type="application/json",
        )

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_memberSetsOwnPseudonym_pseudonymIsSavedAndLogged(self, _):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, True)
        user = MemberFactory.create(is_superuser=False, pseudonym="")

        response = self._patch_pseudonym(user, " test_pseudonym ")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        user.refresh_from_db()
        self.assertEqual("test_pseudonym", user.pseudonym)
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual("test_pseudonym", log_entry.new_values["pseudonym"])

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_memberSendsEmptyPseudonym_pseudonymIsRemoved(self, _):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, True)
        user = MemberFactory.create(is_superuser=False, pseudonym="test_pseudonym")

        response = self._patch_pseudonym(user, "")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        user.refresh_from_db()
        self.assertEqual("", user.pseudonym)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_pseudonymNotSent_pseudonymIsNotChanged(self, _):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, True)
        user = MemberFactory.create(is_superuser=False, pseudonym="test_pseudonym")

        response = self._patch_pseudonym(user, None)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        user.refresh_from_db()
        self.assertEqual("test_pseudonym", user.pseudonym)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_patch_bakeryDisabled_pseudonymIsNotChanged(self, _):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, False)
        user = MemberFactory.create(is_superuser=False, pseudonym="test_pseudonym")

        response = self._patch_pseudonym(user, "other_pseudonym")

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        user.refresh_from_db()
        self.assertEqual("test_pseudonym", user.pseudonym)

    def test_patch_pseudonymTooLong_returns400(self):
        self._set_parameter(ParameterKeys.BAKERY_ENABLED, True)
        user = MemberFactory.create(is_superuser=False, pseudonym="test_pseudonym")

        response = self._patch_pseudonym(user, "a" * 151)

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertEqual("test_pseudonym", user.pseudonym)
