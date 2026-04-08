import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    CoopShareTransactionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.utils import get_today


class TestExistingMemberPurchasesSharesAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_normalMemberPurchaseSharesForAnotherMember_returns403AndDontPurchaseAnything(
        self, mock_fire_action: Mock
    ):
        purchasing_member = MemberFactory.create(
            is_superuser=False,
            iban="test_iban",
            account_owner="test_owner",
            sepa_consent=timezone.now(),
        )
        other_member = MemberFactory.create()
        self.client.force_login(purchasing_member)

        url = reverse("coop:existing_member_purchases_shares")
        data = {"member_id": other_member.id, "number_of_shares_to_add": 2}
        response = self.client.post(url, data)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CoopShareTransaction.objects.exists())
        mock_fire_action.assert_not_called()

    def test_post_normalMemberPurchaseSharesForThemselves_executePurchase(self):
        GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=100)
        )
        member = MemberFactory.create(
            is_superuser=False,
            iban="test_iban",
            account_owner="test_owner",
            sepa_consent=timezone.now(),
        )
        self.client.force_login(member)

        url = reverse("coop:existing_member_purchases_shares")
        data = {"member_id": member.id, "number_of_shares_to_add": 2}
        response = self.client.post(url, data)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        self.assertEqual(2, CoopShareTransaction.objects.get().quantity)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_adminPurchaseSharesForAnotherMember_executePurchase(
        self, mock_fire_action: Mock
    ):
        GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=100)
        )
        mock_timezone(test=self, now=datetime.datetime(year=2024, month=1, day=1))

        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        other_member = MemberFactory.create(
            is_superuser=False,
            iban="test_iban",
            account_owner="test_owner",
            sepa_consent=timezone.now(),
        )
        CoopShareTransactionFactory.create(member=other_member, quantity=2)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_SHARE_PRICE).update(
            value=75
        )

        data = {"member_id": other_member.id, "number_of_shares_to_add": 3}
        response = self.client.post(
            reverse("coop:existing_member_purchases_shares"), data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(2, CoopShareTransaction.objects.count())
        self.assertEqual(
            3, CoopShareTransaction.objects.order_by("valid_at").last().quantity
        )

        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.EXISTING_MEMBER_BUYS_COOP_SHARES,
                recipient_id_in_base_queryset=other_member.id,
                token_data={
                    "number_of_purchased_shares": 3,
                    "price_of_a_share": "75,00",
                    "price_of_the_purchased_shares": "225,00",
                    "new_shares_valid_at": "08.01.2024",
                    "total_number_of_shares": 5,
                    "total_price_of_shares": "375,00",
                },
            ),
        )

    def test_post_memberIsStudent_dontValidateMinimumNumberOfShares(self):
        GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=100)
        )
        member = MemberFactory.create(
            is_student=True,
            iban="iban",
            account_owner="owner",
            sepa_consent=timezone.now(),
        )
        self.client.force_login(member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=5)

        url = reverse("coop:existing_member_purchases_shares")
        data = {"member_id": member.id, "number_of_shares_to_add": 1}
        response = self.client.post(url, data)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        self.assertEqual(1, CoopShareTransaction.objects.get().quantity)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_memberIsNotStudent_validateMinimumNumberOfShares(
        self, mock_fire_action: Mock
    ):
        member = MemberFactory.create(
            is_student=False,
            iban="iban",
            account_owner="owner",
            sepa_consent=timezone.now(),
        )
        self.client.force_login(member)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=5)

        url = reverse("coop:existing_member_purchases_shares")
        data = {"member_id": member.id, "number_of_shares_to_add": 1}
        response = self.client.post(url, data)

        self.assert_change_not_confirmed_with_error(
            response=response,
            error="The minimum final number of shares is 5, this member currently has 0, adding 1 is not enough.",
            mock_fire_action=mock_fire_action,
        )

        self.assertFalse(CoopShareTransaction.objects.exists())

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_userIsNotAMemberYet_cannotBuyShares(self, mock_fire_action: Mock):
        member = MemberFactory.create(
            iban="iban", account_owner="owner", sepa_consent=timezone.now()
        )
        self.client.force_login(member)
        self.assertFalse(CoopShareTransaction.objects.exists())
        CoopShareTransactionFactory.create(
            member=member, valid_at=get_today() + datetime.timedelta(days=1)
        )

        url = reverse("coop:existing_member_purchases_shares")
        data = {"member_id": member.id, "number_of_shares_to_add": 10}
        response = self.client.post(url, data)

        self.assert_change_not_confirmed_with_error(
            response=response,
            error="Du kannst weitere Genossenschaftsanteile erst zeichnen, wenn du formal Mitglied der Genossenschaft geworden bist.",
            mock_fire_action=mock_fire_action,
        )

        self.assertEqual(1, CoopShareTransaction.objects.count())

    def test_post_normalMemberTriesToActAsAdmin_returns403AndDontPurchaseAnything(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("coop:existing_member_purchases_shares")
        data = {"member_id": member.id, "number_of_shares_to_add": 3, "as_admin": True}
        response = self.client.post(url, data)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        self.assertFalse(CoopShareTransaction.objects.exists())
        self.assertEqual(
            {"detail": "Du hast hast die nötige Berechtigung nicht."},
            response.json(),
        )

    def test_post_sendingLessThanTheMinimumShareAsAdmin_dontValidateMinimumNumberOfShares(
        self,
    ):
        GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=100)
        )
        admin = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create(
            is_superuser=False,
            iban="test_iban",
            account_owner="test_owner",
            sepa_consent=timezone.now(),
        )
        self.client.force_login(admin)
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=5)

        data = {
            "member_id": other_member.id,
            "number_of_shares_to_add": 1,
            "as_admin": True,
            "start_date": datetime.date(year=2021, month=7, day=8),
        }
        response = self.client.post(
            reverse("coop:existing_member_purchases_shares"), data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        transaction = CoopShareTransaction.objects.get()
        self.assertEqual(1, transaction.quantity)
        self.assertEqual(datetime.date(year=2021, month=7, day=8), transaction.valid_at)

    def test_post_memberWithExistingBankDataDoesRequestWithoutBankData_executePurchase(
        self,
    ):
        GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=100)
        )

        member = MemberFactory.create(
            is_superuser=False,
            iban="test_iban",
            account_owner="test_owner",
            sepa_consent=timezone.now(),
        )
        self.client.force_login(member)

        url = reverse("coop:existing_member_purchases_shares")
        data = {
            "member_id": member.id,
            "number_of_shares_to_add": 2,
            "account_owner": "",
            "iban": "",
        }
        response = self.client.post(url, data)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, CoopShareTransaction.objects.count())
        self.assertEqual(2, CoopShareTransaction.objects.get().quantity)

    @patch.object(TransactionalTrigger, "fire_action", autospec=True)
    def test_post_memberWithoutExistingBankDataDoesRequestWithoutBankData_returnsError(
        self, mock_fire_action: Mock
    ):
        GrowingPeriodFactory.create(
            start_date=get_today() - datetime.timedelta(days=100)
        )

        member = MemberFactory.create(
            is_superuser=False,
            iban="",
            account_owner="",
            sepa_consent=timezone.now(),
        )
        self.client.force_login(member)

        url = reverse("coop:existing_member_purchases_shares")
        data = {
            "member_id": member.id,
            "number_of_shares_to_add": 2,
        }
        response = self.client.post(url, data)

        self.assert_change_not_confirmed_with_error(
            response=response,
            error="Dieses Mitglied braucht noch Bank-Daten (IBAN usw.)",
            mock_fire_action=mock_fire_action,
        )
        self.assertFalse(CoopShareTransaction.objects.exists())

    def assert_change_not_confirmed_with_error(
        self, response, error: str, mock_fire_action: Mock
    ):
        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()

        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(error, response_content["error"])
        mock_fire_action.assert_not_called()
