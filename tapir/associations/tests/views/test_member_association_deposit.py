import datetime
from unittest.mock import patch

from tapir.accounts.models import TapirUser
from tapir.wirgarten.constants import Permission

from django.urls import reverse

from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.models import AssociationDepositAccount
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from decimal import Decimal


class TestMemberAssociationDeposit(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, True
        )
        self._set_parameter(
            ParameterKeys.ASSOCIATION_DEPOSIT_NAME, "Investitionsbeitrag"
        )
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self.member = MemberFactory()
        self.other = MemberFactory()
        AssociationMembershipFactory(
            member=self.member, start_date=datetime.date(2026, 11, 5), end_date=None
        )
        AssociationDepositSignupHandler.create_signup_deposit(
            self.member,
            Decimal("200"),
            datetime.date(2026, 11, 5),
            True,
            self.member,
            {},
        )
        self.url = reverse("associations:member_deposit")

    def test_self_can_read_and_explicitly_increase_total_with_idempotent_retry(self):
        self.client.force_login(self.member)
        data = self.client.get(self.url, {"member_id": self.member.pk}).json()
        self.assertEqual("Investitionsbeitrag", data["settings"]["name"])
        self.assertEqual(200, data["agreed_amount"])
        preview = self.client.post(
            reverse("associations:deposit_increase_preview"),
            {"member_id": self.member.pk, "total_amount": "250"},
        ).json()
        for _ in range(2):
            response = self.client.post(
                self.url,
                {
                    "member_id": self.member.pk,
                    "total_amount": "250",
                    "confirmation": preview["confirmation"],
                },
            )
            self.assertEqual(200, response.status_code, response.content)
            self.assertEqual(250, response.json()["agreed_amount"])
        self.assertEqual(1, Payment.objects.count())

    def test_other_member_cannot_read_or_change_deposit(self):
        self.client.force_login(self.other)
        self.assertEqual(
            403, self.client.get(self.url, {"member_id": self.member.pk}).status_code
        )
        self.assertEqual(
            403,
            self.client.post(
                self.url, {"member_id": self.member.pk, "total_amount": "250"}
            ).status_code,
        )
        self.assertEqual(
            Decimal("200"), AssociationDepositAccount.objects.get().agreed_amount
        )

    def test_anonymous_cannot_read_or_change_deposit(self):
        self.assertIn(
            self.client.get(self.url, {"member_id": self.member.pk}).status_code,
            [401, 403],
        )
        self.assertIn(
            self.client.post(
                self.url, {"member_id": self.member.pk, "total_amount": "250"}
            ).status_code,
            [401, 403],
        )

    def test_disabled_feature_preserves_readable_history_but_rejects_increase(self):
        self.client.force_login(self.member)
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        response = self.client.get(self.url, {"member_id": self.member.pk})
        self.assertTrue(response.json()["visible"])
        self.assertFalse(response.json()["can_increase"])
        self.assertEqual(
            400,
            self.client.post(
                self.url, {"member_id": self.member.pk, "total_amount": "250"}
            ).status_code,
        )

    def test_account_manager_can_read_without_being_offered_financial_changes(self):
        self.client.force_login(self.other)
        with patch.object(
            TapirUser,
            "has_perm",
            autospec=True,
            side_effect=lambda user, permission, obj=None: permission
            == Permission.Accounts.MANAGE,
        ):
            response = self.client.get(self.url, {"member_id": self.member.pk})
            self.assertEqual(200, response.status_code, response.content)
            self.assertFalse(response.json()["can_increase"])
            response = self.client.post(
                self.url, {"member_id": self.member.pk, "total_amount": "250"}
            )
            self.assertEqual(403, response.status_code)

    def test_multiple_valid_receipts_keep_large_total_readable(self):
        for reference in ["large-receipt-1", "large-receipt-2"]:
            AssociationDepositReceiptRecorder.record_received_deposit(
                self.member,
                Decimal("500000"),
                datetime.date(2026, 11, 5),
                reference,
                "Kontoauszug",
                self.member,
                {},
            )
        self.client.force_login(self.member)
        self.client.raise_request_exception = False
        response = self.client.get(self.url, {"member_id": self.member.pk})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1000000, response.json()["received_amount"])
        self.assertEqual(200, response.json()["agreed_amount"])
        self.assertEqual(0, response.json()["committed_amount"])
        self.assertEqual(999800, response.json()["overpayment_credit"])
        self.assertEqual(0, response.json()["pending_amount"])
        self.assertFalse(Payment.objects.exists())
