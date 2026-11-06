import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositRefund,
    AssociationDepositRefundCreatedLogEntry,
)
from tapir.associations.services.association_deposit_agreement_authorizer import (
    AssociationDepositAgreementAuthorizer,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_receipt_recorder import (
    AssociationDepositReceiptRecorder,
)
from tapir.associations.services.association_deposit_refund_recorder import (
    AssociationDepositRefundRecorder,
)
from tapir.associations.services.association_deposit_signup_handler import (
    AssociationDepositSignupHandler,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.configuration.models import TapirParameter
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import (
    TapirFactoryMixin,
    mock_keycloak,
    mock_timezone,
)


class TestAssociationDepositRefundRaces(TapirFactoryMixin, TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.factory_setup()
        cache.clear()
        mock_keycloak(self)
        configure_mail_module()
        mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        self.today = datetime.date(2026, 11, 6)
        ParameterDefinitions().import_definitions(bulk_create=True)
        for key, value in {
            ParameterKeys.ORGANISATION_LEGAL_STATUS: LEGAL_STATUS_ASSOCIATION,
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED: True,
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED: True,
            ParameterKeys.PAYMENT_DUE_DAY: 5,
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "NL88ABNA2011060885",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "DE98ZZZ09999999999",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
        }.items():
            TapirParameter.objects.filter(key=key).update(value=str(value))
        self.member = MemberFactory(
            is_superuser=True, iban="NL88ABNA2011060885", account_owner="Test Mitglied"
        )
        AssociationMembershipFactory(member=self.member, start_date=self.today)
        AssociationDepositSignupHandler.create_signup_deposit(
            self.member,
            Decimal("200"),
            self.today,
            True,
            self.member,
            {},
            payment_option="standard_instalments",
            expected_instalments=4,
        )
        AssociationDepositReceiptRecorder.record_received_deposit(
            self.member,
            Decimal("100"),
            self.today,
            "original-cash",
            "Kontoauszug",
            self.member,
            {},
        )
        self.account = AssociationDepositAccount.objects.get(member=self.member)
        self.revision = self.account.agreement_revision

    def concurrent(self, actions):
        barrier = Barrier(2)

        def worker(action):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                member = Member.objects.get(pk=self.member.pk)
                barrier.wait(timeout=10)
                try:
                    if action == "receipt":
                        return (
                            AssociationDepositReceiptRecorder.record_received_deposit(
                                member,
                                Decimal("25"),
                                self.today,
                                "later-cash",
                                "Kontoauszug",
                                member,
                                {},
                            ).pk
                        )
                    if action == "export":
                        return PaymentExportBuilder.export_association_deposit_payments(
                            datetime.date(2027, 3, 5), False, {}
                        )
                    if action == "agreement":
                        return (
                            AssociationDepositAgreementAuthorizer.authorize_agreement(
                                member,
                                Decimal("150"),
                                self.today,
                                4,
                                self.today,
                                "Neue Zustimmung",
                                self.revision,
                                uuid.uuid4(),
                                member,
                                {},
                            ).pk
                        )
                    return AssociationDepositRefundRecorder.record_external_refund(
                        member,
                        Decimal("25"),
                        self.today,
                        action,
                        "Bankseitig ausgeführte Rückzahlung",
                        True,
                        self.revision,
                        Decimal("0"),
                        member,
                        {},
                    ).pk
                except ValidationError as error:
                    if "inzwischen" in str(error):
                        return "stale"
                    raise
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(worker, action) for action in actions]
            return [result.result(timeout=20) for result in results]

    def test_same_refund_reference_race_records_and_debits_balance_once(self):
        first, second = self.concurrent(["refund", "refund"])
        self.assertEqual(first, second)
        self.assertEqual(1, AssociationDepositRefund.objects.count())
        self.assertEqual(1, AssociationDepositRefundCreatedLogEntry.objects.count())
        self.assertEqual(
            75,
            AssociationDepositDetailsProvider.get_deposit_details(self.member, {})[
                "retained_amount"
            ],
        )

    def test_refund_and_receipt_race_leave_cash_consistent_and_no_rate_inflation(self):
        original_ids = set(self.account.payments.values_list("pk", flat=True))
        self.concurrent(["refund", "receipt"])
        details = AssociationDepositDetailsProvider.get_deposit_details(self.member, {})
        self.assertEqual(
            (125, 25, 100, 0),
            tuple(
                details[key]
                for key in [
                    "received_amount",
                    "refunded_amount",
                    "retained_amount",
                    "pending_amount",
                ]
            ),
        )
        self.assertLessEqual(
            sum(self.account.payments.values_list("amount", flat=True)), Decimal("100")
        )
        self.assertTrue(
            set(self.account.payments.values_list("pk", flat=True)) <= original_ids
        )
        self.account.refresh_from_db()
        self.assertTrue(self.account.refund_requires_agreement)

    def test_refund_and_export_race_hold_collection_or_require_fresh_refund_confirmation(
        self,
    ):
        refund_result, _ = self.concurrent(["refund", "export"])
        if refund_result == "stale":
            self.assertFalse(AssociationDepositRefund.objects.exists())
            self.assertEqual(
                2, self.account.payments.filter(transaction__isnull=False).count()
            )
        else:
            self.assertEqual(1, AssociationDepositRefund.objects.count())
            self.assertFalse(
                self.account.payments.filter(transaction__isnull=False).exists()
            )
        self.assertTrue(
            all(
                amount == Decimal("50")
                for amount in self.account.payments.values_list("amount", flat=True)
            )
        )

    def test_refund_and_new_agreement_race_require_reconfirmation_of_losing_request(
        self,
    ):
        results = self.concurrent(["refund", "agreement"])
        self.assertEqual(1, results.count("stale"))
        self.account.refresh_from_db()
        if results[0] == "stale":
            self.assertFalse(AssociationDepositRefund.objects.exists())
            self.assertFalse(self.account.refund_requires_agreement)
            self.assertEqual(150, self.account.agreed_amount)
        else:
            self.assertTrue(self.account.refund_requires_agreement)
            self.assertEqual(200, self.account.agreed_amount)
            self.assertEqual(1, AssociationDepositRefund.objects.count())
