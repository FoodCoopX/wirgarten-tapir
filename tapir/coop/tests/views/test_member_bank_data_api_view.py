import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import UpdateTapirUserLogEntry
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberBankDataApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(key=ParameterKeys.SITE_NAME).update(
            value="My Test Org"
        )

    def test_get_memberTriesToGetDataFromAnotherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_banking_data")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_memberTriesToGetOwnData_returnsCorrectData(self):
        user = MemberFactory.create(
            is_superuser=False,
            account_owner="Test Account Owner",
            iban="NL41ABNA3195199319",
        )
        self.client.force_login(user)

        url = reverse("coop:member_banking_data")
        url = f"{url}?member_id={user.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual("My Test Org", response_content["organisation_name"])
        self.assertEqual("Test Account Owner", response_content["account_owner"])
        self.assertEqual("NL41ABNA3195199319", response_content["iban"])

    def test_get_adminTriesToGetDataFromAnotherMember_returnsCorrectData(self):
        user = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create(
            account_owner="Test Account Owner",
            iban="NL41ABNA3195199319",
        )
        self.client.force_login(user)

        url = reverse("coop:member_banking_data")
        url = f"{url}?member_id={target.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual("My Test Org", response_content["organisation_name"])
        self.assertEqual("Test Account Owner", response_content["account_owner"])
        self.assertEqual("NL41ABNA3195199319", response_content["iban"])

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_memberTriesToUpdateDataOfAnotherMember_returns403(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        target = MemberFactory.create()
        self.client.force_login(user)

        url = reverse("coop:member_banking_data")
        response = self.client.patch(
            url,
            data={
                "member_id": target.id,
                "account_owner": "New Owner",
                "iban": "NL41ABNA3195199319",
                "sepa_consent": True,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())
        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_memberTriesToUpdateOwnData_dataUpdatedAndMailSentAndLogEntryCreated(
        self, mock_fire_action: Mock
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        now = mock_timezone(test=self, now=datetime.datetime(year=2017, month=4, day=9))

        url = reverse("coop:member_banking_data")
        response = self.client.patch(
            url,
            data={
                "member_id": user.id,
                "account_owner": "New Owner",
                "iban": "NL41ABNA3195199319",
                "sepa_consent": True,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertEqual("New Owner", user.account_owner)
        self.assertEqual("NL41ABNA3195199319", user.iban)
        self.assertEqual(now, user.sepa_consent)

        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual(user.email, log_entry.actor.email)
        self.assertEqual(user.email, log_entry.user.email)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_DATA, trigger_data.key)
        self.assertEqual(user.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual({}, trigger_data.token_data)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_adminTriesToUpdateDataOfOtherMember_dataUpdatedAndMailSentAndLogEntryCreated(
        self, mock_fire_action: Mock
    ):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(admin)
        now = mock_timezone(test=self, now=datetime.datetime(year=2017, month=4, day=9))

        url = reverse("coop:member_banking_data")
        response = self.client.patch(
            url,
            data={
                "member_id": target.id,
                "account_owner": "New Owner",
                "iban": "NL41ABNA3195199319",
                "sepa_consent": True,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        target.refresh_from_db()
        self.assertEqual("New Owner", target.account_owner)
        self.assertEqual("NL41ABNA3195199319", target.iban)
        self.assertEqual(now, target.sepa_consent)

        self.assertTrue(UpdateTapirUserLogEntry.objects.exists())
        log_entry = UpdateTapirUserLogEntry.objects.get()
        self.assertEqual(admin.email, log_entry.actor.email)
        self.assertEqual(target.email, log_entry.user.email)

        mock_fire_action.assert_called_once()
        trigger_data: TransactionalTriggerData = mock_fire_action.call_args_list[
            0
        ].kwargs["trigger_data"]
        self.assertEqual(Events.MEMBERAREA_CHANGE_DATA, trigger_data.key)
        self.assertEqual(target.id, trigger_data.recipient_id_in_base_queryset)
        self.assertIsNone(trigger_data.recipient_outside_of_base_queryset)
        self.assertEqual({}, trigger_data.token_data)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_patch_updateWithoutSepaConsent_returnsError(self, mock_fire_action: Mock):
        admin = MemberFactory.create(is_superuser=True)
        target = MemberFactory.create()
        self.client.force_login(admin)
        mock_timezone(test=self, now=datetime.datetime(year=2017, month=4, day=9))

        url = reverse("coop:member_banking_data")
        response = self.client.patch(
            url,
            data={
                "member_id": target.id,
                "account_owner": "New Owner",
                "iban": "NL41ABNA3195199319",
                "sepa_consent": False,
            },
            content_type="application/json",
        )

        self.assertStatusCode(response, status.HTTP_400_BAD_REQUEST)

        self.assertFalse(UpdateTapirUserLogEntry.objects.exists())
        mock_fire_action.assert_not_called()
